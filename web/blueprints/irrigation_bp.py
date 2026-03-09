"""
관수 Blueprint (web/blueprints/irrigation_bp.py)
"""
import threading
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
import web.globals as g
from web.globals import _load_soil_config, _save_soil_config, _load_schedules, _save_schedules

irrigation_bp = Blueprint('irrigation', __name__)

# ── 호스건 ───────────────────────────────────────────────────────
@irrigation_bp.route('/api/hose-gun/status', methods=['GET'])
def get_hose_gun_status():
    try:
        if not g.relay_controller:
            return jsonify({'error': 'RelayController가 초기화되지 않았습니다'}), 500
        return jsonify({'active': g.relay_controller.get_hand_gun_status()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@irrigation_bp.route('/api/hose-gun/activate', methods=['POST'])
def activate_hose_gun():
    try:
        if not g.relay_controller:
            return jsonify({'error': 'RelayController가 초기화되지 않았습니다'}), 500
        g.relay_controller.hand_gun_on()
        return jsonify({'success': True, 'message': '호스건이 활성화되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/hose-gun/deactivate', methods=['POST'])
def deactivate_hose_gun():
    try:
        if g.relay_controller is None:
            return jsonify({'success': False, 'error': 'RelayController 초기화 안됨'}), 500
        g.relay_controller.hand_gun_off()
        return jsonify({'success': True, 'message': '호스건이 비활성화되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ── 관수 제어 ─────────────────────────────────────────────────────
@irrigation_bp.route('/api/irrigation/status')
def get_irrigation_status():
    if g.auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 초기화 안됨'}), 503
    return jsonify({'success': True, 'data': g.auto_irrigation.get_status()})

@irrigation_bp.route('/api/irrigation/mode', methods=['POST'])
def set_irrigation_mode():
    if g.auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    mode = request.json.get('mode')
    ok, msg = g.auto_irrigation.set_mode(mode)
    if ok:
        try:
            cfg = _load_soil_config()
            cfg.setdefault('irrigation', {})['mode'] = mode
            _save_soil_config(cfg)
        except Exception as e:
            print(f"[Mode] 설정 저장 실패: {e}")
    return jsonify({'success': ok, 'message': msg})

@irrigation_bp.route('/api/irrigation/start', methods=['POST'])
def start_irrigation():
    if g.auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    zone_id  = request.json.get('zone_id')
    duration = request.json.get('duration', 300)
    if not zone_id:
        return jsonify({'success': False, 'error': 'zone_id 필요'}), 400
    if g.auto_irrigation.is_irrigating:
        return jsonify({'success': False,
                        'error': f'이미 관수 중 (구역 {g.auto_irrigation.current_zone})'}), 409
    def run():
        g.auto_irrigation.irrigate_zone(int(zone_id), int(duration))
    threading.Thread(target=run, daemon=True).start()
    return jsonify({'success': True, 'message': f'구역 {zone_id} 관수 시작 ({duration}초)'})

@irrigation_bp.route('/api/irrigation/stop', methods=['POST'])
def stop_irrigation():
    try:
        if g.relay_controller:
            g.relay_controller.emergency_stop()
        if g.auto_irrigation:
            stop_fn = getattr(g.auto_irrigation, "stop_irrigation", None)
            if callable(stop_fn):
                stop_fn()
            else:
                g.auto_irrigation.is_irrigating = False
                g.auto_irrigation.current_zone  = None
        return jsonify({'success': True, 'message': '관수 긴급 정지 완료'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/irrigation/sensors')
def get_soil_sensors():
    if g.auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    data = g.auto_irrigation.get_sensor_data()
    return jsonify({'success': True, 'data': data, 'count': len(data)})

@irrigation_bp.route('/api/irrigation/sensors/read', methods=['POST'])
def refresh_soil_sensors():
    if g.soil_sensor_manager is None:
        return jsonify({'success': False, 'error': '센서 없음'}), 503
    try:
        results = g.soil_sensor_manager.read_all_zones()
        if g.auto_irrigation:
            g.auto_irrigation.last_sensor_data = results
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/irrigation/threshold', methods=['POST'])
def set_threshold():
    if g.auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    zone_id   = request.json.get('zone_id')
    threshold = request.json.get('threshold')
    if zone_id is None or threshold is None:
        return jsonify({'success': False, 'error': 'zone_id, threshold 필요'}), 400
    g.auto_irrigation.zone_thresholds[int(zone_id)] = float(threshold)
    return jsonify({'success': True, 'message': f'구역 {zone_id} 임계값 → {threshold}%'})

@irrigation_bp.route('/api/irrigation/history')
def get_irrigation_history():
    if g.auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    limit   = int(request.args.get('limit', 20))
    history = g.auto_irrigation.irrigation_history[-limit:]
    return jsonify({'success': True, 'data': list(reversed(history)),
                    'total': len(g.auto_irrigation.irrigation_history)})

# ── 관수 설정 ─────────────────────────────────────────────────────
@irrigation_bp.route('/api/irrigation/config', methods=['GET'])
def get_irrigation_config():
    try:
        cfg  = _load_soil_config()
        irr  = cfg.get('irrigation', {})
        irr['mode'] = g.auto_irrigation.mode if g.auto_irrigation else 'manual'
        return jsonify({'success': True, 'config': irr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/irrigation/config', methods=['POST'])
def save_irrigation_config():
    try:
        data = request.get_json()
        cfg  = _load_soil_config()
        irr  = cfg.get('irrigation', {})
        for k, t in [('check_interval', int), ('irrigation_duration', int),
                     ('zone_interval', int)]:
            if k in data: irr[k] = t(data[k])
        if 'min_tank_level' in data: irr['min_tank_level'] = float(data['min_tank_level'])
        cfg['irrigation'] = irr
        _save_soil_config(cfg)
        if g.auto_irrigation:
            g.auto_irrigation.irrigation_cfg = irr
        return jsonify({'success': True, 'message': '관수 기본 설정이 저장되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/irrigation/thresholds', methods=['GET'])
def get_irrigation_thresholds():
    try:
        cfg = _load_soil_config()
        return jsonify({'success': True, 'thresholds': [
            {'zone_id': s['zone_id'], 'name': s.get('name', f"구역 {s['zone_id']}"),
             'threshold': s.get('moisture_threshold', 40.0)}
            for s in cfg.get('sensors', [])
        ]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/irrigation/thresholds', methods=['POST'])
def save_irrigation_thresholds():
    try:
        data       = request.get_json()
        thresholds = data.get('thresholds', [])
        cfg        = _load_soil_config()
        thr_map    = {int(t['zone_id']): float(t['threshold']) for t in thresholds}
        for sensor in cfg.get('sensors', []):
            zid = int(sensor['zone_id'])
            if zid in thr_map:
                sensor['moisture_threshold'] = thr_map[zid]
        _save_soil_config(cfg)
        if g.auto_irrigation:
            g.auto_irrigation.zone_thresholds.update(thr_map)
        return jsonify({'success': True, 'message': f'{len(thresholds)}개 구역 임계값이 저장되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ── 스케줄 관리 ────────────────────────────────────────────────────
@irrigation_bp.route('/api/schedules/next', methods=['GET'])
def get_next_schedule():
    from datetime import datetime as _dt, timedelta as _td
    def _calc_minutes_until(start_time_str, days):
        now = _dt.now()
        try:
            h, m = map(int, start_time_str.split(':'))
        except Exception:
            return None
        best = None
        for delta_day in range(8):
            target = now.replace(hour=h, minute=m, second=0, microsecond=0) + _td(days=delta_day)
            if target <= now: continue
            dow = target.weekday()
            if days and dow not in days: continue
            diff_min = int((target - now).total_seconds() // 60)
            if best is None or diff_min < best: best = diff_min
        return best
    def _calc_minutes_until_routine(start_date_str, start_time_str, interval_days):
        now = _dt.now()
        try:
            h, m = map(int, start_time_str.split(':'))
            base = _dt.strptime(start_date_str, '%Y-%m-%d').replace(hour=h, minute=m)
        except Exception:
            return None
        if interval_days < 1: interval_days = 1
        delta = (now - base).total_seconds()
        if delta < 0:
            next_run = base
        else:
            cycles   = int(delta // (interval_days * 86400)) + 1
            next_run = base + _td(days=cycles * interval_days)
        return int((next_run - now).total_seconds() // 60)
    if g.irrigation_scheduler and g.irrigation_scheduler._running:
        try:
            items = g.irrigation_scheduler.get_next_schedules(limit=1) or []
            if items:
                s = items[0]
                if 'minutes_until' not in s:
                    if not s.get('start_time') and s.get('next_run'):
                        try: s['start_time'] = s['next_run'].split(' ')[1][:5]
                        except Exception: pass
                    if s.get('next_run'):
                        try:
                            _nrdt = _dt.strptime(s['next_run'], '%Y-%m-%d %H:%M')
                            s['minutes_until'] = max(int((_nrdt - _dt.now()).total_seconds() // 60), 0)
                        except Exception:
                            s['minutes_until'] = _calc_minutes_until(s.get('start_time','00:00'), s.get('days',[])) or 0
                    elif s.get('start_time'):
                        s['minutes_until'] = _calc_minutes_until(s['start_time'], s.get('days',[])) or 0
                return jsonify({'success': True, 'next_schedule': s})
        except Exception:
            pass
    try:
        data      = _load_schedules()
        schedules = [s for s in data.get('schedules', []) if s.get('enabled', True)]
        if not schedules:
            return jsonify({'success': True, 'next_schedule': None, 'message': '예정된 스케줄 없음'})
        best_s, best_min = None, None
        for s in schedules:
            stype = s.get('type', 'schedule')
            if stype == 'routine':
                mins = _calc_minutes_until_routine(s.get('start_date',''), s.get('start_time','00:00'), s.get('interval_days',1))
            else:
                mins = _calc_minutes_until(s.get('start_time','00:00'), s.get('days',[]))
            if mins is not None and (best_min is None or mins < best_min):
                best_s, best_min = s, mins
        if best_s:
            best_s = dict(best_s)
            best_s['minutes_until'] = best_min
            return jsonify({'success': True, 'next_schedule': best_s})
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {e}'}), 500
    return jsonify({'success': True, 'next_schedule': None, 'message': '예정된 스케줄 없음'})

@irrigation_bp.route('/api/schedules/status', methods=['GET'])
def get_scheduler_status():
    if not g.irrigation_scheduler:
        return jsonify({'success': False, 'running': False, 'message': '초기화 안 됨'})
    next_s = g.irrigation_scheduler.get_next_schedule()
    return jsonify({'success': True, 'running': g.irrigation_scheduler._running,
                    'next_schedule': next_s, 'check_interval': 30})

@irrigation_bp.route('/api/schedules', methods=['GET'])
def get_schedules():
    try:
        data = _load_schedules()
        return jsonify({'success': True, 'schedules': data.get('schedules', [])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/schedules', methods=['POST'])
def add_schedule():
    try:
        body     = request.get_json(force=True) or {}
        stype    = body.get('type', 'schedule')
        zone_id  = int(body.get('zone_id', 0))
        duration = int(body.get('duration', 300))
        if zone_id is None:
            return jsonify({'success': False, 'error': 'zone_id 필수'}), 400
        data      = _load_schedules()
        schedules = data.get('schedules', [])
        new_id    = max((s.get('id', 0) for s in schedules), default=0) + 1
        if stype == 'routine':
            start_date     = body.get('start_date', '')
            start_time     = body.get('start_time', '06:00')
            interval_days  = int(body.get('interval_days', 1))
            check_moisture = bool(body.get('check_moisture', False))
            if not start_date or not start_time:
                return jsonify({'success': False, 'error': 'routine: start_date, start_time 필수'}), 400
            new_s = {'id': new_id, 'type': 'routine', 'zone_id': zone_id, 'duration': duration,
                     'start_date': start_date, 'start_time': start_time,
                     'interval_days': interval_days, 'check_moisture': check_moisture,
                     'enabled': True, 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        else:
            start_time = body.get('start_time', '')
            days       = [int(d) for d in body.get('days', [])]
            if not start_time:
                return jsonify({'success': False, 'error': 'schedule: start_time 필수'}), 400
            try: datetime.strptime(start_time, '%H:%M')
            except ValueError:
                return jsonify({'success': False, 'error': '시간 형식이 HH:MM이어야 합니다'}), 400
            new_s = {'id': new_id, 'type': 'schedule', 'zone_id': zone_id,
                     'start_time': start_time, 'duration': duration, 'days': days,
                     'enabled': True, 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        schedules.append(new_s)
        _save_schedules({'schedules': schedules})
        return jsonify({'success': True, 'schedule': new_s, 'message': f'스케줄 #{new_id}가 추가되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    try:
        data      = _load_schedules()
        schedules = data.get('schedules', [])
        new_list  = [s for s in schedules if s.get('id') != schedule_id]
        if len(new_list) == len(schedules):
            return jsonify({'success': False, 'error': f'스케줄 #{schedule_id} 없음'}), 404
        _save_schedules({'schedules': new_list})
        return jsonify({'success': True, 'message': f'스케줄 #{schedule_id}가 삭제되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/schedules/<int:schedule_id>', methods=['PATCH'])
def toggle_schedule(schedule_id):
    try:
        data      = _load_schedules()
        schedules = data.get('schedules', [])
        target    = next((s for s in schedules if s.get('id') == schedule_id), None)
        if target is None:
            return jsonify({'success': False, 'error': f'스케줄 #{schedule_id} 없음'}), 404
        target['enabled'] = not target.get('enabled', True)
        _save_schedules({'schedules': schedules})
        state = '활성화' if target['enabled'] else '비활성화'
        return jsonify({'success': True, 'enabled': target['enabled'],
                        'message': f'스케줄 #{schedule_id} {state}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@irrigation_bp.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    try:
        body      = request.get_json(force=True) or {}
        data      = _load_schedules()
        schedules = data.get('schedules', [])
        target    = next((s for s in schedules if s.get('id') == schedule_id), None)
        if not target:
            return jsonify({'success': False, 'error': f'스케줄 #{schedule_id} 없음'}), 404
        for field in ('zone_id', 'start_time', 'duration', 'days', 'enabled'):
            if field in body:
                val = body[field]
                if   field == 'zone_id':  val = int(val)
                elif field == 'duration': val = int(val)
                elif field == 'days':     val = [int(d) for d in val]
                elif field == 'enabled':  val = bool(val)
                target[field] = val
        stype = body.get('type', target.get('type', 'schedule'))
        target['type'] = stype
        if stype == 'routine':
            for k in ('start_date', 'interval_days', 'check_moisture'):
                if k in body:
                    target[k] = int(body[k]) if k == 'interval_days' else \
                                 bool(body[k]) if k == 'check_moisture' else body[k]
        _save_schedules({'schedules': schedules})
        return jsonify({'success': True, 'schedule': target,
                        'message': f'스케줄 #{schedule_id} 수정 완료'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
