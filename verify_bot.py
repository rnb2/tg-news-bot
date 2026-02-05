import os
import asyncio
import feedparser
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

async def verify_bot():
    print("--- 1. Checking Telegram Connection ---")
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is missing in .env")
        return

    try:
        async with Bot(token=BOT_TOKEN) as bot:
            me = await bot.get_me()
            print(f"Success! Authenticated as: @{me.username} ({me.first_name})")
            print(f"Bot ID: {me.id}")
            
            # Optional: Check if bot can see the channel
            # Note: get_chat might fail if bot is not admin or hasn't interacted with it, 
            # but usually works for public channels or if added as admin.
            try:
                chat = await bot.get_chat(chat_id=CHANNEL_ID)
                print(f"Channel found: {chat.title} ({chat.id})")
            except Exception as e:
                print(f"Warning: Could not get channel info for {CHANNEL_ID}. Make sure the bot is an admin.")
                print(f"Error details: {e}")

    except Exception as e:
        print(f"Error connecting to Telegram: {e}")
        return

    print("\n--- 2. Checking RSS Feeds (Sample) ---")
    test_feed = "https://habr.com/ru/rss/news/?fl=ru" # Using one from sources.py
    print(f"Fetching {test_feed}...")
    try:
        feed = feedparser.parse(test_feed)
        if feed.entries:
            print(f"Success! Found {len(feed.entries)} entries.")
            print(f"Latest title: {feed.entries[0].title}")
        else:
            print("Warning: Feed parsed but no entries found (or empty).")
    except Exception as e:
        print(f"Error fetching RSS: {e}")

if __name__ == "__main__":
    asyncio.run(verify_bot())
