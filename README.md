# 🌱 스마트 관수 시스템 (Smart Irrigation System)

> **Repository**: [spinoza-lab/smart-farm](https://github.com/spinoza-lab/smart-farm)  
> **최종 업데이트**: 2026-02-23  
> **버전**: v2.7

라즈베리파이 기반 자동 관수 및 수위 모니터링 시스템

## 📌 주요 기능

- 🔄 **실시간 센서 모니터링** - 10초 주기 자동 샘플링
- 💧 **수위 관리** - 탱크1(물), 탱크2(양액) 실시간 모니터링
- ⚙️ **정밀 캘리브레이션** - 소수점 3자리 정밀도 (0.001V 단위)
- 📊 **실시간 대시보드** - WebSocket 기반 실시간 업데이트
- 🚨 **알림 시스템** - 수위 부족/과다 자동 경고
- 📈 **데이터 로깅** - CSV 형식 자동 저장 (탱크 수위 + 관수 이력)
- 🌱 **12구역 자동 관수** - 토양 수분 센서 기반 자동/수동/스케줄 모드
- 🎛️ **관수 제어 웹 UI** - 구역별 게이지, 수동 관수, 임계값 설정
- 📥 **CSV 데이터 다운로드** - 탱크 수위·관수 이력 기간별 내보내기
- 🔧 **systemd 자동 시작** - 부팅 시 자동 실행 및 로그 관리
- 📊 **데이터 분석 페이지** - 탱크 수위 트렌드, 관수 효율, 구역별 통계, 줌/팬 차트

## 🛠 하드웨어 구성

### Raspberry Pi 기반 시스템

- **Raspberry Pi 4** - 메인 컨트롤러
- **MCP23017 x2** (I2C 0x20, 0x21) - 32개 GPIO 확장
- **ADS1115** (I2C 0x48) - 4채널 16-bit ADC (센서 읽기, 전압 모드 0~5V)
- **RTC DS1307** (I2C 0x68) - 실시간 시계
- **RS-485 토양 수분 센서 x12** (Modbus RTU) - 수분·온도·EC 측정

### 전원 및 릴레이 시스템

- 릴레이 모듈 6개 x 4채널 (총 24채널)
- 50A 릴레이 x3개
- DC 5V 5A 전원 공급
- 릴레이 구성: 구역 밸브 12개 + 펌프 1개 + 호스건 1개

## 🏗 프로젝트 구조

```
smart_farm/
├── hardware/              # 하드웨어 제어
│   ├── gpio_expander.py       # MCP23017 GPIO 확장
│   ├── relay_controller.py    # 릴레이 제어 (12구역 + 펌프)
│   ├── sensor_reader.py       # ADS1115 센서 읽기
│   ├── modbus_soil_sensor.py  # RS-485 토양 수분 센서 (Modbus RTU)
│   └── rtc_manager.py         # RTC 시간 관리
│
├── irrigation/            # 관수 제어
│   ├── auto_controller.py     # 자동 관수 컨트롤러 (수동/자동/스케줄)
│   ├── config_manager.py      # 설정 관리
│   ├── zone_manager.py        # 구역별 관수
│   ├── scheduler.py           # 스케줄 관리
│   ├── scenarios.py           # 시나리오 실행
│   └── config/                # 설정 파일
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
│   │   ├── settings.html  # 설정 페이지
│   │   └── irrigation.html  # 관수 제어 페이지
│   └── static/            # CSS, JS, 파비콘
│       ├── css/style.css
│       ├── js/
│       │   ├── dashboard.js
│       │   ├── settings.js
│       │   └── irrigation.js  # 관수 제어 클라이언트
│       └── favicon.svg
│
├── logs/                  # 로그 파일
│   ├── sensors_YYYY-MM-DD.csv  # 탱크 수위 센서 데이터 (10초 주기)
│   ├── irrigation_history.csv  # 관수 이력 영구 저장
│   └── alerts.log              # 알림 로그
│
└── config/                # 설정 파일
    ├── sensor_calibration.json  # 탱크 센서 캘리브레이션
    └── soil_sensors.json        # 토양 센서 / 관수 설정
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
- `pyserial` (RS-485 통신)
- `minimalmodbus` (Modbus RTU 드라이버)

### 3. I2C / UART 활성화

```bash
sudo raspi-config
# Interface Options > I2C > Enable
# Interface Options > Serial Port > Enable (RS-485용)
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
- 네트워크: `http://192.168.0.111:5000` (라즈베리파이 IP)

### 5. systemd 서비스 (자동 시작)

```bash
# 서비스 상태 확인
sudo systemctl status smart-farm.service

# 수동 재시작
sudo systemctl restart smart-farm.service

# 부팅 자동 시작 설정
sudo systemctl enable smart-farm.service
```

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
- **입력 범위**: 0.000V ~ 5.000V (전압 모드 전용)
- **입력 정밀도**: 0.001V 단위
- **3중 검증**: HTML + JavaScript + Python 서버
- **자동 반올림**: 소수점 3자리로 자동 정리
- **즉시 적용**: 저장 즉시 모니터링에 반영 (재시작 불필요)

### 샘플링 프로세스

```
타이밍: 10초 주기
  1초째 (0.0초) → 샘플 1
  2초째 (1.0초) → 샘플 2
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

### 토양 수분 센서 (RS-485 Modbus)

- **센서 수**: 12개 (구역 1~12)
- **측정 항목**: 수분(%), 온도(℃), EC(µS/cm)
- **통신**: Modbus RTU over RS-485
- **활용**: 자동 관수 트리거 판단 기준

## 🌱 관수 제어 시스템

### 동작 모드

| 모드 | 설명 |
|------|------|
| **수동 (Manual)** | 웹 UI에서 구역 선택 후 즉시 관수 |
| **자동 (Auto)** | 토양 수분이 임계값 미만이면 자동 관수 |
| **스케줄** | 설정한 시간대에 자동 관수 (준비 중) |

### 관수 실행 흐름

```
[수동] 웹 UI 버튼 클릭
  → POST /api/irrigation/start {zone_id, duration}
  → relay: 펌프 ON → 해당 구역 밸브 ON
  → duration 초 후 밸브 OFF → 펌프 OFF
  → irrigation_history.csv 기록

[자동] 30초 주기 모니터링
  → 12구역 토양 수분 측정
  → 수분 < 임계값 AND 탱크 수위 >= 최소 수위
  → 관수 실행 → CSV 기록
```

### 관수 이력 CSV 저장 형식

```
timestamp,zone_id,duration_sec,trigger,moisture_before,success
2026-02-23 10:15:30,3,30,manual,28.5,true
2026-02-23 11:02:00,7,45,auto,22.1,true
```

## 📈 데이터 로깅

### 탱크 수위 CSV 형식 (sensors_YYYY-MM-DD.csv)

```csv
timestamp,tank1_level,tank2_level,ch0_voltage,ch1_voltage,ch2_voltage,ch3_voltage
2026-02-20 13:08:30,72.2,78.4,0.589,0.589,0.589,0.588
2026-02-20 13:08:40,72.2,78.4,0.589,0.589,0.589,0.588
2026-02-20 13:08:50,72.3,78.5,0.589,0.590,0.590,0.589
```

### 관수 이력 CSV 형식 (irrigation_history.csv)

```
timestamp,zone_id,duration_sec,trigger,moisture_before,success
2026-02-23 10:15:30,3,30,manual,28.5,true
2026-02-23 11:02:00,7,45,auto,22.1,true
```

## 🚨 알림 시스템

### 알림 레벨

| 레벨 | 조건 | 용도 | 예시 |
|------|------|------|------|
| INFO | 정상 상태 | 일반 로그 | 시스템 시작, 설정 변경 |
| WARNING | 경고 상태 | 주의 필요 | 수위 20% 근접, 센서 오류 |
| CRITICAL | 위험 상태 | 즉시 조치 | 수위 20% 미만, 시스템 오류 |

### 알림 임계값
- **최소 수위**: 20% (CRITICAL)
- **최대 수위**: 90% (WARNING/CRITICAL)
- **쿨다운**: 300초 (동일 경고 중복 방지)

## ⚙️ 캘리브레이션

### 설정 페이지 기능

1. **센서 캘리브레이션** (전압 모드 전용):
   - Tank 1 Empty Value: 공탱크 전압 (0.000~5.000V)
   - Tank 1 Full Value: 만수 전압 (0.000~5.000V)
   - Tank 2 Empty Value: 공탱크 전압 (0.000~5.000V)
   - Tank 2 Full Value: 만수 전압 (0.000~5.000V)
   
2. **실시간 센서 값**: 현재 전압 표시 (5초 자동 갱신)

3. **빠른 설정 버튼**:
   - "현재 값을 Empty로 설정"
   - "현재 값을 Full로 설정"

4. **입력 검증 (3단계)**:
   - HTML: `max="5.000"` 속성
   - JavaScript: `validateVoltage()` 함수
   - Python: `validate_voltage()` 함수 (0~5V 범위, 소수점 3자리 반올림)

### 캘리브레이션 적용

- ✅ **즉시 반영**: 저장 즉시 모니터링에 적용
- ✅ **서버 재시작 불필요**: 실시간 reload
- ✅ **정밀도 유지**: 계산 시 전체 정밀도 사용
- ✅ **3중 검증**: HTML pattern + JavaScript + 서버 round()

## 🎨 웹 대시보드 (v2.7)

### 대시보드 페이지 (`/`)

#### 실시간 탭
- **탱크 수위 게이지**: 0~100% 시각화 (색상 코드: 녹색/노랑/빨강)
- **4채널 전압 표시**: CH0~CH3 실시간 전압 (0.001V 정밀도)
- **시스템 상태**: 마지막 업데이트 시각, 24시간 경고 횟수

#### 차트 탭
- **1시간 수위 변화 그래프** (360개 데이터 포인트)
- Chart.js 4.4 기반 실시간 라인 차트
- 10초마다 자동 업데이트
- 범례: 탱크1 (파랑), 탱크2 (주황)

#### 알림 탭
- 최근 10개 경고/알림 표시
- 타임스탬프, 레벨, 메시지

### 설정 페이지 (`/settings`)

- **센서 캘리브레이션**: 정밀 전압 입력 (0.001V 단위)
- **자동 제어**: 관수 임계값 설정 (Stage 8 확장 예정)
- **호스건 설정**: 수동 On/Off
- **알림 설정**: (Stage 8 예정)

### 관수 제어 페이지 (`/irrigation`)

#### 제어 패널 탭
- 시스템 상태 배너 (수동/자동/스케줄 모드 표시)
- 현재 관수 구역 및 오늘 관수 횟수
- 관수 진행 프로그레스 바 (잔여 시간 표시)
- 긴급 정지 버튼
- 모드 선택 버튼 (수동 / 자동 / 스케줄)
- 기본 관수 시간 설정 (초 단위)
- 12구역 토양 수분 바 차트 (Chart.js)

#### 구역별 제어 탭
- 12개 구역 카드 (원형 게이지 + 수분/온도/EC 수치 표시)
- 구역 상태 배지: 관수중 / 건조 / 적정 / 오프라인
- 구역별 수동 관수 버튼
- 임계값 설정 모달 (슬라이더, 10~80%)

#### 관수 이력 탭
- 최근 관수 이력 테이블 (시간, 구역, 관수(초), 트리거, 결과)
- **날짜 필터** (시작일~종료일 선택)
- **CSV 다운로드 버튼**

### 데이터 분석 페이지 (`/analytics`) ← NEW

#### 탱크 수위 트렌드 탭
- **수위 변화 라인 차트** (Chart.js 줌/팬 플러그인)
- **날짜 필터** + 빠른 기간 선택 (오늘 / 7일 / 30일 / 90일)
- 탱크1·탱크2 평균/최소/최대 통계 카드
- 800포인트 다운샘플링 (대용량 데이터 최적화)

#### 관수 분석 탭
- **일별 관수 횟수** 막대 차트
- **트리거 유형 비율** 도넛 차트 (자동/수동/스케줄)
- **구역별 평균 관수 시간** 라인 차트
- 성공률·총 관수 횟수 통계

#### 구역별 통계 탭
- **12구역 관수 횟수** 가로 막대 차트
- **12구역 평균 관수 시간** 가로 막대 차트
- 구역별 성공률 배지 포함 상세 테이블

#### 원시 로그 탭
- 구역·트리거 유형 필터
- 전체 관수 이력 테이블
- **CSV 다운로드** 버튼 (날짜 필터 적용)

#### 공통 UI/UX
- ✅ Gradient 네비게이션 바 (보라색 그라데이션)
- ✅ 7단계 폰트 크기 조절 (xs ~ xxl)
- ✅ Socket.IO 실시간 연결 상태 표시
- ✅ 터치 친화적 버튼 (≥60px 높이)
- ✅ 반응형 디자인 (모바일/태블릿 대응)

## 🔌 API 엔드포인트

### 시스템

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/status` | 시스템 상태 조회 (탱크 수위, 전압, 알림 수) |
| POST | `/api/start_monitoring` | 모니터링 시작 |
| POST | `/api/stop_monitoring` | 모니터링 중지 |
| GET | `/api/data_history?hours=24` | 센서 이력 (최근 100건) |
| GET | `/api/statistics?hours=24` | 탱크 통계 (평균/최소/최대) |

### 캘리브레이션

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/calibration` | 캘리브레이션 설정 조회 |
| POST | `/api/calibration` | 캘리브레이션 저장 (0~5V 검증) |
| GET | `/api/calibration/current` | 현재 실시간 센서 전압 |

### 알림

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/alerts?limit=20` | 최근 알림 목록 |

### 호스건

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/hose-gun/status` | 호스건 상태 조회 |
| POST | `/api/hose-gun/activate` | 호스건 ON |
| POST | `/api/hose-gun/deactivate` | 호스건 OFF |

### 관수 제어

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/irrigation/status` | 관수 전체 상태 (모드, 수분, 이력) |
| POST | `/api/irrigation/mode` | 모드 변경 `{mode: auto/manual/schedule}` |
| POST | `/api/irrigation/start` | 관수 시작 `{zone_id, duration}` |
| POST | `/api/irrigation/stop` | 긴급 정지 |
| GET | `/api/irrigation/sensors` | 토양 센서 현황 (캐시) |
| POST | `/api/irrigation/sensors/read` | 토양 센서 즉시 재측정 |
| POST | `/api/irrigation/threshold` | 구역 임계값 설정 `{zone_id, threshold}` |
| GET | `/api/irrigation/history?limit=20` | 관수 이력 JSON |

### 분석 API ← NEW

| Method | Endpoint | 설명 |
|--------|----------|-----------|
| GET | `/api/analytics/sensor-data` | 탱크 수위 이력 (`?from=&to=`, 다운샘플링 800pt) |
| GET | `/api/analytics/irrigation-history` | 관수 이력 분석 (`?from=&to=`, 구역별 통계 포함) |

### CSV 다운로드

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/download/irrigation-history` | 관수 이력 CSV (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |
| GET | `/api/download/sensor-data` | 탱크 수위 CSV (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |
| GET | `/api/download/files` | 다운로드 가능 파일 목록 |

## 📊 시스템 성능

| 항목 | 수치 |
|------|------|
| 탱크 수위 샘플링 주기 | 10초 (자동) |
| 샘플 개수 | 10회/주기 (Trimmed Mean) |
| 자동 관수 점검 주기 | 30초 |
| 관수 구역 수 | 12구역 |
| 토양 센서 수 | 12개 (RS-485 Modbus) |
| 측정 정밀도 | 0.3% (전압 기준) |
| ADC 해상도 | 16-bit (ADS1115) |
| I2C 속도 | 400 kbit/s |
| 알림 쿨다운 | 5분 (중복 방지) |
| 데이터 저장 | CSV (일별 파일) |
| 업데이트 주기 | 10초 (SocketIO) |
| 시간 표시 | 24시간제 (HH:MM:SS) |
| 차트 데이터 | 360개 (1시간) |

## 🗓 개발 이력

- **2026-02-10**: 하드웨어 설정, I2C 통신 구현, Stage 1 완료
- **2026-02-11**: 관수 시스템 Stage 2 완료 (구역 관리)
- **2026-02-12**: 모니터링 시스템 Stage 3 완료 (센서)
- **2026-02-13**: 웹 인터페이스 Stage 3 완료 (대시보드)
- **2026-02-20 (v2.0)**:
  - ✅ 대시보드 리뉴얼: 설정 페이지와 동일한 UI/UX
  - ✅ 차트 기능 개선: 1시간 (360개) 데이터 표시
  - ✅ 센서 시스템 단순화: 전압 전용 모드 (0~5V)
  - ✅ 입력 검증 강화: 3단계 검증 시스템
  - ✅ 프로덕션 최적화: 디버그 로그 제거
  - ✅ 캘리브레이션 시스템 완성: 소수점 3자리 정밀도
  - ✅ 실시간 모니터링 안정화: 중복 샘플링 제거
  - ✅ Git 정리: 백업 파일 제거, .gitignore 업데이트
- **2026-02-21 (Stage 4)** `e56e521`:
  - ✅ RS-485 토양 수분 센서 드라이버 구현 (Modbus RTU)
  - ✅ AutoIrrigationController 구현 (수동/자동/스케줄)
  - ✅ 관수 이력 메모리 저장 (최대 200건)
  - ✅ 관수 제어 API 8개 추가
- **2026-02-22 (Stage 5)** `e294a82`:
  - ✅ 관수 제어 웹 UI 구현 (irrigation.html, irrigation.js)
  - ✅ 3탭 구성: 제어 패널 / 구역별 제어 / 관수 이력
  - ✅ 12구역 카드 (원형 게이지, 상태 배지, 수동 관수 버튼)
  - ✅ 임계값 설정 모달 (슬라이더)
  - ✅ Socket.IO 실시간 동기화
  - ✅ 네비게이션 바에 관수 제어 링크 추가
- **2026-02-22 (Stage 6)** `c3d1027`:
  - ✅ systemd 서비스 등록 (부팅 자동 시작)
  - ✅ 로그 관리 구성
- **2026-02-23 (Stage 5+)**:
  - ✅ 관수 이력 CSV 영구 저장 (irrigation_history.csv)
  - ✅ 관수 이력 CSV 다운로드 API (날짜 필터 지원)
  - ✅ 탱크 수위 CSV 다운로드 API (기간별 병합)
  - ✅ irrigation.html 관수 이력 탭에 날짜 필터 + CSV 다운로드 버튼 추가
- **2026-02-24 (Stage 7)**:
  - ✅ `analytics.html` / `analytics.js` 데이터 분석 페이지 구현
  - ✅ 탱크 수위 트렌드 탭 (Chart.js 줌/팬, 800pt 다운샘플링)
  - ✅ 관수 분석 탭 (일별 횟수 막대, 트리거 도넛, 시간 라인 차트)
  - ✅ 구역별 통계 탭 (12구역 카운트/평균 가로 막대, 성공률 배지)
  - ✅ 원시 로그 탭 (필터 + 전체 이력 테이블 + CSV 다운로드)
  - ✅ `/api/analytics/sensor-data`, `/api/analytics/irrigation-history` API 추가
  - ✅ 모든 페이지 네비게이션 바에 분석(📊) 링크 추가

## 🔧 주요 해결 과제

### 2026-02-20 업데이트 (v2.0)

#### 1. 대시보드 리뉴얼 ✅
- **변경**: 설정 페이지와 동일한 UI/UX 적용
- **추가**: 탭 메뉴 (실시간 / 차트 / 알림)
- **개선**: 1시간 수위 그래프 (360개 데이터)
- **제거**: 연결 상태 표시, 모니터링 버튼 (자동 시작)

#### 2. 센서 시스템 단순화 ✅
- **변경**: 전압 모드 전용 (0~5V)
- **제거**: 전류 센서 옵션 (4~20mA)
- **제거**: 센서 타입 선택 UI

#### 3. 입력 검증 강화 ✅
- **추가**: HTML/JavaScript/Python 3단계 검증
- **추가**: 0~5V 범위 제한 (소수점 3자리)
- **차단**: API 직접 호출 우회 입력 방지

#### 4. 프로덕션 최적화 ✅
- **제거**: 디버그 로그 (샘플링, SENDER, DEBUG)
- **정리**: 깔끔한 서버 로그 (초기화, 경고, HTTP만)
- **추가**: Git `.gitignore` (백업 파일 제외)
- **추가**: 파비콘 (favicon.svg)

#### 5. 버그 수정 ✅
- **수정**: JavaScript 구문 오류
- **수정**: 들여쓰기 오류 (`sensor_reader.py`, `sensor_monitor.py`)
- **제거**: 불완전한 print 문

#### 6. 캘리브레이션 즉시 반영 ✅
- **문제**: 캘리브레이션 변경 후 서버 재시작 필요
- **해결**: `load_calibration()` 메서드 추가, 저장 즉시 reload

#### 7. 중복 샘플링 제거 ✅
- **문제**: 설정 페이지 접속 시마다 샘플링 재시작
- **해결**: API 엔드포인트를 캐시 사용으로 변경

#### 8. 정밀도 개선 ✅
- **문제**: 소수점 1자리 입력으로 정밀도 부족
- **해결**: 0.001V 단위 입력, 소수점 3자리 처리

## 📝 다음 단계 (TODO)

### ✅ 완료된 Stage

- [x] Stage 1 — 하드웨어 초기화 (I2C, ADS1115, MCP23017, RTC)
- [x] Stage 2 — 센서 모니터링 & 웹 대시보드
- [x] Stage 3 — 캘리브레이션 & 알림 시스템
- [x] Stage 3.5 — UI 개선 & 릴레이 로직 단순화 (`7af7d47`)
- [x] Stage 4 — RS-485 토양 센서 + 자동 관수 제어 (`e56e521`)
- [x] Stage 5 — 관수 제어 웹 UI + CSV 다운로드 (`e294a82`)
- [x] Stage 6 — systemd 자동 시작 + 로그 관리 (`c3d1027`)
- [x] Stage 7 — 데이터 분석 페이지 (`analytics.html`, Chart.js 줌/팬)

### ⏳ 예정된 Stage

#### ~~Stage 7: 로그 분석 페이지~~ ✅ 완료
- [x] 날짜별 과거 데이터 조회 (`analytics.html`)
- [x] 기간별 통계 (일/주/월)
- [x] 관수 효율 분석 (수분 변화 추이 그래프)
- [x] 그래프 줌/팬 기능

#### Stage 8: 알림 고도화
- [ ] Telegram 봇 알림 (수위 경고, 관수 완료)
- [ ] 이메일 알림
- [ ] 알림 임계값 웹 UI 설정

#### Stage 9: 양액 제어 (PWM)
- [ ] EC 기반 양액 농도 자동 조절
- [ ] PWM 펌프 제어

#### Stage 10: 안정성 & 모바일
- [ ] SQLite 데이터베이스 마이그레이션
- [ ] PWA (Progressive Web App)
- [ ] 오프라인 모드 지원

## 🛠️ 문제 해결

### I²C 장치 인식 안 됨
```bash
i2cdetect -y 1
# 0x20, 0x21, 0x48, 0x68 확인
```

### 서비스 상태 확인
```bash
sudo systemctl status smart-farm.service
sudo journalctl -u smart-farm.service -n 50 --no-pager
```

### 웹 페이지가 열리지 않음
```bash
# 서버 실행 확인
ps aux | grep python3

# 포트 확인
sudo netstat -tulnp | grep 5000
```

### 센서 값이 0.000V로 고정됨
```bash
# ADS1115 테스트
cd ~/smart_farm
python3 tests/test_ads1115.py
```

### RS-485 토양 센서 미응답
```bash
ls /dev/ttyUSB* /dev/ttyAMA*
python3 -c "import minimalmodbus; print('OK')"
```

### 관수 이력 CSV 없음
```bash
# irrigation_history.csv는 관수 1회 실행 시 자동 생성
ls -lh ~/smart_farm/logs/irrigation_history.csv
# 없다면 서버 재시작
sudo systemctl restart smart-farm.service
```

## 👤 개발자

- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스

MIT License
