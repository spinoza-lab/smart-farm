"""
Flask 웹 대시보드 메인 애플리케이션

실시간 센서 모니터링 및 제어 웹 인터페이스

작성자: spinoza-lab
날짜: 2026-02-12
버전: v2 (timestamp 타입 체크 + SensorMonitor.start() 제거)
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import sys
import os
from datetime import datetime, timedelta
import threading
import time

# 상위 디렉터리의 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.sensor_monitor import SensorMonitor
from hardware.relay_controller import RelayController
from hardware.modbus_soil_sensor import SoilSensorManager
from irrigation.auto_controller import AutoIrrigationController
from monitoring.data_logger import DataLogger
from monitoring.alert_manager import AlertManager, AlertLevel

# Flask 앱 초기화
app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-farm-secret-2026'

# SocketIO 초기화 (실시간 통신)
socketio = SocketIO(app, cors_allowed_origins="*")

# 전역 객체
sensor_monitor = None
data_logger = None
alert_manager = None
relay_controller = None
soil_sensor_manager = None
auto_irrigation = None
monitoring_active = False
monitoring_thread = None

# 🔥 센서 값 캐시 (샘플링 중복 방지)
cached_sensor_data = {
    'timestamp': None,
    'voltages': [0.0, 0.0, 0.0, 0.0],
    'tank1_level': 0.0,
    'tank2_level': 0.0,
    'sensor_type': 'voltage'
}

def periodic_data_sender():
    """주기적으로 센서 데이터를 가져와서 웹으로 전송"""
    global monitoring_active
    
    print("🔄 periodic_data_sender 스레드 시작")
    
    while monitoring_active:
        try:
            if sensor_monitor:
                # ✅ 직접 샘플링 (캘리브레이션 즉시 반영!)
                status = sensor_monitor._collect_sensor_data()
                
                # print(f"🔄 [SENDER] 샘플링 완료: 탱크1={status['tank1_level']:.1f}%, 탱크2={status['tank2_level']:.1f}%")  # 디버그용
                
                # 전역 캐시 업데이트
                global cached_sensor_data
                cached_sensor_data.update({
                    'timestamp': status['timestamp'],
                    'voltages': status['voltages'],
                    'tank1_level': status['tank1_level'],
                    'tank2_level': status['tank2_level'],
                    'sensor_type': sensor_monitor.sensor_reader.calibration.get('sensor_type', 'voltage')
                })
                
                # 디버깅: status 확인
                # print(f"🔍 [DEBUG] status 전체: {status}")  # 디버그용
                # print(f"🔍 [DEBUG] status['timestamp'] 타입: {type(status['timestamp'])}")  # 디버그용
                # print(f"🔍 [DEBUG] status['timestamp'] 값: {status['timestamp']}")  # 디버그용
                
                # ✅ timestamp 타입 체크 (핵심 수정 1)
                timestamp_obj = status['timestamp']
                if isinstance(timestamp_obj, str):
                    # 이미 문자열이면 그대로 사용
                    timestamp_str = timestamp_obj
                    # DataLogger를 위해 datetime으로 변환
                    try:
                        timestamp_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        timestamp_dt = datetime.now()
                else:
                    # datetime 객체면 문자열로 변환
                    timestamp_str = timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')
                    timestamp_dt = timestamp_obj
                
                # 데이터 로깅
                if data_logger:
                    data_logger.log_sensor_data(
                        tank1_level=status['tank1_level'],
                        tank2_level=status['tank2_level'],
                        voltages=status['voltages'],
                        timestamp=timestamp_dt  # datetime 객체 전달
                    )
                
                # 경고 체크
                if alert_manager:
                    alert_manager.check_water_level(1, status['tank1_level'])
                    alert_manager.check_water_level(2, status['tank2_level'])
                    
                    # 센서 오류 체크
                    for i, voltage in enumerate(status['voltages']):
                        alert_manager.check_sensor_error(voltage, i)
                
                # 웹 클라이언트에 실시간 데이터 푸시
                socketio.emit('sensor_update', {
                    'timestamp': timestamp_str,  # 문자열로 전송
                    'tank1_level': round(status['tank1_level'], 1),
                    'tank2_level': round(status['tank2_level'], 1),
                    'voltages': [round(v, 3) for v in status['voltages']]
                })
                
                # print(f"📡 웹으로 데이터 전송: 탱크1={status['tank1_level']:.1f}%, 탱크2={status['tank2_level']:.1f}%")  # 디버그용
        
        except Exception as e:
            print(f"❌ 주기적 데이터 전송 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 10초 대기
        time.sleep(10)
    
    print("⏹️  periodic_data_sender 스레드 종료")

def init_monitoring_system():
    """모니터링 시스템 초기화"""
    global sensor_monitor, data_logger, alert_manager, relay_controller, soil_sensor_manager, auto_irrigation
    
    try:
        # SensorMonitor 초기화
        sensor_monitor = SensorMonitor(config={
            'check_interval': 10,
            'sample_count': 10,
            'outlier_remove': 2,
            'min_water_level': 20.0,
            'max_water_level': 90.0
        })
        
        # DataLogger 초기화
        data_logger = DataLogger(
            log_dir='/home/pi/smart_farm/logs'
        )
        
        # AlertManager 초기화
        alert_manager = AlertManager(
            tank1_min=20.0,
            tank1_max=90.0,
            tank2_min=20.0,
            tank2_max=90.0,
            cooldown_seconds=300,
            log_file='/home/pi/smart_farm/logs/alerts.log'
        )
        
        # AlertManager 콜백: 경고를 웹 클라이언트에 푸시
        def alert_callback(alert):
            socketio.emit('new_alert', {
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'level': alert.level.value,
                'type': alert.alert_type.value,
                'message': alert.message,
                'tank_num': alert.tank_num,
                'value': alert.value
            })
        
        alert_manager.add_callback(alert_callback)
        # RelayController 초기화
        relay_controller = RelayController()

        # 토양 센서 & 자동 관수 초기화
        try:
            soil_sensor_manager = SoilSensorManager()
            auto_irrigation = AutoIrrigationController(
                sensor_manager=soil_sensor_manager,
                relay_controller=relay_controller
            )
            print("✅ 토양 센서 & 자동 관수 초기화 완료")
        except Exception as e:
            print(f"⚠️  토양 센서 초기화 실패 (센서 미연결?): {e}")
            soil_sensor_manager = None
            auto_irrigation = None

        
        print("✅ 모니터링 시스템 초기화 완료")
        
        # 🔥 서버 시작 시 모니터링 자동 시작
        global monitoring_active, monitoring_thread
        monitoring_active = True
        monitoring_thread = threading.Thread(target=periodic_data_sender, daemon=True)
        monitoring_thread.start()
        print("🚀 모니터링 자동 시작됨 (서버 시작 시)")
        
        return True
        
    except Exception as e:
        print(f"❌ 모니터링 시스템 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================
# 웹 라우트
# ============================================================

@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """시스템 상태 조회"""
    global monitoring_active
    
    try:
        status = {
            'monitoring_active': monitoring_active,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # ✅ 수정: 히스토리에서 마지막 값 가져오기 (샘플링 절대 안 함)
        if sensor_monitor and monitoring_active:
            history = sensor_monitor.get_history(limit=1)
            if history:
                last_data = history[0]
                # timestamp 타입 체크
                if isinstance(last_data['timestamp'], str):
                    timestamp_str = last_data['timestamp']
                else:
                    timestamp_str = last_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                
                status.update({
                    'timestamp': timestamp_str,
                    'tank1_level': round(last_data['tank1_level'], 1),
                    'tank2_level': round(last_data['tank2_level'], 1),
                    'voltages': [round(v, 3) for v in last_data['voltages']]
                })
            else:
                # 히스토리가 아직 없으면 기본값
                status.update({
                    'tank1_level': 0.0,
                    'tank2_level': 0.0,
                    'voltages': [0.0, 0.0, 0.0, 0.0]
                })
        else:
            # 모니터링 꺼져있으면 기본값
            status.update({
                'tank1_level': 0.0,
                'tank2_level': 0.0,
                'voltages': [0.0, 0.0, 0.0, 0.0]
            })
        
        # AlertManager 통계
        if alert_manager:
            alert_status = alert_manager.get_current_status()
            status.update({
                'alert_count_24h': alert_status['alert_count_24h'],
                'critical_count_24h': alert_status['critical_count_24h'],
                'warning_count_24h': alert_status['warning_count_24h']
            })
        
        return jsonify(status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    """모니터링 시작"""
    global monitoring_active, monitoring_thread
    
    try:
        if not sensor_monitor:
            return jsonify({'error': '모니터링 시스템이 초기화되지 않았습니다'}), 500
        
        if monitoring_active:
            return jsonify({'message': '이미 모니터링 중입니다'})
        
        # ✅ 핵심 수정 2: SensorMonitor.start() 제거
        # periodic_data_sender 스레드만 사용 (이중 샘플링 방지)
        
        monitoring_active = True
        
        # 주기적 데이터 전송 스레드 시작
        monitoring_thread = threading.Thread(target=periodic_data_sender, daemon=True)
        monitoring_thread.start()
        
        print("✅ 모니터링 시작됨 (periodic_data_sender만 사용)")
        
        return jsonify({'message': '모니터링 시작됨'})
        
    except Exception as e:
        print(f"❌ 모니터링 시작 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_monitoring', methods=['POST'])
def stop_monitoring():
    """모니터링 중지"""
    global monitoring_active
    
    try:
        if not sensor_monitor:
            return jsonify({'error': '모니터링 시스템이 초기화되지 않았습니다'}), 500
        
        if not monitoring_active:
            return jsonify({'message': '모니터링이 실행 중이 아닙니다'})
        
        # 모니터링 중지
        monitoring_active = False
        
        print("⏹️  모니터링 중지됨")
        
        return jsonify({'message': '모니터링 중지됨'})
        
    except Exception as e:
        print(f"❌ 모니터링 중지 실패: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
def get_alerts():
    """최근 경고 목록 조회"""
    try:
        if not alert_manager:
            return jsonify({'error': 'AlertManager가 초기화되지 않았습니다'}), 500
        
        limit = request.args.get('limit', 20, type=int)
        level = request.args.get('level', None)
        
        # 레벨 필터
        alert_level = None
        if level:
            try:
                alert_level = AlertLevel[level.upper()]
            except KeyError:
                pass
        
        alerts = alert_manager.get_alert_history(
            level=alert_level,
            limit=limit
        )
        
        return jsonify({
            'alerts': [alert.to_dict() for alert in alerts]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data_history')
def get_data_history():
    """센서 데이터 히스토리 조회"""
    try:
        if not data_logger:
            return jsonify({'error': 'DataLogger가 초기화되지 않았습니다'}), 500
        
        hours = request.args.get('hours', 24, type=int)
        
        # 기간 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        # 데이터 조회
        data = data_logger.get_data(
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'data': data[-100:] if len(data) > 100 else data  # 최근 100개만
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics')
def get_statistics():
    """통계 조회"""
    try:
        if not data_logger:
            return jsonify({'error': 'DataLogger가 초기화되지 않았습니다'}), 500
        
        hours = request.args.get('hours', 24, type=int)
        
        # 기간 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        # 통계 계산
        tank1_stats = data_logger.get_statistics(
            start_date=start_date,
            end_date=end_date,
            tank_num=1
        )
        
        tank2_stats = data_logger.get_statistics(
            start_date=start_date,
            end_date=end_date,
            tank_num=2
        )
        
        return jsonify({
            'tank1': tank1_stats,
            'tank2': tank2_stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
# SocketIO 이벤트
# ============================================================

@socketio.on('connect')
def handle_connect():
    """클라이언트 연결"""
    
    emit('connected', {'message': '서버에 연결되었습니다'})

@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제"""
    

