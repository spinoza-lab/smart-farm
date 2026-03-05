#!/bin/bash
# 스마트팜 문서 구조 분할 스크립트
# 실행: bash make_docs.sh

set -e
BASE=/home/pi/smart_farm

echo "📁 docs/ 폴더 생성..."
mkdir -p $BASE/docs

# ─────────────────────────────────────────
echo "📄 HARDWARE.md 생성..."
cat > $BASE/docs/HARDWARE.md << 'MDEOF'
# 🛠 하드웨어 구성

## Raspberry Pi 기반 시스템

- **Raspberry Pi 4** - 메인 컨트롤러
- **MCP23017 x2** (I2C 0x20, 0x21) - 32개 GPIO 확장
- **ADS1115** (I2C 0x48) - 4채널 16-bit ADC (센서 읽기, 전압 모드 0~5V)
- **RTC DS1307** (I2C 0x68) - 실시간 시계
- **RS-485 토양 수분 센서 x12** (Modbus RTU) - 수분·온도·EC 측정

## 전원 및 릴레이 시스템

- 릴레이 모듈 6개 x 4채널 (총 24채널)
- 50A 릴레이 x3개
- DC 5V 5A 전원 공급
- 릴레이 구성: 구역 밸브 12개 + 펌프 1개 + 호스건 1개
MDEOF

# ─────────────────────────────────────────
echo "📄 SETUP.md 생성..."
cat > $BASE/docs/SETUP.md << 'MDEOF'
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
MDEOF

# ─────────────────────────────────────────
echo "📄 TELEGRAM.md 생성..."
cat > $BASE/docs/TELEGRAM.md << 'MDEOF'
# 🤖 텔레그램 알림 봇 (v3.3~v3.6)

## 자동 알림

서버 또는 시스템 이벤트 발생 시 자동으로 텔레그램 메시지를 전송합니다.

| 이벤트 | 메시지 예시 |
|--------|------------|
| 서버 시작 | 🟢 **스마트팜 서버 시작** / ⏰ 2026-03-04 09:00:00 |
| 관수 시작 | 💧 **관수 시작** / 🌿 구역: 1 \| ⏱ 120초 \| 📌 트리거: ⏰ 스케줄 |
| 관수 완료 | ✅ **관수 완료** / 🌿 구역: 1 \| ⏱ 120초 \| 📌 트리거: ⏰ 스케줄 |
| 수위 부족 | 🚨 **탱크1 수위 부족!** / 📊 현재: 15.0% (최소: 20%) |
| 수위 과잉 | ⚠️ **탱크1 수위 과잉!** / 📊 현재: 95.0% (최대: 90%) |
| 센서 오류 | 🔴 **센서 오류** / 채널0 비정상 전압 |

> **알림 쿨다운**: 동일 알림은 설정된 시간(기본 5분) 이내 중복 전송되지 않습니다.
> 웹 UI 설정 페이지에서 조정 가능합니다. (v3.6)

## 인라인 버튼 메뉴 (v3.5 개선)

텍스트 명령어 대신 **인라인 키보드 버튼**으로 시스템을 제어합니다.

### 메인 메뉴 버튼 배치

```
[📊 상태 확인] [📋 오늘 이력]
[📅 스케줄 목록]
[💧 관수 시작]  [🛑 관수 중단]
[🔇 1시간 무음] [🔊 무음 해제]
```

| 버튼 / 명령어 | 설명 |
|--------|------|
| `/start`, `/menu` | 메인 메뉴 열기 |
| `/help` | 도움말 |
| 📊 **상태 확인** | 현재 모드·관수 상태·스케줄러 조회 |
| 📋 **오늘 이력** | 오늘 관수 이력 (최근 5건) |
| 📅 **스케줄 목록** | 등록된 스케줄/루틴 목록 |
| 💧 **관수 시작** | 구역 선택(1~12) → 시간 선택 → 즉시 실행 |
| 🛑 **관수 중단** | 현재 관수 즉시 중단 (≤1초 반응) |
| 🔇 **1시간 무음** | 알림 1시간 무음 설정 |
| 🔊 **무음 해제** | 무음 상태 해제, 알림 즉시 재개 |

> **관수 흐름**: 💧 관수 시작 → 구역 1~12 선택 → 30초/1분/2분/5분/10분/20분 선택
> → 즉시 "💧 관수 요청 접수" 응답 후 백그라운드 실행, 완료 시 ✅ 또는 🛑 알림 전송

## 알림 설정 (config/notifications.json)

