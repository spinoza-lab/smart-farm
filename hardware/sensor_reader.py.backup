#!/usr/bin/env python3
"""
sensor_reader.py
센서 데이터 읽기 클래스 (ADS1115 ADC)
"""

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time


class SensorReader:
    """ADS1115 ADC를 통한 센서 데이터 읽기"""
    
    # 센서 매핑
    SENSOR_MAP = {
        'water_level_1': 0,  # A0: 물탱크 1 수위센서
        'water_level_2': 1,  # A1: 물탱크 2 수위센서
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
        
        print(f"✅ SensorReader 초기화 완료")
    
    def read_voltage(self, channel):
        """
        전압 읽기
        
        Args:
            channel: 채널 번호 (0-3)
            
        Returns:
            float: 전압 (V)
        """
        if channel not in self.channels:
            print(f"❌ 잘못된 채널: {channel}")
            return None
        
        return self.channels[channel].voltage
    
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
    
    def read_water_level(self, tank_num):
        """
        물탱크 수위 읽기
        
        Args:
            tank_num: 탱크 번호 (1 또는 2)
            
        Returns:
            float: 수위 퍼센트 (0-100%)
        """
        if tank_num == 1:
            voltage = self.read_sensor('water_level_1')
        elif tank_num == 2:
            voltage = self.read_sensor('water_level_2')
        else:
            print(f"❌ 잘못된 탱크 번호: {tank_num}")
            return None
        
        if voltage is None:
            return None
        
        # 전압 → 퍼센트 변환
        # 예: 0V = 0%, 5V = 100%
        percent = (voltage / 5.0) * 100.0
        percent = max(0, min(100, percent))  # 0-100 범위로 제한
        
        return percent
    
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
    print("🧪 SensorReader 테스트")
    print("="*60)
    
    try:
        # 센서 리더 초기화
        sensor = SensorReader(address=0x48)
        
        # 테스트 1: 단일 채널 읽기
        print("\n[테스트 1] 채널 0 읽기")
        voltage = sensor.read_voltage(0)
        raw = sensor.read_raw(0)
        print(f"   전압: {voltage:.3f}V")
        print(f"   RAW: {raw}")
        
        # 테스트 2: 물탱크 수위 읽기
        print("\n[테스트 2] 물탱크 수위")
        for tank in [1, 2]:
            level = sensor.read_water_level(tank)
            if level is not None:
                print(f"   탱크 {tank}: {level:.1f}%")
        
        # 테스트 3: 모든 채널 읽기
        print("\n[테스트 3] 모든 채널 읽기")
        all_data = sensor.read_all_channels()
        for channel, voltage in all_data.items():
            print(f"   채널 {channel}: {voltage:.3f}V")
        
        # 테스트 4: 모니터링 (10초)
        print("\n[테스트 4] 센서 모니터링")
        sensor.monitor(interval=2, duration=10)
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
