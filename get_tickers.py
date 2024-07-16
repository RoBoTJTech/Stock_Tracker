from requests_html import HTMLSession
import random
import subprocess
import json
import os
import time
from yahoo_fin import stock_info as si
import requests
from bs4 import BeautifulSoup

# Fetch top gainers
try:
    top_gainers = si.get_day_gainers()
    top_gainers_tickers = top_gainers['Symbol'].tolist()
    print(f"Found {len(top_gainers_tickers)} tickers in Yahoo top gainers.")
except:
    print("Failed to get Yahoo top gainers.")

# Fetch most active stocks
try:
    most_active = si.get_day_most_active()
    most_active_tickers = most_active['Symbol'].tolist()
    print(f"Found {len(most_active_tickers)} tickers in most Yahoo active stocks.")
except:
    print("Failed to get Yahoo most active.")

try:
    url = "https://api.stocktwits.com/api/2/trending/symbols.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    data = response.json()
    trending_tickers = [symbol['symbol'] for symbol in data['symbols']]
    print(f"Found {len(trending_tickers)} tickers in Stocktwits trending stocks.")
except Exception as e:
    print(f"Failed to get Stocktwits trending tickers: {e}")

# Load unique tickers from the unique_tickers.json file
with open('unique_tickers.json', 'r') as file:
    unique_tickers = json.load(file)
print(f"Found {len(unique_tickers)} tickers in unique_tickers.json.")

# Load hot pick tickers from the hot_picks.json file
with open('hot_picks.json', 'r') as file:
    hot_picks = json.load(file)
# Initialize an empty list to hold all tickers
hot_pick_tickers = []

# Iterate over all keys in the JSON data
for key in hot_picks:
    # Extend the all_tickers list with the values from each key
    hot_pick_tickers.extend(hot_picks[key])

print(f"Found {len(hot_pick_tickers)} tickers in hot_picks.json.")


# Scrape tickers from ETF Database
def scrape_tickers_from_page(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to load page {url}")

    soup = BeautifulSoup(response.content, 'html.parser')
    tickers = []

    # Find the table containing the ETF data
    table = soup.find('table', {'id': 'etfs'})

    # Ensure the table is found
    if not table:
        raise Exception("Could not find the ETF table on the page")

    # Find all rows in the table body
    rows = table.find('tbody').find_all('tr')

    for row in rows:
        # Find the ticker symbol in the first column
        symbol_cell = row.find('td', {'data-th': 'Symbol'})
        if symbol_cell:
            ticker = symbol_cell.get_text(strip=True)
            tickers.append(ticker)

    return tickers

def scrape_all_tickers(base_url, pages=5):
    all_tickers = []

    for page in range(1, pages + 1):
        url = f"{base_url}&page={page}"
        print(f"Scraping page {page}")
        tickers = scrape_tickers_from_page(url)
        all_tickers.extend(tickers)

    return all_tickers

# Base URL for the leveraged equity ETFs (without the page parameter)
base_url = 'https://etfdb.com/etfs/leveraged/equity/#etfs&sort_name=ytd_percent_return&sort_order=desc'
scraped_tickers = scrape_all_tickers(base_url)
print(f"Found {len(scraped_tickers)} tickers in leveraged equity ETFs.")

# Directory where the stock data JSON files are stored
stock_data_dir = './stock_data'

# Get tickers from files named *_Overall_Trend.json that are over 1 hour old
old_tickers = []
for filename in os.listdir(stock_data_dir):
    if filename.endswith("_Overall_Trend.json"):
        filepath = os.path.join(stock_data_dir, filename)
        file_age = time.time() - os.path.getmtime(filepath)
        if file_age >= 3600:
            ticker = filename.split('_')[0]
            old_tickers.append(ticker)
print(f"Found {len(old_tickers)} tickers from old Overall_Trend.json files.")

# Combine and deduplicate the tickers
all_tickers = list(set(hot_pick_tickers + top_gainers_tickers + most_active_tickers + trending_tickers + unique_tickers + scraped_tickers + old_tickers))
filtered_tickers = [ticker for ticker in all_tickers if ticker.isalpha()]

print(f"Total unique tickers found: {len(filtered_tickers)}")

# Path to your get_stock_data.py script
script_path = './get_stock_data.py'

# Loop through each ticker and call get_stock_data.py
random.shuffle(filtered_tickers)
for ticker in filtered_tickers:
    json_file_path = os.path.join(stock_data_dir, f"{ticker}_Overall_Trend.json")

    # Check if the file exists and is newer than 1 Hr 
    if os.path.exists(json_file_path):
        file_age = time.time() - os.path.getmtime(json_file_path)
        if file_age < 3600:
            print(f"Skipping {ticker}, file is newer than 1 hour.")
            continue

    # Call the get_stock_data.py script
    subprocess.run(['python3', script_path, ticker])

subprocess.run(['python3', './hot_picks.py', ''])
