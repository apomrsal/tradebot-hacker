from flask import Flask, request, jsonify
import threading
import time
import json
import os

# ✅ تأكد من أن اسم المتغير هو 'app'
app = Flask(__name__)

# تخزين البيانات
devices = {}
pending_commands = {}
pending_results = {}
device_last_seen = {}

# ===== صفحة رئيسية =====
@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'devices_count': len(devices),
        'commands_count': sum(len(cmds) for cmds in pending_commands.values()),
        'results_count': sum(len(res) for res in pending_results.values())
    })

# ===== نقطة الصحة =====
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': time.time()}), 200

# ===== تسجيل جهاز جديد =====
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        device_id = data.get('device_id')
        device_name = data.get('device_name', device_id)
        
        if not device_id:
            return jsonify({'error': 'Missing device_id'}), 400
            
        devices[device_id] = device_name
        device_last_seen[device_id] = time.time()
        
        if device_id not in pending_commands:
            pending_commands[device_id] = []
        if device_id not in pending_results:
            pending_results[device_id] = []
            
        print(f"📱 Device registered: {device_id} ({device_name})")
        print(f"📊 Total devices: {len(devices)}")
        
        return jsonify({'status': 'registered', 'device_id': device_id}), 200
    except Exception as e:
        print(f"❌ Register error: {e}")
        return jsonify({'error': str(e)}), 500

# ===== إرسال أمر =====
@app.route('/send_command', methods=['POST'])
def send_command():
    try:
        data = request.json
        target = data.get('target')
        command = data.get('command')
        
        if not target or not command:
            return jsonify({'error': 'Missing target or command'}), 400
        
        print(f"📤 Received command: {command} -> {target}")
        
        if target == "ALL":
            sent_count = 0
            for dev_id in devices.keys():
                if dev_id not in pending_commands:
                    pending_commands[dev_id] = []
                pending_commands[dev_id].append(command)
                sent_count += 1
            return jsonify({'status': 'sent_to_all', 'count': sent_count}), 200
        
        elif target in devices:
            if target not in pending_commands:
                pending_commands[target] = []
            pending_commands[target].append(command)
            return jsonify({'status': 'sent', 'device': devices[target]}), 200
        
        else:
            return jsonify({'error': 'Device not found'}), 404
            
    except Exception as e:
        print(f"❌ Send command error: {e}")
        return jsonify({'error': str(e)}), 500

# ===== جلب أوامر الجهاز =====
@app.route('/get_commands/<device_id>', methods=['GET'])
def get_commands(device_id):
    try:
        device_last_seen[device_id] = time.time()
        
        if device_id in pending_commands and pending_commands[device_id]:
            cmd = pending_commands[device_id].pop(0)
            print(f"📩 Command retrieved: {cmd} -> {device_id}")
            return jsonify({'command': cmd}), 200
        
        return jsonify({'command': None}), 200
        
    except Exception as e:
        print(f"❌ Get commands error: {e}")
        return jsonify({'command': None}), 200

# ===== إرسال نتيجة =====
@app.route('/send_result', methods=['POST'])
def send_result():
    try:
        data = request.json
        device_id = data.get('device_id')
        result = data.get('result')
        
        if not device_id or not result:
            return jsonify({'error': 'Missing device_id or result'}), 400
        
        if device_id not in pending_results:
            pending_results[device_id] = []
        pending_results[device_id].append(result)
        
        print(f"📥 Result received from {device_id}: {result[:50]}...")
        return jsonify({'status': 'result_received'}), 200
        
    except Exception as e:
        print(f"❌ Send result error: {e}")
        return jsonify({'error': str(e)}), 500

# ===== جلب نتائج الجهاز =====
@app.route('/get_results/<device_id>', methods=['GET'])
def get_results(device_id):
    try:
        if device_id in pending_results and pending_results[device_id]:
            result = pending_results[device_id].pop(0)
            return jsonify({'result': result}), 200
        return jsonify({'result': None}), 200
    except Exception as e:
        print(f"❌ Get results error: {e}")
        return jsonify({'result': None}), 200

