## v0.6.3 — Stage 14: BUG-18 수정 + 환경 데이터 시계열 차트 (2026-03-17)

### 🐛 BUG-18 수정: 관수 이력 렌더링 컬럼명 불일치

`analytics.js`가 SQLite `irrigation_history` 테이블의 실제 컬럼명과 다른 키를 참조하여
관수 트리거 비율·원시 로그·구역별 성공률이 전혀 표시되지 않는 문제 수정.

| 잘못된 참조 | 수정 후 | 비고 |
|---|---|---|
| `r.trigger` | `r.trigger_type \|\| r.trigger` | CSV 폴백 호환 유지 |
| `r.success` | `r.status` (SQLite) / `r.success` (CSV) | 이중 체크 |
| `r.moisture_before` | `r.water_before \|\| r.moisture_before` | CSV 폴백 호환 유지 |

### ✨ 환경 데이터 시계열 차트 추가 (Stage 14 신규)

`analytics.html` 환경 탭에 Chart.js 시계열 차트 3종 추가:
- **SHT30 온도 추이** — 12구역 유효 센서 평균, 줌/팬 지원
- **SHT30 습도 추이** — 12구역 유효 센서 평균, 줌/팬 지원
- **WH65LP 날씨 추이** — 외기 온도/습도/UV/강수량 4축 복합 차트

`analytics.js`에 `loadEnvData()` 함수 추가:
- `/api/analytics/environment?from=...&to=...` 날짜 범위 필터 적용
- 환경 탭 클릭(`shown.bs.tab`) 시 자동 로드
- 시뮬레이션 모드(데이터 없음) 시 빈 상태 안내 메시지 표시

### 📄 변경 파일
- `web/static/js/analytics.js` — BUG-18 수정 + 환경 차트 함수 추가
- `web/templates/analytics.html` — 환경 탭 차트 캔버스 3개 추가

---

## [v0.6.4] – 2026-03-18

### 🐛 버그 수정 (Stage 14b)

#### 문제 1: 분석 그래프 표시 범위 제한
- **원인**: `analytics_bp.py`의 `query_sensor_readings(limit=2000)` 고정값으로
  센서 기록 주기 20초 기준 최대 약 11시간분 데이터만 반환됨.
  `query_air_readings(limit=5000)`은 12개 SHT30 센서 데이터 합산으로 약 7시간.
- **수정**: 날짜 범위(`from`~`to`) 기반 동적 limit 계산 도입.
  - `sensor-data`: `min(days × 5,400, 100,000)` (30일 → 100,000행, 2,000행 샘플링)
  - `air-data`   : `min(days × 20,000, 100,000)`
  - `weather-data`: `min(days × 1,500, 50,000)`
- **효과**: 선택 기간 전체 데이터를 2,000포인트로 균등 샘플링하여 그래프에 표시.

#### 문제 2: 원시 로그 트리거 표시 오류
- **원인**: `analytics.js`가 `'manual'`, `'auto'` 영문 값만 처리.
  DB에 한글(`수동`, `스케줄`, `텔레그램` 등) 또는 기타 유형이 저장된 경우
  뱃지가 올바르게 표시되지 않음.
- **수정**:
  - `TRIGGER_MAP` 상수 도입 – 한/영 양방향 매핑 (`manual`↔`수동`,
    `schedule`↔`스케줄`, `telegram`↔`텔레그램`, `sensor`↔`센서` 등).
  - `renderTriggerDonut()` 전면 재작성 – 실제 DB 값 기반 동적 집계,
    색상 팔레트 다양화.
  - `buildTriggerFilter()` 신규 – 트리거 필터 드롭다운을 실제 DB 값으로 동적 생성.
  - 브라우저 콘솔에 `[IRR] trigger_type 실제 값 샘플` 출력 (진단용).
- **진단 엔드포인트**: `/api/analytics/trigger-stats` 신규 추가
  (DB 내 `trigger_type` 값별 건수 반환).

