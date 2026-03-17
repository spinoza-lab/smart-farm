#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
environment_bp.py — 환경 모니터링 REST API Blueprint

엔드포인트:
  GET /api/environment                  → 전체 환경 상태 (대기 + 기상)
  GET /api/environment/air              → SHT30 대기 센서 목록
  GET /api/environment/weather          → WH65LP 기상 관측 최신값
  GET /api/environment/history/air      → 대기 히스토리 (limit 파라미터)
  GET /api/environment/history/weather  → 기상 히스토리 (limit 파라미터)
  GET /api/environment/logs/air         → 날짜별 CSV 로그 조회 (date 파라미터)
  GET /api/environment/logs/weather     → 날짜별 CSV 로그 조회 (date 파라미터)
"""

import os
import csv
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

environment_bp = Blueprint('environment', __name__)

# 프로젝트 루트 경로
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ──────────────────────────────────────────────────────────────────────
# 헬퍼: globals에서 environment_monitor 가져오기
# ──────────────────────────────────────────────────────────────────────
def _get_monitor():
    try:
        from web import globals as g
        return getattr(g, 'environment_monitor', None)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────
# GET /api/environment
# ──────────────────────────────────────────────────────────────────────
@environment_bp.route('/api/environment', methods=['GET'])
def get_environment():
    """전체 환경 상태 (대기 + 기상 통합)"""
    monitor = _get_monitor()
    if monitor is None:
        return jsonify({
            'success': False,
            'message': '환경 모니터가 초기화되지 않았습니다.',
            'air': [],
            'weather': None
        }), 503

    try:
        status = monitor.get_environment_status()
        return jsonify({
            'success':   True,
            'running':   status.get('running', False),
            'air':       status.get('air', []),
            'weather':   status.get('weather'),
            'timestamp': status.get('timestamp', '')
        })
    except Exception as e:
        logger.error(f"[environment_bp] /api/environment 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────
# GET /api/environment/air
# ──────────────────────────────────────────────────────────────────────
@environment_bp.route('/api/environment/air', methods=['GET'])
def get_air():
    """SHT30 대기 센서 현재 상태"""
    monitor = _get_monitor()
    if monitor is None:
        return jsonify({'success': False, 'message': '환경 모니터 미초기화', 'sensors': []}), 503

    try:
        sensors     = monitor.get_air_status()
        valid_list  = [s for s in sensors if s.get('valid') and s.get('temperature') is not None]
        valid_count = len(valid_list)

        avg_temp = round(sum(s['temperature'] for s in valid_list) / valid_count, 1) \
                   if valid_count else None
        avg_hum  = round(sum(s['humidity']    for s in valid_list) / valid_count, 1) \
                   if valid_count else None

        return jsonify({
            'success':         True,
            'total':           len(sensors),
            'valid_count':     valid_count,
            'avg_temperature': avg_temp,
            'avg_humidity':    avg_hum,
            'sensors':         sensors
        })
    except Exception as e:
        logger.error(f"[environment_bp] /api/environment/air 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────
# GET /api/environment/weather
# ──────────────────────────────────────────────────────────────────────
@environment_bp.route('/api/environment/weather', methods=['GET'])
def get_weather():
    """WH65LP 기상 관측 최신 데이터"""
    monitor = _get_monitor()
    if monitor is None:
        return jsonify({'success': False, 'message': '환경 모니터 미초기화', 'data': None}), 503

    try:
        data = monitor.get_weather_status()
        if data is None:
            return jsonify({
                'success':   True,
                'available': False,
                'message':   '기상 데이터 아직 수신 안됨 (최대 16초 대기)',
                'data':      None
            })
        return jsonify({
            'success':   True,
            'available': True,
            'data':      data
        })
    except Exception as e:
        logger.error(f"[environment_bp] /api/environment/weather 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────
# GET /api/environment/history/air?limit=10
# ──────────────────────────────────────────────────────────────────────
@environment_bp.route('/api/environment/history/air', methods=['GET'])
def get_air_history():
    """SHT30 대기 측정 히스토리"""
    monitor = _get_monitor()
    if monitor is None:
        return jsonify({'success': False, 'data': []}), 503

    limit = min(int(request.args.get('limit', 10)), 100)
    try:
        history = monitor.get_air_history(limit=limit)
        return jsonify({'success': True, 'count': len(history), 'data': history})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────
# GET /api/environment/history/weather?limit=10
# ──────────────────────────────────────────────────────────────────────
@environment_bp.route('/api/environment/history/weather', methods=['GET'])
def get_weather_history():
    """WH65LP 기상 히스토리"""
    monitor = _get_monitor()
    if monitor is None:
        return jsonify({'success': False, 'data': []}), 503

    limit = min(int(request.args.get('limit', 10)), 100)
    try:
        history = monitor.get_weather_history(limit=limit)
        return jsonify({'success': True, 'count': len(history), 'data': history})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────
# GET /api/environment/logs/air?date=2026-03-17
# ──────────────────────────────────────────────────────────────────────
@environment_bp.route('/api/environment/logs/air', methods=['GET'])
def get_air_logs():
    """날짜별 대기 센서 CSV 로그 조회"""
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    log_dir  = os.path.join(_BASE_DIR, 'data', 'air_sensor_logs')
    log_file = os.path.join(log_dir, f'air_{date_str}.csv')
    try:
        rows = _read_csv(log_file)
        return jsonify({'success': True, 'date': date_str, 'count': len(rows), 'data': rows})
    except FileNotFoundError:
        return jsonify({
            'success': True,
            'date':    date_str,
            'count':   0,
            'data':    [],
            'message': f'{date_str} 로그 파일 없음'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────
# GET /api/environment/logs/weather?date=2026-03-17
# ──────────────────────────────────────────────────────────────────────
@environment_bp.route('/api/environment/logs/weather', methods=['GET'])
def get_weather_logs():
    """날짜별 기상 CSV 로그 조회"""
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    log_dir  = os.path.join(_BASE_DIR, 'data', 'weather_logs')
    log_file = os.path.join(log_dir, f'weather_{date_str}.csv')
    try:
        rows = _read_csv(log_file)
        return jsonify({'success': True, 'date': date_str, 'count': len(rows), 'data': rows})
    except FileNotFoundError:
        return jsonify({
            'success': True,
            'date':    date_str,
            'count':   0,
            'data':    [],
            'message': f'{date_str} 로그 파일 없음'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────
def _read_csv(path: str) -> list:
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows
