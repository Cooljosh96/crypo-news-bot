#!/usr/bin/env python3
"""Trending Crypto News Telegram Bot — standard-library only."""
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_FILE = "state.json"
MAX_NEWS_PER_RUN = int(os.getenv("MAX_NEWS_PER_RUN", "12"))
TRENDING_LIMIT = int(os.getenv("TRENDING_LIMIT", "15"))

FEEDS = [
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("The Block", "https://www.theblock.co/rss.xml"),
    ("Google News — crypto", "https://news.google.com/rss/search?q=crypto+OR+cryptocurrency+OR+altcoin+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("Google News — listings and upgrades", "https://news.google.com/rss/search?q=crypto+listing+OR+token+unlock+OR+protocol+upgrade+OR+airdrop+when:1d&hl=en-US&gl=US&ceid=US:en"),
]

def request_text(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "TrendingCryptoNewsBot/1.0 (RSS reader)",
        "Accept": "application/json, application/rss+xml, application/xml, text/xml, */*",
        **(headers or {}),
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")

def telegram_send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError("Telegram API did not confirm the message was sent.")

def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        return {
            "seen_news": set(state.get("seen_news", [])),
            "seen_trending": set(state.get("seen_trending", [])),
            "initialized": bool(state.get("initialized", False)),
        }
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"seen_news": set(), "seen_trending": set(), "initialized": False}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "seen_news": sorted(state["seen_news"])[-1500:],
            "seen_trending": sorted(state["seen_trending"]),
            "initialized": state["initialized"],
        }, f, indent=2)

def parse_date(entry):
    # Return a UTC datetime where possible; otherwise None.
    import email.utils
    raw = entry.get("published") or entry.get("updated") or ""
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None

def fetch_feed(source, url):
    items = []
    try:
        root = ET.fromstring(request_text(url))
        for node in root.findall(".//item"):
            title = clean_text(node.findtext("title", ""))
            link = (node.findtext("link", "") or "").strip()
            guid = (node.findtext("guid", "") or link or title).strip()
            desc = clean_text(node.findtext("description", ""))
            published = node.findtext("pubDate", "") or ""
            if title and link:
                items.append({
                    "source": source, "title": title, "link": link,
                    "id": guid, "description": desc, "published": published,
                })
        # Atom fallback
        if not items:
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for node in root.findall(".//a:entry", ns):
                title = clean_text(node.findtext("a:title", "", ns))
                link_node = node.find("a:link", ns)
                link = link_node.attrib.get("href", "") if link_node is not None else ""
                guid = node.findtext("a:id", "", ns) or link or title
                desc = clean_text(node.findtext("a:summary", "", ns))
                published = node.findtext("a:published", "", ns) or node.findtext("a:updated", "", ns)
                if title and link:
                    items.append({
                        "source": source, "title": title, "link": link,
                        "id": guid, "description": desc, "published": published,
                    })
    except Exception as exc:
        print(f"[WARN] Feed failed: {source}: {exc}")
    return items

def fetch_trending():
    try:
        data = json.loads(request_text("https://api.coingecko.com/api/v3/search/trending"))
        coins = []
        for item in data.get("coins", [])[:TRENDING_LIMIT]:
            coin = item.get("item", {})
            name = coin.get("name", "Unknown")
            symbol = (coin.get("symbol") or "").upper()
            rank = coin.get("market_cap_rank")
            coins.append({"name": name, "symbol": symbol, "rank": rank, "id": coin.get("id", "")})
        return coins
    except Exception as exc:
        print(f"[WARN] CoinGecko trending request failed: {exc}")
        return []

