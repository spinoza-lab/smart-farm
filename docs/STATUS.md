# 📋 Smart Farm 프로젝트 현황 노트

> 최종 업데이트: 2026-03-05
> 버전: v3.6 (안정화 완료)
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
| BUG-1 | 토양센서 읽기 실패 시 시뮬레이션 모드 아닐 경우 관수 중단 + 텔레그램 경고 | irrigation/auto_controller.py | 9637b14 |
| BUG-2 | cooldown_seconds 즉시 반영 누락 + send_message → send 오타 수정 | web/app.py, monitoring/alert_manager.py | 9637b14 |
| BUG-1b | 센서 오류 알림 무한 반복 방지 — 30분(1800초) 쿨다운 추가 | irrigation/auto_controller.py | 33631ae |
| BUG-3 | rtc_manager.set_datetime() no-op 경고 로그 추가 | hardware/rtc_manager.py | 5195101 |
| BUG-4 | rtc_manager.wait_until() 메인스레드 호출 시 즉시 abort 가드 추가 | hardware/rtc_manager.py | 5195101 |
| BUG-5 | periodic_data_sender 스레드 종료 시 watchdog 자동 재시작 (30초 내) | web/app.py | 422be23 |
| BUG-6 | 중복 알림 가능성 확인 → sensor_monitor 콜백 미등록, 실제 중복 없음 확인 | (해소) | 5195101 |
| BUG-7 | 하드코딩 절대경로 /home/pi/smart_farm → _BASE_DIR 동적화 (8개 파일) | 하단 참조 | 5195101 |
| Cache | JS/CSS 캐시 버스팅 — 서버 시작 타임스탬프 기반 ?v={{ cache_ver }} | web/app.py, 4개 템플릿 | 5195101 |
| Jinja2 | url_for()?v= 잘못된 위치 → url_for() }}?v= 수정 (SyntaxError 해결) | 4개 템플릿 | defbdea |

---

## 📂 파일별 변경 상세

### web/app.py
- _BASE_DIR = Path(__file__).resolve().parent.parent 추가 (BUG-7)
- inject_cache_ver() context_processor 추가 (Cache)
- consecutive_errors 카운터 추가 (BUG-5)
- time.sleep(10) try/except 보호 (BUG-5)
- 연속 10회 오류 시 텔레그램 CRITICAL 알림 (BUG-5)
- _start_periodic_sender() 헬퍼 함수 분리 (BUG-5)
- _watchdog_loop() — 30초마다 is_alive() 체크 후 자동 재시작 (BUG-5)
- init_monitoring_system() — SenderWatchdog 스레드 시작 (BUG-5)
- cooldown_seconds 즉시 반영 로직 (BUG-2)
- 멀티라인 문자열 SyntaxError 수정 (누락된 \n 이스케이프)

### irrigation/auto_controller.py
- 센서 읽기 실패 → 시뮬레이션 모드 아닐 경우 관수 중단 + 텔레그램 경고 (BUG-1)
- _send_sensor_alert() — 30분 쿨다운 추가 (BUG-1b)
- f-string 멀티라인 SyntaxError + 들여쓰기 오류 수정 (483행)
- _BASE_DIR 동적 경로 적용 (BUG-7)

### hardware/rtc_manager.py
- set_datetime() → logging.warning() 추가, no-op 명시 (BUG-3)
- wait_until() → 메인스레드 호출 감지 시 즉시 return + error 로그 (BUG-4)

### monitoring/sensor_monitor.py
- _BASE_DIR 동적 경로 적용 (BUG-7)
- 잘못 삽입된 from pathlib import Path (메서드 내부) 제거 후 최상단 이동

### monitoring/telegram_notifier.py
- _BASE_DIR 동적 경로 적용 (BUG-7)

### monitoring/alert_manager.py
- _BASE_DIR 동적 경로 적용 (BUG-7)
- send_message → send 오타 수정 (BUG-2)

### monitoring/data_logger.py
- _BASE_DIR 동적 경로 적용 (BUG-7)

### hardware/modbus_soil_sensor.py
- _BASE_DIR 동적 경로 적용 (BUG-7)

### irrigation/scheduler.py
- _BASE_DIR 동적 경로 적용 (BUG-7)

### web/templates/*.html (index, irrigation, settings, analytics)
- ?v=N 하드코딩 → ?v={{ cache_ver }} 교체 (Cache)
- Jinja2 url_for()?v= → url_for() }}?v= 위치 수정 (Jinja2 SyntaxError)

