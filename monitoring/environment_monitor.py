"""
environment_monitor.py (Stage 11 – SQLite 병행 저장)
기존 CSV 저장 유지 + db_manager 주입 시 SQLite 동시 기록

변경점:
  - __init__에 db_manager 파라미터 추가
  - _log_air()   → db_manager.insert_air_readings_bulk() 추가 호출
  - _log_weather() → db_manager.insert_weather_reading() 추가 호출

작성자: spinoza-lab
날짜:   2026-03-17
"""

import csv
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

_BASE_DIR = Path(__file__).resolve().parent.parent

AIR_LOG_DIR     = str(_BASE_DIR / 'data' / 'air_sensor_logs')
WEATHER_LOG_DIR = str(_BASE_DIR / 'data' / 'weather_logs')

AIR_INTERVAL     = 60   # 초
WEATHER_INTERVAL = 16   # 초
MAX_HISTORY      = 100  # 메모리 버퍼 크기


class EnvironmentMonitor:
    """
    환경 모니터링 스레드 매니저 (Stage 11: SQLite 지원)

    사용법:
        monitor = EnvironmentMonitor(air_mgr, ws_rdr, db_manager=db)
        monitor.start()
        data = monitor.get_environment_status()
        monitor.stop()
    """

    def __init__(self, air_sensor_manager=None,
                 weather_station_reader=None,
                 db_manager=None):
        self.air_mgr     = air_sensor_manager
        self.weather_rdr = weather_station_reader
        self.db_manager  = db_manager          # Stage 11 추가

        self._stop_event = threading.Event()
        self._air_thread     = None
        self._weather_thread = None
        self._lock = threading.Lock()

        # 메모리 히스토리
        self.air_history:     List[dict] = []
        self.weather_history: List[dict] = []

        # 최신 상태 캐시
        self._latest_air:     List[dict] = []
        self._latest_weather: Optional[dict] = None

        # 로그 디렉터리 생성
        os.makedirs(AIR_LOG_DIR,     exist_ok=True)
        os.makedirs(WEATHER_LOG_DIR, exist_ok=True)

        _db_info = "SQLite + CSV" if db_manager else "CSV only"
        print(f"✅ EnvironmentMonitor 초기화 ({_db_info})")

    # ── 스레드 제어 ───────────────────────────────────────────────────────────

    def start(self):
        self._stop_event.clear()
        self._air_thread = threading.Thread(
            target=self._air_loop, daemon=True, name="AirMonitor")
        self._weather_thread = threading.Thread(
            target=self._weather_loop, daemon=True, name="WeatherMonitor")
        self._air_thread.start()
        self._weather_thread.start()
        print("▶️  EnvironmentMonitor 스레드 시작 (Air + Weather)")

    def stop(self):
        self._stop_event.set()
        if self._air_thread:
            self._air_thread.join(timeout=5)
        if self._weather_thread:
            self._weather_thread.join(timeout=5)
        print("⏹️  EnvironmentMonitor 스레드 정지")

    # ── 폴링 루프 ─────────────────────────────────────────────────────────────

    def _air_loop(self):
        while not self._stop_event.is_set():
            try:
                if self.air_mgr:
                    results = self.air_mgr.read_all()
                    if results:
                        self._log_air(results)
                        with self._lock:
                            self._latest_air = results
                            self.air_history.extend(results)
                            if len(self.air_history) > MAX_HISTORY:
                                self.air_history = self.air_history[-MAX_HISTORY:]
            except Exception as e:
                print(f"❌ [AirMonitor] 루프 오류: {e}")
            self._stop_event.wait(AIR_INTERVAL)

    def _weather_loop(self):
        while not self._stop_event.is_set():
            try:
                if self.weather_rdr:
                    data = self.weather_rdr.read()
                    if data:
                        self._log_weather(data)
                        with self._lock:
                            self._latest_weather = data
                            self.weather_history.append(data)
                            if len(self.weather_history) > MAX_HISTORY:
                                self.weather_history = self.weather_history[-MAX_HISTORY:]
            except Exception as e:
                print(f"❌ [WeatherMonitor] 루프 오류: {e}")
            self._stop_event.wait(WEATHER_INTERVAL)

    # ── CSV 저장 ──────────────────────────────────────────────────────────────

    def _log_air(self, results: list):
        """SHT30 데이터 CSV + SQLite 저장"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        fpath    = os.path.join(AIR_LOG_DIR, f"air_{date_str}.csv")
        write_header = not os.path.exists(fpath) or os.path.getsize(fpath) == 0
        try:
            with open(fpath, 'a', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                if write_header:
                    w.writerow(['timestamp', 'sensor_id', 'zone_id',
                                'name', 'temperature', 'humidity', 'valid'])
                for r in results:
                    ts = r.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    w.writerow([ts, r.get('sensor_id', ''), r.get('zone_id', ''),
                                r.get('name', ''), r.get('temperature', ''),
                                r.get('humidity', ''), r.get('valid', True)])
        except Exception as e:
            print(f"❌ [AirMonitor] CSV 저장 실패: {e}")

        # SQLite 저장 (Stage 11)
        if self.db_manager:
            try:
                records = []
                for r in results:
                    ts = r.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    records.append({
                        'timestamp':   ts,
                        'sensor_id':   r.get('sensor_id', ''),
                        'zone_id':     r.get('zone_id', 0),
                        'name':        r.get('name', ''),
                        'temperature': r.get('temperature', 0),
                        'humidity':    r.get('humidity', 0),
                        'valid':       r.get('valid', True),
                    })
                self.db_manager.insert_air_readings_bulk(records)
            except Exception as e:
                print(f"❌ [AirMonitor] SQLite 저장 실패: {e}")

    def _log_weather(self, data: dict):
        """WH65LP 데이터 CSV + SQLite 저장"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        fpath    = os.path.join(WEATHER_LOG_DIR, f"weather_{date_str}.csv")
        write_header = not os.path.exists(fpath) or os.path.getsize(fpath) == 0
        try:
            with open(fpath, 'a', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                if write_header:
                    w.writerow(['timestamp', 'temperature', 'humidity',
                                'wind_speed', 'gust_speed', 'wind_dir', 'wind_dir_str',
                                'rainfall', 'uv_index', 'illuminance',
                                'pressure', 'battery_ok'])
                ts = data.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                w.writerow([ts, data.get('temperature'), data.get('humidity'),
                             data.get('wind_speed'), data.get('gust_speed'),
                             data.get('wind_dir'), data.get('wind_dir_str'),
                             data.get('rainfall'), data.get('uv_index'),
                             data.get('illuminance'), data.get('pressure'),
                             data.get('battery_ok')])
        except Exception as e:
            print(f"❌ [WeatherMonitor] CSV 저장 실패: {e}")

        # SQLite 저장 (Stage 11)
        if self.db_manager:
            try:
                save_data = dict(data)
                if 'timestamp' not in save_data or not save_data['timestamp']:
                    save_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.db_manager.insert_weather_reading(save_data)
            except Exception as e:
                print(f"❌ [WeatherMonitor] SQLite 저장 실패: {e}")

    # ── 상태 조회 API ─────────────────────────────────────────────────────────

    def get_environment_status(self) -> dict:
        with self._lock:
            return {
                'air':         list(self._latest_air),
                'weather':     dict(self._latest_weather) if self._latest_weather else None,
                'running':     not self._stop_event.is_set(),
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

    def get_air_history(self, limit: int = 100) -> list:
        with self._lock:
            return list(self.air_history[-limit:])

    def get_weather_history(self, limit: int = 100) -> list:
        with self._lock:
            return list(self.weather_history[-limit:])