#### 문제 3: 환경 데이터 시뮬레이션 표시 & CSV 없음
- **원인**: 시뮬레이션 모드에서도 `valid=1` 데이터가 저장되어 차트가 표시됨.
  사용자가 실제 센서 데이터와 혼동; 환경 데이터 CSV 다운로드 미제공.
- **수정**:
  - `analytics_environment()` 응답에 `simulation_mode` 플래그 추가
    (`g.simulation_mode` 참조).
  - 시뮬레이션 시 차트 헤더에 주황색 "시뮬레이션" 뱃지 표시,
    차트 레이블에 `[시뮬레이션]` 접미사, 테두리 색상 주황으로 변경.
  - 환경 탭 상단에 경고 배너 (`#sim-mode-banner`) 표시.
  - **SHT30 CSV 다운로드** 버튼 추가: `GET /api/download/air-data`
  - **WH65LP CSV 다운로드** 버튼 추가: `GET /api/download/weather-data`

### 📁 변경 파일
| 파일 | 변경 내용 |
|------|-----------|
| `web/blueprints/analytics_bp.py` | 동적 limit, trigger-stats 엔드포인트 |
| `web/blueprints/download_bp.py`  | air/weather CSV 엔드포인트 신규 |
| `web/static/js/analytics.js`     | TRIGGER_MAP, 동적 도넛, 환경 CSV |
| `web/templates/analytics.html`   | 시뮬 뱃지, CSV 버튼, 트리거 필터 |

## v0.6.2 — Stage 13: 설정 통합 (2026-03-17)

### 🔧 개선 사항

#### config/version.json 추가 (버전 중앙화)
- `config/version.json` 신규 추가: 버전, 스테이지, 릴리즈 날짜, 이력 포함
- `web/app.py`: `_APP_VERSION = _load_version()` 전역 변수로 버전 동적 로드
  - 부팅 시 출력: `🌐 스마트 관수 시스템 v0.6.2 (Blueprint)` (하드코딩 → 동적)
  - docstring 업데이트 반영
- 이전 `v0.4.1` 하드코딩 완전 제거

#### config/notifications.json 쿨다운 통합
- `cooldowns` 섹션 추가로 모듈별 쿨다운 명시:
  - `cooldowns.alert_manager`: AlertManager 알림 쿨다운 (초)
  - `cooldowns.sensor_monitor`: SensorMonitor 자체 쿨다운 (초)
- 기존 최상위 키(`cooldown_seconds`, `sensor_monitor_cooldown`) 하위 호환 유지

### 📄 변경 파일
- `config/version.json` (신규)
- `config/notifications.json` (cooldowns 섹션 추가)
- `web/app.py` (버전 동적 로드 로직)

---

## v0.6.0 (2026-03-17) — Stage 11: SQLite 마이그레이션 ✅

### 🗄️ 데이터베이스 구조 변경
- **기존**: 날짜별 CSV 파일 분산 저장 (`logs/sensors_YYYY-MM-DD.csv` 등)
- **변경**: SQLite 단일 DB 파일 (`data/smart_farm.db`), CSV 파일은 백업으로 유지

### 🆕 신규 파일
| 파일 | 역할 |
|------|------|
| `database/__init__.py` | 패키지 초기화 |
| `database/db_manager.py` | SQLite CRUD 매니저 (5개 테이블, WAL 모드, 인덱스) |
| `database/migrate_csv_to_db.py` | 기존 CSV → SQLite 1회 마이그레이션 스크립트 |

### 🗃️ DB 테이블 구조
| 테이블 | 설명 |
|--------|------|
| `sensor_readings` | 탱크 수위 + ADS1115 전압 (10초마다) |
| `air_sensor_readings` | SHT30 ×12 구역별 온·습도 (60초마다) |
| `weather_readings` | WH65LP 기상 관측소 (16초마다) |
| `irrigation_history` | 관수 이력 |
| `alerts` | 알림 이력 (향후 연동 예정) |

