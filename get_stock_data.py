#!/usr/bin/python3
import os
from yahooquery import Ticker
import yfinance as yf
import pandas as pd
import numpy as np
import argparse
import json
from datetime import time, datetime, timedelta
import pytz

def get_serializable_attributes(ticker):
    serializable_attrs = {}
    try:
        for attr in dir(ticker):
            if not attr.startswith('_'):
                try:
                    value = getattr(ticker, attr)
                    # Attempt to serialize the value to JSON
                    json.dumps(value)
                    serializable_attrs[attr] = value
                except (TypeError, ValueError):
                    pass  # Skip non-serializable attributes
    except:
        pass
    return serializable_attrs

def get_stock_details(ticker_symbol):
    ticker = Ticker(ticker_symbol)
    serializable_attrs = get_serializable_attributes(ticker)
    return serializable_attrs["all_modules"][ticker_symbol]

# Fetch data including pre-market and after-hours
def fetch_yahoo_chart(yf_ticker_obj, period, interval):
    data = yf_ticker_obj.history(period=period, interval=interval, prepost=True)
    return data

def estimate_inflows_outflows(yf_ticker_obj):
    data = fetch_yahoo_chart(yf_ticker_obj, '1mo', '1d')

    if 'Close' in data.columns and 'Volume' in data.columns:
        data['price_change'] = data['Close'].diff()
        data['inflows'] = data.apply(lambda row: row['Volume'] * row['price_change'] if row['price_change'] > 0 else 0, axis=1)
        data['outflows'] = data.apply(lambda row: -row['Volume'] * row['price_change'] if row['price_change'] < 0 else 0, axis=1)

        total_inflows = round(data['inflows'].sum(), 2)
        total_outflows = round(data['outflows'].sum(), 2)
        net_inflows_outflows = round(total_inflows - total_outflows, 2)
        return total_inflows, total_outflows, net_inflows_outflows
    else:
        return 0, 0, 0

def make_recommendation(yf_ticker_obj):
    total_inflows, total_outflows, net_inflows_outflows = estimate_inflows_outflows(yf_ticker_obj)
    try:
        # Fetch additional data for trend analysis
        data = fetch_yahoo_chart(yf_ticker_obj, '1y', '1d')
        data['MA50'] = data['Close'].rolling(window=50).mean()
        data['MA200'] = data['Close'].rolling(window=200).mean()
        MA_Trend = data['MA50'].iloc[-1] - data['MA200'].iloc[-1]
    except:
        MA_Trend = 0

    # Numerical recommendationMean mapping
    if MA_Trend > 0 :
        if net_inflows_outflows > 0:
            recommendation_mean = 1
        else:
            recommendation_mean = 2
    elif MA_Trend <= 0:
        if net_inflows_outflows > 0:
            recommendation_mean = 4
        else:
            recommendation_mean = 5
    else:
        recommendation_mean = 3

    return total_inflows, total_outflows, net_inflows_outflows, recommendation_mean, MA_Trend

# Heikin Ashi Calculations
def calculate_heikin_ashi(data):
    if 'HA_Open' not in data.columns:
        data['HA_Open'] = np.nan
    if 'HA_Close' not in data.columns:
        data['HA_Close'] = np.nan
    if 'HA_High' not in data.columns:
        data['HA_High'] = np.nan
    if 'HA_Low' not in data.columns:
        data['HA_Low'] = np.nan
    if 'ConditionForTopWickOnly' not in data.columns:
        data['ConditionForTopWickOnly'] = False

    data['ConditionForTopWickOnly'] = data['ConditionForTopWickOnly'].astype(bool)

    for i in range(len(data)):
        if i < 2:
            data.loc[data.index[i], 'HA_Close'] = (data.loc[data.index[i], 'Open'] + data.loc[data.index[i], 'High'] + 
                    data.loc[data.index[i], 'Low'] + data.loc[data.index[i], 'Close']) / 4
            data.loc[data.index[i], 'HA_Open'] = data.loc[data.index[i], 'Close']
        else:
            data.loc[data.index[i], 'HA_Close'] = (data.loc[data.index[i-1], 'Open'] + data.loc[data.index[i-1], 'High'] + 
                                                   data.loc[data.index[i-1], 'Low'] + data.loc[data.index[i-1], 'Close']) / 4
            data.loc[data.index[i], 'HA_Open'] = (data.loc[data.index[i-2], 'HA_Open'] + 
                                                  data.loc[data.index[i-2], 'HA_Close']) / 2

        data.loc[data.index[i], 'HA_High'] = max(data.loc[data.index[i-1], 'High'], data.loc[data.index[i], 'HA_Open'], data.loc[data.index[i], 'HA_Close'])
        data.loc[data.index[i], 'HA_Low'] = min(data.loc[data.index[i-1], 'Low'], data.loc[data.index[i], 'HA_Open'], data.loc[data.index[i], 'HA_Close'])

        data.loc[data.index[i], 'ConditionForTopWickOnly'] = (data.loc[data.index[i], 'HA_Close'] >= data.loc[data.index[i], 'HA_Open']) & \
                                                              (data.loc[data.index[i], 'HA_High'] > data.loc[data.index[i], 'HA_Close']) & \
                                                              (data.loc[data.index[i], 'HA_Low'] == min(data.loc[data.index[i], 'HA_Open'], data.loc[data.index[i], 'HA_Close']))

    return data

