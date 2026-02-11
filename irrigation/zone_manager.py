#!/usr/bin/env python3
"""
zone_manager.py
구역 관리 클래스 - 구역별 관수 제어 및 이력 관리
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.relay_controller import RelayController
from hardware.sensor_reader import SensorReader
from hardware.rtc_manager import RTCManager
from irrigation.config_manager import ConfigManager
from datetime import datetime
import time


class ZoneManager:
    """구역별 관수 관리"""
    
    def __init__(self, config_manager=None):
        """
        초기화
        
        Args:
            config_manager: ConfigManager 인스턴스 (None이면 새로 생성)
        """
        print("="*60)
        print("🌱 ZoneManager 초기화")
        print("="*60)
        
        # 설정 관리자
        self.config = config_manager if config_manager else ConfigManager()
        
        # 하드웨어 초기화
        print("\n하드웨어 초기화 중...")
        self.relay = RelayController()
        self.sensor = SensorReader()
        self.rtc = RTCManager()
        
        # 관수 이력
        self.history = []
        
        print("\n✅ ZoneManager 초기화 완료")
        print("="*60)
    
    def get_zone_info(self, zone_id):
        """
        구역 정보 조회
        
        Args:
            zone_id: 구역 ID
            
        Returns:
            dict: 구역 정보 또는 None
        """
        return self.config.get_zone(zone_id)
    
    def get_all_zones(self):
        """
        모든 구역 조회
        
        Returns:
            list: 구역 리스트
        """
        return self.config.get_all_zones()
    
    def check_water_level(self, tank=1):
        """
        물탱크 수위 확인
        
        Args:
            tank: 탱크 번호
            
        Returns:
            float: 수위 (%)
        """
        level = self.sensor.read_water_level(tank)
        
        if level is None:
            print(f"⚠️  탱크 {tank} 수위 읽기 실패")
            return 0
        
        return level
    
    def can_irrigate(self, zone_id):
        """
        관수 가능 여부 확인
        
        Args:
            zone_id: 구역 ID
            
        Returns:
            tuple: (가능 여부, 사유)
        """
        zone = self.get_zone_info(zone_id)
        
        if not zone:
            return False, f"구역 {zone_id}을 찾을 수 없습니다"
        
        if not zone.get('enabled', True):
            return False, f"구역 {zone_id}이 비활성화되어 있습니다"
        
        # 수위 확인 (설정에서 체크 활성화된 경우)
        if self.config.get_setting("system.enable_sensor_check", True):
            min_level = self.config.get_setting("system.min_water_level", 20)
            water_level = self.check_water_level(1)
            
            if water_level < min_level:
                return False, f"수위 부족 ({water_level:.1f}% < {min_level}%)"
        
        return True, "OK"
    
    def irrigate(self, zone_id, duration=None, force=False):
        """
        구역 관수 실행
        
        Args:
            zone_id: 구역 ID
            duration: 관수 시간 (초), None이면 설정값 사용
            force: 안전 체크 무시 여부
            
        Returns:
            bool: 성공 여부
        """
        # 구역 정보 조회
        zone = self.get_zone_info(zone_id)
        if not zone:
            print(f"❌ 구역 {zone_id}을 찾을 수 없습니다")
            return False
        
        # 관수 가능 여부 확인
        if not force:
            can_do, reason = self.can_irrigate(zone_id)
            if not can_do:
                print(f"❌ 관수 불가: {reason}")
                return False
        
        # 관수 시간 설정
        if duration is None:
            duration = self.config.get_setting("system.default_duration", 600)
        
        # 안전 타임아웃
        safety_timeout = self.config.get_setting("system.safety_timeout", 1800)
        if duration > safety_timeout:
            print(f"⚠️  관수 시간이 안전 타임아웃({safety_timeout}초)을 초과합니다")
            duration = safety_timeout
        
        # 관수 시작
        print(f"\n💧 구역 {zone_id} ({zone['name']}) 관수 시작")
        print(f"   밸브: {zone['valve']}, 펌프: {zone['pump']}, 분배밸브: {zone['main_valve']}")
        print(f"   지속시간: {duration}초 ({duration//60}분 {duration%60}초)")
        
        start_time = time.time()
        start_timestamp = self.rtc.get_datetime_string()
        
        try:
            # 1. 펌프 ON
            self.relay.pump_on(zone['pump'])
            time.sleep(0.5)
            
            # 2. 분배 밸브 ON
            self.relay.main_valve_on(zone['main_valve'])
            time.sleep(0.5)
            
            # 3. 관수 밸브 ON
            self.relay.valve_on(zone['valve'])
            
            # 4. 대기
            print(f"   ⏱️  {duration}초 동안 관수 중...")
            
            # 진행 상황 표시 (10초마다)
            elapsed = 0
            while elapsed < duration:
                time.sleep(min(10, duration - elapsed))
                elapsed = time.time() - start_time
                
                if elapsed < duration:
                    remaining = duration - elapsed
                    percent = (elapsed / duration) * 100
                    print(f"   📊 진행: {percent:.1f}% (남은 시간: {int(remaining)}초)")
            
            # 5. 역순으로 OFF
            self.relay.valve_off(zone['valve'])
            time.sleep(0.5)
            
            self.relay.main_valve_off(zone['main_valve'])
            time.sleep(0.5)
            
            self.relay.pump_off(zone['pump'])
            
            end_timestamp = self.rtc.get_datetime_string()
            actual_duration = time.time() - start_time
            
            print(f"✅ 구역 {zone_id} 관수 완료 (실제 시간: {actual_duration:.1f}초)")
            
            # 이력 기록
            self._add_history(
                zone_id=zone_id,
                zone_name=zone['name'],
                start_time=start_timestamp,
                end_time=end_timestamp,
                duration=actual_duration,
                status="success"
            )
            
            return True
            
        except KeyboardInterrupt:
            print("\n⚠️  사용자 중단")
            self.emergency_stop()
            
            self._add_history(
                zone_id=zone_id,
                zone_name=zone['name'],
                start_time=start_timestamp,
                end_time=self.rtc.get_datetime_string(),
                duration=time.time() - start_time,
                status="interrupted"
            )
            
            return False
            
        except Exception as e:
            print(f"\n❌ 관수 실패: {e}")
            self.emergency_stop()
            
            self._add_history(
                zone_id=zone_id,
                zone_name=zone['name'],
                start_time=start_timestamp,
                end_time=self.rtc.get_datetime_string(),
                duration=time.time() - start_time,
                status="error",
                error=str(e)
            )
            
            return False
    
    def _add_history(self, zone_id, zone_name, start_time, end_time, duration, status, error=None):
        """
        관수 이력 추가
        
        Args:
            zone_id: 구역 ID
            zone_name: 구역 이름
            start_time: 시작 시간
            end_time: 종료 시간
            duration: 지속 시간
            status: 상태 (success/interrupted/error)
            error: 오류 메시지 (선택)
        """
        history_entry = {
            "zone_id": zone_id,
            "zone_name": zone_name,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "status": status
        }
        
        if error:
            history_entry["error"] = error
        
        self.history.append(history_entry)
        
        # 최근 100개만 유지
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def get_history(self, zone_id=None, limit=10):
        """
        관수 이력 조회
        
        Args:
            zone_id: 구역 ID (None이면 전체)
            limit: 최대 개수
            
        Returns:
            list: 이력 리스트
        """
        if zone_id:
            filtered = [h for h in self.history if h['zone_id'] == zone_id]
        else:
            filtered = self.history
        
        # 최근 순으로 정렬
        return list(reversed(filtered[-limit:]))
    
    def print_history(self, zone_id=None, limit=10):
        """
        관수 이력 출력
        
        Args:
            zone_id: 구역 ID (None이면 전체)
            limit: 최대 개수
        """
        history = self.get_history(zone_id, limit)
        
        print("\n" + "="*60)
        print(f"📋 관수 이력 (최근 {len(history)}개)")
        print("="*60)
        
        if not history:
            print("   (이력 없음)")
            return
        
        for h in history:
            status_icon = {
                "success": "✅",
                "interrupted": "⚠️",
                "error": "❌"
            }.get(h['status'], "❓")
            
            print(f"\n{status_icon} 구역 {h['zone_id']} ({h['zone_name']})")
            print(f"   시작: {h['start_time']}")
            print(f"   종료: {h['end_time']}")
            print(f"   시간: {h['duration']:.1f}초")
            
            if h.get('error'):
                print(f"   오류: {h['error']}")
        
        print("="*60)
    
    def emergency_stop(self):
        """긴급 정지"""
        print("\n🚨 긴급 정지!")
        self.relay.emergency_stop()
    
    def cleanup(self):
        """정리"""
        print("\n🔧 ZoneManager 정리 중...")
        self.relay.cleanup()
        print("✅ 정리 완료")


# 테스트 코드
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 ZoneManager 테스트")
    print("="*60)
    
    try:
        # ZoneManager 초기화
        zone_mgr = ZoneManager()
        
        # 테스트 1: 구역 정보 조회
        print("\n[테스트 1] 구역 정보")
        zones = zone_mgr.get_all_zones()
        for zone in zones:
            print(f"   구역 {zone['id']}: {zone['name']}")
        
        # 테스트 2: 수위 확인
        print("\n[테스트 2] 수위 확인")
        level = zone_mgr.check_water_level(1)
        print(f"   탱크 1 수위: {level:.1f}%")
        
        # 테스트 3: 관수 가능 여부
        print("\n[테스트 3] 관수 가능 여부")
        can_do, reason = zone_mgr.can_irrigate(1)
        print(f"   구역 1: {can_do} ({reason})")
        
        # 테스트 4: 관수 실행 (5초)
        print("\n[테스트 4] 관수 실행 (5초)")
        zone_mgr.irrigate(zone_id=1, duration=5)
        
        # 테스트 5: 이력 확인
        print("\n[테스트 5] 관수 이력")
        zone_mgr.print_history()
        
        # 정리
        zone_mgr.cleanup()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n⚠️  사용자 중단")
        zone_mgr.emergency_stop()
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
