# 🚀 설치 및 실행

## 1. 가상환경 설정

```bash
cd ~/smart_farm
python3 -m venv smart_farm_env
source smart_farm_env/bin/activate
```

## 2. 의존성 설치

```bash
pip install -r requirements.txt
```

필수 패키지:
- `adafruit-circuitpython-mcp230xx`
- `adafruit-circuitpython-ads1x15==2.2.24`
- `adafruit-circuitpython-ds1307`
- `Adafruit-Blinka>=8.0.0`
- `flask`
- `flask-socketio`
- `pyserial` (RS-485 통신)
- `minimalmodbus>=2.1.1` (Modbus RTU 드라이버)
- `requests` (텔레그램 API 통신)

## 3. I2C / UART 활성화

```bash
sudo raspi-config
# Interface Options > I2C > Enable
# Interface Options > Serial Port > Enable (RS-485용)
sudo reboot
```

## 4. 텔레그램 봇 설정

```bash
cat > config/notifications.json << 'JSONEOF'
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
```

텔레그램 봇 생성 방법:
1. `@BotFather` 에서 `/newbot` 명령으로 봇 생성
2. 발급된 API Token을 `token` 필드에 입력
3. 봇에게 `/start` 메시지 전송 후 아래 명령으로 Chat ID 확인:

```bash
curl -s "https://api.telegram.org/botYOUR_TOKEN/getUpdates" | python3 -m json.tool | grep '"id"'
```

## 5. 웹 서버 실행

```bash
cd ~/smart_farm
source smart_farm_env/bin/activate
nohup python3 web/app.py > logs/web.log 2>&1 &
```

접속 주소:
- 로컬: `http://localhost:5000`
- 네트워크: `http://192.168.0.111:5000` (라즈베리파이 IP)

## 6. systemd 서비스 (자동 시작)

```bash
# 서비스 상태 확인
sudo systemctl status smart-farm.service

# 수동 재시작
sudo systemctl restart smart-farm.service

# 부팅 자동 시작 설정
sudo systemctl enable smart-farm.service
```

## 7. VS Code Remote-SSH 개발 환경 (macOS)

맥북에서 VS Code로 라즈베리파이에 직접 접속하여 개발할 수 있습니다.

```bash
# 맥북에서 SSH 키 생성
ssh-keygen -t ed25519 -C "macbook-to-pi"

# 공개키 라즈베리파이에 등록
ssh-copy-id pi@192.168.0.111

# SSH config 설정
cat >> ~/.ssh/config << 'SSHEOF'
Host smart-farm-pi
    HostName 192.168.0.111
    User pi
    Port 22
    IdentityFile ~/.ssh/id_ed25519
SSHEOF
```

VS Code에서 `Remote - SSH` 익스텐션 설치 후 `smart-farm-pi` 로 접속,
`/home/pi/smart_farm` 폴더를 열면 파일 편집·터미널·Git 모두 VS Code에서 사용 가능합니다.