# Check if the timestamp is within trading hours (9:30 AM to 4:00 PM)
def is_trading_hours(timestamp):
    return time(9, 30) <= timestamp.time() <= time(16, 0)

# Function to identify trigger points and track trades
def identify_triggers(data, Threshold=2, trading_hours=True):
    highest_price = 0
    highest_timestamp = None
    triggers = []
    trades = []
    last_buy_price = 0
    last_buy_timestamp = None

    for i in range(2, len(data)):
        if highest_price < 0:
            highest_price = 0
        else:
            if data['ConditionForTopWickOnly'].iloc[i-2] and data['ConditionForTopWickOnly'].iloc[i-1] and not data['ConditionForTopWickOnly'].iloc[i]:
                if is_trading_hours(data.index[i]) and data['High'].iloc[i] > highest_price:
                    highest_price = data['High'].iloc[i]
                    highest_timestamp = data.index[i]
                #Yahoo charts has bad data sometimes after hours, set to Close instead of High to filter it
                if not is_trading_hours(data.index[i]) and data['High'].iloc[i] > highest_price:
                    highest_price = data['High'].iloc[i]
                    highest_timestamp = data.index[i]

        threshold = highest_price * Threshold / 100

        # Sell logic
        if last_buy_price > 0:
            sell_threshold = last_buy_price + (Threshold / 100 * last_buy_price)
            if (is_trading_hours(data.index[i]) and data['High'].iloc[i] > sell_threshold) or data['High'].iloc[i] > sell_threshold: #Set to close like above to
                sell_trade = {
                    "buy_timestamp": trades[-1]['buy_timestamp'],
                    "buy_price": trades[-1]['buy_price'],
                    "sell_timestamp": str(data.index[i]),
                    "sell_price": round(sell_threshold, 2),
                    "profit": round(sell_threshold - last_buy_price, 2)
                }
                trades[-1].update(sell_trade)
                last_buy_price = 0
                last_buy_timestamp = None

        if highest_price - data['Low'].iloc[i] > threshold and data['ConditionForTopWickOnly'].iloc[i-1] and data['ConditionForTopWickOnly'].iloc[i] and (is_trading_hours(data.index[i]) or not trading_hours):
            trigger = {
                "high_timestamp": str(highest_timestamp),
                "high_price": round(highest_price, 2),
                "trigger_timestamp": str(data.index[i]),
                "trigger_price": round(data['Low'].iloc[i], 2),
                "percentage_drop": round(((highest_price - data['Low'].iloc[i]) / highest_price) * 100, 2),
                "bar_high": round(data['High'].iloc[i], 2),
                "bar_low": round(data['Low'].iloc[i], 2),
                "bar_open": round(data['Open'].iloc[i], 2),
                "bar_close": round(data['Close'].iloc[i], 2)
            }
            triggers.append(trigger)
            if last_buy_price == 0:
                buy_trade = {
                    "buy_timestamp": str(data.index[i]),
                    "buy_price": round(data['Low'].iloc[i], 2)
                }
                last_buy_timestamp = data.index[i]
                trades.append(buy_trade)
                last_buy_price = data['Low'].iloc[i] #Put this in to deail with bad data: max(max(max(data['Low'].iloc[i], data['High'].iloc[i]), data['Open'].iloc[i]), data['Close'].iloc[i])
            highest_price = -1
            highest_timestamp = None

    return triggers, trades

