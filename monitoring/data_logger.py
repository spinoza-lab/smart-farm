"""
DataLogger 모듈 (Stage 11 – SQLite 병행 저장)
기존 CSV 저장은 유지하면서 SQLite에도 동시 기록

변경점 (Stage 11):
  - __init__에 db_manager 파라미터 추가
  - log_sensor_data()에서 DBManager.insert_sensor_reading() 호출

작성자: spinoza-lab
날짜:   2026-03-17
"""

import csv
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import threading

_BASE_DIR = Path(__file__).resolve().parent.parent


class DataLogger:
    """
    센서 데이터 로깅 클래스 (Stage 11: SQLite 병행 저장)

    CSV 형식으로 센서 데이터를 저장하고 조회.
    날짜별로 파일을 자동 분리하여 관리하며,
    db_manager 가 주입되면 SQLite 에도 동시 저장.
    """

    def __init__(self, log_dir: str = str(_BASE_DIR / 'logs'),
                 db_manager=None):
        """
        DataLogger 초기화

        Args:
            log_dir:    로그 파일을 저장할 디렉터리 경로
            db_manager: DBManager 인스턴스 (None 이면 CSV 만 저장)
        """
        self.log_dir    = log_dir
        self.db_manager = db_manager
        self._lock      = threading.Lock()

        self._ensure_log_directory()

        _db_info = "SQLite + CSV" if db_manager else "CSV only"
        print(f"✅ DataLogger 초기화 완료 ({_db_info})")
        print(f"   로그 디렉터리: {self.log_dir}")

    # ── 내부 유틸 ─────────────────────────────────────────────────────────────

    def _ensure_log_directory(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            print(f"📁 로그 디렉터리 생성: {self.log_dir}")

    def _get_log_filename(self, date: Optional[datetime] = None) -> str:
        if date is None:
            date = datetime.now()
        filename = f"sensors_{date.strftime('%Y-%m-%d')}.csv"
        return os.path.join(self.log_dir, filename)

    def _ensure_csv_header(self, filepath: str):
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'tank1_level', 'tank2_level',
                    'ch0_voltage', 'ch1_voltage',
                    'ch2_voltage', 'ch3_voltage'
                ])

    # ── 공개 API ──────────────────────────────────────────────────────────────

    def log_sensor_data(self,
                        tank1_level: float,
                        tank2_level: float,
                        voltages:    List[float],
                        timestamp:   Optional[datetime] = None) -> bool:
        """
        센서 데이터를 CSV(+ SQLite)에 기록

        Args:
            tank1_level: 탱크 1 수위 (%)
            tank2_level: 탱크 2 수위 (%)
            voltages:    4채널 전압 리스트 [ch0, ch1, ch2, ch3]
            timestamp:   타임스탬프 (None 이면 현재 시간)

        Returns:
            성공 여부
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()

            filepath = self._get_log_filename(timestamp)

            # ── CSV 저장 ─────────────────────────────────────
            with self._lock:
                self._ensure_csv_header(filepath)
                with open(filepath, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        f"{tank1_level:.1f}",
                        f"{tank2_level:.1f}",
                        f"{voltages[0]:.3f}",
                        f"{voltages[1]:.3f}",
                        f"{voltages[2]:.3f}",
                        f"{voltages[3]:.3f}"
                    ])

            # ── SQLite 저장 (db_manager 가 있을 때만) ────────
            if self.db_manager:
                self.db_manager.insert_sensor_reading(
                    tank1_level=tank1_level,
                    tank2_level=tank2_level,
                    voltages=voltages,
                    timestamp=timestamp,
                )

            return True

        except Exception as e:
            print(f"❌ 데이터 로깅 실패: {e}")
            return False

    def get_data(self,
                 start_date:  Optional[datetime] = None,
                 end_date:    Optional[datetime] = None,
                 tank_filter: Optional[int]      = None,
                 level_min:   Optional[float]    = None,
                 level_max:   Optional[float]    = None) -> List[Dict]:
        """
        저장된 데이터 조회
        db_manager 가 있으면 SQLite 에서, 없으면 CSV 에서 읽음
        """
        if self.db_manager and start_date is None and end_date is None:
            # SQLite 경로: 최근 24 h 기본
            rows = self.db_manager.query_sensor_readings(hours=24)
            return self._filter_rows(rows, tank_filter, level_min, level_max)

        if self.db_manager and (start_date or end_date):
            s = start_date.strftime("%Y-%m-%d %H:%M:%S") if start_date else None
            e = end_date.strftime("%Y-%m-%d %H:%M:%S")   if end_date   else None
            rows = self.db_manager.query_sensor_readings(start=s, end=e)
            return self._filter_rows(rows, tank_filter, level_min, level_max)

        # CSV 폴백
        return self._get_data_csv(start_date, end_date, tank_filter, level_min, level_max)

    def _filter_rows(self, rows, tank_filter, level_min, level_max):
        if tank_filter is None and level_min is None and level_max is None:
            return rows
        result = []
        for r in rows:
            tank_key = f"tank{tank_filter}_level" if tank_filter else "tank1_level"
            try:
                level = float(r[tank_key])
                if level_min is not None and level < level_min:
                    continue
                if level_max is not None and level > level_max:
                    continue
            except (KeyError, ValueError):
                pass
            result.append(r)
        return result

    def _get_data_csv(self, start_date, end_date, tank_filter, level_min, level_max):
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date

        all_data = []
        current_date = start_date
        while current_date <= end_date:
            filepath = self._get_log_filename(current_date)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if self._apply_filters(row, tank_filter, level_min, level_max):
                                all_data.append(row)
                except Exception as e:
                    print(f"⚠️  파일 읽기 실패 ({filepath}): {e}")
            current_date += timedelta(days=1)
        return all_data

    def _apply_filters(self, row, tank_filter, level_min, level_max):
        try:
            if tank_filter is not None:
                tank_key = f"tank{tank_filter}_level"
                level = float(row[tank_key])
                if level_min is not None and level < level_min:
                    return False
                if level_max is not None and level > level_max:
                    return False
            return True
        except (KeyError, ValueError):
            return False

    def get_statistics(self,
                       start_date: Optional[datetime] = None,
                       end_date:   Optional[datetime] = None,
                       tank_num:   int = 1) -> Dict:
        """기간별 통계 계산"""
        if self.db_manager:
            s = start_date.strftime("%Y-%m-%d %H:%M:%S") if start_date else None
            e = end_date.strftime("%Y-%m-%d %H:%M:%S")   if end_date   else None
            stats = self.db_manager.get_sensor_stats(start=s, end=e)
            tk = stats.get(f"tank{tank_num}", {})
            return {
                'count': stats['count'],
                'avg':   tk.get('avg', 0.0),
                'min':   tk.get('min', 0.0),
                'max':   tk.get('max', 0.0),
                'first': None,
                'last':  None,
            }

        # CSV 폴백
        data = self._get_data_csv(start_date, end_date, None, None, None)
        if not data:
            return {'count': 0, 'avg': 0.0, 'min': 0.0, 'max': 0.0, 'first': None, 'last': None}
        tank_key = f"tank{tank_num}_level"
        levels = [float(row[tank_key]) for row in data]
        return {
            'count': len(levels),
            'avg':   sum(levels) / len(levels),
            'min':   min(levels),
            'max':   max(levels),
            'first': levels[0],
            'last':  levels[-1],
        }

    def get_latest_data(self, limit: int = 10) -> List[Dict]:
        if self.db_manager:
            return self.db_manager.query_sensor_readings(hours=48, limit=limit)
        today     = datetime.now()
        yesterday = today - timedelta(days=1)
        data = self._get_data_csv(yesterday, today, None, None, None)
        return data[-limit:] if data else []

    def delete_old_logs(self, days_to_keep: int = 30) -> int:
        deleted_count = 0
        cutoff_date   = datetime.now() - timedelta(days=days_to_keep)
        try:
            for filename in os.listdir(self.log_dir):
                if filename.startswith("sensors_") and filename.endswith(".csv"):
                    date_str = filename.replace("sensors_", "").replace(".csv", "")
                    try:
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")
                        if file_date < cutoff_date:
                            os.remove(os.path.join(self.log_dir, filename))
                            deleted_count += 1
                            print(f"🗑️  삭제됨: {filename}")
                    except ValueError:
                        continue
        except Exception as e:
            print(f"❌ 로그 정리 실패: {e}")
        return deleted_count

    def get_log_files(self) -> List[Tuple[str, int]]:
        files = []
        try:
            for filename in sorted(os.listdir(self.log_dir)):
                if filename.startswith("sensors_") and filename.endswith(".csv"):
                    filepath = os.path.join(self.log_dir, filename)
                    size     = os.path.getsize(filepath)
                    files.append((filename, size))
        except Exception as e:
            print(f"❌ 파일 목록 조회 실패: {e}")
        return files
