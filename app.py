import os

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

WINDOW_LABELS = {
    "window_1": "1 · Pre-conflict baseline",
    "window_2": "2 · 12-Day War",
    "window_3": "3 · Inter-conflict period",
    "window_4": "4 · Second operation",
    "window_5": "5 · Ceasefire / peace deal",
}

WINDOW_ORDER = list(WINDOW_LABELS.keys())

SECTOR_LABELS = {
    "defense":         "Defense",
    "drones_autonomy": "Drones & Autonomy",
    "cybersecurity":   "Cybersecurity",
    "energy":          "Energy",
    "airlines":        "Airlines",
    "shipping":        "Shipping",
    "agri_food":       "Agriculture & Food",
    "critical_mins":   "Critical Minerals",
    "safe_haven":      "Safe Havens",
    "broad_market":    "Broad Market",
    "big_tech":        "Technology",
    "healthcare":      "Healthcare",
}

SECTOR_COLORS = {
    "Defense":            "#C0392B",  # military red
    "Drones & Autonomy":  "#E74C3C",  # lighter red (war-adjacent tech)
    "Cybersecurity":      "#2C3E50",  # dark slate (dark web / stealth)
    "Energy":             "#E67E22",  # oil orange
    "Airlines":           "#5DADE2",  # sky blue
    "Shipping":           "#148F77",  # ocean teal
    "Agriculture & Food": "#58D68D",  # plant green
    "Critical Minerals":  "#85929E",  # steel gray
    "Safe Havens":        "#D4AC0D",  # gold
    "Broad Market":       "#7D3C98",  # neutral purple
    "Technology":         "#1A5276",  # deep tech blue
    "Healthcare":         "#F1948A",  # soft pink
}


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "war_market"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


@st.cache_data(ttl=300)
def load_ticker_windows() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM ticker_windows", conn)
    conn.close()
    df["window_label"] = df["window_name"].map(WINDOW_LABELS)
    df["sector_label"] = df["asset_class"].map(SECTOR_LABELS).fillna(df["asset_class"])
    return df


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="War Market Analysis",
    page_icon="📈",
    layout="wide",
)

st.title("War Market Analysis")
st.markdown("**US-Iran conflicts 2025–2026 — market impact across asset classes**")

# ── Load data ────────────────────────────────────────────────────────────────

df = load_ticker_windows()

all_windows = WINDOW_ORDER
all_sectors = sorted(df["asset_class"].dropna().unique().tolist())

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")

    selected_windows = st.multiselect(
        "Conflict windows",
        options=all_windows,
        default=all_windows,
        format_func=lambda w: WINDOW_LABELS[w],
    )

    selected_sectors = st.multiselect(
        "Sectors",
        options=all_sectors,
        default=all_sectors,
        format_func=lambda s: SECTOR_LABELS.get(s, s),
    )

# ── Filter ───────────────────────────────────────────────────────────────────

filtered = df[
    df["window_name"].isin(selected_windows) 
    & df["asset_class"].isin(selected_sectors)
]

if filtered.empty:
    st.warning("No data for the current filter selection.")
    st.stop()

# ── Chart 1: Sector comparison — avg % change per asset class per window ─────

st.subheader("Sector Performance by Window")

sector_avg = (
    filtered.groupby(["window_name", "window_label", "sector_label"], sort=False)["pct_change"]
    .mean()
    .round(2)
    .reset_index()
    .rename(columns={"pct_change": "avg_pct_change"})
)

# Chronological window order on x-axis
sector_avg["window_name"] = pd.Categorical(
    sector_avg["window_name"], categories=WINDOW_ORDER, ordered=True
)
sector_avg = sector_avg.sort_values("window_name")

# Sector order: highest global avg first → lowest (most negative) last
sector_global_avg = (
    sector_avg.groupby("sector_label")["avg_pct_change"].mean().sort_values(ascending=False)
)
sector_order = sector_global_avg.index.tolist()

fig = px.bar(
    sector_avg,
    x="window_label",
    y="avg_pct_change",
    color="sector_label",
    barmode="group",
    category_orders={"sector_label": sector_order},
    color_discrete_map=SECTOR_COLORS,
    labels={
        "window_label":   "Conflict Window",
        "avg_pct_change": "Avg % Change",
        "sector_label":   "Sector",
    },
)

fig.update_layout(
    xaxis_tickangle=-10,
    legend_title_text="Sector",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(
        title_text="",
        zeroline=True,
        zerolinecolor="gray",
        zerolinewidth=1,
    ),
    margin=dict(t=60),
    hoverlabel=dict(
        font_size=14,
        font_family="Arial, sans-serif",
        )
)

