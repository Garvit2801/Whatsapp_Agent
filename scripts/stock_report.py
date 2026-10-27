import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

TICKERS = [
    x.strip().upper()
    for x in os.getenv("STOCK_TICKERS", "AAPL,MSFT,GOOGL").split(",")
    if x.strip()
]

# Unofficial Yahoo Finance chart endpoint; no API key needed.
QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"

def fetch_quote(ticker: str) -> dict:
    response = requests.get(
        QUOTE_URL.format(ticker=ticker),
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()
    meta = response.json()["chart"]["result"][0]["meta"]
    return {
        "price": meta["regularMarketPrice"],
        "previous_close": meta.get("chartPreviousClose") or meta.get("previousClose"),
        "currency": meta.get("currency", ""),
    }

def main():
    failures = 0
    print("Stock report")

    for ticker in TICKERS:
        try:
            quote = fetch_quote(ticker)
        except Exception as e:
            failures += 1
            print(f"  {ticker}: failed ({e})")
            continue

        line = f"  {ticker}: {quote['price']:.2f} {quote['currency']}"
        if quote["previous_close"]:
            change = (quote["price"] - quote["previous_close"]) / quote["previous_close"] * 100
            line += f" ({change:+.2f}%)"
        print(line)

    if failures == len(TICKERS):
        sys.exit(1)

if __name__ == "__main__":
    main()
