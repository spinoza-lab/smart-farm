"""
자동 관수 제어기
토양 수분 센서 기반 자동 관수

제어 로직:
  1. 주기적으로 전체 구역 토양 수분 측정
  2. 수분 < 임계값인 구역 감지
  3. 탱크 수위 확인 (최소 수위 이상)
  4. 펌프 ON → 해당 구역 밸브 ON → 관수 → OFF
  5. 관수 이력 기록
"""

import time
import json
import threading
import os
from pathlib import Path
from datetime import datetime

# BUG-7: 설치 경로 동적 계산 (하드코딩 제거)
_BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from hardware.modbus_soil_sensor import SoilSensorManager
    from hardware.relay_controller import RelayController
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("⚠️  하드웨어 모듈 없음 - 시뮬레이션 모드")


class AutoIrrigationController:
    """토양 수분 기반 자동 관수 제어기"""

    CONFIG_PATH = str(_BASE_DIR / 'config/soil_sensors.json')
    LOG_PATH    = str(_BASE_DIR / 'logs/irrigation.log')
    CSV_PATH    = str(_BASE_DIR / 'logs/irrigation_history.csv')

    def __init__(self, sensor_manager=None, relay_controller=None, config_path=None):
        self.config_path      = config_path or self.CONFIG_PATH
        self.sensor_manager   = sensor_manager
        self.relay_controller = relay_controller

        # 상태
        self.mode            = 'manual'   # 'auto' | 'manual' | 'schedule'
        self.is_running      = False
        self.is_irrigating   = False
        self.current_zone    = None
        self.monitor_thread  = None

        # 관수 중단 플래그 (stop_irrigation() 호출 시 True)
        self._stop_requested = False

        # 설정
        self.config          = {}
        self.irrigation_cfg  = {}
        self.zone_thresholds = {}         # {zone_id: threshold}

        # 이력
        self.irrigation_history = []
        self.last_sensor_data   = {}
        self.alert_callback     = None
        # 센서 오류 알림 쿨다운 추적 (BUG-1b)
        self._last_sensor_alert_time = None

        # 관수 진행 시간 추적
        self._irr_start_time = None   # datetime
        self._irr_duration   = 0      # 초

        self._load_config()
        os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)

        print("✅ AutoIrrigationController 초기화 완료")
        print(f"   모드: {self.mode}")
        print(f"   체크 주기: {self.irrigation_cfg.get('check_interval', 600)}초")
        self._init_irrigation_csv()
        self._load_irrigation_history()
        self.last_irrigated_time = {}   # {zone_id: datetime} — S9
        self._load_last_irrigated_times()

    # ──────────────────────────────────────
    # 설정 로드
    # ──────────────────────────────────────
    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            self.irrigation_cfg = self.config.get('irrigation', {})
            # simulation_mode: True=시뮬 허용(개발용), False=센서 없으면 관수 중단
            self.simulation_mode = self.irrigation_cfg.get('simulation_mode', False)

            for s in self.config.get('sensors', []):
                self.zone_thresholds[s['zone_id']] = s.get(
                    'moisture_threshold', 40.0
                )
            print(f"✅ 관수 설정 로드 완료")
        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            self.irrigation_cfg = {
                'min_tank_level': 20.0,
                'irrigation_duration': 300,
                'zone_interval': 10,
                'check_interval': 600,
                'max_zones_simultaneous': 1,
                'simulation_mode': False
            }
            self.simulation_mode = False

    # ──────────────────────────────────────
    # 모드 제어
    # ──────────────────────────────────────
    def set_mode(self, mode):
        """모드 설정: 'auto' | 'manual'  (schedule → auto 자동 변환)"""
        if mode == 'schedule':   # 하위 호환: schedule → auto
            mode = 'auto'
        if mode not in ('auto', 'manual'):
            return False, f"잘못된 모드: {mode}"

        prev = self.mode
        self.mode = mode
        print(f"🔄 관수 모드 변경: {prev} → {mode}")

        if mode == 'auto':
            if not self.is_running:
                self.start_monitor()
            if hasattr(self, '_scheduler') and self._scheduler \
                    and not self._scheduler._running:
                self._scheduler.start()
        elif mode == 'manual':
            if self.is_running:
                self.stop_monitor()
            if hasattr(self, '_scheduler') and self._scheduler \
                    and self._scheduler._running:
                self._scheduler.stop()

        return True, f"모드가 {mode}로 변경되었습니다"

    # ──────────────────────────────────────
    # 모니터링 스레드
    # ──────────────────────────────────────
    def start_monitor(self):
        if self.is_running:
            return
        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self.monitor_thread.start()
        print("🔄 자동 관수 모니터 시작")

    def stop_monitor(self):
        self.is_running = False
        print("⏹️  자동 관수 모니터 정지")

    def _monitor_loop(self):
        """자동 관수 메인 루프"""
        check_interval = self.irrigation_cfg.get('check_interval', 600)

        while self.is_running:
            check_start = time.time()
            try:
                if self.mode == 'auto':
                    self._auto_check_and_irrigate()
            except Exception as e:
                print(f"❌ 모니터 루프 오류: {e}")

            # BUG-15: 관수 소요 시간 제외한 나머지만 대기 (5분 주기 체크 보장)
            elapsed = int(time.time() - check_start)
            remaining = max(0, check_interval - elapsed)
            for _ in range(remaining):
                if not self.is_running:
                    break
                time.sleep(1)

    # ──────────────────────────────────────
    # 자동 관수 체크
    # ──────────────────────────────────────
    def _auto_check_and_irrigate(self):
        """전체 구역 수분 체크 후 필요 구역 자동 관수"""
        print(f"\n{'='*50}")
        print(f"🌱 자동 관수 체크: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        # ── 센서 데이터 수집 ──────────────────────────────────
        if self.sensor_manager:
            sensor_data = self.sensor_manager.read_all_zones()

            # 전체 센서 읽기 실패 시 관수 중단
            valid_count = sum(1 for d in sensor_data.values() if d.get('valid'))
            if valid_count == 0:
                msg = '❌ 모든 토양센서 읽기 실패 - 자동관수를 중단합니다'
                print(msg)
                self._log(msg)
                self._send_sensor_alert(msg)
                return

        elif self.simulation_mode:
            # simulation_mode=true 일 때만 시뮬레이션 허용 (개발·테스트 전용)
            print('⚠️  [시뮬레이션 모드] 가상 센서 데이터를 사용합니다')
            self._log('[시뮬레이션 모드] 가상 센서 데이터 사용')
            sensor_data = self._simulate_sensor_data()

        else:
            # 센서 매니저 없음 + simulation_mode=false → 관수 완전 중단
            msg = ('❌ 토양센서 매니저가 초기화되지 않았습니다.\n'
                   'soil_sensors.json > irrigation > simulation_mode 를 확인하세요.\n'
                   '자동관수를 중단합니다.')
            print(msg)
            self._log('토양센서 매니저 없음 - 자동관수 중단')
            self._send_sensor_alert('⚠️ 토양센서 매니저 없음 - 자동관수 중단')
            return

        self.last_sensor_data = sensor_data

        tank_ok, tank_msg = self._check_tank_level()
        if not tank_ok:
            print(f"⚠️  관수 보류: {tank_msg}")
            self._log(f"관수 보류 - {tank_msg}")
            return

        dry_zones = []
        for zone_id, data in sorted(sensor_data.items()):
            # ── S9: 3단계 관수 주기 판단 ──────────────────────────────────
            zone_cfg     = next((s for s in self.config.get('sensors', [])
                                 if s['zone_id'] == zone_id), {})
            min_interval = zone_cfg.get('min_irrigation_interval', 21600)   # 기본 6h
            max_interval = zone_cfg.get('max_irrigation_interval', 259200)  # 기본 3일

            last_t  = self.last_irrigated_time.get(zone_id)
            elapsed = (datetime.now() - last_t).total_seconds() if last_t else float('inf')

            # 1단계: 미관수 주기 내 → 무조건 스킵
            if elapsed < min_interval:
                print(f"  구역 {zone_id:2d}: ⏳ 미관수 주기 중 "
                      f"({elapsed/3600:.1f}h / {min_interval/3600:.0f}h) — 스킵")
                continue

            # 3단계: 필수관수 주기 초과 → 센서 무관 강제 관수
            if elapsed >= max_interval:
                print(f"  구역 {zone_id:2d}: 🚨 필수관수 주기 초과 "
                      f"({elapsed/86400:.1f}일) — 강제 관수")
                dry_zones.append(zone_id)
                continue

            # 2단계: 일반 습도 판단 (min ≤ elapsed < max)
            if not data.get('valid'):
                print(f"  구역 {zone_id:2d}: ❌ 센서 오류 - {data.get('error')}")
                continue

            threshold = self.zone_thresholds.get(zone_id, 40.0)
            moisture  = data['moisture']

            if moisture < threshold:
                dry_zones.append(zone_id)
                print(f"  구역 {zone_id:2d}: 💧 수분 {moisture:.1f}% < {threshold}% → 관수 필요")
            else:
                print(f"  구역 {zone_id:2d}: ✅ 수분 {moisture:.1f}% (양호)")

        if not dry_zones:
            print("✅ 모든 구역 수분 충분 - 관수 불필요")
            return

        print(f"\n💧 관수 대상: 구역 {dry_zones}")
        for zone_id in dry_zones:
            if not self.is_running:
                break
            # BUG-16: 구역마다 탱크 수위 재체크 (연속 관수 중 수위 저하 대응)
            tank_ok, tank_msg = self._check_tank_level()
            if not tank_ok:
                print(f"⚠️ 탱크 수위 부족 → 나머지 관수 중단: {tank_msg}")
                break
            self.irrigate_zone(zone_id)
            interval = self.irrigation_cfg.get('zone_interval', 10)
            if zone_id != dry_zones[-1]:
                print(f"  ⏳ 다음 구역 대기 {interval}초...")
                time.sleep(interval)

    # ──────────────────────────────────────
    # 관수 중단 (외부 호출용)
    # ──────────────────────────────────────
    def stop_irrigation(self):
        """현재 진행 중인 관수를 중단. irrigate_zone 루프에서 감지."""
        if self.is_irrigating:
            self._stop_requested = True
            print("🛑 관수 중단 요청 수신 – 다음 초 단위에서 중단됩니다")
        else:
            print("💤 stop_irrigation() 호출됐으나 현재 관수 중이 아님")

    # ──────────────────────────────────────
    # 단일 구역 관수
    # ──────────────────────────────────────
    def start_zone_irrigation(self, zone_id, duration=None, trigger="scheduler"):
        """스케줄러/텔레그램 호출용 래퍼 – irrigate_zone() 위임"""
        return self.irrigate_zone(zone_id=zone_id, duration=duration, trigger=trigger)

    def irrigate_zone(self, zone_id, duration=None, trigger=None):
        """단일 구역 관수 실행 (중단 플래그 지원)"""
        if self.is_irrigating:
            return False, f"이미 관수 중 (구역 {self.current_zone})"

        duration = duration or self.irrigation_cfg.get('irrigation_duration', 300)

        print(f"\n💧 구역 {zone_id} 관수 시작 ({duration}초)")

        # 관수 시작 텔레그램 알림
        try:
            import sys as _s
            _am = (_s.modules.get("__main__") or
                   _s.modules.get("web.app") or
                   _s.modules.get("app"))
            _tn = getattr(_am, "telegram_notifier", None)
            if _tn:
                _tn.notify_irrigation_start(zone_id, duration, trigger or self.mode)
        except Exception:
            pass

        self.is_irrigating   = True
        self.current_zone    = zone_id
        self._stop_requested = False          # 플래그 초기화
        self._irr_start_time = datetime.now()
        self._irr_duration   = duration
        start_time           = self._irr_start_time
        aborted              = False

        try:
            if self.relay_controller:
                self.relay_controller.pump_on()
                time.sleep(0.5)
                self.relay_controller.zone_on(zone_id)
            else:
                print(f"  [시뮬레이션] 펌프 ON, 구역 {zone_id} 밸브 ON")

            # ─── 관수 진행 (1초 단위 루프 – 중단 요청 감지) ───────
            print(f"  ⏳ 관수 중... ({duration}초)")
            for elapsed in range(duration):
                if self._stop_requested:
                    print(f"  🛑 관수 중단 감지 ({elapsed}초 경과)")
                    aborted = True
                    break
                time.sleep(1)

        except Exception as e:
            print(f"  ❌ 관수 오류: {e}")
        finally:
            # 반드시 하드웨어 OFF
            if self.relay_controller:
                self.relay_controller.zone_off(zone_id)
                time.sleep(0.3)
                self.relay_controller.pump_off()
            else:
                print(f"  [시뮬레이션] 구역 {zone_id} 밸브 OFF, 펌프 OFF")

            self.is_irrigating   = False
            self.current_zone    = None
            self._stop_requested = False
            self._irr_start_time = None
            self._irr_duration   = 0

        # 실제 관수 시간 계산
        actual_duration = int((datetime.now() - start_time).total_seconds())

        # 완료 텔레그램 알림
        try:
            import sys as _s
            _am = (_s.modules.get("__main__") or
                   _s.modules.get("web.app") or
                   _s.modules.get("app"))
            _tn = getattr(_am, "telegram_notifier", None)
            if _tn:
                _tn.notify_irrigation_done(
                    zone_id, actual_duration,
                    trigger or self.mode,
                    success=not aborted
                )
        except Exception:
            pass

        # 이력 기록
        moisture_before = ''
        if zone_id in self.last_sensor_data:
            m = self.last_sensor_data[zone_id]
            if isinstance(m, dict):
                moisture_before = m.get('moisture', '')

        record = {
            'zone_id':        zone_id,
            'start_time':     start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration':       actual_duration,
            'trigger':        trigger if trigger is not None else self.mode,
            'moisture_before': moisture_before,
            'success':        not aborted
        }
        self.irrigation_history.append(record)
        self._save_to_csv(record)
        if len(self.irrigation_history) > 200:
            self.irrigation_history = self.irrigation_history[-200:]
        # S9: 관수 성공 시 마지막 관수 시간 갱신
        if not aborted:
            self.last_irrigated_time[zone_id] = datetime.now()

        if aborted:
            self._log(f"구역 {zone_id} 관수 중단 ({actual_duration}초 경과)")
            print(f"  🛑 구역 {zone_id} 관수 중단 완료")
            return False, f"구역 {zone_id} 관수 중단됨 ({actual_duration}초)"
        else:
            self._log(f"구역 {zone_id} 관수 완료 ({actual_duration}초)")
            print(f"  ✅ 구역 {zone_id} 관수 완료")
            return True, f"구역 {zone_id} 관수 완료"

    # ──────────────────────────────────────
    # 탱크 수위 확인
    # ──────────────────────────────────────
    def _check_tank_level(self):
        min_level = self.irrigation_cfg.get('min_tank_level', 20.0)
        if hasattr(self, 'get_tank_level_callback') and self.get_tank_level_callback:
            level = self.get_tank_level_callback()
            if level is not None and level < min_level:
                return False, f"탱크 수위 부족 ({level:.1f}% < {min_level}%)"
        return True, "탱크 수위 충분"

    # ──────────────────────────────────────
    # 상태 조회
    # ──────────────────────────────────────
    def attach_scheduler(self, scheduler):
        """스케줄러 주입 (순환 참조 방지용 지연 주입)"""
        self._scheduler = scheduler
        if self.mode == 'auto' and not scheduler._running:
            scheduler.start()

    def get_status(self):
        irr_elapsed = 0
        irr_total   = self._irr_duration or 0
        if self.is_irrigating and self._irr_start_time:
            irr_elapsed = int((datetime.now() - self._irr_start_time).total_seconds())
        return {
            'mode':             self.mode,
            'is_running':       self.is_running,
            'is_irrigating':    self.is_irrigating,
            'current_zone':     self.current_zone,
            'irr_elapsed':      irr_elapsed,
            'irr_total':        irr_total,
            'stop_requested':   self._stop_requested,
            'zone_thresholds':  self.zone_thresholds,
            'last_sensor_data': self.last_sensor_data,
            'recent_history':   self.irrigation_history[-10:]
        }

    def get_sensor_data(self):
        return self.last_sensor_data.copy()

    # ──────────────────────────────────────
    # 로그 & 시뮬레이션
    # ──────────────────────────────────────
    def _load_last_irrigated_times(self):
        """CSV에서 구역별 마지막 관수 시간 복원 — S9"""
        import csv as _csv
        if not os.path.exists(self.CSV_PATH):
            return
        try:
            with open(self.CSV_PATH, 'r', encoding='utf-8') as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    if str(row.get('success', '')).lower() != 'true':
                        continue
                    try:
                        zid = int(row['zone_id'])
                        ts  = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                        if zid not in self.last_irrigated_time or ts > self.last_irrigated_time[zid]:
                            self.last_irrigated_time[zid] = ts
                    except (ValueError, KeyError):
                        continue
            if self.last_irrigated_time:
                print(f'✅ 구역별 마지막 관수 시간 복원: {len(self.last_irrigated_time)}개 구역')
        except Exception as e:
            print(f'⚠️  마지막 관수 시간 복원 실패: {e}')

    def update_last_irrigated_time(self, zone_id):
        """스케줄러 등 외부에서 관수 완료 후 호출 — S9"""
        self.last_irrigated_time[zone_id] = datetime.now()

    def _init_irrigation_csv(self):
        import csv
        if not os.path.exists(self.CSV_PATH) or os.path.getsize(self.CSV_PATH) == 0:
            with open(self.CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'zone_id', 'duration_sec',
                                 'trigger', 'moisture_before', 'success'])
            print(f"✅ 관수 이력 CSV 생성: {self.CSV_PATH}")

    def _load_irrigation_history(self):
        import csv
        if not os.path.exists(self.CSV_PATH):
            return
        try:
            with open(self.CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.irrigation_history = rows[-200:]
            if self.irrigation_history:
                print(f"✅ 관수 이력 {len(self.irrigation_history)}개 로드됨")
        except Exception as e:
            print(f"⚠️  관수 이력 로드 실패: {e}")

    def _save_to_csv(self, record):
        import csv
        try:
            with open(self.CSV_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    record.get('start_time', ''),
                    record.get('zone_id', ''),
                    record.get('duration', ''),
                    record.get('trigger', ''),
                    record.get('moisture_before', ''),
                    record.get('success', True)
                ])
        except Exception as e:
            print(f"⚠️  관수 이력 CSV 저장 실패: {e}")

    def _log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {message}\n"
        try:
            with open(self.LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(line)
        except Exception:
            pass
        print(f"📝 {line.strip()}")

    def _send_sensor_alert(self, message):
        """토양센서 오류를 텔레그램으로 알림 (쿨다운 적용, BUG-1b)"""
        now = datetime.now()
        cooldown = self.irrigation_cfg.get('sensor_alert_cooldown', 1800)  # 기본 30분

        if self._last_sensor_alert_time is not None:
            elapsed = (now - self._last_sensor_alert_time).total_seconds()
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                print(f'⏸️  센서 오류 알림 쿨다운 중 ({remaining}초 남음) - 텔레그램 전송 생략')
                return

        try:
            import sys as _sys
            _main = (_sys.modules.get('__main__') or
                     _sys.modules.get('web.app') or
                     _sys.modules.get('app'))
            _tn = getattr(_main, 'telegram_notifier', None)
            if _tn:
                _tn.send(f'🚨 [자동관수 오류]\n{message}')
                self._last_sensor_alert_time = now
                print(f'📨 센서 오류 알림 전송 완료 (다음 알림: {cooldown // 60}분 후)')
            else:
                # 텔레그램 없어도 쿨다운 타이머는 시작
                self._last_sensor_alert_time = now
        except Exception as e:
            print(f'⚠️  텔레그램 알림 실패: {e}')
    def _simulate_sensor_data(self):
        import random
        data = {}
        for zone_id in range(1, 13):
            data[zone_id] = {
                'zone_id':     zone_id,
                'moisture':    round(random.uniform(20, 80), 1),
                'temperature': round(random.uniform(18, 28), 1),
                'ec':          random.randint(200, 800),
                'valid':       True,
                'timestamp':   datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        return data


# ──────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("🚿 자동 관수 컨트롤러 테스트 (시뮬레이션)")
    print("=" * 50)

    ctrl = AutoIrrigationController()

    status = ctrl.get_status()
    print(f"\n현재 모드: {status['mode']}")
    print(f"임계값 설정: {status['zone_thresholds']}")

    print("\n🧪 수동 관수 체크 실행 (시뮬레이션)...")
    ctrl._auto_check_and_irrigate()
