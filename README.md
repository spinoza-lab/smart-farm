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

### ⏳ 개발 예정
- 센서 모니터링 (수위/토양습도)
- 웹 대시보드 (실시간 제어)
- 데이터 로깅 & 분석
- 알림 시스템

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
├── monitoring/            # 모니터링 (예정)
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

### ⏳ 3단계: 모니터링 & 로깅 (예정)
- [ ] 센서 실시간 모니터링
- [ ] 데이터 로깅 (CSV/SQLite)
- [ ] 알림 시스템

### ⏳ 4단계: 웹 UI (예정)
- [ ] Flask 웹 대시보드
- [ ] 실시간 차트
- [ ] 원격 제어

### ⏳ 5단계: 실전 통합 (부품 대기 중)
- [ ] 릴레이 모듈 설치 및 배선
- [ ] 체크밸브 설치
- [ ] 수위센서 연결
- [ ] 전체 시스템 통합 테스트

## 📅 타임라인

- **2026-02-10**: 프로젝트 시작, I2C 모듈 테스트, 1단계 완료
- **2026-02-11**: 2단계 완료 (관수 로직)

## 👤 개발자

- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스

MIT License
