"""Build a readable Excel workbook from the cleaned data.

Usage: python scripts/build_excel.py data/clean docs/data_dictionary.md out.xlsx

Uses training rows only, so the reserved test set stays out of the workbook.
"""
import os
import re
import sys

import pandas as pd

clean_dir, dict_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
df = pd.read_csv(os.path.join(clean_dir, "train.csv"))
log = pd.read_csv(os.path.join(clean_dir, "cleaning_log.csv"))

summary = (df.groupby(["brand", "item_type"])
             .agg(listings=("listing_id", "size"), with_target=("has_target", "sum"),
                  median_asking_price=("asking_price", "median"),
                  median_estimated_retail_price=("estimated_retail_price", "median"),
                  median_asking_price_ratio=("asking_price_ratio", "median"))
             .reset_index().sort_values(["brand", "listings"], ascending=[True, False]))
by_age = (df[df.age_band.notna()]
            .groupby(["brand", "item_type", "age_band"])
            .agg(listings=("listing_id", "size"), with_target=("has_target", "sum"),
                 median_asking_price=("asking_price", "median"),
                 median_asking_price_ratio=("asking_price_ratio", "median"))
            .reset_index())
by_age["age_band"] = pd.Categorical(by_age.age_band, ["5 or less", "6-10", "11-20", "Over 20"], ordered=True)
by_age = by_age.sort_values(["brand", "item_type", "age_band"])

# Data dictionary sheet from the markdown table in docs/data_dictionary.md
rows = [l for l in open(dict_path, encoding="utf-8") if l.startswith("| `")]
dictionary = pd.DataFrame([[c.strip().strip("`").replace("\\|", "|") for c in re.split(r"(?<!\\)\|", r)[1:-1]] for r in rows],
                          columns=["Column", "Type", "Description", "Values / Example", "Source"])

def title(c):
    words = {"pct": "%", "id": "ID", "url": "URL"}
    return " ".join(words.get(w, w.capitalize()) for w in c.split("_"))

sheets = {
    "Read Me": pd.DataFrame({"About this workbook": [
        "Rebag listings from SouthPark Mall brands, collected October 20, 2026, after cleaning.",
        "Training rows only (12,557). The final test set is kept out of this workbook until D6.",
        "Asking Price Ratio % = asking price / estimated retail price x 100. These are advertised asking prices, not completed sales.",
        "Only listings with an estimated retail price have a ratio; all of them are partner (dropship) listings.",
        "Source data, scripts and the full audit report: https://github.com/ebut11/dtsc3602-luxury-resale"]}),
    "Summary": summary, "Ratio by Age": by_age, "Listings": df.drop(columns=["split"]),
    "Data Dictionary": dictionary, "Cleaning Log": log,
}

with pd.ExcelWriter(out, engine="xlsxwriter") as w:
    wrap = w.book.add_format({"text_wrap": True, "valign": "top"})
    for name, d in sheets.items():
        d = d.copy()
        if name not in ("Data Dictionary", "Read Me"):
            d.columns = [title(c) for c in d.columns]
        d = d.rename(columns={"Asking Price Ratio": "Asking Price Ratio %", "Median Asking Price Ratio": "Median Asking Price Ratio %"})
        d.to_excel(w, sheet_name=name, index=False, startrow=1, header=False)
        ws = w.sheets[name]
        ws.add_table(0, 0, len(d), len(d.columns) - 1,
                     {"columns": [{"header": c} for c in d.columns], "style": "Table Style Medium 2"})
        for i, c in enumerate(d.columns):
            width = max(len(str(c)), d[c].astype(str).str.len().quantile(0.9)) + 2
            ws.set_column(i, i, min(width, 60), wrap if name in ("Data Dictionary", "Read Me", "Cleaning Log") else None)
        ws.freeze_panes(1, 1 if name not in ("Read Me",) else 0)
print(f"wrote {out}: " + ", ".join(f"{k} ({len(v)})" for k, v in sheets.items()))
