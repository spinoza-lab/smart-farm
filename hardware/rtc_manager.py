#!/usr/bin/env python3
"""
rtc_manager.py
RTC DS1307 실시간 시계 관리 클래스
"""

import board
import busio
import adafruit_ds1307
import time
import datetime


class RTCManager:
    """RTC DS1307 실시간 시계 관리"""
    
    def __init__(self, address=0x68):
        """
        초기화
        
        Args:
            address: I2C 주소 (기본 0x68)
        """
        print(f"🔧 RTCManager 초기화 (주소: 0x{address:02X})")
        
        self.address = address
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.rtc = adafruit_ds1307.DS1307(self.i2c)
        
        print(f"✅ RTCManager 초기화 완료")
        
        # RTC 시간 확인
        self._check_rtc_time()
    
    def _check_rtc_time(self):
        """RTC 시간 확인 및 초기화 필요 시 설정"""
        t = self.rtc.datetime
        
        if t.tm_year < 2020:
            print("⚠️  RTC 시간이 초기화되지 않았습니다")
            print("   → 시스템 시간으로 동기화합니다...")
            self.sync_from_system()
        else:
            print(f"✓ RTC 시간: {self.get_datetime_string()}")
    
    def get_datetime(self):
        """
        RTC 시간 읽기
        
        Returns:
            time.struct_time: RTC 시간
        """
        return self.rtc.datetime
    
    def get_datetime_string(self, format="%Y-%m-%d %H:%M:%S"):
        """
        RTC 시간을 문자열로 반환
        
        Args:
            format: 시간 포맷
            
        Returns:
            str: 시간 문자열
        """
        t = self.rtc.datetime
        dt = datetime.datetime(
            t.tm_year, t.tm_mon, t.tm_mday,
            t.tm_hour, t.tm_min, t.tm_sec
        )
        return dt.strftime(format)
    
    def get_time_string(self):
        """
        시간만 반환 (HH:MM:SS)
        
        Returns:
            str: 시간 문자열
        """
        return self.get_datetime_string("%H:%M:%S")
    
    def get_date_string(self):
        """
        날짜만 반환 (YYYY-MM-DD)
        
        Returns:
            str: 날짜 문자열
        """
        return self.get_datetime_string("%Y-%m-%d")
    
    def set_datetime(self, dt=None):
        """
        RTC 시간 설정
        
        Args:
            dt: datetime.datetime 객체 (None이면 현재 시간)
        """
        if dt is None:
            dt = datetime.datetime.now()
        
        self.rtc.datetime = time.struct_time((
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second,
            dt.weekday(), -1, -1
        ))
        
        print(f"✓ RTC 시간 설정: {self.get_datetime_string()}")
    
    def sync_from_system(self):
        """시스템 시간으로 RTC 동기화"""
        now = datetime.datetime.now()
        self.set_datetime(now)
        print(f"✓ RTC 동기화 완료: {self.get_datetime_string()}")
    
    def sync_to_system(self):
        """RTC 시간을 시스템 시간으로 동기화 (sudo 필요)"""
        print("⚠️  시스템 시간 변경은 sudo 권한이 필요합니다")
        print("   명령어: sudo date -s '{}' ".format(self.get_datetime_string()))
    
    def get_timestamp(self):
        """
        타임스탬프 생성 (로그용)
        
        Returns:
            str: [YYYY-MM-DD HH:MM:SS]
        """
        return f"[{self.get_datetime_string()}]"
    
    def is_time_in_range(self, start_time, end_time):
        """
        현재 시간이 지정된 범위 내인지 확인
        
        Args:
            start_time: 시작 시간 (HH:MM 형식, 예: "06:00")
            end_time: 종료 시간 (HH:MM 형식, 예: "18:00")
            
        Returns:
            bool: 범위 내 여부
        """
        current = self.get_time_string()[:5]  # HH:MM
        return start_time <= current <= end_time
    
    def get_hour(self):
        """현재 시간(시) 반환"""
        return self.rtc.datetime.tm_hour
    
    def get_minute(self):
        """현재 분 반환"""
        return self.rtc.datetime.tm_min
    
    def get_weekday(self):
        """
        요일 반환
        
        Returns:
            int: 요일 (0=월요일, 6=일요일)
        """
        return self.rtc.datetime.tm_wday
    
    def get_weekday_name(self, lang='ko'):
        """
        요일 이름 반환
        
        Args:
            lang: 언어 ('ko' 또는 'en')
            
        Returns:
            str: 요일 이름
        """
        weekday = self.get_weekday()
        
        if lang == 'ko':
            names = ['월', '화', '수', '목', '금', '토', '일']
        else:
            names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        return names[weekday]
    
    def wait_until(self, target_time):
        """
        지정된 시간까지 대기
        
        Args:
            target_time: 목표 시간 (HH:MM 형식)
        """
        print(f"⏰ {target_time}까지 대기 중...")
        
        while True:
            current = self.get_time_string()[:5]
            if current >= target_time:
                break
            time.sleep(10)  # 10초마다 확인
        
        print(f"✓ {target_time} 도달")
    
    def display_clock(self, duration=10):
        """
        실시간 시계 표시
        
        Args:
            duration: 표시 시간 (초)
        """
        print("\n" + "="*50)
        print("🕐 실시간 시계")
        print("="*50)
        
        start = time.time()
        
        try:
            while time.time() - start < duration:
                current = self.get_datetime_string()
                weekday = self.get_weekday_name()
                
                print(f"\r⏰ {current} ({weekday})", end='', flush=True)
                time.sleep(1)
        
        except KeyboardInterrupt:
            pass
        
        print("\n" + "="*50)


# 테스트 코드
if __name__ == "__main__":
    print("="*50)
    print("🧪 RTCManager 테스트")
    print("="*50)
    
    try:
        # RTC 관리자 초기화
        rtc = RTCManager(address=0x68)
        
        # 테스트 1: 현재 시간 읽기
        print("\n[테스트 1] 현재 시간")
        print(f"   전체: {rtc.get_datetime_string()}")
        print(f"   날짜: {rtc.get_date_string()}")
        print(f"   시간: {rtc.get_time_string()}")
        print(f"   요일: {rtc.get_weekday_name()}")
        
        # 테스트 2: 타임스탬프
        print("\n[테스트 2] 타임스탬프")
        print(f"   {rtc.get_timestamp()}")
        
        # 테스트 3: 시간 범위 확인
        print("\n[테스트 3] 시간 범위 확인")
        in_range = rtc.is_time_in_range("06:00", "18:00")
        print(f"   06:00-18:00 범위: {'✅ 범위 내' if in_range else '❌ 범위 외'}")
        
        # 테스트 4: 실시간 시계 (10초)
        print("\n[테스트 4] 실시간 시계 표시 (10초)")
        rtc.display_clock(duration=10)
        
        print("\n" + "="*50)
        print("✅ 모든 테스트 완료!")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
