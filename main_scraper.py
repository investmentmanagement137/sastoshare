import os
import time
import csv
import json
import re
import cloudscraper
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import boto3
from botocore.client import Config

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def upload_to_supabase(file_path):
    access_key = os.environ.get("SUPABASE_ACCESS_KEY_ID")
    secret_key = os.environ.get("SUPABASE_SECRET_ACCESS_KEY")
    endpoint_url = "https://unbgkfatcaztstordiyt.storage.supabase.co/storage/v1/s3"
    region_name = "ap-southeast-1"
    bucket_name = "investment_management"
    
    if not access_key or not secret_key:
        print("Skipping S3 upload: Credentials not found in environment.")
        return

    try:
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(signature_version='s3v4')
        )
        
        file_name = os.path.basename(file_path)
        print(f"Uploading {file_name} to bucket '{bucket_name}'...")
        s3.upload_file(file_path, bucket_name, file_name)
        print("Upload successful.")
    except Exception as e:
        print(f"Failed to upload {file_path}: {e}")

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Helpful for CI environments
    driver_path = ChromeDriverManager().install()
    
    # Fix for issue where webdriver-manager returns 'THIRD_PARTY_NOTICES' on Linux
    if "THIRD_PARTY_NOTICES" in driver_path:
        driver_path = os.path.dirname(driver_path) # Go up to folder
        driver_path = os.path.join(driver_path, "chromedriver")
        
    # Ensure executable permissions
    if os.path.exists(driver_path) and not os.access(driver_path, os.X_OK):
        print(f"Adding execute permission to {driver_path}")
        os.chmod(driver_path, 0o755)
        
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_main_sections():
    driver = setup_driver()
    url = "https://nepsealpha.com/mutual-fund-navs"
    print(f"Navigating to {url}...")
    
    try:
        driver.get(url)
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "home")))
        
        # Sections configuration
        sections = [
            {"name": "NAV", "tab_href": "#home", "table_id": "DataTables_Table_0", "select_name": "DataTables_Table_0_length"},
            {"name": "Stock_Holdings_Fund_PE_Ratio", "tab_href": "#stkHolding", "table_id": "DataTables_Table_1", "select_name": "DataTables_Table_1_length"},
            {"name": "Assets_Allocation", "tab_href": "#assetsAllocation", "table_id": "DataTables_Table_2", "select_name": "DataTables_Table_2_length"},
            {"name": "Distributable_Dividend", "tab_href": "#distributableDividend", "table_id": "DataTables_Table_3", "select_name": "DataTables_Table_3_length"}
        ]
        
        today_str = datetime.now().strftime("%d-%m-%Y")
        stock_holdings_file = None
        
        for section in sections:
            print(f"Scraping {section['name']}...")
            try:
                # Click tab (js click is safer)
                tab = driver.find_element(By.CSS_SELECTOR, f"a[href='{section['tab_href']}']")
                driver.execute_script("arguments[0].click();", tab)
                time.sleep(2)
                
                # Show all entries
                select_el = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, section['select_name']))
                )
                Select(select_el).select_by_value('100')
                time.sleep(2) # Wait for redraw
                
                # Parse
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                table = soup.find('table', {'id': section['table_id']})
                
                if table:
                    # Clean up header text
                    headers = [th.text.strip() for th in table.find('thead').find_all('th')]
                    rows = []
                    tbody = table.find('tbody')
                    if tbody:
                        for tr in tbody.find_all('tr'):
                             # Use separator for multiline cells if needed, or just space
                            cells = [td.text.strip() for td in tr.find_all('td')]
                            if len(cells) == len(headers):
                                rows.append(cells)
                    
                    if rows:
                        filename = f"{section['name']}-{today_str}.csv"
                        with open(filename, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(headers)
                            writer.writerows(rows)
                        print(f"Saved {filename}")
                        upload_to_supabase(filename)
                        
                        if section['name'] == "Stock_Holdings_Fund_PE_Ratio":
                            stock_holdings_file = filename
                else:
                    print(f"Table not found for {section['name']}")
                    
            except Exception as e:
                print(f"Error scraping {section['name']}: {e}")
                
        return stock_holdings_file
        
    except Exception as e:
        print(f"Critical error in main loop: {e}")
        if 'driver' in locals():
            print(f"Current URL: {driver.current_url}")
            print(f"Page Title: {driver.title}")
            print("Page Source Snippet:")
            print(driver.page_source[:1000]) # First 1000 chars
    finally:
        if 'driver' in locals():
            driver.quit()

def scrape_detailed_holdings(stock_holdings_file):
    if not stock_holdings_file or not os.path.exists(stock_holdings_file):
        print("Stock Holdings file not found. Skipping detailed scraping.")
        return

    print("Reading symbols for detailed scraping...")
    funds = []
    with open(stock_holdings_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
             # Ensure we have Symbol and Name
            if 'Symbol' in row and 'Name' in row:
                funds.append({'Symbol': row['Symbol'], 'Name': row['Name']})
    
    print(f"Found {len(funds)} funds.")
    
    scraper = cloudscraper.create_scraper()
    today_str = datetime.now().strftime("%d-%m-%Y")
    failed_funds = []
    
    start_time = time.time()
    
    for idx, fund in enumerate(funds):
        # Check execution time (limit to 9 mins 30 sec to allow graceful exit)
        if time.time() - start_time > 570:
            print("\n[WARNING] Time limit approaching (9.5 mins). Stopping detailed scraping gracefully.")
            failed_funds.append("BATCH STOPPED: Time Limit Exceeded")
            break

        symbol = fund['Symbol']
        name = fund['Name']
        url = f"https://nepsealpha.com/mutual-fund-navs/{symbol}?fsk=fs"
        
        print(f"[{idx+1}/{len(funds)}] Process {symbol}...")
        try:
            resp = scraper.get(url, timeout=30) # Added request timeout
            if resp.status_code == 200:
                from io import StringIO
                dfs = pd.read_html(StringIO(resp.text))
                if dfs:
                    df = dfs[0]
                    safe_name = sanitize_filename(name)
                    filename = f"assets-{symbol}-{safe_name}-{today_str}.csv"
                    df.to_csv(filename, index=False)
                    print(f"Saved {filename}")
                    upload_to_supabase(filename)
            else:
                print(f"Failed {symbol}: {resp.status_code}")
                failed_funds.append(f"{symbol}: HTTP {resp.status_code}")
            time.sleep(0.5) 
        except Exception as e:
             # Just log simple error to avoid clutter
            print(f"Error {symbol}: {e}")
            failed_funds.append(f"{symbol}: Error - {e}")

    # Report failures
    print(f"\nScraping Summary: {len(funds) - len(failed_funds)} succeeded, {len(failed_funds)} failed.")
    if failed_funds:
        print("Writing failures to 'scraping_errors.log'...")
        with open('scraping_errors.log', 'w', encoding='utf-8') as f:
            for fail in failed_funds:
                f.write(fail + '\n')
            f.write(f"\nTotal Funds Attempted: {len(funds)}\n")
        print("Check 'scraping_errors.log' for details.")

def scrape_debentures():
    driver = setup_driver()
    url = "https://nepsealpha.com/debenture"
    print(f"Navigating to {url}...")
    
    try:
        driver.get(url)
        # Wait for table
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "DataTables_Table_0")))
        
        # Select 'Show 100 entries' to likely see all (or most)
        try:
            select_el = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "DataTables_Table_0_length"))
            )
            Select(select_el).select_by_value('100')
            time.sleep(2) # Wait for redraw
        except Exception as e:
            print(f"Could not select length: {e}")

        # Parse with BS4
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find('table', {'id': 'DataTables_Table_0'})
        
        if table:
            headers = [th.text.strip() for th in table.find('thead').find_all('th')]
            rows = []
            tbody = table.find('tbody')
            if tbody:
                for tr in tbody.find_all('tr'):
                    cells = [td.text.strip() for td in tr.find_all('td')]
                    # Basic validation
                    if len(cells) == len(headers):
                        rows.append(cells)
            
            if rows:
                today_str = datetime.now().strftime("%d-%m-%Y")
                filename = f"debenture-sastoshare-{today_str}.csv"
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(rows)
                print(f"Saved {filename}")
                upload_to_supabase(filename)
            else:
                print("No rows found for Debentures.")
        else:
            print("Debenture table not found.")
            
    except Exception as e:
        print(f"Error scraping debentures: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Starting Main Scraper...")
    stock_csv = scrape_main_sections()
    scrape_debentures()
    if stock_csv:
        scrape_detailed_holdings(stock_csv)
    print("All tasks completed.")
