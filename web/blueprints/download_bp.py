"""다운로드 Blueprint (Stage 14b – 환경 데이터 CSV 추가)"""
import csv, glob, io, os
from datetime import datetime
from flask import Blueprint, Response, jsonify, request
import web.globals as g

download_bp = Blueprint('download', __name__)


# ── 관수 이력 CSV ─────────────────────────────────────────────────────────────

@download_bp.route('/api/download/irrigation-history')
def download_irrigation_history():
    """관수 이력 CSV (CSV 파일 기반, SQLite 폴백)"""
    date_from = request.args.get('from')
    date_to   = request.args.get('to')

    # ★ SQLite 경로 (Stage 14b 신규: DB 우선)
    if getattr(g, 'db_manager', None):
        try:
            start = f"{date_from} 00:00:00" if date_from else None
            end   = f"{date_to} 23:59:59"   if date_to   else None
            rows  = g.db_manager.query_irrigation_history(start=start, end=end)

            output   = io.StringIO()
            fieldnames = ['timestamp', 'zone_id', 'zone_name',
                          'duration_sec', 'trigger_type',
                          'water_before', 'status']
            writer = csv.DictWriter(output, fieldnames=fieldnames,
                                    extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
            fn = f"irrigation_history_{datetime.now().strftime('%Y%m%d')}.csv"
            return Response(
                '\ufeff' + output.getvalue(),
                mimetype='text/csv; charset=utf-8',
                headers={'Content-Disposition': f'attachment; filename={fn}'}
            )
        except Exception as e:
            pass  # SQLite 실패 시 CSV 폴백

    # ── CSV 파일 폴백 ─────────────────────────────────────
    csv_path = str(g._BASE_DIR / 'logs/irrigation_history.csv')
    if not os.path.exists(csv_path):
        return jsonify({'error': '관수 이력 파일 없음'}), 404
    try:
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if date_from and row.get('timestamp', '') < date_from: continue
                if date_to and row.get('timestamp', '') > date_to + ' 23:59:59': continue
                rows.append(row)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=['timestamp', 'zone_id', 'duration_sec',
                        'trigger', 'moisture_before', 'success']
        )
        writer.writeheader()
        writer.writerows(rows)
        fn = f"irrigation_history_{datetime.now().strftime('%Y%m%d')}.csv"
        return Response(
            '\ufeff' + output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={fn}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── 센서 데이터 CSV ───────────────────────────────────────────────────────────

@download_bp.route('/api/download/sensor-data')
def download_sensor_data():
    """탱크 수위 CSV (날짜별 센서 파일)"""
    log_dir   = str(g._BASE_DIR / 'logs')
    date_from = request.args.get('from')
    date_to   = request.args.get('to')
    try:
        files = sorted(glob.glob(os.path.join(log_dir, 'sensors_*.csv')))
        if date_from:
            files = [f for f in files if os.path.basename(f) >= f'sensors_{date_from}.csv']
        if date_to:
            files = [f for f in files if os.path.basename(f) <= f'sensors_{date_to}.csv']
        if not files:
            return jsonify({'error': '해당 기간 데이터 없음'}), 404
        output = io.StringIO()
        header_written = False
        for fpath in files:
            with open(fpath, 'r', encoding='utf-8') as f:
                rows = list(csv.reader(f))
                if not rows: continue
                if not header_written:
                    output.write(','.join(rows[0]) + '\n')
                    header_written = True
                for row in rows[1:]:
                    output.write(','.join(row) + '\n')
        fname_from = date_from or 'all'
        fname_to   = date_to   or datetime.now().strftime('%Y-%m-%d')
        fn = f"sensor_data_{fname_from}_to_{fname_to}.csv"
        return Response(
            '\ufeff' + output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={fn}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── ★ SHT30 공기 데이터 CSV (신규) ──────────────────────────────────────────

@download_bp.route('/api/download/air-data')
def download_air_data():
    """SHT30 온습도 이력 CSV (SQLite 기반)"""
    if not getattr(g, 'db_manager', None):
        return jsonify({'error': 'DBManager 미초기화'}), 503

    date_from = request.args.get('from')
    date_to   = request.args.get('to')

    try:
        start = f"{date_from} 00:00:00" if date_from else None
        end   = f"{date_to} 23:59:59"   if date_to   else None

        # CSV용: limit 없이 전체 조회 (대용량 가능, 스트리밍)
        rows = g.db_manager.query_air_readings(
            start=start, end=end, hours=720, limit=500_000
        )
        if not rows:
            return jsonify({'error': '해당 기간 공기 데이터 없음'}), 404

        output     = io.StringIO()
        fieldnames = list(rows[0].keys()) if rows else \
                     ['timestamp', 'zone_id', 'sensor_id',
                      'temperature', 'humidity', 'valid']
        writer = csv.DictWriter(output, fieldnames=fieldnames,
                                extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

        fname_from = date_from or 'all'
        fname_to   = date_to   or datetime.now().strftime('%Y-%m-%d')
        fn = f"air_data_{fname_from}_to_{fname_to}.csv"
        return Response(
            '\ufeff' + output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={fn}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── ★ WH65LP 날씨 데이터 CSV (신규) ──────────────────────────────────────────

@download_bp.route('/api/download/weather-data')
def download_weather_data():
    """WH65LP 날씨 이력 CSV (SQLite 기반)"""
    if not getattr(g, 'db_manager', None):
        return jsonify({'error': 'DBManager 미초기화'}), 503

    date_from = request.args.get('from')
    date_to   = request.args.get('to')

    try:
        start = f"{date_from} 00:00:00" if date_from else None
        end   = f"{date_to} 23:59:59"   if date_to   else None

        rows = g.db_manager.query_weather_readings(
            start=start, end=end, hours=720, limit=200_000
        )
        if not rows:
            return jsonify({'error': '해당 기간 날씨 데이터 없음'}), 404

        output     = io.StringIO()
        fieldnames = list(rows[0].keys()) if rows else \
                     ['timestamp', 'temperature', 'humidity',
                      'wind_speed', 'pressure', 'uv_index', 'rainfall']
        writer = csv.DictWriter(output, fieldnames=fieldnames,
                                extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

        fname_from = date_from or 'all'
        fname_to   = date_to   or datetime.now().strftime('%Y-%m-%d')
        fn = f"weather_data_{fname_from}_to_{fname_to}.csv"
        return Response(
            '\ufeff' + output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={fn}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── 파일 목록 ─────────────────────────────────────────────────────────────────

@download_bp.route('/api/download/files')
def list_download_files():
    log_dir = str(g._BASE_DIR / 'logs')
    result  = {'sensor_files': [], 'irrigation_csv': None}
    for fpath in sorted(glob.glob(os.path.join(log_dir, 'sensors_*.csv')), reverse=True):
        fname = os.path.basename(fpath)
        size  = os.path.getsize(fpath)
        rows  = 0
        try:
            with open(fpath, 'r') as f:
                rows = max(0, sum(1 for _ in f) - 1)
        except Exception:
            pass
        result['sensor_files'].append({
            'filename': fname,
            'date':     fname.replace('sensors_', '').replace('.csv', ''),
            'size_kb':  round(size / 1024, 1),
            'rows':     rows
        })
    irr_path = os.path.join(log_dir, 'irrigation_history.csv')
    if os.path.exists(irr_path):
        rows = 0
        try:
            with open(irr_path, 'r') as f:
                rows = max(0, sum(1 for _ in f) - 1)
        except Exception:
            pass
        result['irrigation_csv'] = {
            'filename': 'irrigation_history.csv',
            'size_kb':  round(os.path.getsize(irr_path) / 1024, 1),
            'rows':     rows
        }
    return jsonify({'success': True, 'data': result})
