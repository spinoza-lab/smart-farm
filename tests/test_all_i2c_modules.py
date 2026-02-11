#!/usr/bin/env python3
"""
test_all_i2c_modules.py
모든 I2C 모듈 통합 테스트
- MCP23017 x2 (0x20, 0x21)
- ADS1115 (0x48)
- RTC DS1307 (0x68)
"""

import board
import busio
from test_mcp23017 import test_mcp23017
import time

def scan_i2c():
    """I2C 장치 스캔"""
    print("\n" + "="*60)
    print("🔍 I2C 장치 스캔")
    print("="*60)
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # I2C 스캔
        while not i2c.try_lock():
            pass
        
        devices = i2c.scan()
        i2c.unlock()
        
        print(f"\n발견된 I2C 장치: {len(devices)}개")
        
        device_map = {
            0x20: "MCP23017 #1",
            0x21: "MCP23017 #2",
            0x48: "ADS1115",
            0x68: "RTC DS1307"
        }
        
        for addr in devices:
            name = device_map.get(addr, "알 수 없는 장치")
            print(f"  • 0x{addr:02X}: {name}")
        
        return devices
        
    except Exception as e:
        print(f"\n❌ I2C 스캔 실패: {e}")
        return []

def test_mcp23017_both():
    """MCP23017 x2 테스트"""
    print("\n" + "="*60)
    print("🧪 MCP23017 GPIO 확장 보드 테스트")
    print("="*60)
    
    results = {}
    
    # MCP23017 #1 (0x20)
    print("\n📍 MCP23017 #1 (0x20) 테스트")
    print("-"*60)
    results['MCP #1'] = test_mcp23017(address=0x20, pin_num=0, test_count=2)
    
    time.sleep(1)
    
    # MCP23017 #2 (0x21)
    print("\n📍 MCP23017 #2 (0x21) 테스트")
    print("-"*60)
    results['MCP #2'] = test_mcp23017(address=0x21, pin_num=0, test_count=2)
    
    return results

def test_ads1115():
    """ADS1115 ADC 테스트"""
    print("\n" + "="*60)
    print("🧪 ADS1115 ADC 테스트")
    print("="*60)
    
    try:
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=0x48)
        
        print("\n✓ ADS1115 (0x48) 연결 성공")
        
        # 채널 0 빠른 테스트
        chan = AnalogIn(ads, ADS.P0)
        print(f"  채널 0 전압: {chan.voltage:.3f}V")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ADS1115 테스트 실패: {e}")
        return False

def test_rtc():
    """RTC DS1307 테스트"""
    print("\n" + "="*60)
    print("🧪 RTC DS1307 테스트")
    print("="*60)
    
    try:
        import adafruit_ds1307
        import datetime
        
        i2c = busio.I2C(board.SCL, board.SDA)
        rtc = adafruit_ds1307.DS1307(i2c)
        
        print("\n✓ RTC DS1307 (0x68) 연결 성공")
        
        t = rtc.datetime
        print(f"  RTC 시간: {t.tm_year}/{t.tm_mon:02d}/{t.tm_mday:02d} "
              f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ RTC 테스트 실패: {e}")
        return False

def main():
    """전체 테스트 실행"""
    print("\n" + "="*60)
    print("🚀 스마트 관수 시스템 - I2C 모듈 통합 테스트")
    print("="*60)
    
    results = {}
    
    # 1. I2C 스캔
    devices = scan_i2c()
    
    if not devices:
        print("\n❌ I2C 장치를 찾을 수 없습니다!")
        return False
    
    time.sleep(2)
    
    # 2. MCP23017 x2 테스트
    mcp_results = test_mcp23017_both()
    results.update(mcp_results)
    
    time.sleep(2)
    
    # 3. ADS1115 테스트
    results['ADS1115'] = test_ads1115()
    
    time.sleep(2)
    
    # 4. RTC 테스트
    results['RTC DS1307'] = test_rtc()
    
    # 5. 최종 결과 요약
    print("\n" + "="*60)
    print("📊 최종 테스트 결과")
    print("="*60)
    
    for name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"\n  {name:20s}: {status}")
    
    all_success = all(results.values())
    
    print("\n" + "="*60)
    if all_success:
        print("🎉 모든 I2C 모듈 테스트 성공!")
        print("\n다음 단계:")
        print("  1️⃣ 릴레이 모듈 6채널 x4개 구매")
        print("  2️⃣ 체크밸브 50A x3개 구매")
        print("  3️⃣ 외부 5V 5A 어댑터 구매")
        print("  4️⃣ 릴레이 통합 테스트")
    else:
        print("⚠️  일부 모듈 테스트 실패")
        print("   → 실패한 모듈의 배선을 확인하세요")
    
    print("="*60)
    
    return all_success

if __name__ == '__main__':
    main()
