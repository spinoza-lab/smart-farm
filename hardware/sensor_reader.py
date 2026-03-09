#!/usr/bin/env python3
"""
sensor_reader.py
센서 데이터 읽기 클래스 (ADS1115 ADC) - 캘리브레이션 지원
"""

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time
import json
import os
import logging
from collections import defaultdict

_log = logging.getLogger(__name__)


class SensorReader:
    """ADS1115 ADC를 통한 센서 데이터 읽기"""
    
    # 센서 매핑
    SENSOR_MAP = {
        'water_level_1': 0,  # A0: 물탱크 1 수위센서
        'water_level_2': 1,  # A1: 양액탱크 2 수위센서
        'spare_1': 2,        # A2: 예비
        'spare_2': 3,        # A3: 예비
    }
    
    def __init__(self, address=0x48):
        """
        초기화
        
        Args:
            address: I2C 주소 (기본 0x48)
        """
        print(f"🔧 SensorReader 초기화 (주소: 0x{address:02X})")
        
        self.address = address
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(self.i2c, address=address)
        
        # 채널 객체 생성
        self.channels = {
            0: AnalogIn(self.ads, ADS.P0),
            1: AnalogIn(self.ads, ADS.P1),
            2: AnalogIn(self.ads, ADS.P2),
            3: AnalogIn(self.ads, ADS.P3),
        }
        
        # I2C 재시도 설정
        self.retry_count = 2        # 실패 시 재시도 횟수
        self.retry_delay = 0.05     # 재시도 간격 (50ms)
        self.use_fallback = True    # 마지막 정상값 fallback 사용 여부

        # 오류 추적 (채널별)
        self.last_valid_voltage = {}          # {ch: 마지막 정상 전압}
        self.consecutive_errors = defaultdict(int)  # {ch: 연속 오류 횟수}
        self.total_reads   = defaultdict(int) # {ch: 총 읽기 횟수}
        self.error_reads   = defaultdict(int) # {ch: 오류 횟수}

        # 캘리브레이션 로드
        self.calibration = self._load_calibration()
        
        print(f"✅ SensorReader 초기화 완료")
        print(f"   센서 타입: {self.calibration.get('sensor_type', 'voltage')}")
    
    def _load_calibration(self):
        """캘리브레이션 파일 로드"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config',
            'sensor_calibration.json'
        )
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    calibration = json.load(f)
                print(f"📋 캘리브레이션 로드 완료: {config_path}")
                return calibration
            else:
                print(f"⚠️  캘리브레이션 파일 없음, 기본값 사용")
                return self._get_default_calibration()
        except Exception as e:
            print(f"⚠️  캘리브레이션 로드 실패: {e}, 기본값 사용")
            return self._get_default_calibration()
    
    def _get_default_calibration(self):
        """기본 캘리브레이션 값"""
        return {
            'sensor_type': 'voltage',
            'tank1_water': {
                'empty_value': 0.5,
                'full_value': 4.5
            },
            'tank2_nutrient': {
                'empty_value': 0.5,
                'full_value': 4.5
            }
        }
    
    def reload_calibration(self):
        """캘리브레이션 재로드 (설정 변경 후 호출)"""
        print("🔄 캘리브레이션 재로드 중...")
        self.calibration = self._load_calibration()
        print("✅ 캘리브레이션 재로드 완료")
    
    def read_voltage(self, channel):
        """
        전압 읽기 (I2C 재시도 + fallback)

        Args:
            channel: 채널 번호 (0-3)

        Returns:
            float | None: 정상 시 전압값, 모두 실패 시 None (또는 마지막 정상값)
        """
        if channel not in self.channels:
            print(f"❌ 잘못된 채널: {channel}")
            return None

        self.total_reads[channel] += 1

        for attempt in range(self.retry_count + 1):   # 기본 총 3회 시도
            try:
                voltage = self.channels[channel].voltage

                # ✅ 성공 → 연속 오류 리셋, 정상값 저장
                if self.consecutive_errors[channel] > 0:
                    _log.info(f"[SensorReader] CH{channel} 복구 "
                              f"(이전 연속 오류: {self.consecutive_errors[channel]}회)")
                self.consecutive_errors[channel] = 0
                self.last_valid_voltage[channel]  = voltage
                return voltage

            except (OSError, IOError, TimeoutError) as e:
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay)
                    continue

                # ❌ 재시도 모두 실패
                self.consecutive_errors[channel] += 1
                self.error_reads[channel]         += 1
                _log.warning(
                    f"[SensorReader] CH{channel} 읽기 실패 "
                    f"(재시도 {self.retry_count}회) — "
                    f"{type(e).__name__}: {e} | "
                    f"연속 {self.consecutive_errors[channel]}회"
                )

                # fallback: 마지막 정상값 반환
                if self.use_fallback and channel in self.last_valid_voltage:
                    _log.info(
                        f"[SensorReader] CH{channel} fallback → "
                        f"{self.last_valid_voltage[channel]:.3f}V"
                    )
                    return self.last_valid_voltage[channel]

                return None   # fallback도 없으면 None

    def get_error_stats(self):
        """채널별 오류 통계 반환 (AlertManager / API 용)"""
        stats = {}
        for ch in range(4):
            total = self.total_reads[ch]
            errors = self.error_reads[ch]
            stats[f'ch{ch}'] = {
                'total_reads':       total,
                'error_reads':       errors,
                'success_rate':      round((total - errors) / total * 100, 2) if total > 0 else 100.0,
                'consecutive_errors': self.consecutive_errors[ch],
                'last_valid_voltage': self.last_valid_voltage.get(ch),
            }
        return stats
    
    def read_raw(self, channel):
        """
        RAW 값 읽기
        
        Args:
            channel: 채널 번호 (0-3)
            
        Returns:
            int: RAW 값
        """
        if channel not in self.channels:
            print(f"❌ 잘못된 채널: {channel}")
            return None
        
        return self.channels[channel].value
    
    def read_sensor(self, sensor_name):
        """
        센서 이름으로 전압 읽기
        
        Args:
            sensor_name: 센서 이름 ('water_level_1', 'water_level_2', ...)
            
        Returns:
            float: 전압 (V)
        """
        if sensor_name not in self.SENSOR_MAP:
            print(f"❌ 알 수 없는 센서: {sensor_name}")
            return None
        
        channel = self.SENSOR_MAP[sensor_name]
        return self.read_voltage(channel)
    
    def _voltage_to_percent(self, voltage, empty_value, full_value):
        """
        전압 → 퍼센트 변환 (선형 보간)
        
        Args:
            voltage: 현재 전압 (V)
            empty_value: 공탱크 전압 (V)
            full_value: 만수 전압 (V)
            
        Returns:
            float: 수위 퍼센트 (0-100%)
        """
        if full_value == empty_value:
            return 0.0
        
        percent = ((voltage - empty_value) / (full_value - empty_value)) * 100.0
        percent = max(0, min(100, percent))  # 0-100 범위로 제한
        
        return percent
    

    def read_water_level(self, tank_num):
        """
        물탱크 수위 읽기 (캘리브레이션 적용)
        
        Args:
            tank_num: 탱크 번호 (1 또는 2)
            
        Returns:
            float: 수위 퍼센트 (0-100%)
        """
        if tank_num == 1:
            voltage = self.read_sensor('water_level_1')
            tank_key = 'tank1_water'
        elif tank_num == 2:
            voltage = self.read_sensor('water_level_2')
            tank_key = 'tank2_nutrient'
        else:
            raise ValueError(f"유효하지 않은 탱크 번호: {tank_num}")
        
        # 캘리브레이션 값 가져오기
        empty_value = self.calibration.get(tank_key, {}).get('empty_value', 0.5)
        full_value = self.calibration.get(tank_key, {}).get('full_value', 4.5)
        sensor_type = self.calibration.get('sensor_type', 'voltage')
        
        # 전압 센서 (0~5V)
        percent = self._voltage_to_percent(voltage, empty_value, full_value)
        
        return max(0.0, min(100.0, percent))

    def read_all_channels(self):
        """
        모든 채널 읽기
        
        Returns:
            dict: {채널: 전압}
        """
        result = {}
        for channel in range(4):
            result[channel] = self.read_voltage(channel)
        return result
    
    def monitor(self, interval=2, duration=10):
        """
        센서 모니터링
        
        Args:
            interval: 읽기 간격 (초)
            duration: 모니터링 시간 (초)
        """
        print("\n" + "="*60)
        print(f"📊 센서 모니터링 시작 (간격: {interval}초, 지속: {duration}초)")
        print("="*60)
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                print(f"\n⏰ {time.strftime('%H:%M:%S')}")
                
                # 모든 채널 읽기
                for channel in range(4):
                    voltage = self.read_voltage(channel)
                    raw = self.read_raw(channel)
                    print(f"   채널 {channel}: {voltage:.3f}V (RAW: {raw})")
                
                # 물탱크 수위
                for tank in [1, 2]:
                    level = self.read_water_level(tank)
                    if level is not None:
                        print(f"   💧 탱크 {tank} 수위: {level:.1f}%")
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n⚠️  모니터링 중단")
        
        print("\n" + "="*60)
        print("✅ 모니터링 종료")
        print("="*60)
    
    def calibrate_sensor(self, sensor_name, samples=10):
        """
        센서 캘리브레이션
        
        Args:
            sensor_name: 센서 이름
            samples: 샘플 개수
            
        Returns:
            dict: {'min': 최소값, 'max': 최대값, 'avg': 평균값}
        """
        print(f"\n🔧 {sensor_name} 캘리브레이션 ({samples}회 측정)")
        
        values = []
        for i in range(samples):
            voltage = self.read_sensor(sensor_name)
            if voltage is not None:
                values.append(voltage)
                print(f"   [{i+1}/{samples}] {voltage:.3f}V")
            time.sleep(0.1)
        
        if not values:
            print("❌ 캘리브레이션 실패")
            return None
        
        result = {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values)
        }
        
        print(f"\n📊 캘리브레이션 결과:")
        print(f"   최소: {result['min']:.3f}V")
        print(f"   최대: {result['max']:.3f}V")
        print(f"   평균: {result['avg']:.3f}V")
        
        return result


# 테스트 코드
if __name__ == "__main__":
    print("="*60)
    print("🧪 SensorReader 테스트 (캘리브레이션 지원)")
    print("="*60)
    
    try:
        # 센서 리더 초기화
        sensor = SensorReader(address=0x48)
        
        # 테스트 1: 캘리브레이션 정보 출력
        print("\n[테스트 1] 캘리브레이션 정보")
        print(f"   센서 타입: {sensor.calibration.get('sensor_type')}")
        print(f"   탱크1 공탱크: {sensor.calibration['tank1_water']['empty_value']}V")
        print(f"   탱크1 만수: {sensor.calibration['tank1_water']['full_value']}V")
        print(f"   탱크2 공탱크: {sensor.calibration['tank2_nutrient']['empty_value']}V")
        print(f"   탱크2 만수: {sensor.calibration['tank2_nutrient']['full_value']}V")
        
        # 테스트 2: 단일 채널 읽기
        print("\n[테스트 2] 채널 0 읽기")
        voltage = sensor.read_voltage(0)
        raw = sensor.read_raw(0)
        print(f"   전압: {voltage:.3f}V")
        print(f"   RAW: {raw}")
        
        # 테스트 3: 물탱크 수위 읽기 (캘리브레이션 적용)
        print("\n[테스트 3] 물탱크 수위 (캘리브레이션 적용)")
        for tank in [1, 2]:
            level = sensor.read_water_level(tank)
            if level is not None:
                print(f"   탱크 {tank}: {level:.1f}%")
        
        # 테스트 4: 모든 채널 읽기
        print("\n[테스트 4] 모든 채널 읽기")
        all_data = sensor.read_all_channels()
        for channel, voltage in all_data.items():
            print(f"   채널 {channel}: {voltage:.3f}V")
        
        # 테스트 5: 캘리브레이션 재로드
        print("\n[테스트 5] 캘리브레이션 재로드")
        sensor.reload_calibration()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
