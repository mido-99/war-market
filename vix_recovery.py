import pandas as pd
import numpy as np


#-- Part A: Peak VIX date and spike magnitude per window
# ---- 1. Create temp window periods -----------------
windows_str = """
window_2: 2025-06-13 to 2025-06-24
window_3: 2025-06-25 to 2026-02-27
window_4: 2026-02-28 to 2026-04-07
window_5: 2026-04-08 to 2026-04-30
"""
# Prepare a list of dicts for pandas
windows = [line.strip() for line in windows_str.split('\n') if line.strip()]
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


# ---- 2. Load prices & VIX table ---------------
prices_df = pd.read_csv('data/all_tickers.csv')
prices_df['date'] = pd.to_datetime(prices_df['date'])
# we only care about this from now on
vix_prices_df = prices_df[prices_df['ticker'] == '^VIX']

# ---- 3. Calculate baseline --------------------
# Extract the cutoff date first to keep the main query readable
cutoff_date = windows_df.loc[
    windows_df['window'] == 'window_2', 'start'
    ].item()

# Filter and calculate the mean
vix_baseline = round(
    vix_prices_df.loc[
        vix_prices_df['date'] < cutoff_date, 
        'adj_close'
    ].mean(),
    4
)


# ---- 4. Calculate VIX peaks in windows---------
# Intermediate cross table
merged_df = vix_prices_df.merge(windows_df, how='cross')

# Map row dates between correct window bounds
vix_per_window = merged_df[
    merged_df['date'].between(
        merged_df['start'],
        merged_df['end']
    )
]
# No longer needed
vix_per_window.drop(columns=['start', 'end'], inplace=True)

# Get indices of max adj_close to get dates along
idx_max_vix = vix_per_window.groupby('window')['adj_close'].idxmax()
peaks_df = vix_per_window.loc[idx_max_vix].copy()

# Assign & edit columns
peaks_df['baseline_vix'] = vix_baseline
peaks_df['spike_magnitude'] = round(peaks_df['adj_close'] - vix_baseline, 4)

peaks_vix_df = peaks_df[[
    'window', 'date', 'adj_close', 'baseline_vix', 'spike_magnitude'
]].rename(columns={
    'date': 'peak_date', 'adj_close': 'peak_vix'
    })


# -- Part B: Days to recover (calendar days from peak back to baseline)
# 1. Merge peak date & vix into corresponding window
recoery_vpw = vix_per_window.merge(
    peaks_vix_df[['window', 'peak_date', 'peak_vix']],
    on='window'
    ).copy()

# 2. Gather all potential recovery days STRICTLY within the window bounds
recovery_days = recoery_vpw[
    (recoery_vpw['adj_close'] <= vix_baseline) & 
    (recoery_vpw['date'] > recoery_vpw['peak_date'])
]

# 3. Grab the earliest recovery day per window
recovery_dates = recovery_days.sort_values('date').drop_duplicates(
    subset=['window'], keep='first'
    )

# 4. MASTER LEFT JOIN: Start with your peaks, bring in recoveries if they exist
final_result = peaks_vix_df.merge(
    recovery_dates[['window', 'date']], 
    on='window', 
    how='left'
).rename(columns={'date': 'recovery_date'})

# 5. Calculate delta safely (Window 4 will naturally become NaN)
final_result['days_to_recover'] = (
    final_result['recovery_date'] - final_result['peak_date']
    ).dt.days