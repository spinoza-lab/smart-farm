# 🌱 스마트 관수 시스템 (Smart Irrigation System)

> **Repository**: [spinoza-lab/smart-farm](https://github.com/spinoza-lab/smart-farm)
> **최종 업데이트**: 2026-03-17
> **버전**: v0.5.0

라즈베리파이 기반 자동 관수 및 수위 모니터링 시스템

---

## 📌 주요 기능
- 🔄 **실시간 센서 모니터링** — 10초 주기 자동 샘플링, Trimmed Mean 정밀 처리
- 💧 **수위 관리** — 탱크1(물), 탱크2(양액) 실시간 모니터링 및 임계값 알림
- ⚙️ **정밀 캘리브레이션** — 소수점 3자리 정밀도 (0.001V 단위), 3중 검증
- 📊 **실시간 대시보드** — WebSocket 기반 10초 자동 갱신
- 🚨 **알림 시스템** — 수위/센서 이상 자동 경고, 쿨다운 웹 UI 설정 가능
- 📈 **데이터 로깅** — CSV 형식 자동 저장 (탱크 수위 + 관수 이력)
- 🌱 **12구역 자동 관수** — 토양 수분 센서 기반 수동/자동 모드
- 🗓 **루틴 스케줄러** — 요일 기반(schedule) + N일 주기(routine) + 전체구역 일괄 실행
- 🔒 **인터록 처리** — 동시 관수 방지, ±10분 grace window, 최대 1시간 대기
- 🎛️ **관수 제어 웹 UI** — 구역별 게이지, 수동 관수, 임계값 설정, 진행 상태바
- 📥 **CSV 데이터 다운로드** — 탱크 수위·관수 이력 기간별 내보내기
- 🔧 **systemd 자동 시작** — 부팅 시 자동 실행 및 로그 관리
- 📊 **데이터 분석 페이지** — 탱크 수위 트렌드, 관수 효율, 구역별 통계, 환경 데이터 (Chart.js 줌/팬)
- 🤖 **텔레그램 알림 봇** — 서버 시작·관수 시작/완료·수위 경고 자동 알림 + 인라인 키보드 원격 제어
- 🛡️ **알림 설정 안정성** — notifications.json 손상 방지, 토큰 보호, 원자적 파일 저장
- 🐕 **Watchdog 스레드** — periodic_data_sender 자동 재시작, 30초 내 복구
- 🗂️ **동적 경로 처리** — _BASE_DIR 기반으로 어디서든 실행 가능
- ⚡ **JS/CSS 캐시 버스팅** — 서버 시작 타임스탬프 자동 적용
- 🏗️ **Blueprint 아키텍처** — Flask Blueprint 6개 분리, slim entry point (v0.4.1+)
- 🔁 **관수 주기 관리** — 구역별 최소/최대 관수 간격, 재시작 후 CSV 복원 (v0.4.0)
- 🔋 **I2C 장애 내성** — 재시도 2회 + fallback + 연속 오류 단계별 알림 (v0.4.1)
- 🌡️ **대기 환경 모니터링** — SHT30 × 12 구역별 온습도 + WH65LP 기상 스테이션 (v0.5.0)

---

## 📚 문서
| 문서 | 내용 |
|------|------|
| [🛠 하드웨어 구성](docs/HARDWARE.md) | 부품 목록, I2C 주소, 릴레이 구성, RS-485 버스 배선 |
| [🚀 설치 가이드](docs/SETUP.md) | 환경 설정, 의존성, 텔레그램 봇 설정, VS Code SSH |
| [🌱 시스템 기능](docs/FEATURES.md) | 관수 제어, 센서 모니터링, 웹 인터페이스 상세 |
| [🤖 텔레그램 봇](docs/TELEGRAM.md) | 자동 알림, 인라인 메뉴, 설정 안정성 |
| [🔌 API 레퍼런스](docs/API.md) | 전체 API 엔드포인트 목록 |
| [📝 변경 이력](docs/CHANGELOG.md) | 버전별 업데이트 내용 (v0.2.0~v0.5.0) |
| [🔧 트러블슈팅](docs/TROUBLESHOOTING.md) | 자주 발생하는 오류 및 해결법 |
| [📋 프로젝트 현황](docs/STATUS.md) | 버그 현황, 커밋 이력, 작업 노트 |

---

## 🏗 프로젝트 구조
```
smart_farm/
├── hardware/
│   ├── sensor_reader.py           # ADS1115 (재시도+fallback, v0.4.1)
│   ├── relay_controller.py
│   ├── modbus_soil_sensor.py
│   ├── rtc_manager.py
│   ├── air_sensor_reader.py       # SHT30 Modbus RTU 드라이버 (v0.5.0 신규)
│   └── weather_station_reader.py  # WH65LP 25바이트 파서 (v0.5.0 신규)
├── irrigation/
│   ├── auto_controller.py
│   ├── scheduler.py               # 전체구역(zone_id=0) 지원 (v0.4.1)
│   ├── config_manager.py
│   └── zone_manager.py
├── monitoring/
│   ├── sensor_monitor.py          # None 필터링 + SensorReadError (v0.4.1)
│   ├── data_logger.py
│   ├── alert_manager.py           # 연속 오류 카운터 + 복구 감지 (v0.4.1)
│   ├── telegram_notifier.py
│   └── environment_monitor.py     # 환경 모니터링 스레드 (v0.5.0 신규)
├── web/
│   ├── app.py                     # slim entry point (v0.4.1)
│   ├── globals.py                 # 공유 전역 변수 (v0.5.0 확장)
│   ├── blueprints/                # (v0.4.1+)
│   │   ├── monitoring_bp.py
│   │   ├── irrigation_bp.py
│   │   ├── analytics_bp.py
│   │   ├── notifications_bp.py
│   │   ├── download_bp.py
│   │   └── environment_bp.py      # 환경 API Blueprint (v0.5.0 신규)
│   ├── templates/
│   └── static/
├── config/
│   ├── air_sensors.json           # SHT30 설정 (v0.5.0 신규)
│   └── weather_station.json       # WH65LP 설정 (v0.5.0 신규)
├── docs/
├── logs/
├── scripts/
└── tools/
```

---

## 📊 시스템 성능
| 항목 | 수치 |
|------|------|
| 탱크 수위 샘플링 주기 | 10초 |
| 샘플 개수 | 10회/주기 (Trimmed Mean ±2 제거) |
| 유효 샘플 최소치 | 5회 (v0.4.1) |
| I2C 재시도 횟수 | 2회 / 50ms (v0.4.1) |
| 자동 관수 점검 주기 | 설정 가능 (기본 5분) |
| 스케줄 체크 주기 | 10초 |
| Watchdog 체크 주기 | 30초 |
| 관수 구역 수 | 12구역 + 전체구역 일괄 지원 (v0.4.1) |
| 토양 센서 수 | 12개 (RS-485 Modbus RTU) |
| 대기 온습도 센서 수 | 12개 (SHT30, RS-485 Modbus RTU, v0.5.0) |
| 기상 스테이션 | 1개 (WH65LP, RS-485, 16초 자동 송출, v0.5.0) |
| 환경 모니터링 갱신 주기 | SHT30 60초 / WH65LP 16초 (v0.5.0) |
| 센서 오류 연속 CRITICAL 임계 | 5회 (v0.4.1) |
| 대시보드 업데이트 주기 | 10초 (SocketIO) |
| 텔레그램 폴링 주기 | 3초 |

---

## 🚀 빠른 시작
```bash
sudo systemctl start smart-farm.service
sudo systemctl status smart-farm.service
journalctl -u smart-farm.service -f
# http://192.168.0.111:5000
```

---

## 📝 개발 로드맵

### ✅ 완료된 Stage
- [x] Stage 1~8.6 — 하드웨어 초기화 ~ 시스템 안정화
- [x] **Stage 8.7** — 텔레그램 /restart·/status, 웹 UI 서버 재시작 버튼 (v0.3.7)
- [x] **Stage 9** — 관수 주기 관리 시스템 (v0.4.0)
- [x] **Stage 9.1** — Blueprint 리팩터링 + I2C 장애 내성 (v0.4.1)
- [x] **Stage 10** — 대기 환경 모니터링 소프트웨어 구현 (v0.5.0)
  - SHT30 × 12 Modbus RTU 드라이버
  - WH65LP 25바이트 커스텀 패킷 파서
  - 환경 모니터링 백그라운드 스레드
  - REST API `/api/environment/*` (6개 엔드포인트)
  - 대시보드 환경 모니터링 탭 (기상 카드 + SHT30 구역 그리드)
  - 분석 페이지 환경 데이터 탭 (요약 카드 + 스냅샷 테이블)

### ⏳ 예정된 Stage
- [ ] **Stage 10 하드웨어** — SHT30/WH65LP 실물 연결 및 실센서 검증 (하드웨어 수령 후)
- [ ] **Stage 11** — SQLite 마이그레이션 + 환경 데이터 이력 차트

---

## 🛠 기술 스택
| 분류 | 내용 |
|------|------|
| **MCU** | Raspberry Pi 4 |
| **OS** | Raspberry Pi OS (Bookworm) |
| **언어** | Python 3.11 |
| **웹 프레임워크** | Flask 3.x + Flask-SocketIO + Blueprint (v0.4.1) |
| **프론트엔드** | Vanilla JS + Chart.js + Bootstrap 5 |
| **통신** | I2C (400 kHz), RS-485 Modbus RTU, RS-485 커스텀 프로토콜 |
| **알림** | Telegram Bot API |
| **저장** | CSV (→ SQLite 예정) |
| **서비스** | systemd |

---

## 👤 개발자
- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스
MIT License