# Calculate the number of trading days the money is tied up and the 365-day gain
def calculate_totals(trades, total_triggers, Threshold):
    total_days = 0
    total_profit = 0
    total_sell_orders = 0
    now = datetime.now()

    for trade in trades:
        buy_timestamp = pd.to_datetime(trade['buy_timestamp']).tz_localize(None)
        sell_timestamp = pd.to_datetime(trade['sell_timestamp']).tz_localize(None) if 'sell_timestamp' in trade else now

        # Calculate the number of trading days between buy and sell timestamps
        days_held = len(pd.date_range(start=buy_timestamp, end=sell_timestamp, freq='B'))
        total_days += days_held

        if 'profit' in trade:
            total_profit += trade['profit']
            total_sell_orders += 1

    # Calculate the 365-day gain
    buy_profit_percentage = Threshold * total_sell_orders

    if total_days > 0:
        annual_factor = 252 / total_days  # Use 252 trading days in a year
        Annual_Trade_Gain = buy_profit_percentage * annual_factor
    else:
        Annual_Trade_Gain = 0

    # Productivity Score calculation
    if len(trades) > 0 and total_sell_orders > 0:
        Score = round((
            (len(trades) / np.ceil((total_triggers + 1 - len(trades)) / 2)) *
            (buy_profit_percentage / 100) *
            (Annual_Trade_Gain / 100) *
            (np.log(total_triggers - len(trades) +1) + 1) / 10
        ) * 100, 2)
    else:
        Score = 0

    return total_days, Annual_Trade_Gain, buy_profit_percentage, total_sell_orders, len(trades), Score, now.astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %I:%M:%S %p %Z")

def get_file_age_in_minutes(filename):
    filename_with_extension = filename + '.json'
    directory = os.path.join(os.path.dirname(__file__), 'stock_data')
    file_path = os.path.join(directory, filename_with_extension)

    if not os.path.exists(file_path):
        return 9999999999

    file_mod_time = os.path.getmtime(file_path)
    file_mod_datetime = datetime.fromtimestamp(file_mod_time)
    current_datetime = datetime.now()
    age_timedelta = current_datetime - file_mod_datetime
    age_in_minutes = age_timedelta.total_seconds() / 60

    return age_in_minutes

# Save results to JSON
def save_to_json(ticker, triggers, trades, totals, filename):
    if not triggers and not trades and not totals:
        print(f"No data to save for {filename}. The values are empty.")
        return
    
    if not isinstance(totals, dict):
        raise ValueError(f"Expected a dictionary for totals: {totals}. Did not save: {filename}")
    # Remove keys with a value of 0
    totals = {k: v for k, v in totals.items() if v != 0}

    result = {
        ticker: {
            "triggers": triggers,
            "trades": trades,
            "totals": totals
        }
    }

    # Ensure the stock_data directory exists
    directory = os.path.join(os.path.dirname(__file__), 'stock_data')
    if not os.path.exists(directory):
        os.makedirs(directory)

    filepath = os.path.join(directory, filename)

    with open(filepath, 'w') as f:
        json.dump(result, f, indent=4)
    print(f"Results saved to {filename}")

def recommendation_mean_to_key(mean):
    """
    Convert recommendationMean to a key.
    
    Args:
        mean (float): The recommendationMean value.
        
    Returns:
        str: The recommendation key.
    """
    if mean <= 1.5:
        return "Strong Buy"
    elif mean <= 2.5:
        return "Buy"
    elif mean <= 3.5:
        return "Hold"
    elif mean <= 4.5:
        return "Sell"
    else:
        return "Strong Sell"
    
def convert_to_yahoo_format(custom_format, format_type):
    # Define mappings for period and interval separately using your two-letter format
    period_mapping = {
        '1Mo': '1mo',  # Smallest period
        '3Mo': '3mo',
        '6Mo': '6mo',
        '1Yr': '1y',
        '2Yr': '2y',
        '5Yr': '5y',
        '10Yr': '10y',
        'YtD': 'ytd',
        'Max': 'max',
        '1Dy': '1d',
        '5Dy': '5d',
        '1Wk': '1wk'
    }
    
    interval_mapping = {
        '1Mi': '1m',  # Smallest interval
        '2Mi': '2m',
        '5Mi': '5m',
        '15Mi': '15m',
        '30Mi': '30m',
        '60Mi': '60m',
        '90Mi': '90m',
        '1Hr': '1h',
        '1Dy': '1d',
        '5Dy': '5d',
        '1Wk': '1wk',
        '1Mo': '1mo'
    }
    
    # Select the appropriate mapping based on the format type
    if format_type == 'period':
        mapping = period_mapping
    elif format_type == 'interval':
        mapping = interval_mapping
    else:
        raise ValueError("Invalid format type. Choose 'period' or 'interval'.")
    
    # Convert the custom format to Yahoo's format using the selected mapping
    return mapping.get(custom_format, custom_format)
    
