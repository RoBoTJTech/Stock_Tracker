import os
import json
import math
from datetime import datetime

def get_Scores(directory):
    scores = {
        "Overall_Trend": {},
        "2Yr_1Hr": {},
        "1Mo_5Mi": {}
    }

    for filename in os.listdir(directory):
        if filename.endswith("_Overall_Trend.json"):
            score_type = "Overall_Trend"
        elif filename.endswith("Chart_2Yr_1Hr.json"):
            score_type = "2Yr_1Hr"
        elif filename.endswith("Chart_1Mo_5Mi.json"):
            score_type = "1Mo_5Mi"
        else:
            continue

        filepath = os.path.join(directory, filename)
        with open(filepath, 'r') as f:
            try: 
                ticker = filename.split('_')[0]
                data = json.load(f)
                scores[score_type][ticker] = data[ticker]["totals"]
            except:
                pass
    return scores

def get_lowest_and_average_values(unique_tickers, scores):
    lowest_values = {
        "Overall_Trend": float('inf'),
        "2Yr_1Hr": float('inf'),
        "1Mo_5Mi": float('inf'),
    }

    average_values = {
        "Overall_Trend": 0,
        "2Yr_1Hr": 0,
        "1Mo_5Mi": 0
    }

    total_counts = {
        "Overall_Trend": 0,
        "2Yr_1Hr": 0,
        "1Mo_5Mi": 0
    }

    for ticker in unique_tickers:
        overall_score = scores["Overall_Trend"].get(ticker, {}).get("Score", 0) 
        y2_score = scores["2Yr_1Hr"].get(ticker, {}).get("Score", 0)
        mo1_score = scores["1Mo_5Mi"].get(ticker, {}).get("Score", 0)
        if overall_score < lowest_values["Overall_Trend"]:
            if overall_score > 0:
                lowest_values["Overall_Trend"] = overall_score
        if y2_score < lowest_values["2Yr_1Hr"]:
            if y2_score > 0:
                lowest_values["2Yr_1Hr"] = y2_score
        if mo1_score < lowest_values["1Mo_5Mi"]:
            if mo1_score > 0:
                lowest_values["1Mo_5Mi"] = mo1_score

        average_values["Overall_Trend"] += overall_score
        total_counts["Overall_Trend"] += 1

        average_values["2Yr_1Hr"] += y2_score
        total_counts["2Yr_1Hr"] += 1

        average_values["1Mo_5Mi"] += mo1_score
        total_counts["1Mo_5Mi"] += 1


    for key in average_values:
        if total_counts[key] != 0:
            average_values[key] = (average_values[key] / total_counts[key]) #+ lowest_values[key]) /2
    print(lowest_values)
    print(average_values)
    return lowest_values

def filter_scores(scores, unique_tickers, average_values, trade_type='buy'):
    symbols = []

    if trade_type == 'sell':
        for ticker in unique_tickers:
            symbols.append((ticker, scores["1Mo_5Mi"].get(ticker, {})))
        sorted_tickers = sorted(symbols, key=lambda x: x[1].get("Score", 0), reverse=False)
        symbols = [ticker for ticker, _ in sorted_tickers]
        return symbols
    for ticker in scores["Overall_Trend"].keys():
        if trade_type == 'buy' and ticker in unique_tickers:
            continue
        if trade_type == 'hold' and ticker not in unique_tickers:
            continue
        overall_score = scores["Overall_Trend"].get(ticker, {}).get("Score", 0)
        Overall_Trend = scores["Overall_Trend"].get(ticker, {}).get("Overall_Trend", "Downward")
        y2_score = scores["2Yr_1Hr"].get(ticker, {}).get("Score", 0)
        mo1_score = scores["1Mo_5Mi"].get(ticker, {}).get("Score", 0)
        Sell_Orders = scores["1Mo_5Mi"].get(ticker, {}).get("Sell_Orders", 0)
        Recommendation = scores["Overall_Trend"].get(ticker, {}).get("Recommendation", "None")
        if ("Buy" in Recommendation and
            Sell_Orders > 4 and Overall_Trend == "Upward" and
            overall_score > average_values["Overall_Trend"] and
            y2_score > average_values["2Yr_1Hr"] and
            mo1_score > average_values["1Mo_5Mi"]):
            symbols.append((ticker, scores["1Mo_5Mi"].get(ticker, {})))
    sorted_tickers = sorted(symbols, key=lambda x: x[1].get("Score", 0), reverse=True)
    symbols = [ticker for ticker, _ in sorted_tickers]
    return symbols

def create_hot_picks_json(sell_symbols, buy_symbols, hold_symbols):
    hot_picks = {
        "sell_symbols": sell_symbols,
        "buy_symbols": buy_symbols,
        "hold_symbols": hold_symbols
    }

    with open("hot_picks.json", "w") as file:
        json.dump(hot_picks, file, indent=4)

def main():
    directory = 'stock_data'
    scores = get_Scores(directory)
    print('Getting Hot Picks')

    with open('unique_tickers.json', 'r') as file:
        unique_tickers = json.load(file)

    average_values = get_lowest_and_average_values(unique_tickers, scores)
    buy_symbols = filter_scores(scores, unique_tickers, average_values, 'buy')
    hold_symbols = filter_scores(scores, unique_tickers, average_values, 'hold')
    sell_symbols_unsorted = [ticker for ticker in unique_tickers if ticker not in hold_symbols]
    sell_symbols = filter_scores(scores, sell_symbols_unsorted, average_values, 'sell') 

    # Create Hot Picks JSON file
    create_hot_picks_json(sell_symbols, buy_symbols, hold_symbols)

if __name__ == "__main__":
    main()

