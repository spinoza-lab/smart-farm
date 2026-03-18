"""
analytics_bp.py (Stage 14b – 날짜 범위 limit 동적화, 시뮬레이션 플래그 추가)

변경점 (v0.6.4):
  - sensor-data  : 날짜 범위 기반 동적 limit (최대 100,000행 → 2,000행 샘플링)
  - environment  : 날짜 범위 기반 동적 limit + simulation_mode 플래그 반환
  - trigger-stats: 신규 진단 엔드포인트 (trigger_type 실제 값 확인용)

작성자: spinoza-lab
날짜:   2026-03-18
"""

import csv
import glob
import os
import statistics
from datetime import datetime as _dt
from flask import Blueprint, jsonify, render_template, request
import web.globals as g

analytics_bp = Blueprint('analytics', __name__)


# ── 페이지 ────────────────────────────────────────────────────────────────────

@analytics_bp.route('/analytics')
def analytics():
    return render_template('analytics.html')


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────

def _calc_stats(values: list, rows_ref: list) -> dict:
    vals = [float(v) for v in values if v not in ('', None)]
    if not vals:
        return {'count': 0, 'avg': 0, 'min': 0, 'max': 0,
                'first_timestamp': '', 'last_timestamp': ''}
    ts = [r.get('timestamp', '') for r in rows_ref]
    return {
        'count':           len(vals),
        'avg':             round(statistics.mean(vals), 1),
        'min':             round(min(vals), 1),
        'max':             round(max(vals), 1),
        'first_timestamp': ts[0]  if ts else '',
        'last_timestamp':  ts[-1] if ts else '',
    }


def _calc_day_limit(date_from, date_to, rows_per_day: int, cap: int) -> int:
    """날짜 범위로 동적 limit 계산"""
    try:
        if date_from and date_to:
            d1 = _dt.strptime(date_from, '%Y-%m-%d')
            d2 = _dt.strptime(date_to,   '%Y-%m-%d')
            days = max(1, (d2 - d1).days + 1)
        else:
            days = 7  # 기본값
        return min(days * rows_per_day, cap)
    except Exception:
        return cap


# ── /api/analytics/sensor-data ───────────────────────────────────────────────

