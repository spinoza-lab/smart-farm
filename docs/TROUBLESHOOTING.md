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
  }
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
