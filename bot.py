import os
import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

CHANNEL_LINK = "https://t.me/Astonmovie_Official"
CHANNEL_USERNAME = "@Astonmovie_Official"

ADMIN_PASSWORD = "SOUMYADIP"
ADMIN_ID = int(os.getenv("6073299705", "0"))  # optional, if you want extra security

# ================== DATABASE ==================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, query TEXT)")
conn.commit()

# ================== STATE ==================
user_state = {}
logged_admins = set()

GENRE_MAP = {
    "action": 28,
    "romance": 10749,
    "love": 10749,
    "comedy": 35,
    "horror": 27,
    "thriller": 53,
    "drama": 18,
}

LANG_MAP = {
    "hindi": "hi",
    "english": "en",
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
    "kannada": "kn",
}

# ================== HELPERS ==================
def save_user(user_id: int):
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def save_history(user_id: int, query: str):
    cur.execute("INSERT INTO history (user_id, query) VALUES (?, ?)", (user_id, query))
    conn.commit()

def get_movie(query: str):
    if not TMDB_API_KEY:
        return None

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
    data = requests.get(url, timeout=10).json()

    results = data.get("results", [])
    if not results:
        return None

    m = results[0]
    title = m.get("title", "Unknown")
    overview = m.get("overview", "No overview available.")
    rating = m.get("vote_average", "N/A")
    release = m.get("release_date", "Unknown")
    poster_path = m.get("poster_path")
    poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

    return {
        "title": title,
        "overview": overview,
        "rating": rating,
        "release": release,
        "poster": poster,
    }

def get_trailer(title: str):
    if not YOUTUBE_API_KEY:
        return None

    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={title} trailer&type=video&key={YOUTUBE_API_KEY}"
    )
    data = requests.get(url, timeout=10).json()
    items = data.get("items", [])
    if not items:
        return None

    video_id = items[0]["id"].get("videoId")
    if not video_id:
        return None

    return f"https://youtu.be/{video_id}"

def get_trending():
    if not TMDB_API_KEY:
        return []

    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={TMDB_API_KEY}"
    data = requests.get(url, timeout=10).json()
    results = data.get("results", [])
    return results[:5]

def get_popular():
    if not TMDB_API_KEY:
        return []

    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}"
    data = requests.get(url, timeout=10).json()
    results = data.get("results", [])
    return results[:5]

async def is_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, update.effective_user.id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search Movie", callback_data="search")],
        [InlineKeyboardButton("🔥 Trending", callback_data="trending"),
         InlineKeyboardButton("⭐ Recommendation", callback_data="recommend")],
        [InlineKeyboardButton("🎭 Genre", callback_data="genre"),
         InlineKeyboardButton("🌐 Language", callback_data="lang")],
        [InlineKeyboardButton("👑 Admin", callback_data="admin_open")],
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
    ])

def back_btn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ])

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)

    text = (
        "🎬 *Welcome to Aston Movie Bot*\n\n"
        "Search movies, see posters, ratings, release dates, and more.\n\n"
        "⚡ Bollywood | South | Web Series | Anime\n"
        "📢 Join our channel for updates\n\n"
        "Tap *Continue* to begin."
    )

    keyboard = [[InlineKeyboardButton("✅ Continue", callback_data="continue")]]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

# ================== ADMIN ==================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied.")
        return

    user_state[user_id] = "await_admin_password"
    await update.message.reply_text("🔐 Enter admin password:")

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logged_admins.discard(user_id)
    user_state.pop(user_id, None)
    await update.message.reply_text("🔓 Logged out successfully.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in logged_admins:
        await update.message.reply_text("❌ Admin login required.")
        return

    msg = " ".join(context.args).strip()
    if not msg:
        await update.message.reply_text("Use: /broadcast your message")
        return

    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    sent = 0
    for row in users:
        try:
            await context.bot.send_message(chat_id=row[0], text=msg)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ Broadcast sent to {sent} users.")

# ================== AUTO POST ==================
async def autopost_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in logged_admins:
        await update.message.reply_text("❌ Admin login required.")
        return

    movies = get_trending()
    if not movies:
        await update.message.reply_text("❌ Trending data not available.")
        return

    text = "🔥 *Trending Movies*\n\n"
    for i, m in enumerate(movies, 1):
        text += f"{i}. {m.get('title', 'Unknown')}\n"
    text += "\n📢 Credit: APU"

    await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=text, parse_mode="Markdown")
    await update.message.reply_text("✅ Auto post sent to channel.")

