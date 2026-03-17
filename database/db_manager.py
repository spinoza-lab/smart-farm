"""
DBManager – SQLite 데이터베이스 관리 모듈
Stage 11: CSV 스토리지를 SQLite로 교체

파일 위치: database/db_manager.py
DB 파일:   data/smart_farm.db

테이블 목록:
  sensor_readings      – 탱크 수위 / ADS1115 전압
  air_sensor_readings  – SHT30 ×12 온·습도 (zone 별)
  weather_readings     – WH65LP 기상 관측소
  irrigation_history   – 관수 이력
  alerts               – 알림 이력

작성자: spinoza-lab
날짜:   2026-03-17
"""

import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import json

_BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = str(_BASE_DIR / "data" / "smart_farm.db")

# ──────────────────────────────────────────────────────────────────────────────
# DDL – 테이블 생성 SQL
# ──────────────────────────────────────────────────────────────────────────────
_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;

CREATE TABLE IF NOT EXISTS sensor_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    tank1_level REAL,
    tank2_level REAL,
    ch0_voltage REAL,
    ch1_voltage REAL,
    ch2_voltage REAL,
    ch3_voltage REAL
);
CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_readings(timestamp);

CREATE TABLE IF NOT EXISTS air_sensor_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    sensor_id   TEXT,
    zone_id     INTEGER,
    name        TEXT,
    temperature REAL,
    humidity    REAL,
    valid       INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_air_ts        ON air_sensor_readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_air_sensor_id ON air_sensor_readings(sensor_id);
CREATE INDEX IF NOT EXISTS idx_air_zone_id   ON air_sensor_readings(zone_id);

CREATE TABLE IF NOT EXISTS weather_readings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT    NOT NULL,
    temperature  REAL,
    humidity     REAL,
    wind_speed   REAL,
    gust_speed   REAL,
    wind_dir     INTEGER,
    wind_dir_str TEXT,
    rainfall     REAL,
    uv_index     REAL,
    illuminance  REAL,
    pressure     REAL,
    battery_ok   INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_weather_ts ON weather_readings(timestamp);

CREATE TABLE IF NOT EXISTS irrigation_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT    NOT NULL,
    zone_id      INTEGER,
    zone_name    TEXT,
    trigger_type TEXT,
    duration_sec INTEGER,
    water_before REAL,
    water_after  REAL,
    status       TEXT
);
CREATE INDEX IF NOT EXISTS idx_irr_ts ON irrigation_history(timestamp);

