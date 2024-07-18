import csv
import os
import time
from collections import defaultdict
from flask import Flask, render_template, jsonify, request
import yfinance as yf
import json
from datetime import datetime, timedelta
import _app_functions
from openai import OpenAI
from yahooquery import Ticker
import subprocess


VERSION = "1.0.2"

# Configuration
HISTORY_FILE = "history.json"  # File to store historical data
HOT_PICKS_FILE = "hot_picks.json"
CACHE_DURATION = 300  # Cache duration in seconds (5 minutes)

app = Flask(__name__)
price_cache = {}

client = OpenAI(api_key=_app_functions.load_api_key('openai_key.txt'))

def fetch_stock_data(ticker):
    stock = Ticker(ticker)
    data = {
        "current_price": stock.history(period="1d")["close"].iloc[-1],
        "financials": stock.financial_data,
        "earnings": stock.earnings,
        "recommendations": stock.recommendations,
        "analyst_ratings": stock.recommendation_trend,
        "news": _app_functions.fetch_news_from_rss(ticker),
        "cashflow": stock.cash_flow,
        "balance_sheet": stock.balance_sheet,
        "income_statement": stock.income_statement,
        "summary_detail": stock.summary_detail,
        "summary_profile": stock.summary_profile,
        "moving_averages": {
            "20_day": stock.history(period="20d")["close"].mean() if not stock.history(period="20d").empty else None,
            "50_day": stock.history(period="50d")["close"].mean() if not stock.history(period="50d").empty else None,
            "100_day": stock.history(period="100d")["close"].mean() if not stock.history(period="100d").empty else None,
            "200_day": stock.history(period="200d")["close"].mean() if not stock.history(period="200d").empty else None
        }
    }
    return data

def review_and_analyze_stock(ticker, risk_tolerance, stock_data):

    prompt = (
        f"Based on current data downloaded using yahooquery, please provide a comprehensive report for stock ticker: {ticker} "
        f"including details on current performance, financials, valuation ratios, analyst ratings, and summarize all news clearly related to {ticker}. "
        f"Include the company's profile information to explain what the company does and automatically consider the industry context in your analysis. "
        f"Include technical indicators (using the data provided, provide any indicators you can), "
        f"explain what the specific numbers in the indicators mean to each other based on the real data, "
        f"risk factors, and swing trading potential. Additionally, include a risk assessment "
        f"based on a risk tolerance of {risk_tolerance}, with a final Trade Status value at the "
        f"very bottom of the report formatted as trade_status: with the values of Trade or Don't Trade. DO NOT INCLUDE THE WORDING: Don't Trade, anywhere else "
        f"it should only be used when applicable with the trade_status: value. I look for the phrase Don't Trade, as a trigger.\n\n"
        f"Ensure that all relevant data points are considered equally and consistently in determining the final Trade Status. "
        f"Use the following guidelines to weigh and assess each category based on industry norms and risk tolerance:\n"
        f"1. **Technical Indicators**: Compare the current price against moving averages (20-day, 50-day, 100-day, 200-day). Generally, consider 'Trade' if the current price is above the 50-day and 200-day moving averages, indicating a positive trend. Adjust for risk tolerance: for lower risk tolerance, give more weight to longer-term averages (100-day and 200-day); for higher risk tolerance, give more weight to shorter-term averages (20-day and 50-day).\n"
        f"2. **Analyst Ratings**: Use the average analyst rating to gauge market sentiment. A rating below 2.0 suggests a strong buy, favoring 'Trade'; a rating above 3.0 suggests a hold or sell, favoring 'Don't Trade'. Adjust for risk tolerance: for lower risk tolerance, be more conservative and consider avoiding stocks with ratings above 2.5; for higher risk tolerance, be more aggressive and consider ratings up to 3.0.\n"
        f"3. **Financial Performance**: Evaluate year-over-year earnings growth, revenue growth, profit margin, and cash flow. Positive growth and strong cash flow generally favor 'Trade', while negative trends favor 'Don't Trade'. Adjust for risk tolerance: for lower risk tolerance, prioritize strong profit margins and stable earnings; for higher risk tolerance, be more flexible with earnings and revenue fluctuations.\n"
        f"4. **Valuation Ratios**: Assess P/E ratio, forward P/E, and price to sales ratio. Reasonable valuations based on industry norms favor 'Trade'. Extremely high or low valuations might favor 'Don't Trade'. Adjust for risk tolerance: for lower risk tolerance, prefer stocks with moderate valuations; for higher risk tolerance, be more open to stocks with extreme valuations.\n"
        f"5. **Risk and Volatility**: Use beta and other risk metrics to assess volatility. A beta close to 1 indicates average market risk; significantly higher beta suggests higher volatility, impacting the risk assessment based on {risk_tolerance}. Adjust for risk tolerance: for lower risk tolerance, avoid stocks with beta significantly above 1; for higher risk tolerance, be more accepting of high beta values.\n"
        f"6. **Industry Context**: Consider the industry norms and company profile information, such as the sector, industry, and business model. Ensure that the company’s performance and risks are evaluated in the context of its industry. Adjust for risk tolerance: for lower risk tolerance, prefer companies with stable industry performance; for higher risk tolerance, be more open to companies in more volatile or emerging industries.\n\n"
        f"Here is the provided data:\n{json.dumps(stock_data, indent=2, default=str)}"
    )

    response = client.chat.completions.create(model="gpt-4-turbo",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=4096,  # Adjusted to allow for a larger response if needed
    temperature=0.7)
    return response.choices[0].message.content.strip()

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
            # Get the bid price from the stock's info
            current_price = stock.info['bid']
        except:
            try:
                current_price = stock.history(period='1d',interval='1m',prepost=True)['low'].iloc[-1]
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
                trade_metrics = _app_functions.calculate_trade_metrics(symbol)
                target_price_differential = round(float(price.split(' ')[0]) - mark if ' ' in price else float(price) - mark, 2)
                key = f"{symbol}-{quantity}-{time_placed}"
                last_differential = history.get(key, {}).get('differential', 0)
                listed_date = int(history.get(key, {}).get('listed', time.time()))
                completion_time = _app_functions.calculate_estimated_completion_time(trade_metrics,listed_date)
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
                working_orders.append([symbol, quantity, f"Share Cost: ${bid_price:.2f}<br>Target Price: ${price}<br>Order Cost: ${order_cost:.2f}<br>Order Profit: ${order_profit:.2f}<br>ETC: {completion_time}", f"${mark:.2f}", f"${target_price_differential:.2f}", f"${last_differential:.2f}", color, cache_color])
                if key not in history or history[key].get('mark', mark) != mark:
                    new_history[key] = {'differential': target_price_differential, 'color': color, 'mark': mark, 'listed': listed_date}
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
@app.route('/stock_data/<path:filename>')
def stock_data(filename):
    file_path = os.path.join('stock_data', f'{filename}.json')
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    with open(file_path, 'r') as file:
        data = json.load(file)
    
    return jsonify(data)

