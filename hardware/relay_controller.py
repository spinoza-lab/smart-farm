#!/usr/bin/env python3
"""
relay_controller.py
릴레이 제어 클래스 (v2.0 - 단순화)

하드웨어 구성:
- 펌프: 1개 (모든 구역 공용)
- Zone: 12개 독립 밸브
- 필수 제어: 양액차단, 물차단, 핸드건, 체크밸브
"""

from hardware.gpio_expander import GPIOExpander
import time


class RelayController:
    """릴레이 모듈 제어 (v2.0)"""
    
    # 릴레이 매핑 (relay_hardware_config.md 기준)
    RELAY_MAP = {
        # === 필수 제어 (보드 #1) ===
        'pump': (0x20, 0),           # PA0: 관수펌프
        'nutrient_block': (0x20, 1), # PA1: 양액탱크 차단
        'water_block': (0x20, 2),    # PA2: 물탱크 차단
        'hand_gun': (0x20, 3),       # PA3: 핸드건
        'check_valve': (0x20, 4),    # PA4: 체크밸브
        'spare_1': (0x20, 5),        # PA5: 예비
        
        # === Zone 1~12 (보드 #2, #3) ===
        'zone_1': (0x20, 6),         # PA6
        'zone_2': (0x20, 7),         # PA7
        'zone_3': (0x20, 8),         # PB0
        'zone_4': (0x20, 9),         # PB1
        'zone_5': (0x20, 10),        # PB2
        'zone_6': (0x20, 11),        # PB3
        'zone_7': (0x20, 12),        # PB4
        'zone_8': (0x20, 13),        # PB5
        'zone_9': (0x20, 14),        # PB6
        'zone_10': (0x20, 15),       # PB7
        'zone_11': (0x21, 0),        # PA0
        'zone_12': (0x21, 1),        # PA1
        
        # === 예비 (보드 #4) ===
        'drain_water': (0x21, 2),    # PA2
        'drain_nutrient': (0x21, 3), # PA3
        'spare_zone_13': (0x21, 4),  # PA4
        'spare_zone_14': (0x21, 5),  # PA5
        'spare_2': (0x21, 6),        # PA6
        'spare_3': (0x21, 7),        # PA7
    }
    
    # Zone 매핑 (1-based)
    ZONE_MAP = {i: f'zone_{i}' for i in range(1, 13)}
    MAX_ZONES = 12
    
    def __init__(self):
        """초기화"""
        print("="*60)
        print("🔧 RelayController v2.0 초기화")
        print("="*60)
        
        # GPIO 확장 보드 초기화
        self.gpio_expanders = {
            0x20: GPIOExpander(address=0x20),
            0x21: GPIOExpander(address=0x21)
        }
        
        # 모든 릴레이 핀 설정
        self._setup_all_relays()
        
        # 평상시 상태로 초기화
        self._set_default_state()
        
        print("\n✅ RelayController v2.0 초기화 완료")
        print("="*60)
    
    def _setup_all_relays(self):
        """모든 릴레이 핀 설정"""
        print("\n릴레이 핀 설정 중...")
        
        for name, (addr, pin) in self.RELAY_MAP.items():
            self.gpio_expanders[addr].setup_pin(pin, initial_value=False)
        
        print(f"✓ {len(self.RELAY_MAP)}개 릴레이 핀 설정 완료")
    
    def _set_default_state(self):
        """평상시 상태로 설정"""
        print("\n평상시 상태 설정 중...")
        
        # 필수 제어 - 평상시 ON
        self._set_relay('nutrient_block', True)  # 양액탱크 자동 충수
        self._set_relay('water_block', True)     # 물탱크 자동 충수
        self._set_relay('check_valve', True)     # 역류 방지
        
        # 나머지는 모두 OFF
        self._set_relay('pump', False)
        self._set_relay('hand_gun', False)
        
        for i in range(1, self.MAX_ZONES + 1):
            self.zone_off(i)
        
        print("✓ 평상시 상태 설정 완료")
        print("  - 양액차단: ON (자동 충수)")
        print("  - 물차단: ON (자동 충수)")
        print("  - 체크밸브: ON (역류 방지)")
        print("  - 펌프: OFF")
        print("  - 핸드건: OFF")
        print("  - 모든 Zone: OFF")
    
    def _set_relay(self, name, state):
        """
        릴레이 제어 (내부 메서드)
        
        Args:
            name: 릴레이 이름 (RELAY_MAP의 키)
            state: True(ON) 또는 False(OFF)
        
        Returns:
            bool: 성공 여부
        """
        if name not in self.RELAY_MAP:
            print(f"❌ 잘못된 릴레이 이름: {name}")
            return False
        
        addr, pin = self.RELAY_MAP[name]
        self.gpio_expanders[addr].set_pin(pin, state)
        
        state_str = "ON" if state else "OFF"
        print(f"{'🟢' if state else '⚫'} {name.upper()} → {state_str}")
        
        return True
    
    # ===== 펌프 제어 =====
    
    def pump_on(self):
        """펌프 ON"""
        return self._set_relay('pump', True)
    
    def pump_off(self):
        """펌프 OFF"""
        return self._set_relay('pump', False)
    
    def get_pump_status(self):
        """펌프 상태 확인"""
        addr, pin = self.RELAY_MAP['pump']
        return self.gpio_expanders[addr].get_pin(pin)
    
    # ===== Zone 제어 (1~12) =====
    
    def zone_on(self, zone_num):
        """
        Zone 밸브 ON
        
        Args:
            zone_num: Zone 번호 (1~12)
        """
        if zone_num < 1 or zone_num > self.MAX_ZONES:
            print(f"❌ 잘못된 Zone 번호: {zone_num} (1~{self.MAX_ZONES}만 가능)")
            return False
        
        zone_name = self.ZONE_MAP[zone_num]
        return self._set_relay(zone_name, True)
    
    def zone_off(self, zone_num):
        """
        Zone 밸브 OFF
        
        Args:
            zone_num: Zone 번호 (1~12)
        """
        if zone_num < 1 or zone_num > self.MAX_ZONES:
            print(f"❌ 잘못된 Zone 번호: {zone_num}")
            return False
        
        zone_name = self.ZONE_MAP[zone_num]
        return self._set_relay(zone_name, False)
    
    def get_zone_status(self, zone_num):
        """
        Zone 상태 확인
        
        Args:
            zone_num: Zone 번호 (1~12)
        
        Returns:
            bool: True(ON), False(OFF), None(오류)
        """
        if zone_num < 1 or zone_num > self.MAX_ZONES:
            return None
        
        zone_name = self.ZONE_MAP[zone_num]
        addr, pin = self.RELAY_MAP[zone_name]
        return self.gpio_expanders[addr].get_pin(pin)
    
    def all_zones_off(self):
        """모든 Zone OFF"""
        print("\n🔴 모든 Zone OFF")
        for i in range(1, self.MAX_ZONES + 1):
            self.zone_off(i)
    
    # ===== 핸드건 제어 =====
    
    def hand_gun_on(self):
        """핸드건 ON (안전장치 포함)"""
        print("\n🚰 핸드건 모드 활성화")
        
        # 1. 안전 조치
        self.pump_off()
        self.all_zones_off()
        time.sleep(0.5)
        
        # 2. 핸드건 열기
        return self._set_relay('hand_gun', True)
    
    def hand_gun_off(self):
        """핸드건 OFF"""
        print("\n🔒 핸드건 모드 종료")
        return self._set_relay('hand_gun', False)
    
    def get_hand_gun_status(self):
        """핸드건 상태 확인"""
        addr, pin = self.RELAY_MAP['hand_gun']
        return self.gpio_expanders[addr].get_pin(pin)
    
    # ===== 탱크 차단 제어 =====
    
    def nutrient_block_on(self):
        """양액탱크 차단밸브 ON (자동 충수)"""
        return self._set_relay('nutrient_block', True)
    
    def nutrient_block_off(self):
        """양액탱크 차단밸브 OFF (차단)"""
        return self._set_relay('nutrient_block', False)
    
    def water_block_on(self):
        """물탱크 차단밸브 ON (자동 충수)"""
        return self._set_relay('water_block', True)
    
    def water_block_off(self):
        """물탱크 차단밸브 OFF (차단)"""
        return self._set_relay('water_block', False)
    
    # ===== 체크밸브 제어 =====
    
    def check_valve_on(self):
        """체크밸브 ON (역류 방지)"""
        return self._set_relay('check_valve', True)
    
    def check_valve_off(self):
        """체크밸브 OFF"""
        return self._set_relay('check_valve', False)
    
    # ===== 전체 제어 =====
    
    def all_off(self):
        """모든 릴레이 OFF (긴급 정지)"""
        print("\n🔴 모든 릴레이 OFF")
        for gpio in self.gpio_expanders.values():
            gpio.all_off()
    
    def emergency_stop(self):
        """긴급 정지"""
        print("\n🚨 긴급 정지!")
        self.all_off()
        time.sleep(0.5)
        # 평상시 상태로 복구
        self._set_default_state()
    
    # ===== 관수 시나리오 =====
    
    def irrigate_zone(self, zone_num, duration=600):
        """
        구역 관수 (펌프 + Zone 밸브)
        
        Args:
            zone_num: Zone 번호 (1~12)
            duration: 관수 시간 (초)
        
        Returns:
            bool: 성공 여부
        """
        if zone_num < 1 or zone_num > self.MAX_ZONES:
            print(f"❌ 잘못된 Zone 번호: {zone_num}")
            return False
        
        print(f"\n💧 Zone {zone_num} 관수 시작 (지속시간: {duration}초)")
        
        try:
            # 1. 사전 조건 확인
            # (수위 체크는 호출자가 담당)
            
            # 2. 펌프 ON
            self.pump_on()
            time.sleep(0.5)
            
            # 3. Zone 밸브 ON
            self.zone_on(zone_num)
            
            # 4. 관수 진행
            print(f"   ⏱️  {duration}초 동안 관수 중...")
            time.sleep(duration)
            
            # 5. 역순으로 OFF
            self.zone_off(zone_num)
            time.sleep(0.5)
            
            self.pump_off()
            
            print(f"✅ Zone {zone_num} 관수 완료")
            return True
            
        except KeyboardInterrupt:
            print("\n⚠️  사용자 중단")
            self.zone_off(zone_num)
            self.pump_off()
            return False
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            self.emergency_stop()
            return False
    
    def get_all_status(self):
        """
        모든 릴레이 상태 조회
        
        Returns:
            dict: 릴레이 상태 딕셔너리
        """
        status = {
            'pump': self.get_pump_status(),
            'hand_gun': self.get_hand_gun_status(),
            'zones': {}
        }
        
        for i in range(1, self.MAX_ZONES + 1):
            status['zones'][i] = self.get_zone_status(i)
        
        return status
    
    def cleanup(self):
        """정리"""
        print("\n🔧 RelayController 정리 중...")
        self.all_off()
        for gpio in self.gpio_expanders.values():
            gpio.cleanup()
        print("✅ 정리 완료")