@socketio.on('request_status')
def handle_request_status():
    """상태 요청 (캐시만 반환, 샘플링 안 함)"""
    # ✅ 캐시된 데이터만 반환 (샘플링 안 함!)
    global cached_sensor_data
    
    # timestamp 타입 체크
    timestamp_obj = cached_sensor_data.get('timestamp', '')
    if isinstance(timestamp_obj, str):
        timestamp_str = timestamp_obj
    else:
        timestamp_str = timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')
    
    emit('sensor_update', {
        'timestamp': timestamp_str,
        'tank1_level': round(cached_sensor_data.get('tank1_level', 0), 1),
        'tank2_level': round(cached_sensor_data.get('tank2_level', 0), 1),
        'voltages': [round(v, 3) for v in cached_sensor_data.get('voltages', [0, 0, 0, 0])]
    })

# ============================================================
# 메인 실행
# ============================================================

# ============================================================
# 설정 페이지 라우트 (Stage 3.5 추가)
# ============================================================


@app.route('/irrigation')
def irrigation():
    """관수 제어 페이지"""
    return render_template('irrigation.html')

@app.route('/settings')
def settings():
    """설정 페이지"""
    return render_template('settings.html')

# ============================================================
# 센서 캘리브레이션 API (Stage 3.5 추가)
# ============================================================

