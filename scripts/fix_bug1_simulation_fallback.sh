#!/bin/bash
# ============================================================
# fix_bug1_simulation_fallback.sh
# BUG-1: auto_controller.py 시뮬레이션 fallback 수정
#
# 변경 내용:
#   1. soil_sensors.json > irrigation 섹션에 simulation_mode 필드 추가
#   2. _load_config()에서 simulation_mode 로드
#   3. _auto_check_and_irrigate()에서 센서 없을 때 조건 분기
#      - simulation_mode: true  → 기존처럼 시뮬 데이터 사용 (개발/테스트용)
#      - simulation_mode: false → 관수 중단 + 로그 + 텔레그램 경고
#   4. 전체 센서 읽기 실패(valid=0) 시도 관수 중단 처리 추가
#   5. _send_sensor_alert() 헬퍼 메서드 추가
# ============================================================

BASE="/home/pi/smart_farm"
TARGET="$BASE/irrigation/auto_controller.py"
CONFIG="$BASE/config/soil_sensors.json"
BACKUP="${TARGET}.bak_$(date +%Y%m%d_%H%M%S)"

echo "========================================"
echo " BUG-1 수정 스크립트 시작"
echo "========================================"

# ── 사전 확인 ──────────────────────────────
if [ ! -f "$TARGET" ]; then
    echo "❌ 파일 없음: $TARGET"
    exit 1
fi
if [ ! -f "$CONFIG" ]; then
    echo "❌ 설정 파일 없음: $CONFIG"
    exit 1
fi

# ── 백업 ───────────────────────────────────
cp "$TARGET" "$BACKUP"
echo "✅ 백업 완료: $BACKUP"

# ── Python으로 auto_controller.py 수정 ────
python3 << 'PYEOF'
import re

TARGET = "/home/pi/smart_farm/irrigation/auto_controller.py"

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

# ────────────────────────────────────────────────────────────
# 1. _load_config() 에 simulation_mode 로드 추가
#    "self.irrigation_cfg = self.config.get('irrigation', {})" 바로 뒤에 삽입
# ────────────────────────────────────────────────────────────
OLD_LOAD = "            self.irrigation_cfg = self.config.get('irrigation', {})"
NEW_LOAD = (
    "            self.irrigation_cfg = self.config.get('irrigation', {})\n"
    "            # simulation_mode: True=시뮬 허용(개발용), False=센서 없으면 관수 중단\n"
    "            self.simulation_mode = self.irrigation_cfg.get('simulation_mode', False)"
)
assert OLD_LOAD in src, "ERROR: _load_config 교체 대상 문자열을 찾지 못했습니다."
src = src.replace(OLD_LOAD, NEW_LOAD, 1)

# 기본값 fallback에도 simulation_mode 추가
OLD_FALLBACK = (
    "            self.irrigation_cfg = {\n"
    "                'min_tank_level': 20.0,\n"
    "                'irrigation_duration': 300,\n"
    "                'zone_interval': 10,\n"
    "                'check_interval': 600,\n"
    "                'max_zones_simultaneous': 1\n"
    "            }"
)
NEW_FALLBACK = (
    "            self.irrigation_cfg = {\n"
    "                'min_tank_level': 20.0,\n"
    "                'irrigation_duration': 300,\n"
    "                'zone_interval': 10,\n"
    "                'check_interval': 600,\n"
    "                'max_zones_simultaneous': 1,\n"
    "                'simulation_mode': False\n"
    "            }\n"
    "            self.simulation_mode = False"
)
assert OLD_FALLBACK in src, "ERROR: fallback 설정 교체 대상 문자열을 찾지 못했습니다."
src = src.replace(OLD_FALLBACK, NEW_FALLBACK, 1)

# ────────────────────────────────────────────────────────────
# 2. _auto_check_and_irrigate() 의 센서 읽기 블록 교체
#    기존:
#        if self.sensor_manager:
#            sensor_data = self.sensor_manager.read_all_zones()
#        else:
#            sensor_data = self._simulate_sensor_data()
#
#    변경:
#        simulation_mode 분기 + 전체 센서 실패 시 중단
# ────────────────────────────────────────────────────────────
OLD_SENSOR_BLOCK = (
    "        if self.sensor_manager:\n"
    "            sensor_data = self.sensor_manager.read_all_zones()\n"
    "        else:\n"
    "            sensor_data = self._simulate_sensor_data()\n"
    "\n"
    "        self.last_sensor_data = sensor_data"
)
NEW_SENSOR_BLOCK = (
    "        # ── 센서 데이터 수집 ──────────────────────────────────\n"
    "        if self.sensor_manager:\n"
    "            sensor_data = self.sensor_manager.read_all_zones()\n"
    "\n"
    "            # 전체 센서 읽기 실패 시 관수 중단\n"
    "            valid_count = sum(1 for d in sensor_data.values() if d.get('valid'))\n"
    "            if valid_count == 0:\n"
    "                msg = '❌ 모든 토양센서 읽기 실패 - 자동관수를 중단합니다'\n"
    "                print(msg)\n"
    "                self._log(msg)\n"
    "                self._send_sensor_alert(msg)\n"
    "                return\n"
    "\n"
    "        elif self.simulation_mode:\n"
    "            # simulation_mode=true 일 때만 시뮬레이션 허용 (개발·테스트 전용)\n"
    "            print('⚠️  [시뮬레이션 모드] 가상 센서 데이터를 사용합니다')\n"
    "            self._log('[시뮬레이션 모드] 가상 센서 데이터 사용')\n"
    "            sensor_data = self._simulate_sensor_data()\n"
    "\n"
    "        else:\n"
    "            # 센서 매니저 없음 + simulation_mode=false → 관수 완전 중단\n"
    "            msg = ('❌ 토양센서 매니저가 초기화되지 않았습니다.\\n'\n"
    "                   'soil_sensors.json > irrigation > simulation_mode 를 확인하세요.\\n'\n"
    "                   '자동관수를 중단합니다.')\n"
    "            print(msg)\n"
    "            self._log('토양센서 매니저 없음 - 자동관수 중단')\n"
    "            self._send_sensor_alert('⚠️ 토양센서 매니저 없음 - 자동관수 중단')\n"
    "            return\n"
    "\n"
    "        self.last_sensor_data = sensor_data"
)
assert OLD_SENSOR_BLOCK in src, "ERROR: 센서 읽기 블록 교체 대상 문자열을 찾지 못했습니다."
src = src.replace(OLD_SENSOR_BLOCK, NEW_SENSOR_BLOCK, 1)

