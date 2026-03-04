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
