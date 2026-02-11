#!/usr/bin/env python3
"""
gpio_expander.py
MCP23017 GPIO 확장 보드 관리 클래스
"""

import board
import busio
from adafruit_mcp230xx.mcp23017 import MCP23017
from digitalio import Direction
import time


class GPIOExpander:
    """MCP23017 GPIO 확장 보드 관리"""
    
    def __init__(self, address=0x20):
        """
        초기화
        
        Args:
            address: I2C 주소 (0x20 또는 0x21)
        """
        self.address = address
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.mcp = MCP23017(self.i2c, address=address)
        self.pins = {}
        
        print(f"✓ MCP23017 (0x{address:02X}) 초기화 완료")
    
    def setup_pin(self, pin_num, direction=Direction.OUTPUT, initial_value=False):
        """
        핀 설정
        
        Args:
            pin_num: 핀 번호 (0-15)
            direction: Direction.OUTPUT 또는 Direction.INPUT
            initial_value: 초기값 (OUTPUT일 때)
        """
        if pin_num in self.pins:
            print(f"⚠️  핀 {pin_num}은 이미 설정되었습니다")
            return self.pins[pin_num]
        
        pin = self.mcp.get_pin(pin_num)
        pin.direction = direction
        
        if direction == Direction.OUTPUT:
            pin.value = initial_value
        
        self.pins[pin_num] = pin
        print(f"✓ 핀 {pin_num} 설정 완료 (방향: {'OUTPUT' if direction == Direction.OUTPUT else 'INPUT'})")
        
        return pin
    
    def set_pin(self, pin_num, value):
        """
        핀 출력 설정
        
        Args:
            pin_num: 핀 번호
            value: True(HIGH) 또는 False(LOW)
        """
        if pin_num not in self.pins:
            self.setup_pin(pin_num)
        
        self.pins[pin_num].value = value
    
    def get_pin(self, pin_num):
        """
        핀 상태 읽기
        
        Args:
            pin_num: 핀 번호
            
        Returns:
            bool: 핀 상태
        """
        if pin_num not in self.pins:
            print(f"❌ 핀 {pin_num}이 설정되지 않았습니다")
            return None
        
        return self.pins[pin_num].value
    
    def pulse(self, pin_num, duration=0.1):
        """
        핀에 펄스 신호 출력
        
        Args:
            pin_num: 핀 번호
            duration: 펄스 지속 시간 (초)
        """
        self.set_pin(pin_num, True)
        time.sleep(duration)
        self.set_pin(pin_num, False)
    
    def all_off(self):
        """모든 핀 OFF"""
        for pin_num, pin in self.pins.items():
            if pin.direction == Direction.OUTPUT:
                pin.value = False
        print(f"✓ MCP23017 (0x{self.address:02X}) 모든 핀 OFF")
    
    def cleanup(self):
        """정리"""
        self.all_off()
        print(f"✓ MCP23017 (0x{self.address:02X}) 정리 완료")


# 테스트 코드
if __name__ == "__main__":
    print("="*50)
    print("🧪 GPIOExpander 테스트")
    print("="*50)
    
    try:
        # MCP23017 #1 테스트
        gpio1 = GPIOExpander(address=0x20)
        
        # 핀 0 설정
        gpio1.setup_pin(0)
        
        # 점멸 테스트
        print("\n점멸 테스트 (3회)...")
        for i in range(3):
            print(f"  [{i+1}/3] ON")
            gpio1.set_pin(0, True)
            time.sleep(0.5)
            
            print(f"  [{i+1}/3] OFF")
            gpio1.set_pin(0, False)
            time.sleep(0.5)
        
        # 정리
        gpio1.cleanup()
        
        print("\n" + "="*50)
        print("✅ 테스트 완료!")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
