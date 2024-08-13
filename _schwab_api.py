import requests
import time
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz

def get_bearer_key(file_path='schwab_key.txt'):
    with open(file_path, 'r') as file:
        return file.read().strip()

def get_schwab_data_chunk(ticker, bearer_key, end_date):
    url = f'https://api.schwabapi.com/marketdata/v1/pricehistory'
    params = {
        'symbol': ticker,
        'periodType': 'day',
        'period': 10,  # Request 10 days of data
        'frequencyType': 'minute',
        'frequency': 5,
        'endDate': end_date,
        'needExtendedHoursData': 'true'
    }
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {bearer_key}'
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def collect_30_days_of_data(ticker, bearer_key):
    all_candles = []
    current_end_date = int(time.time() * 1000)  # Current time in milliseconds

    while len(all_candles) < 30 * 24 * 60 // 5:  # Approximate number of 5-minute intervals in 30 days
        data_chunk = get_schwab_data_chunk(ticker, bearer_key, current_end_date)
        candles = data_chunk.get('candles', [])
        
        if not candles:
            break  # Exit if no more data is returned
        
        all_candles.extend(candles)
        
        # Update the end date for the next request to be the oldest datetime in the returned data
        current_end_date = candles[0]['datetime'] - 1  # Move end_date back slightly to ensure no overlap

    # Ensure all candles are sorted by datetime
    all_candles = sorted(all_candles, key=lambda x: x['datetime'])

    # Keep only the last 30 days of data
    thirty_days_ago = datetime.now() - timedelta(days=30)
    thirty_days_ago_timestamp = int(thirty_days_ago.timestamp() * 1000)

    filtered_candles = [candle for candle in all_candles if candle['datetime'] >= thirty_days_ago_timestamp]
    
    return filtered_candles

def candles_to_dataframe(candles):
    eastern = pytz.timezone('US/Eastern')
    data = {
        'Datetime': [datetime.fromtimestamp(candle['datetime'] / 1000, tz=eastern) for candle in candles],
        'Open': [candle['open'] for candle in candles],
        'High': [candle['high'] for candle in candles],
        'Low': [candle['low'] for candle in candles],
        'Close': [candle['close'] for candle in candles],
        'Volume': [candle['volume'] for candle in candles]
    }
    df = pd.DataFrame(data)
    df.set_index('Datetime', inplace=True)
    return df
