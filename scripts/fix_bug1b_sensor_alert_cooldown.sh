#!/usr/bin/env bash
# =============================================================================
# fix_bug1b_sensor_alert_cooldown.sh
# BUG-1b 보완: _send_sensor_alert()에 쿨다운 추가
#
# 변경 대상:
#   - irrigation/auto_controller.py
#       1) __init__에 self._last_sensor_alert_time = None 추가
#       2) _send_sensor_alert() 메서드 → 쿨다운 로직 적용 (30분 기본)
#   - config/soil_sensors.json
#       - irrigation 섹션에 "sensor_alert_cooldown": 1800 추가
#   - docs/STATUS.md
#       - BUG-1b 항목 및 오늘 작업 내용 반영
#
# 실행 방법:
#   bash /home/pi/smart_farm/fix_bug1b_sensor_alert_cooldown.sh
# =============================================================================

set -e

BASE="/home/pi/smart_farm"
CONTROLLER="$BASE/irrigation/auto_controller.py"
JSON="$BASE/config/soil_sensors.json"
STATUS="$BASE/docs/STATUS.md"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=================================================="
echo "  BUG-1b: 센서 오류 알림 쿨다운 적용"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================="

# ──────────────────────────────────────────────────
# STEP 1: 백업
# ──────────────────────────────────────────────────
echo ""
echo "📦 [STEP 1] 백업 생성..."
cp "$CONTROLLER" "${CONTROLLER}.bak_${TIMESTAMP}"
echo "  ✅ auto_controller.py  → ${CONTROLLER}.bak_${TIMESTAMP}"
cp "$JSON" "${JSON}.bak_${TIMESTAMP}"
echo "  ✅ soil_sensors.json   → ${JSON}.bak_${TIMESTAMP}"

# ──────────────────────────────────────────────────
# STEP 2: auto_controller.py 패치 (Python)
# ──────────────────────────────────────────────────
echo ""
echo "🔧 [STEP 2] auto_controller.py 패치..."

python3 << PYEOF
import sys
import re

path = "$CONTROLLER"

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

exit_code = 0

# ── PATCH 1: __init__에 _last_sensor_alert_time 추가 ──────────────────────
ANCHOR = "        self.alert_callback     = None"
INSERT = (
    "\n"
    "        # 센서 오류 알림 쿨다운 추적 (BUG-1b)\n"
    "        self._last_sensor_alert_time = None"
)

if "_last_sensor_alert_time" in src:
    print("  ⚠️  PATCH1: 이미 적용돼 있음 → 건너뜀")
elif ANCHOR in src:
    src = src.replace(ANCHOR, ANCHOR + INSERT, 1)
    print("  ✅ PATCH1: _last_sensor_alert_time 초기화 삽입 완료")
else:
    print("  ❌ PATCH1 실패: 삽입 앵커를 찾지 못했습니다.")
    exit_code = 1

# ── PATCH 2: _send_sensor_alert() 메서드 교체 (정규식 방식) ──────────────
# 함수 시그니처 + docstring + 전체 본문을 정규식으로 교체
# 기존 함수: 쿨다운 없이 _tn.send() 직접 호출
# 신규 함수: 쿨다운 체크 후 전송

NEW_METHOD = '''    def _send_sensor_alert(self, message):
        """토양센서 오류를 텔레그램으로 알림 (쿨다운 적용, BUG-1b)"""
        now = datetime.now()
        cooldown = self.irrigation_cfg.get('sensor_alert_cooldown', 1800)  # 기본 30분

        if self._last_sensor_alert_time is not None:
            elapsed = (now - self._last_sensor_alert_time).total_seconds()
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                print(f'\\u23f8\\ufe0f  센서 오류 알림 쿨다운 중 ({remaining}초 남음) - 텔레그램 전송 생략')
                return

        try:
            import sys as _sys
            _main = (_sys.modules.get('__main__') or
                     _sys.modules.get('web.app') or
                     _sys.modules.get('app'))
            _tn = getattr(_main, 'telegram_notifier', None)
            if _tn:
                _tn.send(f'\\U0001f6a8 [자동관수 오류]\\n{message}')
                self._last_sensor_alert_time = now
                print(f'\\U0001f4e8 센서 오류 알림 전송 완료 (다음 알림: {cooldown // 60}분 후)')
            else:
                # 텔레그램 없어도 쿨다운 타이머는 시작
                self._last_sensor_alert_time = now
        except Exception as e:
            print(f'\\u26a0\\ufe0f  텔레그램 알림 실패: {e}')'''

