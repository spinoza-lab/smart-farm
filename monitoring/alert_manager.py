"""
AlertManager 모듈
센서 경고 감지 및 알림 관리

주요 기능:
- 경고 레벨 관리 (INFO, WARNING, CRITICAL)
- 수위 임계값 기반 경고 감지
- 다중 알림 채널 (콘솔, 로그 파일, SQLite DB)
- 경고 히스토리 추적
- 중복 알림 방지 (쿨다운)

작성자: spinoza-lab
날짜: 2026-02-12
Stage 12: SQLite alerts 테이블 연동 추가 (2026-03-17)
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
                 threshold: Optional[float] = None,   # Stage 12: 임계값 추가
                 timestamp: Optional[datetime] = None):
        self.alert_type = alert_type
        self.level = level
        self.message = message
        self.tank_num = tank_num
        self.value = value
        self.threshold = threshold      # Stage 12
        self.timestamp = timestamp or datetime.now()

    def __str__(self):
        time_str = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        tank_str = f" [탱크{self.tank_num}]" if self.tank_num else ""
        value_str = f" ({self.value:.1f}%)" if self.value is not None else ""
        return f"[{self.level.value}] {time_str}{tank_str} {self.message}{value_str}"

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'level': self.level.value,
            'type': self.alert_type.value,
            'message': self.message,
            'tank_num': self.tank_num,
            'value': self.value,
            'threshold': self.threshold,    # Stage 12
        }


class AlertManager:
    """
    경고 관리 클래스

    센서 데이터 모니터링 및 경고 발생 시 알림 전송
    Stage 12: db_manager 연동으로 SQLite alerts 테이블 자동 저장
    """

    def __init__(self,
                 tank1_min: float = 20.0,
                 tank1_max: float = 90.0,
                 tank2_min: float = 20.0,
                 tank2_max: float = 90.0,
                 cooldown_seconds: int = 300,
                 log_file: Optional[str] = str(_BASE_DIR / 'logs/alerts.log'),
                 db_manager=None,               # Stage 12: SQLite 연동
                 vol_min: float = 0.1,           # 센서 정상 전압 하한
                 vol_max: float = 3.2):          # 센서 정상 전압 상한
        # 수위 임계값
        self.thresholds = {
            1: {'min': tank1_min, 'max': tank1_max},
            2: {'min': tank2_min, 'max': tank2_max}
        }

        # 쿨다운 설정
        self.cooldown_seconds = cooldown_seconds
        self.last_alert_time = {}
        # BUG-14 P1: 센서 연속 오류 카운터 & 복구 플래그
        from collections import defaultdict as _dd
        self.sensor_error_counts = _dd(int)
        self.sensor_recovered    = _dd(lambda: True)

        # 로그 파일
        self.log_file = log_file
        self._ensure_log_file()

        # Stage 12: SQLite DB 연동
        self.db_manager = db_manager

        # 경고 히스토리 (메모리)
        self.alert_history: List[Alert] = []
        self.max_history = 100

        # 콜백 함수들
        self.callbacks: List[Callable] = []

        # 스레드 안전성
        self._lock = threading.Lock()

        # 센서 전압 임계값 (오류 판단 기준) — notifications.json에서 주입
        self.vol_min = vol_min
        self.vol_max = vol_max

        db_mode = "SQLite + CSV" if db_manager else "CSV only"
        print(f"✅ AlertManager 초기화 완료 ({db_mode})")
        print(f"   탱크1 수위 범위: {tank1_min}% ~ {tank1_max}%")
        print(f"   탱크2 수위 범위: {tank2_min}% ~ {tank2_max}%")
        print(f"   쿨다운: {cooldown_seconds}초")
        if log_file:
            print(f"   로그 파일: {log_file}")

    def _ensure_log_file(self):
        if self.log_file:
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

    def set_threshold(self, tank_num: int, min_level: float, max_level: float):
        if tank_num not in [1, 2]:
            raise ValueError("탱크 번호는 1 또는 2여야 합니다")
        self.thresholds[tank_num] = {'min': min_level, 'max': max_level}
        print(f"✅ 탱크{tank_num} 임계값 설정: {min_level}% ~ {max_level}%")

    def add_callback(self, callback: Callable):
        self.callbacks.append(callback)

    def _is_cooldown_active(self, alert_key: str) -> bool:
        if alert_key not in self.last_alert_time:
            return False
        elapsed = (datetime.now() - self.last_alert_time[alert_key]).total_seconds()
        return elapsed < self.cooldown_seconds

    def _update_cooldown(self, alert_key: str):
        self.last_alert_time[alert_key] = datetime.now()

    def _create_alert(self,
                      alert_type: AlertType,
                      level: AlertLevel,
                      message: str,
                      tank_num: Optional[int] = None,
                      value: Optional[float] = None,
                      threshold: Optional[float] = None) -> Alert:   # Stage 12
        alert = Alert(
            alert_type=alert_type,
            level=level,
            message=message,
            tank_num=tank_num,
            value=value,
            threshold=threshold,
        )

        with self._lock:
            self.alert_history.append(alert)
            if len(self.alert_history) > self.max_history:
                self.alert_history.pop(0)

        self._send_alert(alert)
        return alert

    def _send_alert(self, alert: Alert):
        # 1. 콘솔 출력
        self._console_alert(alert)
        # 2. 로그 파일 기록
        if self.log_file:
            self._log_alert(alert)
        # 3. SQLite DB 저장 (Stage 12)
        self._save_to_db(alert)
        # 4. 콜백 함수 호출
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"⚠️  콜백 실행 오류: {e}")

    def _console_alert(self, alert: Alert):
        icons = {
            AlertLevel.INFO: "ℹ️ ",
            AlertLevel.WARNING: "⚠️ ",
            AlertLevel.CRITICAL: "🚨"
        }
        print(f"{icons.get(alert.level, '')} {alert}")

    def _log_alert(self, alert: Alert):
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{alert}\n")
        except Exception as e:
            print(f"⚠️  로그 파일 쓰기 실패: {e}")

    # ── Stage 12: SQLite 저장 ─────────────────────────────────────────────────
    def _save_to_db(self, alert: Alert):
        """
        알림을 SQLite alerts 테이블에 저장
        db_manager가 None이면 무시 (CSV only 모드 유지)
        """
        if self.db_manager is None:
            return
        try:
            self.db_manager.insert_alert(
                level=alert.level.value,
                type_=alert.alert_type.value,
                message=alert.message,
                value=alert.value if alert.value is not None else 0.0,
                threshold=alert.threshold if alert.threshold is not None else 0.0,
                timestamp=alert.timestamp,
            )
        except Exception as e:
            print(f"⚠️  DB 알림 저장 실패: {e}")
    # ─────────────────────────────────────────────────────────────────────────

    def check_water_level(self, tank_num: int, level: float) -> Optional[Alert]:
        if tank_num not in self.thresholds:
            return None

        threshold = self.thresholds[tank_num]
        min_level = threshold['min']
        max_level = threshold['max']

        if level < min_level:
            alert_key = f"low_water_tank{tank_num}"
            if not self._is_cooldown_active(alert_key):
                self._update_cooldown(alert_key)
                return self._create_alert(
                    alert_type=AlertType.LOW_WATER_LEVEL,
                    level=AlertLevel.CRITICAL if level < min_level * 0.8 else AlertLevel.WARNING,
                    message=f"탱크 {tank_num} 수위 부족 (최소: {min_level}%)",
                    tank_num=tank_num,
                    value=level,
                    threshold=min_level,    # Stage 12
                )

        elif level > max_level:
            alert_key = f"high_water_tank{tank_num}"
            if not self._is_cooldown_active(alert_key):
                self._update_cooldown(alert_key)
                return self._create_alert(
                    alert_type=AlertType.HIGH_WATER_LEVEL,
                    level=AlertLevel.WARNING,
                    message=f"탱크 {tank_num} 수위 과잉 (최대: {max_level}%)",
                    tank_num=tank_num,
                    value=level,
                    threshold=max_level,    # Stage 12
                )

        return None

    def check_sensor_error(self, voltage, channel: int):
        """
        센서 오류 체크 (BUG-14 P1)
        - None 전압 허용 (I2C 읽기 실패)
        - 연속 오류 1회 → WARNING, 5회↑ → CRITICAL 재알림
        - 정상 복구 감지 → INFO 알림 + 쿨다운 초기화
        """
        alert_key = f"sensor_error_ch{channel}"
        is_error  = (voltage is None) or (voltage < self.vol_min or voltage > self.vol_max)

        if is_error:
            self.sensor_error_counts[channel] += 1
            self.sensor_recovered[channel] = False
            count    = self.sensor_error_counts[channel]
            volt_str = f"{voltage:.3f}V" if voltage is not None else "None (읽기 실패)"

            if count >= 5 and not self._is_cooldown_active(alert_key + "_critical"):
                self._update_cooldown(alert_key + "_critical")
                return self._create_alert(
                    alert_type=AlertType.SENSOR_ERROR,
                    level=AlertLevel.CRITICAL,
                    message=f"채널 {channel} 센서 연속 오류 {count}회 ({volt_str})",
                    value=voltage,
                    threshold=None,
                )
            elif count == 1 and not self._is_cooldown_active(alert_key):
                self._update_cooldown(alert_key)
                return self._create_alert(
                    alert_type=AlertType.SENSOR_ERROR,
                    level=AlertLevel.WARNING,
                    message=f"채널 {channel} 센서 오류 ({volt_str})",
                    value=voltage,
                    threshold=None,
                )
        else:
            prev = self.sensor_error_counts[channel]
            self.sensor_error_counts[channel] = 0
            if not self.sensor_recovered[channel] and prev > 0:
                self.sensor_recovered[channel] = True
                self.last_alert_time.pop(alert_key, None)
                self.last_alert_time.pop(alert_key + "_critical", None)
                return self._create_alert(
                    alert_type=AlertType.SENSOR_ERROR,
                    level=AlertLevel.INFO,
                    message=f"채널 {channel} 센서 복구됨 (전압: {voltage:.3f}V)",
                    value=voltage,
                    threshold=None,
                )

        return None

    def report_communication_error(self, error_msg: str) -> Alert:
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
        return self._create_alert(
            alert_type=AlertType.SYSTEM_INFO,
            level=AlertLevel.INFO,
            message=message
        )

    def get_alert_history(self,
                          level: Optional[AlertLevel] = None,
                          alert_type: Optional[AlertType] = None,
                          limit: int = 50) -> List[Alert]:
        with self._lock:
            filtered = self.alert_history.copy()
        if level:
            filtered = [a for a in filtered if a.level == level]
        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]
        filtered.reverse()
        return filtered[:limit]

    def get_alert_count(self,
                        level: Optional[AlertLevel] = None,
                        hours: int = 24) -> int:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        with self._lock:
            filtered = [a for a in self.alert_history if a.timestamp >= cutoff_time]
        if level:
            filtered = [a for a in filtered if a.level == level]
        return len(filtered)

    def clear_cooldown(self, alert_key: Optional[str] = None):
        if alert_key:
            if alert_key in self.last_alert_time:
                del self.last_alert_time[alert_key]
                print(f"✅ 쿨다운 초기화: {alert_key}")
        else:
            self.last_alert_time.clear()
            print("✅ 전체 쿨다운 초기화")

    def get_current_status(self) -> Dict:
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

    import tempfile
    temp_log = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
    temp_log.close()

    alert_mgr = AlertManager(
        tank1_min=20.0, tank1_max=90.0,
        tank2_min=25.0, tank2_max=85.0,
        cooldown_seconds=5,
        log_file=temp_log.name
    )

    def custom_callback(alert: Alert):
        print(f"  📢 콜백: {alert.alert_type.value} - {alert.message}")

    alert_mgr.add_callback(custom_callback)

    print("\n[테스트 1] 낮은 수위 경고"); alert_mgr.check_water_level(1, 15.0)
    print("\n[테스트 2] 높은 수위 경고"); alert_mgr.check_water_level(2, 92.0)
    print("\n[테스트 3] 정상 수위")
    r = alert_mgr.check_water_level(1, 50.0)
    print("✅ 경고 없음" if r is None else f"경고: {r}")
    print("\n[테스트 4] 센서 오류")
    alert_mgr.check_sensor_error(0.05, 0)
    alert_mgr.check_sensor_error(3.4, 1)
    print("\n[테스트 5] 통신 오류"); alert_mgr.report_communication_error("I2C 읽기 실패")
    print("\n[테스트 6] 정보성 메시지"); alert_mgr.report_info("시스템 시작됨")

    history = alert_mgr.get_alert_history(limit=10)
    print(f"\n[테스트 7] 히스토리: {len(history)}개")
    for a in history[:3]:
        print(f"  - {a}")

    status = alert_mgr.get_current_status()
    print(f"\n[테스트 8] 상태: CRITICAL {status['critical_count_24h']}개 / WARNING {status['warning_count_24h']}개")

    os.unlink(temp_log.name)
    print("\n✅ 모든 테스트 완료!")


if __name__ == "__main__":
    test_alert_manager()
