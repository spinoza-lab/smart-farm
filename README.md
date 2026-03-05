# 🌱 스마트 관수 시스템 (Smart Irrigation System)

> **Repository**: [spinoza-lab/smart-farm](https://github.com/spinoza-lab/smart-farm)
> **최종 업데이트**: 2026-03-05
> **버전**: v3.6

라즈베리파이 기반 자동 관수 및 수위 모니터링 시스템

---

## 📌 주요 기능

- 🔄 **실시간 센서 모니터링** — 10초 주기 자동 샘플링, Trimmed Mean 정밀 처리
- 💧 **수위 관리** — 탱크1(물), 탱크2(양액) 실시간 모니터링 및 임계값 알림
- ⚙️ **정밀 캘리브레이션** — 소수점 3자리 정밀도 (0.001V 단위), 3중 검증
- 📊 **실시간 대시보드** — WebSocket 기반 10초 자동 갱신
- 🚨 **알림 시스템** — 수위/센서 이상 자동 경고, 쿨다운 웹 UI 설정 가능 (v3.6)
- 📈 **데이터 로깅** — CSV 형식 자동 저장 (탱크 수위 + 관수 이력)
- 🌱 **12구역 자동 관수** — 토양 수분 센서 기반 수동/자동 모드
- 🗓 **루틴 스케줄러** — 요일 기반(schedule) + N일 주기(routine) + 수분 조건부 실행
- 🔒 **인터록 처리** — 동시 관수 방지, ±10분 grace window, 최대 1시간 대기
- 🎛️ **관수 제어 웹 UI** — 구역별 게이지, 수동 관수, 임계값 설정, 진행 상태바
- 📥 **CSV 데이터 다운로드** — 탱크 수위·관수 이력 기간별 내보내기
- 🔧 **systemd 자동 시작** — 부팅 시 자동 실행 및 로그 관리
- 📊 **데이터 분석 페이지** — 탱크 수위 트렌드, 관수 효율, 구역별 통계 (Chart.js 줌/팬)
- 🤖 **텔레그램 알림 봇** — 서버 시작·관수 시작/완료·수위 경고 자동 알림 + 인라인 키보드 원격 제어
- 🛡️ **알림 설정 안정성** — notifications.json 손상 방지, 토큰 보호, 원자적 파일 저장 (v3.5)
- 🐕 **Watchdog 스레드** — periodic_data_sender 자동 재시작, 30초 내 복구 (v3.6)
- 🗂️ **동적 경로 처리** — _BASE_DIR 기반으로 어디서든 실행 가능 (v3.6)
- ⚡ **JS/CSS 캐시 버스팅** — 서버 시작 타임스탬프 자동 적용 (v3.6)

---

## 📚 문서

| 문서 | 내용 |
|------|------|
| [🛠 하드웨어 구성](docs/HARDWARE.md) | 부품 목록, I2C 주소, 릴레이 구성 |
| [🚀 설치 가이드](docs/SETUP.md) | 환경 설정, 의존성, 텔레그램 봇 설정, VS Code SSH |
| [🌱 시스템 기능](docs/FEATURES.md) | 관수 제어, 센서 모니터링, 웹 인터페이스 상세 |
| [🤖 텔레그램 봇](docs/TELEGRAM.md) | 자동 알림, 인라인 메뉴, 설정 안정성 |
| [🔌 API 레퍼런스](docs/API.md) | 전체 API 엔드포인트 목록 (28개) |
| [📝 변경 이력](docs/CHANGELOG.md) | 버전별 업데이트 내용 (v2.0~v3.6) |
| [🔧 트러블슈팅](docs/TROUBLESHOOTING.md) | 자주 발생하는 오류 및 해결법 |
| [📋 프로젝트 현황](docs/STATUS.md) | 버그 현황, 커밋 이력, 작업 노트 |

---

## 🏗 프로젝트 구조

```
smart_farm/
├── hardware/                  # 하드웨어 제어
│   ├── gpio_expander.py       # MCP23017 GPIO 확장 (I2C 0x20/0x21)
│   ├── relay_controller.py    # 릴레이 제어 (구역밸브 12 + 펌프 + 호스건)
│   ├── sensor_reader.py       # ADS1115 센서 읽기 (0~5V, 16-bit)
│   ├── modbus_soil_sensor.py  # RS-485 토양 수분 센서 (Modbus RTU)
│   └── rtc_manager.py         # RTC 시간 관리 (DS1307 커널드라이버 기반)
│
├── irrigation/                # 관수 제어
│   ├── auto_controller.py     # 자동 관수 컨트롤러 (수동/자동)
│   ├── scheduler.py           # 루틴 스케줄러 (schedule/routine 타입)
│   ├── config_manager.py      # 설정 관리
│   ├── zone_manager.py        # 구역별 관수
│   ├── scenarios.py           # 시나리오 실행
│   └── config/                # 관수 설정 파일
│
├── monitoring/                # 모니터링 & 로깅
│   ├── sensor_monitor.py      # 센서 모니터링 (핵심)
│   ├── data_logger.py         # CSV 데이터 저장
│   ├── alert_manager.py       # 알림 관리 (수위 임계값)
│   └── telegram_notifier.py   # 텔레그램 알림 봇 (v3.3~)
│
├── web/                       # 웹 인터페이스
│   ├── app.py                 # Flask 서버 (v3.6, SocketIO)
│   ├── templates/
│   │   ├── index.html         # 대시보드
│   │   ├── settings.html      # 설정 페이지
│   │   ├── irrigation.html    # 관수 제어 페이지
│   │   └── analytics.html     # 데이터 분석 페이지
│   └── static/
│       ├── css/style.css
│       ├── js/
│       │   ├── dashboard.js
│       │   ├── settings.js
│       │   ├── irrigation.js
│       │   └── font-utils.js
│       └── favicon.svg
│
├── scripts/                   # 유지보수 스크립트
│   ├── fix_bug1_simulation_fallback.sh
│   ├── fix_bug1b_sensor_alert_cooldown.sh
│   ├── fix_bug2_cooldown_sync.sh
│   ├── fix_bug5_thread_watchdog.sh
│   ├── fix_rtc_manager.sh
│   ├── make_docs.sh
│   ├── make_status_note.sh
│   └── update_status.sh
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
└── docs/
    ├── HARDWARE.md
    ├── SETUP.md
    ├── FEATURES.md
    ├── TELEGRAM.md
    ├── API.md
    ├── CHANGELOG.md
    ├── TROUBLESHOOTING.md
    └── STATUS.md
```

---

## 📊 시스템 성능

| 항목 | 수치 |
|------|------|
| 탱크 수위 샘플링 주기 | 10초 (자동) |
| 샘플 개수 | 10회/주기 (Trimmed Mean ±2 제거) |
| 자동 관수 점검 주기 | 설정 가능 (기본 10분) |
| 스케줄 체크 주기 | 10초 |
| Watchdog 체크 주기 | 30초 |
| 인터록 grace window | ±10분 |
| 최대 관수 대기 시간 | 1시간 |
| 관수 구역 수 | 12구역 |
| 토양 센서 수 | 12개 (RS-485 Modbus RTU) |
| 측정 정밀도 | 0.3% (전압 기준) |
| ADC 해상도 | 16-bit (ADS1115) |
| I2C 속도 | 400 kbit/s |
| 수위 경고 쿨다운 | 1시간 (웹 UI 설정 가능, v3.6) |
| 센서 오류 알림 쿨다운 | 30분 |
| 대시보드 업데이트 주기 | 10초 (SocketIO) |
| 텔레그램 폴링 주기 | 3초 |
| 연속 오류 CRITICAL 임계 | 10회 |

---

## 🚀 빠른 시작

```bash
# 서비스 시작
sudo systemctl start smart-farm.service

# 상태 확인
sudo systemctl status smart-farm.service

# 실시간 로그
journalctl -u smart-farm.service -f

# 웹 대시보드 접속
# http://192.168.0.111:5000
```

---

## 📝 개발 로드맵

### ✅ 완료된 Stage

- [x] **Stage 1** — 하드웨어 초기화 (I2C, ADS1115, MCP23017, RTC)
- [x] **Stage 2** — 센서 모니터링 & 웹 대시보드
- [x] **Stage 3** — 캘리브레이션 & 알림 시스템
- [x] **Stage 3.5** — UI 개선 & 릴레이 로직 단순화
- [x] **Stage 4** — RS-485 토양 센서 + 자동 관수 제어
- [x] **Stage 5** — 관수 제어 웹 UI + CSV 다운로드
- [x] **Stage 6** — systemd 자동 시작 + 로그 관리
- [x] **Stage 7** — 데이터 분석 페이지 (analytics.html, Chart.js 줌/팬)
- [x] **Stage 7.5** — 모드 단순화 + 루틴 스케줄러 + 분 단위 UI (v3.0)
- [x] **Stage 7.6** — API 버그 수정 + 센서 드라이버 안정화 + 유지보수 도구 추가 (v3.1~v3.2)
- [x] **Stage 8** — 텔레그램 알림 봇 (자동 알림 + 인라인 키보드 원격 제어) (v3.3)
- [x] **Stage 8.5** — 알림 설정 UI (웹 토글·임계값 저장·토큰 보호·쿨다운 설정) (v3.5~v3.6)
- [x] **Stage 8.6** — 시스템 안정화 (Watchdog, 경로 동적화, 캐시 버스팅, BUG-1~7 전체 수정) (v3.6)

### ⏳ 예정된 Stage

#### Stage 8.7: 운영 편의성
- [ ] 웹 UI 서버 재시작 버튼 (settings.html)
- [ ] 텔레그램 /restart, /status 텍스트 명령 추가

#### Stage 9: 양액 제어 (PWM)
- [ ] EC 기반 양액 농도 자동 조절
- [ ] PWM 펌프 제어

#### Stage 10: 안정성 & 모바일
- [ ] SQLite 데이터베이스 마이그레이션
- [ ] PWA (Progressive Web App)
- [ ] 오프라인 모드 지원

---

## 🛠 기술 스택

| 분류 | 내용 |
|------|------|
| **MCU** | Raspberry Pi 4 |
| **OS** | Raspberry Pi OS (Bookworm) |
| **언어** | Python 3.11 |
| **웹 프레임워크** | Flask 3.x + Flask-SocketIO |
| **프론트엔드** | Vanilla JS + Chart.js |
| **통신** | I2C (400 kHz), RS-485 Modbus RTU |
| **알림** | Telegram Bot API |
| **저장** | CSV (→ SQLite 예정) |
| **서비스** | systemd |

---

## 👤 개발자

- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스

MIT License
