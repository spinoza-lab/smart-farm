# 🛠️ 문제 해결

## I²C 장치 인식 안 됨

```bash
i2cdetect -y 1
# 0x20, 0x21, 0x48, 0x68 확인
```

## 서비스 상태 확인

```bash
sudo systemctl status smart-farm.service
sudo journalctl -u smart-farm.service -n 50 --no-pager
```

## 웹 서버 수동 실행

```bash
cd ~/smart_farm
source smart_farm_env/bin/activate
nohup python3 web/app.py > logs/web.log 2>&1 &
curl http://localhost:5000/api/irrigation/status
```

## RS-485 토양 센서 미응답

```bash
ls /dev/ttyUSB* /dev/ttyAMA*
python3 -c "import minimalmodbus; print(minimalmodbus.__version__)"
# 2.1.1 이상 확인
```

## RS-485 센서 Modbus 주소 설정

```bash
# 대화형 주소 설정
python3 tools/set_sensor_address.py

# 버스 스캔
python3 tools/set_sensor_address.py --scan

# 주소 직접 변경 (예: 주소1 → 구역3)
python3 tools/set_sensor_address.py --set 1 3
```

## 스케줄이 실행되지 않음

```bash
# 모드 확인 (auto여야 함)
curl -s http://localhost:5000/api/irrigation/status | python3 -m json.tool | grep mode

# 스케줄러 실행 여부
curl -s http://localhost:5000/api/irrigation/status | python3 -m json.tool | grep is_running

# 다음 스케줄 확인
curl -s http://localhost:5000/api/schedules/next | python3 -m json.tool

# 스케줄러 로그 확인
grep -a "스케줄러\|큐 추가\|관수 실행" /home/pi/smart_farm/logs/web.log | tail -20
```

## 텔레그램 알림이 오지 않음

```bash
# 직접 전송 테스트
python3 -c "
import requests
r = requests.post(
  'https://api.telegram.org/botYOUR_TOKEN/sendMessage',
  json={'chat_id': 'YOUR_CHAT_ID', 'text': '테스트'}
)
print(r.status_code, r.json())
"

# 초기화 로그 확인
grep -a "텔레그램\|TelegramNotifier" /home/pi/smart_farm/logs/web.log

# notifications.json 확인
cat /home/pi/smart_farm/config/notifications.json
```

## 알림 설정 저장 후 토큰이 사라지는 경우 (v3.5 이전)

```bash
# notifications.json 직접 확인
cat /home/pi/smart_farm/config/notifications.json

# 파일이 비어있거나 token이 없으면 직접 복원
cat > /home/pi/smart_farm/config/notifications.json << 'JSONEOF'
{
  "telegram": {
    "enabled": true,
    "token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  },
  "alerts": {
    "server_start": true,
    "irrigation_start": true,
    "irrigation_done": true,
    "water_level_low": true,
    "water_level_high": true,
    "sensor_error": true
  },
  "thresholds": {
    "tank1_min": 20,
    "tank1_max": 90,
    "tank2_min": 20,
    "tank2_max": 90
  },
  "cooldown_seconds": 300
}
JSONEOF
# 서비스 재시작
sudo systemctl restart smart-farm.service
```

## 관수 시간 단위 문제

```
웹 UI 입력: 분 단위
API 저장값: 초 단위 (×60 자동 변환)

예) 설정 페이지에서 5분 입력 → API에 300초로 저장
    스케줄 추가 시 10분 입력 → duration=600으로 저장
```

## minimalmodbus precalculate_read_size 오류

```bash
grep -n "precalculate_read_size" hardware/modbus_soil_sensor.py
# SoilSensorManager._init_sensors() 공유 시리얼 블록에 4개 속성 설정 확인
```

## 분석 페이지 그래프에 데이터가 표시되지 않음 (v0.6.4 이전)

**증상**: 날짜 범위 선택 후 그래프가 비거나, 30일 이상 기간 선택 시 일부 데이터만 표시.

