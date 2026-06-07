import argparse
import asyncio
import html
import json
import os
import random

import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Bot

from sources import RSS_SOURCES

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
HISTORY_FILE = "posted_news.json"

if not BOT_TOKEN or not CHANNEL_ID:
    print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set in .env")
    exit(1)


def load_posted_news() -> set[str]:
    """Load already posted article URLs from the history file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, ValueError):
            return set()
    return set()


def save_posted_news(posted_urls: set[str]) -> None:
    """Save posted article URLs to the history file."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(posted_urls), f, ensure_ascii=False, indent=4)


def clean_summary(html_content: str) -> str:
    """Convert RSS HTML summary to short plain text."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "lxml")
    text = soup.get_text(separator=" ", strip=True)
    if len(text) > 300:
        return text[:300] + "..."
    return text


async def send_telegram_message(
    title: str,
    link: str,
    summary: str,
    category: str,
) -> bool:
    """Send one news item to the configured Telegram channel."""
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            hashtag = category.replace(" ", "_").replace("&", "and")
            text = (
                f"#{html.escape(hashtag)}\n\n"
                f"<b>{html.escape(title)}</b>\n\n"
                f"{html.escape(summary)}\n\n"
                f"<a href='{html.escape(link, quote=True)}'>Читать полностью</a>"
            )
            await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML")
            return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False


def get_fresh_news(posted_urls: set[str]) -> list[dict[str, str]]:
    """Collect fresh RSS entries that were not posted before."""
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
                    summary_raw = entry.get("summary", "") or entry.get("description", "")
                    summary = clean_summary(summary_raw)

                    fresh_news.append(
                        {
                            "title": title,
                            "link": link,
                            "summary": summary,
                            "category": category,
                        }
                    )
        except Exception as e:
            print(f"Error reading RSS {url}: {e}")
            continue

    return fresh_news


async def job() -> bool:
    """Find and publish one fresh news item."""
    print("Starting scheduled job: Looking for news...")
    posted_urls = load_posted_news()
    candidates = get_fresh_news(posted_urls)

    if not candidates:
        print("No fresh news found.")
        return False

    # Pick the first one from our shuffled list
    news_item = candidates[0]

    print(f"Posting: {news_item['title']}")
    success = await send_telegram_message(
        news_item["title"],
        news_item["link"],
        news_item["summary"],
        news_item["category"],
    )

    if success:
        posted_urls.add(news_item["link"])
        save_posted_news(posted_urls)
        print("Success!")
        return True

    print("Failed to send message.")
    return False


def run_schedule() -> None:
    """Run the bot continuously on a local machine."""
    import schedule
    import time

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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Telegram RSS news bot")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="run continuously with local schedule instead of posting once",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.schedule:
        run_schedule()
    else:
        asyncio.run(job())