if 'sensor_alert_cooldown' in src and '_last_sensor_alert_time = now' in src:
    print("  ⚠️  PATCH2: 이미 쿨다운 로직 적용돼 있음 → 건너뜀")
else:
    # 정규식: def _send_sensor_alert(self, message): 부터 다음 def 전까지 (4-space indent method)
    pattern = re.compile(
        r'(    def _send_sensor_alert\(self, message\):.*?)(?=\n    def |\n# )',
        re.DOTALL
    )
    if pattern.search(src):
        src = pattern.sub(NEW_METHOD, src, count=1)
        print("  ✅ PATCH2: _send_sensor_alert() 쿨다운 로직 교체 완료")
    else:
        print("  ❌ PATCH2 실패: _send_sensor_alert() 메서드를 찾지 못했습니다.")
        exit_code = 1

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)
print("  ✅ auto_controller.py 저장 완료")
sys.exit(exit_code)
PYEOF

# ──────────────────────────────────────────────────
# STEP 3: soil_sensors.json 패치
# ──────────────────────────────────────────────────
echo ""
echo "🔧 [STEP 3] soil_sensors.json 에 sensor_alert_cooldown 추가..."

python3 << PYEOF
import json

path = "$JSON"
with open(path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

irr = cfg.get('irrigation', {})
if 'sensor_alert_cooldown' in irr:
    print(f"  ⚠️  sensor_alert_cooldown 이미 존재: {irr['sensor_alert_cooldown']}초 → 유지")
else:
    irr['sensor_alert_cooldown'] = 1800
    cfg['irrigation'] = irr
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("  ✅ sensor_alert_cooldown = 1800초 (30분) 추가 완료")

print("  현재 irrigation 설정:")
for k, v in cfg['irrigation'].items():
    print(f"    {k}: {v}")
PYEOF

# ──────────────────────────────────────────────────
# STEP 4: 패치 결과 검증
# ──────────────────────────────────────────────────
echo ""
echo "🔍 [STEP 4] 패치 결과 검증..."

python3 << PYEOF
import sys

path = "$CONTROLLER"
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

checks = [
    ('_last_sensor_alert_time = None',
     '__init__: _last_sensor_alert_time 초기화'),
    ('sensor_alert_cooldown',
     '_send_sensor_alert: irrigation_cfg에서 쿨다운 읽기'),
    ('elapsed = (now - self._last_sensor_alert_time).total_seconds()',
     '경과 시간 계산 로직'),
    ('쿨다운 중',
     '쿨다운 생략 로그 메시지'),
    ('self._last_sensor_alert_time = now',
     '알림 후 타임스탬프 갱신'),
    ('cooldown // 60',
     '다음 알림까지 남은 분 계산'),
]

all_ok = True
for keyword, desc in checks:
    if keyword in src:
        print(f"  ✅ {desc}")
    else:
        print(f"  ❌ {desc} — 없음: {repr(keyword)}")
        all_ok = False

if all_ok:
    print("\n  🎉 모든 검증 통과!")
else:
    print("\n  ⚠️  일부 항목 누락 — 수동 확인 필요")
    sys.exit(1)
PYEOF

# ──────────────────────────────────────────────────
# STEP 5: docs/STATUS.md 갱신
# ──────────────────────────────────────────────────
echo ""
echo "📝 [STEP 5] docs/STATUS.md 갱신..."

python3 << PYEOF
import re
from datetime import date

path = "$STATUS"
today = date.today().strftime('%Y-%m-%d')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

changed = False

# ── 헤더 날짜 갱신 ─────────────────────────────────────────────────────────
new_content = re.sub(
    r'> 최종 업데이트: \d{4}-\d{2}-\d{2}',
    f'> 최종 업데이트: {today}',
    content
)
if new_content != content:
    content = new_content
    print("  ✅ 헤더 날짜 갱신")
    changed = True

# ── 완료 테이블에 BUG-1b 행 추가 ─────────────────────────────────────────
BUG2_ROW = "| BUG-2 | cooldown_seconds 즉시 반영 강화 + send_message 오타 수정 | ✅ 완료 | web/app.py, irrigation/auto_controller.py |"
BUG1B_ROW = "| BUG-1b | _send_sensor_alert() 쿨다운 추가 (30분, sensor_alert_cooldown) | ✅ 완료 | irrigation/auto_controller.py, config/soil_sensors.json |"

if 'BUG-1b' not in content and BUG2_ROW in content:
    content = content.replace(BUG2_ROW, BUG2_ROW + "\n" + BUG1B_ROW)
    print("  ✅ 완료 테이블에 BUG-1b 행 추가")
    changed = True
elif 'BUG-1b' in content:
    print("  ⚠️  BUG-1b 이미 존재 → 건너뜀")

# ── Git 커밋 이력 추가 ────────────────────────────────────────────────────
NEW_COMMIT_LINE = f"| {today} | fix(BUG-1b): _send_sensor_alert() 쿨다운 추가 (30분) |"
if NEW_COMMIT_LINE not in content:
    # 커밋 이력 테이블에서 첫 번째 데이터 행 앞에 삽입
    content = re.sub(
        r'(\| \d{4}-\d{2}-\d{2} \| fix\(BUG-)',
        NEW_COMMIT_LINE + '\n' + r'\1',
        content,
        count=1
    )
    print("  ✅ Git 커밋 이력 추가")
    changed = True

# ── BUG-1b 수정 상세 섹션 추가 ───────────────────────────────────────────
BUG1B_SECTION = f"""
---

## ✅ BUG-1b 수정 상세 ({today})

**파일**: `irrigation/auto_controller.py`, `config/soil_sensors.json`

**문제**: `_send_sensor_alert()`에 쿨다운 없이 `check_interval(300초)` + RS-485 타임아웃(~60초)마다
텔레그램 알림이 반복 전송 (~6분 간격 무한 반복)

**원인 분석**:
- `AlertManager.cooldown_seconds` = 3600초 → 수위 경고에만 적용
- `_send_sensor_alert()` → `_tn.send()` 직접 호출 → AlertManager 쿨다운 우회

**수정 내용**:
- `__init__`: `self._last_sensor_alert_time = None` 추가
- `_send_sensor_alert()`: 쿨다운 로직 추가
  - `irrigation_cfg['sensor_alert_cooldown']` 값 읽기 (기본: 1800초 = 30분)
  - 마지막 알림 후 쿨다운 미경과 시 텔레그램 전송 생략 (로그만 출력)
  - 전송 후 `_last_sensor_alert_time` 갱신
- `soil_sensors.json` > `irrigation` 섹션에 `"sensor_alert_cooldown": 1800` 추가

**동작 변화 요약**:
| 상황 | 이전 | 이후 |
|---|---|---|
| 첫 번째 센서 오류 | 즉시 전송 | 즉시 전송 ✅ |
| 6분 후 동일 오류 | 또 전송 ❌ | 쿨다운 중 → 생략 ✅ |
| 30분 후 지속 오류 | 또 전송 ❌ | 재전송 (리마인드) ✅ |
| 하드웨어 미연결 상태 | 6분마다 스팸 ❌ | 최초 1회 + 30분 주기 ✅ |

**쿨다운 설정 변경 방법**:
```bash
# soil_sensors.json에서 sensor_alert_cooldown 값 수정 후 서비스 재시작
nano /home/pi/smart_farm/config/soil_sensors.json
sudo systemctl restart smart-farm.service
```

"""

if 'BUG-1b 수정 상세' not in content:
    # "## 🔴 발견된 잠재 버그" 섹션 직전에 삽입
    target = "## 🔴 발견된 잠재 버그 (미수정)"
    if target in content:
        content = content.replace(target, BUG1B_SECTION.strip() + "\n\n---\n\n" + target)
        print("  ✅ BUG-1b 수정 상세 섹션 추가")
        changed = True
else:
    print("  ⚠️  BUG-1b 상세 섹션 이미 존재 → 건너뜀")

# ── 쿨다운 현황 표 추가 ───────────────────────────────────────────────────
COOLDOWN_TABLE = f"""
### ⚙️ 알림 쿨다운 설정 현황 ({today})
| 알림 종류 | 설정 파일 | 키 | 현재값 |
|---|---|---|---|
| 수위 경고 | `config/notifications.json` | `cooldown_seconds` | 3600초 (1시간) |
| 센서 오류 | `config/soil_sensors.json` | `irrigation.sensor_alert_cooldown` | 1800초 (30분) |

> 💡 하드웨어 미조립 상태 → `mode: manual`로 전환 시 자동 체크 자체가 중단됩니다.

---

"""

DOC_SECTION = "## 🗂️ 문서 구조"
if '알림 쿨다운 설정 현황' not in content and DOC_SECTION in content:
    content = content.replace(DOC_SECTION, COOLDOWN_TABLE.strip() + "\n\n---\n\n" + DOC_SECTION)
    print("  ✅ 알림 쿨다운 현황 표 추가")
    changed = True

# ── 자주 쓰는 명령어: sensor_alert_cooldown 확인 명령 추가 ─────────────────
CMD_ANCHOR = "# simulation_mode 확인"
NEW_CMD = """# 센서 오류 알림 쿨다운 확인
python3 -c "import json; cfg=json.load(open('/home/pi/smart_farm/config/soil_sensors.json')); print('sensor_alert_cooldown:', cfg.get('irrigation',{}).get('sensor_alert_cooldown','없음'), '초')"

"""
if 'sensor_alert_cooldown' not in content and CMD_ANCHOR in content:
    content = content.replace(CMD_ANCHOR, NEW_CMD + CMD_ANCHOR)
    print("  ✅ 자주 쓰는 명령어에 쿨다운 확인 명령 추가")
    changed = True

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

if changed:
    print("  ✅ STATUS.md 저장 완료 (변경사항 반영)")
else:
    print("  ℹ️  STATUS.md: 변경사항 없음 (이미 최신 상태)")
PYEOF

# ──────────────────────────────────────────────────
# STEP 6: 서비스 재시작 및 확인
# ──────────────────────────────────────────────────
echo ""
echo "🔄 [STEP 6] 서비스 재시작..."
sudo systemctl restart smart-farm.service
sleep 5

echo ""
echo "📋 서비스 시작 로그 (최근 30초):"
sudo journalctl -u smart-farm.service --since "35 sec ago" --no-pager \
  | grep -E "관수 설정|초기화|쿨다운|cooldown|sensor_alert|ERROR|Error|❌" \
  || echo "  (해당 키워드 로그 없음 — 정상 범위)"

echo ""
sudo systemctl is-active smart-farm.service \
  && echo "  ✅ 서비스 정상 실행 중" \
  || echo "  ❌ 서비스 이상 — sudo journalctl -u smart-farm.service -n 30 으로 확인 필요"

# ──────────────────────────────────────────────────
# 완료 요약
# ──────────────────────────────────────────────────
echo ""
echo "=================================================="
echo "  ✅ BUG-1b 패치 완료"
echo "=================================================="
echo ""
echo "  변경 요약:"
echo "  [auto_controller.py]"
echo "    ① __init__: self._last_sensor_alert_time = None 추가"
echo "    ② _send_sensor_alert(): 쿨다운 로직 추가 (기본 30분)"
echo "  [soil_sensors.json]"
echo "    ③ irrigation.sensor_alert_cooldown = 1800 추가"
echo "  [docs/STATUS.md]"
echo "    ④ BUG-1b 완료 기록 반영"
echo ""
echo "  동작 변화:"
echo "  이전: 센서 오류 시 ~6분마다 텔레그램 알림 (무한 반복)"
echo "  이후: 최초 1회 즉시 → 30분 후 재알림 (쿨다운 적용)"
echo ""
echo "  ─────────────────────────────────────────────────"
echo "  Git 커밋 (권장):"
echo "  ─────────────────────────────────────────────────"
echo "  cd /home/pi/smart_farm"
echo "  git add irrigation/auto_controller.py config/soil_sensors.json docs/STATUS.md"
echo '  git commit -m "fix(BUG-1b): 센서 오류 알림 쿨다운 추가 (30분)'
echo ''
echo '  [auto_controller.py]'
echo '  - __init__: _last_sensor_alert_time = None 추가'
echo '  - _send_sensor_alert(): sensor_alert_cooldown 기반 쿨다운 로직 추가'
echo '    - 기본 30분(1800초), soil_sensors.json에서 조정 가능'
echo '    - 쿨다운 중이면 텔레그램 생략 + 남은 시간 로그 출력'
echo '    - 전송 후 _last_sensor_alert_time 갱신'
echo ''
echo '  [soil_sensors.json]'
echo '  - irrigation.sensor_alert_cooldown: 1800 추가 (30분)'
echo ''
echo '  [docs/STATUS.md]'
echo '  - BUG-1b 완료 기록, 쿨다운 현황 표 추가"'
echo "  git push origin main"
echo "  ─────────────────────────────────────────────────"
echo ""
echo "  쿨다운 즉시 확인:"
echo "  python3 -c \"import json; cfg=json.load(open('/home/pi/smart_farm/config/soil_sensors.json')); print('sensor_alert_cooldown:', cfg.get('irrigation',{}).get('sensor_alert_cooldown'), '초')\""
echo "=================================================="
