# 📋 Smart Farm 프로젝트 현황 노트

> 최종 업데이트: 2026-03-06
> 버전: v3.8 (버그 수정 완료, 관수 로직 검토 진행 중)
> 작업 세션 간 컨텍스트 유지를 위한 내부 노트

---

## ✅ 전체 완료 작업 목록

### v3.5 버그 수정

| ID | 내용 | 파일 | 상태 |
|---|---|---|---|
| Bug-N1 | NameError: telegram_notifier=None 참조 오류 | web/app.py | ✅ |
| Bug-N2 | JSONDecodeError: notifications.json 손상 시 크래시 | monitoring/telegram_notifier.py | ✅ |
| Bug-N3 | 텔레그램 토큰 덮어쓰기 방지 | monitoring/telegram_notifier.py | ✅ |
| Bug-A1 | AlertManager 하드코딩 임계값 → 설정파일 연동 | monitoring/alert_manager.py | ✅ |

---

### v3.6 기능 추가

| ID | 내용 | 파일 | 상태 |
|---|---|---|---|
| Feat-1 | cooldown_seconds 웹 UI 설정 추가 | web/app.py, settings.html, settings.js | ✅ |
| Feat-2 | docs/ 폴더 신설 및 README.md 구조 분할 | docs/*.md | ✅ |
| Feat-3 | RTC DS1307 커널 드라이버 등록 (/boot/firmware/config.txt) | 시스템 설정 | ✅ |
| Feat-4 | RTCManager → datetime.now() 기반으로 교체 (I2C 충돌 해결) | hardware/rtc_manager.py | ✅ |

---

### v3.6 버그 수정 (2026-03-05)

| ID | 내용 | 파일 | 커밋 |
|---|---|---|---|
| BUG-1 | 토양센서 읽기 실패 시 관수 중단 + 텔레그램 경고 | irrigation/auto_controller.py | 9637b14 |
| BUG-2 | cooldown_seconds 즉시 반영 누락 + send_message → send 오타 수정 | web/app.py, monitoring/alert_manager.py | 9637b14 |
| BUG-1b | 센서 오류 알림 무한 반복 방지 — 30분(1800초) 쿨다운 추가 | irrigation/auto_controller.py | 33631ae |
| BUG-3 | rtc_manager.set_datetime() no-op 경고 로그 추가 | hardware/rtc_manager.py | 5195101 |
| BUG-4 | rtc_manager.wait_until() 메인스레드 호출 시 즉시 abort 가드 추가 | hardware/rtc_manager.py | 5195101 |
| BUG-5 | periodic_data_sender 스레드 종료 시 watchdog 자동 재시작 (30초 내) | web/app.py | 422be23 |
| BUG-6 | 중복 알림 가능성 확인 → 실제 중복 없음 확인 (해소) | (해소) | 5195101 |
| BUG-7 | 하드코딩 절대경로 /home/pi/smart_farm → _BASE_DIR 동적화 (8개 파일) | 하단 참조 | 5195101 |
| Cache | JS/CSS 캐시 버스팅 — 서버 시작 타임스탬프 기반 ?v={{ cache_ver }} | web/app.py, 4개 템플릿 | 5195101 |
| Jinja2 | url_for()?v= 잘못된 위치 → url_for() }}?v= 수정 (SyntaxError 해결) | 4개 템플릿 | defbdea |

---

### v3.7 기능 추가 (2026-03-05 ~ 03-06)

| ID | 내용 | 파일 | 커밋 |
|---|---|---|---|
| Stage-8.7 | 텔레그램 /status, /restart 텍스트 명령어 추가 | monitoring/telegram_notifier.py | 3f3bb36 |
| Stage-8.8 | 웹 UI 서버 재시작 버튼 추가 (시스템 관리 탭) | web/app.py, settings.html, settings.js | f5a2a84 |
| Stage-8.8b | system-pane 탭 위치 수정 (alerts 패널 내부 중첩 버그) | web/templates/settings.html | 5ae3b11 |
| Stage-8.8c | confirmRestart 함수 미정의 오류 수정 (settings.js에 추가) | web/static/js/settings.js | fd5b891 |
| Stage-8.8d | 서버 정보 카드 탱크 수위 항목 제거 (불필요 정보 정리) | web/static/js/settings.js | 2032716 |

---

### v3.7 버그 수정 / 안전성 강화 (2026-03-06)

| ID | 내용 | 파일 | 커밋 |
|---|---|---|---|
| BUG-8 | 탱크 수위 콜백 미주입 — 탱크 빈 상태에서도 관수 강행 버그 | web/app.py | 67ff511 |
| BUG-9 | SIGTERM 수신 시 안전 종료 핸들러 미구현 — 재시작 중 펌프 방치 위험 | web/app.py | 67ff511 |

**BUG-8 상세:**
- `auto_irrigation._check_tank_level()`이 `get_tank_level_callback` 존재 여부만 확인
- `app.py`에서 콜백을 주입하지 않아 항상 `return True, "탱크 수위 충분"` 통과
- 수정: `init_monitoring_system()` 내 `auto_irrigation` 생성 직후 `cached_sensor_data` 기반 콜백 주입

**BUG-9 상세:**
- `systemctl restart` 시 SIGTERM → Python 즉시 종료 → `finally` 블록 실행 불가 → 펌프/밸브 ON 유지
- 수정: `import signal` + `import atexit` + `_graceful_shutdown()` + `_emergency_relay_off()` 추가
- 동작: SIGTERM → 관수 중단 플래그 → 2초 대기 → `relay_controller.all_off()` → `sys.exit(0)` → atexit 이중 확인

---

### v3.8 버그 수정 (2026-03-06)

| ID | 내용 | 파일 | 커밋 |
|---|---|---|---|
| BUG-10 | 스케줄러 `thresholds` → `zone_thresholds` 오타 수정 + zone_id 키 타입 수정 | irrigation/scheduler.py | 0a7e504 |
| BUG-11 | 핸드건 인터록 추가 후 제거 — 핸드건은 지하수 직결 독립 배관 확인, 인터록 불필요 | irrigation/auto_controller.py | 550672e→3a58b90 |
| BUG-12 | 재시작 후 `/api/status` 0.0% 반환 버그 수정 | web/app.py | c8234bb |
| BUG-13 | SensorMonitor `alert_cooldown` 하드코딩 → config 읽기 수정 | monitoring/sensor_monitor.py | 3c49fd1 |

**BUG-10 상세:**
- `scheduler.py`의 `check_moisture` 로직에서 `self.controller.thresholds` 오타 (실제 속성명: `zone_thresholds`)
- zone_id 키 타입 불일치: `str(zone_id)` → `zone_id` (int), `f"zone_{zone_id}"` → `zone_id` (int)
- 결과: check_moisture=True 스케줄 실행 시 항상 기본값 40% 사용 → 실제 수분 무시하고 관수 강행

**BUG-11 상세:**
- 최초: 핸드건 ON 중 자동관수 인터록 추가 (커밋 550672e)
- 번복: 핸드건은 지하수 직결 완전 독립 배관 확인 → 관수펌프와 회로 공유 없음
- 최종: 인터록 제거 (커밋 3a58b90) — 핸드건과 자동관수 동시 동작 가능, 하드웨어 문제 없음

**BUG-12 상세:**
- `periodic_data_sender`가 `sensor_monitor._collect_sensor_data()`만 호출하고 `_add_to_history()` 미호출
- → `sensor_monitor.history`는 항상 빈 리스트 → `/api/status`가 0.0% 반환
- 수정 ①(근본): `periodic_data_sender`에 `sensor_monitor._add_to_history(status)` 추가
- 수정 ②(즉각): `/api/status` history 없을 때 `cached_sensor_data` fallback 추가
- 검증: `sudo systemctl restart` 후 15초 내 `tank1_level: 55.2%` 정상 반환 확인 ✅

**BUG-13 상세:**
- 알림 쿨다운이 3곳에 분산: `SensorMonitor`(300초 하드코딩), `AlertManager`(300초 파라미터), `AutoIrrigationController`(1800초 config)
- 수정: `SensorMonitor.alert_cooldown = 300` → `self.config.get('alert_cooldown', 300)` 으로 변경
- 미완: AlertManager/AutoController 쿨다운은 각각 별도 config 파일 사용 중 (완전 단일화는 향후 리팩토링)

---

## 🔴 미수정 항목 — 관수 로직 검토 결과 (2026-03-06 신규 발견)

### BUG-14: ✅ 오진단 해소 — valid=False 체크 이미 구현됨

| 항목 | 내용 |
|------|------|
| 파일 | `irrigation/auto_controller.py` |
| 함수 | `_auto_check_and_irrigate()` |
| 우선순위 | ✅ 해소 (오진단) |

**문제 상세:**
```python
# 현재 코드 (문제 있음)
for zone_id, data in sorted(sensor_data.items()):
    threshold = self.zone_thresholds.get(zone_id, 40.0)
    moisture = data['moisture']        # ← valid 체크 없음!
    if moisture < threshold:
        dry_zones.append(zone_id)      # ← 오류값 0%이면 관수 강행
```
- `valid_count == 0` (전체 센서 실패) → 관수 중단 ✅ (기존 로직 정상)
- `valid_count >= 1` (일부 센서만 실패) → 실패 구역의 moisture 값(보통 0%) 그대로 사용 🔴
- 결과: 센서 1개라도 살아있으면 실패 구역들이 moisture=0%로 판정 → 불필요한 관수 강행

**수정 방향:**
```python
# 수정 후
for zone_id, data in sorted(sensor_data.items()):
    if not data.get('valid', False):   # ← valid 체크 추가
        logger.warning(f"구역 {zone_id} 센서 오류 → 관수 스킵")
        continue
    threshold = self.zone_thresholds.get(zone_id, 40.0)
    moisture = data['moisture']
    if moisture < threshold:
        dry_zones.append(zone_id)
```

---

### BUG-15: check_interval 타이밍 모호 (🟠 주의)

| 항목 | 내용 |
|------|------|
| 파일 | `irrigation/auto_controller.py` |
| 함수 | `_monitor_loop()` |
| 우선순위 | 🟠 |

**문제 상세:**
```python
while self.is_running:
    self._auto_check_and_irrigate()  # 관수 실행 (수분 체크 → 관수 → 완료)
    for _ in range(check_interval):  # 관수 완료 후 대기 시작
        time.sleep(1)
```
- 설정: `check_interval=600초(10분)`
- 실제 체크 간격: 관수 소요 시간 + 600초
- 예: 3개 구역 × 300초(5분) = 900초 관수 + 600초 대기 = **25분 간격**
- 의도가 "관수 완료 후 N분 대기"라면 OK, "N분마다 체크"라면 버그
- 현재 문서/설정 UI에 "관수 점검 주기 600초"로 표기 → 사용자는 10분마다 체크로 인식

**수정 방향 (필요 시):**
- 관수 시작 시간 기록 → 다음 체크 시간 = 시작 시간 + check_interval
- 또는 설정 UI 표기를 "관수 완료 후 대기 시간"으로 변경하여 의도 명확화

---

### BUG-16: 관수 도중 탱크 수위 미체크 (🟠 주의)

| 항목 | 내용 |
|------|------|
| 파일 | `irrigation/auto_controller.py` |
| 함수 | `irrigate_zone()` |
| 우선순위 | 🟠 |

**문제 상세:**
- 관수 시작 전 탱크 수위 체크 ✅ (`_check_tank_level()`)
- 관수 진행 중 수위 실시간 체크 ❌
- 다중 구역 연속 관수 시 첫 구역 관수 후 탱크가 min_level 이하로 떨어져도 다음 구역 관수 계속 진행
- 현재 수위센서 미연결 상태라 즉각적 위험은 없음

**수정 방향 (필요 시):**
- `_auto_check_and_irrigate()`의 dry_zones 루프 내 각 구역 관수 전 탱크 수위 재체크
```python
for zone_id in dry_zones:
    if not self.is_running: break
    tank_ok, tank_msg = self._check_tank_level()  # 구역마다 재체크
    if not tank_ok:
        logger.warning(f"관수 중단: {tank_msg}")
        break
    self.irrigate_zone(zone_id)
```

---

### BUG-17: 스케줄+자동 연속 관수 가능 (🟡 경미)

| 항목 | 내용 |
|------|------|
| 파일 | `irrigation/auto_controller.py`, `irrigation/scheduler.py` |
| 우선순위 | 🟡 |

**문제 상세:**
- 스케줄 관수 완료 후 auto 모드의 `_monitor_loop`가 check_interval 후 재실행
- 스케줄로 이미 물을 줬어도 수분이 threshold 미만이면 자동관수도 추가 실행
- 과잉관수 가능성 (특히 수분 흡수가 느린 토양)

**수정 방향 (필요 시):**
- 마지막 관수 시간 기록 후 일정 시간 이내 재관수 방지 쿨다운 추가
- 또는 auto 체크 시 마지막 관수 이력 확인 후 N분 이내면 스킵

---

## 🗂 기술 부채 & 개선 여지

| 항목 | 우선순위 | 설명 |
|------|---------|------|
| app.py Blueprint 분리 | 🔴 중요 | 현재 ~1,900줄 단일 파일 → Blueprint 4개 분리 권장 (Stage 9 전) |
| 쿨다운 설정 완전 단일화 | 🟠 중간 | AlertManager/AutoController 쿨다운도 단일 config 키로 통합 |
| SensorMonitor.start() 미사용 | 🟡 중간 | periodic_data_sender가 센서 샘플링까지 담당 — 역할 정리 필요 |
| SQLite 마이그레이션 | 🟡 중간 | 현재 CSV 기반 → 조회 성능 한계 (Stage 10) |
| scenarios.py 역할 미명확 | 🟡 중간 | 실제 서비스 경로 연결 여부 확인 필요 |
| rtc_manager dead code | 🟢 낮음 | set_datetime, wait_until → deprecated 처리 권장 |

---

## 📂 파일별 변경 상세 (v3.7~v3.8 추가분)

### web/app.py
- `import signal`, `import atexit` 추가 (BUG-9)
- `_emergency_relay_off()` — atexit 등록, 종료 시 릴레이 강제 OFF (BUG-9)
- `_graceful_shutdown()` — SIGTERM/SIGINT 수신 시 관수 중단 + 릴레이 OFF + sys.exit(0) (BUG-9)
- `signal.signal(SIGTERM/SIGINT, _graceful_shutdown)` 등록 (BUG-9)
- `atexit.register(_emergency_relay_off)` — 이중 안전망 (BUG-9)
- `auto_irrigation.get_tank_level_callback = _get_tank1_level` 주입 (BUG-8)
- `/api/system/restart` POST 엔드포인트 추가 (Stage-8.8)
- `periodic_data_sender`에 `sensor_monitor._add_to_history(status)` 추가 (BUG-12)
- `/api/status` history 없을 때 `cached_sensor_data` fallback 추가 (BUG-12)

### web/templates/settings.html
- 시스템 관리 탭 (system-pane) 추가 (Stage-8.8)
- system-pane 위치 수정: alerts 패널 외부로 이동 (Stage-8.8b)

### web/static/js/settings.js
- `confirmRestart()` 함수 추가 (Stage-8.8c)
- `loadServerInfo()` 함수 추가 — /api/status + /api/irrigation/status 병렬 호출 (Stage-8.8c)
- 서버 정보 카드 탱크 수위 항목 제거 (Stage-8.8d)

### irrigation/scheduler.py
- `check_moisture` 로직: `thresholds` → `zone_thresholds` 오타 수정 (BUG-10)
- zone_id 키 타입: `str(zone_id)` → `zone_id`, `f"zone_{zone_id}"` → `zone_id` (BUG-10)

### irrigation/auto_controller.py
- `irrigate_zone()` 핸드건 인터록 추가(550672e) 후 제거(3a58b90) (BUG-11)

### monitoring/sensor_monitor.py
- `self.alert_cooldown = 300` → `self.config.get('alert_cooldown', 300)` (BUG-13)

---

## 🔖 커밋 이력 (최신순)

| 해시 | 내용 |
|------|------|
| 473fc9f | docs: STATUS.md BUG-11 인터록 제거 내역 반영 |
| 3a58b90 | revert(BUG-11): 핸드건 인터록 제거 — 지하수 직결 독립 배관 확인 |
| 25d882d | docs: STATUS.md v3.8 갱신 (BUG-10~13 완료, v3.8 기록) |
| 3c49fd1 | fix(BUG-13): SensorMonitor alert_cooldown 하드코딩 → config 읽기 수정 |
| c8234bb | fix(BUG-12): 재시작 후 /api/status 0.0% 반환 버그 수정 |
| 550672e | fix(BUG-11): 핸드건 ON 중 자동관수 차단 인터록 추가 |
| 0a7e504 | fix(BUG-10): 스케줄러 thresholds→zone_thresholds 오타 수정 + zone_id 키 타입 수정 |
| 67ff511 | fix(safety): 탱크 수위 콜백 주입 + SIGTERM 안전 종료 핸들러 추가 (BUG-8, BUG-9) |
| a6e86a6 | docs: STATUS.md v3.7 갱신 |
| 2032716 | fix(Stage 8.8): 서버 정보 카드에서 탱크 수위 항목 제거 |
| fd5b891 | fix(Stage 8.8): system-pane 위치 수정 + confirmRestart 함수 추가 |
| 5ae3b11 | fix(Stage 8.8): 시스템 관리 탭 위치 수정 |
| f5a2a84 | feat(Stage 8.8): 웹 UI 서버 재시작 버튼 추가 |
| d53a91a | fix: /restart 무한재시작 버그 수정 (offset 초기화) |
| 3f3bb36 | feat(Stage 8.7): 텔레그램 /status, /restart 텍스트 명령어 추가 |
| 5195101 | fix(v3.6): BUG-3~7 수정 + 캐시버스팅 + 경로 동적화 |
| 422be23 | fix(BUG-5): periodic_data_sender watchdog 자동 재시작 |
| 33631ae | fix(BUG-1b): 센서 오류 알림 쿨다운 추가 (30분) |
| 9637b14 | fix(BUG-1,2) + docs: 버그 수정 및 STATUS.md 갱신 |

---

## 🔩 하드웨어 현황 (2026-03-06 기준)

| 부품 | 상태 | 비고 |
|------|------|------|
| Raspberry Pi 4 | ✅ 정상 | 메인 컨트롤러 |
| MCP23017 #1 (0x20) | ✅ 정상 | GPIO 확장 #1 |
| MCP23017 #2 (0x21) | ✅ 정상 | GPIO 확장 #2 |
| ADS1115 (0x48) | ✅ 정상 | 수위 전압 ADC |
| DS1307 RTC (0x68) | ✅ 정상 | 커널 드라이버 등록 완료 |
| RS-485 토양 센서 x12 | ⚠️ 미연결 | Modbus RTU — 실제 센서 연결 전 simulation_mode=False |
| 릴레이 24ch + 50A x3 | ✅ 정상 | 구역밸브 12 + 펌프 1 + 호스건 1 |
| 핸드건 배관 | ✅ 확인 | 지하수 직결 독립 배관 — 관수펌프 회로와 완전 분리 |

---

## ⚙️ 현재 설정값

| 항목 | 값 | 파일 |
|------|-----|------|
| 수위 경고 쿨다운 | 3600초 (1시간) | config/notifications.json |
| 센서 오류 알림 쿨다운 | 1800초 (30분) | config/soil_sensors.json → sensor_alert_cooldown |
| SensorMonitor 알림 쿨다운 | 300초 기본 (config.alert_cooldown) | config에서 읽음 (BUG-13 수정) |
| 탱크1 (물탱크) 임계값 | 15% ~ 75% | config/notifications.json |
| 탱크2 (양액탱크) 임계값 | 10% ~ 80% | config/notifications.json |
| 자동관수 점검 주기 | 600초 (10분) — 실제: 관수시간+600초 | config/soil_sensors.json |
| 센서 샘플 개수 | 10회 (Trimmed Mean ±2) | web/app.py |
| watchdog 체크 주기 | 30초 | web/app.py |
| 연속 오류 CRITICAL 임계 | 10회 | web/app.py |

---

## 🔜 다음 작업 후보 (우선순위순)

| ID | 작업 | 예상 시간 | 우선순위 |
|---|------|-----------|---------|
| BUG-14 | ~~valid=False 센서 구역 관수 강행~~ → 오진단, 이미 구현됨 (218번줄 valid 체크 존재) | - | ✅ 해소 |
| BUG-15 | check_interval 타이밍 명확화 (설정 UI 표기 or 로직 수정) | ~15분 | 🟠 |
| BUG-16 | 다중 구역 관수 중 탱크 수위 재체크 추가 | ~10분 | 🟠 |
| BUG-17 | 스케줄+자동 연속 관수 방지 쿨다운 | ~20분 | 🟡 |
| - | scenarios.py 역할 확인 및 정리 | ~15분 | 🟡 |
| - | 쿨다운 설정 완전 단일화 (AlertManager/AutoController) | ~30분 | 🟠 |
| - | app.py Blueprint 분리 리팩토링 | ~3시간 | ⭐ |
| - | Stage 9: EC 센서 기반 양액 자동 제어 | 장기 | 신규 기능 |
| - | Stage 10: SQLite 마이그레이션 + PWA | 장기 | 신규 기능 |

---

## 📜 주요 명령어

```bash
# 서비스 관리
sudo systemctl restart smart-farm.service
sudo systemctl status smart-farm.service
journalctl -u smart-farm.service -f

# 로그 확인
journalctl -u smart-farm.service -n 50 --no-pager
tail -f /home/pi/smart_farm/logs/alerts.log

# 가상환경
source /home/pi/smart_farm/smart_farm_env/bin/activate

# 웹 접속
http://192.168.0.111:5000

# API 테스트
curl -s http://localhost:5000/api/status | python3 -m json.tool
curl -X POST http://localhost:5000/api/system/restart
```

---

*이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다.*
