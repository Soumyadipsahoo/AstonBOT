import os 
import requests
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

CHANNEL_LINK = "https://t.me/Astonmovie_Official"
CHANNEL_USERNAME = "@Astonmovie_Official"

ADMIN_ID = 6073299705
ADMIN_PASSWORD = "SOUMYADIP"

INDIAN_LANGS = ["hi", "ta", "te", "ml", "kn"]

# ===== DATABASE =====
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, movie TEXT)")
conn.commit()

# ===== ADMIN STATE =====
waiting_for_password = set()
logged_admins = set()

bot_settings = {
    "force_join": True,
    "maintenance": False
}

# ===== FUNCTIONS =====
def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()

def save_history(user_id, movie):
    cursor.execute("INSERT INTO history VALUES (?, ?)", (user_id, movie))
    conn.commit()

def get_history(user_id):
    cursor.execute("SELECT movie FROM history WHERE user_id=?", (user_id,))
    return cursor.fetchall()

def get_trailer(name):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={name} trailer&type=video&key={YOUTUBE_API_KEY}"
    data = requests.get(url).json()
    try:
        vid = data["items"][0]["id"]["videoId"]
        return f"https://youtube.com/watch?v={vid}"
    except:
        return CHANNEL_LINK

async def check_join(update, context):
    if not bot_settings["force_join"]:
        return True
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, update.effective_user.id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def force_join(update):
    btn = [[InlineKeyboardButton("🔔 Join Channel", url=CHANNEL_LINK)]]
    await update.message.reply_text("⚠️ Join channel first", reply_markup=InlineKeyboardMarkup(btn))

async def check_maintenance(update):
    if bot_settings["maintenance"]:
        await update.message.reply_text("🚧 Bot under maintenance")
        return True
    return False

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    await update.message.reply_text("🔥 Aston Movie Bot Ready!\nUse /movie name")

# ===== MOVIE =====
async def movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_maintenance(update): return
    if not await check_join(update, context):
        await force_join(update)
        return

    user_id = update.effective_user.id
    query = " ".join(context.args)
    save_history(user_id, query)

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
    data = requests.get(url).json()

    indian = [m for m in data["results"] if m.get("original_language") in INDIAN_LANGS]

    if indian:
        m = indian[0]
        trailer = get_trailer(m["title"])
        poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"

        btn = [
            [InlineKeyboardButton("🎥 Trailer", url=trailer)],
            [InlineKeyboardButton("📥 Get Movie", url=CHANNEL_LINK)]
        ]

        await update.message.reply_photo(
            photo=poster,
            caption=f"🎬 {m['title']}\n⭐ {m['vote_average']}\n📅 {m['release_date']}",
            reply_markup=InlineKeyboardMarkup(btn)
        )
    else:
        await update.message.reply_text("❌ Hollywood not allowed")

# ===== HISTORY =====
async def history(update, context):
    data = get_history(update.effective_user.id)
    if not data:
        await update.message.reply_text("No history")
    else:
        text = "\n".join([f"{i+1}. {d[0]}" for i, d in enumerate(data[-10:])])
        await update.message.reply_text(text)

# ===== ADMIN LOGIN =====
async def admin(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    if update.effective_user.id in logged_admins:
        await show_panel(update)
    else:
        waiting_for_password.add(update.effective_user.id)
        await update.message.reply_text("Enter Password:")

async def password_handler(update, context):
    uid = update.effective_user.id
    if uid in waiting_for_password:
        if update.message.text == ADMIN_PASSWORD:
            waiting_for_password.remove(uid)
            logged_admins.add(uid)
            await update.message.reply_text("Login Success")
            await show_panel(update)
        else:
            await update.message.reply_text("Wrong Password")

async def logout(update, context):
    logged_admins.discard(update.effective_user.id)
    await update.message.reply_text("Logged out")

# ===== PANEL =====
async def show_panel(update):
    btn = [
        [InlineKeyboardButton("Users", callback_data="users")],
        [InlineKeyboardButton("Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("Settings", callback_data="settings")],
        [InlineKeyboardButton("Clear History", callback_data="clear")],
        [InlineKeyboardButton("Logout", callback_data="logout")]
    ]
    await update.message.reply_text("Admin Panel", reply_markup=InlineKeyboardMarkup(btn))

async def panel_buttons(update, context):
    q = update.callback_query
    await q.answer()

    if q.from_user.id not in logged_admins:
        return

    if q.data == "users":
        cursor.execute("SELECT COUNT(*) FROM users")
        await q.message.reply_text(f"Users: {cursor.fetchone()[0]}")

    elif q.data == "broadcast":
        await q.message.reply_text("Use /broadcast msg")

    elif q.data == "settings":
        await q.message.reply_text(str(bot_settings))

    elif q.data == "clear":
        cursor.execute("DELETE FROM history")
        conn.commit()
        await q.message.reply_text("History cleared")

    elif q.data == "logout":
        logged_admins.remove(q.from_user.id)
        await q.message.reply_text("Logged out")

# ===== BROADCAST =====
async def broadcast(update, context):
    if update.effective_user.id not in logged_admins:
        return

    msg = " ".join(context.args)
    cursor.execute("SELECT user_id FROM users")
    for u in cursor.fetchall():
        try:
            await context.bot.send_message(chat_id=u[0], text=msg)
        except:
            pass

# ===== MAIN =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("movie", movie))
app.add_handler(CommandHandler("history", history))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("logout", logout))
app.add_handler(CommandHandler("broadcast", broadcast))

app.add_handler(CallbackQueryHandler(panel_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler))

print("🔥 BOT RUNNING...")
app.run_polling()