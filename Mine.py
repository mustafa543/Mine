import os
import subprocess
import threading
import time
import random
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# --- CONFIGURATION ---
BOT_TOKEN = "7759797980:AAHV-FKBXJT10q-d1AEYf0mpHmRubdrzQwE"
ADMIN_ID = 8179218740
MONERO_WALLET = "48FHKyg9XsQ4cFeHZCY3TbLEEo7s42ZULUG1hivPxRHAi6s8FuFFxxJ89wamDqnSNwcmHSPs22M1TfeBzBex6D5V11b1tnx"
MINER_BIN = "./xmrig"
MINING_POOL = "gulf.moneroocean.stream:10128"
MINER_ALGO = "randomx"
MINER_PASS = "mustafa"

# Global variables
miner_processes = []  # list to hold multiple miner processes
mining_thread = None
mining_active = False
mining_threads_per_process = 1  # threads per miner process
number_of_jobs = 4  # total parallel miner jobs
lock = threading.Lock()

def is_admin(user_id):
    return user_id == ADMIN_ID

def start_miner_threads(num_threads, jobs):
    global miner_processes
    miner_processes = []
    for i in range(jobs):
        args = [
            MINER_BIN,
            "-o", MINING_POOL,
            "-a", MINER_ALGO,
            "-u", MONERO_WALLET,
            "-p", MINER_PASS,
            "--threads", str(num_threads),
            "--print-time", "60"
        ]
        p = subprocess.Popen(args)
        miner_processes.append(p)

def stop_miners():
    global miner_processes
    for p in miner_processes:
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
    miner_processes = []

def mining_loop():
    global mining_active
    while mining_active:
        mine_time = random.randint(7200, 10800)
        rest_time = 300

        with lock:
            if not mining_active:
                break
            start_miner_threads(mining_threads_per_process, number_of_jobs)

        print(f"⛏️ Mining with {number_of_jobs} jobs, each with {mining_threads_per_process} threads for {mine_time} seconds")
        for _ in range(mine_time):
            time.sleep(1)
            if not mining_active:
                break

        with lock:
            stop_miners()

        if not mining_active:
            break

        print(f"😴 Resting for {rest_time} seconds")
        for _ in range(rest_time):
            time.sleep(1)
            if not mining_active:
                break

def start_mining(update: Update, context: CallbackContext):
    global mining_active, mining_thread
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("🚫 You are not authorized.")
        return

    if mining_active:
        update.message.reply_text("⚙️ Mining is already running.")
        return

    mining_active = True
    mining_thread = threading.Thread(target=mining_loop)
    mining_thread.start()
    update.message.reply_text(f"✅ Mining started with {number_of_jobs} parallel jobs.")

def stop_mining(update: Update, context: CallbackContext):
    global mining_active, mining_thread
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("🚫 You are not authorized.")
        return

    if not mining_active:
        update.message.reply_text("⚙️ Mining is not running.")
        return

    with lock:
        mining_active = False

    stop_miners()

    if mining_thread and mining_thread.is_alive():
        mining_thread.join(timeout=5)

    mining_thread = None
    update.message.reply_text("🛑 Mining stopped.")

def set_threads(update: Update, context: CallbackContext):
    global mining_threads_per_process
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("🚫 You are not authorized.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        update.message.reply_text("Usage: /setthreads <number>")
        return
    num = int(context.args[0])
    max_threads = os.cpu_count()
    if num < 1 or num > max_threads:
        update.message.reply_text(f"Threads must be between 1 and {max_threads}")
        return
    mining_threads_per_process = num
    update.message.reply_text(f"⚙️ Each mining job threads set to {num}")

def status(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("🚫 You are not authorized.")
        return
    status_text = "✅ Mining is running." if mining_active else "⛔ Mining is stopped."
    update.message.reply_text(status_text)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🤖 Welcome to the Telegram XMRig Mining Bot!\n\n"
        "Commands:\n"
        "/mine start - Start mining\n"
        "/mine stop - Stop mining\n"
        "/setthreads <num> - Set mining threads per job\n"
        "/status - Show mining status\n"
        "/setwallet <wallet_address> - Set mining wallet\n"
        "/restart - Restart miner\n"
        "/info - Show miner info"
    )

def mine_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Usage: /mine start|stop")
        return
    cmd = context.args[0].lower()
    if cmd == "start":
        start_mining(update, context)
    elif cmd == "stop":
        stop_mining(update, context)
    else:
        update.message.reply_text("Unknown command. Use /mine start or /mine stop.")

def setwallet(update: Update, context: CallbackContext):
    global MONERO_WALLET
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("🚫 You are not authorized.")
        return
    
    if len(context.args) != 1:
        update.message.reply_text("Usage: /setwallet <wallet_address>")
        return
    
    new_wallet = context.args[0]
    MONERO_WALLET = new_wallet
    update.message.reply_text(f"✅ Wallet address updated to:\n`{MONERO_WALLET}`", parse_mode="Markdown")

def restart_miner(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("🚫 You are not authorized.")
        return
    
    if not mining_active:
        update.message.reply_text("⚙️ Mining is not running.")
        return

    with lock:
        stop_miners()
        start_miner_threads(mining_threads_per_process, number_of_jobs)

    update.message.reply_text("♻️ Miner restarted.")

def info(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("🚫 You are not authorized.")
        return
    
    status_text = "✅ Running" if mining_active else "⛔ Stopped"
    info_text = (
        f"🔍 Miner Configuration:\n"
        f"Wallet: `{MONERO_WALLET}`\n"
        f"Pool: {MINING_POOL}\n"
        f"Algorithm: {MINER_ALGO}\n"
        f"Threads per job: {mining_threads_per_process}\n"
        f"Number of jobs: {number_of_jobs}\n"
        f"Status: {status_text}"
    )
    update.message.reply_text(info_text, parse_mode="Markdown")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("mine", mine_command))
    dp.add_handler(CommandHandler("setthreads", set_threads))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("setwallet", setwallet))
    dp.add_handler(CommandHandler("restart", restart_miner))
    dp.add_handler(CommandHandler("info", info))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
