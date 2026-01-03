# IDX Disclosure Bot - Simplified Setup

## What Changed?

**Removed:** Watchlist feature (too complex, wastes resources)  
**Kept:** Simple subscribe/unsubscribe system

Everyone who subscribes gets **ALL** disclosures. Simple and efficient!

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Test the Scraper
```bash
python inspect_idx_structure.py
python idx_disclosure_scraper.py
```

### 3. Get Bot Token
- Message @BotFather on Telegram
- Send `/newbot` and follow instructions
- Copy your token

### 4. Configure and Run
Edit `idx_bot_simple.py`:
```python
BOT_TOKEN = "your_actual_token_here"
```

Run:
```bash
python idx_bot_simple.py
```

## 📱 Bot Commands (Simplified)

| Command | What it does |
|---------|-------------|
| `/start` | Subscribe to all disclosures |
| `/stop` | Unsubscribe |
| `/latest` | Show 5 recent disclosures |
| `/stats` | Bot statistics (subscribers, total disclosures) |
| `/help` | Help message |

That's it! No watchlist management, no complexity.

## 🗄️ Database (Simplified)

Only 2 tables now:

1. **disclosures** - All scraped disclosures
2. **subscribers** - Simple list of active users

```sql
CREATE TABLE subscribers (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    subscribed_at TEXT,
    active INTEGER DEFAULT 1
);
```

## 🔄 How It Works

```
Every 10 minutes:
1. Check IDX website
2. Find new disclosures
3. Push to ALL active subscribers
4. Mark as notified
```

Simple, efficient, no filtering logic needed!

## 🚢 Deploy to Railway

Same as before:

```bash
# Push to GitHub
git add .
git commit -m "Simplified IDX bot"
git push

# On Railway:
# 1. New Project from GitHub
# 2. Add env variable: BOT_TOKEN
# 3. Deploy!
```

## 📊 Example Notification

When any new disclosure appears:

```
🔔 New Disclosure: BBRI

📊 Financial Report
📅 03-Jan-2026

📋 Laporan Keuangan Kuartal IV 2025

🔗 [Lihat Dokumen](...)
```

Everyone subscribed gets this - simple!

## ⚡ Files You Need

1. **idx_bot_simple.py** - Main bot (use this instead of idx_disclosure_bot.py)
2. **idx_disclosure_scraper.py** - Scraper (unchanged)
3. **inspect_idx_structure.py** - Debug tool (unchanged)
4. **requirements.txt** - Dependencies

## 🎯 Pro Tips

1. Test with `/latest` to verify scraper works
2. Use `/stats` to monitor subscriber count
3. Bot auto-unsubscribes users who block it
4. Check logs to see notifications being sent

---

Much cleaner than the watchlist version! 🚀
