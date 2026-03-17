# 📋 Smart Farm 프로젝트 현황 노트

> 최종 업데이트: 2026-03-17
> 버전: v0.6.0 (Stage 11: SQLite 마이그레이션 완료)
> 작업 세션 간 컨텍스트 유지를 위한 내부 노트

---

## ✅ 전체 완료 작업 목록

### v0.6.0 신규 완료 (2026-03-17)
| ID | 내용 | 파일 |
|---|---|---|
| Stage 11 | SQLite DBManager 구현 (5개 테이블, WAL 모드, 인덱스) | `database/db_manager.py` |
| Stage 11 | CSV → SQLite 1회 마이그레이션 스크립트 | `database/migrate_csv_to_db.py` |
| Stage 11 | DataLogger SQLite 병행 저장 지원 | `monitoring/data_logger.py` |
| Stage 11 | EnvironmentMonitor SQLite 병행 저장 지원 | `monitoring/environment_monitor.py` |
| Stage 11 | analytics_bp SQLite 쿼리 우선 + CSV 폴백 | `web/blueprints/analytics_bp.py` |
| Stage 11 | globals.py db_manager 전역 변수 추가 | `web/globals.py` |
| Stage 11 | app.py DBManager 초기화 + 파라미터 전달 | `web/app.py` |
| Stage 11 | 신규 API: /api/analytics/environment, /api/analytics/db-info | `web/blueprints/analytics_bp.py` |

### v0.5.0 완료 (2026-03-17)
| ID | 내용 | 파일 |
|---|---|---|
| Stage 10 | SHT30 × 12 Modbus RTU 드라이버 구현 | `hardware/air_sensor_reader.py` |
| Stage 10 | WH65LP 25바이트 커스텀 패킷 파서 구현 | `hardware/weather_station_reader.py` |
| Stage 10 | 환경 모니터링 백그라운드 스레드 | `monitoring/environment_monitor.py` |
| Stage 10 | 환경 REST API Blueprint (6 엔드포인트) | `web/blueprints/environment_bp.py` |
| Stage 10 | 대시보드 환경 모니터링 탭 추가 | `web/templates/index.html` |
| Stage 10 | 분석 페이지 환경 데이터 탭 추가 | `web/templates/analytics.html` |
| Stage 10 | 대시보드 JS 백그라운드 폴링 추가 | `web/static/js/dashboard.js` |

