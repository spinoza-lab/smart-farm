"""
스마트 관수 시스템 - 스케줄러 v2
스케줄 타입: schedule(요일+시간) / routine(날짜시간 기준 N일 반복)
인터록: auto_controller.is_irrigating 플래그 확인 후 대기 실행
유예창: 10분(600초)
"""
import json, logging, threading, time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEDULES_PATH   = Path("/home/pi/smart_farm/config/schedules.json")
GRACE_SECONDS    = 600
INTERLOCK_WAIT   = 10
INTERLOCK_TIMEOUT= 3600
CHECK_INTERVAL   = 30

def _load_schedules():
    if not SCHEDULES_PATH.exists():
        SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULES_PATH.write_text(json.dumps({"schedules":[]}, indent=2))
        return []
    try:
        return json.loads(SCHEDULES_PATH.read_text()).get("schedules", [])
    except Exception as e:
        logger.error(f"schedules.json 로드 실패: {e}"); return []

def _save_schedules(schedules):
    try:
        SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULES_PATH.write_text(json.dumps({"schedules":schedules}, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error(f"schedules.json 저장 실패: {e}")

def _should_run_schedule(entry, now):
    try:
        h, m = map(int, entry["start_time"].split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        diff = (now - target).total_seconds()
        return (now.weekday() in entry.get("days",[])) and (0 <= diff <= GRACE_SECONDS)
    except Exception as e:
        logger.error(f"스케줄 체크 오류: {e}"); return False

def _should_run_routine(entry, now):
    try:
        start_dt = datetime.strptime(f"{entry['start_date']} {entry['start_time']}:00", "%Y-%m-%d %H:%M:%S")
        if now < start_dt: return False
        interval_secs = max(int(entry.get("interval_days",1)),1) * 86400
        phase = (now - start_dt).total_seconds() % interval_secs
        return 0 <= phase <= GRACE_SECONDS
    except Exception as e:
        logger.error(f"루틴 체크 오류: {e}"); return False

def _next_run_schedule(entry, now):
    try:
        h, m = map(int, entry["start_time"].split(":"))
        days = entry.get("days",[])
        for delta in range(8):
            c = (now+timedelta(days=delta)).replace(hour=h,minute=m,second=0,microsecond=0)
            if c > now and c.weekday() in days: return c
    except: pass; return None

def _next_run_routine(entry, now):
    try:
        start_dt = datetime.strptime(f"{entry['start_date']} {entry['start_time']}:00", "%Y-%m-%d %H:%M:%S")
        if now < start_dt: return start_dt
        iv = max(int(entry.get("interval_days",1)),1) * 86400
        elapsed = (now - start_dt).total_seconds()
        return start_dt + timedelta(seconds=(int(elapsed//iv)+1)*iv)
    except: return None

class IrrigationScheduler:
    def __init__(self, auto_controller):
        self.controller = auto_controller
        self._running   = False
        self._thread    = None
        self._executed_keys = set()
        self._queue     = []
        self._queue_lock= threading.Lock()

    def start(self):
        if self._running: return
        self._running = True
        self._thread  = threading.Thread(target=self._run_loop, daemon=True, name="IrrigationScheduler")
        self._thread.start()
        logger.info("IrrigationScheduler 시작")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive(): self._thread.join(timeout=5)
        logger.info("IrrigationScheduler 정지")

    def _run_loop(self):
        while self._running:
            try:
                self._check_and_queue()
                self._process_queue()
            except Exception as e:
                logger.error(f"스케줄 루프 예외: {e}")
            time.sleep(CHECK_INTERVAL)

    def _check_and_queue(self):
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d %H")
        for entry in _load_schedules():
            if not entry.get("enabled", True): continue
            eid = entry.get("id")
            exec_key = (eid, hour_key)
            if exec_key in self._executed_keys: continue
            etype = entry.get("type","schedule")
            should = _should_run_schedule(entry,now) if etype=="schedule" else (_should_run_routine(entry,now) if etype=="routine" else False)
            if should:
                with self._queue_lock:
                    if not any(j["id"]==eid for j in self._queue):
                        logger.info(f"[스케줄러] 큐 추가: id={eid} type={etype} zone={entry.get('zone_id')}")
                        self._queue.append(dict(entry))
                        self._executed_keys.add(exec_key)
                        if len(self._executed_keys)>500:
                            for k in sorted(self._executed_keys)[:250]: self._executed_keys.discard(k)

    def _process_queue(self):
        with self._queue_lock:
            if not self._queue: return
            job = self._queue[0]
        self._execute_job(job)
        with self._queue_lock:
            if self._queue and self._queue[0].get("id")==job.get("id"): self._queue.pop(0)

    def _execute_job(self, entry):
        zone_id        = entry.get("zone_id",1)
        duration       = entry.get("duration",300)
        check_moisture = entry.get("check_moisture",False)
        eid            = entry.get("id","?")
        etype          = entry.get("type","schedule")
        logger.info(f"[스케줄러] 실행 대기: id={eid} zone={zone_id} dur={duration}s check_moisture={check_moisture}")
        waited = 0
        while getattr(self.controller,"is_irrigating",False):
            if waited >= INTERLOCK_TIMEOUT:
                logger.warning(f"[스케줄러] 인터록 타임아웃 → 취소: id={eid}"); return
            logger.debug(f"[스케줄러] 관수중 대기: {waited}s")
            time.sleep(INTERLOCK_WAIT); waited += INTERLOCK_WAIT
            if not self._running: return
        if check_moisture and etype=="routine":
            try:
                sd = self.controller.get_sensor_data()
                m  = sd.get(f"zone_{zone_id}",{}).get("moisture",100)
                th = self.controller.thresholds.get(str(zone_id),40)
                if m >= th:
                    logger.info(f"[스케줄러] 수분 충분 스킵: zone={zone_id} {m}%>={th}%"); return
            except Exception as e:
                logger.warning(f"[스케줄러] 수분 체크 실패(계속): {e}")
        logger.info(f"[스케줄러] 관수 실행: id={eid} zone={zone_id} {duration}s")
        try:
            ok = self.controller.start_zone_irrigation(zone_id=zone_id, duration=duration, trigger="scheduler")
            logger.info(f"[스케줄러] 완료: id={eid} zone={zone_id} ok={ok}")
        except Exception as e:
            logger.error(f"[스케줄러] 예외: id={eid}: {e}")

    # ── 외부 API ──────────────────────────────────────────────────────────────
    def get_all_schedules(self):
        return _load_schedules()

    def add_schedule(self, data):
        schedules = _load_schedules()
        new_id = max((s.get("id",0) for s in schedules), default=0) + 1
        now_str= datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry  = {"id":new_id,"type":data.get("type","schedule"),
                  "zone_id":int(data.get("zone_id",1)),
                  "duration":int(data.get("duration",300)),
                  "enabled":True,"created_at":now_str}
        if entry["type"]=="schedule":
            entry["start_time"] = data.get("start_time","06:00")
            entry["days"]       = data.get("days",[])
        elif entry["type"]=="routine":
            entry["start_date"]     = data.get("start_date",datetime.now().strftime("%Y-%m-%d"))
            entry["start_time"]     = data.get("start_time","06:00")
            entry["interval_days"]  = int(data.get("interval_days",1))
            entry["check_moisture"] = bool(data.get("check_moisture",False))
        schedules.append(entry)
        _save_schedules(schedules)
        logger.info(f"스케줄 추가: id={new_id} type={entry['type']}")
        return entry

    def update_schedule(self, schedule_id, data):
        schedules = _load_schedules()
        for i,s in enumerate(schedules):
            if s.get("id")==schedule_id:
                s.update({k:v for k,v in data.items() if k not in ("id","created_at")})
                schedules[i]=s; _save_schedules(schedules)
                for k in {k for k in self._executed_keys if k[0]==schedule_id}: self._executed_keys.discard(k)
                return True
        return False

    def delete_schedule(self, schedule_id):
        schedules = _load_schedules()
        new_list = [s for s in schedules if s.get("id")!=schedule_id]
        if len(new_list)==len(schedules): return False
        _save_schedules(new_list)
        for k in {k for k in self._executed_keys if k[0]==schedule_id}: self._executed_keys.discard(k)
        return True

    def toggle_schedule(self, schedule_id):
        schedules = _load_schedules()
        for i,s in enumerate(schedules):
            if s.get("id")==schedule_id:
                s["enabled"]=not s.get("enabled",True); schedules[i]=s; _save_schedules(schedules)
                return {"id":schedule_id,"enabled":s["enabled"]}
        return {}

    def get_next_schedules(self, limit=5):
        now = datetime.now(); result = []
        for entry in _load_schedules():
            if not entry.get("enabled",True): continue
            etype = entry.get("type","schedule")
            ndt   = _next_run_schedule(entry,now) if etype=="schedule" else (_next_run_routine(entry,now) if etype=="routine" else None)
            if ndt:
                result.append({"id":entry.get("id"),"type":etype,
                               "zone_id":entry.get("zone_id"),
                               "next_run":ndt.strftime("%Y-%m-%d %H:%M"),
                               "duration":entry.get("duration")})
        result.sort(key=lambda x:x["next_run"])
        return result[:limit]
