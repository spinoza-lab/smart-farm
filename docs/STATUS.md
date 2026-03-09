# 📋 Smart Farm 프로젝트 현황 노트

> 최종 업데이트: 2026-03-09
> 버전: v4.1 (Blueprint 리팩터링 + BUG-14 P0/P1 완료)
> 작업 세션 간 컨텍스트 유지를 위한 내부 노트

---

## ✅ 전체 완료 작업 목록

### v4.1 신규 완료 (2026-03-09)
| ID | 내용 | 파일 | 커밋 |
|---|---|---|---|
| Refactor | Blueprint 분리 (app.py 3000줄 → 5개 bp) | web/blueprints/*.py, web/globals.py | 592fa92 |
| BUG-FIX-TN | auto_controller telegram_notifier 탐색 실패 | web/app.py | 19fa53b |
| BUG-FIX-Z0 | zone_id=0 저장/실행/표시 불가 | irrigation_bp.py, scheduler.py, settings.js, telegram_notifier.py | 여러 커밋 |
| BUG-14 P0-1 | I2C 재시도+fallback+오류통계 | hardware/sensor_reader.py | a299b82 |
| BUG-14 P0-2 | None 샘플 필터링 + SensorReadError | monitoring/sensor_monitor.py | 501df2a, 81c7e71 |
| BUG-14 P1 | None 전압 허용 + 연속 카운터 + 복구 감지 | monitoring/alert_manager.py | bd831c1 |

---

### v3.5 ~ v3.8 완료 (상세는 CHANGELOG.md 참조)
- Bug-N1 ~ Bug-A1, BUG-1 ~ BUG-16 전체 완료

### v4.0 완료 (2026-03-09)
- Stage 9: 관수 주기 관리 시스템 (`32d76d5`)
- BUG-17 WONTFIX: Stage 9로 근본 해결

---

## 🔴 미완료 / 진행 예정

### BUG-14 P2 (다음 작업)
- `/api/status` 응답에 `sensor_errors`, `sensor_stats` 필드 추가
- 웹 대시보드에 센서 오류 채널 시각적 표시

---

## 🗂 기술 부채 & 개선 여지
| 항목 | 우선순위 | 설명 |
|------|---------|------|
| BUG-14 P2 | 🔴 중요 | /api/status 센서 오류 필드 + UI 표시 |
| 쿨다운 설정 완전 단일화 | 🟠 중간 | AlertManager/AutoController 쿨다운 단일 config 키 통합 |
| SQLite 마이그레이션 | 🟡 중간 | 현재 CSV 기반 → 조회 성능 한계 (Stage 10) |
| rtc_manager dead code | 🟢 낮음 | set_datetime, wait_until → deprecated 처리 권장 |

---

## 🔖 커밋 이력 (최신순, v4.1 기준)
| 해시 | 내용 |
|------|------|
| `bd831c1` | fix(alert): None 전압 허용 + 연속 오류 카운터 + 복구 감지 (BUG-14 P1) |
| `81c7e71` | fix(sensor): 패치③ 잔재 else 제거 (SyntaxError 수정) |
| `501df2a` | fix(sensor): None 샘플 필터링 + SensorReadError + 수위 None 처리 (BUG-14 P0-2) |
| `a299b82` | fix(sensor): I2C 예외 처리 + 재시도(2회) + fallback + 오류 통계 (BUG-14 P0-1) |
| `19fa53b` | fix: auto_controller telegram_notifier 탐색 실패 수정 |
| `592fa92` | refactor: Blueprint 분리 (web/app.py → 5개 blueprint) |
| `32d76d5` | feat(S9): 관수 주기 관리 시스템 구현 |
| `473fc9f` | docs: STATUS.md BUG-11 인터록 제거 내역 반영 |
| `3c49fd1` | fix(BUG-13): SensorMonitor alert_cooldown 하드코딩 → config 읽기 수정 |
| `c8234bb` | fix(BUG-12): 재시작 후 /api/status 0.0% 반환 버그 수정 |
| `0a7e504` | fix(BUG-10): 스케줄러 thresholds→zone_thresholds 오타 수정 |
| `67ff511` | fix(safety): 탱크 수위 콜백 주입 + SIGTERM 안전 종료 핸들러 추가 |

---

## 🔩 하드웨어 현황 (2026-03-09 기준)
| 부품 | 상태 | 비고 |
|------|------|------|
| Raspberry Pi 4 | ✅ 정상 | 메인 컨트롤러 |
| MCP23017 #1 (0x20) | ✅ 정상 | GPIO 확장 #1 |
| MCP23017 #2 (0x21) | ✅ 정상 | GPIO 확장 #2 |
| ADS1115 (0x48) | ✅ 정상 | 수위 전압 ADC |
| DS1307 RTC (0x68) | ✅ 정상 | 커널 드라이버 등록 완료 |
| RS-485 토양 센서 x12 | ⚠️ 미연결 | Modbus RTU — 실제 연결 전 simulation_mode |
| 릴레이 24ch + 50A x3 | ✅ 정상 | 구역밸브 12 + 펌프 1 + 호스건 1 |
| 핸드건 배관 | ✅ 확인 | 지하수 직결 독립 배관 — 관수펌프 회로와 완전 분리 |

---

## ⚙️ 현재 설정값
| 항목 | 값 | 파일 |
|------|-----|------|
| 수위 경고 쿨다운 | 3600초 (1시간) | config/notifications.json |
| 센서 연속 오류 CRITICAL 임계 | 5회 | monitoring/alert_manager.py |
| 탱크1 (물탱크) 임계값 | 15% ~ 75% | config/notifications.json |
| 탱크2 (양액탱크) 임계값 | 10% ~ 80% | config/notifications.json |
| 자동관수 점검 주기 | 300초 | config/soil_sensors.json |
| 센서 샘플 개수 | 10회 (Trimmed Mean ±2) | config/sensor_calibration.json |
| 유효 샘플 최소치 | 5회 (sample_count // 2) | monitoring/sensor_monitor.py |
| I2C 재시도 횟수 | 2회 (총 3회, 50ms 간격) | hardware/sensor_reader.py |
| watchdog 체크 주기 | 30초 | web/app.py |

---

## 🔜 다음 작업 후보 (우선순위순)
| ID | 작업 | 예상 시간 | 우선순위 |
|---|------|-----------|---------|
| BUG-14 P2 | /api/status 센서 오류 필드 + 웹 UI 표시 | ~30분 | 🔴 |
| - | PR 생성: refactor/blueprint → main | ~10분 | 🔴 |
| - | 쿨다운 설정 완전 단일화 | ~30분 | 🟠 |
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
curl -s http://localhost:5000/api/notifications/status | python3 -m json.tool
curl -X POST http://localhost:5000/api/notifications/test
```

---

*이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다.*
