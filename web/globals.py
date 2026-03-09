"""
공유 전역 변수 모듈 (web/globals.py)
모든 Blueprint에서 'import web.globals as g' 형태로 import하여 사용
"""
import json
import os
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent

SOIL_SENSORS_PATH = str(_BASE_DIR / 'config/soil_sensors.json')
SCHEDULES_PATH    = str(_BASE_DIR / 'config/schedules.json')

sensor_monitor      = None
data_logger         = None
alert_manager       = None
telegram_notifier   = None
relay_controller    = None
soil_sensor_manager = None
auto_irrigation     = None
irrigation_scheduler= None

monitoring_active  = False
monitoring_thread  = None

cached_sensor_data = {
    'timestamp':   None,
    'voltages':    [0.0, 0.0, 0.0, 0.0],
    'tank1_level': 0.0,
    'tank2_level': 0.0,
    'sensor_type': 'voltage'
}

def _load_soil_config():
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
    os.makedirs(os.path.dirname(SOIL_SENSORS_PATH), exist_ok=True)
    with open(SOIL_SENSORS_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def _load_schedules():
    try:
        with open(SCHEDULES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"schedules": []}

def _save_schedules(data):
    os.makedirs(os.path.dirname(SCHEDULES_PATH), exist_ok=True)
    with open(SCHEDULES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
