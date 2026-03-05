#!/usr/bin/env bash
# =============================================================================
# fix_bug5_thread_watchdog.sh  (v2 - heredoc 셸 해석 문제 해결)
# BUG-5: periodic_data_sender 스레드 watchdog 자동 재시작
# =============================================================================

set -e

BASE="/home/pi/smart_farm"
APP="$BASE/web/app.py"
STATUS="$BASE/docs/STATUS.md"
PATCH_SCRIPT="/tmp/bug5_patch.py"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=================================================="
echo "  BUG-5: periodic_data_sender 스레드 자동 재시작"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================="

# ──────────────────────────────────────────────────
# STEP 1: 백업
# ──────────────────────────────────────────────────
echo ""
echo "📦 [STEP 1] 백업 생성..."
cp "$APP" "${APP}.bak_${TIMESTAMP}"
echo "  ✅ app.py → ${APP}.bak_${TIMESTAMP}"

# ──────────────────────────────────────────────────
# STEP 2: Python 패치 스크립트를 별도 파일로 생성
#         (heredoc 셸 해석 문제 완전 우회)
# ──────────────────────────────────────────────────
echo ""
echo "🔧 [STEP 2] 패치 스크립트 생성 및 실행..."

cat > "$PATCH_SCRIPT" << 'ENDOFPYTHON'
#!/usr/bin/env python3
"""BUG-5 패치: app.py에 watchdog 자동 재시작 추가"""
import sys
import re

app_path    = sys.argv[1]
status_path = sys.argv[2]

with open(app_path, 'r', encoding='utf-8') as f:
    src = f.read()

exit_code = 0

# ============================================================
# PATCH 1-a: periodic_data_sender 맨 앞에 consecutive_errors 추가
# ============================================================
OLD_HEAD = (
    '    print("🔄 periodic_data_sender 스레드 시작")\n'
    '    \n'
    '    while monitoring_active:'
)
NEW_HEAD = (
    '    print("🔄 periodic_data_sender 스레드 시작")\n'
    '    consecutive_errors = 0   # 연속 오류 카운터 (BUG-5)\n'
    '\n'
    '    while monitoring_active:'
)

if 'consecutive_errors' in src:
    print('  ⚠️  PATCH1-a: 이미 적용됨 → 건너뜀')
elif OLD_HEAD in src:
    src = src.replace(OLD_HEAD, NEW_HEAD, 1)
    print('  ✅ PATCH1-a: consecutive_errors 초기화 삽입')
else:
    print('  ❌ PATCH1-a: 패턴 없음')
    exit_code = 1

# ============================================================
# PATCH 1-b: except 블록 + time.sleep 교체
#   기존: except 후 time.sleep(10) 이 try 밖에 있음
#   변경: consecutive_errors 추가 + time.sleep을 try/except로 보호
# ============================================================
OLD_EXCEPT = (
    '        except Exception as e:\n'
    '            print(f"❌ 주기적 데이터 전송 오류: {e}")\n'
    '            import traceback\n'
    '            traceback.print_exc()\n'
    '        \n'
    '        # 10초 대기\n'
    '        time.sleep(10)\n'
    '    \n'
    '    print("⏹️  periodic_data_sender 스레드 종료")'
)
NEW_EXCEPT = (
    '            consecutive_errors = 0   # 성공 시 리셋\n'
    '\n'
    '        except Exception as e:\n'
    '            consecutive_errors += 1\n'
    '            print(f"❌ 주기적 데이터 전송 오류 ({consecutive_errors}회 연속): {e}")\n'
    '            import traceback\n'
    '            traceback.print_exc()\n'
    '            # 연속 10회 오류 시 텔레그램 CRITICAL 알림 (BUG-5)\n'
    '            if consecutive_errors == 10:\n'
    '                try:\n'
    '                    if telegram_notifier:\n'
    '                        telegram_notifier.send(\n'
    '                            "🚨 [시스템 경고]\\n"\n'
    '                            "periodic_data_sender 10회 연속 오류\\n"\n'
    '                            "대시보드 업데이트가 중단됐을 수 있습니다."\n'
    '                        )\n'
    '                except Exception:\n'
    '                    pass\n'
    '\n'
    '        # 10초 대기 (try/except 보호 — 예외로 루프 탈출 방지, BUG-5)\n'
    '        try:\n'
    '            time.sleep(10)\n'
    '        except Exception:\n'
    '            pass\n'
    '\n'
    '    print("⏹️  periodic_data_sender 스레드 종료")'
)

