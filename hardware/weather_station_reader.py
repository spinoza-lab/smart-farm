#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weather_station_reader.py — MISOL WH65LP 기상 관측소 파서
RS-485, /dev/ttyAMA3, 9600bps, 25바이트 커스텀 HEX 패킷
DE/RE → GND 고정 (수신 전용)

─── WH65LP 25바이트 패킷 레이아웃 ──────────────────────────────────
Byte 00   : 0x24 (헤더)
Byte 01   : 0xFF (2번째 헤더)
Byte 02   : 송신기 ID [high]
Byte 03   : 송신기 ID [low]
Byte 04   : 풍향 [high, 0-359°]
Byte 05   : 풍향 [low]
Byte 06   : 풍속 [x0.1 m/s]
Byte 07   : 최대 풍속 [x0.1 m/s]
Byte 08   : 강우량 누적 [high, x0.1 mm]
Byte 09   : 강우량 누적 [low]
Byte 10   : UV 지수 [x0.1]
Byte 11   : 조도 [high, lux]
Byte 12   : 조도 [mid]
Byte 13   : 조도 [low]
Byte 14   : 온도 [high, int16, x0.1°C]
Byte 15   : 온도 [low]
Byte 16   : 습도 [%RH]
Byte 17   : 기압 [high, x0.1 hPa]
Byte 18   : 기압 [mid]
Byte 19   : 기압 [low]
Byte 20   : 배터리 상태 (0=OK, 1=LOW)
Byte 21   : 예약 (0x00)
Byte 22   : 예약 (0x00)
Byte 23   : CRC-8 (polynomial 0x31, init 0x00, byte 0~22 대상)
Byte 24   : 체크섬 (bytes 0~23 합산, 하위 8비트)
────────────────────────────────────────────────────────────────────
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
    'config', 'weather_station.json'
)

PACKET_LENGTH = 25
HEADER_BYTE   = 0x24


