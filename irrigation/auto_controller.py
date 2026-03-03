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
from datetime import datetime

try:
    from hardware.modbus_soil_sensor import SoilSensorManager
    from hardware.relay_controller import RelayController
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("⚠️  하드웨어 모듈 없음 - 시뮬레이션 모드")


class AutoIrrigationController:
    """토양 수분 기반 자동 관수 제어기"""

    CONFIG_PATH = '/home/pi/smart_farm/config/soil_sensors.json'
    LOG_PATH    = '/home/pi/smart_farm/logs/irrigation.log'
    CSV_PATH    = '/home/pi/smart_farm/logs/irrigation_history.csv'

    def __init__(self, sensor_manager=None, relay_controller=None, config_path=None):
        self.config_path     = config_path or self.CONFIG_PATH
        self.sensor_manager  = sensor_manager
        self.relay_controller = relay_controller

        # 상태
        self.mode            = 'manual'   # 'auto' | 'manual' | 'schedule'
        self.is_running      = False
        self.is_irrigating   = False
        self.current_zone    = None
        self.monitor_thread  = None

        # 설정
        self.config          = {}
        self.irrigation_cfg  = {}
        self.zone_thresholds = {}         # {zone_id: threshold}

        # 이력
        self.irrigation_history = []
        self.last_sensor_data   = {}
        self.alert_callback     = None

        # Fix C – patch_v4f: 관수 진행 시간 추적
        self._irr_start_time = None   # datetime
        self._irr_duration   = 0      # 초

        self._load_config()
        os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)

        print("✅ AutoIrrigationController 초기화 완료")
        print(f"   모드: {self.mode}")
        print(f"   체크 주기: {self.irrigation_cfg.get('check_interval', 600)}초")
        self._init_irrigation_csv()
        self._load_irrigation_history()

    # ──────────────────────────────────────
    # 설정 로드
    # ──────────────────────────────────────
    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            self.irrigation_cfg = self.config.get('irrigation', {})

            for s in self.config.get('sensors', []):
                self.zone_thresholds[s['zone_id']] = s.get(
                    'moisture_threshold', 40.0
                )
            print(f"✅ 관수 설정 로드 완료")
        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            self.irrigation_cfg  = {
                'min_tank_level': 20.0,
                'irrigation_duration': 300,
                'zone_interval': 10,
                'check_interval': 600,
                'max_zones_simultaneous': 1
            }

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
            # 스케줄러 시작
            if hasattr(self, '_scheduler') and self._scheduler                     and not self._scheduler._running:
                self._scheduler.start()
        elif mode == 'manual':
            if self.is_running:
                self.stop_monitor()
            # 스케줄러 정지
            if hasattr(self, '_scheduler') and self._scheduler                     and self._scheduler._running:
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
            try:
                if self.mode == 'auto':
                    self._auto_check_and_irrigate()
            except Exception as e:
                print(f"❌ 모니터 루프 오류: {e}")

            # 체크 주기 대기 (1초씩 끊어서 종료 응답성 향상)
            for _ in range(check_interval):
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

        # 1. 센서 데이터 읽기
        if self.sensor_manager:
            sensor_data = self.sensor_manager.read_all_zones()
        else:
            sensor_data = self._simulate_sensor_data()

        self.last_sensor_data = sensor_data

        # 2. 탱크 수위 확인
        tank_ok, tank_msg = self._check_tank_level()
        if not tank_ok:
            print(f"⚠️  관수 보류: {tank_msg}")
            self._log(f"관수 보류 - {tank_msg}")
            return

        # 3. 수분 부족 구역 감지
        dry_zones = []
        for zone_id, data in sorted(sensor_data.items()):
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

        # 4. 관수 실행
        if not dry_zones:
            print("✅ 모든 구역 수분 충분 - 관수 불필요")
            return

        print(f"\n💧 관수 대상: 구역 {dry_zones}")
        for zone_id in dry_zones:
            if not self.is_running:
                break
            self.irrigate_zone(zone_id)
            # 구역 간 대기
            interval = self.irrigation_cfg.get('zone_interval', 10)
            if zone_id != dry_zones[-1]:
                print(f"  ⏳ 다음 구역 대기 {interval}초...")
                time.sleep(interval)

    # ──────────────────────────────────────
    # 단일 구역 관수
    # ──────────────────────────────────────
    def start_zone_irrigation(self, zone_id, duration=None, trigger="scheduler"):
        """스케줄러 호출용 래퍼 – irrigate_zone() 위임"""
        return self.irrigate_zone(zone_id=zone_id, duration=duration, trigger=trigger)

    def irrigate_zone(self, zone_id, duration=None, trigger=None):
        """단일 구역 관수 실행"""
        if self.is_irrigating:
            return False, f"이미 관수 중 (구역 {self.current_zone})"

        duration = duration or self.irrigation_cfg.get('irrigation_duration', 300)

        print(f"\n💧 구역 {zone_id} 관수 시작 ({duration}초)")
        self.is_irrigating   = True
        self.current_zone    = zone_id
        self._irr_start_time = datetime.now()   # Fix C
        self._irr_duration   = duration          # Fix C
        start_time           = self._irr_start_time

        try:
            if self.relay_controller:
                # 실제 릴레이 제어
                self.relay_controller.pump_on()
                time.sleep(0.5)
                self.relay_controller.zone_on(zone_id)
            else:
                print(f"  [시뮬레이션] 펌프 ON, 구역 {zone_id} 밸브 ON")

            # 관수 진행
            print(f"  ⏳ 관수 중... ({duration}초)")
            time.sleep(duration)

        except Exception as e:
            print(f"  ❌ 관수 오류: {e}")
        finally:
            # 반드시 OFF
            if self.relay_controller:
                self.relay_controller.zone_off(zone_id)
                time.sleep(0.3)
                self.relay_controller.pump_off()
            else:
                print(f"  [시뮬레이션] 구역 {zone_id} 밸브 OFF, 펌프 OFF")

            self.is_irrigating   = False
            self.current_zone    = None
            self._irr_start_time = None   # Fix C
            self._irr_duration   = 0      # Fix C

        # 이력 기록
        record = {
            'zone_id':    zone_id,
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration':   duration,
            'trigger':    trigger if trigger is not None else self.mode
        }
        # 관수 전 수분 데이터 추가
        moisture_before = ''
        if zone_id in self.last_sensor_data:
            m = self.last_sensor_data[zone_id]
            if isinstance(m, dict):
                moisture_before = m.get('moisture', '')
        record['moisture_before'] = moisture_before
        record['success'] = True

        self.irrigation_history.append(record)
        self._save_to_csv(record)          # CSV 영구 저장
        if len(self.irrigation_history) > 200:
            self.irrigation_history = self.irrigation_history[-200:]

        self._log(f"구역 {zone_id} 관수 완료 ({duration}초)")
        print(f"  ✅ 구역 {zone_id} 관수 완료")
        return True, f"구역 {zone_id} 관수 완료"

    # ──────────────────────────────────────
    # 탱크 수위 확인
    # ──────────────────────────────────────
    def _check_tank_level(self):
        min_level = self.irrigation_cfg.get('min_tank_level', 20.0)
        # SensorMonitor에서 최신 수위 가져오기 (외부 주입 방식)
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
        # Fix C – patch_v4f: 관수 경과/남은 시간 계산
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
            'zone_thresholds':  self.zone_thresholds,
            'last_sensor_data': self.last_sensor_data,
            'recent_history':   self.irrigation_history[-10:]
        }

    def get_sensor_data(self):
        return self.last_sensor_data.copy()

    # ──────────────────────────────────────
    # 로그 & 시뮬레이션
    # ──────────────────────────────────────
    def _init_irrigation_csv(self):
        """관수 이력 CSV 파일 초기화 (헤더 없으면 생성)"""
        import csv
        if not os.path.exists(self.CSV_PATH) or os.path.getsize(self.CSV_PATH) == 0:
            with open(self.CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'zone_id', 'duration_sec', 'trigger', 'moisture_before', 'success'])
            print(f"✅ 관수 이력 CSV 생성: {self.CSV_PATH}")

    def _load_irrigation_history(self):
        """CSV에서 최근 200개 이력 로드 (재시작해도 유지)"""
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
        """관수 이력 1건을 CSV에 추가"""
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

    def _simulate_sensor_data(self):
        """센서 없을 때 시뮬레이션 데이터"""
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

    # 상태 출력
    status = ctrl.get_status()
    print(f"\n현재 모드: {status['mode']}")
    print(f"임계값 설정: {status['zone_thresholds']}")

    # 시뮬레이션 데이터로 1회 체크
    print("\n🧪 수동 관수 체크 실행 (시뮬레이션)...")
    ctrl._auto_check_and_irrigate()