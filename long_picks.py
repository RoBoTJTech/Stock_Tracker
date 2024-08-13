import os
import json

def get_Scores(directory):
    scores = []

    for filename in os.listdir(directory):
        if filename.endswith("_Overall_Trend.json"):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                ticker = filename.split('_')[0]
                Score = data[ticker]["totals"].get("Score", None)
                if Score > 0 or Score < 0:
                    scores.append((ticker, Score))

    # Sort scores in descending order, treating None as the lowest value
    scores.sort(key=lambda x: (x[1] is None, x[1]), reverse=True)
    return scores

def main():
    directory = 'stock_data'
    scores = get_Scores(directory)

    # Print sorted scores
    for ticker, score in scores:
        print(f"{ticker}: {score}")

if __name__ == "__main__":
    main()

