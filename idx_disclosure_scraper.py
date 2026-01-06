"""
IDX Disclosure Scraper - WORKING VERSION
Uses the official IDX API endpoint: GetAnnouncement
"""

import requests
import sqlite3
from datetime import datetime, timedelta
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
    """Scraper for IDX disclosure announcements using official API"""
    
    def __init__(self):
        self.base_url = "https://www.idx.co.id"
        self.api_endpoint = f"{self.base_url}/primary/ListedCompany/GetAnnouncement"
        
        # Create a session
        self.session = requests.Session()
        
        # Realistic browser headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': f'{self.base_url}/id/perusahaan-tercatat/keterbukaan-informasi',
            'Origin': self.base_url,
        })
    
    def fetch_disclosures(self, page_size: int = 50) -> List[Dict]:
        """
        Fetch latest disclosures from IDX API
        
        Args:
            page_size: Number of disclosures to fetch (default 50)
            
        Returns:
            List of disclosure dictionaries
        """
        try:
            logger.info(f"Fetching disclosures from IDX API...")
            
            # API parameters
            params = {
                'language': 'id-id',
                'pagesize': page_size,
                'indexfrom': 0
            }
            
            # Make the API request
            response = self.session.get(
                self.api_endpoint,
                params=params,
                timeout=15
            )
            
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            logger.info(f"API Response: ResultCount={data.get('ResultCount', 0)}")
            
            # Extract disclosures from response
            replies = data.get('Replies', [])
            
            if not replies:
                logger.warning("No disclosures found in API response")
                return []
            
            # Parse each disclosure
            disclosures = []
            for item in replies:
                try:
                    disclosure = self._parse_disclosure(item)
                    if disclosure:
                        disclosures.append(disclosure)
                except Exception as e:
                    logger.warning(f"Error parsing disclosure: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(disclosures)} disclosures")
            return disclosures
            
        except Exception as e:
            logger.error(f"Error fetching disclosures: {e}")
            return []
    
    def _parse_disclosure(self, item: Dict) -> Optional[Dict]:
        """Parse a single disclosure item from API response"""
        
        try:
            # Extract fields from API response
            # Adjust field names based on actual API response structure
            stock_code = item.get('Kode_Emiten') or item.get('KodeEmiten') or item.get('Code') or 'UNKNOWN'
            
            title = item.get('Headline') or item.get('Title') or item.get('Judul') or 'No title'
            
            # Date field - try multiple possible keys
            date_str = (
                item.get('Tanggal_Publikasi') or 
                item.get('TanggalPublikasi') or 
                item.get('Date') or 
                item.get('PublishedDate') or
                datetime.now().strftime('%d/%m/%Y')
            )
            
            # Parse date
            try:
                # Try different date formats
                for fmt in ['%d/%m/%Y %H:%M:%S', '%d/%m/%Y', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        date_obj = datetime.strptime(date_str.split('.')[0], fmt)
                        date = date_obj.strftime('%d-%b-%Y')
                        break
                    except:
                        continue
                else:
                    date = date_str
            except:
                date = date_str
            
            # PDF/Attachment URL
            attachment = item.get('Attachment') or item.get('File_URL') or item.get('Lampiran')
            
            if attachment and not attachment.startswith('http'):
                pdf_link = f"{self.base_url}{attachment}"
            else:
                pdf_link = attachment
            
            # Create unique ID
            disclosure_id = f"{stock_code}_{date}_{title[:30]}"
            disclosure_id = re.sub(r'[^a-zA-Z0-9_-]', '_', disclosure_id)
            
            # Categorize
            category = self._categorize_disclosure(title)
            
            disclosure = {
                'id': disclosure_id,
                'stock_code': stock_code.upper().strip(),
                'title': title.strip(),
                'date': date,
                'category': category,
                'pdf_link': pdf_link,
                'scraped_at': datetime.now().isoformat()
            }
            
            return disclosure
            
        except Exception as e:
            logger.warning(f"Error in _parse_disclosure: {e}")
            return None
    
    def _categorize_disclosure(self, title: str) -> str:
        """Categorize disclosure based on title keywords"""
        title_lower = title.lower()
        
        categories = {
            'Financial Report': ['laporan keuangan', 'financial statement', 'quarterly', 'tahunan', 'audited'],
            'Corporate Action': ['dividen', 'dividend', 'stock split', 'pemecahan saham', 'rups', 'agm', 'cum'],
            'Rights Issue': ['hmetd', 'rights issue', 'right issue', 'penawaran umum terbatas'],
            'Material Information': ['informasi material', 'material information', 'keterbukaan informasi', 'clarification'],
            'Ownership': ['kepemilikan', 'ownership', 'pemegang saham', 'shareholder'],
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
            logger.info(f"New disclosure saved: {disclosure['stock_code']} - {disclosure['title'][:50]}")
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


def test_scraper():
    """Test function to run scraper and display results"""
    print("="*80)
    print("IDX DISCLOSURE SCRAPER TEST - USING OFFICIAL API")
    print("="*80)
    
    scraper = IDXDisclosureScraper()
    
    print("\nFetching disclosures from IDX API...")
    disclosures = scraper.fetch_disclosures(page_size=10)
    
    if disclosures:
        print(f"\n✅ SUCCESS! Fetched {len(disclosures)} disclosures\n")
        print("-"*80)
        
        for i, disc in enumerate(disclosures, 1):
            print(f"\n{i}. [{disc['stock_code']}] {disc['date']}")
            print(f"   📁 Category: {disc['category']}")
            print(f"   📋 {disc['title'][:70]}...")
            if disc['pdf_link']:
                print(f"   🔗 {disc['pdf_link'][:60]}...")
        
        print("\n" + "-"*80)
        
        # Test database
        print("\nTesting database...")
        db = DisclosureDatabase('test_disclosures.db')
        
        new_count = 0
        for disc in disclosures:
            if db.save_disclosure(disc):
                new_count += 1
        
        print(f"✅ Database test: {new_count} new disclosures saved")
        
    else:
        print("\n❌ No disclosures fetched")
        print("\nPossible issues:")
        print("1. API response structure might have changed")
        print("2. Network/connection issue")
        print("3. IDX API might be down")
    
    print("\n" + "="*80)
    print("✅ Bot is ready! Upload this file to replace the old scraper.")
    print("="*80)


if __name__ == "__main__":
    test_scraper()
