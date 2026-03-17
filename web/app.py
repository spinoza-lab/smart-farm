"""
Flask 웹 대시보드 메인 애플리케이션 (Blueprint 리팩터링)
버전: v0.4.1 (refactor/blueprint)
"""
import os, sys, signal, threading, time, json, atexit
from pathlib import Path
from datetime import datetime

_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(_BASE_DIR))

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-farm-secret-2026'

import time as _time
_CACHE_VER = str(int(_time.time()))

@app.context_processor
def inject_cache_ver():
    return dict(cache_ver=_CACHE_VER)

socketio = SocketIO(app, cors_allowed_origins="*")

import web.globals as g
g._BASE_DIR = _BASE_DIR

from monitoring.sensor_monitor import SensorMonitor
from hardware.relay_controller import RelayController
from hardware.modbus_soil_sensor import SoilSensorManager
from irrigation.auto_controller import AutoIrrigationController
from irrigation.scheduler import IrrigationScheduler
from database.db_manager import DBManager
from monitoring.data_logger import DataLogger
from monitoring.alert_manager import AlertManager
from monitoring.telegram_notifier import TelegramNotifier

from web.blueprints.monitoring_bp    import monitoring_bp
from web.blueprints.irrigation_bp    import irrigation_bp
from web.blueprints.analytics_bp     import analytics_bp
from web.blueprints.notifications_bp import notifications_bp
from web.blueprints.download_bp      import download_bp
from web.blueprints.environment_bp import environment_bp

