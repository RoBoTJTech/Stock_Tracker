from glob import glob
import os
import json
import feedparser
import _app_constants
import time
import _app_constants
from datetime import datetime, timedelta
import pandas as pd
import _app_constants

def calculate_trade_duration(start, end):
    # If start and end are on the same day
    if start.date() == end.date():
        duration = (min(end, end.replace(hour=_app_constants.MARKET_CLOSE.hour, minute=_app_constants.MARKET_CLOSE.minute)) - 
                    max(start, start.replace(hour=_app_constants.MARKET_OPEN.hour, minute=_app_constants.MARKET_OPEN.minute))).total_seconds()
        return max(duration, 0)
    
    # Calculate duration for the first day
    first_day_duration = (start.replace(hour=_app_constants.MARKET_CLOSE.hour, minute=_app_constants.MARKET_CLOSE.minute) - 
                          max(start, start.replace(hour=_app_constants.MARKET_OPEN.hour, minute=_app_constants.MARKET_OPEN.minute))).total_seconds()
    
    # Calculate duration for the last day
    last_day_duration = (min(end, end.replace(hour=_app_constants.MARKET_CLOSE.hour, minute=_app_constants.MARKET_CLOSE.minute)) - 
                         end.replace(hour=_app_constants.MARKET_OPEN.hour, minute=_app_constants.MARKET_OPEN.minute)).total_seconds()
    
    # Calculate full business days in between
    business_days = pd.bdate_range(start=start + timedelta(days=1), end=end - timedelta(days=1)).size
    
    # Calculate total duration
    total_duration = first_day_duration + last_day_duration + (business_days * (_app_constants.MARKET_CLOSE.hour - _app_constants.MARKET_OPEN.hour) * 3600)
    return max(total_duration, 0)

def calculate_trade_metrics(ticker):
    # Load JSON data
    file_path = os.path.join(_app_constants.DATA_PATH, f'{ticker}_Chart_1Mo_5Mi.json')
    # Check if the file exists
    if not os.path.exists(file_path):
        return {
            "shortest_trade_duration": 0,
            "average_trade_duration": 0,
            "longest_trade_duration": 0,
            "shortest_trade_interval": 0,
            "average_trade_interval": 0,
            "longest_trade_interval": 0
        }

    # Load JSON data
    with open(file_path, 'r') as file:
        data = json.load(file)

    trades = data.get(ticker, {}).get("trades", [])

    # Convert trade timestamps to pandas DataFrame
    trades_df = pd.DataFrame(trades)
    trades_df['buy_timestamp'] = pd.to_datetime(trades_df['buy_timestamp'])
    trades_df['sell_timestamp'] = pd.to_datetime(trades_df['sell_timestamp'])

    # Filter out trades without sell_timestamp
    trades_df = trades_df.dropna(subset=['sell_timestamp'])

    # Calculate trade durations in market hours
    trades_df['trade_duration'] = trades_df.apply(lambda row: calculate_trade_duration(row['buy_timestamp'], row['sell_timestamp']), axis=1)

    # Calculate intervals between trades
    trades_df = trades_df.sort_values(by='buy_timestamp')
    trades_df['previous_sell_timestamp'] = trades_df['sell_timestamp'].shift(1)
    trades_df = trades_df.dropna(subset=['previous_sell_timestamp'])
    trades_df['trade_interval'] = trades_df.apply(lambda row: calculate_trade_duration(row['previous_sell_timestamp'], row['buy_timestamp']), axis=1)

    # Calculate metrics
    if not trades_df.empty:
        shortest_trade_duration = trades_df['trade_duration'].min()
        average_trade_duration = trades_df['trade_duration'].mean()
        longest_trade_duration = trades_df['trade_duration'].max()

        shortest_trade_interval = trades_df['trade_interval'].min()
        average_trade_interval = trades_df['trade_interval'].mean()
        longest_trade_interval = trades_df['trade_interval'].max()
    else:
        shortest_trade_duration = average_trade_duration = longest_trade_duration = 0
        shortest_trade_interval = average_trade_interval = longest_trade_interval = 0

    return {
        "shortest_trade_duration": shortest_trade_duration,
        "average_trade_duration": average_trade_duration,
        "longest_trade_duration": longest_trade_duration,
        "shortest_trade_interval": shortest_trade_interval,
        "average_trade_interval": average_trade_interval,
        "longest_trade_interval": longest_trade_interval
    }

def fetch_news_from_rss(ticker):
    rss_url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
    feed = feedparser.parse(rss_url)
    
    news_items = []
    for entry in feed.entries:
        news_items.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary
        })
    
    return news_items