v3.5부터 `thresholds` 섹션, v3.6부터 `cooldown_seconds` 필드가 추가되었습니다:

```json
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
```

## 알림 설정 안정성 (v3.5)

- **토큰 보호**: `GET /api/notifications/config` 응답에서 token/chat_id를 마스킹하여 GET→POST 루프로 인한 토큰 덮어쓰기 방지
- **원자적 파일 저장**: 임시 파일에 쓴 후 rename으로 교체 — 저장 도중 서버 오류가 나도 파일 손상 없음
- **메모리 우선 병합**: POST 요청에 telegram 섹션이 없으면 메모리(실행 중인 `telegram_notifier`)의 값을 유지
- **손상 복구**: 서버 시작 시 `notifications.json`이 없거나 빈 파일이면 기본값으로 자동 복원
MDEOF

# ─────────────────────────────────────────
echo "📄 FEATURES.md 생성..."
cat > $BASE/docs/FEATURES.md << 'MDEOF'
# 🌱 시스템 기능 상세

## 관수 제어 시스템 (v3.0)

### 동작 모드

| 모드 | 설명 |
|------|------|
| **수동 (Manual)** | 웹 UI에서 구역 선택 후 즉시 관수 |
| **자동 (Auto)** | 토양 수분 기반 자동 관수 + 스케줄/루틴 통합 실행 |

> v3.0부터 별도의 "스케줄" 모드가 제거되었습니다.
> 스케줄 및 루틴은 **자동 모드** 내에서 IrrigationScheduler가 통합 처리합니다.

### 스케줄 타입

| 타입 | 설명 | 필드 |
|------|------|------|
| `schedule` | 요일 기반 시간 스케줄 | `zone_id`, `start_time`, `days[]`, `duration`, `enabled` |
| `routine` | N일마다 반복 루틴 | `zone_id`, `start_date`, `start_time`, `interval_days`, `duration`, `check_moisture`, `enabled` |

### 루틴 스케줄러 (IrrigationScheduler)

```
IrrigationScheduler
  ├── schedule 타입: 지정 요일 + 시간에 관수 실행
  ├── routine 타입:  시작 날짜 기준 N일마다 반복
  │     └── check_moisture=true 시: 임계값 이하인 경우만 관수
  ├── 인터록 처리:   동시 관수 방지 (is_irrigating 체크)
  │     ├── ±10분 grace window: 예정 시간 ±10분 이내면 실행 대기
  │     └── 최대 1시간 대기 후 취소
  ├── 체크 주기:     10초 (CHECK_INTERVAL, v3.3에서 30→10초 단축)
  └── 자동 시작:     auto_controller.mode == 'auto' 시 자동 구동
```

### 스케줄 JSON 예시 (config/schedules.json)

```json
[
  {
    "id": 1,
    "type": "schedule",
    "zone_id": 1,
    "start_time": "06:00",
    "days": [0, 2, 4],
    "duration": 300,
    "enabled": true
  },
  {
    "id": 2,
    "type": "routine",
    "zone_id": 3,
    "start_date": "2026-02-25",
    "start_time": "08:00",
    "interval_days": 3,
    "duration": 180,
    "check_moisture": true,
    "enabled": true
  }
]
```

### 관수 실행 흐름

```
[수동] 웹 UI 버튼 클릭
  → POST /api/irrigation/start {zone_id, duration}
  → relay: 펌프 ON → 해당 구역 밸브 ON
  → duration 초 후 밸브 OFF → 펌프 OFF
  → irrigation_history.csv 기록
  → 텔레그램 관수 시작/완료 알림 전송

[자동] check_interval 주기 모니터링
  → 12구역 토양 수분 측정
  → 수분 < 임계값 AND 탱크 수위 >= 최소 수위
  → 관수 실행 → CSV 기록 → 텔레그램 알림

[스케줄/루틴] IrrigationScheduler (10초 주기 체크)
  → 실행 예정 스케줄 탐색 (±10분 grace window)
  → 인터록 확인 (이미 관수 중이면 대기 또는 취소)
  → check_moisture=true면 수분 임계값 재확인
  → 관수 실행 → CSV 기록 → 텔레그램 알림
```

---

## 센서 모니터링 시스템

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

### 토양 수분 센서 (RS-485 Modbus)

- **센서 모델**: CWT-Soil-THC-S (3핀 프로브)
- **센서 수**: 12개 (구역 1~12)
- **측정 항목**: 수분(%), 온도(℃), EC(µS/cm)
- **통신**: Modbus RTU over RS-485, `4800, N, 8, 1`
- **기본 슬레이브 주소**: 1 (공장 출하값), 주소 변경 레지스터: `0x07D0`
- **드라이버**: `minimalmodbus 2.1.1` (공유 시리얼 + `__new__` 초기화 호환)
- **활용**: 자동 관수 트리거 판단 기준