class WeatherStationReader:
    """
    MISOL WH65LP 기상 관측소 수신기
    - 25바이트 커스텀 HEX 패킷 파싱
    - 16초마다 자동 송신 수신
    - simulation_mode: True → 하드웨어 없이 테스트 가능
    """

    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path    = config_path
        self.config         = {}
        self.serial_port    = None
        self._lock          = threading.Lock()
        self._initialized   = False
        self._buffer        = bytearray()

        self.last_data       = None
        self.last_read_time  = None
        self.error_count     = 0
        self.packet_count    = 0

        self._load_config()

    # ──────────────────────────────────────────────────────────────────
    # 설정 로드
    # ──────────────────────────────────────────────────────────────────
    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logger.info(f"[WeatherStation] 설정 로드: {self.config_path}")
        except FileNotFoundError:
            logger.warning("[WeatherStation] 설정 파일 없음, 기본값 사용")
            self.config = {
                "port": "/dev/ttyAMA3",
                "baudrate": 9600,
                "timeout": 2.0,
                "simulation_mode": True,
                "log_dir": "data/weather_logs"
            }
        except Exception as e:
            logger.error(f"[WeatherStation] 설정 로드 오류: {e}")
            self.config = {"simulation_mode": True}

    # ──────────────────────────────────────────────────────────────────
    # CRC-8 / 체크섬
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _crc8(data: bytes, poly: int = 0x31, init: int = 0x00) -> int:
        """CRC-8 (polynomial 0x31, Dallas/Maxim 방식)"""
        crc = init
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ poly) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc

    @staticmethod
    def _checksum(data: bytes) -> int:
        """단순 합산 체크섬 (하위 8비트)"""
        return sum(data) & 0xFF

    # ──────────────────────────────────────────────────────────────────
    # 패킷 파싱
    # ──────────────────────────────────────────────────────────────────
    def parse_packet(self, packet: bytes) -> dict:
        """
        25바이트 WH65LP 패킷 파싱
        반환: 기상 데이터 dict
        예외: ValueError (파싱 실패 시)
        """
        if len(packet) != PACKET_LENGTH:
            raise ValueError(
                f"패킷 길이 오류: {len(packet)}바이트 (기대 {PACKET_LENGTH})"
            )
        if packet[0] != HEADER_BYTE:
            raise ValueError(
                f"헤더 바이트 오류: {packet[0]:#04x} (기대 {HEADER_BYTE:#04x})"
            )

        # CRC-8 검증 (byte 0~22)
        crc_calc = self._crc8(packet[:23])
        crc_recv = packet[23]
        if crc_calc != crc_recv:
            raise ValueError(
                f"CRC-8 불일치: 계산={crc_calc:#04x}, 수신={crc_recv:#04x}"
            )

        # 체크섬 검증 (byte 0~23)
        chk_calc = self._checksum(packet[:24])
        chk_recv = packet[24]
        if chk_calc != chk_recv:
            raise ValueError(
                f"체크섬 불일치: 계산={chk_calc:#04x}, 수신={chk_recv:#04x}"
            )

        # ── 데이터 파싱 ─────────────────────────────────────────────
        station_id   = (packet[2] << 8) | packet[3]

        wind_dir     = ((packet[4] << 8) | packet[5]) & 0x1FF   # 0~359°
        wind_dir_str = self._deg_to_compass(wind_dir)

        wind_speed   = round(packet[6] * 0.1, 1)        # m/s
        gust_speed   = round(packet[7] * 0.1, 1)        # m/s

        rainfall     = round(((packet[8] << 8) | packet[9]) * 0.1, 1)  # mm

        uv_index     = round(packet[10] * 0.1, 1)

        illuminance  = (packet[11] << 16) | (packet[12] << 8) | packet[13]  # lux

        temp_raw     = struct.unpack('>h', bytes([packet[14], packet[15]]))[0]
        temperature  = round(temp_raw * 0.1, 1)          # °C

        humidity     = int(packet[16])                    # %RH

        pressure_raw = (packet[17] << 16) | (packet[18] << 8) | packet[19]
        pressure     = round(pressure_raw * 0.1, 1)      # hPa

        battery_ok   = (packet[20] == 0)

        # 유효성 범위 검사
        if not (-40.0 <= temperature <= 60.0):
            raise ValueError(f"온도 범위 초과: {temperature}°C")
        if not (0 <= humidity <= 100):
            raise ValueError(f"습도 범위 초과: {humidity}%")
        if not (0.0 <= wind_speed <= 60.0):
            raise ValueError(f"풍속 범위 초과: {wind_speed} m/s")
        if not (0 <= wind_dir <= 359):
            raise ValueError(f"풍향 범위 초과: {wind_dir}°")
        if not (300.0 <= pressure <= 1100.0):
            raise ValueError(f"기압 범위 초과: {pressure} hPa")

        self.packet_count += 1
        return {
            'station_id':   station_id,
            'temperature':  temperature,
            'humidity':     humidity,
            'wind_speed':   wind_speed,
            'gust_speed':   gust_speed,
            'wind_dir':     wind_dir,
            'wind_dir_str': wind_dir_str,
            'rainfall':     rainfall,
            'uv_index':     uv_index,
            'illuminance':  illuminance,
            'pressure':     pressure,
            'battery_ok':   battery_ok,
            'valid':        True,
            'timestamp':    time.strftime('%Y-%m-%d %H:%M:%S'),
            'packet_count': self.packet_count
        }

    @staticmethod
    def _deg_to_compass(degrees: int) -> str:
        """풍향 각도 → 16방위 문자열"""
        dirs = [
            'N','NNE','NE','ENE','E','ESE','SE','SSE',
            'S','SSW','SW','WSW','W','WNW','NW','NNW'
        ]
        return dirs[round(degrees / 22.5) % 16]

    # ──────────────────────────────────────────────────────────────────
    # 하드웨어 초기화
    # ──────────────────────────────────────────────────────────────────
    def initialize(self) -> bool:
        if self.config.get('simulation_mode', True):
            logger.info("[WeatherStation] 시뮬레이션 모드 — 하드웨어 초기화 생략")
            self._initialized = True
            return True

        try:
            import serial
            port    = self.config.get('port', '/dev/ttyAMA3')
            baud    = self.config.get('baudrate', 9600)
            timeout = self.config.get('timeout', 2.0)
            self.serial_port = serial.Serial(
                port=port, baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            logger.info(f"[WeatherStation] 포트 열림: {port} @ {baud}bps (수신 전용)")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"[WeatherStation] 포트 열기 실패: {e}")
            return False

    # ──────────────────────────────────────────────────────────────────
    # 데이터 읽기
    # ──────────────────────────────────────────────────────────────────
    def read(self):
        """패킷 수신 및 파싱 (헤더 탐색 방식)"""
        if self.config.get('simulation_mode', True):
            return self.simulate()

        if not self._initialized or self.serial_port is None:
            logger.error("[WeatherStation] 초기화 안됨")
            return None

        try:
            with self._lock:
                new_bytes = self.serial_port.read(50)
                if new_bytes:
                    self._buffer.extend(new_bytes)

                # 버퍼에서 헤더(0x24) 탐색 후 25바이트 파싱
                while len(self._buffer) >= PACKET_LENGTH:
                    idx = self._buffer.find(HEADER_BYTE)
                    if idx == -1:
                        self._buffer.clear()
                        break
                    if idx > 0:
                        del self._buffer[:idx]   # 헤더 앞 쓰레기 데이터 버림

                    if len(self._buffer) < PACKET_LENGTH:
                        break

                    packet = bytes(self._buffer[:PACKET_LENGTH])
                    try:
                        data = self.parse_packet(packet)
                        del self._buffer[:PACKET_LENGTH]
                        self.last_data      = data
                        self.last_read_time = time.time()
                        self.error_count    = 0
                        return data
                    except ValueError as e:
                        logger.debug(f"[WeatherStation] 파싱 실패 → 1바이트 스킵: {e}")
                        del self._buffer[:1]
                        continue
        except Exception as e:
            self.error_count += 1
            logger.warning(f"[WeatherStation] 읽기 오류: {e}")
        return None

    def simulate(self) -> dict:
        """시뮬레이션 데이터 생성"""
        temperature = round(random.uniform(15.0, 35.0), 1)
        humidity    = random.randint(30, 90)
        wind_speed  = round(random.uniform(0.0, 8.0), 1)
        gust_speed  = round(wind_speed + random.uniform(0.0, 2.0), 1)
        wind_dir    = random.randint(0, 359)
        rainfall    = round(random.uniform(0.0, 2.0) if random.random() < 0.1 else 0.0, 1)
        uv_index    = round(random.uniform(0.0, 8.0), 1)
        illuminance = random.randint(5000, 80000)
        pressure    = round(random.uniform(1005.0, 1025.0), 1)

        self.packet_count += 1
        data = {
            'station_id':   1,
            'temperature':  temperature,
            'humidity':     humidity,
            'wind_speed':   wind_speed,
            'gust_speed':   gust_speed,
            'wind_dir':     wind_dir,
            'wind_dir_str': self._deg_to_compass(wind_dir),
            'rainfall':     rainfall,
            'uv_index':     uv_index,
            'illuminance':  illuminance,
            'pressure':     pressure,
            'battery_ok':   True,
            'valid':        True,
            'simulated':    True,
            'timestamp':    time.strftime('%Y-%m-%d %H:%M:%S'),
            'packet_count': self.packet_count
        }
        self.last_data      = data
        self.last_read_time = time.time()
        return data

    def get_last_data(self):
        return self.last_data

    def close(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            logger.info("[WeatherStation] 포트 닫힘")


# ──────────────────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s — %(message)s'
    )
    print("=" * 55)
    print("  WeatherStationReader 단독 테스트 (시뮬레이션)")
    print("=" * 55)

    ws = WeatherStationReader()
    ws.initialize()

    for i in range(3):
        data = ws.read()
        if data:
            print(f"\n[패킷 #{data['packet_count']}]  {data['timestamp']}")
            print(f"  온도:  {data['temperature']:5.1f} °C     습도: {data['humidity']:3d} %")
            print(f"  풍속:  {data['wind_speed']:5.1f} m/s    풍향: {data['wind_dir']:3d}° ({data['wind_dir_str']})")
            print(f"  돌풍:  {data['gust_speed']:5.1f} m/s    강우: {data['rainfall']} mm")
            print(f"  UV:   {data['uv_index']:5.1f}         조도: {data['illuminance']:,} lux")
            print(f"  기압: {data['pressure']:7.1f} hPa   배터리: {'정상' if data['battery_ok'] else '부족'}")
        time.sleep(1)

    ws.close()
    print("\n테스트 완료.")
