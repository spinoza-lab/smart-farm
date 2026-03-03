"""
TelegramNotifier – 스마트팜 텔레그램 알림 모듈
Phase 1: 자동 알림 (수위, 관수 시작/완료, 서버 시작)
Phase 2: 인라인 키보드 버튼 봇 (한글 버튼 메뉴)
"""

import threading
import time
import requests
import json
import os
from datetime import datetime

CONFIG_PATH  = "/home/pi/smart_farm/config/notifications.json"
SCHED_PATH   = "/home/pi/smart_farm/config/schedules.json"
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# ─────────────────────────────────────────────────────────────────────
# 인라인 키보드 레이아웃 상수
# ─────────────────────────────────────────────────────────────────────
MAIN_MENU = {
    "inline_keyboard": [
        [
            {"text": "📊 현재 상태",   "callback_data": "cmd:status"},
            {"text": "📋 오늘 이력",   "callback_data": "cmd:history"}
        ],
        [
            {"text": "📅 스케줄 목록", "callback_data": "cmd:schedules"},
            {"text": "🔇 1시간 무음",  "callback_data": "cmd:mute60"}
        ],
        [
            {"text": "💧 관수 시작",   "callback_data": "cmd:irrigate"},
            {"text": "🛑 관수 중단",   "callback_data": "cmd:stop"}
        ],
        [
            {"text": "🔔 무음 해제",   "callback_data": "cmd:unmute"}
        ]
    ]
}

ZONE_MENU = {
    "inline_keyboard": [
        [
            {"text": "구역 1",  "callback_data": "zone:1"},
            {"text": "구역 2",  "callback_data": "zone:2"},
            {"text": "구역 3",  "callback_data": "zone:3"}
        ],
        [
            {"text": "구역 4",  "callback_data": "zone:4"},
            {"text": "구역 5",  "callback_data": "zone:5"},
            {"text": "구역 6",  "callback_data": "zone:6"}
        ],
        [
            {"text": "구역 7",  "callback_data": "zone:7"},
            {"text": "구역 8",  "callback_data": "zone:8"},
            {"text": "구역 9",  "callback_data": "zone:9"}
        ],
        [
            {"text": "구역 10", "callback_data": "zone:10"},
            {"text": "구역 11", "callback_data": "zone:11"},
            {"text": "구역 12", "callback_data": "zone:12"}
        ],
        [
            {"text": "❌ 취소", "callback_data": "cmd:cancel"}
        ]
    ]
}


def duration_menu(zone_id: int) -> dict:
    """구역별 관수 시간 선택 메뉴"""
    return {
        "inline_keyboard": [
            [
                {"text": "30초",   "callback_data": f"dur:{zone_id}:30"},
                {"text": "1분",    "callback_data": f"dur:{zone_id}:60"},
                {"text": "2분",    "callback_data": f"dur:{zone_id}:120"}
            ],
            [
                {"text": "5분",    "callback_data": f"dur:{zone_id}:300"},
                {"text": "10분",   "callback_data": f"dur:{zone_id}:600"},
                {"text": "20분",   "callback_data": f"dur:{zone_id}:1200"}
            ],
            [
                {"text": "❌ 취소", "callback_data": "cmd:cancel"}
            ]
        ]
    }


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
        print(f"[Telegram] notifications.json 저장 실패: {e}")


