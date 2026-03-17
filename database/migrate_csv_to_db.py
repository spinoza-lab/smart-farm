"""
migrate_csv_to_db.py – 기존 CSV 데이터를 SQLite로 마이그레이션
Stage 11 배포 후 1회 실행

사용법:
  cd ~/smart_farm
  python3 database/migrate_csv_to_db.py

지원 CSV 형식:
  logs/sensors_YYYY-MM-DD.csv        → sensor_readings
  data/air_sensor_logs/air_*.csv     → air_sensor_readings
  data/weather_logs/weather_*.csv    → weather_readings
  logs/irrigation_history.csv        → irrigation_history

작성자: spinoza-lab
날짜:   2026-03-17
"""

import csv
import glob
import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path 에 추가
_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE_DIR))

from database.db_manager import DBManager


def _read_csv(path: str):
    """CSV 파일을 DictReader로 읽어 행 리스트 반환. 실패 시 []."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"  ⚠️  읽기 실패 ({path}): {e}")
        return []


# ──────────────────────────────────────────────────────────────────────────────
# 1. 탱크 센서 CSV (logs/sensors_YYYY-MM-DD.csv)
# ──────────────────────────────────────────────────────────────────────────────
def migrate_sensor_logs(db: DBManager) -> int:
    pattern = str(_BASE_DIR / "logs" / "sensors_*.csv")
    files   = sorted(glob.glob(pattern))
    total   = 0
    print(f"\n[1/4] 탱크 센서 CSV → sensor_readings")
    print(f"      파일 수: {len(files)}")

    for fpath in files:
        rows = _read_csv(fpath)
        ok = 0
        for r in rows:
            ts = r.get("timestamp", "")
            if not ts:
                continue
            try:
                v = [
                    float(r.get("ch0_voltage", 0) or 0),
                    float(r.get("ch1_voltage", 0) or 0),
                    float(r.get("ch2_voltage", 0) or 0),
                    float(r.get("ch3_voltage", 0) or 0),
                ]
                res = db.insert_sensor_reading(
                    tank1_level=float(r.get("tank1_level", 0) or 0),
                    tank2_level=float(r.get("tank2_level", 0) or 0),
                    voltages=v,
                    timestamp=ts,
                )
                if res:
                    ok += 1
            except Exception as e:
                print(f"    행 건너뜀: {e} | {r}")
        fname = os.path.basename(fpath)
        print(f"  ✅ {fname}: {ok}/{len(rows)} 행")
        total += ok

    print(f"  ── 합계: {total} 행")
    return total


# ──────────────────────────────────────────────────────────────────────────────
# 2. 대기 센서 CSV (data/air_sensor_logs/air_*.csv)
# ──────────────────────────────────────────────────────────────────────────────
def migrate_air_logs(db: DBManager) -> int:
    pattern = str(_BASE_DIR / "data" / "air_sensor_logs" / "air_*.csv")
    files   = sorted(glob.glob(pattern))
    total   = 0
    print(f"\n[2/4] 대기 센서 CSV → air_sensor_readings")
    print(f"      파일 수: {len(files)}")

    for fpath in files:
        rows = _read_csv(fpath)
        batch = []
        for r in rows:
            ts = r.get("timestamp", "")
            if not ts:
                continue
            try:
                batch.append({
                    "timestamp":   ts,
                    "sensor_id":   r.get("sensor_id",  ""),
                    "zone_id":     int(r.get("zone_id", 0) or 0),
                    "name":        r.get("name", ""),
                    "temperature": float(r.get("temperature", 0) or 0),
                    "humidity":    float(r.get("humidity",    0) or 0),
                    "valid":       str(r.get("valid", "True")).lower() in ("1", "true"),
                })
            except Exception as e:
                print(f"    행 건너뜀: {e} | {r}")
        ok = db.insert_air_readings_bulk(batch)
        fname = os.path.basename(fpath)
        print(f"  ✅ {fname}: {ok}/{len(rows)} 행")
        total += ok

    print(f"  ── 합계: {total} 행")
    return total


# ──────────────────────────────────────────────────────────────────────────────
# 3. 기상 관측소 CSV (data/weather_logs/weather_*.csv)
# ──────────────────────────────────────────────────────────────────────────────
def migrate_weather_logs(db: DBManager) -> int:
    pattern = str(_BASE_DIR / "data" / "weather_logs" / "weather_*.csv")
    files   = sorted(glob.glob(pattern))
    total   = 0
    print(f"\n[3/4] 기상 관측소 CSV → weather_readings")
    print(f"      파일 수: {len(files)}")

    for fpath in files:
        rows = _read_csv(fpath)
        ok = 0
        for r in rows:
            ts = r.get("timestamp", "")
            if not ts:
                continue
            try:
                data = {
                    "timestamp":   ts,
                    "temperature": float(r.get("temperature", 0) or 0),
                    "humidity":    float(r.get("humidity",    0) or 0),
                    "wind_speed":  float(r.get("wind_speed",  0) or 0),
                    "gust_speed":  float(r.get("gust_speed",  0) or 0),
                    "wind_dir":    int(float(r.get("wind_dir", 0) or 0)),
                    "wind_dir_str": r.get("wind_dir_str", ""),
                    "rainfall":    float(r.get("rainfall",   0) or 0),
                    "uv_index":    float(r.get("uv_index",   0) or 0),
                    "illuminance": float(r.get("illuminance",0) or 0),
                    "pressure":    float(r.get("pressure",   0) or 0),
                    "battery_ok":  str(r.get("battery_ok", "True")).lower() in ("1","true"),
                }
                if db.insert_weather_reading(data):
                    ok += 1
            except Exception as e:
                print(f"    행 건너뜀: {e} | {r}")
        fname = os.path.basename(fpath)
        print(f"  ✅ {fname}: {ok}/{len(rows)} 행")
        total += ok

    print(f"  ── 합계: {total} 행")
    return total


# ──────────────────────────────────────────────────────────────────────────────
# 4. 관수 이력 CSV (logs/irrigation_history.csv)
# ──────────────────────────────────────────────────────────────────────────────
def migrate_irrigation_history(db: DBManager) -> int:
    fpath = str(_BASE_DIR / "logs" / "irrigation_history.csv")
    print(f"\n[4/4] 관수 이력 CSV → irrigation_history")

    if not os.path.exists(fpath):
        print(f"  ℹ️  파일 없음: {fpath} (건너뜀)")
        return 0

    rows = _read_csv(fpath)
    ok   = 0
    for r in rows:
        ts = r.get("timestamp", "")
        if not ts:
            continue
        try:
            db.insert_irrigation_event(
                zone_id      = int(r.get("zone_id",      0) or 0),
                zone_name    = r.get("zone_name",    ""),
                trigger_type = r.get("trigger_type", "manual"),
                duration_sec = int(float(r.get("duration_sec", 0) or 0)),
                water_before = float(r.get("water_before", 0) or 0),
                water_after  = float(r.get("water_after",  0) or 0),
                status       = r.get("status", "completed"),
                timestamp    = ts,
            )
            ok += 1
        except Exception as e:
            print(f"    행 건너뜀: {e} | {r}")

    print(f"  ✅ {ok}/{len(rows)} 행")
    return ok


# ──────────────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🗄️  CSV → SQLite 마이그레이션 (Stage 11)")
    print(f"   DB 경로: {_BASE_DIR / 'data' / 'smart_farm.db'}")
    print("=" * 60)

    db = DBManager()

    t1 = migrate_sensor_logs(db)
    t2 = migrate_air_logs(db)
    t3 = migrate_weather_logs(db)
    t4 = migrate_irrigation_history(db)

    total = t1 + t2 + t3 + t4

    print("\n" + "=" * 60)
    print("📊 마이그레이션 결과")
    print(f"  sensor_readings      : {t1:>6,} 행")
    print(f"  air_sensor_readings  : {t2:>6,} 행")
    print(f"  weather_readings     : {t3:>6,} 행")
    print(f"  irrigation_history   : {t4:>6,} 행")
    print(f"  합계                 : {total:>6,} 행")
    print("=" * 60)

    info = db.get_db_info()
    print("\n📁 DB 상태:")
    for k, v in info.items():
        if k == "db_size_kb":
            print(f"  DB 파일 크기  : {v} KB")
        else:
            print(f"  {k:<22}: {v:>6,} 행")

    print("\n✅ 마이그레이션 완료!")
    print("   CSV 파일은 삭제하지 않습니다. 검증 후 수동으로 제거하세요.")


if __name__ == "__main__":
    main()