### 🔧 수정 파일
| 파일 | 변경 내용 |
|------|---------|
| `monitoring/data_logger.py` | `db_manager` 파라미터 추가, SQLite + CSV 병행 저장 |
| `monitoring/environment_monitor.py` | `db_manager` 파라미터 추가, SQLite + CSV 병행 저장 |
| `web/blueprints/analytics_bp.py` | SQLite 쿼리 우선, CSV 폴백 유지 |
| `web/globals.py` | `db_manager = None` 전역 변수 추가 |
| `web/app.py` | DBManager 초기화, DataLogger/EnvironmentMonitor에 db_manager 전달 |

### 🔌 신규 API 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/analytics/environment` | 환경 데이터 분석 (air/weather/all, 기간 필터) |
| GET | `/api/analytics/db-info` | DB 테이블 행 수 및 파일 크기 |

### 📊 마이그레이션 결과 (2026-03-17)
| 테이블 | 행 수 |
|--------|------|
| sensor_readings | 94,921 |
| air_sensor_readings | 3,072 |
| weather_readings | 954 |
| irrigation_history | 215 |
| 합계 | 99,162 행 |
| DB 크기 | 11 MB |


# 🗓 개발 이력

## 초기 개발
- **2026-02-10**: 하드웨어 설정, I2C 통신 구현, Stage 1 완료
- **2026-02-11**: 관수 시스템 Stage 2 완료 (구역 관리)
- **2026-02-12**: 모니터링 시스템 Stage 3 완료 (센서)
- **2026-02-13**: 웹 인터페이스 Stage 3 완료 (대시보드)

## v0.2.0 (2026-02-20)
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

## v0.3.0 (2026-02-24) `e228b1a`
- ✅ **모드 단순화**: 수동/자동 2모드로 통합 (스케줄 모드 제거)
- ✅ **IrrigationScheduler 완전 구현**: schedule/routine 타입 지원
- ✅ **루틴 기능**: 날짜 기반 N일마다 반복, 수분 체크 옵션
- ✅ **인터록 처리**: ±10분 grace window, 최대 1시간 대기
- ✅ **스케줄 CRUD API** 7개 (`/api/schedules/*`)
- ✅ **UI 분 단위 통합**: 체크 주기·관수 시간 모두 분 입력 (백엔드 초 저장)

## v0.3.1 / patch_v4h (2026-02-25) `75027f2` `b177097`
- ✅ **[Fix-서버시작]** `if __name__ == '__main__':` 블록 유실 복구
- ✅ **[Fix M]** `PUT /api/schedules/<id>` 엔드포인트 복구 → 405 오류 해결
- ✅ **[Fix B]** `toggle_schedule` 빈 바디 복구 → PATCH 500 오류 해결
- ✅ **[Fix J]** `/api/schedules/next` 응답에 `start_time`, `minutes_until` 필드 추가
- ✅ GitHub Issue #5 해결

## v0.3.2 (2026-02-26) `94e3306` `c1feebf`
- ✅ **[Fix S]** `SoilSensorManager` zones 2~12 minimalmodbus 2.x 필수 속성 누락 수정
- ✅ **`tools/set_sensor_address.py`** 신규 추가 (RS485 Modbus 주소 설정 CLI)
- ✅ GitHub Issue #4 해결

## v0.3.3 (2026-03-03) `6005970` `ec64bdf` `b3185e8`
- ✅ **[Bug-M1]** 서버 시작 시 스케줄러 미시작 수정 (모드 기본값 `manual` → `auto`)
- ✅ **[Bug-M2]** `auto` 모드 선택 시 `scheduler.stop()` 즉시 호출되는 버그 수정
- ✅ **[Bug-M3]** `soil_sensors.json` 모드 키 없어 재시작 후 `manual`로 초기화되는 버그 수정
- ✅ **[Bug-S]** `start_zone_irrigation()` 메서드 미존재로 `AttributeError` 무음 실패 수정
- ✅ **[Logger]** `scheduler.py` logger 핸들러 추가
- ✅ **[refactor]** 폰트 크기 조절 공통 모듈화 (`font-utils.js` 신규)
- ✅ **[Stage 8]** 텔레그램 알림 봇 구현 (`monitoring/telegram_notifier.py` 신규)
- ✅ **[성능]** `CHECK_INTERVAL` 30초 → 10초 단축

