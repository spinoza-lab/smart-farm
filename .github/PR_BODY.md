## 📋 변경 요약

`refactor/blueprint` 브랜치의 v4.1 작업 전체를 `main`에 머지합니다.

---

## ✅ 포함된 변경사항

### 🏗 Blueprint 리팩터링 (`592fa92`)
- `web/app.py` (3,000+ 줄) → 5개 Blueprint로 분리
  - `monitoring_bp.py` / `irrigation_bp.py` / `analytics_bp.py`
  - `notifications_bp.py` / `download_bp.py`
- `web/globals.py` 신규 — 공유 전역 변수 관리
- `web/app.py` slim entry point로 축소 (+1,025 / -1,794 lines)

### 🐛 BUG-FIX: telegram_notifier 탐색 실패 (`19fa53b`)
- Blueprint 리팩터링 후 `auto_controller`의 telegram_notifier 탐색이 None 반환
- `web/app.py`에 모듈 레벨 alias 추가로 해결
- 검증: 수동 관수 10초 → 💧관수 시작 / ✅관수 완료 수신 확인

### 🐛 BUG-FIX: zone_id=0 (전체 구역) 처리 (`846b47c`, `f900904`)
- `if not zone_id` → `if zone_id is None` (Python falsy 0 오처리 수정)
- `scheduler.py`: zone_id=0 시 구역 1~12 순차 실행
- `telegram_notifier.py`: `구역0` → `구역전체` 표시

### 🐛 BUG-14: I2C 센서 장애 graceful handling (`a299b82`~`592a6ba`)

| 단계 | 커밋 | 내용 |
|------|------|------|
| P0-1 | `a299b82` | sensor_reader.py — I2C 재시도 2회 + fallback + 오류통계 |
| P0-2 | `501df2a` | sensor_monitor.py — None 샘플 필터링 + SensorReadError |
| P0-2fix | `81c7e71` | sensor_monitor.py — SyntaxError 잔재 else 제거 |
| P1 | `bd831c1` | alert_manager.py — None 전압 허용 + 연속 카운터 + 복구 알림 |
| P2 | `592a6ba` | monitoring_bp.py — /api/status sensor_errors·sensor_stats |

**완성된 오류 처리 흐름:**
```
I2C 읽기 실패
  → sensor_reader: 재시도 2회 → fallback / None 반환
  → sensor_monitor: None 필터링 → SensorReadError
  → _monitor_loop: 10초 대기 후 재시도
  → alert_manager: WARNING(1회) / CRITICAL(5회) Telegram + 복구 알림
  → /api/status: voltages[null], sensor_errors, sensor_stats 노출
```

---

## 🧪 테스트 완료
- [x] 서비스 정상 기동 (`active (running)`)
- [x] `/api/status` — `sensor_errors`, `sensor_stats` 필드 포함 확인
- [x] `python3 -m py_compile` — 모든 수정 파일 문법 OK
- [x] 수동 관수 10초 — Telegram 시작/완료 알림 수신
- [x] zone_id=0 스케줄 저장/실행/표시 정상

---

## 📁 수정된 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `web/app.py` | Blueprint 등록 + telegram_notifier alias |
| `web/globals.py` | 신규 — 전역 변수 관리 |
| `web/blueprints/monitoring_bp.py` | 신규 + sensor_errors/stats |
| `web/blueprints/irrigation_bp.py` | 신규 + zone_id=0 수정 |
| `web/blueprints/analytics_bp.py` | 신규 |
| `web/blueprints/notifications_bp.py` | 신규 |
| `web/blueprints/download_bp.py` | 신규 |
| `hardware/sensor_reader.py` | I2C 재시도 + fallback + 오류통계 |
| `monitoring/sensor_monitor.py` | None 필터링 + SensorReadError |
| `monitoring/alert_manager.py` | None 전압 + 연속 카운터 + 복구 |
| `irrigation/scheduler.py` | zone_id=0 순차 실행 |
| `monitoring/telegram_notifier.py` | zone_id=0 표시 수정 |
| `web/static/js/settings.js` | zone_id=0 falsy 처리 |
| `docs/STATUS.md` | v4.1 전체 완료 반영 |
| `docs/CHANGELOG.md` | v4.1 변경 이력 추가 |

---

## ⚠️ 주의사항
- 머지 후 Pi에서 `sudo systemctl restart smart-farm.service` 필요
- `main` 브랜치 직접 수정 없음 — fast-forward 또는 squash merge 권장