### scripts/ (신규 폴더)
- fix_bug1_simulation_fallback.sh
- fix_bug1b_sensor_alert_cooldown.sh
- fix_bug2_cooldown_sync.sh
- fix_bug5_thread_watchdog.sh
- fix_rtc_manager.sh
- make_docs.sh
- make_status_note.sh
- update_status.sh

---

## 🔖 커밋 이력 (2026-03-05)

| 해시 | 내용 |
|------|------|
| 9637b14 | fix(BUG-1,2) + docs: 버그 수정 및 STATUS.md 갱신 |
| 33631ae | fix(BUG-1b): 센서 오류 알림 쿨다운 추가 (30분) |
| 29480ca | docs: STATUS.md BUG-1b 완료 기록 반영 |
| 422be23 | fix(BUG-5): periodic_data_sender watchdog 자동 재시작 |
| 5195101 | fix(v3.6): BUG-3~7 수정 + 캐시버스팅 + 경로 동적화 |
| a70c396 | docs: STATUS.md 전체 완료 기록 |
| defbdea | fix: Jinja2 캐시버스팅 위치 오류 수정 |

---

## 🔩 하드웨어 현황 (2026-03-05 기준)

| 부품 | 상태 | 비고 |
|------|------|------|
| Raspberry Pi 4 | ✅ 정상 | 메인 컨트롤러 |
| MCP23017 #1 (0x20) | ✅ 정상 | GPIO 확장 #1 |
| MCP23017 #2 (0x21) | ✅ 정상 | GPIO 확장 #2 |
| ADS1115 (0x48) | ✅ 정상 | 수위 전압 ADC |
| DS1307 RTC (0x68) | ✅ 정상 | 커널 드라이버 등록 완료 |
| RS-485 토양 센서 x12 | ✅ 정상 | Modbus RTU |
| 릴레이 24ch + 50A x3 | ✅ 정상 | 구역밸브 12 + 펌프 1 + 호스건 1 |

---

## ⚙️ 현재 설정값

| 항목 | 값 | 파일 |
|------|-----|------|
| 수위 경고 쿨다운 | 3600초 (1시간) | config/notifications.json |
| 센서 오류 알림 쿨다운 | 1800초 (30분) | config/soil_sensors.json → sensor_alert_cooldown |
| 탱크1 (물탱크) 임계값 | 15% ~ 75% | config/notifications.json |
| 탱크2 (양액탱크) 임계값 | 10% ~ 80% | config/notifications.json |
| 자동관수 점검 주기 | 600초 (10분) | config/soil_sensors.json |
| 센서 샘플 개수 | 10회 (Trimmed Mean ±2) | web/app.py |
| watchdog 체크 주기 | 30초 | web/app.py |
| 연속 오류 CRITICAL 임계 | 10회 | web/app.py |

---

## 🗂 기술 부채 & 개선 여지

| 항목 | 우선순위 | 설명 |
|------|---------|------|
| app.py Blueprint 분리 | 🔴 중요 | 1,777줄 단일 파일 → Blueprint 4개 분리 권장 (Stage 9 전) |
| SensorMonitor.start() 미사용 | 🟡 중간 | periodic_data_sender가 센서 샘플링까지 담당 — 역할 정리 필요 |
| SQLite 마이그레이션 | 🟡 중간 | 현재 CSV 기반 → 조회 성능 한계 (Stage 10) |
| scenarios.py 역할 미명확 | 🟡 중간 | 실제 서비스 경로 연결 여부 확인 필요 |
| rtc_manager dead code | 🟢 낮음 | set_datetime, wait_until → deprecated 처리 권장 |

---

## 🔜 다음 작업 후보

| 작업 | 예상 시간 | 우선순위 |
|------|-----------|---------|
| 텔레그램 /restart, /status 텍스트 명령 추가 | ~1시간 | ⭐⭐ |
| 웹 UI 서버 재시작 버튼 (settings.html) | ~30분 | ⭐⭐ |
| scenarios.py 역할 확인 및 정리 | ~15분 | ⭐ |
| app.py Blueprint 분리 리팩토링 | ~3시간 | ⭐ |
| Stage 9: EC 센서 기반 양액 자동 제어 | 장기 | 신규 기능 |
| Stage 10: SQLite 마이그레이션 + PWA | 장기 | 신규 기능 |

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
```

---

*이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다.*
