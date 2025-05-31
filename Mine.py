import os
import subprocess
import threading
import time
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = "7759797980:AAHV-FKBXJT10q-d1AEYf0mpHmRubdrzQwE"
ADMIN_ID = 8179218740
MONERO_WALLET = "47HxtCmFXxqVzQSGjQgBnDC1LRTrokf3aMFocbWQRxYzjhjxkfLGjzwE3PJhrCtdQkXPunr8cZZBAiEmY5W46V1UV8mFMZh"
MINER_BIN = "./xmrig"
MINING_POOL = "gulf.moneroocean.stream:10128"
MINER_ALGO = "randomx"
MINER_PASS = "mustafa"

miner_processes = []
mining_thread = None
mining_active = False
mining_threads_per_process = 1
number_of_jobs = 4
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

        print(f"⛏️ Mining with {number_of_jobs} jobs, {mining_threads_per_process} threads each for {mine_time} seconds")
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to the Telegram XMRig Mining Bot!\n\n"
        "Commands:\n"
        "/mine start - Start mining\n"
        "/mine stop - Stop mining\n"
        "/setthreads <num> - Set threads per job\n"
        "/status - Show mining status\n"
        "/setwallet <wallet> - Set mining wallet\n"
        "/restart - Restart miner\n"
        "/info - Show mining info"
    )


async def mine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /mine start|stop")
        return
    cmd = context.args[0].lower()
    if cmd == "start":
        await start_mining(update, context)
    elif cmd == "stop":
        await stop_mining(update, context)
    else:
        await update.message.reply_text("Unknown command. Use /mine start or /mine stop.")


async def start_mining(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global mining_active, mining_thread
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 You are not authorized.")
        return

    if mining_active:
        await update.message.reply_text("⚙️ Mining is already running.")
        return

    mining_active = True
    mining_thread = threading.Thread(target=mining_loop)
    mining_thread.start()
    await update.message.reply_text(f"✅ Mining started with {number_of_jobs} jobs.")


async def stop_mining(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global mining_active, mining_thread
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 You are not authorized.")
        return

    if not mining_active:
        await update.message.reply_text("⚙️ Mining is not running.")
        return

    with lock:
        mining_active = False
    stop_miners()

    if mining_thread and mining_thread.is_alive():
        mining_thread.join(timeout=5)

    mining_thread = None
    await update.message.reply_text("🛑 Mining stopped.")


async def set_threads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global mining_threads_per_process
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 You are not authorized.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setthreads <number>")
        return
    num = int(context.args[0])
    max_threads = os.cpu_count()
    if num < 1 or num > max_threads:
        await update.message.reply_text(f"Threads must be between 1 and {max_threads}")
        return
    mining_threads_per_process = num
    await update.message.reply_text(f"⚙️ Threads per job set to {num}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 You are not authorized.")
        return
    status_text = "✅ Mining is running." if mining_active else "⛔ Mining is stopped."
    await update.message.reply_text(status_text)


async def setwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MONERO_WALLET
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 You are not authorized.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setwallet <wallet_address>")
        return

    MONERO_WALLET = context.args[0]
    await update.message.reply_text(f"✅ Wallet updated to:\n`{MONERO_WALLET}`", parse_mode="Markdown")


async def restart_miner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 You are not authorized.")
        return

    if not mining_active:
        await update.message.reply_text("⚙️ Mining is not running.")
        return

    with lock:
        stop_miners()
        start_miner_threads(mining_threads_per_process, number_of_jobs)

    await update.message.reply_text("♻️ Miner restarted.")


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 You are not authorized.")
        return

    status_text = "✅ Running" if mining_active else "⛔ Stopped"
    info_text = (
        f"🔍 Miner Info:\n"
        f"Wallet: `{MONERO_WALLET}`\n"
        f"Pool: {MINING_POOL}\n"
        f"Algorithm: {MINER_ALGO}\n"
        f"Threads/job: {mining_threads_per_process}\n"
        f"Jobs: {number_of_jobs}\n"
        f"Status: {status_text}"
    )
    await update.message.reply_text(info_text, parse_mode="Markdown")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mine", mine_command))
    app.add_handler(CommandHandler("setthreads", set_threads))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("setwallet", setwallet))
    app.add_handler(CommandHandler("restart", restart_miner))
    app.add_handler(CommandHandler("info", info))
    app.run_polling()


if __name__ == "__main__":
    main()