---

## 자동관수 설정 (분 단위 UI)

설정 페이지 → 자동관수 설정 탭에서 아래 항목을 설정합니다.

| 항목 | 단위 | 설명 | 저장 단위 |
|------|------|------|----------|
| 자동 체크 주기 | **분** | 토양 수분 점검 주기 | 초 (×60) |
| 기본 관수 시간 | **분** | 구역별 기본 관수 지속 시간 | 초 (×60) |
| 최소 탱크 수위 | % | 관수 허용 최소 수위 | % |
| 구역 간 대기 시간 | **초** | 구역 교체 시 대기 시간 | 초 |

> 웹 UI는 분 단위로 표시하고, 내부 API/파일은 초 단위로 저장합니다.

---

## 웹 인터페이스

### 대시보드 (/)

#### 실시간 탭
- **탱크 수위 게이지**: 0~100% 시각화 (색상 코드: 녹색/노랑/빨강)
- **4채널 전압 표시**: CH0~CH3 실시간 전압 (0.001V 정밀도)
- **관수 상태 카드**: 현재 모드, 관수 중 여부, 다음 스케줄 시간 표시
- **시스템 상태**: 마지막 업데이트 시각, 24시간 경고 횟수

#### 차트 탭
- **1시간 수위 변화 그래프** (360개 데이터 포인트)
- Chart.js 4.4 기반 실시간 라인 차트

#### 알림 탭
- 최근 10개 경고/알림 표시

### 설정 페이지 (/settings)

- **센서 캘리브레이션**: 정밀 전압 입력 (0.001V 단위)
- **자동관수 설정**: 체크 주기, 기본 관수 시간(분), 임계값, 대기 시간
- **스케줄 관수 설정**: schedule/routine 타입 CRUD
  - 스케줄 추가 모달: 타입 선택, 구역, 관수 시간(분), 시작 시간, 요일/반복주기, 수분체크 옵션
  - 테이블: 타입, 구역, 시작 시간, 관수 시간(분), 조건, 수분체크, 활성, 삭제
- **수분 임계값**: 12구역 개별 슬라이더 설정
- **알림 설정** (v3.5~v3.6): 텔레그램 봇 설정, 알림 항목 토글, 수위 임계값, 쿨다운 설정

### 관수 제어 페이지 (/irrigation)

#### 제어 패널 탭
- 시스템 상태 배너 (수동/자동 모드 표시)
- 현재 관수 구역 및 오늘 관수 횟수
- 관수 진행 프로그레스 바 (잔여 시간 표시, 페이지 재진입 시 복원)
- 긴급 정지 버튼
- 모드 선택 버튼 **(수동 / 자동)** — 스케줄 모드 제거됨

#### 구역별 제어 탭
- 12개 구역 카드 (원형 게이지 + 수분/온도/EC 수치 표시)
- 구역 상태 배지: 관수중 / 건조 / 적정 / 오프라인
- 구역별 수동 관수 버튼
- 임계값 설정 모달 (슬라이더, 10~80%)

#### 관수 이력 탭
- 최근 관수 이력 테이블 (시간, 구역, 관수 시간, 트리거, 결과)
- **날짜 필터** (시작일~종료일 선택)
- **CSV 다운로드 버튼**

### 데이터 분석 페이지 (/analytics)

#### 탱크 수위 트렌드 탭
- **수위 변화 라인 차트** (Chart.js 줌/팬 플러그인)
- **날짜 필터** + 빠른 기간 선택 (오늘 / 7일 / 30일 / 90일)
- 탱크1·탱크2 평균/최소/최대 통계 카드
- 800포인트 다운샘플링 (대용량 데이터 최적화)

#### 관수 분석 탭
- **일별 관수 횟수** 막대 차트
- **트리거 유형 비율** 도넛 차트 (자동/수동/스케줄)
- **구역별 평균 관수 시간** 라인 차트

#### 구역별 통계 탭
- **12구역 관수 횟수/평균 시간** 가로 막대 차트
- 구역별 성공률 배지 포함 상세 테이블

#### 원시 로그 탭
- 구역·트리거 유형 필터
- 전체 관수 이력 테이블
- **CSV 다운로드** 버튼 (날짜 필터 적용)
MDEOF

