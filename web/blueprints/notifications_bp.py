"""알림 Blueprint"""
import json, os, subprocess, threading
from datetime import datetime
from flask import Blueprint, jsonify, request
import web.globals as g

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/api/notifications/status', methods=['GET'])
def get_notification_status():
    if g.telegram_notifier is None:
        return jsonify({"connected": False, "polling": False, "is_muted": False})
    return jsonify({"connected": True, **g.telegram_notifier.get_status()})

@notifications_bp.route('/api/notifications/config', methods=['GET'])
def get_notification_config():
    try:
        cfg = {}
        cfg_path = str(g._BASE_DIR / 'config/notifications.json')
        if os.path.exists(cfg_path):
            with open(cfg_path,'r',encoding='utf-8') as f:
                raw = f.read().strip()
                if raw: cfg = json.loads(raw)
        return jsonify({'telegram':{'enabled':cfg.get('telegram',{}).get('enabled',True),'token':'','chat_id':''},
                        'alerts':cfg.get('alerts',{}),'thresholds':cfg.get('thresholds',{}),
                        'cooldown_seconds':cfg.get('cooldown_seconds',300)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/config', methods=['POST'])
def save_notification_config():
    try:
        incoming = request.get_json(force=True, silent=True) or {}
        cfg_path = str(g._BASE_DIR / 'config/notifications.json')
        base = {}
        if os.path.exists(cfg_path):
            with open(cfg_path,'r',encoding='utf-8') as f:
                raw = f.read().strip()
                if raw: base = json.loads(raw)
        tg = base.get('telegram',{})
        if g.telegram_notifier is not None and getattr(g.telegram_notifier,'token',''):
            tg = {'enabled':getattr(g.telegram_notifier,'enabled',True),
                  'token':g.telegram_notifier.token,'chat_id':str(g.telegram_notifier.chat_id)}
        merged = {'telegram':tg,'alerts':incoming.get('alerts',base.get('alerts',{})),
                  'thresholds':incoming.get('thresholds',base.get('thresholds',{})),
                  'cooldown_seconds':incoming.get('cooldown_seconds',base.get('cooldown_seconds',300))}
        tmp = cfg_path + '.tmp'
        with open(tmp,'w',encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        os.replace(tmp, cfg_path)
        if g.alert_manager and 'thresholds' in incoming:
            t = incoming['thresholds']
            try:
                g.alert_manager.set_threshold(1,float(t.get('tank1_min',20)),float(t.get('tank1_max',90)))
                g.alert_manager.set_threshold(2,float(t.get('tank2_min',20)),float(t.get('tank2_max',90)))
            except Exception: pass
        if g.alert_manager:
            new_c = int(merged.get('cooldown_seconds',300))
            if g.alert_manager.cooldown_seconds != new_c:
                g.alert_manager.cooldown_seconds = new_c
        return jsonify({'success': True, 'message': '설정이 저장되었습니다'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/test', methods=['POST'])
def send_notification_test():
    if g.telegram_notifier is None:
        return jsonify({"success": False, "message": "텔레그램 봇이 초기화되지 않았습니다"})
    try:
        g.telegram_notifier.send(
            f"🧪 <b>테스트 메시지</b>\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n✅ 알림 설정이 정상 작동 중입니다!")
        return jsonify({"success": True, "message": "테스트 메시지 전송 완료"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@notifications_bp.route('/api/system/restart', methods=['POST'])
def api_system_restart():
    try:
        if g.telegram_notifier:
            g.telegram_notifier.send("🔄 [서버 재시작]\n웹 UI에서 서버 재시작을 요청했습니다.\n약 10초 후 자동으로 재연결됩니다.")
    except Exception: pass
    def _do_restart():
        import time as _t; _t.sleep(2)
        subprocess.run(["sudo","systemctl","restart","smart-farm.service"], check=False)
    threading.Thread(target=_do_restart, daemon=True).start()
    return jsonify({"success": True, "message": "서버 재시작 요청 완료. 약 10초 후 새로고침하세요."})
