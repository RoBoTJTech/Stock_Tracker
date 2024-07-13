import csv
import os
import time
from collections import defaultdict
from glob import glob
from flask import Flask, render_template
import json
import yfinance as yf
from datetime import datetime, timedelta
import _app_functions

# Configuration
HISTORY_FILE = "history.json"  # File to store historical data
CACHE_DURATION = 300  # Cache duration in seconds (5 minutes)

app = Flask(__name__)
price_cache = {}

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

def parse_trade_data(file_path):
    start_time = int(time.time()) 
    history = _app_functions.load_history(HISTORY_FILE)
    new_history = {}
    unique_tickers = set()
 
    total_price = 0
    total_profit = 0

    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        
        # Skip the initial lines that are not part of the CSV header and data
        header_line = next(reader)
        header_line = ''.join(header_line)
        timestamp_str = header_line.split('on')[1].strip()
        file_timestamp = datetime.strptime(timestamp_str, "%m/%d/%y %H:%M:%S")

        if datetime.now() - file_timestamp > timedelta(minutes=5):
            # If the file is older than 5 minutes, use live prices
            use_live_prices = True
        else:
            use_live_prices = False

        for _ in range(1):
            next(reader)
        
        rows = list(reader)
        
        header = None
        for row in rows:
            if 'Time Placed' in row and 'Symbol' in row and 'Qty' in row and 'Side' in row and 'PRICE' in row and 'Mark' in row and 'Status' in row:
                header = row
                break

        if header is None:
            return "Could not find the header with 'Time Placed', 'Symbol', 'Qty', 'Side', 'PRICE', 'Mark', and 'Status'"

        header = [col.strip() for col in header]
        
        symbol_idx = header.index('Symbol')
        qty_idx = header.index('Qty')
        side_idx = header.index('Side')
        price_idx = header.index('PRICE')
        mark_idx = header.index('Mark')
        status_idx = header.index('Status')
        time_placed_idx = header.index('Time Placed')

        categorized_orders = {}
        working_orders = []
        all_categories = set()
        total_order_price = defaultdict(float)
        total_order_profit = defaultdict(float)

        i = rows.index(header) + 1
        while i < len(rows):
            row = rows[i]
            if len(row) <= max(symbol_idx, qty_idx, side_idx, price_idx, mark_idx, status_idx, time_placed_idx):
                i += 1
                continue

            symbol = row[symbol_idx].strip()
            side = row[side_idx].strip()
            quantity = row[qty_idx].strip().replace('$', '').replace('(', '').replace(')', '').replace(',', '')
            price = row[price_idx].strip()
            mark = row[mark_idx].strip().replace('$', '')
            status = row[status_idx].strip()
            time_placed = row[time_placed_idx].strip()

            if not quantity or not mark:
                i += 1
                continue

            try:
                quantity = float(quantity)
                mark = round(float(mark), 2)
            except ValueError:
                i += 1
                continue

            if use_live_prices:
                if int(time.time()) - 5 < start_time:
                    lookup = True 
                else:
                    lookup = False 
                mark, age_seconds = get_current_mark(symbol,lookup)
                cache_color = _app_functions.calculate_color(age_seconds,CACHE_DURATION)
            else:
                cache_color = '#00FF00'  # Green for fresh data within 5 minutes

            if status == 'WORKING' and side == 'SELL':
                if i + 1 < len(rows) and not _app_functions.is_float(price):
                    extra_row = rows[i + 1]
                    if extra_row[11] != '':
                        price = f"{extra_row[11]} {price}"
                    i += 1

                target_price_differential = round(float(price.split(' ')[0]) - mark if ' ' in price else float(price) - mark, 2)
                key = f"{symbol}-{quantity}-{time_placed}"
                last_differential = history.get(key, {}).get('differential', 0)
                color = 'lightgrey' if key not in history else ('green' if target_price_differential < last_differential else 'red' if target_price_differential > last_differential else history[key].get('color', 'lightgrey'))

                trg_value = float(price.split('+')[1].replace('%', '').replace('$', '')) if 'TRG+' in price else 0
                shares = abs(quantity)
                float_price = float(price.split(' ')[0])
                if '%' in price:
                    profit = float_price - (float_price / (1 + (trg_value / 100))) 
                else:
                    profit = trg_value
                total_price += float_price * shares
                order_profit = shares * profit
                total_profit += order_profit
                bid_price = round(float_price - profit, 2)
                order_cost = round(bid_price * shares, 2)
                working_orders.append([symbol, quantity, f"Share Cost: ${bid_price:.2f}<br>Target Price: ${price}<br>Order Cost: ${order_cost:.2f}<br>Order Profit: ${order_profit:.2f}", f"${mark:.2f}", f"${target_price_differential:.2f}", f"${last_differential:.2f}", color, cache_color])
                if key not in history or history[key].get('mark', mark) != mark:
                    new_history[key] = {'differential': target_price_differential, 'color': color, 'mark': mark}
                else:
                    new_history[key] = history[key]

            last_digit = None
            if side == 'BUY' and quantity >= 0:
                last_digit = int(str(quantity)[-1]) if str(quantity)[-1].isdigit() else None
            elif side == 'SELL' and quantity >= 0:
                last_digit = int(str(quantity)[-1]) if str(quantity)[-1].isdigit() else None
            if '$' not in row[qty_idx]:
                last_digit = None
            if last_digit is not None:
                all_categories.add(last_digit)
                if symbol not in categorized_orders:
                    categorized_orders[symbol] = {'BUY': defaultdict(lambda: {'count': 0, 'price': None}), 'SELL': defaultdict(lambda: {'count': 0, 'prices': set(), 'profit': None})}
                
                if side == 'BUY':
                    shares = int(quantity // mark)
                    total_cost = shares * mark
                    categorized_orders[symbol]['BUY'][last_digit]['count'] += 1
                    if not categorized_orders[symbol]['BUY'][last_digit]['price']:
                        categorized_orders[symbol]['BUY'][last_digit]['price'] = total_cost
                        total_order_price[last_digit] += total_cost
                elif side == 'SELL':
                    shares = int(quantity // mark)
                    if 'TRG+' in price:
                        trg_value = float(price.split('+')[1].replace('%', '').replace('$', ''))
                        if '%' in price:
                            profit = shares * mark * (trg_value / 100)
                        else:
                            profit = shares * trg_value
                        if not categorized_orders[symbol]['SELL'][last_digit]['profit']:
                            categorized_orders[symbol]['SELL'][last_digit]['profit'] = profit
                            total_order_profit[last_digit] += profit

                    categorized_orders[symbol]['SELL'][last_digit]['count'] += 1
                    categorized_orders[symbol]['SELL'][last_digit]['prices'].add(price)

            i += 1

    _app_functions.save_history(new_history,HISTORY_FILE)
    working_orders.sort(key=lambda x: float(x[4].replace('$','')))

    sorted_categories = sorted(all_categories)
    headers = ["Type", "Symbol"] + [f"Cat {cat}" for cat in sorted_categories]

    Report = []
    for symbol, orders in categorized_orders.items():
        buy_orders_waiting = orders['BUY'].get(sorted_categories[0], {}).get('count', 0)
        index_code = f"{buy_orders_waiting:03d}-{symbol}-0"
 
        buy_row = ["BUY", f'<span class="indicator" style="background-color: {cache_color};"></span> ' + symbol] + [f"Orders Waiting: {orders['BUY'][cat]['count']}<br>Order Price: ${orders['BUY'][cat]['price']:.2f}" if cat in orders['BUY'] else '' for cat in sorted_categories] + [index_code]
        sell_row = ["SELL", f'<span class="indicator" style="background-color: {cache_color};"></span> ' + symbol] + [
            f"Orders Waiting: {orders['SELL'][cat]['count']}<br>Sell Price: {'='.join(orders['SELL'][cat]['prices'])}<br>Order Profit: ${orders['SELL'][cat]['profit']:.2f}" if cat in orders['SELL'] else '' 
            for cat in sorted_categories] + [index_code.replace('-0', '-1')]

        Report.append(buy_row)
        Report.append(sell_row)
        unique_tickers.add(symbol)
    total_percentage_gained = {cat: (total_order_profit[cat] / total_order_price[cat]) * 100 if total_order_price[cat] != 0 else 0 for cat in sorted_categories}

    total_rows = [["Totals", ""] + [f"Total Order Price: ${total_order_price[cat]:.2f}<br>Total Order Profit: ${total_order_profit[cat]:.2f}<br>Total % Gain: {total_percentage_gained[cat]:.2f}%" for cat in sorted_categories]]

    # Sort the Report based on the index code (the last element)
    Report.sort(key=lambda row: row[-1])

    # Remove the index code (last element) from each row before rendering
    for row in Report:
        row.pop()

    Report += total_rows
    percentage_gained = (total_profit / total_price) * 100 if total_price != 0 else 0
    working_orders.append(["", "", f"Total Sell Price: ${total_price:.2f}<br>Total Profit: ${total_profit:.2f}<br>Total % Gain: {percentage_gained:.2f}%", "", "", "", ""]) 

    with open("unique_tickers.json", "w") as ticker_file:
        json.dump(list(unique_tickers), ticker_file)

    return headers, Report, working_orders

@app.route('/')
def index():
    csv_file_path = _app_functions.find_newest_file("*TradeActivity.csv*")
    if not csv_file_path:
        return "No CSV files found matching the pattern."

    headers, Report, working_orders = parse_trade_data(csv_file_path)
    filename = os.path.basename(csv_file_path)

    # Load hot_picks.json
    with open("hot_picks.json", "r") as file:
        hot_picks = json.load(file)

    # Load the details for each symbol in hot_picks
    def load_symbol_details(symbol):
        details = {}
        try:
            with open(f'stock_data/{symbol}_Chart_1Mo_5Mi.json', 'r') as f:
                details['1Mo_5Mi'] = json.load(f)[symbol]["totals"]
            with open(f'stock_data/{symbol}_Overall_Trend.json', 'r') as f:
                details['Overall_Trend'] = json.load(f)[symbol]["totals"]
        except FileNotFoundError:
            details['1Mo_5Mi'] = {}
            details['Overall_Trend'] = {}
        return details

    buy_details = {symbol: load_symbol_details(symbol) for symbol in hot_picks['buy_symbols']}
    sell_details = {symbol: load_symbol_details(symbol) for symbol in hot_picks['sell_symbols']}
    hold_details = {symbol: load_symbol_details(symbol) for symbol in hot_picks['hold_symbols']}

    return render_template('Report.html', headers=headers, Report=Report, working_orders=working_orders, filename=filename, hot_picks=hot_picks, buy_details=buy_details, sell_details=sell_details, hold_details=hold_details)


if __name__ == '__main__':
    app.run(debug=True, port=5000)  