# ===== ✅ عرض قائمة الأجهزة (معدل) =====
@app.route('/devices', methods=['GET'])
def get_devices():
    try:
        # ✅ إرجاع قائمة الأجهزة المسجلة
        return jsonify({'devices': devices}), 200
    except Exception as e:
        print(f"❌ Get devices error: {e}")
        return jsonify({'error': str(e)}), 500

# ===== ✅ عرض حالة جهاز معين =====
@app.route('/device_status/<device_id>', methods=['GET'])
def device_status(device_id):
    try:
        if device_id in devices:
            return jsonify({
                'device_id': device_id,
                'device_name': devices[device_id],
                'last_seen': device_last_seen.get(device_id),
                'commands_pending': len(pending_commands.get(device_id, [])),
                'results_pending': len(pending_results.get(device_id, []))
            }), 200
        return jsonify({'error': 'Device not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ✅ حذف جهاز =====
@app.route('/remove_device/<device_id>', methods=['DELETE'])
def remove_device(device_id):
    try:
        if device_id in devices:
            del devices[device_id]
            if device_id in pending_commands:
                del pending_commands[device_id]
            if device_id in pending_results:
                del pending_results[device_id]
            if device_id in device_last_seen:
                del device_last_seen[device_id]
            print(f"🗑️ Device removed: {device_id}")
            return jsonify({'status': 'removed'}), 200
        return jsonify({'error': 'Device not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ✅ تنظيف الأجهزة غير النشطة =====
@app.route('/cleanup', methods=['POST'])
def cleanup():
    try:
        now = time.time()
        removed = []
        for device_id in list(devices.keys()):
            last_seen = device_last_seen.get(device_id, 0)
            if now - last_seen > 300:  # 5 دقائق
                removed.append(device_id)
                del devices[device_id]
                if device_id in pending_commands:
                    del pending_commands[device_id]
                if device_id in pending_results:
                    del pending_results[device_id]
                if device_id in device_last_seen:
                    del device_last_seen[device_id]
        return jsonify({'status': 'cleanup_done', 'removed': removed}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ✅ تسجيل جهاز عبر GET (للتجربة السريعة) =====
@app.route('/register_manual/<device_id>/<device_name>', methods=['GET'])
def register_manual(device_id, device_name):
    try:
        if not device_id:
            return jsonify({'error': 'Missing device_id'}), 400
            
        devices[device_id] = device_name
        device_last_seen[device_id] = time.time()
        
        if device_id not in pending_commands:
            pending_commands[device_id] = []
        if device_id not in pending_results:
            pending_results[device_id] = []
            
        print(f"📱 Device registered manually: {device_id} ({device_name})")
        print(f"📊 Total devices: {len(devices)}")
        
        return jsonify({'status': 'registered', 'device_id': device_id, 'device_name': device_name}), 200
    except Exception as e:
        print(f"❌ Register error: {e}")
        return jsonify({'error': str(e)}), 500

# ===== ✅ عرض جميع المسارات المتاحة (للاختبار) =====
@app.route('/routes', methods=['GET'])
def list_routes():
    try:
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
        return jsonify({'routes': routes}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("=" * 50)
    print("🚀 TradeBot Server Starting...")
    print("=" * 50)
    print(f"📱 Server will run on port: {port}")
    print("📋 Available endpoints:")
    print("  / - Home")
    print("  /health - Health check")
    print("  /register - Register device (POST)")
    print("  /register_manual/<id>/<name> - Register device (GET)")
    print("  /send_command - Send command (POST)")
    print("  /get_commands/<id> - Get commands (GET)")
    print("  /send_result - Send result (POST)")
    print("  /get_results/<id> - Get results (GET)")
    print("  /devices - List all devices (GET)")
    print("  /device_status/<id> - Device status (GET)")
    print("  /remove_device/<id> - Remove device (DELETE)")
    print("  /cleanup - Cleanup inactive devices (POST)")
    print("  /routes - List all routes (GET)")
    print("=" * 50)
    print("📱 Waiting for devices to register...")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port)
