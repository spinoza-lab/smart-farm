#!/usr/bin/env python3
"""
scheduler.py
자동 관수 스케줄러
- 시간 기반 자동 관수
- 요일별 스케줄
- 백그라운드 실행
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from zone_manager import ZoneManager
from config_manager import ConfigManager
from hardware.rtc_manager import RTCManager


class IrrigationScheduler:
    """자동 관수 스케줄러"""
    
    def __init__(self):
        """초기화"""
        print("\n" + "="*60)
        print("⏰ IrrigationScheduler 초기화")
        print("="*60)
        
        self.config_manager = ConfigManager()
        self.zone_manager = ZoneManager()
        self.rtc = RTCManager()
        
        self.running = False
        self.scheduler_thread = None
        
        # 스케줄 체크 간격 (초)
        self.check_interval = 30  # 30초마다 체크
        
        # 실행된 스케줄 추적 (중복 실행 방지)
        self.executed_schedules = {}
        
        print("✅ IrrigationScheduler 초기화 완료\n")
    
    def start(self, blocking=False):
        """
        스케줄러 시작
        
        Args:
            blocking: True면 메인 스레드에서 실행 (Ctrl+C로 종료)
                     False면 백그라운드 스레드로 실행
        """
        if self.running:
            print("⚠️  스케줄러가 이미 실행 중입니다.")
            return
        
        self.running = True
        
        if blocking:
            print("\n" + "="*60)
            print("🚀 스케줄러 시작 (Ctrl+C로 종료)")
            print("="*60)
            try:
                self._run_scheduler()
            except KeyboardInterrupt:
                print("\n\n⏹️  사용자가 스케줄러를 중지했습니다.")
                self.stop()
        else:
            self.scheduler_thread = threading.Thread(
                target=self._run_scheduler,
                daemon=True
            )
            self.scheduler_thread.start()
            print("✅ 스케줄러가 백그라운드에서 시작되었습니다.")
    
    def stop(self):
        """스케줄러 중지"""
        print("\n⏹️  스케줄러 중지 중...")
        self.running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        print("✅ 스케줄러가 중지되었습니다.\n")
    
    def _run_scheduler(self):
        """스케줄러 메인 루프"""
        print(f"⏰ 스케줄 체크 간격: {self.check_interval}초\n")
        
        while self.running:
            try:
                self._check_and_execute_schedules()
                
                # 다음 체크까지 대기
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ 스케줄러 오류: {e}")
                logging.error(f"Scheduler error: {e}")
                time.sleep(60)  # 오류 발생 시 1분 대기
    
    def _check_and_execute_schedules(self):
        """스케줄 체크 및 실행"""
        now_struct = self.rtc.get_datetime()
        now = datetime(
            now_struct.tm_year,
            now_struct.tm_mon,
            now_struct.tm_mday,
            now_struct.tm_hour,
            now_struct.tm_min,
            now_struct.tm_sec
        )
        current_time = now.strftime("%H:%M")
        current_day = now.weekday() + 1
        current_date = now.strftime("%Y-%m-%d")
        
        # 모든 활성 스케줄 가져오기
        schedules = self.config_manager.get_active_schedules()
        
        for schedule in schedules:
            if not schedule.get('enabled', True):
                continue
            
            schedule_id = schedule['id']
            zone_id = schedule['zone_id']
            start_time = schedule['start_time']
            duration = schedule['duration']
            days = schedule.get('days', [])  # 빈 리스트 = 매일
            
            # 스케줄 실행 조건 체크
            should_run = False
            
            # 1) 시간 체크
            if start_time == current_time:
                # 2) 요일 체크
                if not days or current_day in days:
                    # 3) 오늘 이미 실행했는지 체크
                    last_run = self.executed_schedules.get(schedule_id)
                    if last_run != current_date:
                        should_run = True
            
            # 스케줄 실행
            if should_run:
                self._execute_schedule(schedule, current_date)
    
    def _execute_schedule(self, schedule: Dict, current_date: str):
        """스케줄 실행"""
        schedule_id = schedule['id']
        zone_id = schedule['zone_id']
        duration = schedule['duration']
        
        zone_info = self.zone_manager.get_zone_info(zone_id)
        zone_name = zone_info.get('name', f'구역 {zone_id}')
        
        print("\n" + "="*60)
        print(f"📅 스케줄 실행")
        print("="*60)
        print(f"스케줄 ID: {schedule_id}")
        print(f"구역: {zone_name} (ID: {zone_id})")
        print(f"시간: {schedule['start_time']}")
        print(f"지속시간: {duration}초 ({duration//60}분 {duration%60}초)")
        print("="*60)
        
        try:
            # 관수 실행
            success = self.zone_manager.irrigate(
                zone_id=zone_id,
                duration=duration
            )
            
            if success:
                # 실행 기록
                self.executed_schedules[schedule_id] = current_date
                print(f"✅ 스케줄 실행 완료: {zone_name}")
            else:
                print(f"⚠️  스케줄 실행 실패: {zone_name}")
                
        except Exception as e:
            print(f"❌ 스케줄 실행 오류: {e}")
            logging.error(f"Schedule execution error: {e}")
        
        print("="*60 + "\n")
    
    def add_schedule(self, zone_id: int, start_time: str, duration: int, 
                    days: Optional[List[int]] = None) -> int:
        """
        스케줄 추가
        
        Args:
            zone_id: 구역 ID
            start_time: 시작 시간 (HH:MM)
            duration: 지속시간 (초)
            days: 요일 리스트 (1=월, 7=일), None=매일
        
        Returns:
            생성된 스케줄 ID
        """
        schedule_id = self.config_manager.add_schedule(
            zone_id=zone_id,
            start_time=start_time,
            duration=duration,
            days=days or []
        )
        
        zone_info = self.zone_manager.get_zone_info(zone_id)
        zone_name = zone_info.get('name', f'구역 {zone_id}')
        
        days_str = "매일" if not days else f"요일: {days}"
        
        print(f"\n✅ 스케줄 추가 완료")
        print(f"   스케줄 ID: {schedule_id}")
        print(f"   구역: {zone_name} (ID: {zone_id})")
        print(f"   시간: {start_time}")
        print(f"   지속시간: {duration}초")
        print(f"   {days_str}\n")
        
        return schedule_id
    
    def remove_schedule(self, schedule_id: int) -> bool:
        """스케줄 삭제"""
        success = self.config_manager.remove_schedule(schedule_id)
        
        if success:
            print(f"✅ 스케줄 {schedule_id} 삭제 완료")
            
            # 실행 기록도 삭제
            if schedule_id in self.executed_schedules:
                del self.executed_schedules[schedule_id]
        else:
            print(f"⚠️  스케줄 {schedule_id}를 찾을 수 없습니다.")
        
        return success

    def enable_schedule(self, schedule_id: int, enabled: bool = True) -> bool:
        """스케줄 활성화/비활성화"""
        # ConfigManager에 update_schedule이 없으므로
        # 직접 스케줄을 가져와서 수정 후 저장
        schedule = self.config_manager.get_schedule(schedule_id)
        if not schedule:
            print(f"⚠️  스케줄 {schedule_id}를 찾을 수 없습니다.")
            return False
        
        schedule['enabled'] = enabled
        
        # 모든 스케줄 가져오기
        all_schedules = self.config_manager.get_active_schedules()
        
        # 해당 스케줄 업데이트
        for i, s in enumerate(all_schedules):
            if s['id'] == schedule_id:
                all_schedules[i] = schedule
                break
        
        # 저장
        self.config_manager.save_schedules({'schedules': all_schedules})
        success = True

        if success:
            status = "활성화" if enabled else "비활성화"
            print(f"✅ 스케줄 {schedule_id} {status} 완료")
        else:
            print(f"⚠️  스케줄 {schedule_id}를 찾을 수 없습니다.")
        
        return success
    
    def get_active_schedules(self) -> List[Dict]:
        """모든 스케줄 조회"""
        return self.config_manager.get_active_schedules()
    
    def get_next_schedule(self) -> Optional[Dict]:
        """다음 실행될 스케줄 조회"""
        now_struct = self.rtc.get_datetime()
        now = datetime(
            now_struct.tm_year,
            now_struct.tm_mon,
            now_struct.tm_mday,
            now_struct.tm_hour,
            now_struct.tm_min,
            now_struct.tm_sec
        )
        current_time = now.time()
        current_day = now.weekday() + 1
        
        schedules = self.get_active_schedules()
        
        # 활성화된 스케줄만 필터링
        active_schedules = [s for s in schedules if s.get('enabled', True)]
        
        if not active_schedules:
            return None
        
        # 오늘 실행될 스케줄 찾기
        today_schedules = []
        for schedule in active_schedules:
            days = schedule.get('days', [])
            if not days or current_day in days:
                schedule_time = datetime.strptime(
                    schedule['start_time'], 
                    "%H:%M"
                ).time()
                
                if schedule_time > current_time:
                    today_schedules.append(schedule)
        
        # 오늘 남은 스케줄이 있으면 가장 빠른 것 반환
        if today_schedules:
            return min(
                today_schedules, 
                key=lambda s: s['start_time']
            )
        
        # 오늘 남은 스케줄이 없으면 내일 이후 첫 스케줄 반환
        return min(active_schedules, key=lambda s: s['start_time'])
    
    def print_schedule_summary(self):
        """스케줄 요약 출력"""
        schedules = self.get_active_schedules()
        
        print("\n" + "="*60)
        print("📋 스케줄 목록")
        print("="*60)
        
        if not schedules:
            print("등록된 스케줄이 없습니다.")
        else:
            for schedule in schedules:
                schedule_id = schedule['id']
                zone_id = schedule['zone_id']
                zone_info = self.zone_manager.get_zone_info(zone_id)
                zone_name = zone_info.get('name', f'구역 {zone_id}')
                
                start_time = schedule['start_time']
                duration = schedule['duration']
                days = schedule.get('days', [])
                enabled = schedule.get('enabled', True)
                
                status = "✅" if enabled else "⏸️"
                days_str = "매일" if not days else f"요일 {days}"
                
                print(f"\n{status} 스케줄 ID: {schedule_id}")
                print(f"   구역: {zone_name} (ID: {zone_id})")
                print(f"   시간: {start_time}")
                print(f"   지속시간: {duration}초 ({duration//60}분 {duration%60}초)")
                print(f"   실행: {days_str}")
        
        print("="*60)
        
        # 다음 실행 스케줄
        next_schedule = self.get_next_schedule()
        if next_schedule:
            zone_id = next_schedule['zone_id']
            zone_info = self.zone_manager.get_zone_info(zone_id)
            zone_name = zone_info.get('name', f'구역 {zone_id}')
            
            print(f"\n⏰ 다음 실행: {next_schedule['start_time']} - {zone_name}")
        
        print()


def test_scheduler():
    """테스트 함수"""
    print("\n" + "="*60)
    print("🧪 IrrigationScheduler 테스트")
    print("="*60)
    
    scheduler = IrrigationScheduler()
    
    # [테스트 1] 스케줄 추가
    print("\n[테스트 1] 스케줄 추가")
    print("-" * 60)
    
    # 아침 관수 (매일 06:00, 10분)
    schedule1 = scheduler.add_schedule(
        zone_id=1,
        start_time="06:00",
        duration=600,
        days=None  # 매일
    )
    
    # 저녁 관수 (월/수/금 18:00, 15분)
    schedule2 = scheduler.add_schedule(
        zone_id=1,
        start_time="18:00",
        duration=900,
        days=[1, 3, 5]  # 월, 수, 금
    )
    
    # 토마토 구역 (화/목/토 07:00, 12분)
    schedule3 = scheduler.add_schedule(
        zone_id=2,
        start_time="07:00",
        duration=720,
        days=[2, 4, 6]  # 화, 목, 토
    )
    
    # [테스트 2] 스케줄 목록
    print("\n[테스트 2] 스케줄 목록")
    print("-" * 60)
    scheduler.print_schedule_summary()
    
    # [테스트 3] 스케줄 비활성화
    print("\n[테스트 3] 스케줄 비활성화")
    print("-" * 60)
    scheduler.enable_schedule(schedule2, enabled=False)
    scheduler.print_schedule_summary()
    
    # [테스트 4] 스케줄 활성화
    print("\n[테스트 4] 스케줄 활성화")
    print("-" * 60)
    scheduler.enable_schedule(schedule2, enabled=True)
    scheduler.print_schedule_summary()
    
    # [테스트 5] 스케줄 삭제
    print("\n[테스트 5] 스케줄 삭제")
    print("-" * 60)
    scheduler.remove_schedule(schedule3)
    scheduler.print_schedule_summary()
    
    # [테스트 6] 스케줄러 시작 (10초 테스트)
    print("\n[테스트 6] 스케줄러 테스트 실행")
    print("-" * 60)
    print("⚠️  주의: 실제 스케줄 시간에만 관수가 실행됩니다.")
    print("         테스트를 위해 현재 시간+1분 스케줄을 추가하세요.")
    print()
    
    current_time_struct = scheduler.rtc.get_datetime()
    current_time = datetime(
        current_time_struct.tm_year,
        current_time_struct.tm_mon,
        current_time_struct.tm_mday,
        current_time_struct.tm_hour,
        current_time_struct.tm_min,
        current_time_struct.tm_sec
    )
    test_time = (current_time + timedelta(minutes=1)).strftime("%H:%M")
    
    print(f"현재 시간: {current_time.strftime('%H:%M:%S')}")
    print(f"테스트 스케줄 시간: {test_time}")
    
    # 테스트 스케줄 추가
    test_schedule = scheduler.add_schedule(
        zone_id=1,
        start_time=test_time,
        duration=5,  # 5초
        days=None
    )
    
    print(f"\n⏰ 1분 후 ({test_time})에 5초 관수가 실행됩니다.")
    print("   Ctrl+C로 중지할 수 있습니다.\n")
    
    try:
        # 블로킹 모드로 실행 (Ctrl+C로 종료)
        scheduler.start(blocking=True)
    except KeyboardInterrupt:
        print("\n테스트 중단")
    
    print("\n" + "="*60)
    print("✅ 모든 테스트 완료!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_scheduler()
