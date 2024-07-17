import os
import json
import math
import _app_functions
import _app_constants

def worst_trading_rank(unique_tickers, scores):
    rank = 0
    for ticker in unique_tickers:
        ticker_rank = scores["Overall_Trend"].get(ticker, {}).get("Rank", 0)
        if ticker_rank > rank:
            rank = ticker_rank
    return rank

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
                if "Score" in data[ticker]["totals"]:
                    scores[score_type][ticker] = data[ticker]["totals"]
            except Exception as e:
                print(f"Error processing file {filename}: {e}, skipping.")
                continue

    # Create lists of tickers sorted by their score values
    Overall_Trend_Orders = sorted(scores["Overall_Trend"], key=lambda ticker: scores["Overall_Trend"][ticker]["Score"], reverse=True)
    Yr_1Hr_Orders = sorted(scores["2Yr_1Hr"], key=lambda ticker: scores["2Yr_1Hr"][ticker]["Score"], reverse=True)
    Mo_5Mi_Orders = sorted(scores["1Mo_5Mi"], key=lambda ticker: scores["1Mo_5Mi"][ticker]["Score"], reverse=True)
    
    # Calculate the rank for each ticker in the Overall_Trend_Orders list
    ranks = {}
    for i, ticker in enumerate(Overall_Trend_Orders):
        overall_rank = i + 1
        yr_1hr_rank = Yr_1Hr_Orders.index(ticker) + 1 if ticker in Yr_1Hr_Orders else len(Yr_1Hr_Orders) + 1
        mo_5mi_rank = Mo_5Mi_Orders.index(ticker) + 1 if ticker in Mo_5Mi_Orders else len(Mo_5Mi_Orders) + 1
        total_rank = overall_rank + yr_1hr_rank + mo_5mi_rank
        scores["Overall_Trend"][ticker]["Rank"] = total_rank
        ranks[ticker] = {
            "totals": {
                "Overall_Trend_Rank": overall_rank,
                "2Yr_1Hr_Rank": yr_1hr_rank,
                "1Mo_5Mi_Rank": mo_5mi_rank,
                "Total_Rank": total_rank
            }
        } 

    # Sort ranks by Total_Rank
    sorted_ranks = sorted(ranks.items(), key=lambda item: item[1]["totals"]["Total_Rank"])
    # Update scores and add actual Rank to ranks
    for actual_rank, (ticker, rank_info) in enumerate(sorted_ranks, start=1):
        scores["Overall_Trend"][ticker]["Rank"] = actual_rank
        rank_info["totals"]["Rank"] = actual_rank

    # Convert sorted_ranks back to dictionary for output
    sorted_ranks_dict = {ticker: rank_info for ticker, rank_info in sorted_ranks}
    # Write the ranks to ranks.json
    with open('ranks.json', 'w') as outfile:
            json.dump(sorted_ranks_dict, outfile, indent=4)
    
    return scores

def filter_scores(scores, unique_tickers, rank, trade_type='buy'):
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
        Overall_Rank = scores["Overall_Trend"].get(ticker, {}).get("Rank", 0)
        Overall_Trend = scores["Overall_Trend"].get(ticker, {}).get("Overall_Trend", "Downward")
        Sell_Orders = scores["1Mo_5Mi"].get(ticker, {}).get("Sell_Orders", 0)
        Recommendation = scores["Overall_Trend"].get(ticker, {}).get("Recommendation", "None")
        trade_status = _app_functions.ai_trade_status(ticker)
        if (trade_status and "Buy" in Recommendation and Overall_Trend == "Upward" and Overall_Rank <= rank and 
            (trade_type != 'buy' or (trade_type == 'buy' and Sell_Orders > 4))):
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

    rank = worst_trading_rank(unique_tickers, scores)
    buy_symbols = filter_scores(scores, unique_tickers, rank, 'buy')
    hold_symbols = filter_scores(scores, unique_tickers, rank, 'hold')
    sell_symbols_unsorted = [ticker for ticker in unique_tickers if ticker not in hold_symbols]
    sell_symbols = filter_scores(scores, sell_symbols_unsorted, rank, 'sell') 

    # Create Hot Picks JSON file
    create_hot_picks_json(sell_symbols, buy_symbols, hold_symbols)

if __name__ == "__main__":
    main()

