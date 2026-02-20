# 🌱 스마트 관수 시스템 (Smart Irrigation System)

라즈베리파이 기반 자동 관수 및 수위 모니터링 시스템

## 📌 주요 기능

- 🔄 **실시간 센서 모니터링** - 10초 주기 자동 샘플링
- 💧 **수위 관리** - 탱크1(물), 탱크2(양액) 실시간 모니터링
- ⚙️ **정밀 캘리브레이션** - 소수점 3자리 정밀도 (0.001V 단위)
- 📊 **실시간 대시보드** - WebSocket 기반 실시간 업데이트
- 🚨 **알림 시스템** - 수위 부족/과다 자동 경고
- 📈 **데이터 로깅** - CSV 형식 자동 저장
- 🎯 **자동 관수 제어** - 시간/수위 기반 자동화

## 🛠 하드웨어 구성

### Raspberry Pi 기반 시스템

- **Raspberry Pi 4** - 메인 컨트롤러
- **MCP23017 x2** (I2C 0x20, 0x21) - 32개 GPIO 확장
- **ADS1115** (I2C 0x48) - 4채널 16-bit ADC (센서 읽기)
- **RTC DS1307** (I2C 0x68) - 실시간 시계

### 전원 및 릴레이 시스템

- 릴레이 모듈 6개 x 4채널 (총 24채널)
- 50A 릴레이 x3개
- DC 5V 5A 전원 공급

## 🏗 프로젝트 구조

```
smart_farm/
├── hardware/              # 하드웨어 제어
│   ├── gpio_expander.py   # MCP23017 GPIO 확장
│   ├── relay_controller.py # 릴레이 제어
│   ├── sensor_reader.py   # ADS1115 센서 읽기
│   └── rtc_manager.py     # RTC 시간 관리
│
├── irrigation/            # 관수 제어
│   ├── config_manager.py  # 설정 관리
│   ├── zone_manager.py    # 구역별 관수
│   ├── scheduler.py       # 스케줄 관리
│   ├── scenarios.py       # 시나리오 실행
│   └── config/            # 설정 파일
│
├── monitoring/            # 모니터링 & 로깅
│   ├── sensor_monitor.py  # 센서 모니터링 (핵심)
│   ├── data_logger.py     # CSV 데이터 저장
│   └── alert_manager.py   # 알림 관리
│
├── web/                   # 웹 인터페이스
│   ├── app.py             # Flask 서버
│   ├── templates/         # HTML 템플릿
│   │   ├── index.html     # 대시보드
│   │   └── settings.html  # 설정 페이지
│   └── static/            # CSS, JS
│       ├── css/style.css
│       ├── js/dashboard.js
│       └── js/settings.js
│
├── logs/                  # 로그 파일
│   ├── sensors_YYYY-MM-DD.csv  # 센서 데이터
│   └── alerts.log              # 알림 로그
│
└── config/                # 설정 파일
    └── sensor_calibration.json  # 센서 캘리브레이션
```

## 🚀 설치 및 실행

### 1. 가상환경 설정

```bash
cd ~/smart_farm
python3 -m venv smart_farm_env
source smart_farm_env/bin/activate
```

### 2. 의존성 설치

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

### 3. I2C 활성화

```bash
sudo raspi-config
# Interface Options > I2C > Enable
sudo reboot
```

### 4. 웹 서버 실행

```bash
cd ~/smart_farm/web
source ../smart_farm_env/bin/activate
python3 app.py
```

**접속 주소:**
- 로컬: `http://localhost:5000`
- 네트워크: `http://192.168.0.84:5000` (라즈베리파이 IP)

## 📊 센서 모니터링 시스템

### 핵심 기능

#### 1. 자동 샘플링
- **주기**: 10초마다 자동 실행
- **샘플링**: 10회 측정 (1초 간격)
- **이상치 제거**: 상하위 각 2개 제거 (Trimmed Mean)
- **정밀도**: 소수점 3자리 (0.001V)

#### 2. 실시간 데이터 전송
- WebSocket을 통한 실시간 업데이트
- 10초마다 대시보드 자동 갱신
- 지연 없는 즉시 반영

#### 3. 캘리브레이션 시스템
- **입력 정밀도**: 0.001V 단위
- **3중 검증**: HTML + JavaScript + 서버
- **자동 반올림**: 소수점 3자리로 자동 정리
- **즉시 적용**: 저장 즉시 모니터링에 반영 (재시작 불필요)

### 샘플링 프로세스

```
타이밍: 10초 주기
  1초째 (0.0초) → 샘플 1
  2초째 (1.0초) → 샘플 2
  3초째 (2.0초) → 샘플 3
  ...
  10초째 (9.0초) → 샘플 10
  ↓
필터링: [v1, v2, ..., v10]
  상하위 제거: 2개씩
  평균 계산: (v3 + v4 + ... + v8) / 6
```

### 데이터 흐름