# 테스트 코드
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 RelayController v2.0 테스트")
    print("="*60)
    
    try:
        # 릴레이 컨트롤러 초기화
        relay = RelayController()
        
        # 테스트 1: 펌프 제어
        print("\n[테스트 1] 펌프 제어")
        print("-" * 60)
        relay.pump_on()
        time.sleep(2)
        relay.pump_off()
        
        # 테스트 2: Zone 제어
        print("\n[테스트 2] Zone 1 제어")
        print("-" * 60)
        relay.zone_on(1)
        time.sleep(2)
        relay.zone_off(1)
        
        # 테스트 3: 핸드건 모드
        print("\n[테스트 3] 핸드건 모드")
        print("-" * 60)
        relay.hand_gun_on()
        time.sleep(2)
        relay.hand_gun_off()
        
        # 테스트 4: 구역 관수 (5초)
        print("\n[테스트 4] Zone 3 관수 (5초)")
        print("-" * 60)
        relay.irrigate_zone(3, duration=5)
        
        # 테스트 5: 전체 상태 조회
        print("\n[테스트 5] 전체 상태 조회")
        print("-" * 60)
        status = relay.get_all_status()
        print(f"펌프: {'ON' if status['pump'] else 'OFF'}")
        print(f"핸드건: {'ON' if status['hand_gun'] else 'OFF'}")
        print(f"Zone 상태:")
        for zone_num, zone_status in status['zones'].items():
            print(f"  Zone {zone_num}: {'ON' if zone_status else 'OFF'}")
        
        # 정리
        relay.cleanup()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n⚠️  사용자 중단")
        relay.emergency_stop()
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
