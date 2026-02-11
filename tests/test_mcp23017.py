#!/usr/bin/env python3
"""
test_mcp23017.py
MCP23017 GPIO 확장 보드 테스트
LED 또는 릴레이를 연결하여 ON/OFF 동작 확인
"""

import board
import busio
from adafruit_mcp230xx.mcp23017 import MCP23017
from digitalio import Direction
import time

def test_mcp23017(address=0x20, pin_num=0, test_count=5):
    """
    MCP23017 테스트
    
    Args:
        address: I2C 주소 (0x20 또는 0x21)
        pin_num: 테스트할 핀 번호 (0-15)
        test_count: 테스트 반복 횟수
    """
    print("=" * 50)
    print("🧪 MCP23017 GPIO 확장 보드 테스트")
    print("=" * 50)
    print()
    
    try:
        # I2C 초기화
        print("1️⃣ I2C 초기화 중...")
        i2c = busio.I2C(board.SCL, board.SDA)
        print("   ✓ I2C 초기화 성공")
        print()
        
        # MCP23017 연결
        print(f"2️⃣ MCP23017 연결 중... (주소: 0x{address:02X})")
        mcp = MCP23017(i2c, address=address)
        print(f"   ✓ MCP23017 (0x{address:02X}) 연결 성공")
        print()
        
        # 핀 설정
        print(f"3️⃣ 핀 {pin_num} 출력 모드 설정 중...")
        pin = mcp.get_pin(pin_num)
        pin.direction = Direction.OUTPUT
        print(f"   ✓ 핀 {pin_num} 출력 모드 설정 완료")
        print()
        
        # LED/릴레이 점멸 테스트
        print(f"4️⃣ LED/릴레이 점멸 테스트 ({test_count}회)")
        print("   핀 0에 LED를 연결하세요:")
        print("   핀0 → 저항(220Ω) → LED → GND")
        print()
        
        for i in range(test_count):
            print(f"   [{i+1}/{test_count}] 🟢 ON")
            pin.value = True
            time.sleep(1)
            
            print(f"   [{i+1}/{test_count}] ⚫ OFF")
            pin.value = False
            time.sleep(1)
        
        print()
        print("=" * 50)
        print("✅ MCP23017 테스트 완료!")
        print("=" * 50)
        return True
        
    except ValueError as e:
        print()
        print("❌ MCP23017을 찾을 수 없습니다!")
        print()
        print("🔍 문제 해결 방법:")
        print(f"   1. i2cdetect -y 1 을 실행하여 0x{address:02X} 주소 확인")
        print("   2. 배선 확인:")
        print("      - VDD → 3.3V (Pin 1)")
        print("      - GND → GND (Pin 6)")
        print("      - SDA → GPIO 2 (Pin 3)")
        print("      - SCL → GPIO 3 (Pin 5)")
        print("      - A0, A1, A2 → GND (주소 0x20으로 설정)")
        print(f"   3. 주소를 0x21로 바꾸고 싶으면: A0 → 3.3V")
        return False
        
    except Exception as e:
        print()
        print(f"❌ 테스트 실패: {e}")
        print()
        print("🔍 문제 해결:")
        print("   1. I2C가 활성화되어 있는지 확인")
        print("      sudo raspi-config → Interface → I2C → Enable")
        print("   2. 라즈베리파이 재부팅")
        print("   3. 권한 확인: 사용자가 i2c 그룹에 속해 있는지")
        return False

if __name__ == '__main__':
    # 기본 테스트 (0x20, 핀 0, 5회)
    test_mcp23017(address=0x20, pin_num=0, test_count=5)
    
    # 다른 주소 테스트 (주석 해제하여 사용)
    # test_mcp23017(address=0x21, pin_num=0, test_count=5)
