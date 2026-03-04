# 🗓 개발 이력

## 초기 개발

- **2026-02-10**: 하드웨어 설정, I2C 통신 구현, Stage 1 완료
- **2026-02-11**: 관수 시스템 Stage 2 완료 (구역 관리)
- **2026-02-12**: 모니터링 시스템 Stage 3 완료 (센서)
- **2026-02-13**: 웹 인터페이스 Stage 3 완료 (대시보드)

## v2.0 (2026-02-20)

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

## v3.0 (2026-02-24) `e228b1a`

- ✅ **모드 단순화**: 수동/자동 2모드로 통합 (스케줄 모드 제거)
- ✅ **IrrigationScheduler 완전 구현**: schedule/routine 타입 지원
- ✅ **루틴 기능**: 날짜 기반 N일마다 반복, 수분 체크 옵션
- ✅ **인터록 처리**: ±10분 grace window, 최대 1시간 대기
- ✅ **스케줄 CRUD API** 7개 (`/api/schedules/*`)
- ✅ **UI 분 단위 통합**: 체크 주기·관수 시간 모두 분 입력 (백엔드 초 저장)

## v3.1 / patch_v4h (2026-02-25) `75027f2` `b177097`

- ✅ **[Fix-서버시작]** `if __name__ == '__main__':` 블록 유실 복구
- ✅ **[Fix M]** `PUT /api/schedules/<id>` 엔드포인트 복구 → 405 오류 해결
- ✅ **[Fix B]** `toggle_schedule` 빈 바디 복구 → PATCH 500 오류 해결
- ✅ **[Fix J]** `/api/schedules/next` 응답에 `start_time`, `minutes_until` 필드 추가
- ✅ GitHub Issue [#5](https://github.com/spinoza-lab/smart-farm/issues/5) 해결

## v3.2 (2026-02-26) `94e3306` `c1feebf`

- ✅ **[Fix S]** `SoilSensorManager` zones 2~12 minimalmodbus 2.x 필수 속성 누락 수정
- ✅ **`tools/set_sensor_address.py`** 신규 추가 (RS485 Modbus 주소 설정 CLI)
- ✅ GitHub Issue [#4](https://github.com/spinoza-lab/smart-farm/issues/4) 해결

## v3.3 (2026-03-03) `6005970` `ec64bdf` `b3185e8`

- ✅ **[Bug-M1]** 서버 시작 시 스케줄러 미시작 수정 (모드 기본값 `manual` → `auto`)
- ✅ **[Bug-M2]** `auto` 모드 선택 시 `scheduler.stop()` 즉시 호출되는 버그 수정
- ✅ **[Bug-M3]** `soil_sensors.json` 모드 키 없어 재시작 후 `manual`로 초기화되는 버그 수정
- ✅ **[Bug-S]** `start_zone_irrigation()` 메서드 미존재로 `AttributeError` 무음 실패 수정
  - `auto_controller.py`에 `start_zone_irrigation()` 래퍼 메서드 추가
  - `irrigate_zone()`에 `trigger` 파라미터 추가 (CSV에 `scheduler` 트리거 정확히 기록)
- ✅ **[Logger]** `scheduler.py` logger 핸들러 추가 (기존 무음 드롭 → StreamHandler 출력)
- ✅ **[refactor]** 폰트 크기 조절 공통 모듈화 (`font-utils.js` 신규)
  - 기존 페이지별 개별 localStorage 키 → 단일 키 `fontSize` 통합
  - 인라인 스크립트 제거, 전 페이지 `font-utils.js` 공통 사용
- ✅ **[Stage 8]** 텔레그램 알림 봇 구현 (`monitoring/telegram_notifier.py` 신규)
  - Phase 1: 서버 시작·관수 시작/완료·수위 경고·센서 오류 자동 알림
  - Phase 2: `/status`, `/history`, `/schedules`, `/irrigate`, `/stop`, `/mute` 명령어 봇
  - AlertManager 콜백 연동, 폴링 주기 3초
- ✅ **[성능]** `CHECK_INTERVAL` 30초 → 10초 단축 (구역 간 전환 딜레이 개선)
- ✅ **[개발환경]** VS Code Remote-SSH 설정 (맥북 → 라즈베리파이 직접 개발)
- ✅ 주말(2/27~3/2) 7회 미실행 확인 및 전체 원인 규명 완료

## v3.4 (2026-03-03)

- ✅ **[Stage 8 – Telegram 인라인 UI]** 텍스트 명령어 → 인라인 키보드 메뉴로 전면 개편
  - `MAIN_MENU`, `ZONE_MENU` (12구역 그리드), `duration_menu` (30초/1분/2/5/10/20분) 추가
  - `edit_message()` 메서드 추가 — 새 메시지 발송 대신 기존 메시지를 수정해 채팅창 노이즈 최소화
  - `_poll_loop`이 `callback_query`와 텍스트(`/start`, `/menu`, `/help`) 동시 처리
- ✅ **[Bug-T1]** 관수 중단 시 `❌ 관수 실패` + `🛑 중단됨` 이중 메시지 버그 수정
  - `notify_irrigation_done(success=False)` → `🛑 관수 중단됨 – 구역N ⏱ N초 경과` 단일 메시지
- ✅ **[Bug-T2]** 관수 버튼 클릭 시 폴링 스레드 전체 블로킹 버그 수정
  - `_handle_irrigate_zone` — 즉시 "💧 관수 요청 접수" 응답 후 백그라운드 daemon 스레드 실행
- ✅ **[Bug-T3]** 웹 UI `/api/irrigation/stop` 이 `_stop_requested` 플래그 미설정 → 중단 지연 버그 수정
  - `app.py` stop 라우트에 `auto_irrigation.stop_irrigation()` 호출 추가
  - 웹 UI 긴급 정지 1초 이내 즉시 반영
- ✅ **[auto_controller]** `irrigate_zone()` 단일 `time.sleep` → 1초 루프 + `_stop_requested` 플래그 체크
  - `stop_irrigation()` 메서드 신규 추가
  - `actual_duration` 실제 경과 시간 기록, 결과 dict에 `duration`·`success` 포함

## v3.5 (2026-03-04)

- ✅ **[Bug-N1]** `NameError: telegram_notifier is not defined` 수정
  - `web/app.py` 모듈 상단에 `telegram_notifier = None` 전역 선언 추가
- ✅ **[Bug-N2]** `notifications.json` 빈 파일/손상 시 `JSONDecodeError` 수정
  - `get_notification_config`: 빈 파일·파싱 오류 시 기본값으로 자동 복원
  - `save_notification_config`: 원자적 저장 (임시 파일 → rename) 적용
- ✅ **[Bug-N3]** `import json` 누락으로 `save_notification_config` 500 오류 수정
- ✅ **[Fix-N4]** 설정 저장 시 텔레그램 토큰 덮어쓰기 방지
  - `get_notification_config` 응답에서 token/chat_id 마스킹
  - `save_notification_config`: POST에 telegram 섹션 없으면 메모리값 유지
  - `settings.js`: POST 요청에서 alerts/thresholds만 전송 (telegram 제외)
- ✅ **[Fix-N5]** 텔레그램 인라인 메뉴 버튼 배치 개선
  - "현재 상태" → "상태 확인" 이름 변경
  - 버튼 배치: `[상태 확인][오늘 이력] / [스케줄 목록] / [관수 시작][관수 중단] / [1시간 무음][무음 해제]`
- ✅ **[Fix-N6]** `settings.html` 텔레그램 버튼 메뉴 설명을 실제 봇과 동기화
- ✅ `notifications.json`에 `thresholds` 섹션 추가 (tank1/tank2 min/max 수위 임계값)
- ✅ **[Bug-A1]** 서버 재시작 시 AlertManager thresholds 하드코딩 문제 수정
  - 서버 시작 시 `notifications.json`에서 thresholds 로드하여 AlertManager에 적용
  - 폴백: 파일 없거나 오류 시 기본값 20/90% 사용

## v3.6 (2026-03-04) `85404fc`

- ✅ **[feat]** 알림 쿨다운(cooldown_seconds) 웹 UI 설정 추가
  - 서버 시작 시 `notifications.json`에서 `cooldown_seconds` 로드
  - `POST /api/notifications/config`에서 `cooldown_seconds` 저장 및 즉시 반영
  - `GET /api/notifications/config` 응답에 `cooldown_seconds` 포함
  - `settings.html`: 알림 설정 탭에 쿨다운 UI 추가 (분 단위 입력 + 프리셋 버튼)
  - `settings.js`: `loadNotificationConfig()`, `saveCooldownConfig()` 함수 추가
