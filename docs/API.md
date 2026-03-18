# 🔌 API 엔드포인트

> **버전**: v0.6.8 기준
> 외부 접근: `http://spinozadev.iptime.org:15000`
> 내부 접근: `http://192.168.0.111:5000`

## 시스템

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/status` | 시스템 상태 조회 (sensor_errors, sensor_stats 포함) |
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
| GET | `/api/analytics/sensor-data` | 탱크 수위 이력 (`?from=&to=`, 동적 limit, 2,000pt 샘플링) |
| GET | `/api/analytics/irrigation-history` | 관수 이력 분석 (`?from=&to=`) |
| GET | `/api/analytics/environment` | 환경 데이터 분석 (`?type=air\|weather\|all&from=&to=`) |
| GET | `/api/analytics/db-info` | DB 테이블 행 수 및 파일 크기 |
| GET | `/api/analytics/trigger-stats` | 트리거 유형별 건수 (DB 진단용, v0.6.4 신규) |

### `/api/analytics/trigger-stats` 응답 예시
```json
{
  "trigger_counts": {
    "수동": 42,
    "스케줄": 28,
    "텔레그램": 5,
    "센서": 140
  }
}
```

### `/api/analytics/environment` 쿼리 파라미터
| 파라미터 | 기본값 | 설명 |
|---------|------|------|
| `type` | `all` | `air` / `weather` / `all` |
| `from` | 7일 전 | 시작일 (YYYY-MM-DD) |
| `to` | 오늘 | 종료일 (YYYY-MM-DD) |

## CSV 다운로드

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/download/irrigation-history` | 관수 이력 CSV (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |
| GET | `/api/download/sensor-data` | 탱크 수위 CSV (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |
| GET | `/api/download/air-data` | SHT30 대기 센서 CSV (v0.6.4 신규, `?from=&to=`) |
| GET | `/api/download/weather-data` | WH65LP 기상 데이터 CSV (v0.6.4 신규, `?from=&to=`) |

## 환경 모니터링 (v0.5.0)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/environment` | 전체 환경 데이터 (공기 + 기상) |
| GET | `/api/environment/air` | 전체 SHT30 센서 데이터 (12구역) |
| GET | `/api/environment/air/<id>` | 특정 구역 SHT30 데이터 |
| GET | `/api/environment/weather` | WH65LP 기상 데이터 |
| GET | `/api/environment/history/air` | 대기 센서 이력 (최근 100 스냅샷) |
| GET | `/api/environment/history/weather` | 기상 이력 (최근 100 스냅샷) |

### `/api/environment` 응답 예시
```json
{
  "air": {
    "zones": {
      "1": {"temperature": 23.5, "humidity": 65.2, "valid": true},
      "2": {"temperature": 24.1, "humidity": 63.8, "valid": true}
    },
    "simulation_mode": true,
    "timestamp": "2026-03-18T10:00:00"
  },
  "weather": {
    "temperature": 18.3,
    "humidity": 72.0,
    "wind_speed": 2.5,
    "wind_gust": 4.1,
    "wind_direction": 180,
    "rainfall": 0.0,
    "uv_index": 3,
    "lux": 42000,
    "pressure": 1013.2,
    "simulation_mode": true,
    "timestamp": "2026-03-18T10:00:00"
  }
}
```

## 호스건

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/hose-gun/status` | 호스건 상태 조회 |
| POST | `/api/hose-gun/activate` | 호스건 ON |
| POST | `/api/hose-gun/deactivate` | 호스건 OFF |

---

## 📝 API 공통 규칙

- **Content-Type**: `application/json`
- **성공 응답**: `{"status": "ok", ...}` 또는 데이터 직접 반환
- **오류 응답**: `{"error": "오류 메시지"}` + HTTP 4xx/5xx
- **날짜 파라미터**: `YYYY-MM-DD` 형식 (예: `?from=2026-03-01&to=2026-03-18`)
- **CSV 다운로드**: `Content-Disposition: attachment; filename=...` 헤더 포함