# ─────────────────────────────────────────
echo "📄 API.md 생성..."
cat > $BASE/docs/API.md << 'MDEOF'
# 🔌 API 엔드포인트

## 시스템

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/status` | 시스템 상태 조회 |
| POST | `/api/start_monitoring` | 모니터링 시작 |
| POST | `/api/stop_monitoring` | 모니터링 중지 |
| GET | `/api/data_history?hours=24` | 센서 이력 |
| GET | `/api/statistics?hours=24` | 탱크 통계 |

## 캘리브레이션

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/calibration` | 캘리브레이션 설정 조회 |
| POST | `/api/calibration` | 캘리브레이션 저장 (0~5V 검증) |
| GET | `/api/calibration/current` | 현재 실시간 센서 전압 |

## 알림 설정 (v3.5~v3.6)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/notifications/config` | 알림 설정 조회 (token 마스킹) |
| POST | `/api/notifications/config` | 알림 설정 저장 (메모리 우선 병합) |
| GET | `/api/notifications/status` | 텔레그램 봇 상태 조회 |
| POST | `/api/notifications/test` | 텔레그램 테스트 메시지 전송 |

## 관수 제어

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/irrigation/status` | 관수 전체 상태 (모드, 수분, 이력, irr_elapsed/irr_total) |
| POST | `/api/irrigation/mode` | 모드 변경 `{mode: auto\|manual}` |
| POST | `/api/irrigation/start` | 관수 시작 `{zone_id, duration}` |
| POST | `/api/irrigation/stop` | 긴급 정지 |
| GET | `/api/irrigation/sensors` | 토양 센서 현황 (캐시) |
| POST | `/api/irrigation/sensors/read` | 토양 센서 즉시 재측정 |
| POST | `/api/irrigation/threshold` | 구역 임계값 설정 `{zone_id, threshold}` |
| GET | `/api/irrigation/history?limit=20` | 관수 이력 JSON |
| GET | `/api/irrigation/config` | 자동관수 설정 조회 |
| POST | `/api/irrigation/config` | 자동관수 설정 저장 |

## 스케줄 CRUD

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/schedules` | 전체 스케줄/루틴 목록 |
| POST | `/api/schedules` | 새 스케줄/루틴 추가 |
| PUT | `/api/schedules/<id>` | 스케줄 수정 (zone_id, start_time, duration, days, enabled) |
| DELETE | `/api/schedules/<id>` | 스케줄 삭제 |
| PATCH | `/api/schedules/<id>` | 스케줄 활성/비활성 토글 (enabled 필드) |
| GET | `/api/schedules/next` | 다음 실행 예정 스케줄 (next_run, start_time, minutes_until 포함) |

## 분석 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/analytics/sensor-data` | 탱크 수위 이력 (`?from=&to=`, 다운샘플링 800pt) |
| GET | `/api/analytics/irrigation-history` | 관수 이력 분석 (`?from=&to=`) |

## CSV 다운로드

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/download/irrigation-history` | 관수 이력 CSV (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |
| GET | `/api/download/sensor-data` | 탱크 수위 CSV (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |

## 호스건

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/hose-gun/status` | 호스건 상태 조회 |
| POST | `/api/hose-gun/activate` | 호스건 ON |
| POST | `/api/hose-gun/deactivate` | 호스건 OFF |
MDEOF

# ─────────────────────────────────────────
echo "📄 CHANGELOG.md 생성..."
cat > $BASE/docs/CHANGELOG.md << 'MDEOF'
# 🗓 개발 이력

## 초기 개발

- **2026-02-10**: 하드웨어 설정, I2C 통신 구현, Stage 1 완료
- **2026-02-11**: 관수 시스템 Stage 2 완료 (구역 관리)
- **2026-02-12**: 모니터링 시스템 Stage 3 완료 (센서)
- **2026-02-13**: 웹 인터페이스 Stage 3 완료 (대시보드)

## v2.0 (2026-02-20)

- ✅ 대시보드 리뉴얼: 설정 페이지와 동일한 UI/UX
- ✅ 차트 기능 개선: 1시간 (360개) 데이터 표시
- ✅ 센서 시스템 단순화: 전압 전용 모드 (0~5V)
- ✅ 입력 검증 강화: 3단계 검증 시스템
- ✅ 프로덕션 최적화: 디버그 로그 제거
- ✅ 캘리브레이션 시스템 완성: 소수점 3자리 정밀도
- ✅ 실시간 모니터링 안정화: 중복 샘플링 제거

## Stage 4 (2026-02-21) `e56e521`

