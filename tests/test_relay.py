#!/usr/bin/env python3
"""
test_relay.py
릴레이 제어 테스트
MCP23017 출력 → 릴레이 → LED/밸브
"""

import board
import busio
from adafruit_mcp230xx.mcp23017 import MCP23017
from digitalio import Direction
import time

def test_single_relay(address=0x20, pin_num=0):
    """
    단일 릴레이 테스트
    
    Args:
        address: MCP23017 I2C 주소 (0x20 또는 0x21)
        pin_num: 릴레이 연결 핀 번호 (0-15)
    """
    print("=" * 50)
    print("🧪 단일 릴레이 테스트")
    print("=" * 50)
    print()
    
    try:
        # I2C 및 MCP23017 초기화
        i2c = busio.I2C(board.SCL, board.SDA)
        mcp = MCP23017(i2c, address=address)
        
        # 릴레이 핀 설정
        relay = mcp.get_pin(pin_num)
        relay.direction = Direction.OUTPUT
        relay.value = False  # 초기값 OFF
        
        print(f"릴레이 설정:")
        print(f"  주소: 0x{address:02X}")
        print(f"  핀: {pin_num}")
        print()
        
        # 릴레이 5회 ON/OFF
        print("릴레이 동작 테스트 (5회)")
        print("릴레이 '딸깍' 소리를 확인하세요!")
        print()
        
        for i in range(5):
            print(f"  [{i+1}/5] 🟢 릴레이 ON")
            relay.value = True
            time.sleep(2)
            
            print(f"  [{i+1}/5] ⚫ 릴레이 OFF")
            relay.value = False
            time.sleep(2)
        
        print()
        print("✅ 단일 릴레이 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

def test_multiple_relays(address=0x20, relay_count=8, interval=0.5):
    """
    다중 릴레이 순차 테스트
    
    Args:
        address: MCP23017 I2C 주소
        relay_count: 테스트할 릴레이 개수 (1-16)
        interval: 릴레이 간 간격 (초)
    """
    print("=" * 50)
    print(f"🧪 다중 릴레이 순차 테스트 ({relay_count}개)")
    print("=" * 50)
    print()
    
    try:
        # I2C 및 MCP23017 초기화
        i2c = busio.I2C(board.SCL, board.SDA)
        mcp = MCP23017(i2c, address=address)
        
        # 릴레이 핀 설정
        relays = []
        for i in range(relay_count):
            relay = mcp.get_pin(i)
            relay.direction = Direction.OUTPUT
            relay.value = False
            relays.append(relay)
        
        print(f"릴레이 {relay_count}개 초기화 완료")
        print()
        
        # 순차 ON
        print(f"1️⃣ 순차 ON (간격 {interval}초)")
        for i, relay in enumerate(relays):
            print(f"   릴레이 {i+1} ON")
            relay.value = True
            time.sleep(interval)
        
        time.sleep(1)
        
        # 순차 OFF
        print()
        print(f"2️⃣ 순차 OFF (간격 {interval}초)")
        for i, relay in enumerate(relays):
            print(f"   릴레이 {i+1} OFF")
            relay.value = False
            time.sleep(interval)
        
        print()
        
        # 전체 ON/OFF
        print("3️⃣ 전체 ON/OFF (3회)")
        for i in range(3):
            print(f"   [{i+1}/3] 전체 ON")
            for relay in relays:
                relay.value = True
            time.sleep(1)
            
            print(f"   [{i+1}/3] 전체 OFF")
            for relay in relays:
                relay.value = False
            time.sleep(1)
        
        print()
        print("✅ 다중 릴레이 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

def test_valve_simulation():
    """
    밸브 제어 시뮬레이션
    실제 스마트 관수 시스템과 동일한 방식으로 테스트
    """
    print("=" * 50)
    print("🧪 밸브 제어 시뮬레이션")
    print("=" * 50)
    print()
    
    try:
        # I2C 및 MCP23017 초기화
        i2c = busio.I2C(board.SCL, board.SDA)
        mcp1 = MCP23017(i2c, address=0x20)
        
        # 펌프 (핀 15)
        pump = mcp1.get_pin(15)
        pump.direction = Direction.OUTPUT
        pump.value = False
        
        # 밸브 (핀 0-2)
        valves = []
        for i in range(3):
            valve = mcp1.get_pin(i)
            valve.direction = Direction.OUTPUT
            valve.value = False
            valves.append(valve)
        
        print("시뮬레이션 시나리오:")
        print("  펌프 → 대기 2초 → 밸브 1 → 5초 관수 → 밸브 OFF")
        print("  → 밸브 2 → 5초 관수 → 밸브 OFF")
        print("  → 밸브 3 → 5초 관수 → 밸브 OFF → 대기 5초 → 펌프 OFF")
        print()
        
        # 펌프 ON
        print("1️⃣ 펌프 ON")
        pump.value = True
        print("   대기 2초 (안전 인터록)")
        time.sleep(2)
        
        # 각 밸브 순차 관수
        for i, valve in enumerate(valves, 1):
            print()
            print(f"2️⃣ 밸브 {i} 열기")
            valve.value = True
            print(f"   관수 5초...")
            
            for j in range(5):
                print(f"   ⏱️  {j+1}/5 초")
                time.sleep(1)
            
            print(f"   밸브 {i} 닫기")
            valve.value = False
            
            if i < len(valves):
                print("   다음 밸브까지 대기 2초")
                time.sleep(2)
        
        # 펌프 OFF
        print()
        print("3️⃣ 모든 관수 완료")
        print("   대기 5초 (안전 인터록)")
        time.sleep(5)
        print("   펌프 OFF")
        pump.value = False
        
        print()
        print("✅ 밸브 제어 시뮬레이션 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 시뮬레이션 실패: {e}")
        return False

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("릴레이 테스트 메뉴")
    print("=" * 50)
    print()
    print("1. 단일 릴레이 테스트")
    print("2. 다중 릴레이 순차 테스트 (8개)")
    print("3. 밸브 제어 시뮬레이션")
    print()
    
    choice = input("선택 (1-3, Enter=전체): ").strip()
    
    if choice == '1':
        test_single_relay(address=0x20, pin_num=0)
    elif choice == '2':
        test_multiple_relays(address=0x20, relay_count=8, interval=0.5)
    elif choice == '3':
        test_valve_simulation()
    else:
        # 전체 테스트
        print("\n전체 테스트를 시작합니다...\n")
        test_single_relay(address=0x20, pin_num=0)
        print("\n" + "="*50 + "\n")
        time.sleep(2)
        
        test_multiple_relays(address=0x20, relay_count=8, interval=0.5)
        print("\n" + "="*50 + "\n")
        time.sleep(2)
        
        test_valve_simulation()
