#!/usr/bin/env python3
"""
relay_controller.py
릴레이 제어 클래스
"""

from gpio_expander import GPIOExpander
import time


class RelayController:
    """릴레이 모듈 제어"""
    
    # 릴레이 매핑 (예시)
    RELAY_MAP = {
        # 관수 밸브 (12개)
        'valve': {
            1: (0x20, 0),   # MCP #1, PA0
            2: (0x20, 1),   # MCP #1, PA1
            3: (0x20, 2),   # MCP #1, PA2
            4: (0x20, 3),   # MCP #1, PA3
            5: (0x20, 4),   # MCP #1, PA4
            6: (0x20, 5),   # MCP #1, PA5
            7: (0x20, 6),   # MCP #1, PA6
            8: (0x20, 7),   # MCP #1, PA7
            9: (0x20, 8),   # MCP #1, PB0
            10: (0x20, 9),  # MCP #1, PB1
            11: (0x20, 10), # MCP #1, PB2
            12: (0x20, 11), # MCP #1, PB3
        },
        
        # 펌프 (3개)
        'pump': {
            1: (0x20, 12),  # MCP #1, PB4
            2: (0x20, 13),  # MCP #1, PB5
            3: (0x20, 14),  # MCP #1, PB6
        },
        
        # 분배 밸브 (3개)
        'main_valve': {
            1: (0x20, 15),  # MCP #1, PB7
            2: (0x21, 0),   # MCP #2, PA0
            3: (0x21, 1),   # MCP #2, PA1
        },
        
        # 배수 밸브 (4개)
        'drain': {
            1: (0x21, 2),   # MCP #2, PA2
            2: (0x21, 3),   # MCP #2, PA3
            3: (0x21, 4),   # MCP #2, PA4
            4: (0x21, 5),   # MCP #2, PA5
        },
        
        # 예비 (2개)
        'spare': {
            1: (0x21, 6),   # MCP #2, PA6
            2: (0x21, 7),   # MCP #2, PA7
        }
    }
    
    def __init__(self):
        """초기화"""
        print("="*50)
        print("🔧 RelayController 초기화")
        print("="*50)
        
        # GPIO 확장 보드 초기화
        self.gpio_expanders = {
            0x20: GPIOExpander(address=0x20),
            0x21: GPIOExpander(address=0x21)
        }
        
        # 모든 릴레이 핀 설정
        self._setup_all_relays()
        
        print("\n✅ RelayController 초기화 완료")
        print("="*50)
    
    def _setup_all_relays(self):
        """모든 릴레이 핀 설정"""
        print("\n릴레이 핀 설정 중...")
        
        for category, relays in self.RELAY_MAP.items():
            for num, (addr, pin) in relays.items():
                self.gpio_expanders[addr].setup_pin(pin, initial_value=False)
        
        print("✓ 모든 릴레이 핀 설정 완료")
    
    def _set_relay(self, category, num, state):
        """
        릴레이 제어 (내부 메서드)
        
        Args:
            category: 릴레이 종류 ('valve', 'pump', 'main_valve', 'drain', 'spare')
            num: 릴레이 번호
            state: True(ON) 또는 False(OFF)
        """
        if category not in self.RELAY_MAP:
            print(f"❌ 잘못된 카테고리: {category}")
            return False
        
        if num not in self.RELAY_MAP[category]:
            print(f"❌ 잘못된 번호: {category} {num}")
            return False
        
        addr, pin = self.RELAY_MAP[category][num]
        self.gpio_expanders[addr].set_pin(pin, state)
        
        state_str = "ON" if state else "OFF"
        print(f"{'🟢' if state else '⚫'} {category.upper()} #{num} → {state_str}")
        
        return True
    
    # ===== 관수 밸브 제어 =====
    
    def valve_on(self, num):
        """관수 밸브 ON"""
        return self._set_relay('valve', num, True)
    
    def valve_off(self, num):
        """관수 밸브 OFF"""
        return self._set_relay('valve', num, False)
    
    def valve_toggle(self, num):
        """관수 밸브 토글"""
        addr, pin = self.RELAY_MAP['valve'][num]
        current = self.gpio_expanders[addr].get_pin(pin)
        return self._set_relay('valve', num, not current)
    
    # ===== 펌프 제어 =====
    
    def pump_on(self, num):
        """펌프 ON"""
        return self._set_relay('pump', num, True)
    
    def pump_off(self, num):
        """펌프 OFF"""
        return self._set_relay('pump', num, False)
    
    # ===== 분배 밸브 제어 =====
    
    def main_valve_on(self, num):
        """분배 밸브 ON"""
        return self._set_relay('main_valve', num, True)
    
    def main_valve_off(self, num):
        """분배 밸브 OFF"""
        return self._set_relay('main_valve', num, False)
    
    # ===== 배수 밸브 제어 =====
    
    def drain_on(self, num):
        """배수 밸브 ON"""
        return self._set_relay('drain', num, True)
    
    def drain_off(self, num):
        """배수 밸브 OFF"""
        return self._set_relay('drain', num, False)
    
    # ===== 전체 제어 =====
    
    def all_off(self):
        """모든 릴레이 OFF"""
        print("\n🔴 모든 릴레이 OFF")
        for gpio in self.gpio_expanders.values():
            gpio.all_off()
    
    def emergency_stop(self):
        """긴급 정지"""
        print("\n🚨 긴급 정지!")
        self.all_off()
    
    def get_status(self, category, num):
        """
        릴레이 상태 확인
        
        Returns:
            bool: 릴레이 상태 (True=ON, False=OFF)
        """
        if category not in self.RELAY_MAP:
            return None
        if num not in self.RELAY_MAP[category]:
            return None
        
        addr, pin = self.RELAY_MAP[category][num]
        return self.gpio_expanders[addr].get_pin(pin)
    
    # ===== 시나리오 메서드 =====
    
    def irrigate_zone(self, zone_num, duration=10):
        """
        구역 관수 (펌프 + 분배밸브 + 관수밸브)
        
        Args:
            zone_num: 구역 번호 (1-12)
            duration: 관수 시간 (초)
        """
        print(f"\n💧 구역 {zone_num} 관수 시작 (지속시간: {duration}초)")
        
        try:
            # 1. 펌프 ON (예: 펌프 1 사용)
            self.pump_on(1)
            time.sleep(0.5)
            
            # 2. 분배 밸브 ON (예: 분배밸브 1 사용)
            self.main_valve_on(1)
            time.sleep(0.5)
            
            # 3. 관수 밸브 ON
            self.valve_on(zone_num)
            
            # 4. 대기
            print(f"   ⏱️  {duration}초 동안 관수 중...")
            time.sleep(duration)
            
            # 5. 역순으로 OFF
            self.valve_off(zone_num)
            time.sleep(0.5)
            
            self.main_valve_off(1)
            time.sleep(0.5)
            
            self.pump_off(1)
            
            print(f"✅ 구역 {zone_num} 관수 완료")
            
        except KeyboardInterrupt:
            print("\n⚠️  사용자 중단")
            self.all_off()
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            self.all_off()
    
    def winter_drain_mode(self):
        """겨울철 동파 방지 배수"""
        print("\n❄️  겨울철 배수 모드 시작")
        
        try:
            # 모든 배수 밸브 ON
            for i in range(1, 5):
                self.drain_on(i)
                time.sleep(0.5)
            
            print("   ⏱️  60초 동안 배수 중...")
            time.sleep(60)
            
            # 모든 배수 밸브 OFF
            for i in range(1, 5):
                self.drain_off(i)
            
            print("✅ 배수 완료")
            
        except Exception as e:
            print(f"❌ 배수 실패: {e}")
            self.all_off()
    
    def cleanup(self):
        """정리"""
        print("\n🔧 RelayController 정리 중...")
        self.all_off()
        for gpio in self.gpio_expanders.values():
            gpio.cleanup()
        print("✅ 정리 완료")


# 테스트 코드
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🧪 RelayController 테스트")
    print("="*50)
    
    try:
        # 릴레이 컨트롤러 초기화
        relay = RelayController()
        
        # 테스트 1: 개별 릴레이 제어
        print("\n[테스트 1] 개별 릴레이 제어")
        relay.valve_on(1)
        time.sleep(1)
        relay.valve_off(1)
        
        # 테스트 2: 펌프 제어
        print("\n[테스트 2] 펌프 제어")
        relay.pump_on(1)
        time.sleep(1)
        relay.pump_off(1)
        
        # 테스트 3: 구역 관수 (5초)
        print("\n[테스트 3] 구역 1 관수 (5초)")
        relay.irrigate_zone(1, duration=5)
        
        # 정리
        relay.cleanup()
        
        print("\n" + "="*50)
        print("✅ 모든 테스트 완료!")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n⚠️  사용자 중단")
        relay.all_off()
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
