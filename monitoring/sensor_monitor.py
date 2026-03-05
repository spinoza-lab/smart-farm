#!/usr/bin/env python3
"""
sensor_monitor.py
센서 실시간 모니터링 (v3 - 캐시 기능 추가)
- 주기적 센서 값 읽기 (균등 간격 다중 샘플링)
- 이상치 제거 (상하위 각 2개)
- 수위/임계값 체크
- 이상 감지 및 알림
- ✅ 마지막 측정값 캐시 (get_current_status 최적화)
"""

import time
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, List
import logging

from pathlib import Path

# BUG-7: 설치 경로 동적 계산 (하드코딩 제거)
_BASE_DIR = Path(__file__).resolve().parent.parent

import sys
sys.path.append(str(_BASE_DIR))

from hardware.sensor_reader import SensorReader
from hardware.rtc_manager import RTCManager

class SensorMonitor:
    """센서 실시간 모니터링 클래스"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        초기화
        
        Args:
            config: 모니터링 설정
                - check_interval: 체크 간격(초), 기본 60초
                - sample_count: 샘플 개수, 기본 10개
                - outlier_remove: 상하위 제거 개수, 기본 2개
                - min_water_level: 최소 수위(%), 기본 20%
                - max_water_level: 최대 수위(%), 기본 90%
                - alert_callbacks: 알림 콜백 함수 리스트
        """
        print("\n" + "="*60)
        print("📊 SensorMonitor 초기화")
        print("="*60)
        
        self.sensor_reader = SensorReader()
        self.rtc = RTCManager()
        
        # 기본 설정
        self.config = config or {}
        self.check_interval = self.config.get('check_interval', 60)
        self.sample_count = self.config.get('sample_count', 10)
        self.outlier_remove = self.config.get('outlier_remove', 2)
        self.min_water_level = self.config.get('min_water_level', 20.0)
        self.max_water_level = self.config.get('max_water_level', 90.0)
        
        # 샘플 간격 자동 계산 (균등 분산)
        self.sample_interval = self.check_interval / self.sample_count
        
        # 알림 콜백
        self.alert_callbacks = self.config.get('alert_callbacks', [])
        
        # 모니터링 상태
        self.running = False
        self.monitor_thread = None
        
        # 센서 데이터 히스토리
        self.history = []
        
        # 🔥 샘플링 캐시 (중복 샘플링 방지)
        self._cache = {
            'timestamp': None,
            'data': None,
            'ttl': 5  # 캐시 유효 시간 (초)
        }
        self.max_history = 100  # 최대 100개 저장
        
        # ✅ 마지막 측정값 캐시 추가
        self._last_data = None
        self._last_data_lock = __import__('threading').Lock()
        
        # ✅ 캘리브레이션 로드 (초기화 시)
        import os
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'sensor_calibration.json'
        )
        if os.path.exists(config_path):
            print(f"📖 캘리브레이션 파일 로드: {config_path}")
            self.load_calibration(config_path)
        else:
            print(f"⚠️  캘리브레이션 파일 없음, 기본값 사용")
            self.sensor_type = 'voltage'
            self.tank1_empty = 0.0
            self.tank1_full = 3.3
            self.tank2_empty = 0.0
            self.tank2_full = 3.3
        self._last_data_lock = threading.Lock()
        
        # 마지막 알림 시간 (중복 방지)
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5분 쿨다운
        
        print(f"✅ 체크 간격: {self.check_interval}초")
        print(f"✅ 샘플링: {self.sample_count}회 × {self.sample_interval:.1f}초 간격")
        print(f"✅ 이상치 제거: 상하위 각 {self.outlier_remove}개")
        print(f"✅ 수위 범위: {self.min_water_level}% ~ {self.max_water_level}%")
        print("✅ SensorMonitor 초기화 완료\n")
    
    def start(self, blocking: bool = False):
        """
        모니터링 시작
        
        Args:
            blocking: True면 메인 스레드에서 실행 (Ctrl+C로 종료)
                     False면 백그라운드 스레드로 실행
        """
        if self.running:
            print("⚠️  모니터링이 이미 실행 중입니다.")
            return
        
        self.running = True
        
        if blocking:
            print("\n" + "="*60)
            print("🚀 센서 모니터링 시작 (Ctrl+C로 종료)")
            print("="*60)
            print(f"⏰ 체크 간격: {self.check_interval}초")
            print(f"📊 샘플링: {self.sample_count}회 × {self.sample_interval:.1f}초")
            print(f"🔧 이상치 제거: 상하위 각 {self.outlier_remove}개")
            print(f"📏 수위 임계값: {self.min_water_level}% ~ {self.max_water_level}%")
            print("="*60 + "\n")
            
            try:
                self._monitor_loop()
            except KeyboardInterrupt:
                print("\n\n⏹️  사용자가 모니터링을 중지했습니다.")
                self.stop()
        else:
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self.monitor_thread.start()
            print("✅ 센서 모니터링이 백그라운드에서 시작되었습니다.")
    
    def stop(self):
        """모니터링 중지"""
        print("\n⏹️  센서 모니터링 중지 중...")
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        print("✅ 센서 모니터링이 중지되었습니다.\n")
    
    def _monitor_loop(self):
        """모니터링 메인 루프"""
        while self.running:
            try:
                # 센서 데이터 수집 (다중 샘플링 + 이상치 제거)
                data = self._collect_sensor_data()
                
                # ✅ 캐시에 저장
                with self._last_data_lock:
                    self._last_data = data
                
                # 히스토리에 추가
                self._add_to_history(data)
                
                # 임계값 체크
                self._check_thresholds(data)
                
                # 데이터 출력
                self._print_status(data)
                    
            except Exception as e:
                print(f"❌ 모니터링 오류: {e}")
                logging.error(f"Monitor error: {e}")
                time.sleep(10)  # 오류 발생 시 10초 대기
    
    def _collect_sensor_data(self) -> Dict:
        """
        센서 데이터 수집 (다중 샘플링 + 이상치 제거)
        check_interval 동안 균등하게 샘플링
        """
        # 다중 샘플링
        voltage_samples = []
        
        for i in range(self.sample_count):
            voltages = self.sensor_reader.read_all_channels()
            voltage_samples.append(voltages)
            
            # 마지막 샘플 후에는 대기 안 함
            if i < self.sample_count - 1:
                time.sleep(self.sample_interval)
        
        # 채널별로 이상치 제거 후 평균
        filtered_voltages = []
        
        for ch in range(4):
            ch_values = [s[ch] for s in voltage_samples]
            
            # 정렬
            ch_values.sort()
            
            # 상하위 제거 (샘플이 충분할 때만)
            if len(ch_values) > self.outlier_remove * 2:
                trimmed = ch_values[self.outlier_remove:-self.outlier_remove]
            else:
                trimmed = ch_values
            
            # 평균 계산 (소수점 3자리 반올림)
            avg = sum(trimmed) / len(trimmed)
            filtered_voltages.append(round(avg, 3))
        
        
        # 타임스탬프
        timestamp = self.rtc.get_datetime_string('%Y-%m-%d %H:%M:%S')
        
        # ✅ 필터링된 전압으로 직접 수위 계산 (캘리브레이션 즉시 반영!)
        # CH0 = 탱크1, CH1 = 탱크2
        tank1_voltage = filtered_voltages[0]
        tank2_voltage = filtered_voltages[1]
        
        # 🔥 최신 캘리브레이션 값 읽기
        tank1_empty = self.tank1_empty
        tank1_full = self.tank1_full
        tank2_empty = self.tank2_empty
        tank2_full = self.tank2_full
        
        # 탱크1 수위 계산
        if tank1_voltage <= tank1_empty:
            tank1_level = 0.0
        elif tank1_voltage >= tank1_full:
            tank1_level = 100.0
        else:
            tank1_level = round(((tank1_voltage - tank1_empty) / (tank1_full - tank1_empty)) * 100, 1)
        
        # 탱크2 수위 계산
        if tank2_voltage <= tank2_empty:
            tank2_level = 0.0
        elif tank2_voltage >= tank2_full:
            tank2_level = 100.0
        else:
            tank2_level = round(((tank2_voltage - tank2_empty) / (tank2_full - tank2_empty)) * 100, 1)
        
        data = {
            'timestamp': timestamp,
            'voltages': filtered_voltages,
            'tank1_level': tank1_level,
            'tank2_level': tank2_level,
        }
        
        # ✅ 캐시 업데이트
        with self._last_data_lock:
            self._last_data = data.copy()
        
        return data
    
    def _add_to_history(self, data: Dict):
        """히스토리에 데이터 추가"""
        self.history.append(data)
        
        # 최대 개수 유지
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def _check_thresholds(self, data: Dict):
        """임계값 체크 및 알림"""
        tank1_level = data['tank1_level']
        tank2_level = data['tank2_level']
        
        # 수위 부족 체크
        if tank1_level < self.min_water_level:
            self._trigger_alert(
                alert_type='low_water_level',
                message=f"⚠️  탱크 1 수위 부족: {tank1_level:.1f}% (최소: {self.min_water_level}%)",
                data=data
            )
        
        if tank2_level < self.min_water_level:
            self._trigger_alert(
                alert_type='low_water_level',
                message=f"⚠️  탱크 2 수위 부족: {tank2_level:.1f}% (최소: {self.min_water_level}%)",
                data=data
            )
        
        # 수위 과다 체크 (오버플로우 방지)
        if tank1_level > self.max_water_level:
            self._trigger_alert(
                alert_type='high_water_level',
                message=f"⚠️  탱크 1 수위 과다: {tank1_level:.1f}% (최대: {self.max_water_level}%)",
                data=data
            )
        
        if tank2_level > self.max_water_level:
            self._trigger_alert(
                alert_type='high_water_level',
                message=f"⚠️  탱크 2 수위 과다: {tank2_level:.1f}% (최대: {self.max_water_level}%)",
                data=data
            )
    
    def _trigger_alert(self, alert_type: str, message: str, data: Dict):
        """알림 트리거"""
        # 쿨다운 체크 (중복 알림 방지)
        now = time.time()
        last_time = self.last_alert_time.get(alert_type, 0)
        
        if now - last_time < self.alert_cooldown:
            return  # 쿨다운 중
        
        # 알림 출력
        print(f"\n🔔 {message}")
        
        # 마지막 알림 시간 업데이트
        self.last_alert_time[alert_type] = now
        
        # 콜백 실행
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, message, data)
            except Exception as e:
                print(f"❌ 알림 콜백 오류: {e}")
                logging.error(f"Alert callback error: {e}")
    
    def _print_status(self, data: Dict):
        """센서 상태 출력"""
        timestamp = data['timestamp']
        tank1_level = data['tank1_level']
        tank2_level = data['tank2_level']
        voltages = data['voltages']
        
        print(f"\n📊 [{timestamp}]")
        print(f"   탱크 1: {tank1_level:5.1f}% | 탱크 2: {tank2_level:5.1f}%")
        print(f"   CH0: {voltages[0]:.3f}V | CH1: {voltages[1]:.3f}V | "
              f"CH2: {voltages[2]:.3f}V | CH3: {voltages[3]:.3f}V")
    
    def load_calibration(self, config_path):
        """캘리브레이션 설정 다시 로드"""
        try:
            import json
            # print(f"🔍 캘리브레이션 파일 읽기 시작: {config_path}")  # 디버그용
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # print(f"🔍 JSON 파싱 완료: {list(config.keys())}")  # 디버그용
            
            self.sensor_type = config.get('sensor_type', 'voltage')
            
            tank1 = config.get('tank1_water', {})
            tank2 = config.get('tank2_nutrient', {})
            
            self.tank1_empty = float(tank1.get('empty_value', 0.0))
            self.tank1_full = float(tank1.get('full_value', 3.3))
            self.tank2_empty = float(tank2.get('empty_value', 0.0))
            self.tank2_full = float(tank2.get('full_value', 3.3))
            
            print(f"✅ 캘리브레이션 재로드 완료!")
            print(f"   센서 타입: {self.sensor_type}")
            print(f"   탱크1: {self.tank1_empty:.3f}V ~ {self.tank1_full:.3f}V")
            print(f"   탱크2: {self.tank2_empty:.3f}V ~ {self.tank2_full:.3f}V")
            
            return True
            
        except FileNotFoundError as e:
            print(f"❌ 파일을 찾을 수 없음: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            return False
        except Exception as e:
            print(f"❌ 캘리브레이션 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_current_status(self) -> Dict:
        """
        현재 센서 상태 조회
        
        ✅ 캐시된 마지막 측정값을 반환 (새로 샘플링 안 함)
        캐시가 없으면 즉시 1회 측정
        """
        with self._last_data_lock:
            if self._last_data:
                # 캐시된 값 반환 (샘플링 안 함)
                return self._last_data.copy()
        
        # 캐시가 없으면 즉시 측정 (모니터링 시작 전)
        return self._collect_sensor_data()
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        센서 히스토리 조회
        
        Args:
            limit: 조회할 개수 (None이면 전체)
        
        Returns:
            센서 데이터 리스트
        """
        if limit:
            return self.history[-limit:]
        return self.history.copy()
    
    def get_average_levels(self, count: Optional[int] = None) -> Dict:
        """
        최근 N개 데이터의 평균 수위 계산
        
        Args:
            count: 평균 계산할 데이터 개수 (None이면 전체)
        
        Returns:
            평균 수위 {'tank1': float, 'tank2': float, 'count': int}
        """
        if not self.history:
            return {'tank1': 0.0, 'tank2': 0.0, 'count': 0}
        
        # 최근 데이터만 가져오기
        if count:
            recent = self.history[-count:]
        else:
            recent = self.history
        
        actual_count = len(recent)
        tank1_sum = sum(d['tank1_level'] for d in recent)
        tank2_sum = sum(d['tank2_level'] for d in recent)
        
        return {
            'tank1': tank1_sum / actual_count,
            'tank2': tank2_sum / actual_count,
            'count': actual_count
        }
    
    def add_alert_callback(self, callback: Callable):
        """
        알림 콜백 추가
        
        Args:
            callback: 콜백 함수 (alert_type, message, data)
        """
        self.alert_callbacks.append(callback)
        print(f"✅ 알림 콜백 추가됨 (총 {len(self.alert_callbacks)}개)")

def test_sensor_monitor():
    """테스트 함수"""
    print("\n" + "="*60)
    print("🧪 SensorMonitor 테스트")
    print("="*60)
    
    # 테스트 설정 (10초 간격, 10회 샘플링)
    monitor = SensorMonitor(config={
        'check_interval': 10,
        'sample_count': 10,
        'outlier_remove': 2,
        'min_water_level': 20.0,
        'max_water_level': 90.0
    })
    
    # 알림 콜백 등록
    def alert_callback(alert_type, message, data):
        print(f"🔔 콜백 실행: {alert_type} - {message}")
    
    monitor.add_alert_callback(alert_callback)
    
    print("\n" + "="*60)
    print("📋 테스트 1: 단일 측정")
    print("="*60)
    status = monitor.get_current_status()
    print(f"✅ 탱크1: {status['tank1_level']:.1f}%")
    print(f"✅ 탱크2: {status['tank2_level']:.1f}%")
    
    print("\n" + "="*60)
    print("📋 테스트 2: 실시간 모니터링 (20초)")
    print("="*60)
    monitor.start(blocking=False)
    time.sleep(20)
    monitor.stop()
    
    print("\n" + "="*60)
    print("📋 테스트 3: 히스토리 조회")
    print("="*60)
    history = monitor.get_history(limit=2)
    for i, data in enumerate(history, 1):
        # print(f"기록 {i}: {data['timestamp']} - "  # 디버그용
        # f"탱크1={data['tank1_level']:.1f}%, "  # 디버그용
        pass  # 디버그 print 제거됨
    
    print("\n" + "="*60)
    print("📋 테스트 4: 평균 수위")
    print("="*60)
    avg = monitor.get_average_levels()
    print(f"✅ 평균 탱크1: {avg['tank1']:.1f}%")
    print(f"✅ 평균 탱크2: {avg['tank2']:.1f}%")
    print(f"✅ 데이터 개수: {avg['count']}")
    
    print("\n" + "="*60)
    print("✅ 모든 테스트 완료!")
    print("="*60)

if __name__ == '__main__':
    test_sensor_monitor()