## v0.3.4 (2026-03-03)
- ✅ **[Stage 8 – Telegram 인라인 UI]** 텍스트 명령어 → 인라인 키보드 메뉴로 전면 개편
- ✅ **[Bug-T1]** 관수 중단 시 이중 메시지 버그 수정
- ✅ **[Bug-T2]** 관수 버튼 클릭 시 폴링 스레드 전체 블로킹 버그 수정
- ✅ **[Bug-T3]** 웹 UI `/api/irrigation/stop` `_stop_requested` 플래그 미설정 수정

## v0.3.5 (2026-03-04)
- ✅ **[Bug-N1]** `NameError: telegram_notifier is not defined` 수정
- ✅ **[Bug-N2]** `notifications.json` 빈 파일/손상 시 `JSONDecodeError` 수정
- ✅ **[Bug-N3]** `import json` 누락으로 `save_notification_config` 500 오류 수정
- ✅ **[Fix-N4]** 설정 저장 시 텔레그램 토큰 덮어쓰기 방지
- ✅ **[Fix-N5]** 텔레그램 인라인 메뉴 버튼 배치 개선
- ✅ `notifications.json`에 `thresholds` 섹션 추가
- ✅ **[Bug-A1]** 서버 재시작 시 AlertManager thresholds 하드코딩 문제 수정

## v0.3.6 (2026-03-04) `85404fc`
- ✅ **[feat]** 알림 쿨다운(cooldown_seconds) 웹 UI 설정 추가

## v0.3.6 후반 (2026-03-05) `9637b14` `33631ae` `422be23` `5195101`
- [BUG-1] 토양센서 읽기 실패 시 관수 중단 + 텔레그램 경고
- [BUG-1b] 센서 오류 알림 무한 반복 방지 - 30분 쿨다운
- [BUG-2] cooldown_seconds 즉시 반영 누락 + send_message->send 오타 수정
- [BUG-3~4] rtc_manager no-op 경고 로그 + wait_until() abort 가드
- [BUG-5] periodic_data_sender watchdog 자동 재시작 (30초)
- [BUG-7] 하드코딩 절대경로 -> _BASE_DIR 동적화 (8개 파일)
- [Cache] JS/CSS 캐시 버스팅 (서버 시작 타임스탬프 기반)

## v0.3.7 (2026-03-05~06) `3f3bb36` `f5a2a84` `67ff511`
- [Stage 8.7] 텔레그램 /status, /restart 텍스트 명령어 추가
- [Stage 8.8] 웹 UI 서버 재시작 버튼 추가 (시스템 관리 탭)
- [BUG-8] 탱크 수위 콜백 미주입 수정
- [BUG-9] SIGTERM 수신 시 안전 종료 핸들러 미구현 수정

## v0.3.8 (2026-03-06) `0a7e504` `c8234bb` `3c49fd1` `473fc9f` `ac35070` `1e6db0a`
- [BUG-10] 스케줄러 thresholds -> zone_thresholds 오타 수정 + zone_id 키 타입 수정
- [BUG-11] 핸드건 인터록 추가 후 제거 - 지하수 직결 독립 배관 확인
- [BUG-12] 재시작 후 /api/status 0.0% 반환 버그 수정
- [BUG-13] SensorMonitor alert_cooldown 하드코딩 -> config 읽기 수정
- [BUG-15] _monitor_loop 체크 주기 수정 - 관수 소요시간 제외 후 잔여시간만 대기
- [BUG-16] 다중 구역 연속 관수 중 구역마다 탱크 수위 재체크 추가

### 🐛 BUG-14 P2: /api/status 센서 오류 정보 추가 (커밋 `592a6ba`)

