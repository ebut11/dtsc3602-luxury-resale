"""Load the cleaned training rows into Supabase.

Usage: uv run python scripts/load_supabase.py data/clean/train.csv

Needs SUPABASE_URL and SUPABASE_SECRET_KEY in .env (never commit it). Run supabase/schema.sql first.
Safe to re-run: rows are upserted on listing_id.
"""
import math
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
if not url or not key:
    sys.exit("Set SUPABASE_URL and SUPABASE_SECRET_KEY in .env (see .env.example).")

df = pd.read_csv(sys.argv[1]).drop(columns=["split"])
INTS = ["condition_rank", "production_year", "item_age_years", "days_listed"]


def clean(v):
    # JSON has no NaN; send missing values as null
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


records = []
for row in df.to_dict(orient="records"):
    rec = {k: clean(v) for k, v in row.items()}
    for c in INTS:
        if rec[c] is not None:
            rec[c] = int(rec[c])
    records.append(rec)

client = create_client(url, key)
BATCH = 500
for i in range(0, len(records), BATCH):
    client.table("listings_train").upsert(records[i:i + BATCH], on_conflict="listing_id").execute()
    print(f"loaded {min(i + BATCH, len(records)):,} / {len(records):,}", flush=True)

count = client.table("listings_train").select("listing_id", count="exact").limit(1).execute().count
print(f"done: listings_train now has {count:,} rows")