# ────────────────────────────────────────────────────────────
# 3. _send_sensor_alert() 헬퍼 메서드 추가
#    _simulate_sensor_data() 정의 바로 앞에 삽입
# ────────────────────────────────────────────────────────────
OLD_SIMULATE_DEF = "    def _simulate_sensor_data(self):"
NEW_SIMULATE_DEF = (
    "    def _send_sensor_alert(self, message):\n"
    "        \"\"\"토양센서 오류를 텔레그램으로 알림\"\"\"\n"
    "        try:\n"
    "            import sys as _sys\n"
    "            _main = (_sys.modules.get('__main__') or\n"
    "                     _sys.modules.get('web.app') or\n"
    "                     _sys.modules.get('app'))\n"
    "            _tn = getattr(_main, 'telegram_notifier', None)\n"
    "            if _tn:\n"
    "                _tn.send_message(f'🚨 [자동관수 오류]\\n{message}')\n"
    "        except Exception as e:\n"
    "            print(f'⚠️  텔레그램 알림 실패: {e}')\n"
    "\n"
    "    def _simulate_sensor_data(self):"
)
assert OLD_SIMULATE_DEF in src, "ERROR: _simulate_sensor_data 삽입 위치를 찾지 못했습니다."
src = src.replace(OLD_SIMULATE_DEF, NEW_SIMULATE_DEF, 1)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)

print("✅ auto_controller.py 수정 완료")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ Python 수정 실패 - 백업으로 복구합니다"
    cp "$BACKUP" "$TARGET"
    exit 1
fi

# ── soil_sensors.json에 simulation_mode 필드 추가 ──────────
echo ""
echo "── soil_sensors.json 업데이트 중..."
python3 << 'PYEOF'
import json, os

CONFIG = "/home/pi/smart_farm/config/soil_sensors.json"
BACKUP_CFG = CONFIG + ".bak_sim"

with open(CONFIG, "r", encoding="utf-8") as f:
    cfg = json.load(f)

# 백업
import shutil
shutil.copy(CONFIG, BACKUP_CFG)

# irrigation 섹션이 없으면 생성
if "irrigation" not in cfg:
    cfg["irrigation"] = {}

# simulation_mode 가 이미 있으면 덮어쓰지 않음
if "simulation_mode" not in cfg["irrigation"]:
    cfg["irrigation"]["simulation_mode"] = False
    print("✅ simulation_mode: false 추가됨")
else:
    print(f"ℹ️  simulation_mode 이미 존재: {cfg['irrigation']['simulation_mode']} (변경 없음)")

with open(CONFIG, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)

print(f"✅ soil_sensors.json 저장 완료")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ soil_sensors.json 수정 실패"
    exit 1
fi

# ── 결과 검증 ───────────────────────────────
echo ""
echo "── 수정 결과 검증..."
echo ""

echo "[1] simulation_mode 로드 확인:"
grep -n "simulation_mode" "$TARGET"

echo ""
echo "[2] 센서 없음 분기 확인:"
grep -n "센서 매니저 없음\|시뮬레이션 모드\|valid_count\|_send_sensor_alert" "$TARGET"

echo ""
echo "[3] soil_sensors.json irrigation 섹션:"
python3 -c "
import json
with open('$CONFIG') as f:
    cfg = json.load(f)
irr = cfg.get('irrigation', {})
print(json.dumps({k: irr[k] for k in ['simulation_mode', 'check_interval', 'min_tank_level'] if k in irr}, indent=2))
"

echo ""
echo "========================================"
echo " ✅ BUG-1 수정 완료"
echo ""
echo " 변경 요약:"
echo "   • simulation_mode=false → 센서 없으면 관수 중단 + 텔레그램 경고"
echo "   • simulation_mode=true  → 시뮬레이션 허용 (개발/테스트 전용)"
echo "   • 전체 센서 읽기 실패(valid=0) → 관수 중단 + 텔레그램 경고"
echo "   • _send_sensor_alert() 헬퍼 메서드 추가"
echo ""
echo " 테스트:"
echo "   sudo systemctl restart smart-farm.service"
echo "   sudo journalctl -u smart-farm.service --since '1 min ago' --no-pager"
echo ""
echo " 시뮬레이션 모드 활성화 (테스트 시):"
echo "   soil_sensors.json > irrigation > simulation_mode: true"
echo "========================================"
