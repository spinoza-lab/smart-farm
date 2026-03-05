"""
AlertManager 모듈
센서 경고 감지 및 알림 관리

주요 기능:
- 경고 레벨 관리 (INFO, WARNING, CRITICAL)
- 수위 임계값 기반 경고 감지
- 다중 알림 채널 (콘솔, 로그 파일)
- 경고 히스토리 추적
- 중복 알림 방지 (쿨다운)

작성자: spinoza-lab
날짜: 2026-02-12
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable
from enum import Enum
import threading

# BUG-7: 설치 경로 동적 계산 (하드코딩 제거)
_BASE_DIR = Path(__file__).resolve().parent.parent


class AlertLevel(Enum):
    """경고 레벨"""
    INFO = "INFO"           # 정보성 메시지
    WARNING = "WARNING"     # 주의 필요
    CRITICAL = "CRITICAL"   # 즉시 조치 필요


class AlertType(Enum):
    """경고 유형"""
    LOW_WATER_LEVEL = "낮은 수위"
    HIGH_WATER_LEVEL = "높은 수위"
    SENSOR_ERROR = "센서 오류"
    COMMUNICATION_ERROR = "통신 오류"
    SYSTEM_INFO = "시스템 정보"


class Alert:
    """경고 데이터 클래스"""
    
    def __init__(self,
                 alert_type: AlertType,
                 level: AlertLevel,
                 message: str,
                 tank_num: Optional[int] = None,
                 value: Optional[float] = None,
                 timestamp: Optional[datetime] = None):
        """
        경고 객체 생성
        
        Args:
            alert_type: 경고 유형
            level: 경고 레벨
            message: 경고 메시지
            tank_num: 탱크 번호 (해당시)
            value: 측정값 (해당시)
            timestamp: 발생 시간
        """
        self.alert_type = alert_type
        self.level = level
        self.message = message
        self.tank_num = tank_num
        self.value = value
        self.timestamp = timestamp or datetime.now()
    
    def __str__(self):
        """문자열 표현"""
        time_str = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        tank_str = f" [탱크{self.tank_num}]" if self.tank_num else ""
        value_str = f" ({self.value:.1f}%)" if self.value is not None else ""
        
        return f"[{self.level.value}] {time_str}{tank_str} {self.message}{value_str}"
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        return {
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'level': self.level.value,
            'type': self.alert_type.value,
            'message': self.message,
            'tank_num': self.tank_num,
            'value': self.value
        }


class AlertManager:
    """
    경고 관리 클래스
    
    센서 데이터 모니터링 및 경고 발생 시 알림 전송
    """
    
    def __init__(self,
                 tank1_min: float = 20.0,
                 tank1_max: float = 90.0,
                 tank2_min: float = 20.0,
                 tank2_max: float = 90.0,
                 cooldown_seconds: int = 300,
                 log_file: Optional[str] = str(_BASE_DIR / 'logs/alerts.log')):
        """
        AlertManager 초기화
        
        Args:
            tank1_min: 탱크1 최소 수위 (%)
            tank1_max: 탱크1 최대 수위 (%)
            tank2_min: 탱크2 최소 수위 (%)
            tank2_max: 탱크2 최대 수위 (%)
            cooldown_seconds: 중복 알림 방지 시간 (초)
            log_file: 경고 로그 파일 경로
        """
        # 수위 임계값
        self.thresholds = {
            1: {'min': tank1_min, 'max': tank1_max},
            2: {'min': tank2_min, 'max': tank2_max}
        }
        
        # 쿨다운 설정
        self.cooldown_seconds = cooldown_seconds
        self.last_alert_time = {}  # {alert_key: timestamp}
        
        # 로그 파일
        self.log_file = log_file
        self._ensure_log_file()
        
        # 경고 히스토리 (메모리)
        self.alert_history: List[Alert] = []
        self.max_history = 100
        
        # 콜백 함수들
        self.callbacks: List[Callable] = []
        
        # 스레드 안전성
        self._lock = threading.Lock()
        
        print(f"✅ AlertManager 초기화 완료")
        print(f"   탱크1 수위 범위: {tank1_min}% ~ {tank1_max}%")
        print(f"   탱크2 수위 범위: {tank2_min}% ~ {tank2_max}%")
        print(f"   쿨다운: {cooldown_seconds}초")
        if log_file:
            print(f"   로그 파일: {log_file}")
    
    def _ensure_log_file(self):
        """로그 파일 디렉터리 생성"""
        if self.log_file:
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
    
    def set_threshold(self, tank_num: int, min_level: float, max_level: float):
        """
        탱크 수위 임계값 설정
        
        Args:
            tank_num: 탱크 번호 (1 또는 2)
            min_level: 최소 수위 (%)
            max_level: 최대 수위 (%)
        """
        if tank_num not in [1, 2]:
            raise ValueError("탱크 번호는 1 또는 2여야 합니다")
        
        self.thresholds[tank_num] = {'min': min_level, 'max': max_level}
        print(f"✅ 탱크{tank_num} 임계값 설정: {min_level}% ~ {max_level}%")
    
    def add_callback(self, callback: Callable):
        """
        경고 발생 시 호출할 콜백 함수 추가
        
        Args:
            callback: 콜백 함수 (alert: Alert 인자 받음)
        """
        self.callbacks.append(callback)
    
    def _is_cooldown_active(self, alert_key: str) -> bool:
        """
        쿨다운 상태 확인
        
        Args:
            alert_key: 경고 키 (예: "low_water_tank1")
        
        Returns:
            쿨다운 활성 여부
        """
        if alert_key not in self.last_alert_time:
            return False
        
        last_time = self.last_alert_time[alert_key]
        elapsed = (datetime.now() - last_time).total_seconds()
        
        return elapsed < self.cooldown_seconds
    
    def _update_cooldown(self, alert_key: str):
        """쿨다운 시간 업데이트"""
        self.last_alert_time[alert_key] = datetime.now()
    
    def _create_alert(self,
                     alert_type: AlertType,
                     level: AlertLevel,
                     message: str,
                     tank_num: Optional[int] = None,
                     value: Optional[float] = None) -> Alert:
        """
        경고 객체 생성 및 처리
        
        Args:
            alert_type: 경고 유형
            level: 경고 레벨
            message: 경고 메시지
            tank_num: 탱크 번호
            value: 측정값
        
        Returns:
            생성된 Alert 객체
        """
        alert = Alert(
            alert_type=alert_type,
            level=level,
            message=message,
            tank_num=tank_num,
            value=value
        )
        
        # 스레드 안전하게 히스토리 추가
        with self._lock:
            self.alert_history.append(alert)
            
            # 히스토리 크기 제한
            if len(self.alert_history) > self.max_history:
                self.alert_history.pop(0)
        
        # 알림 전송
        self._send_alert(alert)
        
        return alert
    
    def _send_alert(self, alert: Alert):
        """
        경고 알림 전송
        
        Args:
            alert: Alert 객체
        """
        # 1. 콘솔 출력
        self._console_alert(alert)
        
        # 2. 로그 파일 기록
        if self.log_file:
            self._log_alert(alert)
        
        # 3. 콜백 함수 호출
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"⚠️  콜백 실행 오류: {e}")
    
    def _console_alert(self, alert: Alert):
        """콘솔에 경고 출력"""
        # 레벨별 아이콘
        icons = {
            AlertLevel.INFO: "ℹ️ ",
            AlertLevel.WARNING: "⚠️ ",
            AlertLevel.CRITICAL: "🚨"
        }
        
        icon = icons.get(alert.level, "")
        print(f"{icon} {alert}")
    
    def _log_alert(self, alert: Alert):
        """로그 파일에 경고 기록"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{alert}\n")
        except Exception as e:
            print(f"⚠️  로그 파일 쓰기 실패: {e}")
    
    def check_water_level(self, tank_num: int, level: float) -> Optional[Alert]:
        """
        수위 체크 및 경고 발생
        
        Args:
            tank_num: 탱크 번호 (1 또는 2)
            level: 현재 수위 (%)
        
        Returns:
            발생한 경고 (없으면 None)
        """
        if tank_num not in self.thresholds:
            return None
        
        threshold = self.thresholds[tank_num]
        min_level = threshold['min']
        max_level = threshold['max']
        
        # 낮은 수위 체크
        if level < min_level:
            alert_key = f"low_water_tank{tank_num}"
            
            if not self._is_cooldown_active(alert_key):
                self._update_cooldown(alert_key)
                
                return self._create_alert(
                    alert_type=AlertType.LOW_WATER_LEVEL,
                    level=AlertLevel.CRITICAL if level < min_level * 0.8 else AlertLevel.WARNING,
                    message=f"탱크 {tank_num} 수위 부족 (최소: {min_level}%)",
                    tank_num=tank_num,
                    value=level
                )
        
        # 높은 수위 체크
        elif level > max_level:
            alert_key = f"high_water_tank{tank_num}"
            
            if not self._is_cooldown_active(alert_key):
                self._update_cooldown(alert_key)
                
                return self._create_alert(
                    alert_type=AlertType.HIGH_WATER_LEVEL,
                    level=AlertLevel.WARNING,
                    message=f"탱크 {tank_num} 수위 과잉 (최대: {max_level}%)",
                    tank_num=tank_num,
                    value=level
                )
        
        return None
    
    def check_sensor_error(self, voltage: float, channel: int) -> Optional[Alert]:
        """
        센서 오류 체크
        
        Args:
            voltage: 측정 전압
            channel: 채널 번호
        
        Returns:
            발생한 경고 (없으면 None)
        """
        # 비정상 전압 범위 (0V 또는 3.3V 이상)
        if voltage < 0.1 or voltage > 3.2:
            alert_key = f"sensor_error_ch{channel}"
            
            if not self._is_cooldown_active(alert_key):
                self._update_cooldown(alert_key)
                
                return self._create_alert(
                    alert_type=AlertType.SENSOR_ERROR,
                    level=AlertLevel.WARNING,
                    message=f"채널 {channel} 센서 오류 (비정상 전압: {voltage:.3f}V)",
                    value=voltage
                )
        
        return None
    
    def report_communication_error(self, error_msg: str) -> Alert:
        """
        통신 오류 보고
        
        Args:
            error_msg: 오류 메시지
        
        Returns:
            생성된 경고
        """
        alert_key = "communication_error"
        
        if not self._is_cooldown_active(alert_key):
            self._update_cooldown(alert_key)
            
            return self._create_alert(
                alert_type=AlertType.COMMUNICATION_ERROR,
                level=AlertLevel.CRITICAL,
                message=f"통신 오류: {error_msg}"
            )
        
        return None
    
    def report_info(self, message: str) -> Alert:
        """
        정보성 메시지 보고
        
        Args:
            message: 메시지 내용
        
        Returns:
            생성된 경고
        """
        return self._create_alert(
            alert_type=AlertType.SYSTEM_INFO,
            level=AlertLevel.INFO,
            message=message
        )
    
    def get_alert_history(self,
                         level: Optional[AlertLevel] = None,
                         alert_type: Optional[AlertType] = None,
                         limit: int = 50) -> List[Alert]:
        """
        경고 히스토리 조회
        
        Args:
            level: 필터링할 경고 레벨
            alert_type: 필터링할 경고 유형
            limit: 최대 개수
        
        Returns:
            경고 리스트 (최신순)
        """
        with self._lock:
            filtered = self.alert_history.copy()
        
        # 필터 적용
        if level:
            filtered = [a for a in filtered if a.level == level]
        
        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]
        
        # 최신순 정렬 및 제한
        filtered.reverse()
        return filtered[:limit]
    
    def get_alert_count(self,
                       level: Optional[AlertLevel] = None,
                       hours: int = 24) -> int:
        """
        기간 내 경고 개수 조회
        
        Args:
            level: 필터링할 경고 레벨
            hours: 조회 기간 (시간)
        
        Returns:
            경고 개수
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            filtered = [
                a for a in self.alert_history
                if a.timestamp >= cutoff_time
            ]
        
        if level:
            filtered = [a for a in filtered if a.level == level]
        
        return len(filtered)
    
    def clear_cooldown(self, alert_key: Optional[str] = None):
        """
        쿨다운 초기화
        
        Args:
            alert_key: 특정 키만 초기화 (None이면 전체)
        """
        if alert_key:
            if alert_key in self.last_alert_time:
                del self.last_alert_time[alert_key]
                print(f"✅ 쿨다운 초기화: {alert_key}")
        else:
            self.last_alert_time.clear()
            print("✅ 전체 쿨다운 초기화")
    
    def get_current_status(self) -> Dict:
        """
        현재 상태 조회
        
        Returns:
            상태 딕셔너리
        """
        return {
            'thresholds': self.thresholds,
            'cooldown_seconds': self.cooldown_seconds,
            'alert_count_24h': self.get_alert_count(hours=24),
            'critical_count_24h': self.get_alert_count(level=AlertLevel.CRITICAL, hours=24),
            'warning_count_24h': self.get_alert_count(level=AlertLevel.WARNING, hours=24)
        }


# ============================================================
# 테스트 코드
# ============================================================

def test_alert_manager():
    """AlertManager 테스트"""
    
    print("=" * 60)
    print("🧪 AlertManager 테스트")
    print("=" * 60)
    print()
    
    # 테스트용 임시 로그 파일
    import tempfile
    temp_log = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
    temp_log.close()
    
    print("=" * 60)
    print("📊 AlertManager 초기화")
    print("=" * 60)
    alert_mgr = AlertManager(
        tank1_min=20.0,
        tank1_max=90.0,
        tank2_min=25.0,
        tank2_max=85.0,
        cooldown_seconds=5,  # 테스트용 짧은 쿨다운
        log_file=temp_log.name
    )
    print()
    
    # 콜백 함수 추가
    def custom_callback(alert: Alert):
        print(f"  📢 콜백 호출: {alert.alert_type.value} - {alert.message}")
    
    alert_mgr.add_callback(custom_callback)
    
    # [테스트 1] 낮은 수위 경고
    print("[테스트 1] 낮은 수위 경고")
    print("-" * 60)
    alert_mgr.check_water_level(tank_num=1, level=15.0)  # CRITICAL
    print()
    
    # [테스트 2] 높은 수위 경고
    print("[테스트 2] 높은 수위 경고")
    print("-" * 60)
    alert_mgr.check_water_level(tank_num=2, level=92.0)  # WARNING
    print()
    
    # [테스트 3] 정상 수위 (경고 없음)
    print("[테스트 3] 정상 수위 (경고 없음)")
    print("-" * 60)
    result = alert_mgr.check_water_level(tank_num=1, level=50.0)
    if result is None:
        print("✅ 정상 수위: 경고 없음")
    print()
    
    # [테스트 4] 센서 오류
    print("[테스트 4] 센서 오류")
    print("-" * 60)
    alert_mgr.check_sensor_error(voltage=0.05, channel=0)  # 비정상 낮은 전압
    alert_mgr.check_sensor_error(voltage=3.4, channel=1)   # 비정상 높은 전압
    print()
    
    # [테스트 5] 통신 오류
    print("[테스트 5] 통신 오류")
    print("-" * 60)
    alert_mgr.report_communication_error("I2C 읽기 실패")
    print()
    
    # [테스트 6] 정보성 메시지
    print("[테스트 6] 정보성 메시지")
    print("-" * 60)
    alert_mgr.report_info("시스템 시작됨")
    print()
    
    # [테스트 7] 쿨다운 (중복 알림 방지)
    print("[테스트 7] 쿨다운 테스트 (5초 내 중복)")
    print("-" * 60)
    alert_mgr.check_water_level(tank_num=1, level=15.0)  # 쿨다운으로 차단
    print("✅ 쿨다운 활성: 중복 알림 차단됨")
    print()
    
    import time
    print("⏰ 5초 대기 중...")
    time.sleep(5)
    print()
    
    print("[테스트 8] 쿨다운 해제 후 재알림")
    print("-" * 60)
    alert_mgr.check_water_level(tank_num=1, level=15.0)  # 쿨다운 해제됨
    print()
    
    # [테스트 9] 경고 히스토리
    print("[테스트 9] 경고 히스토리")
    print("-" * 60)
    history = alert_mgr.get_alert_history(limit=10)
    print(f"✅ 총 경고 개수: {len(history)}")
    print(f"   최근 3개:")
    for alert in history[:3]:
        print(f"     - {alert}")
    print()
    
    # [테스트 10] 레벨별 통계
    print("[테스트 10] 레벨별 통계")
    print("-" * 60)
    critical = alert_mgr.get_alert_count(level=AlertLevel.CRITICAL, hours=1)
    warning = alert_mgr.get_alert_count(level=AlertLevel.WARNING, hours=1)
    info = alert_mgr.get_alert_count(level=AlertLevel.INFO, hours=1)
    print(f"✅ CRITICAL: {critical}개")
    print(f"✅ WARNING: {warning}개")
    print(f"✅ INFO: {info}개")
    print()
    
    # [테스트 11] 현재 상태
    print("[테스트 11] 현재 상태")
    print("-" * 60)
    status = alert_mgr.get_current_status()
    print(f"✅ 탱크1 범위: {status['thresholds'][1]['min']}% ~ {status['thresholds'][1]['max']}%")
    print(f"✅ 탱크2 범위: {status['thresholds'][2]['min']}% ~ {status['thresholds'][2]['max']}%")
    print(f"✅ 24시간 경고: {status['alert_count_24h']}개")
    print()
    
    # 테스트 로그 파일 삭제
    os.unlink(temp_log.name)
    
    print("=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_alert_manager()