if 'consecutive_errors += 1' in src:
    print('  ⚠️  PATCH1-b: 이미 적용됨 → 건너뜀')
elif OLD_EXCEPT in src:
    src = src.replace(OLD_EXCEPT, NEW_EXCEPT, 1)
    print('  ✅ PATCH1-b: except + time.sleep 교체 완료')
else:
    # fallback: time.sleep(10) 라인만 보호
    pattern_sleep = re.compile(
        r'\n        # 10초 대기\n        time\.sleep\(10\)\n'
    )
    if pattern_sleep.search(src):
        new_sleep = (
            '\n'
            '        # 10초 대기 (try/except 보호 — 루프 탈출 방지, BUG-5)\n'
            '        try:\n'
            '            time.sleep(10)\n'
            '        except Exception:\n'
            '            pass\n'
        )
        src = pattern_sleep.sub(new_sleep, src, count=1)
        print('  ✅ PATCH1-b(fallback): time.sleep try/except 보호 추가')
    else:
        print('  ❌ PATCH1-b: 패턴 없음')
        exit_code = 1

# ============================================================
# PATCH 2+3: _start_periodic_sender() + _watchdog_loop() 추가
#   "def init_monitoring_system():" 바로 앞에 삽입
# ============================================================
WATCHDOG_FUNCS = (
    '\n'
    '\n'
    'def _start_periodic_sender():\n'
    '    """periodic_data_sender 스레드 생성 및 시작 (BUG-5 watchdog 헬퍼)"""\n'
    '    global monitoring_thread\n'
    '    t = threading.Thread(\n'
    '        target=periodic_data_sender, daemon=True, name="PeriodicSender"\n'
    '    )\n'
    '    t.start()\n'
    '    monitoring_thread = t\n'
    '    print("🔄 periodic_data_sender 스레드 (재)시작됨")\n'
    '    return t\n'
    '\n'
    '\n'
    'def _watchdog_loop():\n'
    '    """periodic_data_sender 스레드 감시 및 자동 재시작 (BUG-5)"""\n'
    '    global monitoring_active, monitoring_thread\n'
    '    print("🐕 watchdog 스레드 시작")\n'
    '\n'
    '    while monitoring_active:\n'
    '        time.sleep(30)   # 30초마다 체크\n'
    '\n'
    '        if not monitoring_active:\n'
    '            break\n'
    '\n'
    '        if monitoring_thread is None or not monitoring_thread.is_alive():\n'
    '            if monitoring_active:   # 정상 종료가 아닌 경우만 재시작\n'
    '                print("⚠️  [watchdog] periodic_data_sender 스레드 죽음 → 재시작")\n'
    '                try:\n'
    '                    if telegram_notifier:\n'
    '                        telegram_notifier.send(\n'
    '                            "⚠️ [시스템 복구]\\n"\n'
    '                            "periodic_data_sender 스레드가 종료돼 재시작했습니다.\\n"\n'
    '                            "대시보드 실시간 업데이트가 복구됩니다."\n'
    '                        )\n'
    '                except Exception:\n'
    '                    pass\n'
    '                _start_periodic_sender()\n'
    '\n'
    '    print("🐕 watchdog 스레드 종료")\n'
    '\n'
    '\n'
)

INIT_ANCHOR = 'def init_monitoring_system():'

if '_watchdog_loop' in src:
    print('  ⚠️  PATCH2+3: watchdog 이미 존재 → 건너뜀')
elif INIT_ANCHOR in src:
    src = src.replace(INIT_ANCHOR, WATCHDOG_FUNCS + INIT_ANCHOR, 1)
    print('  ✅ PATCH2: _start_periodic_sender() 추가')
    print('  ✅ PATCH3: _watchdog_loop() 추가')
else:
    print('  ❌ PATCH2+3: def init_monitoring_system() 을 찾지 못했습니다')
    exit_code = 1

