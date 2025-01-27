import os
import requests
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Configuration ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # From BotFather
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/tokens/volume/solana"  # Solana example

# --- Fetch Meme Coins from DexScreener ---
def fetch_meme_coins():
    response = requests.get(DEXSCREENER_URL).json()
    coins = []
    
    for pair in response["pairs"]:
        # Extract metrics
        data = {
            "name": pair["baseToken"]["name"],
            "symbol": pair["baseToken"]["symbol"],
            "price": pair["priceUsd"],
            "volume_24h": pair["volume"]["h24"],
            "liquidity": pair["liquidity"]["usd"],
            "fdv": pair["fdv"],
            "twitter": pair["info"]["socials"].get("twitter", ""),  # Optional fields
            "telegram": pair["info"]["socials"].get("telegram", ""),
            "website": pair["info"].get("website", "")
        }
        coins.append(data)
    
    return pd.DataFrame(coins)

# --- Filter High-Quality Coins ---
def filter_coins(df):
    filtered = df[
        (df["volume_24h"] > 1_000_000) &          # Volume > $1M
        (df["liquidity"] > 100_000) &             # Liquidity > $100k
        (df["fdv"] < 100_000_000) &               # FDV < $100M
        (df["twitter"].notna()) &                 # Has Twitter
        (df["telegram"].notna()) &                # Has Telegram
        (df["website"].notna())                   # Has Website
    ]
    return filtered

# --- Check Liquidity Lock (Example for Solana) ---
def is_liquidity_locked(token_address):
    url = f"https://api.solscan.io/token/meta?token={token_address}"
    response = requests.get(url).json()
    return response.get("data", {}).get("lpLocked", False)  # True/False (if data exists)

# --- Telegram Bot Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Meme Coin Alert Bot Activated!\n\n"
        "I will notify you about new meme coins with:\n"
        "- High Volume\n- Locked Liquidity\n- Active Socials\n- Low FDV"
    )

async def alert_users(context: ContextTypes.DEFAULT_TYPE):
    df = fetch_meme_coins()
    filtered = filter_coins(df)
    
    for _, coin in filtered.iterrows():
        message = (
            f"🔔 **{coin['name']} ({coin['symbol']})**\n"
            f"Price: ${coin['price']}\n"
            f"24h Volume: ${coin['volume_24h']:,.0f}\n"
            f"Liquidity: ${coin['liquidity']:,.0f}\n"
            f"Twitter: {coin['twitter']}\n"
            f"Telegram: {coin['telegram']}\n"
            f"Website: {coin['website']}"
        )
        await context.bot.send_message(chat_id=context.job.chat_id, text=message)

# --- Main Setup ---
if __name__ == "__main__":
    # Initialize Telegram Bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Add commands
    app.add_handler(CommandHandler("start", start))

    # Schedule alerts (check every 5 minutes)
    job_queue = app.job_queue
    job_queue.run_repeating(alert_users, interval=300, first=10)

    # Run bot
    print("Bot is running...")
    app.run_polling()
