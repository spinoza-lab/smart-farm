#!/bin/bash
# make_status_note.sh
# 현재 스마트팜 프로젝트 상태 노트를 docs/STATUS.md 로 저장합니다.

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

### Git 커밋 이력 (최근)
| 해시 | 내용 |
|---|---|
| 최신 | fix: RTCManager를 시스템 시간 기반으로 변경 |
| b19546d | docs: README 구조 분할 (docs/ 폴더 신설) |
| 이전 | feat(v3.6): cooldown_seconds UI 설정 추가 |

---

## 🔴 발견된 잠재 버그 (미수정)

### BUG-1 | auto_controller.py — 시뮬레이션 fallback (심각)
- **위치**: `irrigation/auto_controller.py` → `_simulate_sensor_data()`
- **증상**: 토양센서(RS-485) 읽기 실패 시 랜덤값(20~80%)으로 fallback하여 자동관수 판단
- **위험**: 센서 오류 상태에서도 관수가 정상 동작하는 것처럼 보임 / 엉뚱하게 물을 줄 수 있음
- **수정 방향**: 센서 읽기 실패 시 관수 중단 + 텔레그램 경고 발송

### BUG-2 | 알림 쿨다운 이중 설정 (심각)
- **위치**: `monitoring/alert_manager.py` (기본값 300초) vs `config/notifications.json` (cooldown_seconds: 3600)
- **증상**: 어느 쪽 쿨다운이 실제 텔레그램 발송을 막는지 불명확
- **위험**: UI에서 1시간 설정해도 5분마다 발송될 수 있음 (또는 반대)
- **수정 방향**: AlertManager가 notifications.json의 cooldown_seconds를 읽어 통합 관리

### BUG-3 | rtc_manager.py — set_datetime() 무동작 (중간)
- **위치**: `hardware/rtc_manager.py`
- **증상**: 오늘 수정으로 set_datetime()이 no-op이 됨
- **위험**: 다른 코드(sync_rtc.sh 등)에서 호출 시 조용히 실패
- **수정 방향**: 함수 내부에 NotImplementedError 또는 경고 로그 추가, 호출부 점검

### BUG-4 | rtc_manager.py — wait_until() / display_clock() 블로킹 (중간)
- **위치**: `hardware/rtc_manager.py`
- **증상**: wait_until()이 메인 스레드에서 호출되면 time.sleep(10) 루프로 Flask 서버 멈춤
- **수정 방향**: 호출 여부 확인 후 비동기 처리 또는 별도 스레드에서만 호출하도록 제한

### BUG-5 | app.py — periodic_data_sender 스레드 복구 없음 (중간)
- **위치**: `web/app.py` → periodic_data_sender 스레드
- **증상**: 백그라운드 스레드가 예외로 종료되면 UI WebSocket 갱신이 멈춤 (서비스는 살아있음)
- **수정 방향**: 스레드 내부에 try/except + 자동 재시작 로직 추가

### BUG-6 | sensor_monitor.py + alert_manager.py — 알림 중복 발송 (낮음)
- **위치**: `monitoring/sensor_monitor.py`, `monitoring/alert_manager.py`
- **증상**: 두 모듈이 각각 독립적으로 수위 알림 콜백을 가져 동일 이벤트에 알림이 2회 발송될 수 있음
- **수정 방향**: 알림 발송 경로를 AlertManager 단일 경로로 통합

### BUG-7 | 하드코딩된 절대 경로 (낮음)
- **위치**: 여러 파일 내 `/home/pi/smart_farm/` 직접 기재
- **증상**: 설치 경로 변경 또는 다른 사용자 실행 시 전체 오동작
- **수정 방향**: BASE_DIR = Path(__file__).resolve().parent 방식으로 통일

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

### RTC 특이사항
- `/boot/firmware/config.txt`에 `dtoverlay=i2c-rtc,ds1307` 추가됨
- 커널이 부팅 시 RTC → 시스템 시간 자동 동기화
- `i2cdetect`에서 0x68이 `UU`로 표시되는 것이 정상 (커널 점유)
- `rtc_manager.py`는 I2C 직접 접근 제거, `datetime.now()` 사용으로 변경

---

## 📌 다음 작업 후보

| 우선순위 | 작업 | 예상 시간 |
|---|---|---|
| ⭐⭐⭐ | BUG-1 수정: 시뮬레이션 fallback → 오류 시 관수 중단 | 20분 |
| ⭐⭐⭐ | BUG-2 수정: 쿨다운 통합 (AlertManager ↔ notifications.json) | 30분 |
| ⭐⭐ | BUG-5 수정: periodic_data_sender 스레드 자동 재시작 | 20분 |
| ⭐⭐ | 캐시 버스팅: JS/CSS 버전 쿼리스트링 자동 추가 | 10분 |
| ⭐ | 웹 UI 서버 재시작 버튼 추가 | 30분 |
| ⭐ | 텔레그램 /restart, /status 명령 추가 | 1시간 |
| - | Stage 9: EC 센서 기반 양액 제어 (하드웨어 필요) | 장기 |
| - | Stage 10: SQLite 마이그레이션 + PWA | 장기 |

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

# RTC 상태 확인
timedatectl
ls /dev/rtc*

# I2C 장치 확인
i2cdetect -y 1

# Git 상태
cd /home/pi/smart_farm && git log --oneline -5
```

---

_이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다._
EOF

echo "✅ $TARGET 생성 완료"
