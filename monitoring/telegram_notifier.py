"""
TelegramNotifier – 스마트팜 텔레그램 알림 모듈
Phase 1: 자동 알림 (수위, 관수 시작/완료, 서버 시작)
Phase 2: 명령어 봇 (/status, /irrigate, /stop 등)
"""

import threading
import time
import requests
import json
import os
from datetime import datetime

CONFIG_PATH = "/home/pi/smart_farm/config/notifications.json"
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ notifications.json 저장 실패: {e}")


class TelegramNotifier:
    """텔레그램 알림 전송 클래스"""

    def __init__(self, token: str, chat_id: str):
        self.token    = token
        self.chat_id  = str(chat_id)
        self.enabled  = True
        self._mute_until = None          # datetime or None
        self._lock    = threading.Lock()

        # 명령어 폴링 스레드
        self._polling      = False
        self._poll_thread  = None
        self._last_update  = 0
        self._controller   = None        # AutoIrrigationController 참조 (Phase 2)

        print(f"✅ TelegramNotifier 초기화 완료 (chat_id={self.chat_id})")

    # ── 무음 제어 ──────────────────────────────────────────────────────
    def mute(self, seconds: int):
        from datetime import timedelta
        with self._lock:
            self._mute_until = datetime.now() + timedelta(seconds=seconds)
        print(f"🔇 텔레그램 알림 무음: {seconds}초")

    def unmute(self):
        with self._lock:
            self._mute_until = None
        print("🔔 텔레그램 알림 무음 해제")

    def _is_muted(self) -> bool:
        with self._lock:
            if self._mute_until is None:
                return False
            if datetime.now() < self._mute_until:
                return True
            self._mute_until = None
            return False

    # ── 메시지 전송 ────────────────────────────────────────────────────
    def send(self, text: str, force: bool = False) -> bool:
        """텔레그램 메시지 전송. force=True면 무음 무시."""
        if not self.enabled:
            return False
        if not force and self._is_muted():
            return False
        try:
            url  = TELEGRAM_API.format(token=self.token, method="sendMessage")
            resp = requests.post(url, json={
                "chat_id":    self.chat_id,
                "text":       text,
                "parse_mode": "HTML"
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"⚠️ 텔레그램 전송 실패: {e}")
            return False

    # ── 이벤트별 알림 메서드 ───────────────────────────────────────────
    def notify_server_start(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.send(
            f"🟢 <b>스마트팜 서버 시작</b>\n"
            f"⏰ {now}\n"
            f"📡 192.168.0.111:5000",
            force=True
        )

    def notify_water_level_low(self, tank_num: int, level: float, min_level: float):
        emoji = "🚨" if level < min_level * 0.8 else "⚠️"
        self.send(
            f"{emoji} <b>탱크{tank_num} 수위 부족!</b>\n"
            f"📊 현재: <b>{level:.1f}%</b>  (최소: {min_level:.0f}%)\n"
            f"💡 물을 보충해주세요"
        )

    def notify_water_level_high(self, tank_num: int, level: float, max_level: float):
        self.send(
            f"⚠️ <b>탱크{tank_num} 수위 과잉!</b>\n"
            f"📊 현재: <b>{level:.1f}%</b>  (최대: {max_level:.0f}%)\n"
            f"💡 배수를 확인해주세요"
        )

    def notify_irrigation_start(self, zone_id: int, duration: int, trigger: str):
        trigger_map = {"scheduler": "⏰ 스케줄", "auto": "🤖 자동", "manual": "👆 수동"}
        t_str = trigger_map.get(trigger, trigger)
        self.send(
            f"💧 <b>관수 시작</b>\n"
            f"🌿 구역: <b>{zone_id}</b>  |  ⏱ {duration}초\n"
            f"📌 트리거: {t_str}"
        )

    def notify_irrigation_done(self, zone_id: int, duration: int, trigger: str, success: bool):
        if not success:
            self.send(
                f"❌ <b>관수 실패</b> – 구역{zone_id}\n"
                f"⏱ {duration}초 예정  |  📌 {trigger}"
            )
            return
        trigger_map = {"scheduler": "⏰ 스케줄", "auto": "🤖 자동", "manual": "👆 수동"}
        t_str = trigger_map.get(trigger, trigger)
        self.send(
            f"✅ <b>관수 완료</b>\n"
            f"🌿 구역: <b>{zone_id}</b>  |  ⏱ {duration}초\n"
            f"📌 트리거: {t_str}"
        )

    def notify_sensor_error(self, message: str):
        self.send(f"🔴 <b>센서 오류</b>\n{message}")

    def notify_alert(self, alert):
        """AlertManager 콜백용 – Alert 객체를 받아 레벨별 전송"""
        from monitoring.alert_manager import AlertLevel, AlertType
        if alert.level == AlertLevel.INFO:
            return                       # INFO는 텔레그램 전송 안 함
        if alert.alert_type == AlertType.LOW_WATER_LEVEL:
            self.notify_water_level_low(
                tank_num  = alert.tank_num or 1,
                level     = alert.value or 0,
                min_level = 20.0
            )
        elif alert.alert_type == AlertType.HIGH_WATER_LEVEL:
            self.notify_water_level_high(
                tank_num  = alert.tank_num or 1,
                level     = alert.value or 0,
                max_level = 90.0
            )
        elif alert.alert_type == AlertType.SENSOR_ERROR:
            self.notify_sensor_error(alert.message)
        elif alert.alert_type == AlertType.COMMUNICATION_ERROR:
            self.send(f"📡 <b>통신 오류</b>\n{alert.message}")

    # ── Phase 2: 명령어 폴링 ──────────────────────────────────────────
    def start_polling(self, controller=None):
        """명령어 수신 폴링 시작"""
        self._controller = controller
        if self._polling:
            return
        self._polling = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="TelegramPoller"
        )
        self._poll_thread.start()
        print("✅ 텔레그램 폴링 시작")

    def stop_polling(self):
        self._polling = False

    def _poll_loop(self):
        while self._polling:
            try:
                self._process_updates()
            except Exception as e:
                print(f"⚠️ 폴링 오류: {e}")
            time.sleep(3)

    def _process_updates(self):
        url  = TELEGRAM_API.format(token=self.token, method="getUpdates")
        resp = requests.get(url, params={
            "offset":  self._last_update + 1,
            "timeout": 2
        }, timeout=10)
        if resp.status_code != 200:
            return
        data = resp.json()
        for update in data.get("result", []):
            self._last_update = update["update_id"]
            msg = update.get("message", {})
            text = msg.get("text", "").strip()
            cid  = str(msg.get("chat", {}).get("id", ""))
            if cid != self.chat_id:
                continue                 # 다른 chat은 무시
            self._handle_command(text)

    def _handle_command(self, text: str):
        parts = text.split()
        cmd   = parts[0].lower() if parts else ""

        if cmd == "/status":
            self._cmd_status()
        elif cmd == "/history":
            self._cmd_history()
        elif cmd == "/schedules":
            self._cmd_schedules()
        elif cmd.startswith("/irrigate"):
            self._cmd_irrigate(parts)
        elif cmd == "/stop":
            self._cmd_stop()
        elif cmd.startswith("/mute"):
            self._cmd_mute(parts)
        elif cmd == "/unmute":
            self.unmute()
            self.send("🔔 알림 무음 해제됐습니다.")
        elif cmd == "/start" or cmd == "/help":
            self._cmd_help()

    def _cmd_help(self):
        self.send(
            "🌱 <b>스마트팜 봇 명령어</b>\n\n"
            "/status – 현재 상태\n"
            "/history – 오늘 관수 이력\n"
            "/schedules – 스케줄 목록\n"
            "/irrigate <구역> <초> – 즉시 관수\n"
            "  예: /irrigate 1 30\n"
            "/stop – 현재 관수 중단\n"
            "/mute <분> – 알림 무음\n"
            "  예: /mute 120\n"
            "/unmute – 무음 해제",
            force=True
        )

    def _cmd_status(self):
        if not self._controller:
            self.send("⚠️ 컨트롤러 미연결"); return
        try:
            s = self._controller.get_status()
            mode     = s.get("mode", "?")
            irr      = "관수 중 🚿" if s.get("is_irrigating") else "대기 중 💤"
            sched    = "✅ 실행 중" if s.get("is_running") else "❌ 중지"
            now      = datetime.now().strftime("%H:%M:%S")
            self.send(
                f"📊 <b>스마트팜 현재 상태</b>  ({now})\n\n"
                f"🔧 모드: <b>{mode}</b>\n"
                f"💧 관수: {irr}\n"
                f"⏰ 스케줄러: {sched}",
                force=True
            )
        except Exception as e:
            self.send(f"⚠️ 상태 조회 실패: {e}")

    def _cmd_history(self):
        if not self._controller:
            self.send("⚠️ 컨트롤러 미연결"); return
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            history = [
                r for r in self._controller.irrigation_history
                if r.get("start_time", "").startswith(today)
            ]
            if not history:
                self.send(f"📋 오늘({today}) 관수 이력 없음"); return
            lines = [f"📋 <b>오늘 관수 이력</b> ({today})\n"]
            for r in history[-5:]:
                t = r.get("start_time", "")[-8:]
                z = r.get("zone_id", "?")
                d = r.get("duration", "?")
                tr = r.get("trigger", "?")
                lines.append(f"  {t} | 구역{z} | {d}초 | {tr}")
            self.send("\n".join(lines), force=True)
        except Exception as e:
            self.send(f"⚠️ 이력 조회 실패: {e}")

    def _cmd_schedules(self):
        try:
            import json as _json
            with open("/home/pi/smart_farm/config/schedules.json") as f:
                data = _json.load(f)
            schedules = data.get("schedules", [])
            if not schedules:
                self.send("📅 등록된 스케줄 없음"); return
            lines = ["📅 <b>스케줄 목록</b>\n"]
            day_names = ["월","화","수","목","금","토","일"]
            for s in schedules:
                en   = "✅" if s.get("enabled") else "❌"
                sid  = s.get("id")
                z    = s.get("zone_id")
                t    = s.get("start_time", s.get("start_date", "-"))
                d    = s.get("duration")
                typ  = s.get("type", "schedule")
                if typ == "routine":
                    interval = s.get("interval_days", "?")
                    lines.append(f"{en} ID{sid} | 구역{z} | {t} | {d}초 | {interval}일마다")
                else:
                    days = s.get("days", [])
                    day_str = "".join(day_names[i] for i in days) if days else "매일"
                    lines.append(f"{en} ID{sid} | 구역{z} | {t} | {d}초 | {day_str}")
            self.send("\n".join(lines), force=True)
        except Exception as e:
            self.send(f"⚠️ 스케줄 조회 실패: {e}")

    def _cmd_irrigate(self, parts):
        if not self._controller:
            self.send("⚠️ 컨트롤러 미연결"); return
        try:
            zone_id  = int(parts[1]) if len(parts) > 1 else 1
            duration = int(parts[2]) if len(parts) > 2 else 30
            self.send(f"💧 구역{zone_id} {duration}초 관수 시작합니다...")
            ok, msg = self._controller.start_zone_irrigation(
                zone_id=zone_id, duration=duration, trigger="telegram"
            )
            if not ok:
                self.send(f"❌ 관수 실패: {msg}")
        except (ValueError, IndexError):
            self.send("❌ 사용법: /irrigate <구역번호> <초>\n예: /irrigate 1 30")
        except Exception as e:
            self.send(f"⚠️ 오류: {e}")

    def _cmd_stop(self):
        if not self._controller:
            self.send("⚠️ 컨트롤러 미연결"); return
        try:
            if self._controller.is_irrigating:
                self._controller.stop_irrigation()
                self.send("🛑 관수 중단됐습니다.")
            else:
                self.send("💤 현재 관수 중이 아닙니다.")
        except Exception as e:
            self.send(f"⚠️ 오류: {e}")

    def _cmd_mute(self, parts):
        try:
            minutes = int(parts[1]) if len(parts) > 1 else 60
            self.mute(minutes * 60)
            self.send(f"🔇 {minutes}분 동안 알림이 무음됩니다.", force=True)
        except (ValueError, IndexError):
            self.send("❌ 사용법: /mute <분>\n예: /mute 120")