# Y-axis label as horizontal annotation (avoids unreadable 90° rotation)
fig.add_annotation(
    text="Avg % Change",
    xref="paper", yref="paper",
    x=-0.01, y=1.07,
    showarrow=False,
    font=dict(size=13),
    xanchor="right",
)

st.plotly_chart(fig, use_container_width=True)

# ── Chart 2: Normalized price overlay ────────────────────────────────────────

st.subheader("Normalized Price Overlay (100 = Conflict Start)")

# Keep only tickers belonging to the selected sectors
price_sector = prices_df[prices_df["asset_class"].isin(selected_sectors)].copy()

# Snapshot adj_close on the conflict start date — this becomes the rebase denominator
rebase = (
    price_sector[price_sector["date"] == CONFLICT_START][["ticker", "adj_close"]]
    .rename(columns={"adj_close": "rebase_price"})
)

# Attach rebase prices and compute normalized index (100 = conflict start)
price_sector = price_sector.merge(rebase, on="ticker", how="inner")
price_sector["normalized"] = (
    price_sector["adj_close"] / price_sector["rebase_price"] * 100
).round(2)

# Trim to the visible window date range
price_sector = price_sector[
    (price_sector["date"] >= date_min) & (price_sector["date"] <= date_max)
]

# Sector daily average of normalized prices → one smooth line per sector
sector_norm = (
    price_sector.groupby(["date", "sector_label"])["normalized"]
    .mean()
    .round(2)
    .reset_index()
)

# Line chart: one trace per sector, colored consistently
fig2 = px.line(
    sector_norm,
    x="date",
    y="normalized",
    color="sector_label",
    color_discrete_map=SECTOR_COLORS,
    labels={
        "date":         "Date",
        "normalized":   "Normalized Price",
        "sector_label": "Sector",
    },
)

# Draw vertical timeline markers only for events within the visible range
for ts, label in EVENT_DATES:
    if date_min <= ts <= date_max:
        fig2.add_vline(
            x=ts.value // 10**6,
            line_dash="dash",
            line_color="gray",
            annotation_text=label,
            annotation_position="top right",
            annotation_font_size=11,
        )

# Dotted reference line at 100 (= conflict start level)
fig2.add_hline(
    y=100,
    line_dash="dot",
    line_color="rgba(180,180,180,0.4)",
    line_width=1,
)

# Style: transparent background, consistent with other charts
fig2.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend_title_text="Sector",
    yaxis=dict(title_text=""),
    margin=dict(t=60),
    hoverlabel=dict(font_size=14, font_family="Arial, sans-serif"),
)

# Y-axis label as horizontal annotation (avoids unreadable 90° rotation)
fig2.add_annotation(
    text="Normalized Price (100 = conflict start)",
    xref="paper", yref="paper",
    x=0, y=1.06,
    showarrow=False,
    font=dict(size=13),
    xanchor="left",
)

st.plotly_chart(fig2, use_container_width=True)

# ── Chart 3: VIX spike ───────────────────────────────────────────────────────

st.subheader("VIX Volatility Index")

# Isolate VIX rows and trim to the visible window date range
vix_df = prices_df[
    (prices_df["ticker"] == "^VIX")
    & (prices_df["date"] >= date_min)
    & (prices_df["date"] <= date_max)
].copy()

if not vix_df.empty:
    # Line chart for VIX daily close
    fig3 = px.line(
        vix_df,
        x="date",
        y="adj_close",
        labels={"date": "Date", "adj_close": "VIX"},
    )

    # Draw vertical timeline markers only for events within the visible range
    for ts, label in EVENT_DATES:
        if date_min <= ts <= date_max:
            fig3.add_vline(
                x=ts.value // 10**6,
                line_dash="dash",
                line_color="#E74C3C",
                annotation_text=label,
                annotation_position="top right",
                annotation_font_size=11,
            )

    # Style the VIX line — sky blue stands out against red event markers
    fig3.update_traces(line_color="#5DADE2", line_width=2)

    # Style: transparent background, consistent with other charts
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            title_text="",
            zeroline=False,
        ),
        margin=dict(t=60),
        hoverlabel=dict(font_size=14, font_family="Arial, sans-serif"),
    )

    # Y-axis label as horizontal annotation (avoids unreadable 90° rotation)
    fig3.add_annotation(
        text="VIX Level",
        xref="paper", yref="paper",
        x=-0.05, y=1.07,
        showarrow=False,
        font=dict(size=13),
        xanchor="left",
    )

    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No VIX data for the selected window range.")

