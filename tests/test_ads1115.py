#!/usr/bin/env python3
"""
test_ads1115.py
ADS1115 ADC 테스트 (v3.x 호환)
"""

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time

def test_ads1115(address=0x48, channel=0, duration=10):
    print("=" * 50)
    print("🧪 ADS1115 ADC 테스트")
    print("=" * 50)
    print()
    
    try:
        # I2C 초기화
        print("1️⃣ I2C 초기화 중...")
        i2c = busio.I2C(board.SCL, board.SDA)
        print("   ✓ I2C 초기화 성공")
        print()
        
        # ADS1115 연결
        print(f"2️⃣ ADS1115 연결 중... (주소: 0x{address:02X})")
        ads = ADS.ADS1115(i2c, address=address)
        print(f"   ✓ ADS1115 (0x{address:02X}) 연결 성공")
        print()
        
        # 채널 설정
        print(f"3️⃣ 채널 {channel} 설정 중...")
        
        # 채널 핀 매핑 (v3.x 호환)
        channels = {
            0: ADS.P0,
            1: ADS.P1,
            2: ADS.P2,
            3: ADS.P3
        }
        
        if channel not in channels:
            print(f"   ❌ 잘못된 채널: {channel} (0-3만 가능)")
            return False
        
        chan = AnalogIn(ads, channels[channel])
        print(f"   ✓ 채널 {channel} 설정 완료")
        print()
        
        # 전압 측정
        print(f"4️⃣ 전압 측정 ({duration}초)")
        print()
        print("   📊 측정 시작...")
        print("   " + "-" * 45)
        
        for i in range(duration):
            voltage = chan.voltage
            value = chan.value
            
            # 프로그레스 바
            bar_length = 30
            bar_filled = int((voltage / 3.3) * bar_length)
            bar = "█" * bar_filled + "░" * (bar_length - bar_filled)
            
            print(f"   [{i+1:2d}/{duration:2d}] {voltage:.3f}V |{bar}| ({value:5d})")
            time.sleep(1)
        
        print("   " + "-" * 45)
        print()
        print("=" * 50)
        print("✅ ADS1115 테스트 완료!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print()
        print(f"❌ 테스트 실패: {e}")
        print()
        print("🔍 배선 확인:")
        print("   VDD → 3.3V (Pin 1)")
        print("   GND → GND (Pin 6)")
        print("   SDA → GPIO2 (Pin 3)")
        print("   SCL → GPIO3 (Pin 5)")
        print("   ADDR → GND")
        return False

if __name__ == '__main__':
    test_ads1115(address=0x48, channel=0, duration=10)
