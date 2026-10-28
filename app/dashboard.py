"""D2 dashboard: explore asking-price ratios for SouthPark Mall brands on Rebag.

Reads the cleaned training rows from Supabase (table listings_train).
Run locally:  uv run streamlit run app/dashboard.py
Local testing without Supabase: set LOCAL_CSV=data/clean/train.csv
"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Luxury Asking Prices", page_icon="👜", layout="wide")

# Validated categorical slots (light mode reference palette), fixed per brand
BRAND_COLOR = {"Louis Vuitton": "#2a78d6", "Gucci": "#eb6834", "Chanel": "#1baf7a", "Saint Laurent": "#eda100",
               "Balenciaga": "#e87ba4", "Burberry": "#008300", "Tiffany & Co.": "#6250d6", "Dolce & Gabbana": "#e34948"}
OTHER = "#8a8984"
MAIN_FOUR = ["Louis Vuitton", "Gucci", "Chanel", "Saint Laurent"]
GRADE = {"Fair": "Fair–Good", "Good": "Fair–Good", "Very Good": "Very Good", "Great": "Great",
         "Excellent": "Excellent–Pristine", "Pristine": "Excellent–Pristine"}
GRADES = ["Fair–Good", "Very Good", "Great", "Excellent–Pristine"]
AGE_BANDS = ["5 or less", "6-10", "11-20", "Over 20"]
MIN_N = 30


@st.cache_data(ttl=3600, show_spinner="Loading listings from Supabase…")
def load() -> tuple[pd.DataFrame, str]:
    local = os.environ.get("LOCAL_CSV")
    if local:
        return pd.read_csv(local), "local CSV (testing only)"
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    rows, start, page = [], 0, 1000
    while True:  # Supabase returns at most 1,000 rows per request
        chunk = client.table("listings_train").select("*").range(start, start + page - 1).execute().data
        rows += chunk
        if len(chunk) < page:
            break
        start += page
    return pd.DataFrame(rows), "Supabase"


def style(fig, height=380, xtitle=None, ytitle=None):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", hovermode="closest", legend=dict(orientation="h", y=-0.2),
                      xaxis_title=xtitle, yaxis_title=ytitle, font=dict(size=13))
    fig.update_xaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False)
    return fig


def color(brand):
    return BRAND_COLOR.get(brand, OTHER)


try:
    df, source = load()
except Exception as e:  # keep the page usable and say what went wrong
    st.error(f"Couldn't load data from Supabase: {e}")
    st.stop()
if df.empty:
    st.warning("No rows returned. Has scripts/load_supabase.py been run?")
    st.stop()

df["grade"] = df.condition.map(GRADE)
df["listed_at"] = pd.to_datetime(df.listed_at)

# ---------- Header and filters ----------
st.title("Luxury asking prices on Rebag")
st.caption("SouthPark Mall brands · Rebag listings collected Oct 20, 2026 · cleaned training rows only · "
           f"data source: {source}")
st.info("**Asking price ratio** = advertised asking price ÷ Rebag's estimated retail price × 100. These are listing "
        "prices from partner sellers, **not completed sales**.", icon="ℹ️")

brands_all = df.brand.value_counts().index.tolist()
c1, c2, c3, c4 = st.columns([3, 2, 2, 1.4])
brands = c1.multiselect("Brands", brands_all, default=[b for b in MAIN_FOUR if b in brands_all])
types = c2.multiselect("Item type", sorted(df.item_type.dropna().unique()), default=["Handbag"])
grades = c3.multiselect("Condition", GRADES, default=GRADES)
recent_only = c4.toggle("Recent listings only", help="Posted Sep 1 – Oct 20, 2026 (removes likely markdowns)")

f = df[df.brand.isin(brands) & df.item_type.isin(types) & df.grade.isin(grades)]
if recent_only:
    f = f[f.recent]
t = f[f.has_target]
if not brands or not types:
    st.warning("Pick at least one brand and one item type.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Listings", f"{len(f):,}")
k2.metric("With a retail price", f"{len(t):,}", f"{len(t) / max(len(f), 1):.0%} of listings", delta_color="off")
k3.metric("Median asking price ratio", f"{t.asking_price_ratio.median():.1f}%" if len(t) else "—")
k4.metric("Median asking price", f"${f.asking_price.median():,.0f}" if len(f) else "—")
if 0 < len(t) < MIN_N:
    st.warning(f"Only {len(t)} listings with a retail price match these filters, so the medians are unreliable.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Brand", "Condition", "Age", "Coverage", "Data"])

# ---------- Brand ----------
with tab1:
    st.subheader("Asking price ratio by brand")
    st.caption("Box = middle 50% of listings, line = median. Brands with fewer than 30 listings are greyed and marked.")
    order = t.groupby("brand").asking_price_ratio.median().sort_values().index
    fig = go.Figure()
    for b in order:
        s = t.loc[t.brand == b, "asking_price_ratio"]
        small = len(s) < MIN_N
        fig.add_trace(go.Box(x=s, name=f"{b} (n={len(s)}){' ⚠' if small else ''}", orientation="h",
                             marker_color=OTHER if small else color(b), boxpoints=False, line_width=1.5,
                             hovertemplate=f"<b>{b}</b><br>%{{x:.1f}}%<extra></extra>"))
    fig.update_layout(showlegend=False)
    st.plotly_chart(style(fig, 60 + 55 * max(len(order), 1), "Asking price, % of estimated retail"), width="stretch")

# ---------- Condition ----------
with tab2:
    st.subheader("Median ratio by condition")
    st.caption("Good is combined with Fair and Pristine with Excellent, since each has few listings on its own.")
    fig = go.Figure()
    for b in order:
        g = t[t.brand == b].groupby("grade").asking_price_ratio.agg(["median", "size"]).reindex(GRADES)
        fig.add_trace(go.Scatter(x=GRADES, y=g["median"], name=b, mode="lines+markers",
                                 line=dict(color=color(b), width=2.5), marker=dict(size=10, line=dict(width=2, color="white")),
                                 customdata=g["size"].fillna(0), connectgaps=False,
                                 hovertemplate=f"<b>{b}</b><br>%{{x}}: %{{y:.1f}}%<br>%{{customdata:.0f}} listings<extra></extra>"))
    st.plotly_chart(style(fig, 420, None, "Median asking price, % of retail"), width="stretch")

# ---------- Age ----------
with tab3:
    st.subheader("Median ratio by item age")
    aged = t[t.age_band.notna()]
    if aged.empty:
        st.info("Age is only known for Louis Vuitton and Chanel. Add one of them to the brand filter.")
    else:
        st.caption("Age comes from Louis Vuitton date codes and Chanel serial numbers. Microchipped items (2021 or later) "
                   "fall in '5 or less'. Hover for the number of listings in each point.")
        fig = go.Figure()
        for b in aged.brand.unique():
            g = aged[aged.brand == b].groupby("age_band").asking_price_ratio.agg(
                median="median", q1=lambda s: s.quantile(0.25), q3=lambda s: s.quantile(0.75), n="size").reindex(AGE_BANDS)
            fig.add_trace(go.Scatter(x=["5 or less", "6–10", "11–20", "Over 20"], y=g["median"], name=b,
                                     mode="lines+markers", line=dict(color=color(b), width=2.5),
                                     marker=dict(size=10, line=dict(width=2, color="white")),
                                     error_y=dict(type="data", symmetric=False, array=g.q3 - g["median"],
                                                  arrayminus=g["median"] - g.q1, color=color(b), thickness=1.5, width=0),
                                     customdata=g.n.fillna(0),
                                     hovertemplate=f"<b>{b}</b><br>%{{x}} years: %{{y:.1f}}%<br>%{{customdata:.0f}} listings<extra></extra>"))
        st.plotly_chart(style(fig, 420, "Item age (years) · bars show the middle 50%", "Asking price, % of retail"),
                        width="stretch")

# ---------- Coverage ----------
with tab4:
    st.subheader("Where the target and age exist")
    st.caption("All brands and item types in the training data, ignoring the filters above. "
               "This is why the analysis focuses on Louis Vuitton, Gucci, Chanel and Saint Laurent handbags.")
    cov = (df.groupby("brand").agg(listings=("listing_id", "size"), with_target=("has_target", "sum"),
                                   with_age=("item_age_years", "count")).sort_values("listings"))
    fig = go.Figure()
    fig.add_trace(go.Bar(y=cov.index, x=cov.listings, orientation="h", name="All listings", marker_color="#d8d7d2",
                         hovertemplate="%{y}: %{x:,} listings<extra></extra>"))
    fig.add_trace(go.Bar(y=cov.index, x=cov.with_target, orientation="h", name="With a retail price", marker_color="#2a78d6",
                         hovertemplate="%{y}: %{x:,} with a retail price<extra></extra>"))
    fig.update_layout(barmode="overlay")
    st.plotly_chart(style(fig, 460, "Training listings"), width="stretch")
    tm = df[df.has_target].groupby("recent").asking_price_ratio.agg(["median", "size"])
    if len(tm) == 2:
        st.markdown(f"**Time on market:** listings posted before September 2026 have a median ratio of "
                    f"**{tm.loc[False, 'median']:.1f}%** ({tm.loc[False, 'size']:,} listings) versus "
                    f"**{tm.loc[True, 'median']:.1f}%** for recent ones ({tm.loc[True, 'size']:,}), consistent with markdowns.")

# ---------- Data ----------
with tab5:
    st.subheader("Filtered listings")
    cols = ["brand", "model", "item_type", "condition", "asking_price", "estimated_retail_price", "asking_price_ratio",
            "item_age_years", "accessories", "listed_at", "url"]
    st.dataframe(f[cols].sort_values("asking_price_ratio", ascending=False), width="stretch", hide_index=True,
                 column_config={"url": st.column_config.LinkColumn("Listing"),
                                "asking_price": st.column_config.NumberColumn("Asking price", format="$%d"),
                                "estimated_retail_price": st.column_config.NumberColumn("Est. retail", format="$%d"),
                                "asking_price_ratio": st.column_config.NumberColumn("Ratio %", format="%.1f"),
                                "listed_at": st.column_config.DateColumn("Listed")})
    st.download_button("Download these rows as CSV", f[cols].to_csv(index=False), "filtered_listings.csv", "text/csv")

st.caption("Data: Rebag public product feed · Code: github.com/ebut11/dtsc3602-luxury-resale · DTSC 3602, Fall 2026")