**파일**: `web/blueprints/monitoring_bp.py`

#### 변경 내용
- **voltages 배열 None 보존**: I2C 오류 채널은 `0.0` 대신 `null` 반환
  - `last_data` 경로(라인 29) + `cached_sensor_data` 폴백 경로(라인 35) 둘 다 수정
- **`sensor_errors` 필드 추가**: 채널별 연속 오류 여부 `{ch0~ch3: bool}`
  - `alert_manager.sensor_error_counts` 기반
- **`sensor_stats` 필드 추가**: 채널별 통계
  - `sensor_reader.get_error_stats()` 기반
  - `{consecutive_errors, total_reads, error_reads, success_rate, last_valid_voltage}`
- 모두 `try/except`로 감싸 미초기화 상태에서도 안전하게 동작

## v0.4.0 (2026-03-09) `32d76d5`
- [Stage 9] 관수 주기 관리 시스템 구현
  - 구역별 마지막 관수 시간 추적 (last_irrigated_time 딕셔너리)
  - 재시작 후 CSV(irrigation_history.csv)에서 자동 복원
  - 3단계 자동관수 판단 로직:
    - elapsed < min_interval(6h) → 미관수 주기, 무조건 스킵
    - min_interval ≤ elapsed < max_interval(3일) → 습도 기반 관수
    - elapsed ≥ max_interval → 필수관수, 센서 오류 무관 강제 실행
  - soil_sensors.json 구역별 min_irrigation_interval, max_irrigation_interval 추가
  - scheduler.py 스케줄 완료 후 update_last_irrigated_time() 연결
- [BUG-17 WONTFIX] 스케줄+자동 연속 과관수 -> Stage 9 미관수 주기로 근본 해결

## v0.4.1 (2026-03-09) `592fa92` `19fa53b` `bd831c1` `81c7e71` `a299b82` `501df2a`

### 🏗 Blueprint 리팩터링 (커밋 `592fa92`)
- `web/app.py` (3,000+ 라인) → 5개 Blueprint로 분리 (+1,025 / -1,794 lines)
  - `web/blueprints/monitoring_bp.py` (~8 routes)
  - `web/blueprints/irrigation_bp.py` (~14 routes)
  - `web/blueprints/analytics_bp.py` (~3 routes)
  - `web/blueprints/notifications_bp.py` (~4 routes)
  - `web/blueprints/download_bp.py` (~3 routes)
- `web/globals.py` 신규 — 공유 전역 변수 관리
- `web/app.py` slim entry point로 축소

### 🐛 BUG-FIX: auto_controller telegram_notifier 탐색 실패 (커밋 `19fa53b`)
- **원인**: Blueprint 리팩터링 후 `telegram_notifier`가 `web.globals`로 이동,
  `auto_controller.py`의 `sys.modules["web.app"].telegram_notifier` 탐색이 `None` 반환
- **증상**: 관수 시작/완료 텔레그램 알림 미전송
- **수정**: `web/app.py` 초기화 완료 후 모듈 레벨 alias 추가
- **검증**: 수동 관수 10초 → 💧 관수 시작 / ✅ 관수 완료 수신 확인

### 🐛 BUG-FIX: zone_id=0 (전체 구역) 저장/실행 불가
- `web/blueprints/irrigation_bp.py`: `if not zone_id` → `if zone_id is None`
- `web/static/js/settings.js`: `if (!zone_id)` → null/NaN/empty 체크로 교체
- `irrigation/scheduler.py`: `zone_id == 0` 시 구역 1~12 순차 실행 로직 추가
- `monitoring/telegram_notifier.py`: 스케줄 목록 `구역0` → `구역전체` 표시 수정