class TelegramNotifier:
    """텔레그램 알림 + 인라인 키보드 봇"""

    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = str(chat_id)
        self.enabled = True

        self._mute_until = None          # float(time.time()) or None
        self._lock       = threading.Lock()

        # 폴링 스레드
        self._polling     = False
        self._poll_thread = None
        self._last_update = 0
        self._controller  = None         # AutoIrrigationController 참조

        print(f"[Telegram] TelegramNotifier 초기화 완료 (chat_id={self.chat_id})")

    # ── 무음 제어 ──────────────────────────────────────────────────────
    def mute(self, seconds: int):
        with self._lock:
            self._mute_until = time.time() + seconds
        print(f"[Telegram] 무음 설정: {seconds}초")

    def unmute(self):
        with self._lock:
            self._mute_until = None
        print("[Telegram] 무음 해제")

    def _is_muted(self) -> bool:
        with self._lock:
            if self._mute_until is None:
                return False
            if time.time() < self._mute_until:
                return True
            self._mute_until = None
            return False

    def _mute_remaining(self) -> str:
        """무음 남은 시간 문자열 반환"""
        with self._lock:
            if self._mute_until is None:
                return ""
            remaining = self._mute_until - time.time()
            if remaining <= 0:
                self._mute_until = None
                return ""
            m = int(remaining // 60)
            s = int(remaining % 60)
            if m > 0:
                return f"{m}분 {s}초"
            return f"{s}초"

    # ── 메시지 전송 ────────────────────────────────────────────────────
    def send(self, text: str, force: bool = False, buttons: dict = None) -> dict:
        """텔레그램 메시지 전송. 성공 시 응답 JSON 반환."""
        if not self.enabled:
            return {}
        if not force and self._is_muted():
            return {}
        try:
            url     = TELEGRAM_API.format(token=self.token, method="sendMessage")
            payload = {
                "chat_id":    self.chat_id,
                "text":       text,
                "parse_mode": "HTML"
            }
            if buttons:
                payload["reply_markup"] = buttons
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
            print(f"[Telegram] 전송 실패: {e}")
            return {}

    def edit_message(self, chat_id: str, message_id: int,
                     text: str, buttons: dict = None) -> bool:
        """기존 메시지 내용 + 버튼 수정 (editMessageText)"""
        try:
            url     = TELEGRAM_API.format(token=self.token, method="editMessageText")
            payload = {
                "chat_id":    str(chat_id),
                "message_id": message_id,
                "text":       text,
                "parse_mode": "HTML"
            }
            if buttons:
                payload["reply_markup"] = buttons
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Telegram] edit_message 실패: {e}")
            return False

    def _answer_callback(self, callback_query_id: str, text: str = ""):
        """callback_query 응답 (로딩 스피너 해제)"""
        try:
            url = TELEGRAM_API.format(token=self.token, method="answerCallbackQuery")
            requests.post(url, json={
                "callback_query_id": callback_query_id,
                "text": text
            }, timeout=5)
        except Exception:
            pass

    # ── 이벤트별 자동 알림 메서드 ─────────────────────────────────────
    def _alert_enabled(self, key: str) -> bool:
        """notifications.json alerts.<key>가 True인지 확인. 읽기 실패 시 True(전송)."""
        try:
            return _load_config().get("alerts", {}).get(key, True)
        except Exception:
            return True

    def notify_server_start(self):
        if not self._alert_enabled("server_start"):
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.send(
            "🟢 <b>스마트팜 서버 시작</b>\n"
            f"⏰ {now}\n"
            "📡 192.168.0.111:5000",
            force=True,
            buttons=MAIN_MENU
        )

    def notify_water_level_low(self, tank_num: int, level: float, min_level: float):
        if not self._alert_enabled("water_level_low"):
            return
        emoji = "🚨" if level < min_level * 0.8 else "⚠️"
        self.send(
            f"{emoji} <b>탱크{tank_num} 수위 부족!</b>\n"
            f"📊 현재: <b>{level:.1f}%</b>  (최소: {min_level:.0f}%)\n"
            "💡 물을 보충해주세요"
        )

    def notify_water_level_high(self, tank_num: int, level: float, max_level: float):
        if not self._alert_enabled("water_level_high"):
            return
        self.send(
            f"⚠️ <b>탱크{tank_num} 수위 과잉!</b>\n"
            f"📊 현재: <b>{level:.1f}%</b>  (최대: {max_level:.0f}%)\n"
            "💡 배수를 확인해주세요"
        )

    def notify_irrigation_start(self, zone_id: int, duration: int, trigger: str):
        if not self._alert_enabled("irrigation_start"):
            return
        trigger_map = {"scheduler": "⏰ 스케줄", "auto": "🤖 자동",
                       "manual": "👆 수동", "telegram": "📱 텔레그램"}
        t_str = trigger_map.get(trigger, trigger)
        self.send(
            "💧 <b>관수 시작</b>\n"
            f"🌿 구역: <b>{zone_id}</b>  |  ⏱ {duration}초\n"
            f"📌 트리거: {t_str}"
        )

    def notify_irrigation_done(self, zone_id: int, duration: int,
                                trigger: str, success: bool):
        if not success:
            # 중단(aborted)은 irrigation_done 토글에 관계없이 항상 전송
            self.send(
                f"🛑 <b>관수 중단됨</b> – 구역{zone_id}\n"
                f"⏱ {duration}초 경과  |  📌 {trigger}"
            )
            return
        if not self._alert_enabled("irrigation_done"):
            return
        trigger_map = {"scheduler": "⏰ 스케줄", "auto": "🤖 자동",
                       "manual": "👆 수동", "telegram": "📱 텔레그램"}
        t_str = trigger_map.get(trigger, trigger)
        self.send(
            "✅ <b>관수 완료</b>\n"
            f"🌿 구역: <b>{zone_id}</b>  |  ⏱ {duration}초\n"
            f"📌 트리거: {t_str}"
        )

    def notify_sensor_error(self, message: str):
        if not self._alert_enabled("sensor_error"):
            return
        self.send(f"🔴 <b>센서 오류</b>\n{message}")

    def notify_alert(self, alert):
        """AlertManager 콜백용 – Alert 객체를 받아 레벨별 전송"""
        try:
            from monitoring.alert_manager import AlertLevel, AlertType
        except ImportError:
            return
        if alert.level == AlertLevel.INFO:
            return
        if alert.alert_type == AlertType.LOW_WATER_LEVEL:
            _th = _load_config().get("thresholds", {})
            _tnum = alert.tank_num or 1
            _min = float(_th.get(f"tank{_tnum}_min", 20.0))
            self.notify_water_level_low(
                tank_num=_tnum,
                level=alert.value or 0,
                min_level=_min
            )
        elif alert.alert_type == AlertType.HIGH_WATER_LEVEL:
            _th = _load_config().get("thresholds", {})
            _tnum = alert.tank_num or 1
            _max = float(_th.get(f"tank{_tnum}_max", 90.0))
            self.notify_water_level_high(
                tank_num=_tnum,
                level=alert.value or 0,
                max_level=_max
            )
        elif alert.alert_type == AlertType.SENSOR_ERROR:
            self.notify_sensor_error(alert.message)
        elif alert.alert_type == AlertType.COMMUNICATION_ERROR:
            self.send(f"📡 <b>통신 오류</b>\n{alert.message}")

    # ── 폴링 ──────────────────────────────────────────────────────────
    def start_polling(self, controller=None):
        """인라인 키보드 콜백 수신 폴링 시작"""
        self._controller = controller
        if self._polling:
            return
        self._polling = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="TelegramPoller"
        )
        self._poll_thread.start()
        print("[Telegram] 폴링 시작")

    def stop_polling(self):
        self._polling = False

    def get_status(self) -> dict:
        """봇 상태 딕셔너리 반환 (app.py /api/notifications/status 용)"""
        return {
            "polling":        self._polling,
            "is_muted":       self._is_muted(),
            "mute_remaining": self._mute_remaining(),
            "mute_until":     self._mute_until,   # Unix timestamp (float or None)
        }

        print("[Telegram] 폴링 중지")

    def _poll_loop(self):
        while self._polling:
            try:
                self._poll_updates()
            except Exception as e:
                print(f"[Telegram] 폴링 오류: {e}")
            time.sleep(3)

    def _poll_updates(self):
        url  = TELEGRAM_API.format(token=self.token, method="getUpdates")
        resp = requests.get(url, params={
            "offset":  self._last_update + 1,
            "timeout": 2
        }, timeout=10)
        if resp.status_code != 200:
            return

        for update in resp.json().get("result", []):
            self._last_update = update["update_id"]

            # ── callback_query (버튼 클릭) ─────────────────────────
            if "callback_query" in update:
                cq      = update["callback_query"]
                cq_id   = cq["id"]
                cq_chat = str(cq["message"]["chat"]["id"])
                cq_mid  = cq["message"]["message_id"]
                data    = cq.get("data", "")

                if cq_chat != self.chat_id:
                    continue

                self._answer_callback(cq_id)

                # ── 메인 메뉴 명령 ──
                if data == "cmd:status":
                    self._handle_status(cq_chat, cq_mid)

                elif data == "cmd:history":
                    self._handle_history(cq_chat, cq_mid)

                elif data == "cmd:schedules":
                    self._handle_schedules(cq_chat, cq_mid)

                elif data == "cmd:irrigate":
                    self.edit_message(cq_chat, cq_mid,
                                      "💧 <b>관수 구역 선택</b>\n구역 번호를 선택하세요:",
                                      buttons=ZONE_MENU)

                elif data == "cmd:stop":
                    self._handle_stop(cq_chat, cq_mid)

                elif data == "cmd:mute60":
                    self.mute(3600)
                    self.edit_message(
                        cq_chat, cq_mid,
                        "🔇 <b>1시간 무음 설정됨</b>\n자동 알림이 1시간 동안 차단됩니다.",
                        buttons=MAIN_MENU
                    )

                elif data == "cmd:unmute":
                    self.unmute()
                    self.edit_message(
                        cq_chat, cq_mid,
                        "🔔 <b>무음 해제됨</b>\n알림이 정상 수신됩니다.",
                        buttons=MAIN_MENU
                    )

                elif data == "cmd:cancel":
                    self.edit_message(
                        cq_chat, cq_mid,
                        "🌱 <b>스마트팜 제어 메뉴</b>\n원하는 기능을 선택하세요.",
                        buttons=MAIN_MENU
                    )

                # ── 구역 선택 ──
                elif data.startswith("zone:"):
                    zone_id = int(data.split(":")[1])
                    self.edit_message(
                        cq_chat, cq_mid,
                        f"⏱ <b>구역 {zone_id} 관수 시간 선택</b>",
                        buttons=duration_menu(zone_id)
                    )

                # ── 시간 선택 → 관수 실행 ──
                elif data.startswith("dur:"):
                    _, zone_str, dur_str = data.split(":")
                    self._handle_irrigate_zone(
                        int(zone_str), int(dur_str), cq_chat, cq_mid
                    )

                continue  # callback_query 처리 완료

            # ── 일반 메시지 (텍스트 명령) ──────────────────────────
            msg  = update.get("message", {})
            text = msg.get("text", "").strip()
            cid  = str(msg.get("chat", {}).get("id", ""))
            if not text or cid != self.chat_id:
                continue

            cmd = text.split()[0].lower()
            if cmd in ("/start", "/menu", "/help"):
                self.send(
                    "🌱 <b>스마트팜 제어 메뉴</b>\n원하는 기능을 선택하세요.",
                    force=True,
                    buttons=MAIN_MENU
                )

    # ── 버튼 핸들러 ───────────────────────────────────────────────────
    def _handle_status(self, chat_id: str, message_id: int):
        try:
            if self._controller:
                s        = self._controller.get_status()
                mode     = s.get("mode") or s.get("irrigation_mode") or "알 수 없음"
                is_irr   = s.get("is_irrigating", False)
                is_run   = s.get("is_running", False)
            else:
                # controller 없으면 API fallback
                r    = requests.get("http://127.0.0.1:5000/api/irrigation/status", timeout=3)
                d    = r.json()
                mode = d.get("mode") or d.get("irrigation_mode") or "알 수 없음"
                is_irr = d.get("is_irrigating", False)
                is_run = d.get("is_running", False)

            irr_str  = "🚿 관수 중" if is_irr else "💤 대기 중"
            run_str  = "✅ 실행 중" if is_run else "⛔ 중지"
            mute_str = ""
            rem      = self._mute_remaining()
            if rem:
                mute_str = f"\n🔇 무음: {rem} 남음"

            now = datetime.now().strftime("%H:%M:%S")
            self.edit_message(
                chat_id, message_id,
                f"📊 <b>스마트팜 현재 상태</b>  ({now})\n\n"
                f"🔧 모드: <b>{mode}</b>\n"
                f"💧 관수: {irr_str}\n"
                f"⏰ 스케줄러: {run_str}{mute_str}",
                buttons=MAIN_MENU
            )
        except Exception as e:
            self.edit_message(chat_id, message_id,
                              f"⚠️ 상태 조회 실패: {e}", buttons=MAIN_MENU)

    def _handle_history(self, chat_id: str, message_id: int):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            if self._controller:
                history = [
                    r for r in (self._controller.irrigation_history or [])
                    if r.get("start_time", "").startswith(today)
                ]
            else:
                r       = requests.get("http://127.0.0.1:5000/api/irrigation/history", timeout=3)
                history = [
                    x for x in r.json().get("history", [])
                    if x.get("start_time", "").startswith(today)
                ]

            if not history:
                self.edit_message(chat_id, message_id,
                                  f"📋 오늘({today}) 관수 이력이 없습니다.",
                                  buttons=MAIN_MENU)
                return

            lines = [f"📋 <b>오늘 관수 이력</b> ({today})\n"]
            for rec in history[-8:]:
                t  = rec.get("start_time", "")[-8:]
                z  = rec.get("zone_id", "?")
                d  = rec.get("duration", "?")
                tr = rec.get("trigger", "?")
                lines.append(f"  {t} | 구역{z} | {d}초 | {tr}")
            self.edit_message(chat_id, message_id,
                              "\n".join(lines), buttons=MAIN_MENU)
        except Exception as e:
            self.edit_message(chat_id, message_id,
                              f"⚠️ 이력 조회 실패: {e}", buttons=MAIN_MENU)

    def _handle_schedules(self, chat_id: str, message_id: int):
        try:
            with open(SCHED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            # schedules.json 구조: {"schedules": [...]} 또는 리스트 직접
            if isinstance(data, dict):
                items = data.get("schedules", [])
            elif isinstance(data, list):
                items = data
            else:
                items = []

            if not items:
                self.edit_message(chat_id, message_id,
                                  "📅 등록된 스케줄이 없습니다.", buttons=MAIN_MENU)
                return

            day_names = ["월", "화", "수", "목", "금", "토", "일"]
            lines     = ["📅 <b>스케줄 목록</b>\n"]
            for s in items:
                en   = "✅" if s.get("enabled") else "❌"
                sid  = s.get("id", "?")
                z    = s.get("zone_id", "?")
                t    = s.get("start_time", s.get("start_date", "-"))
                d    = s.get("duration", "?")
                typ  = s.get("type", "schedule")
                if typ == "routine":
                    interval = s.get("interval_days", "?")
                    lines.append(f"{en} ID{sid} | 구역{z} | {t} | {d}초 | {interval}일마다")
                else:
                    days    = s.get("days", [])
                    day_str = "".join(day_names[i] for i in days if 0 <= i <= 6) if days else "매일"
                    lines.append(f"{en} ID{sid} | 구역{z} | {t} | {d}초 | {day_str}")

            self.edit_message(chat_id, message_id,
                              "\n".join(lines), buttons=MAIN_MENU)
        except Exception as e:
            self.edit_message(chat_id, message_id,
                              f"⚠️ 스케줄 조회 실패: {e}", buttons=MAIN_MENU)

    def _handle_stop(self, chat_id: str, message_id: int):
        try:
            if not self._controller:
                self.edit_message(chat_id, message_id,
                                  "⚠️ 컨트롤러 미연결", buttons=MAIN_MENU)
                return
            if getattr(self._controller, "is_irrigating", False):
                # stop_irrigation 메서드가 있는지 확인 후 호출
                stop_fn = getattr(self._controller, "stop_irrigation", None)
                if callable(stop_fn):
                    stop_fn()
                else:
                    self._controller.is_irrigating = False
                self.edit_message(chat_id, message_id,
                                  "🛑 <b>관수 중단 요청을 보냈습니다.</b>\n"
                                  "진행 중인 단계 완료 후 중단됩니다.", buttons=MAIN_MENU)
            else:
                self.edit_message(chat_id, message_id,
                                  "💤 현재 관수 중이 아닙니다.", buttons=MAIN_MENU)
        except Exception as e:
            self.edit_message(chat_id, message_id,
                              f"⚠️ 오류: {e}", buttons=MAIN_MENU)

    def _handle_irrigate_zone(self, zone_id: int, duration: int,
                               chat_id: str, message_id: int):
        """관수 요청을 즉시 수락하고 실제 관수는 백그라운드 스레드에서 실행.
        start_zone_irrigation()이 블로킹 함수이므로 폴링 스레드를 점유하지 않도록 분리."""
        if not self._controller:
            self.edit_message(chat_id, message_id,
                              "⚠️ 컨트롤러 미연결", buttons=MAIN_MENU)
            return

        # ① 즉시 메인 메뉴로 복귀 → 폴링 스레드가 바로 다음 업데이트를 처리할 수 있음
        dur_str = f"{duration // 60}분" if duration >= 60 else f"{duration}초"
        self.edit_message(
            chat_id, message_id,
            f"💧 <b>관수 요청 접수</b>\n"
            f"🌿 구역 {zone_id}  |  ⏱ {dur_str}\n"
            f"잠시 후 시작 알림이 전송됩니다.",
            buttons=MAIN_MENU
        )

        # ② 실제 관수는 별도 스레드에서 실행 (블로킹 time.sleep이 있어도 무관)
        def _run():
            try:
                ok, msg = self._controller.start_zone_irrigation(
                    zone_id=zone_id, duration=duration, trigger="telegram"
                )
                if not ok:
                    # "중단됨" → notify_irrigation_done이 이미 메시지 전송
                    # "이미 관수 중" 등 실제 실패만 별도 안내
                    if "중단됨" not in msg:
                        self.send(f"❌ <b>관수 시작 실패</b>\n🌿 구역 {zone_id}\n{msg}",
                                  force=True)
            except Exception as e:
                self.send(f"⚠️ 관수 오류: {e}", force=True)

        threading.Thread(target=_run, daemon=True, name=f"Irrigate-Z{zone_id}").start()
