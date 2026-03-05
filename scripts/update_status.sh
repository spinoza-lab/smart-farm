#!/bin/bash
# update_status.sh
# docs/STATUS.md 를 오늘 작업 내용으로 갱신합니다.

TARGET="/home/pi/smart_farm/docs/STATUS.md"
mkdir -p /home/pi/smart_farm/docs

cat > "$TARGET" << 'EOF'
# 📋 Smart Farm 프로젝트 현황 노트

> 최종 업데이트: 2026-03-05
> 버전: v3.6 (진행 중)

---

## ✅ 완료된 작업 목록

### v3.5 버그 수정
| ID | 내용 | 상태 |
|---|---|---|
| Bug-N1 | NameError: telegram_notifier=None 참조 오류 | ✅ 완료 |
| Bug-N2 | JSONDecodeError: notifications.json 손상 시 크래시 | ✅ 완료 |
| Bug-N3 | 텔레그램 토큰 덮어쓰기 방지 | ✅ 완료 |
| Bug-A1 | AlertManager 하드코딩 임계값 → 설정파일 연동 | ✅ 완료 |

### v3.6 기능 추가
| ID | 내용 | 상태 |
|---|---|---|
| Feat-1 | cooldown_seconds UI 설정 추가 (app.py, settings.html, settings.js) | ✅ 완료 |
| Feat-2 | docs/ 폴더 신설 및 README.md 구조 분할 | ✅ 완료 |
| Feat-3 | RTC DS1307 커널 드라이버 등록 (/boot/firmware/config.txt) | ✅ 완료 |
| Feat-4 | RTCManager를 datetime.now() 기반으로 교체 (I2C 충돌 해결) | ✅ 완료 |

### v3.6 버그 수정 (2026-03-05)
| ID | 내용 | 상태 | 관련 파일 |
|---|---|---|---|
| BUG-1 | 토양센서 시뮬레이션 fallback 조건부 제어 | ✅ 완료 | irrigation/auto_controller.py, config/soil_sensors.json |
| BUG-2 | cooldown_seconds 즉시 반영 강화 + send_message 오타 수정 | ✅ 완료 | web/app.py, irrigation/auto_controller.py |

### Git 커밋 이력 (최근순)
| 날짜 | 내용 |
|---|---|
| 2026-03-05 | fix(BUG-2): cooldown_seconds 즉시 반영 강화 + send_message 버그 수정 |
| 2026-03-05 | fix(BUG-1): 토양센서 시뮬레이션 fallback 조건부 제어 |
| 2026-03-05 | fix: RTCManager를 시스템 시간 기반으로 변경 |
| 2026-03-04 | docs: README 구조 분할 (docs/ 폴더 신설) |
| 2026-03-04 | feat(v3.6): cooldown_seconds UI 설정 추가 |

---

## ✅ BUG-1 수정 상세 (2026-03-05)

**파일**: `irrigation/auto_controller.py`, `config/soil_sensors.json`

**문제**: 토양센서(RS-485) 읽기 실패 시 랜덤값(20~80%)으로 자동 fallback하여 자동관수 판단
→ 센서 단선/오류 상태에서도 관수가 정상 동작하는 것처럼 보이거나 엉뚱하게 물을 줄 수 있음

**수정 내용**:
- `soil_sensors.json` > `irrigation` 섹션에 `simulation_mode: false` 추가
- `_load_config()`: `self.simulation_mode` 로드
- `_auto_check_and_irrigate()` 분기 변경:
  - `sensor_manager` 있음 → 실제 센서 읽기 (기존과 동일)
  - `sensor_manager` 없음 + `simulation_mode: true` → 시뮬 데이터 허용 (개발/테스트 전용)
  - `sensor_manager` 없음 + `simulation_mode: false` (기본값) → 관수 중단 + 텔레그램 경고
  - 전체 센서 읽기 실패 (valid=0) → 관수 중단 + 텔레그램 경고
- `_send_sensor_alert()` 헬퍼 메서드 신규 추가

**운영 시 주의**: `simulation_mode`는 기본값 `false`. 개발/테스트 시에만 `soil_sensors.json`에서 `true`로 변경

---

## ✅ BUG-2 수정 상세 (2026-03-05)

**파일**: `web/app.py`, `irrigation/auto_controller.py`

