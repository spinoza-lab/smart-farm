#!/usr/bin/env python3
"""
scenarios.py
관수 시나리오 관리
- 순차 관수 (여러 구역 순서대로)
- 긴급 배수 (동파 방지)
- 전체 테스트
- 일괄 작업
"""

import time
from typing import List, Optional
from datetime import datetime

from zone_manager import ZoneManager
from config_manager import ConfigManager


class IrrigationScenarios:
    """관수 시나리오 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        print("\n" + "="*60)
        print("🎬 IrrigationScenarios 초기화")
        print("="*60)
        
        self.zone_manager = ZoneManager()
        self.config_manager = ConfigManager()
        
        print("✅ IrrigationScenarios 초기화 완료\n")
    
    def sequential_irrigation(self, zone_ids: List[int], 
                            duration_per_zone: Optional[int] = None,
                            interval: int = 5) -> bool:
        """
        순차 관수: 여러 구역을 순서대로 관수
        
        Args:
            zone_ids: 구역 ID 리스트 [1, 2, 3]
            duration_per_zone: 각 구역 관수 시간(초), None이면 기본값 사용
            interval: 구역 간 대기 시간(초)
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("🔄 순차 관수 시작")
        print("="*60)
        print(f"구역 순서: {zone_ids}")
        print(f"구역당 시간: {duration_per_zone or '기본값'}초")
        print(f"구역 간 대기: {interval}초")
        print("="*60 + "\n")
        
        total_zones = len(zone_ids)
        success_count = 0
        
        for idx, zone_id in enumerate(zone_ids, 1):
            zone_info = self.zone_manager.get_zone_info(zone_id)
            zone_name = zone_info.get('name', f'구역 {zone_id}')
            
            # 관수 시간 결정
            if duration_per_zone:
                duration = duration_per_zone
            else:
                # ConfigManager에서 기본 시간 가져오기
                duration = self.config_manager.get_default_duration()
            
            print(f"\n📍 [{idx}/{total_zones}] {zone_name} (ID: {zone_id})")
            print(f"   지속시간: {duration}초 ({duration//60}분 {duration%60}초)")
            print("-" * 60)
            
            # 관수 실행
            success = self.zone_manager.irrigate(
                zone_id=zone_id,
                duration=duration
            )
            
            if success:
                success_count += 1
                print(f"✅ {zone_name} 완료")
            else:
                print(f"⚠️  {zone_name} 실패")
            
            # 다음 구역 전 대기 (마지막 구역 제외)
            if idx < total_zones:
                print(f"\n⏳ {interval}초 대기 중...")
                time.sleep(interval)
        
        print("\n" + "="*60)
        print(f"✅ 순차 관수 완료: {success_count}/{total_zones} 성공")
        print("="*60 + "\n")
        
        return success_count == total_zones
    
    def emergency_drain(self, zones: Optional[List[int]] = None) -> bool:
        """
        긴급 배수: 동파 방지를 위한 전체 배수
        모든 밸브를 짧게 열어서 배관 내부 물 제거
        
        Args:
            zones: 배수할 구역 리스트, None이면 전체 구역
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("🚨 긴급 배수 모드")
        print("="*60)
        print("⚠️  동파 방지를 위한 배관 배수 시작")
        print("="*60 + "\n")
        
        # 대상 구역 결정
        if zones is None:
            all_zones = self.config_manager.get_all_zones()
            zones = [z['id'] for z in all_zones if z.get('enabled', True)]
        
        print(f"대상 구역: {len(zones)}개")
        print(f"구역 ID: {zones}\n")
        
        drain_duration = 3  # 3초씩 짧게 열어서 배수
        success_count = 0
        
        for zone_id in zones:
            zone_info = self.zone_manager.get_zone_info(zone_id)
            zone_name = zone_info.get('name', f'구역 {zone_id}')
            
            print(f"💧 {zone_name} 배수 중... ({drain_duration}초)")
            
            success = self.zone_manager.irrigate(
                zone_id=zone_id,
                duration=drain_duration,
                force=True  # 수위 체크 무시
            )
            
            if success:
                success_count += 1
                print(f"   ✅ {zone_name} 배수 완료")
            else:
                print(f"   ⚠️  {zone_name} 배수 실패")
            
            time.sleep(1)  # 구역 간 1초 대기
        
        print("\n" + "="*60)
        print(f"✅ 긴급 배수 완료: {success_count}/{len(zones)} 성공")
        print("="*60 + "\n")
        
        return success_count == len(zones)
    
    def test_all_zones(self, test_duration: int = 5) -> bool:
        """
        전체 구역 테스트: 모든 구역을 짧게 테스트
        
        Args:
            test_duration: 각 구역 테스트 시간(초)
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("🧪 전체 구역 테스트")
        print("="*60)
        print(f"테스트 시간: 각 구역 {test_duration}초")
        print("="*60 + "\n")
        
        all_zones = self.config_manager.get_all_zones()
        active_zones = [z for z in all_zones if z.get('enabled', True)]
        
        print(f"활성 구역: {len(active_zones)}개\n")
        
        results = {}
        
        for zone in active_zones:
            zone_id = zone['id']
            zone_name = zone.get('name', f'구역 {zone_id}')
            
            print(f"🧪 테스트: {zone_name} (ID: {zone_id})")
            print(f"   {test_duration}초 동작 테스트...")
            
            success = self.zone_manager.irrigate(
                zone_id=zone_id,
                duration=test_duration,
                force=True  # 센서 체크 무시
            )
            
            results[zone_id] = success
            
            if success:
                print(f"   ✅ {zone_name} 정상")
            else:
                print(f"   ❌ {zone_name} 오류")
            
            time.sleep(2)  # 구역 간 2초 대기
        
        # 결과 요약
        success_count = sum(results.values())
        total_count = len(results)
        
        print("\n" + "="*60)
        print("📊 테스트 결과 요약")
        print("="*60)
        
        for zone_id, success in results.items():
            zone_info = self.zone_manager.get_zone_info(zone_id)
            zone_name = zone_info.get('name', f'구역 {zone_id}')
            status = "✅ 정상" if success else "❌ 오류"
            print(f"구역 {zone_id} ({zone_name}): {status}")
        
        print("="*60)
        print(f"성공률: {success_count}/{total_count} ({success_count/total_count*100:.0f}%)")
        print("="*60 + "\n")
        
        return success_count == total_count
    
    def morning_routine(self) -> bool:
        """
        아침 루틴: 설정된 모든 구역을 순차 관수
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("🌅 아침 관수 루틴")
        print("="*60)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"시작 시간: {current_time}\n")
        
        # 모든 활성 구역 가져오기
        all_zones = self.config_manager.get_all_zones()
        active_zones = [z['id'] for z in all_zones if z.get('enabled', True)]
        
        if not active_zones:
            print("⚠️  활성화된 구역이 없습니다.")
            return False
        
        # 순차 관수 실행
        return self.sequential_irrigation(
            zone_ids=active_zones,
            duration_per_zone=None,  # 기본값 사용
            interval=5
        )
    
    def evening_routine(self) -> bool:
        """
        저녁 루틴: 아침보다 짧은 시간으로 관수
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("🌆 저녁 관수 루틴")
        print("="*60)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"시작 시간: {current_time}\n")
        
        # 모든 활성 구역 가져오기
        all_zones = self.config_manager.get_all_zones()
        active_zones = [z['id'] for z in all_zones if z.get('enabled', True)]
        
        if not active_zones:
            print("⚠️  활성화된 구역이 없습니다.")
            return False
        
        # 기본 시간의 70%로 관수
        default_duration = self.config_manager.get_default_duration()
        evening_duration = int(default_duration * 0.7)
        
        # 순차 관수 실행
        return self.sequential_irrigation(
            zone_ids=active_zones,
            duration_per_zone=evening_duration,
            interval=3
        )
    
    def custom_scenario(self, zone_durations: dict, interval: int = 5) -> bool:
        """
        커스텀 시나리오: 구역별로 다른 시간 설정
        
        Args:
            zone_durations: {zone_id: duration} 딕셔너리
                           예: {1: 600, 2: 300, 3: 450}
            interval: 구역 간 대기 시간(초)
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("⚙️  커스텀 관수 시나리오")
        print("="*60)
        
        total_zones = len(zone_durations)
        success_count = 0
        
        for idx, (zone_id, duration) in enumerate(zone_durations.items(), 1):
            zone_info = self.zone_manager.get_zone_info(zone_id)
            zone_name = zone_info.get('name', f'구역 {zone_id}')
            
            print(f"\n📍 [{idx}/{total_zones}] {zone_name}")
            print(f"   지속시간: {duration}초 ({duration//60}분 {duration%60}초)")
            
            success = self.zone_manager.irrigate(
                zone_id=zone_id,
                duration=duration
            )
            
            if success:
                success_count += 1
                print(f"   ✅ 완료")
            else:
                print(f"   ⚠️  실패")
            
            # 다음 구역 전 대기
            if idx < total_zones:
                print(f"\n⏳ {interval}초 대기...")
                time.sleep(interval)
        
        print("\n" + "="*60)
        print(f"✅ 커스텀 시나리오 완료: {success_count}/{total_zones} 성공")
        print("="*60 + "\n")
        
        return success_count == total_zones


def test_scenarios():
    """테스트 함수"""
    print("\n" + "="*60)
    print("🧪 IrrigationScenarios 테스트")
    print("="*60)
    
    scenarios = IrrigationScenarios()
    
    # [테스트 1] 순차 관수
    print("\n[테스트 1] 순차 관수")
    print("-" * 60)
    scenarios.sequential_irrigation(
        zone_ids=[1, 2],
        duration_per_zone=5,
        interval=3
    )
    
    # [테스트 2] 전체 구역 테스트
    print("\n[테스트 2] 전체 구역 테스트")
    print("-" * 60)
    scenarios.test_all_zones(test_duration=3)
    
    # [테스트 3] 커스텀 시나리오
    print("\n[테스트 3] 커스텀 시나리오")
    print("-" * 60)
    scenarios.custom_scenario(
        zone_durations={1: 5, 2: 3},
        interval=2
    )
    
    # [테스트 4] 긴급 배수
    print("\n[테스트 4] 긴급 배수")
    print("-" * 60)
    print("⚠️  주의: 실제 배수가 실행됩니다!")
    user_input = input("계속하시겠습니까? (y/N): ")
    
    if user_input.lower() == 'y':
        scenarios.emergency_drain()
    else:
        print("⏸️  테스트 4 스킵\n")
    
    print("\n" + "="*60)
    print("✅ 모든 테스트 완료!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_scenarios()
