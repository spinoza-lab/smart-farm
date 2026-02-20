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
                
                print(f"🔄 [SENDER] 샘플링 완료: 탱크1={status['tank1_level']:.1f}%, 탱크2={status['tank2_level']:.1f}%")
                
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
                print(f"🔍 [DEBUG] status 전체: {status}")
                print(f"🔍 [DEBUG] status['timestamp'] 타입: {type(status['timestamp'])}")
                print(f"🔍 [DEBUG] status['timestamp'] 값: {status['timestamp']}")
                
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
                
                print(f"📡 웹으로 데이터 전송: 탱크1={status['tank1_level']:.1f}%, 탱크2={status['tank2_level']:.1f}%")
        
        except Exception as e:
            print(f"❌ 주기적 데이터 전송 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 10초 대기
        time.sleep(10)
    
    print("⏹️  periodic_data_sender 스레드 종료")


def init_monitoring_system():
    """모니터링 시스템 초기화"""
    global sensor_monitor, data_logger, alert_manager
    
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
    print(f"🔌 클라이언트 연결: {request.sid}")
    emit('connected', {'message': '서버에 연결되었습니다'})


@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제"""
    print(f"🔌 클라이언트 연결 해제: {request.sid}")


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
        print("🔵 /api/calibration POST 요청 받음")
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
        print(f"🔵 load_calibration 호출: {config_path}")
        sensor_monitor.load_calibration(config_path)
        print("🔵 load_calibration 완료")
        
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

hose_gun_active = False

@app.route('/api/hose-gun/status', methods=['GET'])
def get_hose_gun_status():
    """호스건 상태 조회"""
    return jsonify({
        'active': hose_gun_active
    })


@app.route('/api/hose-gun/activate', methods=['POST'])
def activate_hose_gun():
    """호스건 활성화 (Mock)"""
    global hose_gun_active
    try:
        hose_gun_active = True
        print("🚰 호스건 활성화 (Mock)")
        
        return jsonify({
            'success': True,
            'message': '호스건이 활성화되었습니다 (Mock)'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/hose-gun/deactivate', methods=['POST'])
def deactivate_hose_gun():
    """호스건 비활성화 (Mock)"""
    global hose_gun_active
    try:
        hose_gun_active = False
        print("🔒 호스건 비활성화 (Mock)")
        
        return jsonify({
            'success': True,
            'message': '호스건이 비활성화되었습니다 (Mock)'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        socketio.run(
            app,
            host='0.0.0.0',  # 외부 접속 허용
            port=5000,
            debug=True,
            use_reloader=False  # 리로더 비활성화 (센서 충돌 방지)
        )
    else:
        print("❌ 시스템 초기화 실패")
