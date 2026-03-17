# 📋 Smart Farm 프로젝트 현황 노트

> 최종 업데이트: 2026-03-17
> 버전: v0.5.0 (Stage 10: 대기 환경 모니터링 소프트웨어 완료)
> 작업 세션 간 컨텍스트 유지를 위한 내부 노트

---

## ✅ 전체 완료 작업 목록

### v0.5.0 신규 완료 (2026-03-17)
| ID | 내용 | 파일 |
|---|---|---|
| Stage 10 | SHT30 × 12 Modbus RTU 드라이버 구현 | `hardware/air_sensor_reader.py` |
| Stage 10 | WH65LP 25바이트 커스텀 패킷 파서 구현 | `hardware/weather_station_reader.py` |
| Stage 10 | 환경 모니터링 백그라운드 스레드 | `monitoring/environment_monitor.py` |
| Stage 10 | 환경 REST API Blueprint (6 엔드포인트) | `web/blueprints/environment_bp.py` |
| Stage 10 | globals.py 환경 전역 변수 추가 | `web/globals.py` |
| Stage 10 | app.py Blueprint 등록 + 초기화 통합 | `web/app.py` |
| Stage 10 | 대시보드 환경 모니터링 탭 추가 | `web/templates/index.html` |
| Stage 10 | 분석 페이지 환경 데이터 탭 추가 | `web/templates/analytics.html` |
| Stage 10 | 대시보드 JS 백그라운드 폴링 추가 | `web/static/js/dashboard.js` |
| Stage 10 | SHT30 설정 파일 생성 | `config/air_sensors.json` |
| Stage 10 | WH65LP 설정 파일 생성 | `config/weather_station.json` |

### v0.4.1 완료 (2026-03-09)
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

## 🔌 REST API 전체 목록 (v0.5.0 기준)

### 환경 모니터링 (신규, v0.5.0)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/environment` | 전체 환경 데이터 (공기 + 기상) |
| GET | `/api/environment/air` | 전체 SHT30 센서 데이터 |
| GET | `/api/environment/air/<id>` | 특정 구역 SHT30 데이터 |
| GET | `/api/environment/weather` | WH65LP 기상 데이터 |
| GET | `/api/environment/history/air` | 대기 센서 이력 (최근 100 스냅샷) |
| GET | `/api/environment/history/weather` | 기상 이력 (최근 100 스냅샷) |

---

## 🟡 미완료 / 진행 예정

### Stage 10 하드웨어 연결 (하드웨어 수령 후)
| 항목 | 설명 |
|------|------|
| SHT30 실센서 연결 | `simulation_mode: false` 전환 + /dev/ttyAMA2 배선 |
| WH65LP 실센서 연결 | `simulation_mode: false` 전환 + /dev/ttyAMA3 배선 |
| UART 오버레이 활성화 | `/boot/firmware/config.txt` dtoverlay=uart3/uart4 추가 후 재부팅 |
| MAX485 #2/#3 연결 | Bus 2 (GPIO4/5/17), Bus 3 (GPIO8/9/GND) 배선 |
| 종단저항 설치 | Bus 1/2 양끝 120Ω 각 1개 (총 4개) |

### 기술 부채
| 항목 | 우선순위 | 설명 |
|------|---------|------|
| 대시보드 센서 오류 UI | 🟠 중간 | 오류 채널 시각적 표시 (빨간 배지 등) |
| 쿨다운 설정 완전 단일화 | 🟠 중간 | AlertManager/AutoController 쿨다운 단일 config 키 통합 |
| sensor_voltage_thresholds | 🟠 중간 | 0.1V/3.2V 하드코딩 → notifications.json으로 이동 |
| globals.py SensorErrorState | 🟡 낮음 | 설계는 있으나 미구현 — 필요 시 추가 |
| SQLite 마이그레이션 | 🟡 중간 | 현재 CSV 기반 → 조회 성능 한계 |
| rtc_manager dead code | 🟢 낮음 | set_datetime, wait_until → deprecated 처리 권장 |
| 환경 데이터 이력 차트 | 🟡 낮음 | 분석 페이지에 시계열 차트 추가 (현재 스냅샷만) |

---

## 🔖 커밋 이력 (최신순, v0.5.0 기준)
| 해시 | 내용 |
|------|------|
| *(예정)* | feat(Stage10): 대기 환경 모니터링 추가 (SHT30×12 + WH65LP + UI) |
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

