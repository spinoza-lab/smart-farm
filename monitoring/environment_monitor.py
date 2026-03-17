#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
environment_monitor.py — 환경 모니터링 백그라운드 스레드
- SHT30 대기 온습도: 60초 간격 읽기
- WH65LP 기상 관측소: 16초 간격 폴링
- CSV 로그: data/air_sensor_logs/air_YYYY-MM-DD.csv
           data/weather_logs/weather_YYYY-MM-DD.csv
"""

import os
import csv
import time
import logging
import threading
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)

BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIR_LOG_DIR     = os.path.join(BASE_DIR, 'data', 'air_sensor_logs')
WEATHER_LOG_DIR = os.path.join(BASE_DIR, 'data', 'weather_logs')

AIR_INTERVAL     = 60   # SHT30 읽기 간격 (초)
WEATHER_INTERVAL = 16   # WH65LP 폴링 간격 (초)
MAX_HISTORY      = 100  # 메모리 히스토리 최대 개수


class EnvironmentMonitor:
    """
    환경 모니터링 스레드 매니저

    사용법:
        monitor = EnvironmentMonitor(air_mgr, ws_rdr)
        monitor.start()
        ...
        data = monitor.get_environment_status()
        monitor.stop()
    """

    def __init__(self, air_sensor_manager=None, weather_station_reader=None):
        self.air_mgr     = air_sensor_manager
        self.weather_rdr = weather_station_reader

        # 현재 측정값
        self.air_data:     List[dict] = []
        self.weather_data: Optional[dict] = None

        # 히스토리 (메모리, 최근 MAX_HISTORY개)
        self.air_history:     List[dict] = []
        self.weather_history: List[dict] = []

        self._running        = False
        self._air_thread     = None
        self._weather_thread = None
        self._lock           = threading.Lock()

        # 로그 디렉토리 생성
        os.makedirs(AIR_LOG_DIR,     exist_ok=True)
        os.makedirs(WEATHER_LOG_DIR, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────
    # 시작 / 정지
    # ──────────────────────────────────────────────────────────────────
    def start(self):
        if self._running:
            logger.warning("[EnvMonitor] 이미 실행 중입니다.")
            return

        self._running = True
        logger.info("[EnvMonitor] 환경 모니터링 시작")

        if self.air_mgr:
            ok = self.air_mgr.initialize()
            if ok:
                self._air_thread = threading.Thread(
                    target=self._air_loop,
                    name="AirSensorThread",
                    daemon=True
                )
                self._air_thread.start()
                logger.info(f"[EnvMonitor] SHT30 스레드 시작 (간격: {AIR_INTERVAL}s)")
            else:
                logger.error("[EnvMonitor] SHT30 초기화 실패 — 스레드 시작 안함")

        if self.weather_rdr:
            ok = self.weather_rdr.initialize()
            if ok:
                self._weather_thread = threading.Thread(
                    target=self._weather_loop,
                    name="WeatherStationThread",
                    daemon=True
                )
                self._weather_thread.start()
                logger.info(f"[EnvMonitor] WH65LP 스레드 시작 (간격: {WEATHER_INTERVAL}s)")
            else:
                logger.error("[EnvMonitor] WH65LP 초기화 실패 — 스레드 시작 안함")

    def stop(self):
        self._running = False
        if self.air_mgr:
            try:
                self.air_mgr.close()
            except Exception as e:
                logger.warning(f"[EnvMonitor] SHT30 닫기 오류: {e}")
        if self.weather_rdr:
            try:
                self.weather_rdr.close()
            except Exception as e:
                logger.warning(f"[EnvMonitor] WH65LP 닫기 오류: {e}")
        logger.info("[EnvMonitor] 환경 모니터링 정지")

    # ──────────────────────────────────────────────────────────────────
    # SHT30 루프
    # ──────────────────────────────────────────────────────────────────
    def _air_loop(self):
        logger.debug("[EnvMonitor] SHT30 루프 진입")
        while self._running:
            try:
                results = self.air_mgr.read_all()
                with self._lock:
                    self.air_data = results
                    snapshot = {
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'sensors':   results
                    }
                    self.air_history.append(snapshot)
                    if len(self.air_history) > MAX_HISTORY:
                        self.air_history.pop(0)

                self._log_air(results)

                valid_cnt = sum(1 for r in results if r.get('valid'))
                logger.debug(
                    f"[EnvMonitor] SHT30 완료: {valid_cnt}/{len(results)} 유효"
                )
            except Exception as e:
                logger.error(f"[EnvMonitor] SHT30 루프 오류: {e}")

            # 1초 단위 대기 → 빠른 정지 반응
            for _ in range(AIR_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)

    # ──────────────────────────────────────────────────────────────────
    # WH65LP 루프
    # ──────────────────────────────────────────────────────────────────
    def _weather_loop(self):
        logger.debug("[EnvMonitor] WH65LP 루프 진입")
        while self._running:
            try:
                data = self.weather_rdr.read()
                if data and data.get('valid'):
                    with self._lock:
                        self.weather_data = data
                        self.weather_history.append(data)
                        if len(self.weather_history) > MAX_HISTORY:
                            self.weather_history.pop(0)
                    self._log_weather(data)
                    logger.debug(
                        f"[EnvMonitor] WH65LP: "
                        f"{data['temperature']}°C / {data['humidity']}% / "
                        f"풍속 {data['wind_speed']}m/s"
                    )
            except Exception as e:
                logger.error(f"[EnvMonitor] WH65LP 루프 오류: {e}")

            for _ in range(WEATHER_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)

    # ──────────────────────────────────────────────────────────────────
    # CSV 로그
    # ──────────────────────────────────────────────────────────────────
    def _log_air(self, results: list):
        today    = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(AIR_LOG_DIR, f'air_{today}.csv')
        new_file = not os.path.exists(log_file)
        try:
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow([
                        'timestamp', 'sensor_id', 'zone_id',
                        'name', 'temperature', 'humidity', 'valid'
                    ])
                ts = time.strftime('%Y-%m-%d %H:%M:%S')
                for r in results:
                    w.writerow([
                        ts,
                        r.get('sensor_id', ''),
                        r.get('zone_id', ''),
                        r.get('name', ''),
                        r.get('temperature', ''),
                        r.get('humidity', ''),
                        r.get('valid', False)
                    ])
        except Exception as e:
            logger.warning(f"[EnvMonitor] 대기 CSV 기록 실패: {e}")

    def _log_weather(self, data: dict):
        today    = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(WEATHER_LOG_DIR, f'weather_{today}.csv')
        new_file = not os.path.exists(log_file)
        try:
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow([
                        'timestamp', 'temperature', 'humidity',
                        'wind_speed', 'gust_speed', 'wind_dir', 'wind_dir_str',
                        'rainfall', 'uv_index', 'illuminance',
                        'pressure', 'battery_ok'
                    ])
                w.writerow([
                    data.get('timestamp', ''),
                    data.get('temperature', ''),
                    data.get('humidity', ''),
                    data.get('wind_speed', ''),
                    data.get('gust_speed', ''),
                    data.get('wind_dir', ''),
                    data.get('wind_dir_str', ''),
                    data.get('rainfall', ''),
                    data.get('uv_index', ''),
                    data.get('illuminance', ''),
                    data.get('pressure', ''),
                    data.get('battery_ok', '')
                ])
        except Exception as e:
            logger.warning(f"[EnvMonitor] 기상 CSV 기록 실패: {e}")

    # ──────────────────────────────────────────────────────────────────
    # 상태 조회 API
    # ──────────────────────────────────────────────────────────────────
    def get_air_status(self) -> list:
        with self._lock:
            return list(self.air_data)

    def get_weather_status(self) -> Optional[dict]:
        with self._lock:
            return self.weather_data

    def get_environment_status(self) -> dict:
        with self._lock:
            return {
                'air':       list(self.air_data),
                'weather':   self.weather_data,
                'running':   self._running,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

    def get_air_history(self, limit: int = 10) -> list:
        with self._lock:
            return list(self.air_history[-limit:])

    def get_weather_history(self, limit: int = 10) -> list:
        with self._lock:
            return list(self.weather_history[-limit:])


# ──────────────────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.path.insert(0, BASE_DIR)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s — %(message)s'
    )

    from hardware.air_sensor_reader    import AirSensorManager
    from hardware.weather_station_reader import WeatherStationReader

    print("=" * 55)
    print("  EnvironmentMonitor 단독 테스트 (시뮬레이션, 35초)")
    print("=" * 55)

    air_mgr = AirSensorManager()
    ws_rdr  = WeatherStationReader()
    monitor = EnvironmentMonitor(air_mgr, ws_rdr)
    monitor.start()

    try:
        for step in range(3):
            time.sleep(10)
            print(f"\n[{time.strftime('%H:%M:%S')}] 상태 조회 #{step + 1}")
            air = monitor.get_air_status()
            ws  = monitor.get_weather_status()

            if air:
                valid = [s for s in air if s.get('valid') and s.get('temperature') is not None]
                if valid:
                    avg_t = sum(s['temperature'] for s in valid) / len(valid)
                    avg_h = sum(s['humidity']    for s in valid) / len(valid)
                    print(f"  SHT30  : {len(valid)}/{len(air)} 유효 | "
                          f"평균 온도 {avg_t:.1f}°C / 습도 {avg_h:.1f}%")
                else:
                    print("  SHT30  : 유효 데이터 없음")
            else:
                print("  SHT30  : 데이터 대기 중 (60초 간격)")

            if ws:
                print(f"  WH65LP : {ws['temperature']}°C / {ws['humidity']}% | "
                      f"풍속 {ws['wind_speed']}m/s ({ws['wind_dir_str']}) | "
                      f"기압 {ws['pressure']}hPa")
            else:
                print("  WH65LP : 데이터 대기 중 (16초 간격)")
    except KeyboardInterrupt:
        print("\n[인터럽트] 정지 중...")
    finally:
        monitor.stop()
        print("테스트 완료.")
