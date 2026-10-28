"""D2 exploratory plots, from training rows only.

Usage: python scripts/eda_plots.py data/clean/train.csv reports/figures
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

# Validated categorical slots (dataviz reference palette, light mode), assigned per brand in fixed order
BRAND_COLOR = {"Louis Vuitton": "#2a78d6", "Gucci": "#eb6834", "Chanel": "#1baf7a", "Saint Laurent": "#eda100"}
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#a3a29c", "#e6e5e1", "#ffffff"
MAIN = "#2a78d6"
FOUR = list(BRAND_COLOR)
CONDITIONS = ["Fair", "Good", "Very Good", "Great", "Excellent", "Pristine"]
AGE_BANDS = ["5 or less", "6-10", "11-20", "Over 20"]
MIN_N = 30

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK_2,
    "xtick.color": INK_2, "ytick.color": INK_2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.dpi": 200, "savefig.bbox": "tight",
})

df = pd.read_csv(src)
tt = df[df.has_target]
bags = tt[tt.item_type == "Handbag"]


def finish(fig, ax, title, subtitle, name, source="Source: Rebag partner listings, collected Oct 20, 2026 (training rows)"):
    # Anchored in points from the plot area, so spacing holds at any figure height
    where = ("figure fraction", "axes fraction")
    ax.annotate(title, xy=(0.01, 1), xycoords=where, xytext=(0, 30), textcoords="offset points",
                fontsize=13, fontweight="bold", color=INK, ha="left", va="bottom")
    ax.annotate(subtitle, xy=(0.01, 1), xycoords=where, xytext=(0, 12), textcoords="offset points",
                fontsize=10, color=INK_2, ha="left", va="bottom")
    ax.annotate(source, xy=(0.01, 0), xycoords=where, xytext=(0, -48), textcoords="offset points",
                fontsize=8, color=MUTED, ha="left", va="top")
    fig.savefig(os.path.join(out, name))
    plt.close(fig)


# 1. Where the target and age exist, by brand
cov = (df.groupby("brand").agg(rows=("listing_id", "size"), target=("has_target", "sum"),
                               age_and_target=("item_age_years", lambda s: int((s.notna() & df.loc[s.index, "has_target"]).sum())))
         .sort_values("rows"))
fig, ax = plt.subplots(figsize=(8, 5))
y = range(len(cov))
ax.barh(y, cov.rows, color=GRID, height=0.7, label="All listings")
ax.barh(y, cov.target, color=MAIN, height=0.7, label="With a retail price (target)")
ax.barh(y, cov.age_and_target, color="#184f95", height=0.7, label="With target and age")
for i, (_, r) in enumerate(cov.iterrows()):
    ax.text(r.rows + 60, i, f"{r.target:,.0f} of {r.rows:,.0f} ({r.target / r.rows:.0%})", va="center", fontsize=8.5, color=INK_2)
ax.set_yticks(list(y), cov.index)
ax.set_xlabel("Training listings")
ax.set_xlim(0, cov.rows.max() * 1.3)
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right", frameon=False, fontsize=9)
finish(fig, ax, "Only 15% of listings have a retail price, and age only exists for two brands",
       "Training listings by brand: all, with a target, and with both target and age", "fig1_coverage.png",
       source="Source: Rebag listings, collected Oct 20, 2026 (training rows)")

# 2. Ratio by brand, handbags
order = bags.groupby("brand").asking_price_ratio.median().sort_values().index
counts = bags.brand.value_counts()
order = [b for b in order if counts[b] >= 5]
fig, ax = plt.subplots(figsize=(8, 4.6))
data = [bags.loc[bags.brand == b, "asking_price_ratio"] for b in order]
bp = ax.boxplot(data, orientation="horizontal", widths=0.55, patch_artist=True, showfliers=False,
                medianprops={"color": INK, "linewidth": 2}, whiskerprops={"color": INK_2}, capprops={"color": INK_2})
for patch, b in zip(bp["boxes"], order):
    small = counts[b] < MIN_N
    patch.set(facecolor=GRID if small else "#cde2fb", edgecolor=MUTED if small else MAIN, linewidth=1.2)
for i, b in enumerate(order, 1):
    med = bags.loc[bags.brand == b, "asking_price_ratio"].median()
    ax.text(86, i, f"median {med:.0f}%  ·  n = {counts[b]}" + ("  (small)" if counts[b] < MIN_N else ""),
            va="center", fontsize=8.5, color=INK_2)
ax.set_yticks(range(1, len(order) + 1), order)
ax.set_xlim(0, 120)
ax.set_xticks(range(0, 101, 20))
ax.set_xlabel("Asking price as % of estimated retail")
ax.grid(axis="y", visible=False)
finish(fig, ax, "Handbags are listed at about 60–65% of retail for the big four brands",
       "Asking-price ratio for handbags by brand (box = middle 50%, line = median; grey = under 30 listings)", "fig2_brand.png")

# 3. Ratio by condition, four main brands (handbags)
# Good and Pristine are too thin on their own, so they join their neighbouring grade
GRADE = {"Fair": "Fair–Good", "Good": "Fair–Good", "Very Good": "Very Good", "Great": "Great",
         "Excellent": "Excellent–Pristine", "Pristine": "Excellent–Pristine"}
GRADES = ["Fair–Good", "Very Good", "Great", "Excellent–Pristine"]
cond = bags.assign(grade=bags.condition.map(GRADE))
fig, ax = plt.subplots(figsize=(8, 4.6))
x = list(range(len(GRADES)))
ends = []
for b in FOUR:
    g = cond[cond.brand == b].groupby("grade").asking_price_ratio.agg(["median", "size"]).reindex(GRADES)
    ax.plot(x, g["median"], color=BRAND_COLOR[b], linewidth=2, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=2, label=f"{b} (n={int(g['size'].sum())})")
    ends.append((g["median"].iloc[-1], b))
# Direct labels at the right end, nudged apart so they never overlap
ends.sort()
placed = []
for val, b in ends:
    y = max(val, placed[-1] + 1.3) if placed else val
    placed.append(y)
    ax.text(len(GRADES) - 1 + 0.1, y, b, color=INK, fontsize=9, va="center")
ax.set_xticks(x, GRADES)
ax.set_xlim(-0.3, len(GRADES) - 1 + 0.9)
ax.set_ylabel("Median asking price, % of retail")
ax.legend(loc="upper left", frameon=False, fontsize=8.5)
finish(fig, ax, "Better condition generally lifts the asking-price ratio",
       "Median ratio by condition grade, handbags (Good joined with Fair, Pristine with Excellent)", "fig3_condition.png")

# 4. Ratio by age band, Louis Vuitton and Chanel
aged = tt[tt.brand.isin(["Louis Vuitton", "Chanel"]) & tt.age_band.notna()]
fig, ax = plt.subplots(figsize=(8, 4.6))
ns = {}
for k, b in enumerate(["Louis Vuitton", "Chanel"]):
    g = aged[aged.brand == b].groupby("age_band").asking_price_ratio.agg(
        median="median", q1=lambda s: s.quantile(0.25), q3=lambda s: s.quantile(0.75), n="size").reindex(AGE_BANDS)
    ns[b] = g.n.astype(int).tolist()
    xs = [i + (k - 0.5) * 0.18 for i in range(len(AGE_BANDS))]
    ax.vlines(xs, g.q1, g.q3, color=BRAND_COLOR[b], linewidth=2, alpha=0.6)
    ax.plot(xs, g["median"], color=BRAND_COLOR[b], linewidth=2, marker="o", markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=2, label=b)
    ax.text(xs[-1] + 0.12, g["median"].iloc[-1], b, fontsize=9, color=INK, va="center")
# Sample sizes sit under each age band instead of crowding the plot
ax.set_xticks(range(len(AGE_BANDS)),
              [f"{lab}\nLV {lv} · Chanel {ch}" for lab, lv, ch in zip(["5 or less", "6–10", "11–20", "Over 20"], ns["Louis Vuitton"], ns["Chanel"])])
ax.set_xlabel("Item age in years (listings per brand below each band)")
ax.set_ylabel("Asking price, % of retail")
ax.set_xlim(-0.4, len(AGE_BANDS) - 0.2)
ax.legend(loc="lower left", frameon=False, fontsize=9)
finish(fig, ax, "Older Louis Vuitton and Chanel items are listed at lower ratios",
       f"Median (dot) and middle 50% (bar) by age band; Chanel 'Over 20' has only {ns['Chanel'][-1]} listings", "fig4_age.png")

# 5. Time on market
tm = tt.assign(posted=tt.recent.map({True: "Posted Sep–Oct 2026", False: "Posted before Sep 2026"}))
groups = ["Posted before Sep 2026", "Posted Sep–Oct 2026"]
fig, ax = plt.subplots(figsize=(8, 3.4))
bp = ax.boxplot([tm.loc[tm.posted == g, "asking_price_ratio"] for g in groups], orientation="horizontal", widths=0.5,
                patch_artist=True, showfliers=False, medianprops={"color": INK, "linewidth": 2},
                whiskerprops={"color": INK_2}, capprops={"color": INK_2})
for patch, c in zip(bp["boxes"], ["#fbe0d4", "#cde2fb"]):
    patch.set(facecolor=c, edgecolor=INK_2, linewidth=1.2)
for i, g in enumerate(groups, 1):
    s = tm.loc[tm.posted == g]
    ax.text(86, i, f"median {s.asking_price_ratio.median():.0f}%  ·  n = {len(s):,}  ·  {s.days_listed.median():.0f} days listed",
            va="center", fontsize=8.5, color=INK_2)
ax.set_yticks([1, 2], groups)
ax.set_xlim(0, 130)
ax.set_xticks(range(0, 101, 20))
ax.set_xlabel("Asking price as % of estimated retail")
ax.grid(axis="y", visible=False)
finish(fig, ax, "Listings that have sat longer are priced about 7 points lower",
       "Asking-price ratio by when the listing was posted (likely markdowns)", "fig5_time_on_market.png")

print("wrote", sorted(os.listdir(out)))
