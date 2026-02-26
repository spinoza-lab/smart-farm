"""
CWT-Soil-THC-S 토양 센서 드라이버
RS-485 Modbus RTU 통신

센서 스펙:
  - 통신: RS-485 Modbus RTU
  - 기본 주소: 1 (변경 가능: 1~254)
  - 통신 설정: 4800 bps, N, 8, 1
  - 레지스터:
      0x0000: 토양 수분 (0.1 %RH)
      0x0001: 온도 (0.1 ℃, 음수는 2의 보수)
      0x0002: EC 전기전도도 (1 μS/cm)

배선:
  갈색: DC 5~30V
  검정: GND
  노랑: RS-485 A+
  파랑: RS-485 B-

MAX485 연결:
  GPIO14 (TX) → DI
  GPIO15 (RX) → RO
  GPIO18      → DE + RE (묶기)
"""

import minimalmodbus
import serial
import time
import json
import os

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO 없음 - 테스트 모드로 실행")


# ──────────────────────────────────────────
# DE/RE 자동 제어 시리얼 클래스
# ──────────────────────────────────────────
class RS485Serial(serial.Serial):
    """MAX485 DE/RE 핀 자동 제어 시리얼 포트"""

    def __init__(self, *args, de_re_pin=18, **kwargs):
        self.de_re_pin = de_re_pin
        self._gpio_ok = False

        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(de_re_pin, GPIO.OUT)
                GPIO.output(de_re_pin, GPIO.LOW)   # 기본: 수신 모드
                self._gpio_ok = True
            except Exception as e:
                print(f"⚠️  GPIO 설정 실패: {e}")

        super().__init__(*args, **kwargs)

    def write(self, data):
        """송신 시 DE/RE HIGH → 전송 → DE/RE LOW"""
        if self._gpio_ok:
            GPIO.output(self.de_re_pin, GPIO.HIGH)   # 송신 모드
            time.sleep(0.001)                         # 안정화 대기

        result = super().write(data)
        self.flush()

        if self._gpio_ok:
            # 전송 완료 대기: 바이트수 × 비트수 / 보율 + 여유
            tx_time = (len(data) * 10 / self.baudrate) + 0.003
            time.sleep(tx_time)
            GPIO.output(self.de_re_pin, GPIO.LOW)    # 수신 모드

        return result


# ──────────────────────────────────────────
# 단일 센서 클래스
# ──────────────────────────────────────────
class SoilSensor:
    """CWT-Soil-THC-S 단일 센서 인터페이스"""

    REGISTER_MOISTURE    = 0x0000
    REGISTER_TEMPERATURE = 0x0001
    REGISTER_EC          = 0x0002

    def __init__(self, port, slave_address, de_re_pin=18, timeout=1.0):
        self.slave_address = slave_address
        self.port = port

        # RS485 시리얼 포트 생성
        rs485_serial = RS485Serial(
            port,
            baudrate=4800,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            de_re_pin=de_re_pin
        )

        # minimalmodbus 에 커스텀 시리얼 주입
        self.instrument = minimalmodbus.Instrument.__new__(minimalmodbus.Instrument)
        self.instrument.serial = rs485_serial
        self.instrument.address = slave_address
        self.instrument.mode = minimalmodbus.MODE_RTU
        self.instrument.debug = False
        self.instrument.close_port_after_each_call = False
        self.instrument.BYTEORDER_BIG = minimalmodbus.BYTEORDER_BIG
        # minimalmodbus 2.x 호환 설정
        # __new__() 생성 시 __init__ 미호출로 내부 속성 누락 → 강제 초기화
        if not hasattr(self.instrument, 'precalculate_read_size'):
            self.instrument.precalculate_read_size = False   # 2.x 기본값
        if not hasattr(self.instrument, 'clear_buffers_before_each_transaction'):
            self.instrument.clear_buffers_before_each_transaction = True
        # 2.x 에서 추가된 필수 내부 속성 초기화
        if not hasattr(self.instrument, 'handle_local_echo'):
            self.instrument.handle_local_echo = False
        if not hasattr(self.instrument, '_print_all_errors'):
            self.instrument._print_all_errors = False

    def read_all(self):
        """수분, 온도, EC 3개 레지스터 동시 읽기"""
        regs = self.instrument.read_registers(
            self.REGISTER_MOISTURE, 3, functioncode=3
        )

        moisture    = regs[0] / 10.0

        # 음수 온도 처리 (16비트 2의 보수)
        raw_temp = regs[1]
        if raw_temp > 32767:
            raw_temp -= 65536
        temperature = raw_temp / 10.0

        ec = regs[2]  # μS/cm

        return {
            'moisture':    round(moisture, 1),
            'temperature': round(temperature, 1),
            'ec':          ec,
            'address':     self.slave_address,
            'valid':       True
        }

    def read_moisture(self):
        """토양 수분만 읽기"""
        raw = self.instrument.read_register(
            self.REGISTER_MOISTURE, functioncode=3
        )
        return round(raw / 10.0, 1)

    def close(self):
        if self.instrument.serial.is_open:
            self.instrument.serial.close()


