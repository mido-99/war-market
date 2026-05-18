import pandas as pd

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