def news_message(item, trending_names):
    title = item["title"]
    description = item.get("description", "")
    # Coin tags are based on words present in the title/description, not guessed from the article.
    combined = (title + " " + description).lower()
    matched = []
    for coin in trending_names:
        name = coin["name"]
        symbol = coin["symbol"]
        if (name and len(name) > 2 and re.search(r"\b" + re.escape(name.lower()) + r"\b", combined)):
            matched.append(name)
        elif symbol and len(symbol) >= 3 and re.search(r"\b" + re.escape(symbol.lower()) + r"\b", combined):
            matched.append(symbol)
    tag_line = "🔥 Trending coin mention: " + ", ".join(dict.fromkeys(matched[:4])) if matched else "🗞️ General crypto-market headline"
    snippet = (description[:240] + "…") if len(description) > 240 else description
    lines = [
        "🚨 TRENDING CRYPTO NEWS",
        "",
        title,
        "",
        f"📰 Source: {item['source']}",
        tag_line,
    ]
    if snippet:
        lines += ["", snippet]
    lines += ["", "🔗 Read more: " + item["link"], "", "ℹ️ News alert only — verify the source and market data."]
    return "\n".join(lines)

def main():
    state = load_state()
    coins = fetch_trending()
    trending_names = coins
    current_ids = {c["id"] for c in coins if c.get("id")}
    new_trending = current_ids - state["seen_trending"] if state["initialized"] else current_ids

    # Send a compact trending snapshot on first run; afterwards, only newly appearing trending coins.
    if coins and not state["initialized"]:
        lines = ["📈 COINGECKO TRENDING COINS", ""]
        for index, coin in enumerate(coins[:10], start=1):
            rank = f" | Market-cap rank #{coin['rank']}" if coin.get("rank") else ""
            symbol = f" ({coin['symbol']})" if coin.get("symbol") else ""
            lines.append(f"{index}. {coin['name']}{symbol}{rank}")
        lines += ["", "Popularity/trending data is not a buy or sell signal."]
        telegram_send("\n".join(lines))
    elif new_trending:
        newly = [c for c in coins if c.get("id") in new_trending]
        lines = ["🆕 NEW COIN(S) ENTERED COINGECKO TRENDING", ""]
        for coin in newly[:10]:
            symbol = f" ({coin['symbol']})" if coin.get("symbol") else ""
            rank = f" | Market-cap rank #{coin['rank']}" if coin.get("rank") else ""
            lines.append(f"• {coin['name']}{symbol}{rank}")
        lines += ["", "Trending means increased search interest, not guaranteed price movement."]
        telegram_send("\n".join(lines))

    all_items = []
    for source, url in FEEDS:
        all_items.extend(fetch_feed(source, url))

    # Stable de-duplication across feeds.
    unique = {}
    for item in all_items:
        key = item["link"] or item["id"]
        if key and key not in unique:
            unique[key] = item

    fresh = [item for key, item in unique.items() if item["id"] not in state["seen_news"]]
    # Prefer recently published items, but don't discard items if a feed has no usable date.
    now = datetime.now(timezone.utc)
    dated, undated = [], []
    for item in fresh:
        dt = parse_date(item)
        if dt is None:
            undated.append(item)
        elif (now - dt).total_seconds() <= 36 * 3600:
            dated.append((dt, item))
    dated.sort(key=lambda pair: pair[0], reverse=True)
    candidates = [item for _, item in dated] + undated

    sent_keys = []
    for item in candidates[:MAX_NEWS_PER_RUN]:
        try:
            telegram_send(news_message(item, trending_names))
            sent_keys.append(item["id"])
            time.sleep(0.4)
        except Exception as exc:
            print(f"[WARN] Telegram send failed for article: {exc}")

    # Mark all fetched IDs as seen to avoid sending old backlog on future runs.
    state["seen_news"].update(item["id"] for item in all_items if item.get("id"))
    state["seen_trending"] = current_ids
    state["initialized"] = True
    save_state(state)
    print(f"Run complete. Trending coins: {len(coins)}; fresh news sent: {len(sent_keys)}; feeds checked: {len(FEEDS)}")

if __name__ == "__main__":
    main()
