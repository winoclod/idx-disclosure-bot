"""
IDX Disclosure Bot - Real-time notification system for Indonesian Stock Exchange disclosures
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time
import re
from typing import List, Dict, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IDXDisclosureScraper:
    """Scraper for IDX disclosure announcements"""
    
    def __init__(self):
        self.base_url = "https://www.idx.co.id"
        self.disclosure_url = f"{self.base_url}/id/perusahaan-tercatat/pengumuman-emiten/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def fetch_disclosures(self) -> List[Dict]:
        """
        Fetch latest disclosures from IDX website
        Returns list of disclosure dictionaries
        """
        try:
            logger.info(f"Fetching disclosures from {self.disclosure_url}")
            response = requests.get(self.disclosure_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            disclosures = []
            
            # Method 1: Try to find table with disclosures
            # IDX typically uses a table structure or DataTables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cols = row.find_all('td')
                    
                    if len(cols) >= 3:  # Minimum columns expected
                        try:
                            disclosure = self._parse_row(cols, row)
                            if disclosure:
                                disclosures.append(disclosure)
                        except Exception as e:
                            logger.warning(f"Error parsing row: {e}")
                            continue
            
            logger.info(f"Found {len(disclosures)} disclosures")
            return disclosures
            
        except requests.RequestException as e:
            logger.error(f"Error fetching disclosures: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []
    
    def _parse_row(self, cols, row) -> Optional[Dict]:
        """
        Parse a table row to extract disclosure information
        Adjust this based on actual IDX table structure
        """
        try:
            # Typical IDX disclosure table structure:
            # Date | Stock Code | Title | Attachment
            
            # Extract date
            date_text = cols[0].get_text(strip=True)
            
            # Extract stock code
            stock_code = cols[1].get_text(strip=True).upper()
            
            # Extract title/description
            title = cols[2].get_text(strip=True)
            
            # Extract PDF link if available
            pdf_link = None
            link_tag = row.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                if not href.startswith('http'):
                    pdf_link = f"{self.base_url}{href}"
                else:
                    pdf_link = href
            
            # Create unique ID
            disclosure_id = f"{stock_code}_{date_text}_{title[:20]}"
            disclosure_id = re.sub(r'[^a-zA-Z0-9_-]', '', disclosure_id)
            
            # Categorize disclosure type
            category = self._categorize_disclosure(title)
            
            disclosure = {
                'id': disclosure_id,
                'stock_code': stock_code,
                'title': title,
                'date': date_text,
                'category': category,
                'pdf_link': pdf_link,
                'scraped_at': datetime.now().isoformat()
            }
            
            return disclosure
            
        except Exception as e:
            logger.warning(f"Error parsing disclosure row: {e}")
            return None
    
    def _categorize_disclosure(self, title: str) -> str:
        """Categorize disclosure based on title keywords"""
        title_lower = title.lower()
        
        categories = {
            'Financial Report': ['laporan keuangan', 'financial statement', 'quarterly', 'tahunan'],
            'Corporate Action': ['dividen', 'dividend', 'stock split', 'pemecahan saham', 'rups', 'agm'],
            'Rights Issue': ['hmetd', 'rights issue', 'right issue', 'penawaran umum terbatas'],
            'Material Information': ['informasi material', 'material information', 'keterbukaan informasi'],
            'Acquisition': ['akuisisi', 'acquisition', 'merger', 'penggabungan'],
            'Other': []
        }
        
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        
        return 'Other'


class DisclosureDatabase:
    """SQLite database handler for tracking disclosures"""
    
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
        
        # User watchlists table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_watchlists (
                user_id INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                PRIMARY KEY (user_id, stock_code)
            )
        ''')
        
        # User settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                all_stocks INTEGER DEFAULT 0,
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
            # Already exists
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
    
    def get_user_watchlist(self, user_id: int) -> List[str]:
        """Get user's watchlist stocks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT stock_code FROM user_watchlists WHERE user_id = ?', (user_id,))
        stocks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return stocks
    
    def add_to_watchlist(self, user_id: int, stock_code: str):
        """Add stock to user's watchlist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO user_watchlists (user_id, stock_code) VALUES (?, ?)',
                         (user_id, stock_code.upper()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def remove_from_watchlist(self, user_id: int, stock_code: str):
        """Remove stock from user's watchlist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_watchlists WHERE user_id = ? AND stock_code = ?',
                      (user_id, stock_code.upper()))
        conn.commit()
        conn.close()
    
    def get_active_users(self) -> List[int]:
        """Get all active users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM user_settings WHERE active = 1')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def set_all_stocks_mode(self, user_id: int, enabled: bool):
        """Enable/disable all stocks mode for user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_settings (user_id, all_stocks, active)
            VALUES (?, ?, 1)
        ''', (user_id, 1 if enabled else 0))
        conn.commit()
        conn.close()
    
    def get_user_settings(self, user_id: int) -> Dict:
        """Get user settings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT all_stocks, active FROM user_settings WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {'all_stocks': bool(row[0]), 'active': bool(row[1])}
        return {'all_stocks': False, 'active': False}


def test_scraper():
    """Test function to run scraper and display results"""
    print("="*60)
    print("IDX DISCLOSURE SCRAPER TEST")
    print("="*60)
    
    scraper = IDXDisclosureScraper()
    disclosures = scraper.fetch_disclosures()
    
    if disclosures:
        print(f"\n✅ Successfully fetched {len(disclosures)} disclosures\n")
        
        for i, disc in enumerate(disclosures[:5], 1):  # Show first 5
            print(f"{i}. {disc['stock_code']} - {disc['date']}")
            print(f"   Category: {disc['category']}")
            print(f"   Title: {disc['title'][:80]}...")
            if disc['pdf_link']:
                print(f"   Link: {disc['pdf_link']}")
            print()
    else:
        print("\n❌ No disclosures fetched. Check:")
        print("   1. Internet connection")
        print("   2. IDX website availability")
        print("   3. Page structure might have changed")
    
    # Test database
    print("\n" + "="*60)
    print("DATABASE TEST")
    print("="*60)
    
    db = DisclosureDatabase('test_disclosures.db')
    
    if disclosures:
        for disc in disclosures[:3]:
            is_new = db.save_disclosure(disc)
            print(f"{'[NEW]' if is_new else '[EXISTS]'} {disc['stock_code']} - {disc['title'][:50]}")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    test_scraper()
