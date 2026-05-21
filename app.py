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
    return df


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="War Market Analysis",
    page_icon="📈",
    layout="wide",
)

st.title("War Market Analysis")
st.caption("US-Iran conflicts 2025–2026 — market impact across asset classes")

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
    )

# ── Filter ───────────────────────────────────────────────────────────────────

filtered = df[
    df["window_name"].isin(selected_windows) & df["asset_class"].isin(selected_sectors)
]

if filtered.empty:
    st.warning("No data for the current filter selection.")
    st.stop()

# ── Chart 1: Sector comparison — avg % change per asset class per window ─────

st.subheader("Sector Performance by Window")

sector_avg = (
    filtered.groupby(["window_name", "window_label", "asset_class"], sort=False)["pct_change"]
    .mean()
    .round(2)
    .reset_index()
    .rename(columns={"pct_change": "avg_pct_change"})
)

# Preserve chronological window order
sector_avg["window_name"] = pd.Categorical(
    sector_avg["window_name"], categories=WINDOW_ORDER, ordered=True
)
sector_avg = sector_avg.sort_values("window_name")

fig = px.bar(
    sector_avg,
    x="window_label",
    y="avg_pct_change",
    color="asset_class",
    barmode="group",
    labels={
        "window_label": "Window",
        "avg_pct_change": "Avg % Change",
        "asset_class": "Sector",
    },
    color_discrete_sequence=px.colors.qualitative.Safe,
)

fig.update_layout(
    xaxis_tickangle=-20,
    legend_title_text="Sector",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=1),
)

st.plotly_chart(fig, use_container_width=True)
