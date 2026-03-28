import os
import requests
from telegram import *
from telegram.ext import *

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB = os.getenv("TMDB_API_KEY")
YT = os.getenv("YOUTUBE_API_KEY")

CHANNEL = "https://t.me/Astonmovie_Official"

ADMIN_ID = 6073299705
ADMIN_PASSWORD = "SOUMYADIP"

# ================= MOVIE SEARCH =================
def get_movie(q):
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB}&query={q}"
    data = requests.get(url).json()

    if data["results"]:
        m = data["results"][0]

        return {
            "title": m.get("title") or m.get("name"),
            "overview": m.get("overview"),
            "rating": m.get("vote_average"),
            "date": m.get("release_date") or m.get("first_air_date"),
            "poster": "https://image.tmdb.org/t/p/w500" + str(m.get("poster_path")),
            "lang": m.get("original_language")
        }
    return None

# ================= TRAILER =================
def get_trailer(name):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={name} trailer&key={YT}"
    data = requests.get(url).json()

    try:
        vid = data["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{vid}"
    except:
        return None

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🚀 Continue", callback_data="go")]]
    await update.message.reply_text(
        "🎬 *Aston Movie Bot*\n\nSearch anything 👇",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= BUTTON =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "go":
        kb = [
            [InlineKeyboardButton("🔍 Search", callback_data="search")],
            [InlineKeyboardButton("🔥 Trending", callback_data="trend")],
            [InlineKeyboardButton("📢 Channel", url=CHANNEL)]
        ]
        await q.edit_message_text("Choose 👇", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "search":
        await q.edit_message_text("Send movie name")

# ================= SEARCH =================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    movie = get_movie(text)

    # ❌ Not found fallback
    if not movie:
        await update.message.reply_text(
            f"❌ Yeh content yahan nahi hai\n\n"
            f"🎬 Dusre bot me available 👇\n{SECOND_BOT}"
        )
        return

    # ❌ Hollywood filter
    if movie["lang"] == "en":
        await update.message.reply_text(
            f"❌ Hollywood yahan nahi milega\n\n👉 {SECOND_BOT}"
        )
        return

    trailer = get_trailer(movie["title"])

    caption = f"""
🎬 *{movie['title']}*

⭐ {movie['rating']}
📅 {movie['date']}

📝 {movie['overview'][:200]}

📢 Credit: APU
"""

    kb = []

    if trailer:
        kb.append([InlineKeyboardButton("🎥 Trailer", url=trailer)])

    kb.append([InlineKeyboardButton("📥 Download", url=CHANNEL)])

    await update.message.reply_photo(
        photo=movie["poster"],
        caption=caption,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= ADMIN =================
logged = set()

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Access denied")

    await update.message.reply_text("Enter password:")
    context.user_data["admin"] = True

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("admin"):
        if update.message.text == ADMIN_PASSWORD:
            logged.add(update.effective_user.id)
            await update.message.reply_text("✅ Admin Login")
        else:
            await update.message.reply_text("❌ Wrong Password")

# ================= MAIN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_login))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

print("BOT RUNNING")
app.run_polling()
