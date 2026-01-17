# SastoShare Scraper

This project is an automated Python scraper designed to extract Mutual Fund and Debenture data from [NepseAlpha](https://nepsealpha.com/). It runs daily via GitHub Actions and uploads the collected data to Supabase Storage (S3).

## Features

*   **Daily Automation**: Scrapes data automatically every day at 6:00 AM Nepal Time (UTC+5:45).
*   **Comprehensive Data**:
    *   **Mutual Funds**: NAV, Assets Allocation, Distributable Dividend, Stock Holdings, and Fund PE Ratio.
    *   **Detailed Holdings**: Detailed stock portfolio for *each* individual mutual fund (approx. 50+ funds).
    *   **Debentures**: Comprehensive list of debentures and their details.
*   **Stealth Scraping**: Uses Selenium (headless) with stealth configurations to bypass bot detection for dynamic content.
*   **Cloudflare Bypass**: Uses `cloudscraper` to handle protected API endpoints for detailed holdings.
*   **S3 Integration**: Automatically uploads all generated CSV files to a configured Supabase Storage bucket.
*   **Error Logging**: Generates a `scraping_errors.log` file if any specific fund fails to scrape.

## Project Structure

*   `main_scraper.py`: The master script. It orchestrates the entire process:
    1.  Sets up a Headless Chrome driver.
    2.  Scrapes the main Mutual Fund sections strings.
    3.  Scrapes the Debenture table.
    4.  Iterates through all funds to scrape their detailed stock holdings.
    5.  Uploads every file to Supabase S3 immediately after saving.
*   `scrape_debentures.py`: A standalone script to test/run *only* the debenture scraping part.
*   `requirements.txt`: Python dependencies.
*   `.github/workflows/daily_scrape.yml`: GitHub Actions configuration for the daily schedule.
*   `push_to_github.bat`: Helper script for one-click git pushes on Windows.

## Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/investmentmanagement137/sastoshare_new.git
    cd sastoshare_new
    ```

2.  **Install Dependencies**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables**
    The script requires the following environment variables for S3 upload. Create a `.env` file or set them in your system/GitHub Secrets:
    *   `SUPABASE_ACCESS_KEY_ID`
    *   `SUPABASE_SECRET_ACCESS_KEY`

## How It Works

### 1. Main Sections (`scrape_main_sections`)
*   Navigates to `https://nepsealpha.com/mutual-fund-navs`.
*   Uses Selenium to interact with the page tabs (NAV, Assets, Dividend, etc.).
*   Forces the "Show 100 entries" dropdown to ensure all data is visible.
*   Extracts the table data using BeautifulSoup.
*   Saves as `[SectionName]-[Date].csv`.

### 2. Debentures (`scrape_debentures`)
*   Navigates to `https://nepsealpha.com/debenture`.
*   Similar logic to main sections: loads table, expands entries, and extracts data.
*   Saves as `debenture-sastoshare-[Date].csv`.

### 3. Detailed Holdings (`scrape_detailed_holdings`)
*   Reads the list of funds from the previously scraped `Stock_Holdings_Fund_PE_Ratio` CSV.
*   Constructs the detail URL for each fund: `https://nepsealpha.com/mutual-fund-navs/{SYMBOL}?fsk=fs`.
*   Uses `cloudscraper` to bypass potential 403 Forbidden errors on these specific pages.
*   Saves each fund's portfolio as `assets-[Symbol]-[FundName]-[Date].csv`.

## Output Files

All files are saved as CSVs with the current date:
*   `NAV-DD-MM-YYYY.csv`
*   `Assets_Allocation-DD-MM-YYYY.csv`
*   `Distributable_Dividend-DD-MM-YYYY.csv`
*   `Stock_Holdings_Fund_PE_Ratio-DD-MM-YYYY.csv`
*   `debenture-sastoshare-DD-MM-YYYY.csv`
*   `assets-[Symbol]-[Fund Name]-DD-MM-YYYY.csv` (One per fund)

## Running Locally

To run the full scraper:
```powershell
python main_scraper.py
```

To run only the debenture scraper:
```powershell
python scrape_debentures.py
```

## GitHub Actions

The workflow is configured in `.github/workflows/daily_scrape.yml`.
*   **Trigger**: Push to `main`/`master` AND Schedule (`15 0 * * *` cron = 6:00 AM Nepal Time).
*   **Secrets**: Ensure `SUPABASE_ACCESS_KEY_ID` and `SUPABASE_SECRET_ACCESS_KEY` are added to your repository's "Actions Secrets".