CREATE TABLE IF NOT EXISTS alerts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level     TEXT,
    type      TEXT,
    message   TEXT,
    value     REAL,
    threshold REAL
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp);
"""


class DBManager:
    """
    SQLite 데이터베이스 매니저

    사용 예시:
        db = DBManager()
        db.insert_sensor_reading(tank1_level=75.2, tank2_level=68.0,
                                 voltages=[2.1, 1.9, 0.6, 0.6])
        rows = db.query_sensor_readings(hours=24)
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._ensure_data_dir()
        self._init_db()
        print(f"✅ DBManager 초기화 완료: {self.db_path}")

    # ── 초기화 ────────────────────────────────────────────────────────────────

    def _ensure_data_dir(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """테이블 & 인덱스 생성 (없으면)"""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.executescript(_DDL)
                conn.commit()
            finally:
                conn.close()

    # ── 공통 헬퍼 ─────────────────────────────────────────────────────────────

    def _ts_now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _ts_str(self, ts) -> str:
        if ts is None:
            return self._ts_now()
        if isinstance(ts, datetime):
            return ts.strftime("%Y-%m-%d %H:%M:%S")
        return str(ts)

    def _rows_to_dicts(self, rows) -> List[Dict]:
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════════════════════
    # sensor_readings
    # ═══════════════════════════════════════════════════════════════════════════

    def insert_sensor_reading(
        self,
        tank1_level: float,
        tank2_level: float,
        voltages: List[float],
        timestamp=None,
    ) -> bool:
        """탱크 수위 + 전압 1행 삽입"""
        ts = self._ts_str(timestamp)
        v = (voltages + [0.0, 0.0, 0.0, 0.0])[:4]
        sql = """INSERT INTO sensor_readings
                 (timestamp, tank1_level, tank2_level,
                  ch0_voltage, ch1_voltage, ch2_voltage, ch3_voltage)
                 VALUES (?,?,?,?,?,?,?)"""
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    conn.execute(sql, (ts, round(tank1_level, 2), round(tank2_level, 2),
                                       round(v[0], 4), round(v[1], 4),
                                       round(v[2], 4), round(v[3], 4)))
                    conn.commit()
                    return True
                finally:
                    conn.close()
        except Exception as e:
            print(f"❌ insert_sensor_reading 실패: {e}")
            return False

    def query_sensor_readings(
        self,
        hours: int = 24,
        start: Optional[str] = None,
        end:   Optional[str] = None,
        limit: int = 2000,
    ) -> List[Dict]:
        """기간별 센서 데이터 조회 (최근순 → 오래된순)"""
        if start is None:
            start = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        if end is None:
            end = self._ts_now()
        sql = """SELECT * FROM sensor_readings
                 WHERE timestamp BETWEEN ? AND ?
                 ORDER BY timestamp ASC LIMIT ?"""
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(sql, (start, end, limit)).fetchall()
                return self._rows_to_dicts(rows)
            finally:
                conn.close()

    def get_sensor_stats(
        self,
        hours: int = 24,
        start: Optional[str] = None,
        end:   Optional[str] = None,
    ) -> Dict:
        """탱크 수위 통계 반환"""
        if start is None:
            start = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        if end is None:
            end = self._ts_now()
        sql = """SELECT
                   COUNT(*)         AS cnt,
                   AVG(tank1_level) AS t1_avg, MIN(tank1_level) AS t1_min, MAX(tank1_level) AS t1_max,
                   AVG(tank2_level) AS t2_avg, MIN(tank2_level) AS t2_min, MAX(tank2_level) AS t2_max,
                   MIN(timestamp)   AS first_ts, MAX(timestamp) AS last_ts
                 FROM sensor_readings WHERE timestamp BETWEEN ? AND ?"""
        with self._lock:
            conn = self._get_conn()
            try:
                r = conn.execute(sql, (start, end)).fetchone()
                cnt = r["cnt"] or 0
                return {
                    "count": cnt,
                    "tank1": {
                        "avg":  round(r["t1_avg"] or 0, 1),
                        "min":  round(r["t1_min"] or 0, 1),
                        "max":  round(r["t1_max"] or 0, 1),
                    },
                    "tank2": {
                        "avg":  round(r["t2_avg"] or 0, 1),
                        "min":  round(r["t2_min"] or 0, 1),
                        "max":  round(r["t2_max"] or 0, 1),
                    },
                    "first_timestamp": r["first_ts"] or "",
                    "last_timestamp":  r["last_ts"]  or "",
                }
            finally:
                conn.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # air_sensor_readings
    # ═══════════════════════════════════════════════════════════════════════════

    def insert_air_reading(
        self,
        timestamp,
        sensor_id: str,
        zone_id:   int,
        name:      str,
        temperature: float,
        humidity:    float,
        valid:       bool = True,
    ) -> bool:
        ts = self._ts_str(timestamp)
        sql = """INSERT INTO air_sensor_readings
                 (timestamp, sensor_id, zone_id, name, temperature, humidity, valid)
                 VALUES (?,?,?,?,?,?,?)"""
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    conn.execute(sql, (ts, sensor_id, zone_id, name,
                                       round(temperature, 2), round(humidity, 2),
                                       1 if valid else 0))
                    conn.commit()
                    return True
                finally:
                    conn.close()
        except Exception as e:
            print(f"❌ insert_air_reading 실패: {e}")
            return False

    def insert_air_readings_bulk(self, records: List[Dict]) -> int:
        """
        SHT30 배치 삽입 (환경 모니터 루프에서 12개 동시 삽입)
        records: [{'timestamp':…, 'sensor_id':…, 'zone_id':…,
                   'name':…, 'temperature':…, 'humidity':…, 'valid':…}, …]
        """
        sql = """INSERT INTO air_sensor_readings
                 (timestamp, sensor_id, zone_id, name, temperature, humidity, valid)
                 VALUES (:timestamp, :sensor_id, :zone_id, :name,
                         :temperature, :humidity, :valid)"""
        rows = []
        for r in records:
            rows.append({
                "timestamp":   self._ts_str(r.get("timestamp")),
                "sensor_id":   r.get("sensor_id", ""),
                "zone_id":     r.get("zone_id", 0),
                "name":        r.get("name", ""),
                "temperature": round(float(r.get("temperature", 0)), 2),
                "humidity":    round(float(r.get("humidity", 0)),    2),
                "valid":       1 if r.get("valid", True) else 0,
            })
        if not rows:
            return 0
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    conn.executemany(sql, rows)
                    conn.commit()
                    return len(rows)
                finally:
                    conn.close()
        except Exception as e:
            print(f"❌ insert_air_readings_bulk 실패: {e}")
            return 0

    def query_air_readings(
        self,
        hours:     int = 24,
        start:     Optional[str] = None,
        end:       Optional[str] = None,
        zone_id:   Optional[int] = None,
        sensor_id: Optional[str] = None,
        limit:     int = 5000,
    ) -> List[Dict]:
        if start is None:
            start = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        if end is None:
            end = self._ts_now()
        params: List[Any] = [start, end]
        where  = "WHERE timestamp BETWEEN ? AND ?"
        if zone_id is not None:
            where += " AND zone_id = ?"; params.append(zone_id)
        if sensor_id is not None:
            where += " AND sensor_id = ?"; params.append(sensor_id)
        sql = f"SELECT * FROM air_sensor_readings {where} ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(sql, params).fetchall()
                return self._rows_to_dicts(rows)
            finally:
                conn.close()

    def get_latest_air_snapshot(self) -> List[Dict]:
        """각 zone_id 마지막 값 1행씩 반환 (대시보드용)"""
        sql = """SELECT a.* FROM air_sensor_readings a
                 INNER JOIN (
                     SELECT zone_id, MAX(timestamp) AS max_ts
                     FROM air_sensor_readings GROUP BY zone_id
                 ) b ON a.zone_id = b.zone_id AND a.timestamp = b.max_ts
                 ORDER BY a.zone_id"""
        with self._lock:
            conn = self._get_conn()
            try:
                return self._rows_to_dicts(conn.execute(sql).fetchall())
            finally:
                conn.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # weather_readings
    # ═══════════════════════════════════════════════════════════════════════════

    def insert_weather_reading(self, data: Dict) -> bool:
        ts = self._ts_str(data.get("timestamp"))
        sql = """INSERT INTO weather_readings
                 (timestamp, temperature, humidity, wind_speed, gust_speed,
                  wind_dir, wind_dir_str, rainfall, uv_index,
                  illuminance, pressure, battery_ok)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    conn.execute(sql, (
                        ts,
                        data.get("temperature"),  data.get("humidity"),
                        data.get("wind_speed"),   data.get("gust_speed"),
                        data.get("wind_dir"),     data.get("wind_dir_str"),
                        data.get("rainfall"),     data.get("uv_index"),
                        data.get("illuminance"),  data.get("pressure"),
                        1 if data.get("battery_ok", True) else 0,
                    ))
                    conn.commit()
                    return True
                finally:
                    conn.close()
        except Exception as e:
            print(f"❌ insert_weather_reading 실패: {e}")
            return False

    def query_weather_readings(
        self,
        hours: int = 24,
        start: Optional[str] = None,
        end:   Optional[str] = None,
        limit: int = 2000,
    ) -> List[Dict]:
        if start is None:
            start = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        if end is None:
            end = self._ts_now()
        sql = """SELECT * FROM weather_readings
                 WHERE timestamp BETWEEN ? AND ?
                 ORDER BY timestamp ASC LIMIT ?"""
        with self._lock:
            conn = self._get_conn()
            try:
                return self._rows_to_dicts(conn.execute(sql, (start, end, limit)).fetchall())
            finally:
                conn.close()

    def get_latest_weather(self) -> Optional[Dict]:
        """최신 기상 1행 반환"""
        sql = "SELECT * FROM weather_readings ORDER BY timestamp DESC LIMIT 1"
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(sql).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # irrigation_history
    # ═══════════════════════════════════════════════════════════════════════════

    def insert_irrigation_event(
        self,
        zone_id:      int,
        zone_name:    str,
        trigger_type: str,
        duration_sec: int,
        water_before: float = 0.0,
        water_after:  float = 0.0,
        status:       str = "completed",
        timestamp=None,
    ) -> bool:
        ts = self._ts_str(timestamp)
        sql = """INSERT INTO irrigation_history
                 (timestamp, zone_id, zone_name, trigger_type,
                  duration_sec, water_before, water_after, status)
                 VALUES (?,?,?,?,?,?,?,?)"""
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    conn.execute(sql, (ts, zone_id, zone_name, trigger_type,
                                       duration_sec, water_before, water_after, status))
                    conn.commit()
                    return True
                finally:
                    conn.close()
        except Exception as e:
            print(f"❌ insert_irrigation_event 실패: {e}")
            return False

    def query_irrigation_history(
        self,
        hours: int = 168,
        start: Optional[str] = None,
        end:   Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict]:
        if start is None:
            start = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        if end is None:
            end = self._ts_now()
        sql = """SELECT * FROM irrigation_history
                 WHERE timestamp BETWEEN ? AND ?
                 ORDER BY timestamp DESC LIMIT ?"""
        with self._lock:
            conn = self._get_conn()
            try:
                return self._rows_to_dicts(conn.execute(sql, (start, end, limit)).fetchall())
            finally:
                conn.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # alerts
    # ═══════════════════════════════════════════════════════════════════════════

    def insert_alert(
        self,
        level:     str,
        type_:     str,
        message:   str,
        value:     float = 0.0,
        threshold: float = 0.0,
        timestamp=None,
    ) -> bool:
        ts = self._ts_str(timestamp)
        sql = """INSERT INTO alerts (timestamp, level, type, message, value, threshold)
                 VALUES (?,?,?,?,?,?)"""
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    conn.execute(sql, (ts, level, type_, message, value, threshold))
                    conn.commit()
                    return True
                finally:
                    conn.close()
        except Exception as e:
            print(f"❌ insert_alert 실패: {e}")
            return False

    def query_alerts(
        self,
        hours: int = 24,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        start = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        params: List[Any] = [start]
        where  = "WHERE timestamp >= ?"
        if level:
            where += " AND level = ?"; params.append(level.upper())
        sql = f"SELECT * FROM alerts {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            conn = self._get_conn()
            try:
                return self._rows_to_dicts(conn.execute(sql, params).fetchall())
            finally:
                conn.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════════════

    def get_db_info(self) -> Dict:
        """테이블 별 행 수 및 DB 파일 크기 반환"""
        tables = ["sensor_readings", "air_sensor_readings",
                  "weather_readings", "irrigation_history", "alerts"]
        info = {}
        with self._lock:
            conn = self._get_conn()
            try:
                for t in tables:
                    row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {t}").fetchone()
                    info[t] = row["cnt"]
            finally:
                conn.close()
        try:
            info["db_size_kb"] = round(Path(self.db_path).stat().st_size / 1024, 1)
        except Exception:
            info["db_size_kb"] = 0
        return info

    def vacuum(self):
        """VACUUM – 미사용 공간 회수"""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("VACUUM")
                conn.commit()
                print("✅ VACUUM 완료")
            finally:
                conn.close()
