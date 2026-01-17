import cloudscraper

def main():
    # URL pattern found by browser agent: https://nepsealpha.com/mutual-fund-navs/{SYMBOL}?fsk=fs
    # Example: C30MF
    url = "https://nepsealpha.com/mutual-fund-navs/C30MF?fsk=fs"
    
    print(f"Testing URL: {url}")
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response length:", len(response.text))
            if "table" in response.text:
                print("Success! Table found in response.")
                print(response.text[:500]) # Print first 500 chars to verify
            else:
                print("Response received but no table found. Content preview:")
                print(response.text[:200])
        else:
            print("Failed to access URL.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
