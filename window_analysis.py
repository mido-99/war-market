import pandas as pd
import numpy as np


# ---- 1. Create temp window periods
windows_str = """
window_1: 2025-01-02 to 2025-06-12
window_2: 2025-06-13 to 2025-06-24
window_3: 2025-06-25 to 2026-02-27
window_4: 2026-02-28 to 2026-04-07
window_5: 2026-04-08 to 2026-04-30
"""

# Prepare a list of dicts for pandas
windows = [
    line.strip() for line in windows_str.split('\n') if line.strip()
    ]

windows_periods = [
    {
        'window': window.split(':')[0],
        'start': window.split(':')[1].split('to')[0].strip(),
        'end': window.split(':')[1].split('to')[1].strip(),
    }
    for window in windows
]

# Create df & correct data type
windows_df = pd.DataFrame(windows_periods)

windows_df['start'] = pd.to_datetime(windows_df['start'])
windows_df['end'] = pd.to_datetime(windows_df['end'])


# ---- 2. Merge prices with window periods 
prices_df = pd.read_csv('data/all_tickers.csv')

# Step 1: Temporarily combine every single row of prices with every row of windows
# This creates a giant combined table where every date is matched with all 5 windows
cross_merged = prices_df.merge(windows_df, how="cross")

# Step 2: Keep only the rows where the price date actually falls between the window dates
# This acts exactly like our SQL: ON p.date BETWEEN wb.w_start AND wb.w_end
merged_df = cross_merged[
    (cross_merged["date"] >= cross_merged["start"])
    & (cross_merged["date"] <= cross_merged["end"])
]

# Step 3: Clean up the extra date columns we don't need anymore
merged_df = merged_df.drop(columns=["start", "end"])


# ---- 3. Create df with first & last price for each ticker

# Group by the identifiers, and calculate min/max on the date column
first_last_df = (
    merged_df.groupby(["ticker", "asset_class", "window"])
    .agg(
        first_date=("date", "min"), 
        last_date=("date", "max")
        )
    .reset_index()
    .sort_values(['window', 'asset_class'])
)

# Bring start_price and end_price from merged_df. We have 2 approaches

# 1. the indexing Approach
# Step A: Build the Search Index (The Phonebook)
price_lookup = merged_df.set_index(['ticker', 'date'])['adj_close']

prices_at_ends = first_last_df.copy()

# Step B: Search for the Start Price
prices_at_ends['start_price'] = prices_at_ends.set_index(
    ['ticker', 'first_date']
).index.map(price_lookup)

# Step C: Search for the End Price
prices_at_ends['end_price'] = prices_at_ends.set_index(
    ['ticker', 'last_date']
).index.map(price_lookup)

# # 2. the merge Approach - commented out
# # Step 1: Bring in the start_price
# # We merge first_last_df with a sliced, renamed copy of merged_df
# merged_start = first_last_df.merge(
#     merged_df[["ticker", "date", "adj_close"]].rename(
#         columns={"date": "first_date", "adj_close": "start_price"}
#     ),
#     on=["ticker", "first_date"],
#     how="inner",
# )

# # Step 2: Bring in the end_price
# # We merge our new table with another sliced, renamed copy of merged_df
# prices_at_ends = merged_start.merge(
#     merged_df[["ticker", "date", "adj_close"]].rename(
#         columns={"date": "last_date", "adj_close": "end_price"}
#     ),
#     on=["ticker", "last_date"],
#     how="inner",
# )


# ---- 4. Calculate % for each ticker & rank in its class
# Change Percentage
prices_at_ends['pct_change'] = (prices_at_ends['end_price'] - prices_at_ends['start_price']).div(
    prices_at_ends['start_price'].replace(0, np.nan)
) * 100

# Rank in Class
prices_at_ends['rank_in_class'] = (
    prices_at_ends.groupby(['window', 'asset_class'])['pct_change']
    .rank(
        method='max',
        ascending=True
        )
)

# Cast type int instead of float for cleanliness
prices_at_ends['rank_in_class'] = prices_at_ends['rank_in_class'].astype(int)