@app.route('/api/calibration', methods=['GET'])
def get_calibration():
    """캘리브레이션 설정 조회"""
    try:
        import json
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config',
            'sensor_calibration.json'
        )
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                calibration = json.load(f)
            return jsonify(calibration)
        else:
            return jsonify({
                'sensor_type': 'voltage',
                'tank1_water': {
                    'empty_value': 0.5,
                    'full_value': 4.5,
                    'calibrated_at': None
                },
                'tank2_nutrient': {
                    'empty_value': 0.5,
                    'full_value': 4.5,
                    'calibrated_at': None
                }
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def validate_voltage(value, field_name):
    """전압 입력값 검증 (0~5V)"""
    try:
        num = float(value)
        if not (0 <= num <= 5.0):
            raise ValueError(f"{field_name}는 0V ~ 5.0V 범위여야 합니다 (입력값: {num}V)")
        return round(num, 3)
    except (ValueError, TypeError) as e:
        raise ValueError(f"{field_name}는 유효한 숫자가 아닙니다")

@app.route('/api/calibration', methods=['POST'])
def save_calibration():
    """캘리브레이션 설정 저장"""
    try:
        # print("🔵 /api/calibration POST 요청 받음")  # 디버그용
        import json
        from datetime import datetime
        
        data = request.get_json()
        
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config',
            'sensor_calibration.json'
        )
        
        if data.get('update_type_only'):
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    calibration = json.load(f)
            else:
                calibration = {}
            
            calibration['sensor_type'] = data.get('sensor_type', 'voltage')
            calibration['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            calibration = {
                'sensor_type': data.get('sensor_type', 'voltage'),
                'last_updated': now,
                'tank1_water': {
                    'empty_value': validate_voltage(data['tank1_water']['empty_value'], 'Tank 1 Empty'),
                    'full_value': validate_voltage(data['tank1_water']['full_value'], 'Tank 1 Full'),
                    'calibrated_at': now
                },
                'tank2_nutrient': {
                    'empty_value': validate_voltage(data['tank2_nutrient']['empty_value'], 'Tank 2 Empty'),
                    'full_value': validate_voltage(data['tank2_nutrient']['full_value'], 'Tank 2 Full'),
                    'calibrated_at': now
                }
            }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(calibration, f, indent=2, ensure_ascii=False)
        
        # ✅ 센서 모니터에 새 캘리브레이션 적용
        global sensor_monitor, cached_sensor_data
        # print(f"🔵 load_calibration 호출: {config_path}")  # 디버그용
        sensor_monitor.load_calibration(config_path)
        # print("🔵 load_calibration 완료")  # 디버그용
        
        # 캐시 초기화 및 즉시 새 데이터 샘플링
        print("🔄 캘리브레이션 변경 후 즉시 샘플링...")
        new_data = sensor_monitor._collect_sensor_data()  # 직접 샘플링
        
        # ✅ 두 캐시 모두 업데이트 (동기화!)
        sensor_monitor._last_data = new_data
        global cached_sensor_data
        cached_sensor_data.update(new_data)
        
        print(f"✅ 새 캘리브레이션 적용: 탱크1={new_data.get('tank1_level', 0):.1f}%, 탱크2={new_data.get('tank2_level', 0):.1f}%")
        
        return jsonify({
            'success': True,
            'message': '캘리브레이션 설정이 저장되고 적용되었습니다'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calibration/current', methods=['GET'])
def get_current_sensor_values():
    """실시간 센서 값 조회"""
    try:
        import json
        
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config',
            'sensor_calibration.json'
        )
        
        sensor_type = 'voltage'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                calibration = json.load(f)
                sensor_type = calibration.get('sensor_type', 'voltage')
        
        # ✅ 캐시된 센서 값만 반환 (샘플링 안 함!)
        global cached_sensor_data
        
        voltages = cached_sensor_data.get('voltages', [0, 0, 0, 0])
        tank1_value = voltages[0] if len(voltages) > 0 else 0
        tank2_value = voltages[1] if len(voltages) > 1 else 0
        
        return jsonify({
            'success': True,
            'sensor_type': sensor_type,
            'tank1_value': tank1_value,
            'tank2_value': tank2_value,
            'tank1_water': calibration.get('tank1_water', {}),
            'tank2_nutrient': calibration.get('tank2_nutrient', {})
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 호스건 제어 API (Stage 3.5 추가 - Mock)
# ============================================================


@app.route('/api/hose-gun/status', methods=['GET'])
def get_hose_gun_status():
    """호스건 상태 조회"""
    try:
        if not relay_controller:
            return jsonify({'error': 'RelayController가 초기화되지 않았습니다'}), 500
        
        status = relay_controller.get_hand_gun_status()
        return jsonify({
            'active': status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hose-gun/activate', methods=['POST'])
def activate_hose_gun():
    """호스건 활성화"""
    try:
        if not relay_controller:
            return jsonify({'error': 'RelayController가 초기화되지 않았습니다'}), 500
        
        # 호스건 활성화 (안전장치 포함)
        relay_controller.hand_gun_on()
        
        return jsonify({
            'success': True,
            'message': '호스건이 활성화되었습니다'
        })
    except Exception as e:
        print(f"❌ 호스건 활성화 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hose-gun/deactivate', methods=['POST'])
def deactivate_hose_gun():
    """호스건 비활성화"""
    global relay_controller
    try:
        if relay_controller is None:
            return jsonify({
                'success': False,
                'error': 'RelayController 초기화 안됨'
            }), 500
        
        relay_controller.hand_gun_off()
        print("🔒 호스건 비활성화")
        
        return jsonify({
            'success': True,
            'message': '호스건이 비활성화되었습니다'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# 🌱 자동 관수 API
# ============================================================

@app.route('/api/irrigation/status')
def get_irrigation_status():
    """자동 관수 전체 상태 조회"""
    global auto_irrigation
    if auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 초기화 안됨'}), 503
    return jsonify({'success': True, 'data': auto_irrigation.get_status()})


@app.route('/api/irrigation/mode', methods=['POST'])
def set_irrigation_mode():
    """관수 모드 변경: auto / manual / schedule"""
    global auto_irrigation
    if auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    mode = request.json.get('mode')
    ok, msg = auto_irrigation.set_mode(mode)
    return jsonify({'success': ok, 'message': msg})


@app.route('/api/irrigation/start', methods=['POST'])
def start_irrigation():
    """수동 관수 시작: zone_id, duration(초) 지정"""
    global auto_irrigation
    if auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    zone_id  = request.json.get('zone_id')
    duration = request.json.get('duration', 300)
    if not zone_id:
        return jsonify({'success': False, 'error': 'zone_id 필요'}), 400
    if auto_irrigation.is_irrigating:
        return jsonify({'success': False,
                        'error': f'이미 관수 중 (구역 {auto_irrigation.current_zone})'}), 409

    def run():
        auto_irrigation.irrigate_zone(int(zone_id), int(duration))

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'success': True,
                    'message': f'구역 {zone_id} 관수 시작 ({duration}초)'})


@app.route('/api/irrigation/stop', methods=['POST'])
def stop_irrigation():
    """관수 긴급 정지"""
    global auto_irrigation, relay_controller
    try:
        if relay_controller:
            relay_controller.emergency_stop()
        if auto_irrigation:
            auto_irrigation.is_irrigating = False
            auto_irrigation.current_zone  = None
        return jsonify({'success': True, 'message': '관수 긴급 정지 완료'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/irrigation/sensors')
def get_soil_sensors():
    """토양 센서 전체 현황 조회"""
    global auto_irrigation, soil_sensor_manager
    if auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    # 최신 데이터 반환 (캐시)
    data = auto_irrigation.get_sensor_data()
    return jsonify({'success': True, 'data': data,
                    'count': len(data)})


@app.route('/api/irrigation/sensors/read', methods=['POST'])
def refresh_soil_sensors():
    """토양 센서 즉시 재측정"""
    global soil_sensor_manager, auto_irrigation
    if soil_sensor_manager is None:
        return jsonify({'success': False, 'error': '센서 없음'}), 503
    try:
        results = soil_sensor_manager.read_all_zones()
        if auto_irrigation:
            auto_irrigation.last_sensor_data = results
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/irrigation/threshold', methods=['POST'])
def set_threshold():
    """구역별 관수 임계값 설정"""
    global auto_irrigation
    if auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    zone_id   = request.json.get('zone_id')
    threshold = request.json.get('threshold')
    if zone_id is None or threshold is None:
        return jsonify({'success': False, 'error': 'zone_id, threshold 필요'}), 400
    auto_irrigation.zone_thresholds[int(zone_id)] = float(threshold)
    return jsonify({'success': True,
                    'message': f'구역 {zone_id} 임계값 → {threshold}%'})


@app.route('/api/irrigation/history')
def get_irrigation_history():
    """관수 이력 조회"""
    global auto_irrigation
    if auto_irrigation is None:
        return jsonify({'success': False, 'error': '자동 관수 시스템 없음'}), 503
    limit = int(request.args.get('limit', 20))
    history = auto_irrigation.irrigation_history[-limit:]
    return jsonify({'success': True, 'data': list(reversed(history)),
                    'total': len(auto_irrigation.irrigation_history)})


# ============================================================
# 📥 CSV 다운로드 API
# ============================================================

@app.route('/api/download/irrigation-history')
def download_irrigation_history():
    """관수 이력 CSV 다운로드"""
    import csv, io
    from flask import Response

    csv_path = '/home/pi/smart_farm/logs/irrigation_history.csv'

    if not os.path.exists(csv_path):
        return jsonify({'error': '관수 이력 파일 없음'}), 404

    # 쿼리 파라미터: 날짜 필터 (선택)
    date_from = request.args.get('from')  # YYYY-MM-DD
    date_to   = request.args.get('to')

    try:
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if date_from and row.get('timestamp', '') < date_from:
                    continue
                if date_to and row.get('timestamp', '') > date_to + ' 23:59:59':
                    continue
                rows.append(row)

        # CSV 문자열 생성
        output = io.StringIO()
        fieldnames = ['timestamp', 'zone_id', 'duration_sec', 'trigger', 'moisture_before', 'success']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

        filename = f"irrigation_history_{datetime.now().strftime('%Y%m%d')}.csv"
        return Response(
            '﻿' + output.getvalue(),   # BOM: 엑셀 한글 깨짐 방지
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/sensor-data')
def download_sensor_data():
    """탱크 수위 센서 데이터 CSV 다운로드"""
    import glob
    from flask import Response

    log_dir   = '/home/pi/smart_farm/logs'
    date_from = request.args.get('from')   # YYYY-MM-DD
    date_to   = request.args.get('to')

    try:
        # 파일 목록 (날짜 필터)
        files = sorted(glob.glob(os.path.join(log_dir, 'sensors_*.csv')))
        if date_from:
            files = [f for f in files if os.path.basename(f) >= f'sensors_{date_from}.csv']
        if date_to:
            files = [f for f in files if os.path.basename(f) <= f'sensors_{date_to}.csv']

        if not files:
            return jsonify({'error': '해당 기간 데이터 없음'}), 404

        # 파일 합치기
        import io, csv
        output = io.StringIO()
        header_written = False
        total_rows = 0

        for fpath in files:
            with open(fpath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                if not rows:
                    continue
                if not header_written:
                    output.write(','.join(rows[0]) + '\n')
                    header_written = True
                for row in rows[1:]:
                    output.write(','.join(row) + '\n')
                    total_rows += 1

        fname_from = date_from or 'all'
        fname_to   = date_to   or datetime.now().strftime('%Y-%m-%d')
        filename   = f"sensor_data_{fname_from}_to_{fname_to}.csv"

        return Response(
            '\ufeff' + output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/files')
def list_download_files():
    """다운로드 가능한 파일 목록 조회"""
    import glob

    log_dir = '/home/pi/smart_farm/logs'
    result  = {'sensor_files': [], 'irrigation_csv': None}

    # 센서 CSV 파일 목록
    for fpath in sorted(glob.glob(os.path.join(log_dir, 'sensors_*.csv')), reverse=True):
        fname = os.path.basename(fpath)
        size  = os.path.getsize(fpath)
        rows  = 0
        try:
            with open(fpath, 'r') as f:
                rows = max(0, sum(1 for _ in f) - 1)  # 헤더 제외
        except Exception:
            pass
        result['sensor_files'].append({
            'filename': fname,
            'date': fname.replace('sensors_','').replace('.csv',''),
            'size_kb': round(size/1024, 1),
            'rows': rows
        })

    # 관수 이력 CSV
    irr_path = os.path.join(log_dir, 'irrigation_history.csv')
    if os.path.exists(irr_path):
        rows = 0
        try:
            with open(irr_path,'r') as f:
                rows = max(0, sum(1 for _ in f) - 1)
        except Exception:
            pass
        result['irrigation_csv'] = {
            'filename': 'irrigation_history.csv',
            'size_kb': round(os.path.getsize(irr_path)/1024, 1),
            'rows': rows
        }

    return jsonify({'success': True, 'data': result})


# ============================================================
# 📊 분석 페이지 라우트 + API  (Stage 7)
# ============================================================

@app.route('/analytics')
def analytics():
    """데이터 분석 페이지"""
    return render_template('analytics.html')


@app.route('/api/analytics/sensor-data')
def analytics_sensor_data():
    """분석용 탱크 수위 CSV 데이터 조회 (날짜 필터 + 통계)"""
    import csv, glob, statistics

    log_dir   = '/home/pi/smart_farm/logs'
    date_from = request.args.get('from')
    date_to   = request.args.get('to')

    try:
        files = sorted(glob.glob(os.path.join(log_dir, 'sensors_*.csv')))
        if date_from:
            files = [f for f in files if os.path.basename(f) >= f'sensors_{date_from}.csv']
        if date_to:
            files = [f for f in files if os.path.basename(f) <= f'sensors_{date_to}.csv']

        rows = []
        for fpath in files:
            with open(fpath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)

        # 통계 계산
        def calc_stats(values, rows_ref):
            vals = [float(v) for v in values if v not in ('', None)]
            if not vals:
                return {'count': 0, 'avg': 0, 'min': 0, 'max': 0,
                        'first_timestamp': '', 'last_timestamp': ''}
            ts = [r.get('timestamp','') for r in rows_ref]
            return {
                'count': len(vals),
                'avg':   round(statistics.mean(vals), 1),
                'min':   round(min(vals), 1),
                'max':   round(max(vals), 1),
                'first_timestamp': ts[0]  if ts else '',
                'last_timestamp':  ts[-1] if ts else '',
            }

        t1_vals = [r.get('tank1_level', '') for r in rows]
        t2_vals = [r.get('tank2_level', '') for r in rows]

        # 응답 데이터 다운샘플 (최대 2000행 전송)
        MAX_ROWS = 2000
        step = max(1, len(rows) // MAX_ROWS)
        sampled = rows[::step]

        return jsonify({
            'success': True,
            'data':   sampled,
            'total':  len(rows),
            'stats': {
                'tank1': calc_stats(t1_vals, rows),
                'tank2': calc_stats(t2_vals, rows),
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analytics/irrigation-history')
def analytics_irrigation_history():
    """분석용 관수 이력 전체 조회 (날짜 필터)"""
    import csv

    csv_path  = '/home/pi/smart_farm/logs/irrigation_history.csv'
    date_from = request.args.get('from')
    date_to   = request.args.get('to')

    if not os.path.exists(csv_path):
        # 파일이 없으면 메모리 이력 반환
        global auto_irrigation
        if auto_irrigation:
            history = list(reversed(auto_irrigation.irrigation_history))
            return jsonify({'success': True, 'data': history, 'source': 'memory'})
        return jsonify({'success': True, 'data': [], 'source': 'empty'})

    try:
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get('timestamp', '')
                if date_from and ts < date_from:
                    continue
                if date_to   and ts > date_to + ' 23:59:59':
                    continue
                rows.append(row)

        return jsonify({
            'success': True,
            'data':    list(reversed(rows)),
            'total':   len(rows),
            'source':  'csv'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ⚙️  자동 관수 설정 API  (Stage 5.5)
# ============================================================

SOIL_SENSORS_PATH = '/home/pi/smart_farm/config/soil_sensors.json'
SCHEDULES_PATH    = '/home/pi/smart_farm/config/schedules.json'

def _load_soil_config():
    """soil_sensors.json 로드"""
    import json
    try:
        with open(SOIL_SENSORS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            "modbus": {},
            "sensors": [
                {"zone_id": i, "sensor_address": i, "name": f"구역 {i}",
                 "enabled": True, "moisture_threshold": 40.0}
                for i in range(1, 13)
            ],
            "irrigation": {
                "min_tank_level": 20.0, "irrigation_duration": 300,
                "zone_interval": 10,    "check_interval": 600,
                "max_zones_simultaneous": 1
            }
        }

def _save_soil_config(cfg):
    """soil_sensors.json 저장"""
    import json, os
    os.makedirs(os.path.dirname(SOIL_SENSORS_PATH), exist_ok=True)
    with open(SOIL_SENSORS_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def _load_schedules():
    """schedules.json 로드"""
    import json
    try:
        with open(SCHEDULES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"schedules": []}

def _save_schedules(data):
    """schedules.json 저장"""
    import json, os
    os.makedirs(os.path.dirname(SCHEDULES_PATH), exist_ok=True)
    with open(SCHEDULES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.route('/api/irrigation/config', methods=['GET'])
def get_irrigation_config():
    """자동 관수 기본 설정 조회"""
    try:
        cfg = _load_soil_config()
        irr = cfg.get('irrigation', {})
        # 현재 모드도 포함
        mode = 'manual'
        if auto_irrigation:
            mode = auto_irrigation.mode
        irr['mode'] = mode
        return jsonify({'success': True, 'config': irr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/irrigation/config', methods=['POST'])
def save_irrigation_config():
    """자동 관수 기본 설정 저장 및 컨트롤러 즉시 반영"""
    try:
        data = request.get_json()
        cfg  = _load_soil_config()

        irr = cfg.get('irrigation', {})
        if 'check_interval'      in data: irr['check_interval']      = int(data['check_interval'])
        if 'irrigation_duration' in data: irr['irrigation_duration'] = int(data['irrigation_duration'])
        if 'min_tank_level'      in data: irr['min_tank_level']      = float(data['min_tank_level'])
        if 'zone_interval'       in data: irr['zone_interval']       = int(data['zone_interval'])
        cfg['irrigation'] = irr

        _save_soil_config(cfg)

        # 실행 중인 AutoIrrigationController에 즉시 반영
        if auto_irrigation:
            auto_irrigation.irrigation_cfg = irr
            print(f"✅ 관수 설정 즉시 반영: check={irr.get('check_interval')}s, "
                  f"duration={irr.get('irrigation_duration')}s")

        return jsonify({'success': True, 'message': '관수 기본 설정이 저장되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/irrigation/thresholds', methods=['GET'])
def get_irrigation_thresholds():
    """12구역 수분 임계값 조회"""
    try:
        cfg = _load_soil_config()
        thresholds = [
            {
                'zone_id':   s['zone_id'],
                'name':      s.get('name', f"구역 {s['zone_id']}"),
                'threshold': s.get('moisture_threshold', 40.0)
            }
            for s in cfg.get('sensors', [])
        ]
        return jsonify({'success': True, 'thresholds': thresholds})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/irrigation/thresholds', methods=['POST'])
def save_irrigation_thresholds():
    """12구역 수분 임계값 일괄 저장 및 컨트롤러 즉시 반영"""
    try:
        data       = request.get_json()
        thresholds = data.get('thresholds', [])   # [{zone_id, threshold}, ...]

        cfg     = _load_soil_config()
        thr_map = {int(t['zone_id']): float(t['threshold']) for t in thresholds}

        for sensor in cfg.get('sensors', []):
            zid = int(sensor['zone_id'])
            if zid in thr_map:
                sensor['moisture_threshold'] = thr_map[zid]

        _save_soil_config(cfg)

        # AutoIrrigationController zone_thresholds 즉시 반영
        if auto_irrigation:
            auto_irrigation.zone_thresholds.update(thr_map)
            print(f"✅ 임계값 즉시 반영: {thr_map}")

        return jsonify({'success': True,
                        'message': f'{len(thresholds)}개 구역 임계값이 저장되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 📅 스케줄 API  (Stage 5.5)
# ============================================================

@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    """스케줄 목록 조회"""
    try:
        data = _load_schedules()
        return jsonify({'success': True, 'schedules': data.get('schedules', [])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/schedules', methods=['POST'])
def add_schedule():
    """스케줄 추가"""
    try:
        from datetime import datetime as dt
        body      = request.get_json()
        zone_id   = int(body.get('zone_id', 0))
        start_time = body.get('start_time', '')
        duration  = int(body.get('duration', 300))
        days      = [int(d) for d in body.get('days', [])]

        if not zone_id or not start_time:
            return jsonify({'success': False, 'error': 'zone_id, start_time 필수'}), 400

        # HH:MM 형식 검증
        try:
            dt.strptime(start_time, '%H:%M')
        except ValueError:
            return jsonify({'success': False, 'error': '시간 형식이 HH:MM이어야 합니다'}), 400

        data = _load_schedules()
        schedules = data.get('schedules', [])

        new_id = max((s.get('id', 0) for s in schedules), default=0) + 1
        new_schedule = {
            'id':         new_id,
            'zone_id':    zone_id,
            'start_time': start_time,
            'duration':   duration,
            'days':       days,
            'enabled':    True,
            'created_at': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        schedules.append(new_schedule)
        _save_schedules({'schedules': schedules})

        print(f"✅ 스케줄 추가: #{new_id} 구역{zone_id} {start_time} {duration}s")
        return jsonify({'success': True, 'schedule': new_schedule,
                        'message': f'스케줄 #{new_id}가 추가되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """스케줄 삭제"""
    try:
        data      = _load_schedules()
        schedules = data.get('schedules', [])
        new_list  = [s for s in schedules if s.get('id') != schedule_id]

        if len(new_list) == len(schedules):
            return jsonify({'success': False, 'error': f'스케줄 #{schedule_id} 없음'}), 404

        _save_schedules({'schedules': new_list})
        print(f"🗑️  스케줄 #{schedule_id} 삭제")
        return jsonify({'success': True, 'message': f'스케줄 #{schedule_id}가 삭제되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/schedules/<int:schedule_id>', methods=['PATCH'])
def toggle_schedule(schedule_id):
    """스케줄 활성화/비활성화"""
    try:
        body      = request.get_json()
        enabled   = bool(body.get('enabled', True))
        data      = _load_schedules()
        schedules = data.get('schedules', [])

        found = False
        for s in schedules:
            if s.get('id') == schedule_id:
                s['enabled'] = enabled
                found = True
                break

        if not found:
            return jsonify({'success': False, 'error': f'스케줄 #{schedule_id} 없음'}), 404

        _save_schedules({'schedules': schedules})
        status = '활성화' if enabled else '비활성화'
        print(f"🔄 스케줄 #{schedule_id} {status}")
        return jsonify({'success': True, 'message': f'스케줄 #{schedule_id}가 {status}되었습니다'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



if __name__ == '__main__':
    print("=" * 60)
    print("🌐 스마트 관수 시스템 웹 대시보드 v2")
    print("=" * 60)
    print()
    
    # 모니터링 시스템 초기화
    if init_monitoring_system():
        print()
        print("🚀 Flask 서버 시작...")
        print("📡 접속 주소: http://localhost:5000")
        print("   (Raspberry Pi IP: http://[라즈베리파이IP]:5000)")
        print()
        print("⏹️  종료: Ctrl+C")
        print("=" * 60)
        print()
        
        # Flask 서버 실행
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        print("❌ 시스템 초기화 실패")
