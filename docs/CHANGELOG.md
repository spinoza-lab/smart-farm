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

## 🔮 v0.5.0 (예정) — Stage 10: 대기환경 모니터링

> 하드웨어 주문 완료 (2026-03-11). 배송 후 구현 예정.

### 추가 하드웨어
- **CDSENET EID041-G01 (SHT30)** × 12 — 구역별 대기 온도·습도 (RS-485 Modbus, 9600bps)
- **MISOL WH65LP** × 1 — 외부 기상 스테이션 (RS-485, 독자 25바이트 프로토콜, 9600bps)
- **MAX485 모듈** × 2 추가 (Bus 2/3)

### RS-485 버스 배선 계획
| 버스 | UART | 경로 | TX | RX | DE/RE | 용도 |
|------|------|------|----|----|-------|------|
| Bus 1 | UART0 | /dev/ttyAMA0 | GPIO14 | GPIO15 | GPIO18 | 토양 센서 ×12 (기존) |
| Bus 2 | UART3 | /dev/ttyAMA2 | GPIO4 (Pin7) | GPIO5 (Pin29) | GPIO17 (Pin11) | 대기 온습도 ×12 (신규) |
| Bus 3 | UART4 | /dev/ttyAMA3 | GPIO8 (Pin24) | GPIO9 (Pin21) | GND (Pin25) | 기상 스테이션 ×1 (신규) |

### 추가 소프트웨어 파일 목록
```
config/air_sensors.json          # SHT30 설정 (포트/baudrate/센서목록)
config/weather_station.json      # WH65LP 설정 (포트/baudrate)
hardware/air_sensor_reader.py    # SHT30 Modbus RTU 드라이버
hardware/weather_station_reader.py  # WH65LP 패킷 파서
monitoring/environment_monitor.py   # 백그라운드 폴링 스레드
web/blueprints/environment_bp.py    # REST API (/api/environment/*)
web/globals.py                   # 전역 변수 추가 (수정)
web/app.py                       # Blueprint 등록 (수정)
web/templates/index.html         # 대시보드 환경 섹션 추가 (수정)
```

### 계획된 API 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/environment` | 전체 환경 데이터 (공기 + 기상) |
| GET | `/api/environment/air` | 전체 SHT30 센서 데이터 |
| GET | `/api/environment/air/<id>` | 특정 구역 SHT30 데이터 |
| GET | `/api/environment/weather` | WH65LP 기상 데이터 |
| POST | `/api/environment/air/<id>/enable` | 센서 활성화/비활성화 |
