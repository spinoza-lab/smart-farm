# 🌱 스마트 관수 시스템

Raspberry Pi 기반 자동 관수 시스템

## 📊 하드웨어

### 제어 모듈
- **Raspberry Pi 4** - 메인 컨트롤러
- **MCP23017 x2** (I2C 0x20, 0x21) - GPIO 확장 (32핀)
- **ADS1115** (I2C 0x48) - 4채널 ADC 센서
- **RTC DS1307** (I2C 0x68) - 실시간 시계

### 릴레이 & 밸브 (예정)
- 릴레이 모듈 6채널 x4개 (총 24개)
- 체크밸브 50A x3개
- 외부 전원 DC 5V 5A

## 🚀 기능

### ✅ 구현 완료
- **수동 관수**: 구역별 개별 제어
- **자동 스케줄**: 시간/요일별 자동 관수
- **순차 관수**: 여러 구역 순서대로 관수
- **긴급 배수**: 동파 방지용 배관 배수
- **커스텀 시나리오**: 구역별 맞춤 관수
- **센서 모니터링**: 실시간 수위 모니터링 (다중 샘플링 + 이상치 제거)
- **데이터 로깅**: CSV 형식 센서 데이터 저장 및 조회
- **경고 관리**: 수위/센서 오류 감지 및 다중 알림
- **웹 대시보드**: Flask 기반 실시간 모니터링 UI ✨

### ⏳ 개발 예정
- 자동 관수 연동 (센서 기반)
- 시스템 안정화 (systemd 서비스)
- 웹 대시보드 고도화 (통계 페이지)
- 모바일 앱 (선택)

## 📂 프로젝트 구조

```
smart_farm/
├── hardware/              # 하드웨어 제어 라이브러리
│   ├── gpio_expander.py   # MCP23017 GPIO 확장
│   ├── relay_controller.py # 릴레이 제어
│   ├── sensor_reader.py   # ADS1115 센서
│   └── rtc_manager.py     # RTC 시간 관리
│
├── irrigation/            # 관수 로직
│   ├── config_manager.py  # 설정 관리
│   ├── zone_manager.py    # 구역 관리
│   ├── scheduler.py       # 자동 스케줄러
│   ├── scenarios.py       # 관수 시나리오
│   └── config/            # 설정 파일
│
├── monitoring/            # 모니터링 & 로깅
│   ├── sensor_monitor.py  # 실시간 센서 모니터링 ✅
│   ├── data_logger.py     # CSV 데이터 로깅 ✅
│   └── alert_manager.py   # 경고 관리 시스템 ✅
│
├── web/                   # 웹 대시보드 ✨
│   ├── app.py             # Flask 서버
│   ├── templates/         # HTML 템플릿
│   │   └── index.html
│   └── static/            # CSS, JS
│       ├── css/style.css
│       └── js/dashboard.js
│
├── logs/                  # 로그 파일
│   ├── sensors_YYYY-MM-DD.csv  # 센서 데이터
│   └── alerts.log              # 경고 로그
│
└── tests/                 # 테스트 스크립트
```

## 🛠️ 설치

### 1. 가상환경 생성
```bash
cd ~/smart_farm
python3 -m venv smart_farm_env
source smart_farm_env/bin/activate
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

필요 라이브러리:
- `adafruit-circuitpython-mcp230xx`
- `adafruit-circuitpython-ads1x15==2.2.24`
- `adafruit-circuitpython-ds1307`
- `Adafruit-Blinka>=8.0.0`
- `flask` - 웹 서버
- `flask-socketio` - 실시간 통신

### 3. I2C 활성화
```bash
sudo raspi-config
# Interface Options > I2C > Enable
sudo reboot
```

## 💻 사용법

### 수동 관수
```python
from irrigation.zone_manager import ZoneManager

zone_mgr = ZoneManager()
zone_mgr.irrigate(zone_id=1, duration=600)  # 구역 1, 10분
```

### 자동 스케줄
```python
from irrigation.scheduler import IrrigationScheduler

scheduler = IrrigationScheduler()

# 매일 아침 06:00, 10분 관수
scheduler.add_schedule(
    zone_id=1,
    start_time="06:00",
    duration=600
)

# 스케줄러 시작
scheduler.start(blocking=True)
```

### 순차 관수
```python
from irrigation.scenarios import IrrigationScenarios

