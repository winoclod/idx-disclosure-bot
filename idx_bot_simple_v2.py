"""
IDX Disclosure Telegram Bot - Simplified Version
Push ALL new disclosures to all subscribed users
"""

import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from idx_disclosure_scraper import IDXDisclosureScraper, DisclosureDatabase
import logging
from typing import List, Dict
import sqlite3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimplifiedDatabase:
    """Simplified database - just track disclosures and subscribers"""
    
    def __init__(self, db_path: str = 'idx_disclosures.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Disclosures table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disclosures (
                id TEXT PRIMARY KEY,
                stock_code TEXT NOT NULL,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                category TEXT,
                pdf_link TEXT,
                scraped_at TEXT NOT NULL,
                notified INTEGER DEFAULT 0
            )
        ''')
        
        # Subscribers table - simple list of active users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                subscribed_at TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def save_disclosure(self, disclosure: Dict) -> bool:
        """Save disclosure to database, return True if new"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO disclosures (id, stock_code, title, date, category, pdf_link, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                disclosure['id'],
                disclosure['stock_code'],
                disclosure['title'],
                disclosure['date'],
                disclosure['category'],
                disclosure['pdf_link'],
                disclosure['scraped_at']
            ))
            conn.commit()
            logger.info(f"New disclosure saved: {disclosure['id']}")
            return True
            
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def mark_notified(self, disclosure_id: str):
        """Mark disclosure as notified"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE disclosures SET notified = 1 WHERE id = ?', (disclosure_id,))
        conn.commit()
        conn.close()
    
    def subscribe_user(self, user_id: int, username: str = None):
        """Subscribe a user"""
        from datetime import datetime
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO subscribers (user_id, username, subscribed_at, active)
                VALUES (?, ?, ?, 1)
            ''', (user_id, username, datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error subscribing user: {e}")
            return False
        finally:
            conn.close()
    
    def unsubscribe_user(self, user_id: int):
        """Unsubscribe a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE subscribers SET active = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def get_active_subscribers(self) -> List[int]:
        """Get all active subscribers"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM subscribers WHERE active = 1')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def is_subscribed(self, user_id: int) -> bool:
        """Check if user is subscribed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT active FROM subscribers WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == 1
    
    def get_subscriber_count(self) -> int:
        """Get total active subscribers"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM subscribers WHERE active = 1')
        count = cursor.fetchone()[0]
        conn.close()
        return count


class IDXDisclosureBot:
    """Simplified Telegram bot - just subscribe/unsubscribe"""
    
    def __init__(self, token: str):
        self.token = token
        self.scraper = IDXDisclosureScraper()
        self.db = SimplifiedDatabase()
        self.application = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # Auto-subscribe on start
        self.db.subscribe_user(user_id, username)
        
        welcome_message = """
🔔 *IDX Disclosure Bot*

Selamat datang! Bot ini akan memberitahu Anda tentang *semua* keterbukaan informasi terbaru dari Bursa Efek Indonesia.

✅ Anda sekarang *berlangganan* notifikasi!

*Perintah yang tersedia:*

/latest - Tampilkan 5 disclosure terakhir
/stop - Berhenti berlangganan notifikasi
/start - Aktifkan kembali notifikasi
/stats - Lihat statistik bot
/help - Bantuan

Setiap ada disclosure baru dari emiten manapun di IDX, Anda akan langsung mendapat notifikasi! 🚀
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command - unsubscribe"""
        user_id = update.effective_user.id
        self.db.unsubscribe_user(user_id)
        
        await update.message.reply_text(
            "❌ Anda telah berhenti berlangganan.\n\n"
            "Gunakan /start untuk berlangganan kembali.",
            parse_mode='Markdown'
        )
    
    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /latest command - show recent disclosures"""
        await update.message.reply_text("🔍 Mengambil disclosure terbaru...")
        
        disclosures = self.scraper.fetch_disclosures()
        
        if not disclosures:
            await update.message.reply_text("❌ Tidak dapat mengambil data dari IDX.")
            return
        
        # Send each disclosure as separate message with rich format
        for i, disc in enumerate(disclosures[:5], 1):
            message = f"*{i}. {disc['title']}*\n\n"
            message += f"📊 *Stock*\n{disc['stock_code']}\n\n"
            message += f"📅 *Tanggal*\n{disc['date']}\n"
            
            if disc['pdf_link']:
                message += f"\n🔗 *Lampiran*\n[Lihat Dokumen]({disc['pdf_link']})\n"
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown', 
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.5)  # Small delay between messages
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show bot statistics"""
        subscriber_count = self.db.get_subscriber_count()
        
        # Get total disclosures tracked
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM disclosures')
        total_disclosures = cursor.fetchone()[0]
        conn.close()
        
        stats_message = f"""
📊 *Statistik Bot*

👥 Total Subscribers: *{subscriber_count}*
📋 Total Disclosures Tracked: *{total_disclosures}*
⏱️ Check Interval: *10 menit*

Bot aktif 24/7 memantau disclosure IDX!
        """
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📖 *Bantuan IDX Disclosure Bot*

*Perintah:*
/start - Berlangganan notifikasi
/stop - Berhenti berlangganan
/latest - Lihat 5 disclosure terakhir
/stats - Lihat statistik bot
/help - Bantuan ini

*Kategori Disclosure:*
• 📊 Financial Report - Laporan keuangan
• 📈 Corporate Action - RUPS, dividen, stock split
• 💰 Rights Issue - HMETD
• ℹ️ Material Information - Info material
• 🤝 Acquisition - Akuisisi, merger
• 📄 Other - Lainnya

*Cara Kerja:*
Bot memeriksa website IDX setiap 10 menit. Saat ada disclosure baru dari emiten manapun, Anda langsung mendapat push notification!

Sederhana, efisien, dan real-time! 🚀
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def check_and_notify(self, context: ContextTypes.DEFAULT_TYPE):
        """Periodic task to check for new disclosures and notify all subscribers"""
        logger.info("Checking for new disclosures...")
        
        # Fetch latest disclosures
        disclosures = self.scraper.fetch_disclosures()
        
        if not disclosures:
            logger.warning("No disclosures fetched")
            return
        
        # Process each disclosure
        new_count = 0
        for disclosure in disclosures:
            is_new = self.db.save_disclosure(disclosure)
            
            if is_new:
                new_count += 1
                # Notify ALL subscribers
                await self.notify_all_subscribers(disclosure, context)
                self.db.mark_notified(disclosure['id'])
        
        if new_count > 0:
            logger.info(f"Found {new_count} new disclosures and notified subscribers")
        else:
            logger.info("No new disclosures")
    
    async def notify_all_subscribers(self, disclosure: Dict, context: ContextTypes.DEFAULT_TYPE):
        """Notify all active subscribers about new disclosure"""
        subscribers = self.db.get_active_subscribers()
        
        if not subscribers:
            logger.info("No active subscribers")
            return
        
        message = self.format_disclosure_message(disclosure)
        
        success_count = 0
        fail_count = 0
        
        for user_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"Failed to notify user {user_id}: {e}")
                # If user blocked the bot, unsubscribe them
                if "Forbidden" in str(e) or "blocked" in str(e).lower():
                    self.db.unsubscribe_user(user_id)
                    logger.info(f"Unsubscribed user {user_id} (blocked bot)")
        
        logger.info(f"Notified {success_count} subscribers about {disclosure['stock_code']} (failed: {fail_count})")
    
    def format_disclosure_message(self, disclosure: Dict) -> str:
        """Format disclosure as Telegram message - Rich format like Satpam IDX"""
        
        # Get full title without truncation
        title = disclosure['title']
        stock_code = disclosure['stock_code']
        
        # Create rich message format
        message = f"""*{title}*

📊 *Stock*
{stock_code}

📅 *Tanggal*
{disclosure['date']}
"""
        
        # Add PDF links if available - use Markdown link like /latest command
        if disclosure['pdf_link']:
            message += f"""
🔗 *Dokumen PDF*
[Lihat Dokumen]({disclosure['pdf_link']})

_Tahan link dan pilih open in_
"""
        
        return message
    
    def run(self):
        """Run the bot"""
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("latest", self.latest_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Add periodic job to check for new disclosures every 10 minutes
        job_queue = self.application.job_queue
        job_queue.run_repeating(
            self.check_and_notify,
            interval=600,  # 10 minutes
            first=10  # First check after 10 seconds
        )
        
        # Start bot
        logger.info("Bot starting...")
        logger.info(f"Active subscribers: {self.db.get_subscriber_count()}")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Get bot token from environment variable (set in Railway)
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable not set!")
        logger.error("Set it in Railway dashboard under Variables tab")
        exit(1)
    
    bot = IDXDisclosureBot(BOT_TOKEN)
    bot.run()
