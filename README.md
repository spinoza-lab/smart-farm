# 🌱 스마트 관수 시스템 (Smart Irrigation System)

> **Repository**: [spinoza-lab/smart-farm](https://github.com/spinoza-lab/smart-farm)
> **최종 업데이트**: 2026-03-18
> **버전**: v0.6.8

라즈베리파이 기반 자동 관수 및 수위 모니터링 시스템

---

## 📌 주요 기능
- 🔄 **실시간 센서 모니터링** — 10초 주기 자동 샘플링, Trimmed Mean 정밀 처리
- 💧 **수위 관리** — 탱크1(물), 탱크2(양액) 실시간 모니터링 및 임계값 알림
- ⚙️ **정밀 캘리브레이션** — 소수점 3자리 정밀도 (0.001V 단위), 3중 검증
- 📊 **실시간 대시보드** — WebSocket 기반 10초 자동 갱신
- 🚨 **알림 시스템** — 수위/센서 이상 자동 경고, 쿨다운 웹 UI 설정 가능
- 📈 **데이터 로깅** — SQLite DB 저장 (탱크 수위 + 관수 이력 + 환경 데이터) + CSV 병행 저장
- 🌱 **12구역 자동 관수** — 토양 수분 센서 기반 수동/자동 모드
- 🗓 **루틴 스케줄러** — 요일 기반(schedule) + N일 주기(routine) + 전체구역 일괄 실행
- 🔒 **인터록 처리** — 동시 관수 방지, ±10분 grace window, 최대 1시간 대기
- 🎛️ **관수 제어 웹 UI** — 구역별 게이지, 수동 관수, 임계값 설정, 진행 상태바
- 📥 **CSV 데이터 다운로드** — 탱크 수위·관수 이력·환경 데이터 기간별 내보내기
- 🔧 **systemd 자동 시작** — 부팅 시 자동 실행 및 로그 관리
- 📊 **데이터 분석 페이지** — 탱크 수위 트렌드, 관수 효율, 구역별 통계, 환경 시계열 차트 (Chart.js 줌/팬)
- 🤖 **텔레그램 알림 봇** — 서버 시작·관수 시작/완료·수위 경고 자동 알림 + 인라인 키보드 원격 제어
- 🛡️ **알림 설정 안정성** — notifications.json 손상 방지, 토큰 보호, 원자적 파일 저장
- 🐕 **Watchdog 스레드** — periodic_data_sender 자동 재시작, 30초 내 복구
- 🗂️ **동적 경로 처리** — _BASE_DIR 기반으로 어디서든 실행 가능
- ⚡ **JS/CSS 캐시 버스팅** — 서버 시작 타임스탬프 자동 적용
- 🏗️ **Blueprint 아키텍처** — Flask Blueprint 6개 분리, slim entry point
- 🔁 **관수 주기 관리** — 구역별 최소/최대 관수 간격, 재시작 후 CSV 복원
- 🔋 **I2C 장애 내성** — 재시도 2회 + fallback + 연속 오류 단계별 알림
- 🌡️ **대기 환경 모니터링** — SHT30 ×12 구역별 온·습도 + WH65LP 기상 관측소 (v0.5.0)
- 🗄️ **SQLite 데이터베이스** — CSV → SQLite 마이그레이션, 인덱스 기반 고속 조회 (v0.6.0)
- 📱 **반응형 UI** — PC 중앙정렬(container-xxl) + 모바일 햄버거 메뉴 (v0.6.8)

---

## 📚 문서
| 문서 | 내용 |
|------|------|
| [🛠 하드웨어 구성](docs/HARDWARE.md) | 부품 목록, I2C 주소, 릴레이 구성 |
| [🚀 설치 가이드](docs/SETUP.md) | 환경 설정, 의존성, 텔레그램 봇 설정, VS Code SSH |
| [🌱 시스템 기능](docs/FEATURES.md) | 관수 제어, 센서 모니터링, 웹 인터페이스 상세 |
| [🤖 텔레그램 봇](docs/TELEGRAM.md) | 자동 알림, 인라인 메뉴, 설정 안정성 |
| [🔌 API 레퍼런스](docs/API.md) | 전체 API 엔드포인트 목록 |
| [📝 변경 이력](docs/CHANGELOG.md) | 버전별 업데이트 내용 |
| [🔧 트러블슈팅](docs/TROUBLESHOOTING.md) | 자주 발생하는 오류 및 해결법 |
| [📋 프로젝트 현황](docs/STATUS.md) | 버그 현황, 커밋 이력, 작업 노트 |

---

## 🏗 프로젝트 구조
```
smart_farm/
├── hardware/
│   ├── sensor_reader.py           # ADS1115 (재시도+fallback)
│   ├── relay_controller.py
│   ├── modbus_soil_sensor.py
│   ├── rtc_manager.py
│   ├── air_sensor_reader.py       # SHT30 ×12 Modbus RTU (v0.5.0)
│   └── weather_station_reader.py  # WH65LP 25바이트 파서 (v0.5.0)
├── irrigation/
│   ├── auto_controller.py
│   ├── scheduler.py
│   ├── config_manager.py
│   └── zone_manager.py
├── monitoring/
│   ├── sensor_monitor.py
│   ├── data_logger.py             # SQLite + CSV 병행 저장 (v0.6.0)
│   ├── alert_manager.py
│   ├── telegram_notifier.py
│   └── environment_monitor.py     # 환경 모니터링 스레드 (v0.5.0, SQLite 지원 v0.6.0)
├── database/                      # (v0.6.0 신규)
│   ├── __init__.py
│   ├── db_manager.py              # SQLite CRUD 매니저 (5개 테이블)
│   └── migrate_csv_to_db.py       # 기존 CSV → SQLite 마이그레이션
├── web/
│   ├── app.py
│   ├── globals.py
│   ├── blueprints/
│   │   ├── monitoring_bp.py
│   │   ├── irrigation_bp.py
│   │   ├── analytics_bp.py        # SQLite 쿼리 우선 (v0.6.0)
│   │   ├── notifications_bp.py
│   │   ├── download_bp.py         # air/weather CSV 다운로드 (v0.6.4)
│   │   └── environment_bp.py      # 환경 API (v0.5.0)
│   ├── templates/                 # 반응형 UI (container-xxl + 햄버거, v0.6.8)
│   └── static/
├── config/
│   ├── version.json               # 버전 중앙 관리 (v0.6.2)
│   └── notifications.json         # cooldowns 섹션 추가 (v0.6.2)
├── data/
│   ├── smart_farm.db              # SQLite DB (v0.6.0)
│   ├── air_sensor_logs/           # SHT30 CSV 백업
│   └── weather_logs/              # WH65LP CSV 백업
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
| 유효 샘플 최소치 | 5회 |
| I2C 재시도 횟수 | 2회 / 50ms |
| 자동 관수 점검 주기 | 설정 가능 (기본 5분) |
| 스케줄 체크 주기 | 10초 |
| Watchdog 체크 주기 | 30초 |
| 관수 구역 수 | 12구역 + 전체구역 일괄 지원 |
| 토양 센서 수 | 12개 (RS-485 Modbus RTU) |
| 대시보드 업데이트 주기 | 10초 (SocketIO) |
| 텔레그램 폴링 주기 | 3초 |
| SHT30 폴링 주기 | 60초 |
| WH65LP 수신 주기 | 16초 (자동 송출) |
| SQLite DB 크기 | ~11MB (99,162행 기준) |

---

## 🚀 빠른 시작
```bash
sudo systemctl start smart-farm.service
sudo systemctl status smart-farm.service
journalctl -u smart-farm.service -f
# 로컬: http://192.168.0.111:5000
# 외부: http://spinozadev.iptime.org:15000
```

---

## 📝 개발 로드맵

### ✅ 완료된 Stage
- [x] Stage 1~8.6 — 하드웨어 초기화 ~ 시스템 안정화
- [x] **Stage 8.7** — 텔레그램 /restart·/status, 웹 UI 서버 재시작 버튼 (v0.3.7)
- [x] **Stage 9** — 관수 주기 관리 시스템 (v0.4.0)
- [x] **Stage 9.1** — Blueprint 리팩터링 + I2C 장애 내성 (v0.4.1)
- [x] **Stage 10** — 대기 환경 모니터링 SHT30×12 + WH65LP (v0.5.0)
- [x] **Stage 11** — SQLite 마이그레이션 (v0.6.0)
- [x] **Stage 13** — 설정 통합 (config/version.json + cooldowns) (v0.6.2)
- [x] **Stage 14** — BUG-18 수정 + 환경 시계열 차트 (v0.6.3)
- [x] **Stage 14b** — 분석 그래프 기간 범위 + 트리거 표시 + 환경 CSV (v0.6.4)
- [x] **Stage 14c** — 코드 패치 묶음 (v0.6.5)
- [x] **Stage 14d/14e** — 네비바 폰트버튼 삽입 (4개 템플릿) (v0.6.6~v0.6.7)
- [x] **Stage 14f** — PC 중앙정렬(container-xxl) + 모바일 햄버거 네비바 (v0.6.8)

### ⏳ 예정된 작업
- [ ] **쿨다운 설정 완전 단일화** — AlertManager/SensorMonitor/AutoController 쿨다운 단일 config 키 통합
- [ ] **sensor_voltage_thresholds 외부화** — 0.1V/3.2V 하드코딩 → notifications.json으로 이동
- [ ] **대시보드 센서 오류 UI 배지** — 채널별 오류 상태 시각화
- [ ] **Stage 10 하드웨어 연결** — SHT30·WH65LP 수령 후 simulation_mode=false 전환
- [ ] **alerts 테이블 연동** — AlertManager 알림 발생 시 SQLite alerts 테이블에 저장
- [ ] **DB 자동 정리 스케줄러** — 오래된 데이터 자동 삭제/아카이브

---

## 🛠 기술 스택
| 분류 | 내용 |
|------|------|
| **MCU** | Raspberry Pi 4 |
| **OS** | Raspberry Pi OS (Bookworm) |
| **언어** | Python 3.11 |
| **웹 프레임워크** | Flask 3.x + Flask-SocketIO + Blueprint |
| **프론트엔드** | Vanilla JS + Chart.js + Bootstrap 5 |
| **통신** | I2C (400 kHz), RS-485 Modbus RTU |
| **알림** | Telegram Bot API |
| **저장** | SQLite (주) + CSV (백업) |
| **서비스** | systemd |

---

## 👤 개발자
- GitHub: [@spinoza-lab](https://github.com/spinoza-lab)

## 📄 라이선스
MIT License