scenarios = IrrigationScenarios()

# 구역 1, 2, 3을 순서대로 관수
scenarios.sequential_irrigation(
    zone_ids=[1, 2, 3],
    duration_per_zone=600,
    interval=5
)
```

### 긴급 배수
```python
# 동파 방지용 배관 배수
scenarios.emergency_drain()
```

### 센서 모니터링
```python
from monitoring.sensor_monitor import SensorMonitor

monitor = SensorMonitor(config={
    'check_interval': 10,    # 10초마다 체크
    'sample_count': 10,      # 10개 샘플 수집
    'outlier_remove': 2,     # 상하위 각 2개 제거
    'min_water_level': 20.0,
    'max_water_level': 90.0
})

# 현재 상태 확인 (캐시에서)
status = monitor.get_current_status()
print(f"탱크 1: {status['tank1_level']}%")
print(f"탱크 2: {status['tank2_level']}%")

# 백그라운드 모니터링 시작
monitor.start(blocking=False)
```

### 데이터 로깅
```python
from monitoring.data_logger import DataLogger

logger = DataLogger(log_dir='/home/pi/smart_farm/logs')

# 센서 데이터 저장
logger.log_sensor_data(
    tank1_level=85.5,
    tank2_level=78.3,
    voltages=[2.15, 1.98, 0.65, 0.62]
)

# 데이터 조회
data = logger.get_data(
    start_date=datetime(2026, 2, 10),
    end_date=datetime(2026, 2, 12)
)

# 통계 계산
stats = logger.get_statistics(tank_num=1)
```

### 경고 관리
```python
from monitoring.alert_manager import AlertManager, AlertLevel

alert_mgr = AlertManager(
    tank1_min=20.0,
    tank1_max=90.0,
    cooldown_seconds=300  # 5분 쿨다운
)

# 수위 체크
alert_mgr.check_water_level(tank_num=1, level=15.0)

# 커스텀 콜백 추가
def email_alert(alert):
    if alert.level == AlertLevel.CRITICAL:
        send_email(alert.message)

alert_mgr.add_callback(email_alert)

# 경고 히스토리 조회
history = alert_mgr.get_alert_history(limit=10)
```

### 웹 대시보드 실행 ✨
```bash
cd ~/smart_farm/web
source ../smart_farm_env/bin/activate
python3 app.py
```

브라우저에서 접속:
- 로컬: `http://localhost:5000`
- 외부: `http://192.168.0.84:5000`

**웹 대시보드 기능:**
- 실시간 탱크 수위 표시 (게이지)
- 수위 추이 그래프 (Chart.js, 시:분:초)
- 경고 알림 실시간 표시
- 모니터링 시작/중지 제어
- 10초 간격 자동 갱신 (SocketIO)

### 통합 모니터링
```python
from monitoring.sensor_monitor import SensorMonitor
from monitoring.data_logger import DataLogger
from monitoring.alert_manager import AlertManager

# 초기화
monitor = SensorMonitor(config={'check_interval': 10})
logger = DataLogger()
alert_mgr = AlertManager(tank1_min=20.0, tank1_max=90.0)

# 통합 콜백
def integrated_callback(alert_type, message, data):
    # 데이터는 자동으로 저장됨 (periodic_data_sender)
    print(f"경고: {message}")

# AlertManager 콜백 등록
alert_mgr.add_callback(lambda alert: print(alert.message))

# SensorMonitor 경고 콜백 등록
monitor.add_alert_callback(integrated_callback)

# 모니터링 시작
monitor.start(blocking=False)
```

## 🧪 테스트

### 하드웨어 테스트
```bash
cd ~/smart_farm/hardware
python3 relay_controller.py
python3 sensor_reader.py
python3 rtc_manager.py
```

### 관수 로직 테스트
```bash
cd ~/smart_farm/irrigation
python3 zone_manager.py
python3 scheduler.py
python3 scenarios.py
```

### 모니터링 테스트
```bash
cd ~/smart_farm/monitoring
python3 sensor_monitor.py
python3 data_logger.py
python3 alert_manager.py
```

### 웹 대시보드 테스트
```bash
cd ~/smart_farm/web
source ../smart_farm_env/bin/activate
python3 app.py
```

## 📝 개발 진행

### ✅ 1단계: 하드웨어 제어 (완료 2026-02-10)
- [x] MCP23017 GPIO 확장
- [x] 릴레이 제어 (24개)
- [x] ADS1115 센서 읽기
- [x] RTC 시간 관리

