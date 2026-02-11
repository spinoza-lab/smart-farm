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

### ⏳ 개발 예정
- 데이터 로깅 (CSV/SQLite)
- 알림 시스템
- 웹 대시보드 (실시간 제어)

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
├── monitoring/            # 모니터링
│   ├── sensor_monitor.py  # 실시간 센서 모니터링 ✅
│   ├── data_logger.py     # 데이터 로깅 (예정)
│   └── alert_manager.py   # 알림 관리 (예정)
│
├── web/                   # 웹 UI (예정)
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

monitor = SensorMonitor(
    check_interval=10,      # 10초마다 체크
    sample_count=10,        # 10개 샘플 수집
    outlier_remove=2        # 상하위 각 2개 제거
)

# 현재 상태 확인
status = monitor.get_current_status()
print(f"탱크 1: {status['tank1_level']}%")
print(f"탱크 2: {status['tank2_level']}%")

# 백그라운드 모니터링 시작
monitor.start_monitoring(callback=my_callback)
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

### 센서 모니터링 테스트
```bash
cd ~/smart_farm/monitoring
python3 sensor_monitor.py
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

### 🔄 3단계: 모니터링 & 로깅 (진행 중 2026-02-11)
- [x] **SensorMonitor** - 실시간 센서 모니터링
  - 다중 샘플링 (10회/체크)
  - 균등 샘플링 분포 (sample_interval = check_interval / sample_count)
  - 이상치 제거 (Trimmed Mean: 상하위 각 2개 제거)
  - 노이즈 억제 효과 (±0.8% → ±0.3%)
  - 백그라운드 모니터링 스레드
  - 수위 경고 시스템
  - 히스토리 추적
- [ ] DataLogger (데이터 로깅 CSV/SQLite)
- [ ] AlertManager (알림 시스템)

### ⏳ 4단계: 웹 UI (예정)
- [ ] Flask 웹 대시보드
- [ ] 실시간 차트
- [ ] 원격 제어

### ⏳ 5단계: 실전 통합 (부품 대기 중)
- [ ] 릴레이 모듈 설치 및 배선
- [ ] 체크밸브 설치
- [ ] 수위센서 연결
- [ ] 전체 시스템 통합 테스트

## 📊 SensorMonitor 기술 상세

### 다중 샘플링 알고리즘
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

### 성능 특징
- **샘플링 주기**: 10초 (커스터마이징 가능)
- **샘플 개수**: 10회/체크
- **측정 정확도**: ±0.3% (필터링 후)
- **ADC 해상도**: 16-bit (ADS1115)
- **하드웨어 여유도**: 128 SPS → 1Hz 샘플링 충분

## 📅 타임라인

- **2026-02-10**: 프로젝트 시작, I2C 모듈 테스트, 1단계 완료
- **2026-02-11**: 2단계 완료 (관수 로직), 3단계 시작 (SensorMonitor 완료)

## 👤 개발자

- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스

MIT License
