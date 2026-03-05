#!/bin/bash
# ============================================================
# fix_bug2_cooldown_sync.sh
# BUG-2: cooldown_seconds 즉시 반영 강화
#
# 분석 결과 요약:
#   - app.py는 이미 STEP5에서 cooldown을 alert_manager에 반영하고 있음
#   - 단, 조건이 'cooldown_seconds' in incoming 이라서
#     UI가 cooldown 없이 부분 저장(alerts만, thresholds만)할 경우 누락됨
#   - 수정: incoming 대신 merged 값을 사용 → 항상 파일에 저장된 값과 동기화
#
# 추가 수정 (BUG-1 후속):
#   - auto_controller.py _send_sensor_alert() 에서
#     _tn.send_message() → _tn.send() 로 수정
#     (TelegramNotifier에 send_message() 메서드가 없어 조용히 실패하던 버그)
# ============================================================

BASE="/home/pi/smart_farm"
APP_PY="$BASE/web/app.py"
CTRL_PY="$BASE/irrigation/auto_controller.py"

APP_BAK="${APP_PY}.bak_$(date +%Y%m%d_%H%M%S)"
CTRL_BAK="${CTRL_PY}.bak_$(date +%Y%m%d_%H%M%S)"

echo "========================================"
echo " BUG-2 수정 스크립트 시작"
echo "========================================"

# ── 사전 확인 ──────────────────────────────
if [ ! -f "$APP_PY" ]; then
    echo "❌ 파일 없음: $APP_PY"; exit 1
fi
if [ ! -f "$CTRL_PY" ]; then
    echo "❌ 파일 없음: $CTRL_PY"; exit 1
fi

# ── 백업 ───────────────────────────────────
cp "$APP_PY"  "$APP_BAK"
cp "$CTRL_PY" "$CTRL_BAK"
echo "✅ 백업: $APP_BAK"
echo "✅ 백업: $CTRL_BAK"

# ════════════════════════════════════════════
# 수정 1: app.py — STEP 5 쿨다운 반영 조건 강화
# ════════════════════════════════════════════
echo ""
echo "── [1/2] app.py STEP5 쿨다운 반영 수정 중..."
python3 << 'PYEOF'
TARGET = "/home/pi/smart_farm/web/app.py"

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

# ── 교체 대상 (기존 STEP 5 cooldown 블록) ──────────────────────
OLD = (
    "        if alert_manager and 'cooldown_seconds' in incoming:\n"
    "            try:\n"
    "                alert_manager.cooldown_seconds = int(incoming['cooldown_seconds'])\n"
    "                print(f'[Save] 쿨다운 즉시 반영: {alert_manager.cooldown_seconds}s')\n"
    "            except Exception:\n"
    "                pass"
)

# ── 교체 내용 (merged 값 사용 + 디버그 로그 강화) ───────────────
NEW = (
    "        # ── BUG-2 fix: incoming 유무와 무관하게 merged 값으로 항상 동기화\n"
    "        #   (alerts만 저장하거나 thresholds만 저장하는 부분 업데이트 시에도 반영)\n"
    "        if alert_manager:\n"
    "            try:\n"
    "                new_cooldown = int(merged.get('cooldown_seconds', 300))\n"
    "                if alert_manager.cooldown_seconds != new_cooldown:\n"
    "                    print(f'[Save] 쿨다운 변경: {alert_manager.cooldown_seconds}s → {new_cooldown}s')\n"
    "                    alert_manager.cooldown_seconds = new_cooldown\n"
    "                else:\n"
    "                    print(f'[Save] 쿨다운 유지: {new_cooldown}s (변경 없음)')\n"
    "            except Exception as _ce:\n"
    "                print(f'[Save] 쿨다운 반영 실패: {_ce}')"
)

assert OLD in src, (
    "ERROR: app.py STEP5 교체 대상 문자열을 찾지 못했습니다.\n"
    "이미 수정된 파일이거나 버전이 다릅니다."
)

src = src.replace(OLD, NEW, 1)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)

print("✅ app.py STEP5 쿨다운 반영 수정 완료")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ app.py 수정 실패 - 백업으로 복구"
    cp "$APP_BAK" "$APP_PY"
    exit 1
fi

# ════════════════════════════════════════════
# 수정 2: auto_controller.py — send_message → send
# ════════════════════════════════════════════
echo ""
echo "── [2/2] auto_controller.py send_message 버그 수정 중..."
python3 << 'PYEOF'
TARGET = "/home/pi/smart_farm/irrigation/auto_controller.py"

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

OLD = "            _tn.send_message(f'🚨 [자동관수 오류]\\n{message}')"
NEW = "            _tn.send(f'🚨 [자동관수 오류]\\n{message}')"

if OLD not in src:
    # 이미 수정됐거나 다른 버전인지 확인
    if "_tn.send(" in src and "_send_sensor_alert" in src:
        print("ℹ️  auto_controller.py: 이미 send()로 수정되어 있음 (변경 없음)")
    else:
        print("⚠️  auto_controller.py: 교체 대상 문자열 없음 — 수동 확인 필요")
        print("    grep 결과:")
        import subprocess
        result = subprocess.run(
            ["grep", "-n", "send_message\\|_tn.send", TARGET],
            capture_output=True, text=True
        )
        print(result.stdout or "    (해당 라인 없음)")
else:
    src = src.replace(OLD, NEW, 1)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(src)
    print("✅ auto_controller.py send_message → send 수정 완료")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ auto_controller.py 수정 실패 - 백업으로 복구"
    cp "$CTRL_BAK" "$CTRL_PY"
    exit 1
fi

# ── 결과 검증 ───────────────────────────────
echo ""
echo "── 수정 결과 검증..."

echo ""
echo "[1] app.py STEP5 — 쿨다운 반영 코드 확인:"
grep -n "BUG-2 fix\|new_cooldown\|쿨다운 변경\|쿨다운 유지" "$APP_PY"

echo ""
echo "[2] auto_controller.py — send 메서드 확인:"
grep -n "_tn\.send\b\|_tn\.send_message" "$CTRL_PY"

echo ""
echo "[3] 현재 notifications.json cooldown 값:"
python3 -c "
import json
with open('/home/pi/smart_farm/config/notifications.json') as f:
    cfg = json.load(f)
cs = cfg.get('cooldown_seconds', '(없음)')
print(f'  cooldown_seconds = {cs}초 ({int(cs)//60}분)' if isinstance(cs, int) else f'  cooldown_seconds = {cs}')
"

echo ""
echo "========================================"
echo " ✅ BUG-2 수정 완료"
echo ""
echo " 변경 요약:"
echo "   [app.py] STEP5 쿨다운 반영 조건 강화"
echo "     이전: 'cooldown_seconds' in incoming 일 때만 반영"
echo "     이후: 항상 merged 값으로 alert_manager와 동기화"
echo "           (부분 저장 시에도 누락 없이 반영)"
echo ""
echo "   [auto_controller.py] _send_sensor_alert 버그 수정"
echo "     이전: _tn.send_message() → 존재하지 않는 메서드 (조용히 실패)"
echo "     이후: _tn.send() → 정상 텔레그램 발송"
echo ""
echo " 서비스 재시작:"
echo "   sudo systemctl restart smart-farm.service"
echo "   sudo journalctl -u smart-farm.service --since '1 min ago' --no-pager | grep -E 'cooldown|쿨다운|Save'"
echo "========================================"
