#!/usr/bin/env python3
"""
fix_irrigation_remigrate.py  (Stage 14c)
=========================================
관수 이력 SQLite 재마이그레이션 – 컬럼명 불일치 버그 수정 후 재실행

[버그 원인]
  migrate_csv_to_db.py가 r.get("trigger_type", "manual") 을 사용하지만
  irrigation_history.csv 컬럼명은 "trigger" → 항상 'manual' 저장.
  동일하게 moisture_before → water_before, success → status 매핑도 누락.

[이 스크립트의 동작]
  1. SQLite irrigation_history 테이블 레코드 전체 삭제
  2. logs/irrigation_history.csv 에서 올바른 컬럼명으로 읽기
  3. 수정된 매핑으로 재삽입
  4. 결과 요약 출력

Usage:
    cd ~/smart_farm
    python3 fix_irrigation_remigrate.py
"""

import csv, os, sys, sqlite3
from pathlib import Path
from datetime import datetime

_BASE_DIR = Path(__file__).resolve().parent

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
DB_PATH  = _BASE_DIR / 'data' / 'smart_farm.db'
CSV_PATH = _BASE_DIR / 'logs' / 'irrigation_history.csv'

if not DB_PATH.exists():
    print(f"[ERROR] DB 파일 없음: {DB_PATH}")
    sys.exit(1)

if not CSV_PATH.exists():
    print(f"[ERROR] CSV 파일 없음: {CSV_PATH}")
    sys.exit(1)

# ── CSV 읽기 ──────────────────────────────────────────────────────────────────
print(f"[1/4] CSV 읽는 중: {CSV_PATH}")
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print(f"      {len(rows)}행 로드됨")

# 컬럼 확인
if rows:
    print(f"      컬럼: {list(rows[0].keys())}")

# ── DB 연결 & 기존 레코드 삭제 ────────────────────────────────────────────────
print(f"\n[2/4] SQLite 연결: {DB_PATH}")
conn = sqlite3.connect(str(DB_PATH))
cur  = conn.cursor()

cur.execute("SELECT COUNT(*) FROM irrigation_history")
existing_count = cur.fetchone()[0]
print(f"      기존 레코드 수: {existing_count}건")

print(f"\n[3/4] 기존 레코드 삭제 후 재삽입...")
cur.execute("DELETE FROM irrigation_history")
print(f"      {existing_count}건 삭제 완료")

# ── 재삽입 ────────────────────────────────────────────────────────────────────
INSERT_SQL = """INSERT OR IGNORE INTO irrigation_history
    (timestamp, zone_id, zone_name, trigger_type,
     duration_sec, water_before, water_after, status)
    VALUES (?,?,?,?,?,?,?,?)"""

ok = 0
skipped = 0
trigger_counter = {}

for r in rows:
    ts = r.get('timestamp', '').strip()
    if not ts:
        skipped += 1
        continue

    # ★ 올바른 컬럼 매핑 (CSV 컬럼명 기준)
    zone_id      = int(r.get('zone_id', 0) or 0)
    zone_name    = r.get('zone_name', '')          # 구 CSV는 없음 → 빈 문자열
    # trigger / trigger_type 모두 시도
    trigger_type = (r.get('trigger_type') or r.get('trigger') or 'manual').strip()
    duration_sec = int(float(r.get('duration_sec', 0) or 0))
    # water_before / moisture_before 모두 시도
    water_before = float(r.get('water_before') or r.get('moisture_before') or 0)
    water_after  = float(r.get('water_after', 0) or 0)
    # status / success 모두 시도
    raw_status = r.get('status', '').strip()
    if raw_status:
        status = raw_status
    else:
        raw_success = str(r.get('success', 'True')).strip().lower()
        status = 'completed' if raw_success in ('true', '1', 'yes') else 'failed'

    # zone_name 없으면 zone_id로 채우기
    if not zone_name:
        zone_name = f'구역 {zone_id}'

    try:
        cur.execute(INSERT_SQL, (
            ts, zone_id, zone_name, trigger_type,
            duration_sec, water_before, water_after, status
        ))
        ok += 1
        trigger_counter[trigger_type] = trigger_counter.get(trigger_type, 0) + 1
    except Exception as e:
        print(f"  ⚠️  행 건너뜀: {e} | {r}")
        skipped += 1

conn.commit()
conn.close()

# ── 결과 ─────────────────────────────────────────────────────────────────────
print(f"\n[4/4] 완료!")
print(f"  삽입 성공: {ok}건")
print(f"  건너뜀:   {skipped}건")
print(f"\n  trigger_type 분포:")
for k, v in sorted(trigger_counter.items(), key=lambda x: -x[1]):
    print(f"    {k:15s}: {v}건")
print(f"\n✅ 재마이그레이션 완료 – 분석 페이지를 새로고침하세요.")