### v0.4.1 완료 (2026-03-09)
| ID | 내용 | 파일 | 커밋 |
|---|---|---|---|
| Refactor | Blueprint 분리 (app.py → 5개 bp) | web/blueprints/*.py | 592fa92 |
| BUG-FIX-TN | auto_controller telegram_notifier 탐색 실패 | web/app.py | 19fa53b |
| BUG-FIX-Z0 | zone_id=0 저장/실행/표시 불가 | irrigation_bp.py 외 | 846b47c |
| BUG-14 P0~P2 | I2C 재시도+fallback+오류통계+UI | sensor_reader.py 외 | a299b82 |

---

## 🔌 REST API 전체 목록 (v0.6.0 기준)

### 환경 모니터링 (v0.5.0)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/environment` | 전체 환경 데이터 (공기 + 기상) |
| GET | `/api/environment/air` | 전체 SHT30 센서 데이터 |
| GET | `/api/environment/air/<id>` | 특정 구역 SHT30 데이터 |
| GET | `/api/environment/weather` | WH65LP 기상 데이터 |
| GET | `/api/environment/history/air` | 대기 센서 이력 (최근 100 스냅샷) |
| GET | `/api/environment/history/weather` | 기상 이력 (최근 100 스냅샷) |

### 분석 (v0.6.0 업데이트)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/analytics/sensor-data` | 탱크 센서 데이터 (SQLite 우선) |
| GET | `/api/analytics/irrigation-history` | 관수 이력 (SQLite 우선) |
| GET | `/api/analytics/environment` | 환경 데이터 분석 (신규, SQLite) |
| GET | `/api/analytics/db-info` | DB 상태 확인 (신규) |

---

## 🗄️ SQLite DB 구조 (v0.6.0)

**파일 경로**: `data/smart_farm.db`

| 테이블 | 행 수 (2026-03-17) | 설명 |
|--------|------------------|------|
| sensor_readings | ~94,946 | 탱크 수위 + ADS1115 전압 |
| air_sensor_readings | ~3,120 | SHT30 ×12 구역별 온·습도 |
| weather_readings | ~967 | WH65LP 기상 관측소 |
| irrigation_history | 215 | 관수 이력 |
| alerts | 0 | 알림 이력 (향후 연동 예정) |

```bash
# DB 상태 확인
curl -s http://localhost:5000/api/analytics/db-info | python3 -m json.tool
```

---

## 🟡 미완료 / 진행 예정

### 🔴 버그 수정 필요
| 항목 | 설명 |
|------|------|
| **분석 페이지 기간 조회 오동작** | SQLite 연동 후 date range 필터가 정상 작동하지 않음. analytics_bp.py 쿼리 파라미터 확인 필요 |

### 🟠 추후 작업 예정
| 항목 | 우선순위 | 설명 |
|------|---------|------|
| **버전 관리 일원화** | 🟠 중간 | `config/version.json` 도입 → app.py, 대시보드, API 등 버전 표기 전체 통합 |
| 환경 데이터 시계열 차트 | 🟡 낮음 | 분석 페이지에 Air/Weather 기간별 그래프 추가 (현재 스냅샷만) |
| alerts 테이블 연동 | 🟡 낮음 | AlertManager 알림 발생 시 SQLite alerts 테이블에 저장 |
| DB 자동 정리 스케줄러 | 🟡 낮음 | 오래된 데이터 자동 삭제 / 아카이브 기능 |
| 쿨다운 설정 완전 단일화 | 🟠 중간 | AlertManager/AutoController 쿨다운 단일 config 키 통합 |
| sensor_voltage_thresholds | 🟠 중간 | 0.1V/3.2V 하드코딩 → notifications.json으로 이동 |

### Stage 10 하드웨어 연결 (하드웨어 수령 후)
| 항목 | 설명 |
|------|------|
| SHT30 실센서 연결 | `simulation_mode: false` 전환 + /dev/ttyAMA2 배선 |
| WH65LP 실센서 연결 | `simulation_mode: false` 전환 + /dev/ttyAMA3 배선 |
| UART 오버레이 활성화 | `/boot/firmware/config.txt` dtoverlay=uart3/uart4 추가 후 재부팅 |
| MAX485 #2/#3 연결 | Bus 2 (GPIO4/5/17), Bus 3 (GPIO8/9/GND) 배선 |

---

## 🔖 커밋 이력 (최신순, v0.6.0 기준)
| 해시 | 내용 |
|------|------|
| *(예정)* | feat(Stage11): SQLite 마이그레이션 (DBManager + 병행저장) v0.6.0 |
| `befc14d` | feat(Stage10): 대기 환경 모니터링 추가 (SHT30×12 + WH65LP) v0.5.0 |
| `592a6ba` | feat(api): /api/status sensor_errors·sensor_stats 추가 (BUG-14 P2) |
| `bd831c1` | fix(alert): None 전압 허용 + 연속 오류 카운터 + 복구 감지 (BUG-14 P1) |
| `592fa92` | refactor: Blueprint 분리 (web/app.py → 5개 blueprint) |
| `32d76d5` | feat(S9): 관수 주기 관리 시스템 구현 |

---

## 🔩 하드웨어 현황 (2026-03-17 기준)
| 부품 | 상태 | 비고 |
|------|------|------|
| Raspberry Pi 4 | ✅ 정상 | 메인 컨트롤러 |
| MCP23017 #1 (0x20) | ✅ 정상 | GPIO 확장 #1 |
| MCP23017 #2 (0x21) | ✅ 정상 | GPIO 확장 #2 |
| ADS1115 (0x48) | ✅ 정상 | 수위 전압 ADC |
| DS1307 RTC (0x68) | ✅ 정상 | 커널 드라이버 등록 완료 |
| RS-485 토양 센서 x12 | ⚠️ 미연결 | simulation_mode=false, 연결 시 즉시 동작 |
| QDY30A 수위 센서 x2 | ⚠️ 미연결 | 전압 분배 회로 구성 후 연결 예정 |
| 6채널 릴레이 보드 x4 (24ch) | ⚠️ 미연결 | 외부 5V 전원 연결 후 배선 예정 |
| MAX485 모듈 #1 | ⚠️ 미연결 | RS-485 Bus 1 (토양 센서) |
| MAX485 모듈 #2 | 🛒 구매 필요 | RS-485 Bus 2 (대기 온습도) |
| MAX485 모듈 #3 | 🛒 구매 필요 | RS-485 Bus 3 (기상 스테이션) |
| RD-125B (5V+24V SMPS) | ✅ 구매 완료 | 릴레이+센서 전원 통합 |
| AC 24V 트랜스 25W | ✅ 구매 완료 | 전자밸브 전원 |
| AC 24V 전자밸브 | ✅ 보유 | 구역밸브 12+기타 |
| 한일펌프 PA-1688SS | ✅ 보유 | 220V 2HP 자흡식 |
| SSR 40A + 방열판 | 🛒 구매 예정 | 펌프 제어용 |
| 10kΩ 저항 x4 | 🛒 필요 | 수위 센서 전압 분배 |
| 120Ω 종단저항 x4 | 🛒 필요 | RS-485 Bus 양끝 종단 |
| **CDSENET EID041-G01 (SHT30) x12** | **📦 배송 중** | **대기 온습도 RS-485 Modbus, 소프트웨어 완료** |
| **MISOL WH65LP** | **📦 배송 중** | **기상 스테이션 RS-485, 소프트웨어 완료** |

---

## ⚙️ 현재 설정값
| 항목 | 값 | 파일 |
|------|-----|------|
| 수위 경고 쿨다운 | 3600초 (1시간) | config/notifications.json |
| 탱크1 (물탱크) 임계값 | 20% ~ 90% | config/notifications.json |
| 탱크2 (양액탱크) 임계값 | 20% ~ 90% | config/notifications.json |
| 자동관수 점검 주기 | 300초 | config/soil_sensors.json |
| 센서 샘플 개수 | 10회 (Trimmed Mean ±2) | monitoring/sensor_monitor.py |
| watchdog 체크 주기 | 30초 | web/app.py |
| SHT30 폴링 주기 | 60초 | monitoring/environment_monitor.py |
| WH65LP 수신 주기 | 16초 (자동 송출) | monitoring/environment_monitor.py |
| SHT30 simulation_mode | true (하드웨어 수령 전) | config/air_sensors.json |
| WH65LP simulation_mode | true (하드웨어 수령 전) | config/weather_station.json |
| SQLite DB 경로 | data/smart_farm.db | database/db_manager.py |

---

## 📜 주요 명령어
```bash
# 서비스 관리
sudo systemctl restart smart-farm.service
sudo systemctl status smart-farm.service
journalctl -u smart-farm.service -f
journalctl -u smart-farm.service -n 50 --no-pager

# 가상환경
source /home/pi/smart_farm_env/bin/activate

# API 확인
curl -s http://localhost:5000/api/status | python3 -m json.tool
curl -s http://localhost:5000/api/environment | python3 -m json.tool
curl -s http://localhost:5000/api/analytics/db-info | python3 -m json.tool

# DB 직접 확인
sqlite3 ~/smart_farm/data/smart_farm.db ".tables"
sqlite3 ~/smart_farm/data/smart_farm.db "SELECT COUNT(*) FROM sensor_readings;"

# simulation_mode 해제 (하드웨어 수령 후)
python3 -c "
import json
for f in ['config/air_sensors.json','config/weather_station.json']:
    d = json.load(open(f)); d['simulation_mode']=False
    json.dump(d, open(f,'w'), indent=4, ensure_ascii=False)
    print(f'✅ {f} → simulation_mode: false')
"
```

---

*이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다.*