### ✅ 2단계: 관수 로직 (완료 2026-02-11)
- [x] ConfigManager (설정/스케줄 관리)
- [x] ZoneManager (구역별 제어)
- [x] IrrigationScheduler (자동 스케줄러)
- [x] IrrigationScenarios (다양한 시나리오)

### ✅ 3단계: 모니터링 & 로깅 (완료 2026-02-13) ✨
- [x] **SensorMonitor** - 실시간 센서 모니터링
  - 다중 샘플링 (10회/체크)
  - 균등 샘플링 분포 (sample_interval = check_interval / sample_count)
  - 이상치 제거 (Trimmed Mean: 상하위 각 2개 제거)
  - 노이즈 억제 효과 (±0.8% → ±0.3%)
  - **측정값 캐시** (Threading Lock으로 동시성 제어)
  - 백그라운드 모니터링 스레드
  - 수위 경고 시스템
  - 히스토리 추적
  
- [x] **DataLogger** - 데이터 저장 및 관리
  - CSV 형식 센서 데이터 저장
  - 날짜별 자동 파일 분리 (logs/sensors_YYYY-MM-DD.csv)
  - 데이터 조회 및 필터링
  - 통계 계산 (평균, 최소, 최대)
  - 오래된 로그 자동 삭제
  - 스레드 안전 보장
  
- [x] **AlertManager** - 경고 관리 시스템
  - 3단계 경고 레벨 (INFO, WARNING, CRITICAL)
  - 수위 임계값 기반 경고 감지
  - 센서 오류 감지 (비정상 전압)
  - 통신 오류 감지
  - 다중 알림 채널 (콘솔, 로그 파일, 콜백)
  - 중복 알림 방지 (쿨다운 5분)
  - 경고 히스토리 및 통계
  
- [x] **웹 대시보드** - Flask 기반 실시간 모니터링 UI ✨
  - Flask + SocketIO 실시간 양방향 통신
  - 탱크 수위 게이지 (진행 바 + 색상 표시)
  - 수위 추이 그래프 (Chart.js, 시:분:초 단위)
  - 실시간 경고 알림 표시 (색상 구분)
  - 모니터링 시작/중지 제어
  - 10초 간격 자동 데이터 갱신
  - Bootstrap 5 반응형 디자인
  - **주요 해결 과제:**
    - 중복 샘플링 문제 해결 (캐시 도입)
    - 그래프 "Invalid Date" 오류 해결 (timestamp 형식 통일)
    - 브라우저 캐시 문제 해결 (버전 파라미터)

### ⏳ 4단계: 자동화 & 통합 (계획)
- [ ] 센서 기반 자동 관수
- [ ] ZoneManager와 SensorMonitor 통합
- [ ] 수위 부족/과다 시 자동 급수/배수

### ⏳ 5단계: 시스템 안정화 (계획)
- [ ] systemd 서비스 등록
- [ ] 자동 재시작 설정
- [ ] 로그 로테이션
- [ ] 오류 복구 메커니즘

### ⏳ 6단계: 웹 대시보드 고도화 (계획)
- [ ] 통계 페이지 (일/주/월 평균)
- [ ] 장기 수위 추이 그래프
- [ ] 데이터 다운로드 (CSV/Excel)
- [ ] 이메일/SMS 알림
- [ ] 모바일 반응형 개선

### ⏳ 7단계: 실전 통합 (부품 대기 중)
- [ ] 릴레이 모듈 설치 및 배선
- [ ] 체크밸브 설치
- [ ] 수위센서 연결
- [ ] 전체 시스템 통합 테스트

## 📊 Stage 3 기술 상세

### SensorMonitor 다중 샘플링 알고리즘
```
체크 간격: 10초
├─ 샘플 1 (0.0초)  ─┐
├─ 샘플 2 (1.0초)   │
├─ 샘플 3 (2.0초)   │
├─ ...              ├─ 10개 샘플 균등 분포
├─ 샘플 10 (9.0초) ─┘
└─ 이상치 제거 처리
   ├─ 정렬: [v1, v2, ..., v10]
   ├─ 상하위 제거: 각 2개씩
   └─ 평균 계산: (v3 + v4 + ... + v8) / 6
```