### 코드 분석 결과 (수정 전)
- `app.py`의 `init_monitoring_system()`이 서버 시작 시 `notifications.json`의 `cooldown_seconds`를 읽어 `AlertManager`에 주입 → 시작 시점은 정상
- `save_notification_config()` STEP5에서 `alert_manager.cooldown_seconds` 즉시 반영 로직 존재
- **문제**: 반영 조건이 `'cooldown_seconds' in incoming` → alerts만, thresholds만 저장하는 부분 업데이트 시 쿨다운 동기화 누락 가능

### 수정 내용
**[app.py]** STEP5 쿨다운 반영 조건 강화
- 이전: `'cooldown_seconds' in incoming` 일 때만 반영
- 이후: `merged['cooldown_seconds']` 값으로 항상 동기화 (저장된 값 = 메모리 값 보장)
- 변경·유지 여부를 로그로 출력

**[auto_controller.py]** `_send_sensor_alert()` 메서드 버그 수정 (BUG-1 후속)
- 이전: `_tn.send_message()` → TelegramNotifier에 존재하지 않는 메서드 (조용히 실패)
- 이후: `_tn.send()` → 정상 텔레그램 발송

### 서비스 재시작 후 확인된 로그
```
[Init] thresholds 로드: 탱크1=15.0~75.0%, 탱크2=10.0~80.0%, 쿨다운=3600s
   쿨다운: 3600초
```

---

## 🔴 발견된 잠재 버그 (미수정)

### BUG-3 | rtc_manager.py — set_datetime() 무동작 (낮음)
- **위치**: `hardware/rtc_manager.py`
- **증상**: v3.6 RTCManager 수정 후 `set_datetime()`이 no-op 상태
- **위험**: `scripts/sync_rtc.sh` 등 호출부에서 조용히 실패
- **수정 방향**: 함수 내 경고 로그 또는 `NotImplementedWarning` 추가, 호출부 일괄 점검
- **우선순위**: 낮음 (커널이 RTC 동기화 담당, 앱에서 직접 시간 쓸 일 없음)

### BUG-4 | rtc_manager.py — wait_until() / display_clock() 블로킹 (낮음)
- **위치**: `hardware/rtc_manager.py`
- **증상**: `wait_until()`이 메인 스레드에서 호출되면 `time.sleep(10)` 루프로 Flask 서버 정지 가능
- **수정 방향**: 실제 호출 여부 확인 후 필요 시 비동기 처리
- **현황**: 현재 scheduler.py 등 별도 스레드에서만 호출되는 것으로 추정, 확인 필요

### BUG-5 | app.py — periodic_data_sender 스레드 복구 없음 (중간)
- **위치**: `web/app.py` → `periodic_data_sender` 스레드
- **증상**: 백그라운드 스레드가 예외로 종료 시 UI WebSocket 갱신 중단 (서비스는 살아있음)
- **수정 방향**: 스레드 내부 `while` 루프에 `try/except` + 루프 계속 유지 (현재는 예외 발생 시 스레드 종료)
- **우선순위**: 중간 (서비스 크래시는 아니나 대시보드가 멈추는 현상 발생 가능)

### BUG-6 | sensor_monitor.py + alert_manager.py — 알림 중복 발송 가능성 (낮음)
- **위치**: `monitoring/sensor_monitor.py`, `monitoring/alert_manager.py`
- **증상**: 두 모듈 각각 수위 알림 콜백 보유 → 동일 이벤트에 텔레그램 알림 2회 발송 가능
- **수정 방향**: 알림 발송 경로를 AlertManager 단일 경로로 통합
- **현황**: 실제 중복 여부 로그로 확인 필요

### BUG-7 | 하드코딩된 절대 경로 (낮음)
- **위치**: 여러 파일 내 `/home/pi/smart_farm/` 직접 기재
- **증상**: 설치 경로 변경 또는 다른 사용자 실행 시 전체 오동작
- **수정 방향**: `BASE_DIR = Path(__file__).resolve().parent` 방식으로 통일
- **우선순위**: 낮음 (현재 운영 환경 고정)

---

## 🔧 하드웨어 현황