@app.route('/analyze_stock', methods=['GET'])
def analyze_stock():
    ticker = request.args.get('ticker')
    risk_tolerance = request.args.get('risk_tolerance', default=5, type=int)

    if not ticker:
        return jsonify({"error": "Ticker parameter is required"}), 400

    cache_file_path = f'./stock_data/{ticker}_Analysis.json'
    current_trade_status = True
    # Check if the cache file exists and is newer than 6 hours
    if os.path.exists(cache_file_path):
        # Read the cached file and return its content with a timestamp
        with open(cache_file_path, 'r') as cache_file:
            cached_response = cache_file.read()
        if "Don't Trade" in cached_response:
            current_trade_status = False
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file_path))
        if datetime.now() - file_mod_time < timedelta(hours=24):
            timestamp = file_mod_time.strftime('%Y-%m-%d %H:%M:%S')
            return jsonify({"analysis": cached_response, "timestamp": timestamp})

    try:
        stock_data = fetch_stock_data(ticker)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        analysis = review_and_analyze_stock(ticker, risk_tolerance, stock_data)
        
        # Write the analysis to the cache file
        os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)
        with open(cache_file_path, 'w') as cache_file:
            cache_file.write(analysis)
        
        if ("Don't Trade" in analysis and current_trade_status) or \
            ("Don't Trade" not in analysis and not current_trade_status):
            subprocess.run(["python3", "hot_picks.py"])

        return jsonify({"analysis": analysis, "timestamp": current_time})
    except Exception as e:
        return jsonify({"analysis": str(e), "timestamp": current_time}), 500


@app.route('/')
def index():
    csv_file_path = _app_functions.find_newest_file("*TradeActivity.csv*")
    if not csv_file_path:
        return "No CSV files found matching the pattern."

    # Compare the timestamps and run the script if csv_file_path is newer
    if os.path.getmtime(csv_file_path) > os.path.getmtime(HOT_PICKS_FILE):
        subprocess.run(["python3", "hot_picks.py"])

    headers, Report, working_orders = parse_trade_data(csv_file_path)
    filename = os.path.basename(csv_file_path)

    # Load hot_picks.json
    with open("hot_picks.json", "r") as file:
        hot_picks = json.load(file)
    #Load rank.json
    with open("ranks.json", "r") as file:
        ranks = json.load(file)

    # Load the details for each symbol in hot_picks
    def load_symbol_details(symbol, ranks):
        details = {}
        try:
            with open(f'stock_data/{symbol}_Chart_1Mo_5Mi.json', 'r') as f:
                details['1Mo_5Mi'] = json.load(f)[symbol]["totals"]
            with open(f'stock_data/{symbol}_Overall_Trend.json', 'r') as f:
                details['Overall_Trend'] = json.load(f)[symbol]["totals"]
            if symbol in ranks:
                details['Rank'] = ranks[symbol]["totals"]
            else:
                details['Rank'] = {}
            trade_status = _app_functions.ai_trade_status(symbol, None)
            if trade_status is True:
                details['trade_status'] = {"status": "&#128077;"}
            elif trade_status is False:
                details['trade_status'] = {"status": "&#128078;"}
            else:
                details['trade_status'] = {}
        except FileNotFoundError:
            details['1Mo_5Mi'] = {}
            details['Overall_Trend'] = {}
            details['Rank'] = {}
            details['trade_status'] = {}
        return details
    
    buy_details = {symbol: load_symbol_details(symbol, ranks) for symbol in hot_picks['buy_symbols']}
    sell_details = {symbol: load_symbol_details(symbol, ranks) for symbol in hot_picks['sell_symbols']}
    hold_details = {symbol: load_symbol_details(symbol, ranks) for symbol in hot_picks['hold_symbols']}

    return render_template('Report.html', headers=headers, Report=Report, working_orders=working_orders, filename=filename, hot_picks=hot_picks, buy_details=buy_details, sell_details=sell_details, hold_details=hold_details, version=VERSION)


if __name__ == '__main__':
    app.run(debug=True, port=5000)  

