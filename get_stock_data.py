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
import warnings
import _schwab_api
import _sec_api
import _file_functions

warnings.filterwarnings("ignore")

if os.path.exists('etf_list.json'):
    with open('etf_list.json', 'r') as file:
        etf_list = json.load(file)


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

def make_recommendation(yf_ticker_obj, short_period=10):
    def calculate_slope(ma_series, start, end):
        """
        Calculate the slope of the moving average series between two points.
        
        :param ma_series: Pandas Series representing the moving average.
        :param start: Integer, the start index for the slope calculation.
        :param end: Integer, the end index for the slope calculation.
        :return: The slope of the moving average between the two points.
        """
        diff = ma_series.iloc[end] - ma_series.iloc[start]
        period = end - start
        slope = diff / period
        return slope

    total_inflows, total_outflows, net_inflows_outflows = estimate_inflows_outflows(yf_ticker_obj)
    try:
        # Fetch additional data for trend analysis
        data = fetch_yahoo_chart(yf_ticker_obj, '1y', '1d')
        data['MA50'] = data['Close'].rolling(window=50).mean()
        data['MA200'] = data['Close'].rolling(window=200).mean()
        MA_Trend = data['MA50'].iloc[-1] - data['MA200'].iloc[-1]

        # Define the periods for slope calculation
        last_period_start = -short_period
        last_period_end = -1
        prev_period_start = -2 * short_period
        prev_period_end = -short_period

        # Calculate the slopes
        slope_50_last_period = calculate_slope(data['MA50'], last_period_start, last_period_end)
        slope_50_prev_period = calculate_slope(data['MA50'], prev_period_start, prev_period_end)
        slope_200_last_period = calculate_slope(data['MA200'], last_period_start, last_period_end)
        slope_200_prev_period = calculate_slope(data['MA200'], prev_period_start, prev_period_end)

        # Key Conditions
        c1 = data['Close'].iloc[-1] > data['MA50'].iloc[-1] * 1.01  # Current price above 50-day MA by 1%
        c2 = data['MA50'].iloc[-1] > data['MA200'].iloc[-1] * 1.01  # 50-day MA above 200-day MA by 1%
        c3 = slope_50_last_period > slope_50_prev_period            # Slope of 50-day MA increasing
        c4 = slope_200_last_period > slope_200_prev_period          # Slope of 200-day MA increasing
        c5 = slope_50_last_period > slope_200_last_period * 1.0005  # Slope of 50-day MA is 0.05% greater than 200-day MA slope

        # Overall assessment for swing trading
        Trade_Status = "Trade" if all([c1, c2, c3, c4, c5]) else "Do Not Trade"
    
        # Prepare result as JSON
        ma_result = {
            "MA (Close > 50d)": "Met" if c1 else "Not Met",
            "MA (50d > 200d)": "Met" if c2 else "Not Met",
            "MA (50d slope increasing)": "Met" if c3 else "Not Met",
            "MA (200d slope increasing)": "Met" if c4 else "Not Met",
            "MA (50d slope > 200d slope by 0.05%)": "Met" if c5 else "Not Met",
            "Trade_Status": Trade_Status
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        MA_Trend = 0
        ma_result = {}

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

    return total_inflows, total_outflows, net_inflows_outflows, recommendation_mean, MA_Trend, ma_result

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
            if data['High'].iloc[i-1] > highest_price:
                highest_price = data['High'].iloc[i-1]
                highest_timestamp = data.index[i-1]

        threshold = highest_price * Threshold / 100

        # Sell logic
        if last_buy_price > 0:
            sell_threshold = last_buy_price + (Threshold / 100 * last_buy_price)
            if (is_trading_hours(data.index[i]) and data['High'].iloc[i] >= sell_threshold):
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

        if highest_price - data['High'].iloc[i-1] > threshold and data['High'].iloc[i] > data['High'].iloc[i-1] \
            and data['Open'].iloc[i-1] < data['Open'].iloc[i-2] and (is_trading_hours(data.index[i]) or not trading_hours):
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
                last_buy_price = data['Low'].iloc[i]
            highest_timestamp = None
            highest_price = 0

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

# Save results to JSON
def json_file_query(ticker, triggers, trades, totals, filename):

    # Ensure the stock_data directory exists
    directory = os.path.join(os.path.dirname(__file__), 'stock_data')
    if not os.path.exists(directory):
        os.makedirs(directory)

    filepath = os.path.join(directory, filename)

    previous_totals = {}
    # Check if file exists and read previous totals if available
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            data = json.load(file)
            if ticker in data and 'totals' in data[ticker]:
                previous_totals = data[ticker]['totals']

    if not triggers and not trades and not totals:
        print(f"Loading dataset from {filename}.")
        return previous_totals
    
    if not isinstance(totals, dict):
        print(f"Loading dataset from  {totals}.")
        return previous_totals
    # Remove keys with a value of 0
    totals = {k: v for k, v in totals.items() if v != 0}

    result = {
        ticker: {
            "triggers": triggers,
            "trades": trades,
            "totals": totals
        }
    }

    with open(filepath, 'w') as f:
        json.dump(result, f, indent=4)
    print(f"Saving dataset to {filename}")
    return totals

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
def analyze_chart(ticker,period,interval,age, yf_ticker_obj = False):
    if _file_functions.get_file_age_in_minutes(f"{ticker}_Chart_{period}_{interval}") > age:
        try:  
            if not yf_ticker_obj:
                bearer_key = _schwab_api.get_bearer_key()
                candles = _schwab_api.collect_30_days_of_data(ticker, bearer_key)
                data = _schwab_api.candles_to_dataframe(candles)   
            else:
                data = fetch_yahoo_chart(yf_ticker_obj, convert_to_yahoo_format(period,'period'), 
                    convert_to_yahoo_format(interval, 'interval'))        
        except:  
            data = None 
    else:
        data = None
    if data is not None:
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

        json_file_query(ticker, best_triggers, best_trades, best_totals, f"{ticker}_Chart_{period}_{interval}.json")

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

    chart_score = apr * total_months * (curved_ratio + 1) * (1 + avg_monthly_change / 100)
    risk = 10 - risk
    risk_weight = 0.2
    score = max(chart_score * max(combined_weighted_ratio, .01), 0) * (1 + risk_weight * risk)
    return score

# Analyze stock data for different periods and resolutions
def analyze_stock(ticker):
    print(f"Scraping data for: {ticker}")
    yf_ticker_obj = yf.Ticker(ticker)

    analyze_chart(ticker, '1Mo', '5Mi', 60, yf_ticker_obj)

    # Analyze max monthly data
    if _file_functions.get_file_age_in_minutes(f"{ticker}_Overall_Trend") > 1440:
        sec_info = {}
        if _file_functions.get_file_age_in_minutes(f"{ticker}_SEC_Info") > 43200:
            cik, start_date = _sec_api.get_company_info(ticker)
            if cik:
                sec_info = {'cik': cik, 'start_date': start_date}
        if ticker in etf_list and not sec_info.get('cik', 'Delisted').isdigit():
            sec_info = {'cik': 'ETF'}
        sec_info = json_file_query(ticker, [], [], sec_info,  f"{ticker}_SEC_Info.json")

        data = fetch_yahoo_chart(yf_ticker_obj, 'max', '1mo')
        #data = data[(data['Volume'] > (data['Volume'].iloc[-1]/1000))]
        try: 
            details = {}
            if _file_functions.get_file_age_in_minutes(f"{ticker}_Details") > 2880:
                details = get_stock_details(ticker)
            details = json_file_query(ticker, [], [], details, f"{ticker}_Details.json")
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
            earnings_date = details.get('calendarEvents', {}).get('earnings', {}).get('earningsDate', ['None'])[0]
            
        except Exception as e:
            print(e) 
            Recommendation = 'None'
            risk = 5
            pe_ratio = 0
            forward_pe_ratio = 0
            peg_ratio = 0
            ps_ratio = 0
            earnings_date = 'None'
    else:
        data = None
    if data is not None:
        # Calculate the start and end average prices
        Start_Date = data.index.min().strftime('%Y-%m-%d')
        Last_Name_Change = sec_info.get('start_date', Start_Date)

        # Filter the data from Last_Name_Change date onwards
        filtered_data = data.loc[Last_Name_Change:]

        # Calculate Start_Price using the filtered data
        if not filtered_data.empty:
            start_row = filtered_data.iloc[0]
            Start_Price = round((start_row['High'] + start_row['Low'] + start_row['Open'] + start_row['Close']) / 4, 2)
        else:
            Start_Price = round((data['High'].iloc[0] + data['Low'].iloc[0] + data['Open'].iloc[0] + data['Close'].iloc[0]) /4, 2)
        End_Price = round((data['High'].iloc[-1] + data['Low'].iloc[-1] + data['Open'].iloc[-1] + data['Close'].iloc[-1]) /4, 2)
        Overall_Trend = "Upward" if End_Price > Start_Price else "Downward"


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
        def high_to_highest_curve(ratio, optimal_ratio=0.75):
            return 1 - ((ratio - optimal_ratio) ** 2) / (4 * optimal_ratio ** 2)

        # Apply the curved function to high_to_highest_ratio
        curved_ratio = high_to_highest_curve(High_To_Highest_Ratio)

        inflow, outflow, netflow, recommendation_mean, MA_Trend, ma_result = make_recommendation(yf_ticker_obj)

        # Calculate the score
        print(Average_APR, total_months, curved_ratio, Average_Monthly_Change, 
                                pe_ratio, forward_pe_ratio, peg_ratio, ps_ratio, risk)
        Score = calculate_score(Average_APR, total_months, curved_ratio, Average_Monthly_Change, 
                                pe_ratio, forward_pe_ratio, peg_ratio, ps_ratio, risk)

        if Recommendation == 'None':
            Recommendation = recommendation_mean_to_key(recommendation_mean)

        # Save the results to JSON (mock function)
        json_file_query(ticker, [], [], {
            "CIK": sec_info.get('cik','Delisted'),
            'Earnings_Date': earnings_date,
            "Start_Date": Start_Date,
            "Last_Name_Change": Last_Name_Change,
            "First_Month_Average": Start_Price,
            "Current_Month_Average": End_Price,
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
            "50_200_MA": round(MA_Trend, 2),
            "MA_Analysis": ma_result,
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