# ============================================================
# PATCH 4: init_monitoring_system 내 스레드 시작 → 헬퍼 + watchdog 으로 교체
# ============================================================
OLD_THREAD = (
    '        monitoring_active = True\n'
    '        monitoring_thread = threading.Thread(target=periodic_data_sender, daemon=True)\n'
    '        monitoring_thread.start()\n'
    '        print("🚀 모니터링 자동 시작됨 (서버 시작 시)")'
)
NEW_THREAD = (
    '        monitoring_active = True\n'
    '        _start_periodic_sender()   # BUG-5: 헬퍼 함수로 시작\n'
    '\n'
    '        # BUG-5: watchdog 스레드 시작 (스레드 죽으면 자동 재시작)\n'
    '        _watchdog_thread = threading.Thread(\n'
    '            target=_watchdog_loop, daemon=True, name="SenderWatchdog"\n'
    '        )\n'
    '        _watchdog_thread.start()\n'
    '        print("🚀 모니터링 자동 시작됨 (서버 시작 시)")\n'
    '        print("🐕 watchdog 스레드 시작됨")'
)

if 'SenderWatchdog' in src:
    print('  ⚠️  PATCH4: watchdog 시작 이미 존재 → 건너뜀')
elif OLD_THREAD in src:
    src = src.replace(OLD_THREAD, NEW_THREAD, 1)
    print('  ✅ PATCH4: init_monitoring_system watchdog 시작 코드 추가')
else:
    # fallback 정규식
    pattern_init = re.compile(
        r'(        monitoring_active = True\n'
        r'        monitoring_thread = threading\.Thread\(target=periodic_data_sender, daemon=True\)\n'
        r'        monitoring_thread\.start\(\)\n'
        r'        print\("🚀 모니터링 자동 시작됨 \(서버 시작 시\)"\))'
    )
    if pattern_init.search(src):
        src = pattern_init.sub(NEW_THREAD, src, count=1)
        print('  ✅ PATCH4(fallback): watchdog 시작 코드 추가')
    else:
        print('  ❌ PATCH4: 스레드 시작 패턴 없음')
        exit_code = 1

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(src)
print('  ✅ app.py 저장 완료')

# ============================================================
# STATUS.md 갱신
# ============================================================
from datetime import date
today = date.today().strftime('%Y-%m-%d')

with open(status_path, 'r', encoding='utf-8') as f:
    md = f.read()

changed = False

# 헤더 날짜
new_md = re.sub(r'> 최종 업데이트: \d{4}-\d{2}-\d{2}',
                f'> 최종 업데이트: {today}', md)
if new_md != md:
    md = new_md
    print('  ✅ STATUS.md 날짜 갱신')
    changed = True

# 완료 테이블 BUG-5 행 추가
BUG1B = '| BUG-1b | _send_sensor_alert() 쿨다운 추가 (30분, sensor_alert_cooldown) | ✅ 완료 | irrigation/auto_controller.py, config/soil_sensors.json |'
BUG5  = '| BUG-5 | periodic_data_sender 스레드 watchdog 자동 재시작 | ✅ 완료 | web/app.py |'
if 'BUG-5 |' not in md and BUG1B in md:
    md = md.replace(BUG1B, BUG1B + '\n' + BUG5)
    print('  ✅ STATUS.md 완료 테이블 BUG-5 추가')
    changed = True

# Git 커밋 이력
new_commit = f'| {today} | fix(BUG-5): periodic_data_sender watchdog 자동 재시작 추가 |'
if new_commit not in md:
    md = re.sub(
        r'(\| \d{4}-\d{2}-\d{2} \| fix\(BUG-)',
        new_commit + '\n' + r'\1',
        md, count=1
    )
    print('  ✅ STATUS.md 커밋 이력 추가')
    changed = True

# BUG-5 수정 상세 섹션
BUG5_DETAIL = f"""
---

## ✅ BUG-5 수정 상세 ({today})

**파일**: `web/app.py`

**문제**: `periodic_data_sender` 스레드가 죽으면 대시보드 실시간 업데이트가 조용히 멈춤
- `time.sleep(10)` 이 try/except 밖에 있어 예외 시 루프 탈출 가능
- 스레드가 죽어도 감지·재시작 로직 없음

**수정 내용**:
- PATCH1: `consecutive_errors` 카운터 + `time.sleep` try/except 보호 + 10회 연속 오류 시 텔레그램 알림
- PATCH2: `_start_periodic_sender()` 헬퍼 함수 (스레드 시작 로직 함수화)
- PATCH3: `_watchdog_loop()` — 30초마다 `is_alive()` 확인, 죽으면 재시작 + 텔레그램 복구 알림
- PATCH4: `init_monitoring_system`에서 watchdog 스레드(`SenderWatchdog`) 함께 시작

| 상황 | 이전 | 이후 |
|---|---|---|
| time.sleep 중 예외 | 루프 탈출 → 스레드 종료 ❌ | try/except 보호 → 계속 ✅ |
| 스레드 예기치 않은 종료 | 감지 불가 ❌ | watchdog 30초 내 감지 → 재시작 ✅ |
| 10회 연속 오류 | 조용히 실패 ❌ | 텔레그램 CRITICAL 알림 ✅ |

"""