# Analyze stock data for different periods and resolutions
def analyze_yahoo_chart(ticker,period,interval,age, yf_ticker_obj):
    if get_file_age_in_minutes(f"{ticker}_Chart_{period}_{interval}") > age:
        try:  
            data = fetch_yahoo_chart(yf_ticker_obj, convert_to_yahoo_format(period,'period'), 
                                     convert_to_yahoo_format(interval, 'interval'))            
        except:      
            data = None 
    else:
        data = None
    if data is not None:
        data = calculate_heikin_ashi(data)
        best_threshold = 0
        best_triggers = []
        best_trades = []
        best_score = 0
        best_totals = {}

        for threshold in range(1, 21):
            triggers, trades = identify_triggers(data, threshold)
            total_days, Annual_Trade_Gain, buy_profit_percentage, total_sell_orders, total_buy_orders, Score, now = calculate_totals(trades, len(triggers), threshold)

            if (Score > best_score and total_sell_orders >= 4) or (total_sell_orders < 4 and total_sell_orders > 0 and best_score == 0):
                best_score = Score
                best_threshold = threshold
                best_triggers = triggers
                best_trades = trades
                best_totals = {
                    "Report": f"Source: Yahoo, Period: {period}, Interval: {interval}",
                    "Threshold": threshold,
                    "Triggers": len(triggers),
                    "Buy_Orders": total_buy_orders,
                    "Sell_Orders": total_sell_orders,
                    "Gained": buy_profit_percentage,
                    "Working_Days": total_days,
                    "Annual_Trade_Gain": round(Annual_Trade_Gain, 2),
                    "Score": Score,
                    "Updated": now
                }
                print(ticker,best_totals)

        save_to_json(ticker, best_triggers, best_trades, best_totals, f"{ticker}_Chart_{period}_{interval}.json")

def high_to_highest_score(ratio):
    optimal_ratio = 0.5
    max_score = 1  # Normalized to a range of 0 to 1 for simplicity

    # Calculate score with a parabolic function
    score = max_score * (1 - ((ratio - optimal_ratio) ** 2) / optimal_ratio ** 2)
    return max(0, score)  # Ensure the score is not negative

def calculate_score(apr, total_months, curved_ratio, avg_monthly_change, pe_ratio, forward_pe_ratio, peg_ratio, ps_ratio, risk):
    
    weighted_pe = 1 / (pe_ratio + 1) * 0.075 if pe_ratio and pe_ratio > 0 else 0
    weighted_forward_pe = 1 / (forward_pe_ratio + 1) * 0.075 if forward_pe_ratio and forward_pe_ratio > 0 else 0
    weighted_peg = 1 / (peg_ratio + 1) * 0.4 if peg_ratio and peg_ratio > 0 else 0
    weighted_ps = 1 / (ps_ratio + 1) * 0.3 if ps_ratio and ps_ratio > 0 else 0

    combined_weighted_ratio = weighted_pe + weighted_forward_pe + weighted_peg + weighted_ps
    if combined_weighted_ratio == 0:
        combined_weighted_ratio = curved_ratio / 2

    chart_score = apr * total_months * curved_ratio * (1 + avg_monthly_change / 100)
    ratio_score = combined_weighted_ratio
    risk = 10 - risk
    risk_weight = 0.2
    score = max(chart_score * max(ratio_score, .01), 0) * (1 + risk_weight * risk)
    return score

