# 📋 Smart Farm 프로젝트 현황 노트

> 최종 업데이트: 2026-03-18
> 버전: v0.6.8 (Stage 14f: 반응형 UI 완료)
> 작업 세션 간 컨텍스트 유지를 위한 내부 노트

---

## ✅ 전체 완료 작업 목록

### v0.6.8 신규 완료 (2026-03-18) — Stage 14f
| ID | 내용 | 파일 |
|---|---|---|
| Stage 14f | PC 레이아웃 container-xxl 적용 (4개 템플릿) | `web/templates/*.html` |
| Stage 14f | 모바일 햄버거 메뉴 네비바 구현 | `web/templates/*.html` |
| Stage 14e | 네비바 폰트 버튼 4개 페이지 삽입 (fix_navbar_remaining.py) | `web/templates/*.html` |
| Stage 14e | 패턴 미스매치 수정 (fix_navbar_index_settings.py) | `web/templates/index.html`, `settings.html` |

### v0.6.5~v0.6.7 완료 (2026-03-18) — Stage 14c~14e
| ID | 내용 | 파일 |
|---|---|---|
| Stage 14c | trigger_type 정합성 개선 | `web/blueprints/analytics_bp.py` |
| Stage 14d | 네비바 폰트버튼 삽입 (analytics.html 기준) | `web/templates/analytics.html` |

### v0.6.4 완료 (2026-03-18) — Stage 14b
| ID | 내용 | 파일 |
|---|---|---|
| Stage 14b | 분석 그래프 기간 범위 동적 limit 계산 | `web/blueprints/analytics_bp.py` |
| Stage 14b | TRIGGER_MAP + 동적 도넛 차트 + 트리거 필터 | `web/static/js/analytics.js` |
| Stage 14b | 환경 시뮬레이션 뱃지 + CSV 다운로드 버튼 | `web/templates/analytics.html` |
| Stage 14b | trigger-stats 진단 API 신규 | `web/blueprints/analytics_bp.py` |
| Stage 14b | air-data / weather-data CSV 다운로드 API | `web/blueprints/download_bp.py` |

### v0.6.3 완료 (2026-03-17) — Stage 14
| ID | 내용 | 파일 |
|---|---|---|
| BUG-18 | 관수 이력 컬럼명 불일치 수정 | `web/static/js/analytics.js` |
| Stage 14 | 환경 데이터 시계열 차트 3종 추가 | `web/templates/analytics.html` |

### v0.6.2 완료 (2026-03-17) — Stage 13
| ID | 내용 | 파일 |
|---|---|---|
| Stage 13 | config/version.json 신규 (버전 중앙화) | `config/version.json` |
| Stage 13 | notifications.json cooldowns 섹션 추가 | `config/notifications.json` |
| Stage 13 | app.py 버전 동적 로드 | `web/app.py` |

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

## 🔌 REST API 전체 목록 (v0.6.8 기준)

### 환경 모니터링 (v0.5.0)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/environment` | 전체 환경 데이터 (공기 + 기상) |
| GET | `/api/environment/air` | 전체 SHT30 센서 데이터 |
| GET | `/api/environment/air/<id>` | 특정 구역 SHT30 데이터 |
| GET | `/api/environment/weather` | WH65LP 기상 데이터 |
| GET | `/api/environment/history/air` | 대기 센서 이력 (최근 100 스냅샷) |
| GET | `/api/environment/history/weather` | 기상 이력 (최근 100 스냅샷) |

### 분석 (v0.6.4 업데이트)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/analytics/sensor-data` | 탱크 센서 데이터 (SQLite 우선, 동적 limit) |
| GET | `/api/analytics/irrigation-history` | 관수 이력 (SQLite 우선) |
| GET | `/api/analytics/environment` | 환경 데이터 분석 (신규, SQLite) |
| GET | `/api/analytics/db-info` | DB 상태 확인 |
| GET | `/api/analytics/trigger-stats` | 트리거 유형별 건수 (진단용, v0.6.4 신규) |