- ✅ RS-485 토양 수분 센서 드라이버 구현 (Modbus RTU)
- ✅ AutoIrrigationController 구현 (수동/자동/스케줄)
- ✅ 관수 이력 메모리 저장 (최대 200건)
- ✅ 관수 제어 API 8개 추가

## Stage 5 (2026-02-22) `e294a82`

- ✅ 관수 제어 웹 UI 구현 (irrigation.html, irrigation.js)
- ✅ 3탭 구성: 제어 패널 / 구역별 제어 / 관수 이력
- ✅ 12구역 카드 (원형 게이지, 상태 배지, 수동 관수 버튼)
- ✅ 임계값 설정 모달 (슬라이더)
- ✅ Socket.IO 실시간 동기화

## Stage 6 (2026-02-22) `c3d1027`

- ✅ systemd 서비스 등록 (부팅 자동 시작)
- ✅ 로그 관리 구성

## Stage 5+ (2026-02-23)

- ✅ 관수 이력 CSV 영구 저장 (irrigation_history.csv)
- ✅ 관수 이력 CSV 다운로드 API (날짜 필터 지원)
- ✅ 탱크 수위 CSV 다운로드 API (기간별 병합)

## Stage 7 (2026-02-24)

- ✅ `analytics.html` / `analytics.js` 데이터 분석 페이지 구현
- ✅ 탱크 수위 트렌드, 관수 분석, 구역별 통계, 원시 로그 탭
- ✅ Chart.js 줌/팬, 800pt 다운샘플링
- ✅ `/api/analytics/sensor-data`, `/api/analytics/irrigation-history` API 추가

## v3.0 (2026-02-24) `e228b1a`

- ✅ **모드 단순화**: 수동/자동 2모드로 통합 (스케줄 모드 제거)
- ✅ **IrrigationScheduler 완전 구현**: schedule/routine 타입 지원
- ✅ **루틴 기능**: 날짜 기반 N일마다 반복, 수분 체크 옵션
- ✅ **인터록 처리**: ±10분 grace window, 최대 1시간 대기
- ✅ **스케줄 CRUD API** 7개 (`/api/schedules/*`)
- ✅ **UI 분 단위 통합**: 체크 주기·관수 시간 모두 분 입력 (백엔드 초 저장)

## v3.1 / patch_v4h (2026-02-25) `75027f2` `b177097`

