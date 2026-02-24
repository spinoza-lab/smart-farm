"""
scheduler_new.py - 스케줄 기반 자동 관수 스케줄러 (완전 재작성)
- AutoIrrigationController 주입 방식으로 의존성 단순화
- schedules.json 직접 읽기 (ConfigManager 불필요)
- datetime.now() 사용 (RTCManager 제거)
- 요일 체계 통일: 0=월요일 ~ 6=일요일 (Python weekday() 기준)
"""

import json
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class IrrigationScheduler:
    """
    schedules.json을 주기적으로 읽어 설정된 시간/요일에 관수를 실행하는 스케줄러.
    AutoIrrigationController.irrigate_zone()을 호출하여 실제 관수를 수행한다.
    """

    def __init__(self, auto_controller, schedules_path: str):
        """
        :param auto_controller: AutoIrrigationController 인스턴스
        :param schedules_path: schedules.json 파일 경로 (절대경로 권장)
        """
        self.auto_controller = auto_controller
        self.schedules_path = Path(schedules_path)
        self.check_interval = 30          # 초 단위 점검 주기
        self.running = False
        self._thread = None
        # {schedule_id: 'YYYY-MM-DD'} 형식으로 오늘 이미 실행된 스케줄 기록
        self._executed_today: dict[int, str] = {}
        logger.info("[Scheduler] 초기화 완료 (schedules: %s)", self.schedules_path)

    # ──────────────────────────────────────────
    # 공개 메서드
    # ──────────────────────────────────────────

    def start(self):
        """백그라운드 데몬 스레드로 스케줄러를 시작한다."""
        if self.running:
            logger.warning("[Scheduler] 이미 실행 중입니다.")
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._run_loop, name="IrrigationScheduler", daemon=True
        )
        self._thread.start()
        logger.info("[Scheduler] 스케줄러 시작 (interval=%ds)", self.check_interval)

    def stop(self):
        """스케줄러를 중지한다."""
        self.running = False
        logger.info("[Scheduler] 스케줄러 중지 요청")

    def get_next_schedule(self) -> dict | None:
        """
        지금 이후 가장 빨리 실행될 스케줄 정보를 반환한다.
        반환 형식: {schedule_id, zone_id, zone_name, start_time, duration, days, minutes_until}
        실행 예정 스케줄이 없으면 None 반환.
        """
        schedules = self._load_schedules()
        now = datetime.now()
        today_str = now.strftime("%H:%M")
        today_wd = now.weekday()          # 0=월 ~ 6=일

        candidates = []
        for s in schedules:
            if not s.get("enabled", True):
                continue
            days = s.get("days")          # None 또는 [0,1,...] 리스트

            # 오늘 실행 가능 여부 확인
            if days is None or today_wd in days:
                t = s["start_time"]       # "HH:MM"
                if t > today_str:         # 아직 실행 전
                    h, m = map(int, t.split(":"))
                    run_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                    minutes_until = int((run_dt - now).total_seconds() / 60)
                    candidates.append({**s, "minutes_until": minutes_until, "run_dt": run_dt})

            # 내일 이후 체크 (오늘 스케줄 없을 때)
            if not candidates:
                for delta in range(1, 8):
                    future_dt = now + timedelta(days=delta)
                    future_wd = future_dt.weekday()
                    if days is None or future_wd in days:
                        h, m = map(int, s["start_time"].split(":"))
                        run_dt = future_dt.replace(
                            hour=h, minute=m, second=0, microsecond=0
                        )
                        minutes_until = int((run_dt - now).total_seconds() / 60)
                        candidates.append(
                            {**s, "minutes_until": minutes_until, "run_dt": run_dt}
                        )
                        break

        if not candidates:
            return None

        next_s = min(candidates, key=lambda x: x["run_dt"])
        next_s.pop("run_dt", None)
        return next_s

    # ──────────────────────────────────────────
    # 내부 메서드
    # ──────────────────────────────────────────

    def _run_loop(self):
        """메인 루프: check_interval 초마다 스케줄 점검."""
        logger.info("[Scheduler] 루프 진입")
        while self.running:
            try:
                self._check_and_execute()
            except Exception as exc:
                logger.error("[Scheduler] 점검 중 오류: %s", exc, exc_info=True)
            # check_interval 을 1초 단위로 나눠 sleep 해야 stop() 이 빠르게 반응
            for _ in range(self.check_interval):
                if not self.running:
                    break
                import time
                time.sleep(1)
        logger.info("[Scheduler] 루프 종료")

    def _load_schedules(self) -> list:
        """schedules.json을 읽어 리스트로 반환. 파일 없으면 빈 리스트."""
        try:
            if not self.schedules_path.exists():
                return []
            with open(self.schedules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.error("[Scheduler] schedules.json 로드 실패: %s", exc)
            return []

    def _check_and_execute(self):
        """현재 시각과 스케줄을 비교하여 실행 조건이 맞으면 관수를 시작한다."""
        schedules = self._load_schedules()
        if not schedules:
            return

        now = datetime.now()
        current_time = now.strftime("%H:%M")  # "HH:MM"
        current_wd   = now.weekday()           # 0=월 ~ 6=일
        today_str    = now.strftime("%Y-%m-%d")

        for s in schedules:
            sid = s.get("id")
            if sid is None:
                continue
            if not s.get("enabled", True):
                continue
            if s.get("start_time") != current_time:
                continue
            # 오늘 이미 실행했으면 스킵
            if self._executed_today.get(sid) == today_str:
                continue
            # 요일 체크: days 필드가 없거나 빈 리스트면 매일 실행
            days = s.get("days")
            if days and current_wd not in days:
                continue

            # ✅ 실행 조건 충족
            logger.info(
                "[Scheduler] 스케줄 #%d 실행 시작 - 구역 %d, 시각 %s",
                sid, s.get("zone_id", "?"), current_time,
            )
            self._executed_today[sid] = today_str
            # 별도 스레드로 실행(블로킹 방지)
            t = threading.Thread(
                target=self._execute_schedule,
                args=(s,),
                daemon=True,
                name=f"sched-{sid}",
            )
            t.start()

    def _execute_schedule(self, schedule: dict):
        """실제 관수 실행 (별도 스레드)."""
        sid       = schedule.get("id")
        zone_id   = schedule.get("zone_id")
        duration  = schedule.get("duration", 300)
        zone_name = schedule.get("zone_name", f"구역 {zone_id}")

        logger.info(
            "[Scheduler] 스케줄 #%d 실행: %s, %d초 관수", sid, zone_name, duration
        )
        try:
            success = self.auto_controller.irrigate_zone(
                zone_id=zone_id,
                duration=duration,
                trigger="schedule",
            )
            if success:
                logger.info("[Scheduler] 스케줄 #%d 관수 완료 (%s)", sid, zone_name)
            else:
                logger.warning("[Scheduler] 스케줄 #%d 관수 실패 (%s)", sid, zone_name)
        except Exception as exc:
            logger.error(
                "[Scheduler] 스케줄 #%d 관수 중 예외: %s", sid, exc, exc_info=True
            )
