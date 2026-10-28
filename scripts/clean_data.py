"""Audit and clean the Rebag listings, then reserve the final test set.

Usage: python scripts/clean_data.py data/rebag_all_listings.csv data/clean

Writes:
  <out>/southpark_listings_clean.csv   every cleaned SouthPark-brand row, with a `split` column
  <out>/train.csv                      rows for model development (D2-D5)
  <out>/test.csv                       final test set: do not open until D6
  <out>/cleaning_log.csv               rows removed or changed at each step
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

src, out = sys.argv[1], sys.argv[2]
COLLECTED = pd.Timestamp("2026-10-20")
RECENT_FROM = pd.Timestamp("2026-09-01")
SEED = 3602

# Rebag's condition scale, worst to best
CONDITION_RANK = {"Fair": 1, "Good": 2, "Very Good": 3, "Great": 4, "Excellent": 5, "Pristine": 6}
STRAPS = {"With Strap", "Extra Strap", "Detachable Strap", "Chain Strap"}

log = []

def step(name, before, after, note):
    log.append({"step": name, "rows_before": before, "rows_after": after, "rows_affected": before - after, "note": note})


raw = pd.read_csv(src)
df = raw[raw.southpark_brand].drop(columns="southpark_brand").copy()
step("Keep SouthPark brands", len(raw), len(df), "Brands with a store at SouthPark Mall")

# 1. "Outlet" is Rebag's label for new outlet stock, not a used-condition grade
n = len(df)
df = df[df.condition != "Outlet"]
step("Drop Outlet items", n, len(df), "New outlet stock, not resale listings")

# 2. Same physical item listed twice by a partner seller: identical date code, model, price and condition.
#    Only real date codes count; microchipped items share "NFC Only", so they can't be matched safely.
df["brand_code"] = df.brand_code.replace(r"(?i)^nfc\s*only$", "NFC Only", regex=True)
df = df.sort_values("listed_at")
same_listing = df.duplicated(["brand", "model", "brand_code", "asking_price", "condition"], keep="first")
real_code = df.brand_code.notna() & ~df.brand_code.isin(["NFC Only", "No Code"])
n = len(df)
df = df[~(real_code & same_listing)]
step("Drop duplicate relistings", n, len(df), "Same brand, model, date code, price and condition; kept the earliest")

# Microchipped lookalikes (same model, price, condition, "NFC Only") may be one item listed twice: flag, don't drop
nfc_twins = (df.brand_code == "NFC Only") & df.duplicated(["brand", "model", "asking_price", "condition", "brand_code"], keep=False)
df["possible_duplicate"] = nfc_twins
log.append({"step": "Flag possible duplicates", "rows_before": len(df), "rows_after": len(df),
            "rows_affected": int(nfc_twins.sum()), "note": "Microchipped items with identical model, price and condition"})

# 3. Implausible retail estimates (ratio under 5%) -> treat the retail price as missing
bad_retail = df.asking_price_ratio < 5
df.loc[bad_retail, ["estimated_retail_price", "asking_price_ratio"]] = np.nan
log.append({"step": "Blank implausible retail prices", "rows_before": len(df), "rows_after": len(df),
            "rows_affected": int(bad_retail.sum()), "note": "Ratio under 5% (e.g. a $871,750 retail estimate on a necklace)"})

# 4. Derived columns
df["condition_rank"] = df.condition.map(CONDITION_RANK)
df["year_is_lower_bound"] = df.year_source.str.contains("2021 or later", na=False)
df["age_band"] = pd.cut(df.item_age_years, [-1, 5, 10, 20, 100], labels=["5 or less", "6-10", "11-20", "Over 20"])
df["days_listed"] = (COLLECTED - pd.to_datetime(df.listed_at)).dt.days
df["recent"] = pd.to_datetime(df.listed_at) >= RECENT_FROM

acc = df.accessories.fillna("").str.split(r",\s*")
df["accessories_known"] = df.accessories.notna()
df["has_dust_bag"] = acc.apply(lambda a: "Dust Bag" in a)
df["has_strap"] = acc.apply(lambda a: bool(STRAPS & set(a)))
df["has_authenticity_card"] = acc.apply(lambda a: "Authenticity Card" in a)
for col in ["has_dust_bag", "has_strap", "has_authenticity_card"]:
    df[col] = df[col].where(df.accessories_known)  # blank accessories = unknown, not "none"
df["accessories"] = df.accessories.fillna("Unknown")
df["has_target"] = df.asking_price_ratio.notna()

# 5. Final test set: 20% of bag models, so the same model never appears in both train and test
df["model_group"] = (df.brand + " | " + df.model.str.lower().str.replace(r"\s+", " ", regex=True).str.strip())
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
train_idx, test_idx = next(gss.split(df, groups=df.model_group))
df["split"] = "train"
df.iloc[test_idx, df.columns.get_loc("split")] = "test"

order = ["listing_id", "split", "brand", "model", "model_group", "item_type", "product_type", "condition", "condition_rank",
         "asking_price", "estimated_retail_price", "asking_price_ratio", "has_target", "production_year", "item_age_years",
         "age_band", "year_is_lower_bound", "year_source", "brand_code", "accessories", "accessories_known", "has_dust_bag",
         "has_strap", "has_authenticity_card", "exterior_material", "exterior_color", "hardware_color", "size", "available",
         "listed_at", "days_listed", "recent", "dropship_partner", "possible_duplicate", "url"]
df = df[order].sort_values(["brand", "listing_id"]).reset_index(drop=True)

os.makedirs(out, exist_ok=True)
df.to_csv(os.path.join(out, "southpark_listings_clean.csv"), index=False, encoding="utf-8-sig")
df[df.split == "train"].to_csv(os.path.join(out, "train.csv"), index=False, encoding="utf-8-sig")
df[df.split == "test"].to_csv(os.path.join(out, "test.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(log).to_csv(os.path.join(out, "cleaning_log.csv"), index=False)

print(pd.DataFrame(log).to_string(index=False))
print(df.groupby("split").agg(rows=("listing_id", "size"), with_target=("has_target", "sum"),
                              with_target_and_age=("item_age_years", lambda s: int((s.notna() & df.loc[s.index, "has_target"]).sum())),
                              models=("model_group", "nunique")).to_string())
print("model groups in both splits:", len(set(df[df.split == "train"].model_group) & set(df[df.split == "test"].model_group)))
