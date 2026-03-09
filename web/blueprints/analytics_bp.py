"""분석 Blueprint"""
import csv, glob, os, statistics
from flask import Blueprint, jsonify, render_template, request
import web.globals as g

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics')
def analytics():
    return render_template('analytics.html')

@analytics_bp.route('/api/analytics/sensor-data')
def analytics_sensor_data():
    log_dir = str(g._BASE_DIR / 'logs')
    date_from = request.args.get('from')
    date_to   = request.args.get('to')
    try:
        files = sorted(glob.glob(os.path.join(log_dir, 'sensors_*.csv')))
        if date_from: files = [f for f in files if os.path.basename(f) >= f'sensors_{date_from}.csv']
        if date_to:   files = [f for f in files if os.path.basename(f) <= f'sensors_{date_to}.csv']
        rows = []
        for fpath in files:
            with open(fpath, 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f): rows.append(row)
        def calc_stats(values, rows_ref):
            vals = [float(v) for v in values if v not in ('', None)]
            if not vals: return {'count':0,'avg':0,'min':0,'max':0,'first_timestamp':'','last_timestamp':''}
            ts = [r.get('timestamp','') for r in rows_ref]
            return {'count':len(vals),'avg':round(statistics.mean(vals),1),'min':round(min(vals),1),
                    'max':round(max(vals),1),'first_timestamp':ts[0] if ts else '','last_timestamp':ts[-1] if ts else ''}
        MAX_ROWS = 2000
        step = max(1, len(rows) // MAX_ROWS)
        return jsonify({'success':True,'data':rows[::step],'total':len(rows),
                        'stats':{'tank1':calc_stats([r.get('tank1_level','') for r in rows],rows),
                                 'tank2':calc_stats([r.get('tank2_level','') for r in rows],rows)}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/api/analytics/irrigation-history')
def analytics_irrigation_history():
    csv_path = str(g._BASE_DIR / 'logs/irrigation_history.csv')
    date_from = request.args.get('from')
    date_to   = request.args.get('to')
    if not os.path.exists(csv_path):
        if g.auto_irrigation:
            return jsonify({'success':True,'data':list(reversed(g.auto_irrigation.irrigation_history)),'source':'memory'})
        return jsonify({'success':True,'data':[],'source':'empty'})
    try:
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                ts = row.get('timestamp','')
                if date_from and ts < date_from: continue
                if date_to and ts > date_to+' 23:59:59': continue
                rows.append(row)
        return jsonify({'success':True,'data':list(reversed(rows)),'total':len(rows),'source':'csv'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