if 'BUG-5 수정 상세' not in md:
    target = '## 🔴 발견된 잠재 버그 (미수정)'
    if target in md:
        md = md.replace(target, BUG5_DETAIL.strip() + '\n\n---\n\n' + target)
        print('  ✅ STATUS.md BUG-5 상세 섹션 추가')
        changed = True

# 다음 작업 후보 BUG-5 완료 표시
old_row = '| ⭐⭐⭐ | BUG-5 | periodic_data_sender 스레드 자동 재시작 | 20분 |'
new_row = '| ~~⭐⭐⭐~~ | ~~BUG-5~~ | ~~periodic_data_sender 스레드 자동 재시작~~ | ✅ 완료 |'
if old_row in md:
    md = md.replace(old_row, new_row)
    print('  ✅ STATUS.md 다음 작업 BUG-5 완료 표시')
    changed = True

with open(status_path, 'w', encoding='utf-8') as f:
    f.write(md)
if changed:
    print('  ✅ STATUS.md 저장 완료')
else:
    print('  ℹ️  STATUS.md 변경 없음')

sys.exit(exit_code)
ENDOFPYTHON

python3 "$PATCH_SCRIPT" "$APP" "$STATUS"

# ──────────────────────────────────────────────────
# STEP 3: 검증
# ──────────────────────────────────────────────────
echo ""
echo "🔍 [STEP 3] 패치 결과 검증..."

python3 - "$APP" << 'VERIFY'
import sys
path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()
checks = [
    ('consecutive_errors',            'PATCH1: 연속 오류 카운터'),
    ('consecutive_errors == 10',      'PATCH1: 10회 오류 시 텔레그램'),
    ('except Exception:\n            pass', 'PATCH1: time.sleep 보호'),
    ('def _start_periodic_sender',    'PATCH2: 헬퍼 함수'),
    ('def _watchdog_loop',            'PATCH3: watchdog 함수'),
    ('monitoring_thread.is_alive',    'PATCH3: is_alive 체크'),
    ('SenderWatchdog',                'PATCH4: watchdog 스레드 시작'),
]
ok = True
for kw, desc in checks:
    found = kw in src
    print(f"  {'✅' if found else '❌'} {desc}")
    if not found:
        ok = False
if ok:
    print('\n  🎉 모든 검증 통과!')
else:
    print('\n  ⚠️  일부 항목 누락')
    sys.exit(1)
VERIFY

# ──────────────────────────────────────────────────
# STEP 4: 서비스 재시작
# ──────────────────────────────────────────────────
echo ""
echo "🔄 [STEP 4] 서비스 재시작..."
sudo systemctl restart smart-farm.service
sleep 6

echo ""
echo "📋 watchdog 관련 로그:"
sudo journalctl -u smart-farm.service --since "40 sec ago" --no-pager \
  | grep -E "watchdog|Watchdog|PeriodicSender|SenderWatchdog|🐕|🚀|🔄 periodic|ERROR|❌" \
  || echo "  (해당 키워드 없음)"

echo ""
sudo systemctl is-active smart-farm.service \
  && echo "  ✅ 서비스 정상 실행 중" \
  || echo "  ❌ 서비스 이상 확인 필요"

# ──────────────────────────────────────────────────
# 완료
# ──────────────────────────────────────────────────
echo ""
echo "=================================================="
echo "  ✅ BUG-5 패치 완료"
echo "=================================================="
echo ""
echo "  Git 커밋:"
echo "  cd /home/pi/smart_farm"
echo "  git add web/app.py docs/STATUS.md"
echo "  git commit -m 'fix(BUG-5): periodic_data_sender watchdog 자동 재시작'"
echo "  git push origin main"
echo "=================================================="
