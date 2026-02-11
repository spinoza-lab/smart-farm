#!/usr/bin/env python3
"""
config_manager.py
설정 관리 클래스 - 스케줄 및 구역 설정 저장/로드
"""

import json
import os
from datetime import datetime
from pathlib import Path


class ConfigManager:
    """설정 파일 관리"""
    
    def __init__(self, config_dir="config"):
        """
        초기화
        
        Args:
            config_dir: 설정 파일 디렉토리
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 설정 파일 경로
        self.schedule_file = self.config_dir / "schedules.json"
        self.zone_file = self.config_dir / "zones.json"
        self.settings_file = self.config_dir / "settings.json"
        
        print(f"✓ ConfigManager 초기화 (디렉토리: {self.config_dir})")
        
        # 기본 설정 파일이 없으면 생성
        self._init_default_configs()
    
    def _init_default_configs(self):
        """기본 설정 파일 생성"""
        
        # 기본 구역 설정
        if not self.zone_file.exists():
            default_zones = {
                "zones": [
                    {
                        "id": 1,
                        "name": "구역 1",
                        "valve": 1,
                        "pump": 1,
                        "main_valve": 1,
                        "sensor_channel": 0,
                        "enabled": True
                    }
                ]
            }
            self.save_zones(default_zones)
            print(f"✓ 기본 구역 설정 생성: {self.zone_file}")
        
        # 기본 스케줄
        if not self.schedule_file.exists():
            default_schedules = {
                "schedules": []
            }
            self.save_schedules(default_schedules)
            print(f"✓ 기본 스케줄 생성: {self.schedule_file}")
        
        # 기본 시스템 설정
        if not self.settings_file.exists():
            default_settings = {
                "system": {
                    "default_duration": 600,  # 10분 (초)
                    "safety_timeout": 1800,   # 30분 (초)
                    "min_water_level": 20,    # 최소 수위 (%)
                    "enable_sensor_check": True,
                    "log_level": "INFO"
                },
                "hardware": {
                    "mcp23017_addresses": [0x20, 0x21],
                    "ads1115_address": 0x48,
                    "rtc_address": 0x68
                }
            }
            self.save_settings(default_settings)
            print(f"✓ 기본 시스템 설정 생성: {self.settings_file}")
    
    # ===== 스케줄 관리 =====
    
    def load_schedules(self):
        """
        스케줄 로드
        
        Returns:
            dict: 스케줄 데이터
        """
        try:
            with open(self.schedule_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 스케줄 로드 실패: {e}")
            return {"schedules": []}
    
    def save_schedules(self, schedules_data):
        """
        스케줄 저장
        
        Args:
            schedules_data: 스케줄 데이터
        """
        try:
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(schedules_data, f, indent=2, ensure_ascii=False)
            print(f"✓ 스케줄 저장 완료: {len(schedules_data.get('schedules', []))}개")
            return True
        except Exception as e:
            print(f"❌ 스케줄 저장 실패: {e}")
            return False
    
    def add_schedule(self, zone_id, start_time, duration, days=None, enabled=True):
        """
        스케줄 추가
        
        Args:
            zone_id: 구역 ID
            start_time: 시작 시간 ("HH:MM" 형식)
            duration: 지속 시간 (초)
            days: 요일 리스트 [0-6] (0=월요일, 6=일요일), None이면 매일
            enabled: 활성화 여부
        
        Returns:
            int: 스케줄 ID
        """
        schedules = self.load_schedules()
        
        # 새 스케줄 ID 생성
        schedule_id = max([s.get('id', 0) for s in schedules['schedules']], default=0) + 1
        
        new_schedule = {
            "id": schedule_id,
            "zone_id": zone_id,
            "start_time": start_time,
            "duration": duration,
            "days": days if days is not None else [0, 1, 2, 3, 4, 5, 6],  # 매일
            "enabled": enabled,
            "created_at": datetime.now().isoformat()
        }
        
        schedules['schedules'].append(new_schedule)
        self.save_schedules(schedules)
        
        print(f"✓ 스케줄 추가: ID={schedule_id}, 구역={zone_id}, 시간={start_time}")
        return schedule_id
    
    def remove_schedule(self, schedule_id):
        """
        스케줄 삭제
        
        Args:
            schedule_id: 스케줄 ID
        """
        schedules = self.load_schedules()
        schedules['schedules'] = [s for s in schedules['schedules'] if s['id'] != schedule_id]
        self.save_schedules(schedules)
        print(f"✓ 스케줄 삭제: ID={schedule_id}")
    
    def get_schedule(self, schedule_id):
        """
        특정 스케줄 조회
        
        Args:
            schedule_id: 스케줄 ID
            
        Returns:
            dict: 스케줄 데이터 또는 None
        """
        schedules = self.load_schedules()
        for schedule in schedules['schedules']:
            if schedule['id'] == schedule_id:
                return schedule
        return None
    
    def get_active_schedules(self):
        """
        활성화된 스케줄 목록
        
        Returns:
            list: 활성화된 스케줄 리스트
        """
        schedules = self.load_schedules()
        return [s for s in schedules['schedules'] if s.get('enabled', True)]
    
    # ===== 구역 관리 =====
    
    def load_zones(self):
        """
        구역 설정 로드
        
        Returns:
            dict: 구역 데이터
        """
        try:
            with open(self.zone_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 구역 로드 실패: {e}")
            return {"zones": []}
    
    def save_zones(self, zones_data):
        """
        구역 설정 저장
        
        Args:
            zones_data: 구역 데이터
        """
        try:
            with open(self.zone_file, 'w', encoding='utf-8') as f:
                json.dump(zones_data, f, indent=2, ensure_ascii=False)
            print(f"✓ 구역 저장 완료: {len(zones_data.get('zones', []))}개")
            return True
        except Exception as e:
            print(f"❌ 구역 저장 실패: {e}")
            return False
    
    def get_zone(self, zone_id):
        """
        특정 구역 정보 조회
        
        Args:
            zone_id: 구역 ID
            
        Returns:
            dict: 구역 데이터 또는 None
        """
        zones = self.load_zones()
        for zone in zones['zones']:
            if zone['id'] == zone_id:
                return zone
        return None
    
    def get_all_zones(self):
        """
        모든 구역 조회
        
        Returns:
            list: 구역 리스트
        """
        zones = self.load_zones()
        return zones.get('zones', [])
    
    def add_zone(self, name, valve, pump, main_valve, sensor_channel=None, enabled=True):
        """
        구역 추가
        
        Args:
            name: 구역 이름
            valve: 관수 밸브 번호
            pump: 펌프 번호
            main_valve: 분배 밸브 번호
            sensor_channel: 센서 채널 (선택)
            enabled: 활성화 여부
        
        Returns:
            int: 구역 ID
        """
        zones = self.load_zones()
        
        # 새 구역 ID 생성
        zone_id = max([z.get('id', 0) for z in zones['zones']], default=0) + 1
        
        new_zone = {
            "id": zone_id,
            "name": name,
            "valve": valve,
            "pump": pump,
            "main_valve": main_valve,
            "sensor_channel": sensor_channel,
            "enabled": enabled
        }
        
        zones['zones'].append(new_zone)
        self.save_zones(zones)
        
        print(f"✓ 구역 추가: ID={zone_id}, 이름={name}")
        return zone_id
    
    # ===== 시스템 설정 =====
    
    def load_settings(self):
        """
        시스템 설정 로드
        
        Returns:
            dict: 설정 데이터
        """
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            return {}
    
    def save_settings(self, settings_data):
        """
        시스템 설정 저장
        
        Args:
            settings_data: 설정 데이터
        """
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
            print(f"✓ 설정 저장 완료")
            return True
        except Exception as e:
            print(f"❌ 설정 저장 실패: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """
        특정 설정값 조회
        
        Args:
            key: 설정 키 (예: "system.default_duration")
            default: 기본값
            
        Returns:
            설정값
        """
        settings = self.load_settings()
        keys = key.split('.')
        
        value = settings
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    # ===== 백업 및 복원 =====
    
    def backup_all(self, backup_dir="backups"):
        """
        모든 설정 백업
        
        Args:
            backup_dir: 백업 디렉토리
        """
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"config_backup_{timestamp}.json"
        
        backup_data = {
            "timestamp": timestamp,
            "schedules": self.load_schedules(),
            "zones": self.load_zones(),
            "settings": self.load_settings()
        }
        
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            print(f"✓ 백업 완료: {backup_file}")
            return str(backup_file)
        except Exception as e:
            print(f"❌ 백업 실패: {e}")
            return None


# 테스트 코드
if __name__ == "__main__":
    print("="*60)
    print("🧪 ConfigManager 테스트")
    print("="*60)
    
    try:
        # ConfigManager 초기화
        config = ConfigManager()
        
        # 테스트 1: 구역 추가
        print("\n[테스트 1] 구역 추가")
        zone_id = config.add_zone(
            name="토마토 구역",
            valve=1,
            pump=1,
            main_valve=1,
            sensor_channel=0
        )
        
        # 테스트 2: 스케줄 추가
        print("\n[테스트 2] 스케줄 추가")
        schedule_id = config.add_schedule(
            zone_id=zone_id,
            start_time="06:00",
            duration=600,  # 10분
            days=[1, 3, 5]  # 월/수/금
        )
        
        # 테스트 3: 데이터 조회
        print("\n[테스트 3] 데이터 조회")
        zone = config.get_zone(zone_id)
        print(f"   구역: {zone}")
        
        schedule = config.get_schedule(schedule_id)
        print(f"   스케줄: {schedule}")
        
        # 테스트 4: 설정 조회
        print("\n[테스트 4] 설정 조회")
        default_duration = config.get_setting("system.default_duration")
        print(f"   기본 관수 시간: {default_duration}초")
        
        # 테스트 5: 백업
        print("\n[테스트 5] 백업")
        backup_file = config.backup_all()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