### 측정값 캐시 메커니즘 (v3)
```
_monitor_loop (백그라운드 스레드)
   ↓
샘플링 10회 수행 → 평균 계산
   ↓
캐시에 저장 (_last_data) ← Threading Lock
   ↓
히스토리에 추가
   ↓
10초 대기 후 반복

get_current_status() 호출 시
   ↓
캐시에서 반환 (샘플링 안 함!) ✅
```

### 웹 대시보드 데이터 흐름
```
periodic_data_sender (백그라운드 스레드, 10초 간격)
   ↓
sensor_monitor.get_current_status() → 캐시에서 읽기
   ↓
data_logger.log_sensor_data() → CSV 저장
   ↓
alert_manager.check_water_level() → 경고 체크
   ↓
socketio.emit('sensor_update') → 웹 브라우저로 전송
   ↓
dashboard.js → Chart 업데이트 + UI 갱신
```

### DataLogger CSV 형식
```csv
timestamp,tank1_level,tank2_level,ch0_voltage,ch1_voltage,ch2_voltage,ch3_voltage
2026-02-13 09:28:17,12.1,12.1,0.604,0.603,0.603,0.603
2026-02-13 09:28:27,12.2,12.0,0.605,0.604,0.602,0.603
2026-02-13 09:28:37,12.1,12.1,0.604,0.604,0.603,0.602
```

### AlertManager 경고 레벨
| 레벨 | 아이콘 | 설명 | 예시 |
|------|--------|------|------|
| INFO | ℹ️ | 정보성 메시지 | 시스템 시작, 정상 동작 |
| WARNING | ⚠️ | 주의 필요 | 수위 임계값 접근, 센서 오류 |
| CRITICAL | 🚨 | 즉시 조치 필요 | 수위 위험, 통신 오류 |

### 성능 메트릭
| 항목 | 사양 |
|------|------|
| 샘플링 주기 | 10초 (커스터마이징 가능) |
| 샘플 개수 | 10회/체크 |
| 측정 정확도 | ±0.3% (필터링 후) |
| ADC 해상도 | 16-bit (ADS1115) |
| I2C 속도 | 400 kbit/s |
| 경고 쿨다운 | 5분 (기본값) |
| 로그 파일 | 날짜별 자동 분리 |
| 웹 갱신 주기 | 10초 (SocketIO) |
| 그래프 시간 해상도 | 시:분:초 (HH:MM:SS) |

### 주요 기술적 해결 과제

#### 1. 중복 샘플링 문제
- **문제**: `/api/status`와 `periodic_data_sender`가 동시에 10회 샘플링 수행
- **증상**: 로그에 샘플링 숫자 뒤섞임, 2~3개 샘플링이 동시 실행
- **해결**:
  - `sensor_monitor.py`에 `_last_data` 캐시 추가
  - `get_current_status()`가 캐시 반환 (샘플링 안 함)
  - `/api/status`는 `get_history(limit=1)` 사용
  - Threading Lock으로 동시성 제어
- **결과**: 10초마다 정확히 1번만 샘플링 실행 ✅

#### 2. 그래프 "Invalid Date" 오류
- **문제**: Chart.js에서 x축 시간이 "Invalid Date"로 표시
- **원인**: `rtc.get_time_string()`이 시간만 반환 (`'09:28:17'`)
- **해결**:
  - `sensor_monitor.py`에서 `get_datetime_string('%Y-%m-%d %H:%M:%S')` 사용
  - JavaScript에서 `' '` → `'T'` 변환 (ISO 8601 형식)
  - 브라우저 캐시 해결: `dashboard.js?v=7`
- **결과**: 그래프 시간 정상 표시 (`09:28:17`) ✅

#### 3. 초 단위 표시
- **요구사항**: 10초 간격 측정이므로 시:분만 표시하면 구분 불가
- **해결**: `toLocaleTimeString`에 `second: '2-digit'` 추가
- **결과**: `오전 09:28:17` 또는 `09:28:17` (24시간 형식) ✅

## 📅 타임라인

- **2026-02-10**: 프로젝트 시작, I2C 모듈 테스트, 1단계 완료
- **2026-02-11**: 2단계 완료 (관수 로직)
- **2026-02-12**: 3단계 시작 (모니터링 시스템)
- **2026-02-13**: 3단계 완료 (웹 대시보드 포함) ✨

## 👤 개발자

- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스

MIT License