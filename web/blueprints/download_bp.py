"""다운로드 Blueprint"""
import csv, glob, io, os
from datetime import datetime
from flask import Blueprint, Response, jsonify, request
import web.globals as g

download_bp = Blueprint('download', __name__)

@download_bp.route('/api/download/irrigation-history')
def download_irrigation_history():
    csv_path = str(g._BASE_DIR / 'logs/irrigation_history.csv')
    if not os.path.exists(csv_path): return jsonify({'error': '관수 이력 파일 없음'}), 404
    date_from = request.args.get('from'); date_to = request.args.get('to')
    try:
        rows = []
        with open(csv_path,'r',encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if date_from and row.get('timestamp','') < date_from: continue
                if date_to and row.get('timestamp','') > date_to+' 23:59:59': continue
                rows.append(row)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['timestamp','zone_id','duration_sec','trigger','moisture_before','success'])
        writer.writeheader(); writer.writerows(rows)
        filename = f"irrigation_history_{datetime.now().strftime('%Y%m%d')}.csv"
        return Response('\ufeff'+output.getvalue(), mimetype='text/csv; charset=utf-8',
                        headers={'Content-Disposition': f'attachment; filename={filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@download_bp.route('/api/download/sensor-data')
def download_sensor_data():
    log_dir = str(g._BASE_DIR / 'logs')
    date_from = request.args.get('from'); date_to = request.args.get('to')
    try:
        files = sorted(glob.glob(os.path.join(log_dir,'sensors_*.csv')))
        if date_from: files = [f for f in files if os.path.basename(f) >= f'sensors_{date_from}.csv']
        if date_to:   files = [f for f in files if os.path.basename(f) <= f'sensors_{date_to}.csv']
        if not files: return jsonify({'error': '해당 기간 데이터 없음'}), 404
        output = io.StringIO(); header_written = False
        for fpath in files:
            with open(fpath,'r',encoding='utf-8') as f:
                rows = list(csv.reader(f))
                if not rows: continue
                if not header_written:
                    output.write(','.join(rows[0])+'\n'); header_written = True
                for row in rows[1:]: output.write(','.join(row)+'\n')
        fname_from = date_from or 'all'
        fname_to   = date_to or datetime.now().strftime('%Y-%m-%d')
        filename   = f"sensor_data_{fname_from}_to_{fname_to}.csv"
        return Response('\ufeff'+output.getvalue(), mimetype='text/csv; charset=utf-8',
                        headers={'Content-Disposition': f'attachment; filename={filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@download_bp.route('/api/download/files')
def list_download_files():
    log_dir = str(g._BASE_DIR / 'logs')
    result  = {'sensor_files': [], 'irrigation_csv': None}
    for fpath in sorted(glob.glob(os.path.join(log_dir,'sensors_*.csv')), reverse=True):
        fname = os.path.basename(fpath); size = os.path.getsize(fpath); rows = 0
        try:
            with open(fpath,'r') as f: rows = max(0, sum(1 for _ in f)-1)
        except Exception: pass
        result['sensor_files'].append({'filename':fname,'date':fname.replace('sensors_','').replace('.csv',''),
                                        'size_kb':round(size/1024,1),'rows':rows})
    irr_path = os.path.join(log_dir,'irrigation_history.csv')
    if os.path.exists(irr_path):
        rows = 0
        try:
            with open(irr_path,'r') as f: rows = max(0, sum(1 for _ in f)-1)
        except Exception: pass
        result['irrigation_csv'] = {'filename':'irrigation_history.csv',
                                    'size_kb':round(os.path.getsize(irr_path)/1024,1),'rows':rows}
    return jsonify({'success': True, 'data': result})
