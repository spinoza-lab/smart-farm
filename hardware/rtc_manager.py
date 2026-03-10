#!/usr/bin/env python3
"""
rtc_manager.py
RTC DS1307 실시간 시계 관리 클래스

v3.6 수정: 커널이 /dev/rtc0으로 DS1307을 점유하므로
adafruit_ds1307 직접 접근 제거 → datetime.now() 사용
부팅 시 커널이 RTC→시스템 시간 자동 동기화하므로 동일하게 정확함
"""

import time
import datetime

class RTCManager:
    """RTC DS1307 실시간 시계 관리 (시스템 시간 기반)"""

    def __init__(self, address=0x68):
        print(f"🔧 RTCManager 초기화 (시스템 시간 모드)")
        self.address = address
        self._check_rtc_time()
        print(f"✅ RTCManager 초기화 완료")

    def _check_rtc_time(self):
        """시스템 시간 확인"""
        now = datetime.datetime.now()
        if now.year < 2020:
            print("⚠️  시스템 시간이 올바르지 않습니다. NTP 또는 RTC 확인 필요")
        else:
            print(f"✓ RTC 시간: {self.get_datetime_string()}")

    def get_datetime(self):
        """
        현재 시간 읽기

        Returns:
            time.struct_time: 현재 시간
        """
        return datetime.datetime.now().timetuple()

    def get_datetime_string(self, format="%Y-%m-%d %H:%M:%S"):
        """
        현재 시간을 문자열로 반환

        Args:
            format: 시간 포맷

        Returns:
            str: 시간 문자열
        """
        return datetime.datetime.now().strftime(format)

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
        return datetime.datetime.now().hour

    def get_minute(self):
        """현재 분 반환"""
        return datetime.datetime.now().minute

    def get_weekday(self):
        """
        요일 반환

        Returns:
            int: 요일 (0=월요일, 6=일요일)
        """
        return datetime.datetime.now().weekday()

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

