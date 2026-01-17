import os
import csv
import time
import cloudscraper
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import re

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def main():
    # 1. Read symbols from the Stock Holdings CSV
    # The file is expected to be in the current directory
    # Find the latest Stock_Holdings file
    files = [f for f in os.listdir('.') if f.startswith('Stock_Holdings_Fund_PE_Ratio-') and f.endswith('.csv')]
    if not files:
        print("No Stock Holdings CSV found. Please run the previous scraping step first.")
        return
    
    # Sort to get the latest one
    latest_file = sorted(files)[-1]
    print(f"Reading symbols from {latest_file}...")
    
    funds = []
    with open(latest_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            funds.append({
                'Symbol': row['Symbol'],
                'Name': row['Name']
            })
    
    print(f"Found {len(funds)} funds to scrape.")
    
    # 2. Setup Cloudscraper
    scraper = cloudscraper.create_scraper()
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    # 3. Iterate and Scrape
    success_count = 0
    fail_count = 0
    
    for idx, fund in enumerate(funds):
        symbol = fund['Symbol']
        name = fund['Name']
        
        # Construct URL
        # URL Logic: https://nepsealpha.com/mutual-fund-navs/{SYMBOL}?fsk=fs
        url = f"https://nepsealpha.com/mutual-fund-navs/{symbol}?fsk=fs"
        
        print(f"[{idx+1}/{len(funds)}] Scraping {symbol} - {name}...")
        
        try:
            response = scraper.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table')
                
                if table:
                    # Parse table using pandas
                    # The response is just an HTML fragment often, or a full page
                    dfs = pd.read_html(str(table))
                    
                    if dfs:
                        df = dfs[0]
                        # Clean filename: symbol name date .csv
                        # e.g. NMB50 NMB 50 12-01-2026.csv
                        # User request: symbol name date .csv
                        safe_name = sanitize_filename(name)
                        filename = f"{symbol}-{safe_name}-{today_str}.csv"
                        
                        df.to_csv(filename, index=False)
                        print(f"  -> Saved {filename} ({len(df)} rows)")
                        success_count += 1
                    else:
                        print("  -> Top table found but pandas could not parse it.")
                        fail_count += 1
                else:
                    print("  -> No table found in response.")
                    fail_count += 1
            else:
                print(f"  -> Failed with status {response.status_code}")
                fail_count += 1
                
        except Exception as e:
            print(f"  -> Error: {e}")
            fail_count += 1
            
        # Be polite to the server
        time.sleep(1) 
        
    print("-" * 30)
    print(f"Completed. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
