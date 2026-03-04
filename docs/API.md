# 🔌 API 엔드포인트

## 시스템

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/status` | 시스템 상태 조회 |
| POST | `/api/start_monitoring` | 모니터링 시작 |
| POST | `/api/stop_monitoring` | 모니터링 중지 |
| GET | `/api/data_history?hours=24` | 센서 이력 |
| GET | `/api/statistics?hours=24` | 탱크 통계 |

## 캘리브레이션

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/calibration` | 캘리브레이션 설정 조회 |
| POST | `/api/calibration` | 캘리브레이션 저장 (0~5V 검증) |
| GET | `/api/calibration/current` | 현재 실시간 센서 전압 |

## 알림 설정 (v3.5~v3.6)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/notifications/config` | 알림 설정 조회 (token 마스킹) |
| POST | `/api/notifications/config` | 알림 설정 저장 (메모리 우선 병합) |
| GET | `/api/notifications/status` | 텔레그램 봇 상태 조회 |
| POST | `/api/notifications/test` | 텔레그램 테스트 메시지 전송 |

## 관수 제어

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/irrigation/status` | 관수 전체 상태 (모드, 수분, 이력, irr_elapsed/irr_total) |
| POST | `/api/irrigation/mode` | 모드 변경 `{mode: auto\|manual}` |
| POST | `/api/irrigation/start` | 관수 시작 `{zone_id, duration}` |
| POST | `/api/irrigation/stop` | 긴급 정지 |
| GET | `/api/irrigation/sensors` | 토양 센서 현황 (캐시) |
| POST | `/api/irrigation/sensors/read` | 토양 센서 즉시 재측정 |
| POST | `/api/irrigation/threshold` | 구역 임계값 설정 `{zone_id, threshold}` |
| GET | `/api/irrigation/history?limit=20` | 관수 이력 JSON |
| GET | `/api/irrigation/config` | 자동관수 설정 조회 |
| POST | `/api/irrigation/config` | 자동관수 설정 저장 |

## 스케줄 CRUD

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/schedules` | 전체 스케줄/루틴 목록 |
| POST | `/api/schedules` | 새 스케줄/루틴 추가 |
| PUT | `/api/schedules/<id>` | 스케줄 수정 (zone_id, start_time, duration, days, enabled) |
| DELETE | `/api/schedules/<id>` | 스케줄 삭제 |
| PATCH | `/api/schedules/<id>` | 스케줄 활성/비활성 토글 (enabled 필드) |
| GET | `/api/schedules/next` | 다음 실행 예정 스케줄 (next_run, start_time, minutes_until 포함) |

## 분석 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/analytics/sensor-data` | 탱크 수위 이력 (`?from=&to=`, 다운샘플링 800pt) |
| GET | `/api/analytics/irrigation-history` | 관수 이력 분석 (`?from=&to=`) |

## CSV 다운로드

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/download/irrigation-history` | 관수 이력 CSV (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |
| GET | `/api/download/sensor-data` | 탱크 수위 CSV (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |

## 호스건

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/hose-gun/status` | 호스건 상태 조회 |
| POST | `/api/hose-gun/activate` | 호스건 ON |
| POST | `/api/hose-gun/deactivate` | 호스건 OFF |