# ──────────────────────────────────────────
# 멀티 센서 매니저
# ──────────────────────────────────────────
class SoilSensorManager:
    """12개 구역 토양 센서 통합 관리"""

    CONFIG_PATH = '/home/pi/smart_farm/config/soil_sensors.json'

    def __init__(self, config_path=None):
        self.config_path = config_path or self.CONFIG_PATH
        self.config      = {}
        self.sensors     = {}      # {zone_id: SoilSensor}
        self.last_readings = {}    # {zone_id: {moisture, temperature, ec, ...}}
        self._port_open  = False

        self._load_config()
        self._init_sensors()

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"✅ 토양 센서 설정 로드: {self.config_path}")
        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            self.config = {}

    def _init_sensors(self):
        if not self.config:
            return

        modbus_cfg = self.config.get('modbus', {})
        port       = modbus_cfg.get('port', '/dev/ttyAMA0')
        de_re_pin  = modbus_cfg.get('de_re_pin', 18)
        timeout    = modbus_cfg.get('timeout', 1.0)

        print(f"\n{'='*50}")
        print(f"🔧 SoilSensorManager 초기화")
        print(f"   포트: {port}, DE/RE: GPIO{de_re_pin}")
        print(f"{'='*50}")

        sensors_cfg = self.config.get('sensors', [])
        first_sensor = True

        for s_cfg in sensors_cfg:
            if not s_cfg.get('enabled', True):
                continue

            zone_id = s_cfg['zone_id']
            address = s_cfg['sensor_address']

            try:
                if first_sensor:
                    # 첫 번째 센서가 시리얼 포트 개설
                    sensor = SoilSensor(port, address, de_re_pin, timeout)
                    first_sensor = False
                    shared_serial = sensor.instrument.serial
                else:
                    # 나머지 센서는 포트 공유
                    sensor = SoilSensor.__new__(SoilSensor)
                    sensor.slave_address = address
                    sensor.port = port
                    sensor.instrument = minimalmodbus.Instrument.__new__(
                        minimalmodbus.Instrument
                    )
                    sensor.instrument.serial  = shared_serial
                    sensor.instrument.address = address
                    sensor.instrument.mode    = minimalmodbus.MODE_RTU
                    sensor.instrument.debug   = False
                    sensor.instrument.close_port_after_each_call = False
                    # ── Fix S: 누락된 minimalmodbus 2.x 필수 속성 추가 ──
                    sensor.instrument.precalculate_read_size = True
                    sensor.instrument.clear_buffers_before_each_transaction = True
                    sensor.instrument.handle_local_echo = False
                    sensor.instrument._print_all_errors = False

                self.sensors[zone_id] = sensor
                print(f"  ✓ 구역 {zone_id:2d} 센서 등록 (Modbus 주소: {address})")

            except Exception as e:
                print(f"  ✗ 구역 {zone_id} 센서 초기화 실패: {e}")

        print(f"✅ 총 {len(self.sensors)}개 센서 등록 완료\n")

    def read_zone(self, zone_id, retry=3):
        """특정 구역 센서 읽기 (재시도 포함)"""
        sensor = self.sensors.get(zone_id)
        if not sensor:
            return {'valid': False, 'error': f'구역 {zone_id} 센서 없음'}

        for attempt in range(retry):
            try:
                data = sensor.read_all()
                data['zone_id']   = zone_id
                data['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
                self.last_readings[zone_id] = data
                return data
            except Exception as e:
                if attempt < retry - 1:
                    time.sleep(0.3)
                else:
                    error_data = {
                        'zone_id':   zone_id,
                        'valid':     False,
                        'error':     str(e),
                        'moisture':  None,
                        'temperature': None,
                        'ec':        None,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self.last_readings[zone_id] = error_data
                    return error_data

    def read_all_zones(self):
        """전체 구역 순차 읽기"""
        results = {}
        for zone_id in sorted(self.sensors.keys()):
            results[zone_id] = self.read_zone(zone_id)
            time.sleep(0.1)   # 센서 간 응답 간격
        return results

    def get_moisture(self, zone_id):
        """마지막 수분값 반환 (없으면 None)"""
        reading = self.last_readings.get(zone_id, {})
        if reading.get('valid'):
            return reading.get('moisture')
        return None

    def get_last_readings(self):
        return self.last_readings.copy()

    def close(self):
        if self.sensors:
            first = next(iter(self.sensors.values()))
            try:
                first.instrument.serial.close()
                print("✅ 시리얼 포트 닫힘")
            except Exception:
                pass


# ──────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("🌱 토양 센서 테스트")
    print("=" * 50)

    manager = SoilSensorManager()

    if not manager.sensors:
        print("❌ 등록된 센서 없음. config/soil_sensors.json 확인!")
    else:
        print(f"\n📡 전체 구역 센서 읽기 시작...")
        results = manager.read_all_zones()

        print(f"\n{'구역':^6} {'수분(%)':^10} {'온도(℃)':^10} {'EC(μS/cm)':^12} {'상태':^8}")
        print("-" * 55)

        for zone_id, data in sorted(results.items()):
            if data['valid']:
                print(f"  {zone_id:2d}  | "
                      f"{data['moisture']:6.1f}%   | "
                      f"{data['temperature']:6.1f}℃  | "
                      f"{data['ec']:8d}      | ✅")
            else:
                print(f"  {zone_id:2d}  | {'N/A':^8}   | "
                      f"{'N/A':^8}  | {'N/A':^10}    | "
                      f"❌ {data.get('error','오류')}")

    manager.close()
