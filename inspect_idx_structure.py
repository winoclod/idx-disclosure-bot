"""
IDX Page Structure Inspector
Use this to understand the actual HTML structure of IDX disclosure page
Run this on your local machine to see how to parse the page
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime


def inspect_idx_page():
    """Comprehensive inspection of IDX disclosure page"""
    
    url = "https://www.idx.co.id/id/perusahaan-tercatat/pengumuman-emiten/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print("="*80)
    print("IDX DISCLOSURE PAGE STRUCTURE INSPECTOR")
    print("="*80)
    print(f"\nFetching: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch page. Status: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Save full HTML for manual inspection
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = f"idx_page_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"✅ Saved full HTML to: {html_file}")
        
        print("\n" + "="*80)
        print("ANALYZING PAGE STRUCTURE")
        print("="*80)
        
        # 1. Find all tables
        print("\n📊 TABLES FOUND:")
        tables = soup.find_all('table')
        print(f"Total tables: {len(tables)}")
        
        for i, table in enumerate(tables, 1):
            print(f"\n--- Table {i} ---")
            print(f"ID: {table.get('id', 'None')}")
            print(f"Class: {table.get('class', 'None')}")
            
            # Count rows
            thead = table.find('thead')
            tbody = table.find('tbody')
            rows = table.find_all('tr')
            
            print(f"Total rows: {len(rows)}")
            if thead:
                print(f"Has <thead>: Yes")
            if tbody:
                print(f"Has <tbody>: Yes")
            
            # Show header row
            if rows:
                header_row = rows[0]
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                print(f"Headers: {headers}")
                
                # Show first data row if exists
                if len(rows) > 1:
                    first_data_row = rows[1]
                    cols = first_data_row.find_all('td')
                    print(f"First row columns: {len(cols)}")
                    
                    # Print each column
                    for j, col in enumerate(cols):
                        text = col.get_text(strip=True)[:50]
                        links = col.find_all('a')
                        print(f"  Col {j}: {text}")
                        if links:
                            print(f"    Links: {[a.get('href') for a in links[:2]]}")
        
        # 2. Check for DataTables or AJAX
        print("\n" + "="*80)
        print("CHECKING FOR DYNAMIC CONTENT")
        print("="*80)
        
        scripts = soup.find_all('script')
        print(f"\nTotal <script> tags: {len(scripts)}")
        
        ajax_indicators = []
        datatable_found = False
        
        for script in scripts:
            if script.string:
                script_text = script.string.lower()
                
                # Check for common patterns
                if 'datatable' in script_text:
                    datatable_found = True
                    print("✅ DataTable detected!")
                    
                    # Try to extract AJAX URL
                    if 'ajax' in script_text:
                        # Look for URL patterns
                        import re
                        urls = re.findall(r'["\']([^"\']*(?:api|data|json)[^"\']*)["\']', script.string)
                        if urls:
                            print(f"Possible AJAX URLs: {urls[:3]}")
                            ajax_indicators.extend(urls)
                
                if 'ajax' in script_text and 'url' in script_text:
                    print("⚠️  AJAX loading detected - may need alternative approach")
        
        # 3. Look for API endpoints in page
        print("\n" + "="*80)
        print("SEARCHING FOR API ENDPOINTS")
        print("="*80)
        
        page_source = str(soup)
        
        # Common API patterns
        api_patterns = [
            r'/api/[^\s"\'<>]+',
            r'/data/[^\s"\'<>]+',
            r'\.json[^\s"\'<>]*',
            r'/endpoint/[^\s"\'<>]+'
        ]
        
        import re
        found_apis = set()
        
        for pattern in api_patterns:
            matches = re.findall(pattern, page_source)
            found_apis.update(matches)
        
        if found_apis:
            print("Possible API endpoints found:")
            for api in list(found_apis)[:10]:
                print(f"  - {api}")
        else:
            print("No obvious API endpoints found")
        
        # 4. Check for specific disclosure-related elements
        print("\n" + "="*80)
        print("DISCLOSURE-SPECIFIC ELEMENTS")
        print("="*80)
        
        disclosure_keywords = [
            'pengumuman', 'emiten', 'disclosure', 'announcement',
            'keterbukaan', 'informasi'
        ]
        
        for keyword in disclosure_keywords:
            elements = soup.find_all(class_=lambda x: x and keyword in str(x).lower())
            if elements:
                print(f"Elements with '{keyword}' in class: {len(elements)}")
        
        # 5. Generate sample parser code
        print("\n" + "="*80)
        print("RECOMMENDED PARSER APPROACH")
        print("="*80)
        
        if datatable_found and ajax_indicators:
            print("\n⚠️  AJAX/DataTable Detected!")
            print("\nRecommended approach:")
            print("1. Use Selenium/Playwright to render JavaScript")
            print("2. Or find the AJAX endpoint and call it directly")
            print("3. Check Network tab in browser DevTools")
            print("\nPossible AJAX URLs to investigate:")
            for url in ajax_indicators[:3]:
                print(f"  - {url}")
        
        elif tables and len(tables) > 0:
            print("\n✅ Static HTML Table Found!")
            print("\nRecommended approach:")
            print("1. Parse the table using BeautifulSoup")
            print("2. Extract columns based on position")
            print(f"3. Table has {len(tables[0].find_all('tr'))} rows")
            
            if len(tables) > 0 and len(tables[0].find_all('tr')) > 1:
                print("\nSample parser code:")
                print("""
for row in table.find_all('tr')[1:]:  # Skip header
    cols = row.find_all('td')
    if len(cols) >= 3:
        date = cols[0].get_text(strip=True)
        stock_code = cols[1].get_text(strip=True)
        title = cols[2].get_text(strip=True)
        
        # Get PDF link
        link = row.find('a', href=True)
        pdf_url = link['href'] if link else None
                """)
        else:
            print("\n⚠️  No clear table structure found")
            print("Manual inspection of HTML file required")
        
        # 6. Summary and next steps
        print("\n" + "="*80)
        print("SUMMARY & NEXT STEPS")
        print("="*80)
        
        print(f"\n1. Review saved HTML file: {html_file}")
        print("2. Open in browser or text editor")
        print("3. Look for the disclosure table/data")
        print("4. Note the HTML structure (table, divs, etc.)")
        print("5. Update idx_disclosure_scraper.py accordingly")
        
        if datatable_found:
            print("\n⚠️  DataTable found - might need Selenium or API approach")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    inspect_idx_page()