**원인**: `analytics_bp.py`의 limit 고정값(2000행)이 긴 기간의 데이터를 포괄하지 못함.

**해결**: v0.6.4에서 기간 기반 동적 limit 계산으로 수정됨. 최신 버전으로 업데이트하거나
`analytics_bp.py`의 query_* 함수 호출부에서 limit 파라미터를 제거하면 DB 전체 기간 쿼리됨.

## 분석 페이지 트리거 도넛 차트가 비어 있음

**증상**: 관수 분석 탭의 트리거 유형 비율 차트가 표시되지 않거나 일부만 표시.

**원인**: 트리거 값이 DB에 한글(`수동`, `스케줄`)로 저장되어 있으나
기존 JS 코드가 영문(`manual`, `schedule`)만 처리함.

**해결**: v0.6.4의 TRIGGER_MAP 업데이트로 수정됨. 아래 명령으로 실제 DB 값 확인:

```bash
curl -s http://localhost:5000/api/analytics/trigger-stats | python3 -m json.tool
```

## 환경 차트에 시뮬레이션 데이터가 실제 데이터처럼 표시됨

**증상**: SHT30/WH65LP 하드웨어 미연결 상태에서 환경 차트에 규칙적인 시뮬레이션 데이터 표시.

**해결**: v0.6.4에서 시뮬레이션 뱃지 및 경고 배너 추가. 하드웨어 수령 후:

```bash
python3 -c "
import json
for f in ['config/air_sensors.json', 'config/weather_station.json']:
    d = json.load(open(f))
    d['simulation_mode'] = False
    json.dump(d, open(f,'w'), indent=4, ensure_ascii=False)
    print(f'✅ {f} → simulation_mode: false')
"
sudo systemctl restart smart-farm.service
```

## 웹 UI 네비게이션 버튼이 모바일에서 겹치거나 줄바꿈됨

**증상**: 스마트폰에서 접속 시 상단 네비게이션 버튼들이 겹치거나 여러 줄로 표시됨.

**해결**: v0.6.8에서 모바일 햄버거 메뉴로 교체됨. 최신 버전으로 업데이트 후 서비스 재시작:

```bash
cd ~/smart_farm
git pull origin main
sudo systemctl restart smart-farm.service
```

## PC 화면에서 UI가 좌우로 너무 넓게 표시됨

**증상**: 넓은 모니터에서 카드/차트가 전체 너비로 펼쳐져 가독성이 낮음.

**해결**: v0.6.8에서 `container-xxl` 적용으로 최대 1400px 중앙정렬. 최신 버전 업데이트 후
캐시 강제 새로 고침 (Ctrl+Shift+R):

```bash
sudo systemctl restart smart-farm.service
# 브라우저 강제 새로고침: Ctrl+Shift+R (Windows/Linux) 또는 Cmd+Shift+R (Mac)
```

## container 레이아웃 현황 확인

```bash
grep -n "container-fluid\|container-xxl" \
  /home/pi/smart_farm/web/templates/index.html | head -10
# 예상 출력:
# 242:    <div class="container-xxl">
# 284:    <div class="container-xxl mt-4">
```

## UART3/4 경로가 없음 (/dev/ttyAMA2, /dev/ttyAMA3)

**증상**: SHT30 또는 WH65LP 연결 시 `/dev/ttyAMA2` 또는 `/dev/ttyAMA3` 없음 오류.

**해결**: `/boot/firmware/config.txt`에 UART 오버레이 추가 후 재부팅:

```bash
sudo nano /boot/firmware/config.txt
# 파일 끝에 추가:
# dtoverlay=uart3   # GPIO4(TX), GPIO5(RX) → MAX485 #2 대기 온습도
# dtoverlay=uart4   # GPIO8(TX), GPIO9(RX) → MAX485 #3 기상 스테이션

sudo reboot

# 재부팅 후 확인
ls -la /dev/ttyAMA*
# /dev/ttyAMA0, /dev/ttyAMA2, /dev/ttyAMA3 모두 표시되어야 함
```