# Analyze stock data for different periods and resolutions
def analyze_stock(ticker):
    print(f"Scraping data for: {ticker}")
    yf_ticker_obj = yf.Ticker(ticker)

    analyze_yahoo_chart(ticker, '1Mo', '5Mi', 60, yf_ticker_obj)
    analyze_yahoo_chart(ticker, '6Mo', '1Hr', 60 * 4, yf_ticker_obj)
    analyze_yahoo_chart(ticker, '2Yr', '1Hr', 60 * 24 * 7, yf_ticker_obj)

    # Analyze max monthly data
    if get_file_age_in_minutes(f"{ticker}_Overall_Trend") > 1440:
        data = fetch_yahoo_chart(yf_ticker_obj, 'max', '1mo')
        try: 
            details = get_stock_details(ticker)
            save_to_json(ticker, [], [], details, f"{ticker}_Details.json")
            # Extract financial recommendation mean and convert it
            recommendation_mean = details.get('financialData', {}).get('recommendationMean', None)
            if recommendation_mean:
                Recommendation = recommendation_mean_to_key(recommendation_mean)
            else:
                Recommendation = 'None'

            # Extract financial ratios with default values if primary keys are missing
            risk = details.get('assetProfile', {}).get('overallRisk', 5)
            pe_ratio = round(details.get('summaryDetail', {}).get('trailingPE', 0),2)
            forward_pe_ratio = round(details.get('summaryDetail', {}).get('forwardPE', 0),2)
            peg_ratio = round(details.get('defaultKeyStatistics', {}).get('pegRatio', 0),2)
            ps_ratio = round(details.get('summaryDetail', {})
                             .get('priceToSalesTrailing12Months', 0),2)
        except Exception as e:
            print(e) 
            Recommendation = 'None'
            risk = 5
            pe_ratio = 0
            forward_pe_ratio = 0
            peg_ratio = 0
            ps_ratio = 0
    else:
        data = None
    if data is not None:
        Start_Date = data.index.min().strftime('%Y-%m-%d')
        Overall_Trend = "Upward" if data['High'].iloc[-1] > data['High'].iloc[0] else "Downward"

        # Calculate the start and end prices
        Start_Price = round(data['Close'].iloc[0], 2)
        End_Price = round(data['Close'].iloc[-1], 2)

        # Calculate monthly percentage changes
        monthly_changes = data['High'].pct_change().dropna() * 100

        # Calculate the average monthly percentage change
        Average_Monthly_Change = monthly_changes.mean()

        # Calculate the total months
        total_months = len(monthly_changes)

        # Annualize the average monthly change
        Average_APR = Average_Monthly_Change * 12

        # Calculate the total number of days
        total_days = (data.index[-1] - data.index[0]).days

        # Calculate the total number of months
        total_months = total_days / 30.44  # Average number of days per month

        # Calculate the daily growth rate
        daily_growth_rate = (End_Price / max(Start_Price,1)) ** (1 / max(total_days,1)) - 1

        # Calculate the annual APR based on daily compounding
        Average_APR = round(((1 + daily_growth_rate) ** 365 - 1) * 100, 2)

        # Find the highest high
        Highest_High = data['High'].max()

        # Compare the current month's high to the highest high
        Current_High = data['High'].iloc[-1]
        High_To_Highest_Ratio = Current_High / Highest_High if Highest_High != 0 else 0

          # Define the curved function for high_to_highest_ratio
        def high_to_highest_curve(ratio, optimal_ratio=0.5):
            return 1 - ((ratio - optimal_ratio) ** 2) / (4 * optimal_ratio ** 2)

        # Apply the curved function to high_to_highest_ratio
        curved_ratio = high_to_highest_curve(High_To_Highest_Ratio)

        inflow, outflow, netflow, recommendation_mean, MA_Trend = make_recommendation(yf_ticker_obj)

        # Calculate the score
        Score = calculate_score(Average_APR, total_months, curved_ratio, Average_Monthly_Change, 
                                pe_ratio, forward_pe_ratio, peg_ratio, ps_ratio, risk)

        if Recommendation == 'None':
            Recommendation = recommendation_mean_to_key(recommendation_mean)

        # Save the results to JSON (mock function)
        save_to_json(ticker, [], [], {
            "Start_Date": Start_Date,
            "Start_Price": Start_Price,
            "Current_Price": End_Price,
            "Overall_Trend": Overall_Trend,
            "Average_Monthly_Change": round(Average_Monthly_Change, 2),
            "Average_APR": Average_APR,
            "Highest_High": round(Highest_High, 2),
            "Current_High": round(Current_High, 2),
            "High_To_Highest_Ratio": round(High_To_Highest_Ratio, 2),
            "Trailing_PE_Ratio": pe_ratio,
            "Forward_PE_Ratio": forward_pe_ratio,
            "PEG_Ratio": peg_ratio,
            "PS_Ratio": ps_ratio,
            "Recommendation": Recommendation, 
            "Month_Inflow": inflow,
            "Month_Outflow": outflow,
            "Month_Net": netflow,
            "50_200_MA_Trend": round(MA_Trend, 2),
            "Risk": risk,
            "Score": round(Score, 2),
            "Updated": datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %I:%M:%S %p %Z")
        }, f"{ticker}_Overall_Trend.json")





if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
                                     'Analyze stock data for different periods and resolutions.')
    parser.add_argument('ticker', type=str, help='Stock ticker symbol')
    args = parser.parse_args()

    analyze_stock(args.ticker.upper())