| 장치 | 모델 | I2C/포트 | 상태 |
|---|---|---|---|
| Raspberry Pi 4 | - | - | ✅ 정상 |
| GPIO 확장 | MCP23017 ×2 | 0x20, 0x21 | ✅ 정상 |
| ADC | ADS1115 | 0x48 | ✅ 정상 |
| RTC | DS1307 | 0x68 (커널 점유 UU) | ✅ 정상 (커널 드라이버) |
| 토양센서 | RS-485 Modbus ×12 | /dev/ttyS0 | ✅ 정상 (미검증) |
| 수위센서 | 아날로그 ×2 | ADS1115 CH0, CH1 | ✅ 정상 |
| 릴레이 | 6×4ch (24ch 총) | MCP23017 | ✅ 정상 |
| 여분 릴레이 채널 | - | ~10ch 여유 | - |
| 여분 ADS1115 채널 | - | CH2, CH3 | - |

### 수위 임계값 현황 (2026-03-05 기준)
- 탱크1 (물탱크): 최소 15% / 최대 75%
- 탱크2 (양액탱크): 최소 10% / 최대 80%

### RTC 특이사항
- `/boot/firmware/config.txt` 에 `dtoverlay=i2c-rtc,ds1307` 추가됨
- `/boot/config.txt` 에도 동일 라인 있으나 Bookworm 이후 **무시됨** (firmware 경로가 유효)
- 커널 부팅 시 RTC → 시스템 시간 자동 동기화
- `i2cdetect -y 1` 에서 0x68이 `UU` 표시 = 커널 점유 중 (정상)
- `rtc_manager.py` 는 I2C 직접 접근 제거, `datetime.now()` 사용

---

## 📌 다음 작업 후보

| 우선순위 | ID | 작업 | 예상 시간 |
|---|---|---|---|
| ⭐⭐⭐ | BUG-5 | periodic_data_sender 스레드 자동 재시작 | 20분 |
| ⭐⭐ | - | 캐시 버스팅: JS/CSS 버전 쿼리스트링 자동 추가 | 10분 |
| ⭐⭐ | - | 웹 UI 서버 재시작 버튼 추가 | 30분 |
| ⭐ | - | 텔레그램 /restart, /status 명령 추가 | 1시간 |
| ⭐ | BUG-4 | wait_until() 실제 호출 여부 확인 및 처리 | 10분 |
| ⭐ | BUG-3 | set_datetime() 호출부 점검 및 경고 로그 추가 | 10분 |
| - | - | Stage 9: EC 센서 기반 양액 제어 (하드웨어 필요) | 장기 |
| - | - | Stage 10: SQLite 마이그레이션 + PWA | 장기 |

---

## 🗂️ 문서 구조

```
smart_farm/
├── README.md              # 프로젝트 소개 + 문서 링크허브
└── docs/
    ├── STATUS.md          # ← 이 파일 (현재 작업 상황)
    ├── HARDWARE.md        # 하드웨어 구성
    ├── SETUP.md           # 설치 및 실행 가이드
    ├── FEATURES.md        # 주요 기능 상세
    ├── TELEGRAM.md        # 텔레그램 봇 설정
    ├── API.md             # API 엔드포인트 목록
    ├── CHANGELOG.md       # 버전별 개발 이력
    └── TROUBLESHOOTING.md # 문제 해결 가이드
```

---

## 🔑 자주 쓰는 명령어

```bash
# 서비스 상태 확인
sudo systemctl status smart-farm.service

# 서비스 재시작
sudo systemctl restart smart-farm.service

# 실시간 로그 확인
sudo journalctl -u smart-farm.service -f

# 최근 에러만 보기
sudo journalctl -u smart-farm.service --since "10 min ago" --no-pager | grep -E "ERROR|Error|❌"

# 쿨다운 값 확인
cat /home/pi/smart_farm/config/notifications.json | python3 -m json.tool | grep cooldown

# 쿨다운 실제 반영 확인 (서비스 시작 로그)
sudo journalctl -u smart-farm.service --since "5 min ago" --no-pager | grep -E "쿨다운|cooldown"

# RTC 상태 확인
timedatectl && ls /dev/rtc*

# I2C 장치 확인 (0x68=UU 가 정상)
i2cdetect -y 1

# simulation_mode 확인
python3 -c "import json; cfg=json.load(open('/home/pi/smart_farm/config/soil_sensors.json')); print('simulation_mode:', cfg.get('irrigation',{}).get('simulation_mode','없음'))"

# Git 최근 커밋
cd /home/pi/smart_farm && git log --oneline -8
```

---

_이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다._
EOF

echo "✅ $TARGET 갱신 완료"
