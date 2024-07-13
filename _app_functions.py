from glob import glob
import os
import json

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