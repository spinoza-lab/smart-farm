#!/usr/bin/env bash
# BUG-18: SensorMonitor 쿨다운을 notifications.json으로 단일화
# 변경 파일: config/notifications.json, web/app.py

set -e
cd ~/smart_farm

echo "=== BUG-18: 쿨다운 단일화 패치 시작 ==="

# ──────────────────────────────────────────────
# STEP 1: config/notifications.json에 sensor_monitor_cooldown 추가
# (이미 추가된 경우 스킵)
# ──────────────────────────────────────────────
python3 << 'PYEOF'
import json, sys

path = 'config/notifications.json'
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"❌ {path} 파일 없음")
    sys.exit(1)

if 'sensor_monitor_cooldown' in data:
    print(f"ℹ️  sensor_monitor_cooldown 이미 존재: {data['sensor_monitor_cooldown']}s (변경 없음)")
else:
    data['sensor_monitor_cooldown'] = 300
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ (1) notifications.json: sensor_monitor_cooldown=300 추가")

print(f"    cooldown_seconds (AlertManager)     : {data.get('cooldown_seconds', '없음')}s")
print(f"    sensor_monitor_cooldown (SensorMon) : {data.get('sensor_monitor_cooldown', '없음')}s")
PYEOF

# ──────────────────────────────────────────────
# STEP 2: web/app.py 수정 (실제 코드 기준)
# ──────────────────────────────────────────────
python3 << 'PYEOF'
path = 'web/app.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

OLD = """        g.sensor_monitor = SensorMonitor(config={
            'check_interval': 10, 'sample_count': 10,
            'outlier_remove': 2, 'min_water_level': 20.0, 'max_water_level': 90.0
        })
        g.data_logger = DataLogger(log_dir=str(_BASE_DIR / 'logs'))
        try:
            with open(str(_BASE_DIR / 'config/notifications.json')) as f:
                _nc = json.load(f)
            _thr = _nc.get('thresholds', {})
            _t1_min = float(_thr.get('tank1_min', 20.0)); _t1_max = float(_thr.get('tank1_max', 90.0))
            _t2_min = float(_thr.get('tank2_min', 20.0)); _t2_max = float(_thr.get('tank2_max', 90.0))
            _cooldown = int(_nc.get('cooldown_seconds', 300))
        except Exception as e:
            print(f'[Init] thresholds 로드 실패: {e}'); _t1_min=_t2_min=20.0; _t1_max=_t2_max=90.0; _cooldown=300"""

NEW = """        g.data_logger = DataLogger(log_dir=str(_BASE_DIR / 'logs'))
        try:
            with open(str(_BASE_DIR / 'config/notifications.json')) as f:
                _nc = json.load(f)
            _thr = _nc.get('thresholds', {})
            _t1_min = float(_thr.get('tank1_min', 20.0)); _t1_max = float(_thr.get('tank1_max', 90.0))
            _t2_min = float(_thr.get('tank2_min', 20.0)); _t2_max = float(_thr.get('tank2_max', 90.0))
            _cooldown = int(_nc.get('cooldown_seconds', 300))
            _cooldown_sm = int(_nc.get('sensor_monitor_cooldown', 300))  # BUG-18: SM 쿨다운
        except Exception as e:
            print(f'[Init] thresholds 로드 실패: {e}')
            _t1_min=_t2_min=20.0; _t1_max=_t2_max=90.0; _cooldown=300; _cooldown_sm=300
        g.sensor_monitor = SensorMonitor(config={
            'check_interval': 10, 'sample_count': 10,
            'outlier_remove': 2, 'min_water_level': 20.0, 'max_water_level': 90.0,
            'alert_cooldown': _cooldown_sm  # BUG-18: notifications.json에서 읽기
        })"""

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ (2) web/app.py: SensorMonitor에 alert_cooldown 주입, 로딩 순서 수정")
else:
    print("❌ 패턴 미발견 - 아래 실제 코드를 확인하세요:")
    # 디버깅용: 해당 영역 출력
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if 'SensorMonitor(config' in line:
            print(f"  실제 코드 ({i-1}~{i+12}번 라인):")
            for j in range(max(0, i-2), min(len(lines), i+13)):
                print(f"  {j+1:4d}: {repr(lines[j])}")
            break
PYEOF

# ──────────────────────────────────────────────
# STEP 3: 문법 검사
# ──────────────────────────────────────────────
python3 -m py_compile web/app.py && echo "✅ (3) app.py 문법 OK" || echo "❌ app.py 문법 오류"

# ──────────────────────────────────────────────
# STEP 4: git commit (notifications.json은 gitignore라 제외)
# ──────────────────────────────────────────────
git add web/app.py
git commit -m "fix(BUG-18): SensorMonitor 쿨다운 notifications.json으로 단일화

- web/app.py: notifications.json 로딩을 SensorMonitor 생성 앞으로 이동
- SensorMonitor config에 alert_cooldown 전달 (BUG-13 완전 수정)
- notifications.json에 sensor_monitor_cooldown: 300 추가 (gitignore 제외)

쿨다운 현황:
  AlertManager  : notifications.json cooldown_seconds (3600s)
  SensorMonitor : notifications.json sensor_monitor_cooldown (300s)
  AutoController: soil_sensors.json sensor_alert_cooldown (1800s, 유지)"

echo ""
echo "=== ✅ BUG-18 패치 완료 ==="
echo "  서비스 재시작: sudo systemctl restart smart-farm.service"
echo "  로그 확인    : sudo journalctl -u smart-farm.service -n 20 --no-pager"