### CSV 다운로드 (v0.6.4 업데이트)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/download/irrigation-history` | 관수 이력 CSV |
| GET | `/api/download/sensor-data` | 탱크 수위 CSV |
| GET | `/api/download/air-data` | SHT30 대기 센서 CSV (v0.6.4 신규) |
| GET | `/api/download/weather-data` | WH65LP 기상 데이터 CSV (v0.6.4 신규) |

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

### 🟠 기술 부채 (Technical Debt)
| 항목 | 우선순위 | 예상 소요 | 설명 |
|------|---------|---------|------|
| **쿨다운 설정 완전 단일화** | 🟠 중간 | ~30분 | AlertManager/SensorMonitor/AutoController 쿨다운 단일 config 키 통합 |
| **sensor_voltage_thresholds 외부화** | 🟠 중간 | ~20분 | 0.1V/3.2V 하드코딩 → notifications.json으로 이동 |
| **대시보드 센서 오류 UI 배지** | 🟠 중간 | ~1시간 | 채널별 오류 상태 시각화 |
| **trigger_type 네이밍 완전 정합** | 🟡 낮음 | ~30분 | `schedule`/`scheduler` 혼용 완전 해소 |

### Stage 10 하드웨어 연결 (하드웨어 수령 후)
| 항목 | 설명 |
|------|------|
| SHT30 실센서 연결 | `simulation_mode: false` 전환 + /dev/ttyAMA2 배선 |
| WH65LP 실센서 연결 | `simulation_mode: false` 전환 + /dev/ttyAMA3 배선 |
| UART 오버레이 활성화 | `/boot/firmware/config.txt` dtoverlay=uart3/uart4 추가 후 재부팅 |
| MAX485 #2/#3 연결 | Bus 2 (GPIO4/5/17), Bus 3 (GPIO8/9/GND) 배선 |

### 장기 개선 항목
| 항목 | 설명 |
|------|------|
| alerts 테이블 연동 | AlertManager 알림 발생 시 SQLite alerts 테이블에 저장 |
| DB 자동 정리 스케줄러 | 오래된 데이터 자동 삭제/아카이브 기능 |
| PWA 오프라인 캐싱 | 홈 화면 아이콘 + 오프라인 접근 지원 |

---

## 🔖 커밋 이력 (최신순, v0.6.8 기준)
| 해시 | 태그 | 내용 |
|------|------|------|
| *(예정)* | v0.6.8 | fix(Stage14f): PC 중앙정렬(container-xxl) + 모바일 햄버거 네비바 |
| *(예정)* | v0.6.6 | fix(Stage14e): 네비바 폰트버튼 삽입 (4개 템플릿) |
| *(예정)* | v0.6.4 | fix(Stage14b): 분석 기간 범위 + 트리거 표시 + 환경 CSV |
| *(예정)* | v0.6.3 | feat(Stage14): BUG-18 수정 + 환경 시계열 차트 |
| *(예정)* | v0.6.2 | feat(Stage13): config/version.json + cooldowns 통합 |
| `befc14d` | v0.5.0 | feat(Stage10): 대기 환경 모니터링 추가 (SHT30×12 + WH65LP) |
| `592a6ba` | — | feat(api): /api/status sensor_errors·sensor_stats 추가 (BUG-14 P2) |
| `bd831c1` | — | fix(alert): None 전압 허용 + 연속 오류 카운터 + 복구 감지 (BUG-14 P1) |
| `592fa92` | v0.4.1 | refactor: Blueprint 분리 (web/app.py → 5개 blueprint) |
| `32d76d5` | v0.4.0 | feat(S9): 관수 주기 관리 시스템 구현 |

---

## 🔩 하드웨어 현황 (2026-03-18 기준)
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
| 앱 버전 소스 | config/version.json | web/app.py (_load_version) |
| 네비바 레이아웃 | container-xxl + 햄버거 (Bootstrap 5) | web/templates/*.html |
| 외부 접근 URL | http://spinozadev.iptime.org:15000 | 공유기 포트포워딩 설정 |

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
curl -s http://localhost:5000/api/analytics/trigger-stats | python3 -m json.tool

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

# 현재 버전 확인
cat config/version.json
```

---

*이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다.*
