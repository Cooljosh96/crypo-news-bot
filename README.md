# Trending Crypto News Telegram Bot

A small Telegram bot that checks CoinGecko trending coins and crypto RSS feeds, then sends new headlines to Telegram. It uses Python's standard library only.

## What it does
- Sends a CoinGecko trending-coins snapshot on the first run.
- Alerts when a new coin enters CoinGecko's trending list.
- Checks Cointelegraph, CoinDesk, The Block, and Google News RSS searches for crypto headlines, listings, token unlocks, protocol upgrades, and airdrops.
- Removes duplicate headlines and remembers sent stories in `state.json`.
- Runs on GitHub Actions every 10 minutes.

**Important:** trending popularity and news are not trading signals. Sources may be delayed, unavailable, or rate-limited. GitHub scheduled runs can also be delayed.

## Set it up from your phone

### 1. Create a separate Telegram bot
1. Open Telegram and search for the official `@BotFather`.
2. Send `/newbot` and follow its instructions.
3. Give the bot a display name and a unique username ending in `bot`.
4. Copy the token BotFather gives you. Keep it private; anyone with it may control your bot.

### 2. Get your Telegram chat ID
1. Open your new bot using the link BotFather gives you.
2. Tap **Start** and send it a message such as `hello`.
3. In a browser, open this URL after replacing `YOUR_TOKEN` with the token:
   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
4. Find `message` → `chat` → `id`. That number is your `TELEGRAM_CHAT_ID`.
5. Do not share the URL or screenshot while it contains your token. If you expose the token, revoke it through BotFather and create a new one.

### 3. Create a GitHub repository
1. Sign in to GitHub and create a new repository named `trending-crypto-news-bot`.
2. Public repositories can run standard GitHub-hosted Actions without runner-minute charges; private repositories use the account's included quota and limits.
3. Add these files at the exact paths shown in this project:
   - `main.py`
   - `.github/workflows/bot.yml`
   - `state.json`
4. For the first setup, create `state.json` containing:
   `{ "seen_news": [], "seen_trending": [], "initialized": false }`

### 4. Add secrets
In the repository, go to **Settings → Secrets and variables → Actions → New repository secret**.
Create:
- `TELEGRAM_BOT_TOKEN` = token from BotFather
- `TELEGRAM_CHAT_ID` = your chat ID number

Never put either value directly into `main.py` or the workflow file.

### 5. Enable and test it
1. Open the repository's **Actions** tab and enable workflows if GitHub asks.
2. Select **Trending Crypto News Bot**.
3. Tap **Run workflow** to test it immediately.
4. Open the run and inspect the logs if it fails.
5. The scheduled workflow runs every 10 minutes after the files are on the repository's default branch.

## Adjusting the number of alerts
In `.github/workflows/bot.yml`, change `MAX_NEWS_PER_RUN: "12"` to a smaller or larger number. A large number can create a lot of notifications. `TRENDING_LIMIT` controls how many CoinGecko trending coins are considered (public endpoint commonly returns up to 15).

## Troubleshooting
- **No message arrives:** confirm you tapped Start in the bot chat, then check both repository secrets.
- **401 from Telegram:** token is wrong or has been revoked; create a new token with BotFather and update the secret.
- **403 from Telegram:** start the bot chat and confirm the chat ID is correct.
- **CoinGecko or RSS errors:** a source may rate-limit or temporarily block requests; retry the workflow later.
- **No scheduled runs:** confirm the workflow is on the default branch and check Actions settings. GitHub may delay scheduled workflows during busy periods.
- **State commit fails:** confirm workflow permissions allow read/write access to repository contents in Settings → Actions → General.

## Sources and limitations
- CoinGecko trending search: `https://api.coingecko.com/api/v3/search/trending`
- Cointelegraph RSS: `https://cointelegraph.com/rss`
- CoinDesk RSS: `https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml`
- The Block RSS: `https://www.theblock.co/rss.xml`
- This starter version does not provide guaranteed real-time coverage, financial advice, or verified automatic sentiment analysis. Coin mentions are matched only when a trending coin's name or symbol appears in the headline/summary.
