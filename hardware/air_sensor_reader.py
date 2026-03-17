#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
air_sensor_reader.py — SHT30 RS-485 Modbus RTU 드라이버
CDSENET EID041-G01S, /dev/ttyAMA2, 9600bps
레지스터: 0x0000 = 온도(int16 x0.1°C), 0x0001 = 습도(uint16 x0.1%)
DE/RE 핀: GPIO17 (Pin 11)
"""

import os
import json
import time
import random
import logging
import threading
import struct

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'config', 'air_sensors.json'
)


class AirSensor:
    """SHT30 단일 센서 드라이버 (Modbus RTU)"""

    TEMP_REG = 0x0000
    HUM_REG  = 0x0001
    NUM_REGS = 2

    def __init__(self, address: int, name: str = "", zone_id: int = 0):
        self.address           = address
        self.name              = name or f"에어센서_{address}"
        self.zone_id           = zone_id
        self.last_temperature  = None
        self.last_humidity     = None
        self.last_read_time    = None
        self.error_count       = 0
        self.valid             = False

    # ──────────────────────────────────────────────────────────────────
    # Modbus CRC-16
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _crc16(data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _build_read_request(self) -> bytes:
        """FC03 읽기 요청 프레임 생성 (8바이트)"""
        frame = struct.pack('>BBHH',
                            self.address, 0x03,
                            self.TEMP_REG, self.NUM_REGS)
        crc = self._crc16(frame)
        return frame + struct.pack('<H', crc)

    def parse_response(self, raw: bytes):
        """
        FC03 응답 파싱 (9바이트)
        [addr][0x03][byte_cnt=4][temp_hi][temp_lo][hum_hi][hum_lo][crc_lo][crc_hi]
        반환: (temperature, humidity)
        """
        if len(raw) < 9:
            raise ValueError(f"응답 길이 부족: {len(raw)}바이트 (기대 9)")

        addr, func, byte_cnt = raw[0], raw[1], raw[2]

        if addr != self.address:
            raise ValueError(f"주소 불일치: 응답={addr}, 기대={self.address}")
        if func == 0x83:
            raise ValueError(f"Modbus 예외 응답: 에러코드={raw[2]:#04x}")
        if func != 0x03:
            raise ValueError(f"Function Code 불일치: {func:#04x}")
        if byte_cnt != 4:
            raise ValueError(f"바이트 카운트 불일치: {byte_cnt}")

        # CRC 검증
        crc_calc = self._crc16(raw[:7])
        crc_recv = struct.unpack('<H', raw[7:9])[0]
        if crc_calc != crc_recv:
            raise ValueError(
                f"CRC 불일치: 계산={crc_calc:#06x}, 수신={crc_recv:#06x}"
            )

        # 온도 (int16, signed, x0.1°C)
        raw_temp    = struct.unpack('>h', raw[3:5])[0]
        temperature = round(raw_temp * 0.1, 1)

        # 습도 (uint16, unsigned, x0.1%)
        raw_hum  = struct.unpack('>H', raw[5:7])[0]
        humidity = round(raw_hum * 0.1, 1)

        # 유효성 검사
        if not (-40.0 <= temperature <= 80.0):
            raise ValueError(f"온도 범위 초과: {temperature}°C")
        if not (0.0 <= humidity <= 100.0):
            raise ValueError(f"습도 범위 초과: {humidity}%")

        return temperature, humidity

    def simulate(self) -> dict:
        """시뮬레이션 데이터 반환 (하드웨어 없을 때)"""
        temperature = round(random.uniform(18.0, 32.0), 1)
        humidity    = round(random.uniform(40.0, 85.0), 1)
        self.last_temperature = temperature
        self.last_humidity    = humidity
        self.last_read_time   = time.time()
        self.valid            = True
        return {
            'sensor_id':   self.address,
            'zone_id':     self.zone_id,
            'name':        self.name,
            'temperature': temperature,
            'humidity':    humidity,
            'valid':       True,
            'simulated':   True,
            'timestamp':   time.strftime('%Y-%m-%d %H:%M:%S')
        }


class AirSensorManager:
    """
    SHT30 다중 센서 매니저
    - RS-485 Modbus RTU, UART3 (/dev/ttyAMA2), 9600bps
    - DE/RE 제어: GPIO17 (Pin 11)
    - 최대 15개 센서, 주소 1-15
    - simulation_mode: True → 하드웨어 없이 테스트 가능
    """

    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path    = config_path
        self.config         = {}
        self.sensors        = []
        self.serial_port    = None
        self._lock          = threading.Lock()
        self._de_re_pin     = None
        self._gpio_ok       = False
        self._initialized   = False
        self._load_config()

    # ──────────────────────────────────────────────────────────────────
    # 설정 로드
    # ──────────────────────────────────────────────────────────────────
    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logger.info(f"[AirSensorManager] 설정 로드: {self.config_path}")
        except FileNotFoundError:
            logger.warning("[AirSensorManager] 설정 파일 없음, 기본값 사용")
            self.config = {
                "port": "/dev/ttyAMA2",
                "baudrate": 9600,
                "timeout": 1.0,
                "retries": 3,
                "de_re_pin": 17,
                "read_interval": 60,
                "simulation_mode": True,
                "sensors": []
            }
        except Exception as e:
            logger.error(f"[AirSensorManager] 설정 로드 오류: {e}")
            self.config = {"simulation_mode": True, "sensors": []}

        # AirSensor 객체 생성 (enabled만)
        self.sensors = []
        for s in self.config.get('sensors', []):
            if s.get('enabled', True):
                self.sensors.append(AirSensor(
                    address=s['address'],
                    name=s.get('name', f"구역 {s['address']} 대기"),
                    zone_id=s.get('zone_id', s['address'])
                ))
        logger.info(f"[AirSensorManager] 활성 센서 {len(self.sensors)}개")

    # ──────────────────────────────────────────────────────────────────
    # 하드웨어 초기화
    # ──────────────────────────────────────────────────────────────────
    def initialize(self) -> bool:
        if self.config.get('simulation_mode', True):
            logger.info("[AirSensorManager] 시뮬레이션 모드 — 하드웨어 초기화 생략")
            self._initialized = True
            return True

        # 시리얼 포트 열기
        try:
            import serial
            self.serial_port = serial.Serial(
                port     = self.config.get('port', '/dev/ttyAMA2'),
                baudrate = self.config.get('baudrate', 9600),
                bytesize = serial.EIGHTBITS,
                parity   = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                timeout  = self.config.get('timeout', 1.0)
            )
            logger.info(
                f"[AirSensorManager] 포트 열림: "
                f"{self.config.get('port')} @ {self.config.get('baudrate')}bps"
            )
        except Exception as e:
            logger.error(f"[AirSensorManager] 시리얼 포트 오류: {e}")
            return False

        # GPIO DE/RE 핀 초기화
        pin = self.config.get('de_re_pin', 17)
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)  # 기본: 수신 모드
            self._de_re_pin = pin
            self._gpio_ok   = True
            logger.info(f"[AirSensorManager] DE/RE GPIO{pin} 초기화 완료")
        except ImportError:
            logger.warning("[AirSensorManager] RPi.GPIO 없음 — GPIO 제어 불가")
        except Exception as e:
            logger.warning(f"[AirSensorManager] GPIO 초기화 오류: {e}")

        self._initialized = True
        return True

    def _set_tx(self, enable: bool):
        """DE/RE 핀 제어: True=송신, False=수신"""
        if self._gpio_ok and self._de_re_pin is not None:
            import RPi.GPIO as GPIO
            GPIO.output(self._de_re_pin, GPIO.HIGH if enable else GPIO.LOW)

    # ──────────────────────────────────────────────────────────────────
    # 단일 센서 읽기
    # ──────────────────────────────────────────────────────────────────
    def read_sensor(self, sensor: AirSensor) -> dict:
        if self.config.get('simulation_mode', True):
            return sensor.simulate()

        retries = self.config.get('retries', 3)
        for attempt in range(1, retries + 1):
            with self._lock:
                try:
                    self._set_tx(True)
                    time.sleep(0.002)
                    self.serial_port.reset_input_buffer()
                    self.serial_port.write(sensor._build_read_request())
                    self._set_tx(False)
                    time.sleep(0.05)
                    raw = self.serial_port.read(9)
                    temp, hum = sensor.parse_response(raw)

                    sensor.last_temperature = temp
                    sensor.last_humidity    = hum
                    sensor.last_read_time   = time.time()
                    sensor.valid            = True
                    sensor.error_count      = 0

                    return {
                        'sensor_id':   sensor.address,
                        'zone_id':     sensor.zone_id,
                        'name':        sensor.name,
                        'temperature': temp,
                        'humidity':    hum,
                        'valid':       True,
                        'timestamp':   time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception as e:
                    if attempt < retries:
                        logger.debug(
                            f"[AirSensorManager] addr={sensor.address} "
                            f"재시도 {attempt}/{retries}: {e}"
                        )
                        time.sleep(0.1 * attempt)
                    else:
                        sensor.error_count += 1
                        sensor.valid = False
                        logger.warning(
                            f"[AirSensorManager] addr={sensor.address} "
                            f"최대 재시도 초과: {e}"
                        )
                        return {
                            'sensor_id':   sensor.address,
                            'zone_id':     sensor.zone_id,
                            'name':        sensor.name,
                            'temperature': None,
                            'humidity':    None,
                            'valid':       False,
                            'error':       str(e),
                            'timestamp':   time.strftime('%Y-%m-%d %H:%M:%S')
                        }

    # ──────────────────────────────────────────────────────────────────
    # 전체 센서 읽기
    # ──────────────────────────────────────────────────────────────────
    def read_all(self) -> list:
        """모든 활성 센서 순차 읽기"""
        results = []
        for sensor in self.sensors:
            results.append(self.read_sensor(sensor))
            if not self.config.get('simulation_mode', True):
                time.sleep(0.1)   # 센서 간 지연
        return results

    def get_sensor_status(self) -> list:
        """마지막 측정값 반환"""
        return [
            {
                'sensor_id':   s.address,
                'zone_id':     s.zone_id,
                'name':        s.name,
                'temperature': s.last_temperature,
                'humidity':    s.last_humidity,
                'valid':       s.valid,
                'error_count': s.error_count,
                'last_read':   (
                    time.strftime('%Y-%m-%d %H:%M:%S',
                                  time.localtime(s.last_read_time))
                    if s.last_read_time else None
                )
            }
            for s in self.sensors
        ]

    def close(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            logger.info("[AirSensorManager] 시리얼 포트 닫힘")
        if self._gpio_ok and self._de_re_pin is not None:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup(self._de_re_pin)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s — %(message)s'
    )
    print("=" * 55)
    print("  AirSensorManager 단독 테스트 (시뮬레이션)")
    print("=" * 55)

    mgr = AirSensorManager()
    mgr.initialize()
    print(f"활성 센서 수: {len(mgr.sensors)}\n")

    results = mgr.read_all()
    for r in results:
        status = "✅" if r['valid'] else "❌"
        print(f"  {status} [{r['sensor_id']:2d}] {r['name']:15s} | "
              f"온도: {str(r.get('temperature','N/A')):6s}°C | "
              f"습도: {str(r.get('humidity','N/A')):6s}%")

    mgr.close()
    print("\n테스트 완료.")