app.register_blueprint(monitoring_bp)
app.register_blueprint(irrigation_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(download_bp)
app.register_blueprint(environment_bp)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/irrigation')
def irrigation(): return render_template('irrigation.html')

@app.route('/settings')
def settings(): return render_template('settings.html')

@socketio.on('connect')
def handle_connect(): emit('connected', {'message': '서버에 연결되었습니다'})

@socketio.on('disconnect')
def handle_disconnect(): pass

@socketio.on('request_status')
def handle_request_status():
    ts_obj = g.cached_sensor_data.get('timestamp', '')
    ts_str = ts_obj if isinstance(ts_obj, str) else ts_obj.strftime('%Y-%m-%d %H:%M:%S')
    emit('sensor_update', {
        'timestamp':   ts_str,
        'tank1_level': round(g.cached_sensor_data.get('tank1_level', 0), 1),
        'tank2_level': round(g.cached_sensor_data.get('tank2_level', 0), 1),
        'voltages':    [round(v, 3) for v in g.cached_sensor_data.get('voltages', [0,0,0,0])]
    })

def periodic_data_sender():
    print("🔄 periodic_data_sender 스레드 시작")
    consecutive_errors = 0
    while g.monitoring_active:
        try:
            if g.sensor_monitor:
                status = g.sensor_monitor._collect_sensor_data()
                g.cached_sensor_data.update({
                    'timestamp': status['timestamp'], 'voltages': status['voltages'],
                    'tank1_level': status['tank1_level'], 'tank2_level': status['tank2_level'],
                    'sensor_type': g.sensor_monitor.sensor_reader.calibration.get('sensor_type', 'voltage')
                })
                g.sensor_monitor._add_to_history(status)
                ts_obj = status['timestamp']
                ts_str = ts_obj if isinstance(ts_obj, str) else ts_obj.strftime('%Y-%m-%d %H:%M:%S')
                ts_dt  = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S') if isinstance(ts_obj, str) else ts_obj
                if g.data_logger:
                    g.data_logger.log_sensor_data(
                        tank1_level=status['tank1_level'], tank2_level=status['tank2_level'],
                        voltages=status['voltages'], timestamp=ts_dt)
                if g.alert_manager:
                    g.alert_manager.check_water_level(1, status['tank1_level'])
                    g.alert_manager.check_water_level(2, status['tank2_level'])
                    for i, v in enumerate(status['voltages']): g.alert_manager.check_sensor_error(v, i)
                socketio.emit('sensor_update', {
                    'timestamp': ts_str,
                    'tank1_level': round(status['tank1_level'], 1),
                    'tank2_level': round(status['tank2_level'], 1),
                    'voltages': [round(v, 3) for v in status['voltages']]
                })
            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            print(f"❌ 주기적 데이터 전송 오류 ({consecutive_errors}회 연속): {e}")
            if consecutive_errors == 10:
                try:
                    if g.telegram_notifier:
                        g.telegram_notifier.send(f'🚨 [시스템 경고]\nperiodic_data_sender 10회 연속 오류\n마지막 오류: {e}')
                except Exception: pass
        try: time.sleep(10)
        except Exception: pass
    print("⏹️  periodic_data_sender 스레드 종료")

def _start_periodic_sender():
    t = threading.Thread(target=periodic_data_sender, daemon=True, name="PeriodicSender")
    t.start(); g.monitoring_thread = t
    print("🔄 periodic_data_sender 스레드 (재)시작됨")
    return t

def _watchdog_loop():
    print("🐕 watchdog 스레드 시작")
    while g.monitoring_active:
        time.sleep(30)
        if not g.monitoring_active: break
        if g.monitoring_thread is None or not g.monitoring_thread.is_alive():
            if g.monitoring_active:
                print("⚠️  [watchdog] periodic_data_sender 스레드 죽음 → 재시작")
                try:
                    if g.telegram_notifier: g.telegram_notifier.send('⚠️ [시스템 복구]\nperiodic_data_sender 스레드 재시작됨')
                except Exception: pass
                _start_periodic_sender()
    print("🐕 watchdog 스레드 종료")

def init_monitoring_system():
    try:
        # Stage 11: SQLite DBManager 초기화
        try:
            g.db_manager = DBManager()
            print("✅ DBManager 초기화 완료")
        except Exception as _e:
            print(f"⚠️  DBManager 초기화 실패: {_e}")
            g.db_manager = None
        g.data_logger = DataLogger(log_dir=str(_BASE_DIR / 'logs'), db_manager=g.db_manager)
        try:
            with open(str(_BASE_DIR / 'config/notifications.json')) as f:
                _nc = json.load(f)
            _thr = _nc.get('thresholds', {})
            _t1_min = float(_thr.get('tank1_min', 20.0)); _t1_max = float(_thr.get('tank1_max', 90.0))
            _t2_min = float(_thr.get('tank2_min', 20.0)); _t2_max = float(_thr.get('tank2_max', 90.0))
            _cooldown = int(_nc.get('cooldown_seconds', 300))
            _cooldown_sm = int(_nc.get('sensor_monitor_cooldown', 300))  # BUG-18: SM 쿨다운
        except Exception as e:
            print(f'[Init] thresholds 로드 실패: {e}')
            _t1_min=_t2_min=20.0; _t1_max=_t2_max=90.0; _cooldown=300; _cooldown_sm=300
        g.sensor_monitor = SensorMonitor(config={
            'check_interval': 10, 'sample_count': 10,
            'outlier_remove': 2, 'min_water_level': 20.0, 'max_water_level': 90.0,
            'alert_cooldown': _cooldown_sm  # BUG-18: notifications.json에서 읽기
        })
        g.alert_manager = AlertManager(tank1_min=_t1_min, tank1_max=_t1_max, tank2_min=_t2_min, tank2_max=_t2_max,
                                        cooldown_seconds=_cooldown, log_file=str(_BASE_DIR/'logs/alerts.log'), db_manager=g.db_manager)
        def alert_callback(alert):
            socketio.emit('new_alert', {'timestamp':alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'level':alert.level.value,'type':alert.alert_type.value,'message':alert.message,
                'tank_num':alert.tank_num,'value':alert.value})
        g.alert_manager.add_callback(alert_callback)
        g.relay_controller = RelayController()
        try:
            g.soil_sensor_manager = SoilSensorManager()
            g.auto_irrigation = AutoIrrigationController(
                sensor_manager=g.soil_sensor_manager, relay_controller=g.relay_controller)
            def _get_tank1_level(): return g.cached_sensor_data.get('tank1_level')
            g.auto_irrigation.get_tank_level_callback = _get_tank1_level
            try:
                g.irrigation_scheduler = IrrigationScheduler(g.auto_irrigation)
                from web.globals import _load_soil_config
                _b_mode = _load_soil_config().get('irrigation', {}).get('mode', 'auto')
                g.auto_irrigation.set_mode(_b_mode)
                g.auto_irrigation.attach_scheduler(g.irrigation_scheduler)
                print(f"[Init] 스케줄러 연결 완료 (running={g.irrigation_scheduler._running})")
                try:
                    with open(str(_BASE_DIR/'config/notifications.json')) as f: _nc = json.load(f)
                    _tc = _nc.get("telegram", {})
                    if _tc.get("enabled", False):
                        g.telegram_notifier = TelegramNotifier(token=_tc["token"], chat_id=_tc["chat_id"])
                        g.alert_manager.add_callback(g.telegram_notifier.notify_alert)
                        g.telegram_notifier.start_polling(controller=g.auto_irrigation)
                        g.telegram_notifier.notify_server_start()
                        print("✅ 텔레그램 알림 초기화 완료")
                        import sys as _s; _s.modules[__name__].telegram_notifier = g.telegram_notifier  # auto_controller 호환 alias
                except Exception as e: print(f"⚠️ 텔레그램 초기화 실패: {e}")
            except Exception as e: print(f"⚠️  IrrigationScheduler 초기화 실패: {e}"); g.irrigation_scheduler = None
        except Exception as e:
            print(f"⚠️  토양 센서 초기화 실패: {e}"); g.soil_sensor_manager = None; g.auto_irrigation = None
        # Stage 10: 환경 모니터링 초기화
        try:
            from hardware.air_sensor_reader      import AirSensorManager
            from hardware.weather_station_reader import WeatherStationReader
            from monitoring.environment_monitor  import EnvironmentMonitor
            g.air_sensor_manager  = AirSensorManager()
            g.weather_station     = WeatherStationReader()
            g.environment_monitor = EnvironmentMonitor(
                air_sensor_manager=g.air_sensor_manager,
                weather_station_reader=g.weather_station,
                db_manager=g.db_manager
            )
            g.environment_monitor.start()
            print("✅ 환경 모니터링 초기화 완료 (SHT30 + WH65LP)")
        except Exception as e:
            print(f"⚠️  환경 모니터링 초기화 실패: {e}")
        print("✅ 모니터링 시스템 초기화 완료")
        g.monitoring_active = True
        _start_periodic_sender()
        threading.Thread(target=_watchdog_loop, daemon=True, name="SenderWatchdog").start()
        print("🚀 모니터링 자동 시작됨")
        return True
    except Exception as e:
        print(f"❌ 모니터링 시스템 초기화 실패: {e}"); import traceback; traceback.print_exc(); return False

def _emergency_relay_off():
    try:
        if g.relay_controller: g.relay_controller.all_off(); print("✅ [종료] 모든 릴레이 OFF 완료")
    except Exception as e: print(f"⚠️ [종료] 릴레이 OFF 실패: {e}")

atexit.register(_emergency_relay_off)

def _graceful_shutdown(signum, frame):
    sig_name = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
    print(f"\n🛑 [{sig_name}] 수신 - 안전 종료 시작")
    try:
        if g.auto_irrigation and g.auto_irrigation.is_irrigating:
            g.auto_irrigation._stop_requested = True; time.sleep(2)
    except Exception as e: print(f"  ⚠️ 관수 중단 오류: {e}")
    try:
        if g.environment_monitor: g.environment_monitor.stop(); print("✅ [종료] 환경 모니터 정지")
    except Exception as e: print(f"⚠️ [종료] 환경 모니터 정지 실패: {e}")
    _emergency_relay_off()
    print("✅ 안전 종료 완료"); sys.exit(0)

if __name__ == '__main__':
    print("="*60)
    print("🌐 스마트 관수 시스템 v0.4.1 (Blueprint)")
    print("="*60)
    if init_monitoring_system():
        signal.signal(signal.SIGTERM, _graceful_shutdown)
        signal.signal(signal.SIGINT,  _graceful_shutdown)
        socketio.run(app, host='0.0.0.0', port=5000, debug=False,
                     use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        print("❌ 시스템 초기화 실패")
