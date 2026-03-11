import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import matplotlib.pyplot as plt
import asyncio

TOKEN = "8674157496:AAGv5pd9ovV8w2rrwME4a61i6I7eUxE_KyY"
ADMIN_ID = 5410925696

# Database
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

login_user = {}

# Keyboards
Menu_driver = ReplyKeyboardMarkup([
    ["🚕 Order", "⛽ Bensin"],
    ["🍜 Makan", "🅿 Parkir"],
    ["🔧 Servis", "📊 Saldo"],
    ["📅 Rekap Hari", "📆 Rekap Minggu"],
    ["🗓 Rekap Bulan", "📈 Grafik"],
    ["📱 REGIST MOD", "💬 Chat Admin"],
    ["🔑 Reset Password", "🔐 Login"]
], resize_keyboard=True)

Menu_admin = ReplyKeyboardMarkup([
    ["👥 List Driver"],
    ["📊 Semua Transaksi"]
], resize_keyboard=True)

Menu_mod = ReplyKeyboardMarkup([
    ["Shopee MOD", "Grab MOD", "Gojek MOD", "Maxim MOD"]
], resize_keyboard=True)

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.first_name or "Driver"

    if user_id == ADMIN_ID:
        await update.message.reply_text("Admin Panel", reply_markup=Menu_admin)
        return

    welcome_text = f"✨ *Halo {username}* ✨\nSelamat datang di *OJOL SELATAN CIKARANG*"
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=Menu_driver
    )

# Laporan harian
async def laporan_harian(app):
    try:
        hari = str(datetime.now().date())
        c.execute("SELECT driver, tipe, jumlah FROM transaksi WHERE tanggal=?", (hari,))
        data = c.fetchall()
        laporan = "📊 Laporan Harian\n"
        for d in data:
            laporan += f"{d[0]} {d[1]} {d[2]}\n"
        await app.bot.send_message(ADMIN_ID, laporan)
    except Exception as e:
        print("Error laporan harian:", e)

# Pesan
async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user.id

    if text.startswith("daftar"):
        data = text.split()
        if len(data) != 4:
            await update.message.reply_text("Format salah. Ketik:\ndaftar NamaDriver NomorHP Password")
            return
        nama, hp, pw = data[1], data[2], data[3]
        c.execute("INSERT INTO drivers VALUES(NULL,?,?,?,?)", (nama, hp, pw, ""))
        conn.commit()
        await update.message.reply_text("Pendaftaran berhasil")
        return

    if text.startswith("login"):
        data = text.split()
        if len(data) != 3:
            await update.message.reply_text("Format salah. Ketik:\nlogin Nama Password")
            return
        nama, pw = data[1], data[2]
        c.execute("SELECT * FROM drivers WHERE name=? AND password=?", (nama, pw))
        d = c.fetchone()
        if d:
            login_user[user] = nama
            await update.message.reply_text("Login berhasil", reply_markup=Menu_driver)
        else:
            await update.message.reply_text("Login gagal")
        return

    if text == "🔐 Login":
        await update.message.reply_text("Ketik login seperti ini:\nlogin Nama Password")
        return

    if user not in login_user:
        return

    driver = login_user[user]

    if text in ["🚕 Order", "⛽ Bensin", "🍜 Makan", "🅿 Parkir", "🔧 Servis"]:
        context.user_data["tipe"] = text.lower()
        await update.message.reply_text("Masukkan jumlah")
        return

    if text == "📱 REGIST MOD":
        await update.message.reply_text("Pilih MOD", reply_markup=Menu_mod)
        return

    if text in ["Shopee MOD", "Grab MOD", "Gojek MOD", "Maxim MOD"]:
        c.execute("UPDATE drivers SET mod=? WHERE name=?", (text, driver))
        conn.commit()
        await context.bot.send_message(ADMIN_ID, f"{driver} memakai {text}")
        await update.message.reply_text("MOD tersimpan. Silakan chat admin.")
        return

    if text == "💬 Chat Admin":
        await update.message.reply_text("Tuliskan pesan Anda, nanti akan diteruskan ke admin.")
        context.user_data["chat_admin"] = True
        return

    if text == "🔑 Reset Password":
        await update.message.reply_text("Ketik:\nresetpassword NomorHP PasswordBaru")
        return

    if text == "📈 Grafik":
        try:
            c.execute("SELECT jumlah FROM transaksi WHERE driver=? AND tipe='order'", (driver,))
            data = c.fetchall()
            nilai = [d[0] for d in data]
            plt.plot(nilai)
            plt.title("Grafik Penghasilan")
            file = "grafik.png"
            plt.savefig(file)
            plt.close()
            await context.bot.send_photo(user, open(file, "rb"))
        except Exception as e:
            await update.message.reply_text("Gagal membuat grafik")
            print("Error grafik:", e)
        return

    if text.isdigit() and "tipe" in context.user_data:
        jumlah = int(text)
        tipe = context.user_data.get("tipe")
        tanggal = str(datetime.now().date())
        c.execute("INSERT INTO transaksi VALUES(?,?,?,?)", (driver, tanggal, tipe, jumlah))
        conn.commit()
        await update.message.reply_text("Data tersimpan")
        context.user_data.pop("tipe")
        return

# Setup bot
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

# Scheduler
async def start_scheduler(app):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(laporan_harian, "cron", hour=23, minute=59, args=[app])
    scheduler.start()

# === MAIN RUN STABIL RAILWAY ===
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

nest_asyncio.apply()  # penting supaya event loop yang sudah ada bisa jalan

app = ApplicationBuilder().token(TOKEN).build()

# Tambahkan handler
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

# Scheduler di dalam bot
async def setup_scheduler(app):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(laporan_harian, "cron", hour=23, minute=59, args=[app])
    scheduler.start()

# Jalankan bot + scheduler
async def main():
    await setup_scheduler(app)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

# Eksekusi bot tanpa menutup loop
asyncio.get_event_loop().run_until_complete(main())