# ================== SEARCH LOGIC ==================
async def search_movie_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_state.get(user_id) == "await_admin_password":
        if text == ADMIN_PASSWORD:
            logged_admins.add(user_id)
            user_state.pop(user_id, None)

            keyboard = [
                [InlineKeyboardButton("📊 Users", callback_data="admin_users")],
                [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
                [InlineKeyboardButton("🚀 Auto Post Now", callback_data="admin_autopost")],
                [InlineKeyboardButton("🔓 Logout", callback_data="admin_logout")],
            ]
            await update.message.reply_text(
                "👑 *Admin Panel*\n\nChoose an option:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Wrong password.")
        return

    if user_state.get(user_id) == "search_movie":
        user_state.pop(user_id, None)
        await send_movie_result(update, context, text)
        return

    # normal free text search
    await send_movie_result(update, context, text)

async def send_movie_result(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    save_history(update.effective_user.id, query)
    movie = get_movie(query)

    if not movie:
        await update.message.reply_text("❌ Movie not found.")
        return

    trailer = get_trailer(movie["title"])
    trailer_text = trailer if trailer else "Not available"

    caption = (
        f"🎬 *{movie['title']}*\n\n"
        f"⭐ Rating: {movie['rating']}\n"
        f"📅 Release: {movie['release']}\n\n"
        f"📝 {movie['overview'][:350]}\n\n"
        f"🎥 Trailer: {trailer_text}\n"
        f"📢 Credit: APU"
    )

    keyboard = [
        [InlineKeyboardButton("📥 Get More / Channel", url=CHANNEL_LINK)],
    ]
    if trailer:
        keyboard.insert(0, [InlineKeyboardButton("🎥 Watch Trailer", url=trailer)])

    if movie["poster"]:
        await update.message.reply_photo(
            photo=movie["poster"],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

# ================== CALLBACKS ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "continue":
        joined = await is_joined(update, context)
        if not joined:
            await query.edit_message_text(
                "❌ Pehle channel join karo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                    [InlineKeyboardButton("🔄 Check Again", callback_data="continue")],
                ]),
            )
            return

        await query.edit_message_text(
            "✅ Welcome to Aston Movie Bot\n\nChoose an option:",
            reply_markup=main_menu(),
        )
        return

    if data == "home":
        await query.edit_message_text(
            "✅ Welcome to Aston Movie Bot\n\nChoose an option:",
            reply_markup=main_menu(),
        )
        return

    if data == "search":
        user_state[user_id] = "search_movie"
        await query.edit_message_text(
            "🔍 Send movie name now.",
            reply_markup=back_btn(),
        )
        return

    if data == "trending":
        movies = get_trending()
        if not movies:
            await query.edit_message_text("❌ Trending data not available.", reply_markup=back_btn())
            return

        text = "🔥 *Trending Movies*\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m.get('title', 'Unknown')}\n"
        text += "\n📢 Credit: APU"

        await query.edit_message_text(text, reply_markup=back_btn(), parse_mode="Markdown")
        return

    if data == "recommend":
        movies = get_popular()
        if not movies:
            await query.edit_message_text("❌ Recommendation data not available.", reply_markup=back_btn())
            return

        text = "⭐ *Recommended Movies*\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m.get('title', 'Unknown')}\n"
        text += "\n📢 Credit: APU"

        await query.edit_message_text(text, reply_markup=back_btn(), parse_mode="Markdown")
        return

    if data == "genre":
        keyboard = [
            [InlineKeyboardButton("Action", callback_data="genre_action"),
             InlineKeyboardButton("Romance", callback_data="genre_romance")],
            [InlineKeyboardButton("Comedy", callback_data="genre_comedy"),
             InlineKeyboardButton("Horror", callback_data="genre_horror")],
            [InlineKeyboardButton("Drama", callback_data="genre_drama"),
             InlineKeyboardButton("Thriller", callback_data="genre_thriller")],
        ]
        await query.edit_message_text(
            "🎭 Select a genre:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data == "lang":
        keyboard = [
            [InlineKeyboardButton("Hindi", callback_data="lang_hindi"),
             InlineKeyboardButton("English", callback_data="lang_english")],
            [InlineKeyboardButton("Tamil", callback_data="lang_tamil"),
             InlineKeyboardButton("Telugu", callback_data="lang_telugu")],
            [InlineKeyboardButton("Malayalam", callback_data="lang_malayalam"),
             InlineKeyboardButton("Kannada", callback_data="lang_kannada")],
        ]
        await query.edit_message_text(
            "🌐 Select a language:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("genre_"):
        key = data.split("_", 1)[1]
        genre_id = GENRE_MAP.get(key)
        if not genre_id:
            await query.edit_message_text("❌ Genre not found.", reply_markup=back_btn())
            return

        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}"
        res = requests.get(url, timeout=10).json()
        results = res.get("results", [])[:5]

        if not results:
            await query.edit_message_text("❌ No movies found.", reply_markup=back_btn())
            return

        text = f"🎭 *{key.title()} Movies*\n\n"
        for i, m in enumerate(results, 1):
            text += f"{i}. {m.get('title', 'Unknown')}\n"
        text += "\n📢 Credit: APU"

        await query.edit_message_text(text, reply_markup=back_btn(), parse_mode="Markdown")
        return

    if data.startswith("lang_"):
        key = data.split("_", 1)[1]
        lang_code = LANG_MAP.get(key)
        if not lang_code:
            await query.edit_message_text("❌ Language not found.", reply_markup=back_btn())
            return

        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_original_language={lang_code}"
        res = requests.get(url, timeout=10).json()
        results = res.get("results", [])[:5]

        if not results:
            await query.edit_message_text("❌ No movies found.", reply_markup=back_btn())
            return

        text = f"🌐 *{key.title()} Movies*\n\n"
        for i, m in enumerate(results, 1):
            text += f"{i}. {m.get('title', 'Unknown')}\n"
        text += "\n📢 Credit: APU"

        await query.edit_message_text(text, reply_markup=back_btn(), parse_mode="Markdown")
        return

    if data == "admin_open":
        user_state[user_id] = "await_admin_password"
        await query.edit_message_text(
            "🔐 Send admin password now.\n\nUse: `SOUMYADIP`",
            reply_markup=back_btn(),
            parse_mode="Markdown",
        )
        return

    if data == "admin_users":
        if user_id not in logged_admins:
            await query.edit_message_text("❌ Admin login required.", reply_markup=back_btn())
            return

        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        await query.edit_message_text(f"👥 Total Users: {count}", reply_markup=back_btn())
        return

    if data == "admin_broadcast":
        if user_id not in logged_admins:
            await query.edit_message_text("❌ Admin login required.", reply_markup=back_btn())
            return

        user_state[user_id] = "await_broadcast"
        await query.edit_message_text(
            "📢 Send the broadcast message now.",
            reply_markup=back_btn(),
        )
        return

    if data == "admin_autopost":
        if user_id not in logged_admins:
            await query.edit_message_text("❌ Admin login required.", reply_markup=back_btn())
            return

        movies = get_trending()
        if not movies:
            await query.edit_message_text("❌ Trending data not available.", reply_markup=back_btn())
            return

        text = "🔥 *Trending Movies*\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m.get('title', 'Unknown')}\n"
        text += "\n📢 Credit: APU"

        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=text,
            parse_mode="Markdown",
        )
        await query.edit_message_text("✅ Auto post sent to channel.", reply_markup=back_btn())
        return

    if data == "admin_logout":
        logged_admins.discard(user_id)
        user_state.pop(user_id, None)
        await query.edit_message_text("🔓 Logged out.", reply_markup=back_btn())
        return

# ================== MESSAGE ROUTER ==================
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_state.get(user_id) == "await_broadcast":
        if user_id not in logged_admins:
            await update.message.reply_text("❌ Admin login required.")
            return

        cur.execute("SELECT user_id FROM users")
        users = cur.fetchall()

        sent = 0
        for row in users:
            try:
                await context.bot.send_message(chat_id=row[0], text=text)
                sent += 1
            except:
                pass

        user_state.pop(user_id, None)
        await update.message.reply_text(f"✅ Broadcast sent to {sent} users.")
        return

    if user_state.get(user_id) == "await_admin_password":
        if text == ADMIN_PASSWORD:
            logged_admins.add(user_id)
            user_state.pop(user_id, None)

            keyboard = [
                [InlineKeyboardButton("📊 Users", callback_data="admin_users")],
                [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
                [InlineKeyboardButton("🚀 Auto Post Now", callback_data="admin_autopost")],
                [InlineKeyboardButton("🔓 Logout", callback_data="admin_logout")],
            ]
            await update.message.reply_text(
                "👑 *Admin Panel*\n\nChoose an option:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Wrong password.")
        return

    if user_state.get(user_id) == "search_movie":
        user_state.pop(user_id, None)
        await send_movie_result(update, context, text)
        return

    await send_movie_result(update, context, text)

# ================== MAIN ==================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("logout", logout))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

print("BOT RUNNING...")
app.run_polling(drop_pending_updates=True)