def ai_trade_status(ticker, default = True):
    details_file = os.path.join(_app_constants.DATA_PATH, f"{ticker}_Details.json")
    analysis_file = os.path.join(_app_constants.DATA_PATH, f"{ticker}_Analysis.json")

    # Check if details file exists
    if (not os.path.exists(details_file) and os.path.exists(analysis_file) and (datetime.now() - datetime.fromtimestamp(os.path.getmtime(analysis_file))).days > 30) or not os.path.exists(analysis_file):
        return default  # Proceed with trade since we lack information

    # Load the details file and get the latest earnings date
    with open(details_file, 'r') as f:
        details_data = json.load(f)

    earnings_dates = details_data[ticker]['totals'].get('calendarEvents', {}).get('earnings', {}).get('earningsDate', [])

    if not earnings_dates:
        latest_earnings_date = datetime.now() + timedelta(days=60)
    else:
        # Convert date strings to datetime objects and find the latest date
        earnings_dates = [datetime.strptime(date.split(' ')[0], '%Y-%m-%d') for date in earnings_dates]
        latest_earnings_date = max(earnings_dates)

    # Get the modification date of the analysis file
    analysis_mod_time = datetime.fromtimestamp(os.path.getmtime(analysis_file))
    if analysis_mod_time < latest_earnings_date - timedelta(days=90):
        return default  # Proceed with trade since the analysis file is outdated

    # Load the analysis file and check for the phrase 'Don't Trade'
    with open(analysis_file, 'r') as f:
        analysis_data = f.read()

    if "Don't Trade" in analysis_data:
        print(f"Don't trade {ticker}")
        return False  # Don't trade based on the analysis recommendation

    return True  # Proceed with trade if none of the above conditions are met

def load_api_key(file_path):
    try:
        with open(file_path, 'r') as file:
            # Read the file content and strip any leading/trailing whitespace
            api_key = file.read().strip()
            # Return the api key if it's not empty
            if api_key:
                return api_key
            else:
                raise ValueError("API key is empty")
    except (FileNotFoundError, ValueError) as e:
        # Handle the case where the file is not found or the API key is empty
        print(f"Error loading API key: {e}")
        # Return a fake key for demonstration purposes
        return "PUT_YOUR_OPENAI_KEY_IN_openai_key.txt"

def calculate_color(age_seconds,cache_duration):
    if age_seconds >= cache_duration or age_seconds < 0:
        return '#FF0000'  # Red
    green_value = int(255 * (1 - age_seconds / cache_duration))
    red_value = int(255 * (age_seconds / cache_duration))
    return f'#{red_value:02X}{green_value:02X}00'

def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def find_newest_file(pattern):
    files = glob(pattern)
    if not files:
        return None
    newest_file = max(files, key=os.path.getmtime)
    return newest_file

def load_history(history_file):
    if os.path.exists(history_file):
        with open(history_file, "r") as file:
            return json.load(file)
    return {}

def calculate_estimated_completion_time(trade_metrics, listed_date):
    # Convert listed_date from epoch to datetime
    listed_date = pd.to_datetime(listed_date, unit='s')
    
    # Get the longest trade duration in seconds
    longest_trade_duration = trade_metrics['longest_trade_duration']
    
    # Convert the longest trade duration from seconds to business hours and round up to the nearest hour
    total_business_hours = longest_trade_duration / 3600
    total_business_hours = int(total_business_hours) if total_business_hours.is_integer() else int(total_business_hours) + 1
    
    # Define custom business hours
    business_hours = pd.offsets.CustomBusinessHour(start=_app_constants.MARKET_OPEN.strftime('%H:%M'), 
                                                   end=_app_constants.MARKET_CLOSE.strftime('%H:%M'))
    
    # Calculate the estimated completion date by adding business hours to the listed date
    estimated_completion_date = listed_date + (business_hours * total_business_hours)
    
    # Calculate the remaining duration from now until the estimated completion date
    current_epoch_time = pd.Timestamp.now().timestamp()
    remaining_duration = estimated_completion_date.timestamp() - current_epoch_time
    
    # Convert the remaining duration to a timedelta object
    remaining_timedelta = timedelta(seconds=remaining_duration)
    
    # Format the timedelta to "X d Y hr Z min W sec"
    days, seconds = remaining_timedelta.days, remaining_timedelta.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    # Create the formatted string
    estimated_completion_time_str = f"{days} d {hours} hr {minutes} min {seconds} sec"

    return estimated_completion_time_str

def save_history(history,history_file):
    with open(history_file, "w") as file:
        json.dump(history, file)

def get_current_mark(symbol,lookup = True):
    global price_cache
    # Check if the price is cached and still valid
    if symbol in price_cache:
        cached_price, timestamp = price_cache[symbol]
        age_seconds = time.time() - timestamp
        if age_seconds < CACHE_DURATION or not lookup:
            return cached_price, age_seconds
    try:
        # Fetch the current price from Yahoo Finance
        stock = yf.Ticker(symbol)
        try:
            current_price = stock.history(period='1d',interval='1m',prepost=True)['Close'].iloc[-1]
        except:
            current_price = stock.history(period='1d',prepost=True)['Close'].iloc[-1]

        # Check if the new price is the same as the cached price
        if symbol in price_cache and price_cache[symbol][0] == current_price:
            cached_price, timestamp = price_cache[symbol]
            age_seconds = time.time() - timestamp
            price_cache[symbol] = (current_price, time.time() + CACHE_DURATION)
            return cached_price, CACHE_DURATION 

        # Cache the price if different
        price_cache[symbol] = (current_price, time.time())
        return current_price, 0

    except Exception as e:
        # If there is an error, return the cached price with the age
        if symbol in price_cache:
            cached_price, timestamp = price_cache[symbol]
            age_seconds = time.time() - timestamp
            return cached_price, age_seconds
        else:
            # If no cached price exists, raise the exception
            raise e