@analytics_bp.route('/api/analytics/sensor-data')
def analytics_sensor_data():
    date_from = request.args.get('from')
    date_to   = request.args.get('to')

    # ── SQLite 경로 ──────────────────────────────────────
    if getattr(g, 'db_manager', None):
        try:
            start = f"{date_from} 00:00:00" if date_from else None
            end   = f"{date_to} 23:59:59"   if date_to   else None

            # ★ 날짜 범위 기반 동적 limit
            # 센서 기록 주기 ~20초 → 1일 ≈ 4,320행, 여유 25% 추가 → 5,400
            # 최대 100,000행 (약 6.4일치 full 데이터 or 30일치 샘플링)
            dyn_limit = _calc_day_limit(date_from, date_to,
                                        rows_per_day=5400, cap=100_000)

            rows = g.db_manager.query_sensor_readings(
                start=start, end=end, hours=168, limit=dyn_limit
            )
            MAX_ROWS = 2000
            step    = max(1, len(rows) // MAX_ROWS)
            sampled = rows[::step]
            stats   = g.db_manager.get_sensor_stats(start=start, end=end)
            return jsonify({
                'success': True,
                'data':    sampled,
                'total':   len(rows),
                'sampled': len(sampled),
                'stats': {
                    'tank1': {
                        'count':           stats['count'],
                        'avg':             stats['tank1']['avg'],
                        'min':             stats['tank1']['min'],
                        'max':             stats['tank1']['max'],
                        'first_timestamp': stats['first_timestamp'],
                        'last_timestamp':  stats['last_timestamp'],
                    },
                    'tank2': {
                        'count':           stats['count'],
                        'avg':             stats['tank2']['avg'],
                        'min':             stats['tank2']['min'],
                        'max':             stats['tank2']['max'],
                        'first_timestamp': stats['first_timestamp'],
                        'last_timestamp':  stats['last_timestamp'],
                    },
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ── CSV 폴백 ─────────────────────────────────────────
    log_dir = str(g._BASE_DIR / 'logs')
    try:
        files = sorted(glob.glob(os.path.join(log_dir, 'sensors_*.csv')))
        if date_from:
            files = [f for f in files if os.path.basename(f) >= f'sensors_{date_from}.csv']
        if date_to:
            files = [f for f in files if os.path.basename(f) <= f'sensors_{date_to}.csv']
        rows = []
        for fpath in files:
            with open(fpath, 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    rows.append(row)
        MAX_ROWS = 2000
        step = max(1, len(rows) // MAX_ROWS)
        return jsonify({
            'success': True,
            'data':    rows[::step],
            'total':   len(rows),
            'stats': {
                'tank1': _calc_stats([r.get('tank1_level', '') for r in rows], rows),
                'tank2': _calc_stats([r.get('tank2_level', '') for r in rows], rows),
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── /api/analytics/irrigation-history ────────────────────────────────────────

@analytics_bp.route('/api/analytics/irrigation-history')
def analytics_irrigation_history():
    date_from = request.args.get('from')
    date_to   = request.args.get('to')

    # ── SQLite 경로 ──────────────────────────────────────
    if getattr(g, 'db_manager', None):
        try:
            start = f"{date_from} 00:00:00" if date_from else None
            end   = f"{date_to} 23:59:59"   if date_to   else None
            rows  = g.db_manager.query_irrigation_history(start=start, end=end)
            return jsonify({'success': True, 'data': rows, 'total': len(rows), 'source': 'sqlite'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ── CSV / 메모리 폴백 ─────────────────────────────────
    csv_path = str(g._BASE_DIR / 'logs/irrigation_history.csv')
    if not os.path.exists(csv_path):
        if g.auto_irrigation:
            return jsonify({
                'success': True,
                'data':    list(reversed(g.auto_irrigation.irrigation_history)),
                'source':  'memory'
            })
        return jsonify({'success': True, 'data': [], 'source': 'empty'})
    try:
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                ts = row.get('timestamp', '')
                if date_from and ts < date_from:
                    continue
                if date_to and ts > date_to + ' 23:59:59':
                    continue
                rows.append(row)
        return jsonify({'success': True, 'data': list(reversed(rows)),
                        'total': len(rows), 'source': 'csv'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── /api/analytics/environment ───────────────────────────────────────────────

@analytics_bp.route('/api/analytics/environment')
def analytics_environment():
    """
    환경 데이터 분석 API (Stage 14b – 동적 limit + 시뮬레이션 플래그)
    쿼리 파라미터:
      from  – YYYY-MM-DD (기본: 7일 전)
      to    – YYYY-MM-DD (기본: 오늘)
      type  – air | weather | all (기본: all)
    """
    date_from = request.args.get('from')
    date_to   = request.args.get('to')
    data_type = request.args.get('type', 'all')

    if not getattr(g, 'db_manager', None):
        return jsonify({'success': False, 'error': 'DBManager 미초기화'}), 503

    try:
        start = f"{date_from} 00:00:00" if date_from else None
        end   = f"{date_to} 23:59:59"   if date_to   else None

        # ★ 시뮬레이션 모드 여부 (app.py 글로벌에서 읽기)
        simulation_mode = bool(getattr(g, 'simulation_mode', False))

        result = {
            'success':         True,
            'simulation_mode': simulation_mode,
        }

        if data_type in ('air', 'all'):
            # ★ 동적 limit:
            # SHT30 12개 × 기록 주기 ~5초 → 1시간 = 12 × 720 = 8,640행
            # 1일 = 207,360행 → 전체 조회는 무리; 100,000행 ≈ 11.5h분 full
            # 날짜별 cap: 소량 요청(1일)엔 20,000, 장기 요청엔 100,000
            air_limit = _calc_day_limit(date_from, date_to,
                                        rows_per_day=20_000, cap=100_000)
            air_rows = g.db_manager.query_air_readings(
                start=start, end=end, hours=168, limit=air_limit
            )
            # 차트용 샘플링 (최대 5,000행 – JS에서 timestamp 집계 후 실제 포인트 감소)
            step = max(1, len(air_rows) // 5000)
            result['air'] = {
                'data':  air_rows[::step],
                'total': len(air_rows),
            }

        if data_type in ('weather', 'all'):
            # WH65LP 1개 × ~60초 → 1일 = 1,440행
            wx_limit = _calc_day_limit(date_from, date_to,
                                       rows_per_day=1500, cap=50_000)
            wx_rows = g.db_manager.query_weather_readings(
                start=start, end=end, hours=168, limit=wx_limit
            )
            step = max(1, len(wx_rows) // 2000)
            result['weather'] = {
                'data':  wx_rows[::step],
                'total': len(wx_rows),
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── /api/analytics/trigger-stats (진단) ──────────────────────────────────────

@analytics_bp.route('/api/analytics/trigger-stats')
def analytics_trigger_stats():
    """
    관수 트리거 유형 분포 조회 (디버깅·진단용)
    DB에 실제 저장된 trigger_type 값과 건수를 반환합니다.
    """
    if not getattr(g, 'db_manager', None):
        return jsonify({'success': False, 'error': 'DBManager 미초기화'}), 503
    try:
        import sqlite3
        conn = sqlite3.connect(g.db_manager.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(trigger_type, '(null)') AS trigger_type,
                   COUNT(*) AS cnt
            FROM   irrigation_history
            GROUP  BY trigger_type
            ORDER  BY cnt DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({'success': True, 'trigger_distribution': rows})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── /api/analytics/db-info ───────────────────────────────────────────────────

@analytics_bp.route('/api/analytics/db-info')
def analytics_db_info():
    """DB 상태 확인 (테이블 행 수, 파일 크기)"""
    if not getattr(g, 'db_manager', None):
        return jsonify({'success': False, 'error': 'DBManager 미초기화'}), 503
    try:
        return jsonify({'success': True, 'info': g.db_manager.get_db_info()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
