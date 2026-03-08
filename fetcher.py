"""
Bloomberg Data Fetcher
======================
Run this script on a machine with Bloomberg Terminal to fetch all ticker data
and save it as a Parquet file. The Streamlit dashboard reads from this file.

Usage:
    python fetcher.py

Schedule this daily (e.g. Windows Task Scheduler) to keep data fresh.
After running, commit & push the updated parquet to GitHub so the
Streamlit Cloud app picks up the new data automatically.
"""

import os
import sys
import pandas as pd
from datetime import datetime

try:
    from xbbg import blp
except ImportError:
    print("ERROR: xbbg not installed. Run: pip install xbbg blpapi")
    print("       blpapi: pip install --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/ blpapi")
    sys.exit(1)

# ── paths ────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "DIM_METALS_DESCRIPTION.csv")
DATA_DIR = os.path.join(BASE_DIR, "data")
PARQUET_PATH = os.path.join(DATA_DIR, "metals_data.parquet")

# ── settings ─────────────────────────────────────────────────
YEARS_OF_HISTORY = 15
FIELD = "PX_LAST"


def load_tickers():
    df = pd.read_csv(CSV_PATH)
    for c in df.select_dtypes("object"):
        df[c] = df[c].str.strip().str.strip('"')
    return df["TICKER_BLOOMBERG"].unique().tolist()


def fetch_all(tickers, start, end):
    """Fetch each ticker individually and return a long-format DataFrame."""
    frames = []
    ok, fail = 0, 0

    for i, ticker in enumerate(tickers, 1):
        print(f"  [{i}/{len(tickers)}] {ticker} ... ", end="", flush=True)
        try:
            raw = blp.bdh(ticker, FIELD, start, end)
            if raw is None or raw.empty:
                print("NO DATA")
                fail += 1
                continue
            raw = raw.reset_index()
            df = pd.DataFrame({
                "ticker": ticker,
                "date": pd.to_datetime(raw.iloc[:, 0]),
                "value": pd.to_numeric(raw.iloc[:, 1], errors="coerce"),
            })
            df = df.dropna(subset=["value"])
            if df.empty:
                print("EMPTY")
                fail += 1
            else:
                frames.append(df)
                print(f"OK ({len(df)} rows)")
                ok += 1
        except Exception as e:
            print(f"ERROR: {e}")
            fail += 1

    print(f"\nDone: {ok} succeeded, {fail} failed out of {len(tickers)} tickers.")
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=["ticker", "date", "value"])


def main():
    print("=" * 60)
    print("Bloomberg Data Fetcher")
    print("=" * 60)

    tickers = load_tickers()
    print(f"Loaded {len(tickers)} tickers from CSV.\n")

    end = datetime.now().strftime("%Y-%m-%d")
    start = f"{datetime.now().year - YEARS_OF_HISTORY}-01-01"
    print(f"Fetching {FIELD} from {start} to {end}\n")

    data = fetch_all(tickers, start, end)

    os.makedirs(DATA_DIR, exist_ok=True)
    data.to_parquet(PARQUET_PATH, index=False)
    size_mb = os.path.getsize(PARQUET_PATH) / (1024 * 1024)
    print(f"\nSaved {len(data)} rows to {PARQUET_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