## 🔩 하드웨어 현황 (2026-03-17 기준)
| 부품 | 상태 | 비고 |
|------|------|------|
| Raspberry Pi 4 | ✅ 정상 | 메인 컨트롤러 |
| MCP23017 #1 (0x20) | ✅ 정상 | GPIO 확장 #1 |
| MCP23017 #2 (0x21) | ✅ 정상 | GPIO 확장 #2 |
| ADS1115 (0x48) | ✅ 정상 | 수위 전압 ADC |
| DS1307 RTC (0x68) | ✅ 정상 | 커널 드라이버 등록 완료 |
| RS-485 토양 센서 x12 | ⚠️ 미연결 | simulation_mode=false, 연결 시 즉시 동작 |
| QDY30A 수위 센서 x2 | ⚠️ 미연결 | 전압 분배 회로 구성 후 연결 예정 |
| 6채널 릴레이 보드 x4 (24ch) | ⚠️ 미연결 | 외부 5V 전원 연결 후 배선 예정 |
| MAX485 모듈 #1 | ⚠️ 미연결 | RS-485 Bus 1 (토양 센서) |
| MAX485 모듈 #2 | 🛒 구매 필요 | RS-485 Bus 2 (대기 온습도) |
| MAX485 모듈 #3 | 🛒 구매 필요 | RS-485 Bus 3 (기상 스테이션) |
| RD-125B (5V+24V SMPS) | ✅ 구매 완료 | 릴레이+센서 전원 통합 |
| AC 24V 트랜스 25W | ✅ 구매 완료 | 전자밸브 전원 |
| AC 24V 전자밸브 | ✅ 보유 | 구역밸브 12+기타 |
| 한일펌프 PA-1688SS | ✅ 보유 | 220V 2HP 자흡식 |
| SSR 40A + 방열판 | 🛒 구매 예정 | 펌프 제어용 |
| 10kΩ 저항 x4 | 🛒 필요 | 수위 센서 전압 분배 |
| 120Ω 종단저항 x4 | 🛒 필요 | RS-485 Bus 1/2 양끝 종단 |
| **CDSENET EID041-G01 (SHT30) x12** | **📦 배송 중** | **대기 온습도 RS-485 Modbus, 소프트웨어 완료** |
| **MISOL WH65LP** | **📦 배송 중** | **기상 스테이션 RS-485, 소프트웨어 완료** |

---

## ⚙️ 현재 설정값
| 항목 | 값 | 파일 |
|------|-----|------|
| 수위 경고 쿨다운 | 3600초 (1시간) | config/notifications.json |
| 센서 연속 오류 CRITICAL 임계 | 5회 | monitoring/alert_manager.py |
| 탱크1 (물탱크) 임계값 | 20% ~ 90% | config/notifications.json |
| 탱크2 (양액탱크) 임계값 | 20% ~ 90% | config/notifications.json |
| 자동관수 점검 주기 | 300초 | config/soil_sensors.json |
| 센서 샘플 개수 | 10회 (Trimmed Mean ±2) | config/sensor_calibration.json |
| 유효 샘플 최소치 | 5회 (sample_count // 2) | monitoring/sensor_monitor.py |
| I2C 재시도 횟수 | 2회 (총 3회, 50ms 간격) | hardware/sensor_reader.py |
| watchdog 체크 주기 | 30초 | web/app.py |
| **SHT30 폴링 주기** | **60초** | **monitoring/environment_monitor.py** |
| **WH65LP 수신 주기** | **16초 (자동 송출)** | **monitoring/environment_monitor.py** |
| **SHT30 simulation_mode** | **true (하드웨어 수령 전)** | **config/air_sensors.json** |
| **WH65LP simulation_mode** | **true (하드웨어 수령 전)** | **config/weather_station.json** |

---

## 🔜 다음 작업 후보 (우선순위순)
| 작업 | 예상 시간 | 우선순위 |
|------|-----------|---------|
| **Stage 10 커밋 & 푸시 (v0.5.0 태그)** | **~5분** | **🔴 즉시** |
| 하드웨어 수령 후 simulation_mode=false 전환 | ~10분 | 🔴 (하드웨어 수령 시) |
| UART3/4 dtoverlay 활성화 + 재부팅 | ~10분 | 🔴 (하드웨어 수령 시) |
| MAX485 #2/#3 배선 + 실센서 테스트 | ~2~3시간 | 🔴 (하드웨어 수령 시) |
| 쿨다운 설정 완전 단일화 | ~30분 | 🟠 |
| sensor_voltage_thresholds config 분리 | ~20분 | 🟠 |
| 대시보드 센서 오류 UI 표시 | ~1시간 | 🟠 |
| 환경 데이터 이력 차트 (분석 페이지) | ~2시간 | 🟡 |
| SQLite 마이그레이션 | 장기 | 🟡 |

---

## 📜 주요 명령어
```bash
sudo systemctl restart smart-farm.service
sudo systemctl status smart-farm.service
journalctl -u smart-farm.service -f
journalctl -u smart-farm.service -n 50 --no-pager
source /home/pi/smart_farm_env/bin/activate
curl -s http://localhost:5000/api/status | python3 -m json.tool
curl -s http://localhost:5000/api/environment | python3 -m json.tool
curl -s http://localhost:5000/api/environment/air | python3 -m json.tool
curl -s http://localhost:5000/api/environment/weather | python3 -m json.tool
ls -la /dev/ttyAMA*   # UART 포트 확인

# simulation_mode 해제 (하드웨어 수령 후)
python3 -c "
import json
for f in ['config/air_sensors.json','config/weather_station.json']:
    d = json.load(open(f)); d['simulation_mode']=False
    json.dump(d, open(f,'w'), indent=4, ensure_ascii=False)
    print(f'✅ {f} → simulation_mode: false')
"
```

---

*이 파일은 작업 세션 간 컨텍스트 유지를 위한 내부 노트입니다.*