### 🐛 BUG-14: I2C 센서 읽기 실패 처리 (P0 + P1 완료)
| 단계 | 커밋 | 파일 | 내용 |
|------|------|------|------|
| P0-1 | `a299b82` | `hardware/sensor_reader.py` | I2C 재시도 2회 + fallback + 오류통계 |
| P0-2 | `501df2a` | `monitoring/sensor_monitor.py` | None 샘플 필터링 + SensorReadError |
| P0-2 수정 | `81c7e71` | `monitoring/sensor_monitor.py` | SyntaxError 잔재 else 제거 |
| P1 | `bd831c1` | `monitoring/alert_manager.py` | None 전압 허용 + 연속 카운터 + 복구 감지 |

---

## v0.5.0 (2026-03-17) — Stage 10: 대기 환경 모니터링 ✅

### 🌡️ 신규 하드웨어 지원
- **CDSENET EID041-G01 (SHT30)** × 12 — 구역별 대기 온도·습도 (RS-485 Modbus RTU, 9600bps)
- **MISOL WH65LP** × 1 — 외부 기상 스테이션 (RS-485, 독자 25바이트 프로토콜, 16초 자동 송출)

### 🆕 신규 파일
| 파일 | 역할 |
|------|------|
| `config/air_sensors.json` | SHT30 × 12 Modbus 설정 (포트, baudrate, 센서 목록, simulation_mode) |
| `config/weather_station.json` | WH65LP 설정 (포트, baudrate, 패킷 길이, simulation_mode) |
| `hardware/air_sensor_reader.py` | SHT30 Modbus RTU 드라이버 (CRC-16, DE/RE GPIO 17 제어, simulate 지원) |
| `hardware/weather_station_reader.py` | WH65LP 25바이트 패킷 파서 (CRC-8 poly 0x31, simulate 지원) |
| `monitoring/environment_monitor.py` | 백그라운드 폴링 스레드 (SHT30 60초 / WH65LP 16초, CSV 로그) |
| `web/blueprints/environment_bp.py` | 환경 REST API Blueprint (6개 엔드포인트) |

### 🔧 수정 파일
| 파일 | 변경 내용 |
|------|---------|
| `web/globals.py` | `air_sensor_manager`, `weather_station`, `environment_monitor`, `environment_state` 추가 |
| `web/app.py` | `environment_bp` 등록, `EnvironmentMonitor` 초기화/시작, 종료 시 stop() 호출 |
| `web/templates/index.html` | 환경 모니터링 탭 추가 (기상 카드 6종 + SHT30 구역 그리드) |
| `web/templates/analytics.html` | 환경 데이터 탭 추가 (요약 카드 4종 + 스냅샷 테이블 + 기상 배지) |
| `web/static/js/dashboard.js` | 백그라운드 환경 API 폴링 추가 (60초 간격) |

### 🔌 신규 API 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/environment` | 전체 환경 데이터 (공기 + 기상) |
| GET | `/api/environment/air` | 전체 SHT30 센서 데이터 |
| GET | `/api/environment/air/<id>` | 특정 구역 SHT30 데이터 |
| GET | `/api/environment/weather` | WH65LP 기상 데이터 |
| GET | `/api/environment/history/air` | 대기 센서 이력 (최근 100 스냅샷) |
| GET | `/api/environment/history/weather` | 기상 이력 (최근 100 스냅샷) |

### 🖥️ UI 변경
- **대시보드** (`index.html`): 탭 3개 → 4개, 환경 모니터링 탭 추가
  - 기상 정보 패널: 온도/습도/풍속+돌풍/기압/강수량/UV+조도 카드
  - 구역별 SHT30 그리드: 12구역 동적 카드 (오류 구역 빨간 테두리)
  - 60초 자동 갱신, 탭 클릭 즉시 갱신, 시뮬레이션 배지 표시
- **분석 페이지** (`analytics.html`): 탭 4개 → 5개, 환경 데이터 탭 추가
  - 요약 카드: 평균 온도/습도, 외부 온도, UV 지수
  - 구역별 스냅샷 테이블 (12구역 전체, 이상 구역 빨간 행)
  - 현재 기상 배지 패널 (WH65LP 실시간)

> ⚠️ 현재 `simulation_mode: true` 상태 — 실제 하드웨어 수령 후 `false`로 전환 예정
