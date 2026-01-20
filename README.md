# SastoShare - Nepal Mutual Fund & Debenture Scraper

Automated scraper for Nepal's mutual fund and debenture data from [NepseAlpha](https://nepsealpha.com/). Runs daily via GitHub Actions and uploads data to Supabase S3 Storage.

## 🎯 Features

| Feature | Description |
|---------|-------------|
| **Daily Automation** | Scrapes at 6:00 PM NPT every day |
| **Detailed Holdings** | Scrapes 52+ individual fund portfolios every 2 days |
| **Cloudflare Bypass** | Uses Playwright with auto-challenge solving |
| **S3 Upload** | Automatically uploads all CSVs to Supabase Storage |
| **Rate Limit Handling** | Smart cooldowns and retry logic |

## 📊 Data Collected

### Daily Scrape (`--task daily`)
| File | Description |
|------|-------------|
| `NAV-DD-MM-YYYY.csv` | Net Asset Value for all mutual funds |
| `MF_Assets_Allocation-DD-MM-YYYY.csv` | Fund asset distribution (stocks, bonds, cash) |
| `Distributable_Dividend-DD-MM-YYYY.csv` | Expected dividend capacity |
| `Stock_Holdings_Fund_PE_Ratio-DD-MM-YYYY.csv` | Fund PE ratios and stock holding % |
| `debenture-sastoshare-DD-MM-YYYY.csv` | All debentures with yields and maturity |

### Detailed Scrape (`--task detailed`)
| File | Description |
|------|-------------|
| `assets-[SYMBOL]-[Fund Name]-DD-MM-YYYY.csv` | Individual stock portfolio for each fund (52+ files) |

## 🚀 Quick Start

### Local Setup
```bash
# Clone
git clone https://github.com/investmentmanagement137/sastoshare.git
cd sastoshare

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run
python main_scraper.py --task daily      # Quick daily data
python main_scraper.py --task detailed   # Full detailed holdings
python main_scraper.py --task all        # Everything
```

### Environment Variables
For S3 upload, set these (or add to GitHub Secrets):
```
SUPABASE_ACCESS_KEY_ID=your_key
SUPABASE_SECRET_ACCESS_KEY=your_secret
```

## ⏰ GitHub Actions Schedule

| Workflow | Schedule | Task |
|----------|----------|------|
| `daily_scrape.yml` | 6:00 PM NPT daily | `--task daily` |
| `detailed_scrape.yml` | 6:00 PM NPT every 2 days | `--task detailed` |

## 🛡️ Anti-Bot Protection

NepseAlpha uses Cloudflare protection. This scraper handles it with:

1. **Playwright Browser** - Real browser instead of HTTP requests
2. **Cloudflare Challenge Auto-Solve** - Waits up to 15s for challenge to complete
3. **Rate Limiting** - 8-15s delays between requests
4. **Consecutive Failure Cooldown** - 60s pause after 3+ failures
5. **Retry Queue** - Failed symbols retry later (up to 3 attempts)

## 📁 Project Structure

```
sastoshare/
├── main_scraper.py          # Main scraper script
├── requirements.txt         # Python dependencies
├── .github/workflows/
│   ├── daily_scrape.yml     # Daily automation
│   └── detailed_scrape.yml  # Detailed holdings automation
└── nepsealpha-skill/        # Selector documentation
    ├── SKILL.md
    └── selectors.json
```

## 🔧 How It Works

### 1. Main Sections (Playwright)
- Opens headless Chromium browser
- Navigates to each tab (NAV, Assets, Dividend, Holdings)
- Selects "Show 100 entries" to load all data
- Parses tables with BeautifulSoup
- Uploads CSV immediately after saving

### 2. Detailed Fund Holdings (Playwright)
- Reads fund list from `Stock_Holdings_Fund_PE_Ratio` CSV
- Visits each fund's detail page: `/mutual-fund-navs/{SYMBOL}?fsk=fs`
- Handles Cloudflare challenges automatically
- Parses portfolio table with pandas
- Rate-limited with smart cooldowns

### 3. S3 Upload
- Sanitizes filenames (replaces special chars with `-`)
- Uploads to Supabase S3-compatible storage
- Uses boto3 with S3v4 signature

## 📝 Error Handling

- **`scraping_errors.log`** - Lists failed funds and reasons
- **25-minute timeout** - Graceful stop before GitHub Actions limit
- **Retry logic** - Failed items retry up to 3 times

## 📜 License

MIT
