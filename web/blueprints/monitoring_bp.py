"""
모니터링 Blueprint (web/blueprints/monitoring_bp.py)
"""
import os
import threading
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
import web.globals as g

monitoring_bp = Blueprint('monitoring', __name__)

@monitoring_bp.route('/api/status')
def get_status():
    try:
        status = {
            'monitoring_active': g.monitoring_active,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        if g.sensor_monitor and g.monitoring_active:
            history = g.sensor_monitor.get_history(limit=1)
            if history:
                last_data = history[0]
                ts = last_data['timestamp']
                ts_str = ts if isinstance(ts, str) else ts.strftime('%Y-%m-%d %H:%M:%S')
                status.update({
                    'timestamp':   ts_str,
                    'tank1_level': round(last_data['tank1_level'], 1),
                    'tank2_level': round(last_data['tank2_level'], 1),
                    'voltages':    [round(v, 3) for v in last_data['voltages']]
                })
            else:
                status.update({
                    'tank1_level': round(g.cached_sensor_data.get('tank1_level', 0.0), 1),
                    'tank2_level': round(g.cached_sensor_data.get('tank2_level', 0.0), 1),
                    'voltages':    [round(v, 3) for v in g.cached_sensor_data.get('voltages', [0.0]*4)]
                })
                if g.cached_sensor_data.get('timestamp'):
                    status['timestamp'] = g.cached_sensor_data['timestamp']
        else:
            status.update({'tank1_level': 0.0, 'tank2_level': 0.0, 'voltages': [0.0]*4})
        if g.alert_manager:
            as_ = g.alert_manager.get_current_status()
            status.update({
                'alert_count_24h':    as_['alert_count_24h'],
                'critical_count_24h': as_['critical_count_24h'],
                'warning_count_24h':  as_['warning_count_24h']
            })
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    try:
        if not g.sensor_monitor:
            return jsonify({'error': '모니터링 시스템이 초기화되지 않았습니다'}), 500
        if g.monitoring_active:
            return jsonify({'message': '이미 모니터링 중입니다'})
        g.monitoring_active = True
        from web.app import periodic_data_sender
        t = threading.Thread(target=periodic_data_sender, daemon=True)
        t.start()
        g.monitoring_thread = t
        return jsonify({'message': '모니터링 시작됨'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/api/stop_monitoring', methods=['POST'])
def stop_monitoring():
    try:
        if not g.sensor_monitor:
            return jsonify({'error': '모니터링 시스템이 초기화되지 않았습니다'}), 500
        if not g.monitoring_active:
            return jsonify({'message': '모니터링이 실행 중이 아닙니다'})
        g.monitoring_active = False
        return jsonify({'message': '모니터링 중지됨'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/api/alerts')
def get_alerts():
    try:
        if not g.alert_manager:
            return jsonify({'error': 'AlertManager가 초기화되지 않았습니다'}), 500
        limit = request.args.get('limit', 20, type=int)
        level = request.args.get('level', None)
        alert_level = None
        if level:
            try:
                from monitoring.alert_manager import AlertLevel
                alert_level = AlertLevel[level.upper()]
            except KeyError:
                pass
        alerts = g.alert_manager.get_alert_history(level=alert_level, limit=limit)
        return jsonify({'alerts': [a.to_dict() for a in alerts]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/api/data_history')
def get_data_history():
    try:
        if not g.data_logger:
            return jsonify({'error': 'DataLogger가 초기화되지 않았습니다'}), 500
        hours = request.args.get('hours', 24, type=int)
        end_date   = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        data = g.data_logger.get_data(start_date=start_date, end_date=end_date)
        return jsonify({'data': data[-100:] if len(data) > 100 else data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/api/statistics')
def get_statistics():
    try:
        if not g.data_logger:
            return jsonify({'error': 'DataLogger가 초기화되지 않았습니다'}), 500
        hours = request.args.get('hours', 24, type=int)
        end_date   = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        t1 = g.data_logger.get_statistics(start_date=start_date, end_date=end_date, tank_num=1)
        t2 = g.data_logger.get_statistics(start_date=start_date, end_date=end_date, tank_num=2)
        return jsonify({'tank1': t1, 'tank2': t2})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def validate_voltage(value, field_name):
    try:
        num = float(value)
        if not (0 <= num <= 5.0):
            raise ValueError(f"{field_name}는 0V ~ 5.0V 범위여야 합니다 (입력값: {num}V)")
        return round(num, 3)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name}는 유효한 숫자가 아닙니다")

@monitoring_bp.route('/api/calibration', methods=['GET'])
def get_calibration():
    try:
        import json
        config_path = str(g._BASE_DIR / 'config/sensor_calibration.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({
            'sensor_type': 'voltage',
            'tank1_water':    {'empty_value': 0.5, 'full_value': 4.5, 'calibrated_at': None},
            'tank2_nutrient': {'empty_value': 0.5, 'full_value': 4.5, 'calibrated_at': None}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/api/calibration', methods=['POST'])
def save_calibration():
    try:
        import json
        data        = request.get_json()
        config_path = str(g._BASE_DIR / 'config/sensor_calibration.json')
        if data.get('update_type_only'):
            calibration = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    calibration = json.load(f)
            calibration['sensor_type']  = data.get('sensor_type', 'voltage')
            calibration['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            calibration = {
                'sensor_type': data.get('sensor_type', 'voltage'), 'last_updated': now,
                'tank1_water': {
                    'empty_value': validate_voltage(data['tank1_water']['empty_value'], 'Tank 1 Empty'),
                    'full_value':  validate_voltage(data['tank1_water']['full_value'],  'Tank 1 Full'),
                    'calibrated_at': now
                },
                'tank2_nutrient': {
                    'empty_value': validate_voltage(data['tank2_nutrient']['empty_value'], 'Tank 2 Empty'),
                    'full_value':  validate_voltage(data['tank2_nutrient']['full_value'],  'Tank 2 Full'),
                    'calibrated_at': now
                }
            }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(calibration, f, indent=2, ensure_ascii=False)
        g.sensor_monitor.load_calibration(config_path)
        new_data = g.sensor_monitor._collect_sensor_data()
        g.sensor_monitor._last_data = new_data
        g.cached_sensor_data.update(new_data)
        return jsonify({'success': True, 'message': '캘리브레이션 설정이 저장되고 적용되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@monitoring_bp.route('/api/calibration/current', methods=['GET'])
def get_current_sensor_values():
    try:
        import json
        config_path = str(g._BASE_DIR / 'config/sensor_calibration.json')
        calibration = {}
        sensor_type = 'voltage'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                calibration = json.load(f)
                sensor_type = calibration.get('sensor_type', 'voltage')
        voltages    = g.cached_sensor_data.get('voltages', [0]*4)
        return jsonify({
            'success': True, 'sensor_type': sensor_type,
            'tank1_value': voltages[0] if len(voltages) > 0 else 0,
            'tank2_value': voltages[1] if len(voltages) > 1 else 0,
            'tank1_water':   calibration.get('tank1_water', {}),
            'tank2_nutrient': calibration.get('tank2_nutrient', {})
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
