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
        'name': window.split(':')[0],
        'start': window.split(':')[1].split('to')[0].strip(),
        'end': window.split(':')[1].split('to')[1].strip(),
    }
    for window in windows
]

# Create df & correct data type
windows_df = pd.DataFrame(windows_periods)

windows_df['start'] = pd.to_datetime(windows_df['start'])
windows_df['end'] = pd.to_datetime(windows_df['end'])