```
periodic_data_sender (백그라운드 스레드, 10초 주기)
  ↓
_collect_sensor_data() (직접 샘플링)
  ↓
data_logger.log_sensor_data() (CSV 저장)
  ↓
alert_manager.check_water_level() (알림 체크)
  ↓
socketio.emit('sensor_update') (웹으로 전송)
  ↓
dashboard.js가 Chart 업데이트 + UI 갱신
```

## 📈 데이터 로깅

### CSV 형식

```csv
timestamp,tank1_level,tank2_level,ch0_voltage,ch1_voltage,ch2_voltage,ch3_voltage
2026-02-20 13:08:30,72.2,78.4,0.589,0.589,0.589,0.588
2026-02-20 13:08:40,72.2,78.4,0.589,0.589,0.589,0.588
2026-02-20 13:08:50,72.3,78.5,0.589,0.590,0.590,0.589
```

## 🚨 알림 시스템

### 알림 레벨

| 레벨 | 조건 | 용도 | 예시 |
|------|------|------|------|
| INFO | 정상 상태 | 일반 로그 | 시스템 시작, 설정 변경 |
| WARNING | 경고 상태 | 주의 필요 | 수위 20% 근접, 센서 오류 |
| CRITICAL | 위험 상태 | 즉시 조치 | 수위 20% 미만, 시스템 오류 |

## ⚙️ 캘리브레이션

### 설정 페이지 기능

1. **센서 타입 선택**: 전압/수위 모드
2. **탱크별 설정**:
   - Empty Value: 공탱크 전압 (0.001V 단위)
   - Full Value: 만수 전압 (0.001V 단위)
3. **실시간 센서 값**: 현재 전압 및 수위 표시 (5초 자동 갱신)
4. **입력 검증**:
   - 최대값: 5.000V
   - 소수점: 3자리까지만
   - 자동 반올림: 입력값 자동 정리

### 캘리브레이션 적용

- ✅ **즉시 반영**: 저장 즉시 모니터링에 적용
- ✅ **서버 재시작 불필요**: 실시간 reload
- ✅ **정밀도 유지**: 계산 시 전체 정밀도 사용
- ✅ **3중 검증**: HTML pattern + JavaScript + 서버 round()

## 🔧 주요 해결 과제

### 2026-02-20 업데이트

#### 1. 캘리브레이션 즉시 반영 ✅
- **문제**: 캘리브레이션 변경 후 서버 재시작 필요
- **해결**: `load_calibration()` 메서드 추가, 저장 즉시 reload

#### 2. 중복 샘플링 제거 ✅
- **문제**: 설정 페이지 접속 시마다 샘플링 재시작
- **해결**: API 엔드포인트를 캐시 사용으로 변경

#### 3. 정밀도 개선 ✅
- **문제**: 소수점 1자리 입력으로 정밀도 부족
- **해결**: 0.001V 단위 입력, 소수점 3자리 처리

#### 4. 입력 검증 강화 ✅
- **문제**: 잘못된 값 입력 시 오류 발생 가능
- **해결**: 3중 검증 (HTML + JS + 서버) 및 자동 반올림

#### 5. 실시간 업데이트 ✅
- **문제**: 대시보드 수동 새로고침 필요
- **해결**: WebSocket (SocketIO) 기반 자동 업데이트

## 📊 시스템 성능

| 항목 | 수치 |
|------|------|
| 샘플링 주기 | 10초 (자동) |
| 샘플 개수 | 10회/주기 |
| 측정 정밀도 | 0.3% (전압 기준) |
| ADC 해상도 | 16-bit (ADS1115) |
| I2C 속도 | 400 kbit/s |
| 알림 쿨다운 | 5분 (중복 방지) |
| 데이터 저장 | CSV (일별 파일) |
| 업데이트 주기 | 10초 (SocketIO) |
| 시간 표시 | 24시간제 (HH:MM:SS) |

## 🗓 개발 이력

- **2026-02-10**: 하드웨어 설정, I2C 통신 구현, Stage 1 완료
- **2026-02-11**: 관수 시스템 Stage 2 완료 (구역 관리)
- **2026-02-12**: 모니터링 시스템 Stage 3 완료 (센서)
- **2026-02-13**: 웹 인터페이스 Stage 3 완료 (대시보드)
- **2026-02-20**: 
  - ✅ 캘리브레이션 시스템 완성 (소수점 3자리 정밀도)
  - ✅ 실시간 모니터링 안정화 (중복 샘플링 제거)
  - ✅ 입력 검증 3중 시스템 구현
  - ✅ WebSocket 기반 실시간 업데이트

## 📝 다음 단계 (TODO)

- [ ] 데이터 시각화 그래프 (시간별 수위 추이)
- [ ] 자동 관수 제어 연동
- [ ] systemd 서비스 등록 (자동 시작)
- [ ] 이메일/SMS 알림
- [ ] 데이터베이스 연동 (SQLite)
- [ ] 모바일 최적화

## 👤 개발자

- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스

MIT License