- ✅ **[Fix-서버시작]** `if __name__ == '__main__':` 블록 유실 복구
- ✅ **[Fix M]** `PUT /api/schedules/<id>` 엔드포인트 복구 → 405 오류 해결
- ✅ **[Fix B]** `toggle_schedule` 빈 바디 복구 → PATCH 500 오류 해결
- ✅ **[Fix J]** `/api/schedules/next` 응답에 `start_time`, `minutes_until` 필드 추가
- ✅ GitHub Issue [#5](https://github.com/spinoza-lab/smart-farm/issues/5) 해결

## v3.2 (2026-02-26) `94e3306` `c1feebf`

- ✅ **[Fix S]** `SoilSensorManager` zones 2~12 minimalmodbus 2.x 필수 속성 누락 수정
- ✅ **`tools/set_sensor_address.py`** 신규 추가 (RS485 Modbus 주소 설정 CLI)
- ✅ GitHub Issue [#4](https://github.com/spinoza-lab/smart-farm/issues/4) 해결

## v3.3 (2026-03-03) `6005970` `ec64bdf` `b3185e8`

- ✅ **[Bug-M1]** 서버 시작 시 스케줄러 미시작 수정 (모드 기본값 `manual` → `auto`)
- ✅ **[Bug-M2]** `auto` 모드 선택 시 `scheduler.stop()` 즉시 호출되는 버그 수정
- ✅ **[Bug-M3]** `soil_sensors.json` 모드 키 없어 재시작 후 `manual`로 초기화되는 버그 수정
- ✅ **[Bug-S]** `start_zone_irrigation()` 메서드 미존재로 `AttributeError` 무음 실패 수정
  - `auto_controller.py`에 `start_zone_irrigation()` 래퍼 메서드 추가
  - `irrigate_zone()`에 `trigger` 파라미터 추가 (CSV에 `scheduler` 트리거 정확히 기록)
- ✅ **[Logger]** `scheduler.py` logger 핸들러 추가 (기존 무음 드롭 → StreamHandler 출력)
- ✅ **[refactor]** 폰트 크기 조절 공통 모듈화 (`font-utils.js` 신규)
  - 기존 페이지별 개별 localStorage 키 → 단일 키 `fontSize` 통합
  - 인라인 스크립트 제거, 전 페이지 `font-utils.js` 공통 사용
- ✅ **[Stage 8]** 텔레그램 알림 봇 구현 (`monitoring/telegram_notifier.py` 신규)
  - Phase 1: 서버 시작·관수 시작/완료·수위 경고·센서 오류 자동 알림
  - Phase 2: `/status`, `/history`, `/schedules`, `/irrigate`, `/stop`, `/mute` 명령어 봇
  - AlertManager 콜백 연동, 폴링 주기 3초
- ✅ **[성능]** `CHECK_INTERVAL` 30초 → 10초 단축 (구역 간 전환 딜레이 개선)
- ✅ **[개발환경]** VS Code Remote-SSH 설정 (맥북 → 라즈베리파이 직접 개발)
- ✅ 주말(2/27~3/2) 7회 미실행 확인 및 전체 원인 규명 완료

## v3.4 (2026-03-03)

- ✅ **[Stage 8 – Telegram 인라인 UI]** 텍스트 명령어 → 인라인 키보드 메뉴로 전면 개편
  - `MAIN_MENU`, `ZONE_MENU` (12구역 그리드), `duration_menu` (30초/1분/2/5/10/20분) 추가
  - `edit_message()` 메서드 추가 — 새 메시지 발송 대신 기존 메시지를 수정해 채팅창 노이즈 최소화
  - `_poll_loop`이 `callback_query`와 텍스트(`/start`, `/menu`, `/help`) 동시 처리
- ✅ **[Bug-T1]** 관수 중단 시 `❌ 관수 실패` + `🛑 중단됨` 이중 메시지 버그 수정
  - `notify_irrigation_done(success=False)` → `🛑 관수 중단됨 – 구역N ⏱ N초 경과` 단일 메시지
- ✅ **[Bug-T2]** 관수 버튼 클릭 시 폴링 스레드 전체 블로킹 버그 수정
  - `_handle_irrigate_zone` — 즉시 "💧 관수 요청 접수" 응답 후 백그라운드 daemon 스레드 실행
- ✅ **[Bug-T3]** 웹 UI `/api/irrigation/stop` 이 `_stop_requested` 플래그 미설정 → 중단 지연 버그 수정
  - `app.py` stop 라우트에 `auto_irrigation.stop_irrigation()` 호출 추가
  - 웹 UI 긴급 정지 1초 이내 즉시 반영
- ✅ **[auto_controller]** `irrigate_zone()` 단일 `time.sleep` → 1초 루프 + `_stop_requested` 플래그 체크
  - `stop_irrigation()` 메서드 신규 추가
  - `actual_duration` 실제 경과 시간 기록, 결과 dict에 `duration`·`success` 포함

## v3.5 (2026-03-04)

- ✅ **[Bug-N1]** `NameError: telegram_notifier is not defined` 수정
  - `web/app.py` 모듈 상단에 `telegram_notifier = None` 전역 선언 추가
- ✅ **[Bug-N2]** `notifications.json` 빈 파일/손상 시 `JSONDecodeError` 수정
  - `get_notification_config`: 빈 파일·파싱 오류 시 기본값으로 자동 복원
  - `save_notification_config`: 원자적 저장 (임시 파일 → rename) 적용
- ✅ **[Bug-N3]** `import json` 누락으로 `save_notification_config` 500 오류 수정
- ✅ **[Fix-N4]** 설정 저장 시 텔레그램 토큰 덮어쓰기 방지
  - `get_notification_config` 응답에서 token/chat_id 마스킹
  - `save_notification_config`: POST에 telegram 섹션 없으면 메모리값 유지
  - `settings.js`: POST 요청에서 alerts/thresholds만 전송 (telegram 제외)
- ✅ **[Fix-N5]** 텔레그램 인라인 메뉴 버튼 배치 개선
  - "현재 상태" → "상태 확인" 이름 변경
  - 버튼 배치: `[상태 확인][오늘 이력] / [스케줄 목록] / [관수 시작][관수 중단] / [1시간 무음][무음 해제]`
- ✅ **[Fix-N6]** `settings.html` 텔레그램 버튼 메뉴 설명을 실제 봇과 동기화
- ✅ `notifications.json`에 `thresholds` 섹션 추가 (tank1/tank2 min/max 수위 임계값)
- ✅ **[Bug-A1]** 서버 재시작 시 AlertManager thresholds 하드코딩 문제 수정
  - 서버 시작 시 `notifications.json`에서 thresholds 로드하여 AlertManager에 적용
  - 폴백: 파일 없거나 오류 시 기본값 20/90% 사용

## v3.6 (2026-03-04) `85404fc`

- ✅ **[feat]** 알림 쿨다운(cooldown_seconds) 웹 UI 설정 추가
  - 서버 시작 시 `notifications.json`에서 `cooldown_seconds` 로드
  - `POST /api/notifications/config`에서 `cooldown_seconds` 저장 및 즉시 반영
  - `GET /api/notifications/config` 응답에 `cooldown_seconds` 포함
  - `settings.html`: 알림 설정 탭에 쿨다운 UI 추가 (분 단위 입력 + 프리셋 버튼)
  - `settings.js`: `loadNotificationConfig()`, `saveCooldownConfig()` 함수 추가
MDEOF

# ─────────────────────────────────────────
echo "📄 TROUBLESHOOTING.md 생성..."
cat > $BASE/docs/TROUBLESHOOTING.md << 'MDEOF'
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
MDEOF

# ─────────────────────────────────────────
echo "📄 README.md 교체..."
cat > $BASE/README.md << 'MDEOF'
# 🌱 스마트 관수 시스템 (Smart Irrigation System)

> **Repository**: [spinoza-lab/smart-farm](https://github.com/spinoza-lab/smart-farm)
> **최종 업데이트**: 2026-03-04
> **버전**: v3.6

라즈베리파이 기반 자동 관수 및 수위 모니터링 시스템

---

## 📌 주요 기능

- 🔄 **실시간 센서 모니터링** - 10초 주기 자동 샘플링
- 💧 **수위 관리** - 탱크1(물), 탱크2(양액) 실시간 모니터링
- ⚙️ **정밀 캘리브레이션** - 소수점 3자리 정밀도 (0.001V 단위)
- 📊 **실시간 대시보드** - WebSocket 기반 실시간 업데이트
- 🚨 **알림 시스템** - 수위 부족/과다 자동 경고 (쿨다운 설정 가능, v3.6)
- 📈 **데이터 로깅** - CSV 형식 자동 저장 (탱크 수위 + 관수 이력)
- 🌱 **12구역 자동 관수** - 토양 수분 센서 기반 수동/자동 모드
- 🗓 **루틴 스케줄러** - 날짜/시간 기반 반복 관수 루틴 + 수분 체크 옵션
- 🔒 **인터록 처리** - 동시 관수 방지, ±10분 grace window
- 🎛️ **관수 제어 웹 UI** - 구역별 게이지, 수동 관수, 임계값 설정
- 📥 **CSV 데이터 다운로드** - 탱크 수위·관수 이력 기간별 내보내기
- 🔧 **systemd 자동 시작** - 부팅 시 자동 실행 및 로그 관리
- 📊 **데이터 분석 페이지** - 탱크 수위 트렌드, 관수 효율, 구역별 통계, 줌/팬 차트
- 🤖 **텔레그램 알림 봇** - 서버 시작·관수 시작/완료·수위 경고 자동 알림 + 원격 명령어 제어
- 🛡️ **알림 설정 안정성** - notifications.json 손상 방지, 토큰 보호, 원자적 파일 저장 (v3.5)

---

## 📚 문서

| 문서 | 내용 |
|------|------|
| [🛠 하드웨어 구성](docs/HARDWARE.md) | 부품 목록, 릴레이 구성 |
| [🚀 설치 가이드](docs/SETUP.md) | 환경 설정, 의존성, 텔레그램 봇 설정, VS Code SSH |
| [🌱 시스템 기능](docs/FEATURES.md) | 관수 제어, 센서 모니터링, 웹 인터페이스 상세 |
| [🤖 텔레그램 봇](docs/TELEGRAM.md) | 자동 알림, 인라인 메뉴, 설정 안정성 |
| [🔌 API 레퍼런스](docs/API.md) | 전체 API 엔드포인트 목록 |
| [📝 변경 이력](docs/CHANGELOG.md) | 버전별 업데이트 내용 (v2.0~v3.6) |
| [🔧 트러블슈팅](docs/TROUBLESHOOTING.md) | 자주 발생하는 오류 및 해결법 |

---

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
│   ├── auto_controller.py     # 자동 관수 컨트롤러 (수동/자동)
│   ├── scheduler.py           # 루틴 스케줄러 (schedule/routine 타입)
│   ├── config_manager.py      # 설정 관리
│   ├── zone_manager.py        # 구역별 관수
│   ├── scenarios.py           # 시나리오 실행
│   └── config/                # 설정 파일
│
├── monitoring/            # 모니터링 & 로깅
│   ├── sensor_monitor.py      # 센서 모니터링 (핵심)
│   ├── data_logger.py         # CSV 데이터 저장
│   ├── alert_manager.py       # 알림 관리
│   └── telegram_notifier.py   # 텔레그램 알림 봇 (v3.3~)
│
├── web/                   # 웹 인터페이스
│   ├── app.py             # Flask 서버 (v3.6)
│   ├── templates/
│   │   ├── index.html         # 대시보드
│   │   ├── settings.html      # 설정 페이지
│   │   └── irrigation.html    # 관수 제어 페이지
│   └── static/
│       ├── css/style.css
│       ├── js/
│       │   ├── dashboard.js
│       │   ├── settings.js
│       │   ├── irrigation.js
│       │   └── font-utils.js
│       └── favicon.svg
│
├── tools/
│   └── set_sensor_address.py  # RS485 Modbus 주소 설정 CLI
│
├── logs/
│   ├── sensors_YYYY-MM-DD.csv
│   ├── irrigation_history.csv
│   └── alerts.log
│
├── config/
│   ├── sensor_calibration.json
│   ├── soil_sensors.json
│   ├── schedules.json
│   └── notifications.json
│
└── docs/                  # 상세 문서
    ├── HARDWARE.md
    ├── SETUP.md
    ├── FEATURES.md
    ├── TELEGRAM.md
    ├── API.md
    ├── CHANGELOG.md
    └── TROUBLESHOOTING.md
```

---

## 📊 시스템 성능

| 항목 | 수치 |
|------|------|
| 탱크 수위 샘플링 주기 | 10초 (자동) |
| 샘플 개수 | 10회/주기 (Trimmed Mean) |
| 자동 관수 점검 주기 | 설정 가능 (기본 10분) |
| 스케줄 체크 주기 | 10초 (v3.3, 기존 30초) |
| 인터록 grace window | ±10분 |
| 최대 관수 대기 시간 | 1시간 |
| 관수 구역 수 | 12구역 |
| 토양 센서 수 | 12개 (RS-485 Modbus) |
| 측정 정밀도 | 0.3% (전압 기준) |
| ADC 해상도 | 16-bit (ADS1115) |
| I2C 속도 | 400 kbit/s |
| 알림 쿨다운 | 웹 UI에서 설정 가능 (기본 5분, v3.6) |
| 데이터 저장 | CSV (일별 파일) |
| 업데이트 주기 | 10초 (SocketIO) |
| 텔레그램 폴링 주기 | 3초 |

---

## 📝 다음 단계 (TODO)

### ✅ 완료된 Stage

- [x] Stage 1 — 하드웨어 초기화 (I2C, ADS1115, MCP23017, RTC)
- [x] Stage 2 — 센서 모니터링 & 웹 대시보드
- [x] Stage 3 — 캘리브레이션 & 알림 시스템
- [x] Stage 3.5 — UI 개선 & 릴레이 로직 단순화
- [x] Stage 4 — RS-485 토양 센서 + 자동 관수 제어
- [x] Stage 5 — 관수 제어 웹 UI + CSV 다운로드
- [x] Stage 6 — systemd 자동 시작 + 로그 관리
- [x] Stage 7 — 데이터 분석 페이지 (analytics.html, Chart.js 줌/팬)
- [x] Stage 7.5 — 모드 단순화 + 루틴 스케줄러 + 분 단위 UI (v3.0)
- [x] Stage 7.6 — API 버그 수정 + 센서 드라이버 안정화 + 유지보수 도구 추가 (v3.1~v3.2)
- [x] Stage 8 — 텔레그램 알림 봇 (자동 알림 + 명령어 제어) (v3.3)
- [x] Stage 8.5 — 알림 설정 UI (웹 토글·임계값 저장·토큰 보호·쿨다운 설정) (v3.5~v3.6)

### ⏳ 예정된 Stage

#### Stage 9: 양액 제어 (PWM)
- [ ] EC 기반 양액 농도 자동 조절
- [ ] PWM 펌프 제어

#### Stage 10: 안정성 & 모바일
- [ ] SQLite 데이터베이스 마이그레이션
- [ ] PWA (Progressive Web App)
- [ ] 오프라인 모드 지원

---

## 👤 개발자

- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스

MIT License
MDEOF

# ─────────────────────────────────────────
echo ""
echo "✅ 완료! 생성된 파일 목록:"
ls -lh $BASE/docs/
echo ""
echo "📄 README.md 크기:"
wc -l $BASE/README.md
