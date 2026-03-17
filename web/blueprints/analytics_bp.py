"""
analytics_bp.py (Stage 11 – SQLite 우선, CSV 폴백)
기존 CSV 쿼리를 SQLite DBManager로 교체하되,
db_manager 가 없으면 기존 CSV 로직으로 폴백

변경점:
  - analytics_sensor_data() : DBManager.query_sensor_readings() 사용
  - analytics_irrigation_history() : DBManager.query_irrigation_history() 사용
  - /api/analytics/environment : 신규 (air + weather 데이터)

작성자: spinoza-lab
날짜:   2026-03-17
"""

import csv
import glob
import os
import statistics
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
            rows = g.db_manager.query_sensor_readings(
                start=start, end=end, hours=168, limit=2000
            )
            MAX_ROWS = 2000
            step = max(1, len(rows) // MAX_ROWS)
            sampled = rows[::step]
            stats = g.db_manager.get_sensor_stats(start=start, end=end)
            return jsonify({
                'success': True,
                'data':    sampled,
                'total':   len(rows),
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
    환경 데이터 분석 API (Stage 11 신규)
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

        result = {'success': True}

        if data_type in ('air', 'all'):
            air_rows = g.db_manager.query_air_readings(
                start=start, end=end, hours=168, limit=5000
            )
            # 샘플링 (최대 2000 행)
            step = max(1, len(air_rows) // 2000)
            result['air'] = {
                'data':  air_rows[::step],
                'total': len(air_rows),
            }

        if data_type in ('weather', 'all'):
            wx_rows = g.db_manager.query_weather_readings(
                start=start, end=end, hours=168, limit=2000
            )
            result['weather'] = {
                'data':  wx_rows,
                'total': len(wx_rows),
            }

        return jsonify(result)

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
