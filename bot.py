import os
import time
import json
import random
import asyncio
import schedule
import feedparser
from telegram import Bot
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from sources import RSS_SOURCES

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
HISTORY_FILE = "posted_news.json"

if not BOT_TOKEN or not CHANNEL_ID:
    print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set in .env")
    exit(1)

def load_posted_news():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, ValueError):
            return set()
    return set()

def save_posted_news(posted_urls):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(posted_urls), f, indent=4)

def clean_summary(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "lxml")
    text = soup.get_text(separator=" ", strip=True)
    if len(text) > 300:
        return text[:300] + "..."
    return text

async def send_telegram_message(title, link, summary, category):
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            text = f"#{category.replace(' ', '_')}\n\n<b>{title}</b>\n\n{summary}\n\n<a href='{link}'>Читать полностью</a>"
            await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode='HTML')
            return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def get_fresh_news(posted_urls):
    fresh_news = []
    
    # Flatten sources into a list of (Category, URL)
    all_feeds = []
    for category, urls in RSS_SOURCES.items():
        for url in urls:
            all_feeds.append((category, url))
    
    # Shuffle to ensure variety if we are running multiple times
    random.shuffle(all_feeds)

    for category, url in all_feeds:
        try:
            feed = feedparser.parse(url)
            # Check the first few entries to save time
            for entry in feed.entries[:3]:
                link = entry.link
                if link not in posted_urls:
                    title = entry.title
                    summary_raw = entry.get('summary', '') or entry.get('description', '')
                    summary = clean_summary(summary_raw)
                    
                    fresh_news.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'category': category
                    })
        except Exception as e:
            print(f"Error reading RSS {url}: {e}")
            continue
            
    return fresh_news

async def job():
    print("Starting scheduled job: Looking for news...")
    posted_urls = load_posted_news()
    candidates = get_fresh_news(posted_urls)
    
    if not candidates:
        print("No fresh news found.")
        return

    # Pick the first one from our shuffled list
    news_item = candidates[0]
    
    print(f"Posting: {news_item['title']}")
    success = await send_telegram_message(
        news_item['title'], 
        news_item['link'], 
        news_item['summary'],
        news_item['category']
    )
    
    if success:
        posted_urls.add(news_item['link'])
        save_posted_news(posted_urls)
        print("Success!")
    else:
        print("Failed to send message.")

def run_schedule():
    # Schedule 5 posts a day
    times = ["09:00", "12:00", "15:00", "18:00", "21:00"]
    
    for t in times:
        schedule.every().day.at(t).do(lambda: asyncio.run(job()))
    
    print(f"Bot started. Scheduling posts at: {', '.join(times)}")
    
    # Optional: Run once immediately for testing if needed
    asyncio.run(job())
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run_schedule()
