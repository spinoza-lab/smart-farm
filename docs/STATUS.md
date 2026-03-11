# 📋 Smart Farm 프로젝트 현황 노트

> 최종 업데이트: 2026-03-11
> 버전: v0.4.1 (Blueprint 리팩터링 + BUG-14 P0/P1/P2 완료)
> v0.5.0 개발 예정: 대기환경 모니터링 (SHT30 × 12 + WH65LP 기상 스테이션)
> 작업 세션 간 컨텍스트 유지를 위한 내부 노트

---

## ✅ 전체 완료 작업 목록

### v0.4.1 신규 완료 (2026-03-09)
| ID | 내용 | 파일 | 커밋 |
|---|---|---|---|
| Refactor | Blueprint 분리 (app.py 3000줄 → 5개 bp) | web/blueprints/*.py, web/globals.py | 592fa92 |
| BUG-FIX-TN | auto_controller telegram_notifier 탐색 실패 | web/app.py | 19fa53b |
| BUG-FIX-Z0 | zone_id=0 저장/실행/표시 불가 | irrigation_bp.py, scheduler.py, settings.js, telegram_notifier.py | 846b47c, f900904 |
| BUG-14 P0-1 | I2C 재시도+fallback+오류통계 | hardware/sensor_reader.py | a299b82 |
| BUG-14 P0-2 | None 샘플 필터링 + SensorReadError | monitoring/sensor_monitor.py | 501df2a, 81c7e71 |
| BUG-14 P1 | None 전압 허용 + 연속 카운터 + 복구 감지 | monitoring/alert_manager.py | bd831c1 |
| BUG-14 P2 | /api/status sensor_errors·sensor_stats 추가 | web/blueprints/monitoring_bp.py | 592a6ba |

---

### BUG-14 완료 상세 — I2C 센서 장애 대응 (전체 완료 ✅)

**오류 처리 흐름 (완성):**
```
I2C 읽기 실패
  → sensor_reader: 재시도 2회(50ms 간격) → fallback(마지막 정상값) / None 반환
  → sensor_monitor: None 샘플 필터링 → 유효 샘플 < min_valid_samples → SensorReadError
  → _monitor_loop: 10초 대기 후 재시도 (서비스 중단 없음)
  → alert_manager: 1회 WARNING / 5회 CRITICAL Telegram 알림 + 복구 시 INFO 알림
  → /api/status: voltages[null], sensor_errors{chX: true}, sensor_stats 노출
```

| 단계 | 커밋 | 파일 | 내용 |
|------|------|------|------|
| P0-1 | `a299b82` | `hardware/sensor_reader.py` | I2C 재시도 2회 + fallback + 오류통계 |
| P0-2 | `501df2a` | `monitoring/sensor_monitor.py` | None 샘플 필터링 + SensorReadError |
| P0-2 수정 | `81c7e71` | `monitoring/sensor_monitor.py` | SyntaxError 잔재 else 제거 |
| P1 | `bd831c1` | `monitoring/alert_manager.py` | None 전압 허용 + 연속 카운터 + 복구 감지 |
| P2 | `592a6ba` | `web/blueprints/monitoring_bp.py` | /api/status sensor_errors·sensor_stats |

---

### v0.3.5 ~ v0.3.8 완료 (상세는 CHANGELOG.md 참조)
- Bug-N1 ~ Bug-A1, BUG-1 ~ BUG-16 전체 완료

### v0.4.0 완료 (2026-03-09)
- Stage 9: 관수 주기 관리 시스템 (`32d76d5`)
- BUG-17 WONTFIX: Stage 9로 근본 해결

---

## 🚧 v0.5.0 개발 계획 — 대기환경 모니터링 (Stage 10)

> 하드웨어 주문 완료 (2026-03-11). 배송 후 구현 예정.

### 추가 하드웨어
| 부품 | 수량 | 용도 | 상태 |
|------|------|------|------|
| CDSENET EID041-G01 (SHT30, RS-485 Modbus) | 12개 | 구역별 대기 온도·습도 | 📦 주문 완료 |
| MISOL WH65LP (RS-485, 커스텀 프로토콜) | 1개 | 외부 기상 관측 | 📦 주문 완료 |
| MAX485 모듈 (DI/DE/RE/RO/VCC/A/B/GND 핀형) | 2개 | RS-485 Bus 2/3 | 🛒 구매 필요 |
| 120Ω 종단저항 | 4개 | Bus 1/2 종단 | 🛒 구매 필요 |

### 추가 RS-485 버스 구성

| 버스 | UART | /dev 경로 | TX GPIO (물리핀) | RX GPIO (물리핀) | DE/RE | 장치 | 통신속도 |
|------|------|----------|----------------|----------------|-------|------|---------|
| Bus 2 | UART3 | /dev/ttyAMA2 | GPIO4 (Pin 7) | GPIO5 (Pin 29) | GPIO17 (Pin 11) | SHT30 ×12 | 9600 bps |
| Bus 3 | UART4 | /dev/ttyAMA3 | GPIO8 (Pin 24) | GPIO9 (Pin 21) | GND (Pin 25) | WH65LP ×1 | 9600 bps |

`/boot/firmware/config.txt`에 추가:
```
dtoverlay=uart3
dtoverlay=uart4
```

### 추가 소프트웨어 파일

| 파일 | 역할 | 상태 |
|------|------|------|
| `config/air_sensors.json` | SHT30 Modbus 설정 (포트, baudrate, 센서 목록) | 🔧 작성 필요 |
| `config/weather_station.json` | WH65LP 설정 (포트, baudrate, 위치) | 🔧 작성 필요 |
| `hardware/air_sensor_reader.py` | SHT30 Modbus RTU 드라이버 (DE/RE 제어 포함) | 🔧 작성 필요 |
| `hardware/weather_station_reader.py` | WH65LP 25바이트 패킷 파서 | 🔧 작성 필요 |
| `monitoring/environment_monitor.py` | 백그라운드 폴링 스레드 (SHT30: 60s, WH65LP: 16s) | 🔧 작성 필요 |
| `web/blueprints/environment_bp.py` | REST API (`/api/environment`, `/air`, `/weather`) | 🔧 작성 필요 |
| `web/globals.py` | `air_sensor_manager`, `environment_monitor` 전역 변수 추가 | 🔧 수정 필요 |
| `web/app.py` | `environment_bp` 등록 + EnvironmentMonitor 시작 | 🔧 수정 필요 |
| `web/templates/index.html` | 대기환경 대시보드 섹션 추가 | 🔧 수정 필요 |

### SHT30 레지스터 맵 (CDSENET EID041-G01)
| 레지스터 | 데이터 | 배율 | 비고 |
|---------|------|------|------|
| 0x0000 | 온도 (int16 signed) | ×0.1 °C | raw ≥ 32768 → raw - 65536 |
| 0x0001 | 습도 (uint16) | ×0.1 %RH | - |

> ⚠️ 실제 레지스터 주소는 설명서 수령 후 재확인 필요

### 구현 순서 (예상 소요시간)
1. `config/air_sensors.json`, `config/weather_station.json` 생성 (30분)
2. `hardware/air_sensor_reader.py` 구현 + 시뮬레이션 테스트 (2시간)
3. `hardware/weather_station_reader.py` 구현 + 로우 패킷 로그 검증 (3시간)
4. `web/globals.py` 전역 변수 추가 (30분)
5. `monitoring/environment_monitor.py` 백그라운드 스레드 구현 (2시간)
6. `web/blueprints/environment_bp.py` API 구현 (1시간)
7. `web/templates/index.html` 대시보드 UI 추가 (1시간)
8. `web/app.py` 통합 등록 + 전체 테스트 (1시간)

---

## 🟡 미완료 / 진행 예정

### 기술 부채
| 항목 | 우선순위 | 설명 |
|------|---------|------|
| 대시보드 센서 오류 UI | 🟠 중간 | 오류 채널 시각적 표시 (빨간 배지 등) |
| 쿨다운 설정 완전 단일화 | 🟠 중간 | AlertManager/AutoController 쿨다운 단일 config 키 통합 |
| sensor_voltage_thresholds | 🟠 중간 | 0.1V/3.2V 하드코딩 → notifications.json으로 이동 |
| globals.py SensorErrorState | 🟡 낮음 | 설계는 있으나 미구현 — 필요 시 추가 |
| SQLite 마이그레이션 | 🟡 중간 | 현재 CSV 기반 → 조회 성능 한계 |
| rtc_manager dead code | 🟢 낮음 | set_datetime, wait_until → deprecated 처리 권장 |

---

## 🔖 커밋 이력 (최신순, v0.4.1 기준)
| 해시 | 내용 |
|------|------|
| `592a6ba` | feat(api): /api/status sensor_errors·sensor_stats 추가 (BUG-14 P2) |
| `e88f333` | docs: v0.4.1 문서 업데이트 |
| `bd831c1` | fix(alert): None 전압 허용 + 연속 오류 카운터 + 복구 감지 (BUG-14 P1) |
| `81c7e71` | fix(sensor): 패치③ 잔재 else 제거 (SyntaxError 수정) |
| `501df2a` | fix(sensor): None 샘플 필터링 + SensorReadError + 수위 None 처리 (BUG-14 P0-2) |
| `a299b82` | fix(sensor): I2C 예외 처리 + 재시도(2회) + fallback + 오류 통계 (BUG-14 P0-1) |
| `f900904` | fix(zone_id=0): irrigation_bp/scheduler/telegram_notifier 수정 |
| `846b47c` | fix(zone_id=0): Python/JS falsy 0 처리 수정 |
| `19fa53b` | fix: auto_controller telegram_notifier 탐색 실패 수정 |
| `592fa92` | refactor: Blueprint 분리 (web/app.py → 5개 blueprint) |
| `32d76d5` | feat(S9): 관수 주기 관리 시스템 구현 |
| `3c49fd1` | fix(BUG-13): SensorMonitor alert_cooldown 하드코딩 → config 읽기 수정 |
| `c8234bb` | fix(BUG-12): 재시작 후 /api/status 0.0% 반환 버그 수정 |
| `0a7e504` | fix(BUG-10): 스케줄러 thresholds→zone_thresholds 오타 수정 |
| `67ff511` | fix(safety): 탱크 수위 콜백 주입 + SIGTERM 안전 종료 핸들러 추가 |

---

## 🔩 하드웨어 현황 (2026-03-11 기준)
| 부품 | 상태 | 비고 |
|------|------|------|
| Raspberry Pi 4 | ✅ 정상 | 메인 컨트롤러 |
| MCP23017 #1 (0x20) | ✅ 정상 | GPIO 확장 #1 |
| MCP23017 #2 (0x21) | ✅ 정상 | GPIO 확장 #2 |
| ADS1115 (0x48) | ✅ 정상 | 수위 전압 ADC |
| DS1307 RTC (0x68) | ✅ 정상 | 커널 드라이버 등록 완료 |
| RS-485 토양 센서 x12 | ⚠️ 미연결 | simulation_mode=false |
| QDY30A 수위 센서 x2 | ⚠️ 미연결 | 전압 분배 회로 구성 후 연결 예정 |
| 6채널 릴레이 보드 x4 (24ch) | ⚠️ 미연결 | 외부 5V 전원 연결 후 배선 예정 |
| MAX485 모듈 #1 | ⚠️ 미연결 | RS-485 Bus 1 (토양 센서) 구성 예정 |
| MAX485 모듈 #2 | 🛒 구매 필요 | RS-485 Bus 2 (대기 온습도) |
| MAX485 모듈 #3 | 🛒 구매 필요 | RS-485 Bus 3 (기상 스테이션) |
| RD-125B (5V+24V SMPS) | ✅ 구매 완료 | 릴레이+센서 전원 통합 |
| AC 24V 트랜스 25W | ✅ 구매 완료 | 전자밸브 전원 |
| AC 24V 전자밸브 | ✅ 보유 | 구역밸브 12+기타 |
| 한일펌프 PA-1688SS | ✅ 보유 | 220V 2HP 자흡식 |
| SSR 40A + 방열판 | 🛒 구매 예정 | 펌프 제어용 |
| 10kΩ 저항 x4 | 🛒 필요 | 수위 센서 전압 분배 |
| 120Ω 종단저항 x4 | 🛒 필요 | RS-485 Bus 1/2 양끝 종단 |
| **CDSENET EID041-G01 (SHT30) x12** | **📦 주문 완료** | **대기 온습도 RS-485 Modbus** |
| **MISOL WH65LP** | **📦 주문 완료** | **기상 스테이션 RS-485** |

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
| 작업 | 예상 시간 | 우선순위 |
|------|-----------|---------|
| 쿨다운 설정 완전 단일화 | ~30분 | 🟠 |
| sensor_voltage_thresholds config 분리 | ~20분 | 🟠 |
| 대시보드 센서 오류 UI 표시 | ~1시간 | 🟠 |
| **[v0.5.0] config.txt UART3/4 오버레이 추가** | **~10분** | **🔴 신규 (하드웨어 수령 전 선행 가능)** |
| **[v0.5.0] air_sensor_reader.py 구현** | **~2시간** | **🔴 신규** |
| **[v0.5.0] weather_station_reader.py 구현** | **~3시간** | **🔴 신규** |
| **[v0.5.0] environment_monitor + API + UI** | **~4시간** | **🔴 신규** |
| Stage 10: SQLite 마이그레이션 | 장기 | 🟡 |

---

## 📜 주요 명령어
```bash
sudo systemctl restart smart-farm.service
sudo systemctl status smart-farm.service
journalctl -u smart-farm.service -f
journalctl -u smart-farm.service -n 50 --no-pager
source /home/pi/smart_farm_env/bin/activate
curl -s http://localhost:5000/api/status | python3 -m json.tool
curl -s http://localhost:5000/api/environment | python3 -m json.tool   # v0.5.0 추가 예정
ls -la /dev/ttyAMA*   # UART 포트 확인
```

---

*이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다.*
