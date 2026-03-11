import nest_asyncio
nest_asyncio.apply()

import sqlite3
from datetime import datetime
from telegram import ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import matplotlib.pyplot as plt

# === Token & Admin ===
TOKEN = "8674157496:AAGv5pd9ovV8w2rrwME4a61i6I7eUxE_KyY"
ADMIN_ID = 5410925696

# === Database ===
conn = sqlite3.connect("ojol.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS drivers(
id INTEGER PRIMARY KEY,
name TEXT,
phone TEXT,
password TEXT,
mod TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS transaksi(
driver TEXT,
tanggal TEXT,
tipe TEXT,
jumlah INTEGER
)""")
conn.commit()

# === Login tracking ===
login_user = {}

# === Keyboards ===
menu_driver = ReplyKeyboardMarkup([
    ["🚕 Order","⛽ Bensin"],
    ["🍜 Makan","🅿 Parkir"],
    ["🔧 Servis","📊 Saldo"],
    ["📈 Grafik","📱 REGIST MOD"]
], resize_keyboard=True)

menu_mod = ReplyKeyboardMarkup([
    ["Shopee MOD"],["Grab MOD"],["Gojek MOD"],["Maxim MOD"]
], resize_keyboard=True)

# === Handlers ===
async def start(update, context):
    await update.message.reply_text(
        f"✨ Halo {update.message.from_user.first_name}!\nSelamat datang di OJOL SELATAN CIKARANG\n\n"
        "Login:\nlogin Nama Password"
    )

async def laporan_harian(app):
    hari = str(datetime.now().date())
    c.execute("SELECT driver,tipe,jumlah FROM transaksi WHERE tanggal=?", (hari,))
    data = c.fetchall()
    if data:
        laporan = "📊 Laporan Harian\n"
        for d in data:
            laporan += f"{d[0]} {d[1]} {d[2]}\n"
        await app.bot.send_message(ADMIN_ID, laporan)

async def message(update, context):
    text = update.message.text
    user = update.message.from_user.id

    # Login
    if text.startswith("login"):
        data = text.split()
        if len(data) != 3:
            await update.message.reply_text("Format salah!\nlogin Nama Password")
            return
        nama, pw = data[1], data[2]
        c.execute("SELECT * FROM drivers WHERE name=? AND password=?", (nama, pw))
        d = c.fetchone()
        if d:
            login_user[user] = nama
            await update.message.reply_text("Login berhasil", reply_markup=menu_driver)
        else:
            await update.message.reply_text("Login gagal")
        return

    if user not in login_user:
        return

    driver = login_user[user]

    # Pilih MOD
    if text == "📱 REGIST MOD":
        await update.message.reply_text("Pilih MOD", reply_markup=menu_mod)
    elif text in ["Shopee MOD","Grab MOD","Gojek MOD","Maxim MOD"]:
        c.execute("UPDATE drivers SET mod=? WHERE name=?", (text, driver))
        conn.commit()
        await update.message.reply_text(f"MOD tersimpan: {text}")
        await context.bot.send_message(ADMIN_ID, f"{driver} memakai {text}")
        return

    # Grafik
    elif text == "📈 Grafik":
        c.execute("SELECT jumlah FROM transaksi WHERE driver=? AND tipe='order'", (driver,))
        data = c.fetchall()
        if not data:
            await update.message.reply_text("Belum ada data")
            return
        nilai = [d[0] for d in data]
        plt.plot(nilai)
        plt.title("Grafik Penghasilan")
        file = "grafik.png"
        plt.savefig(file)
        plt.close()
        await context.bot.send_photo(user, open(file,"rb"))

    # Input transaksi
    elif text.isdigit():
        tipe = context.user_data.get("tipe")
        if tipe:
            jumlah = int(text)
            tanggal = str(datetime.now().date())
            c.execute("INSERT INTO transaksi VALUES(?,?,?,?)",(driver,tanggal,tipe,jumlah))
            conn.commit()
            await update.message.reply_text("Data tersimpan")

# === Application & Scheduler ===
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

scheduler = AsyncIOScheduler()
scheduler.add_job(laporan_harian, "cron", hour=23, minute=59, args=[app])
scheduler.start()

# === Run polling ===
app.run_polling()