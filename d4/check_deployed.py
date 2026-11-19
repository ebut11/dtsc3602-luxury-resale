"""Verify the deployed Modal API matches the local saved pipeline.

Run from the repository root:  uv run python -m d4.check_deployed [API_URL]
Writes d4/local_vs_deployed.csv and exits non-zero on any mismatch.
"""
import sys
from pathlib import Path

import httpx
import pandas as pd
from fastapi.testclient import TestClient

from d4.api import app

URL = sys.argv[1] if len(sys.argv) > 1 else "https://ebut11--luxury-resale-d4-web.us-east.modal.run"
OUT = Path(__file__).with_name("local_vs_deployed.csv")

VALID_CASES = [
    {"brand": "Gucci", "item_type": "Handbag", "condition": "Very Good", "age_band": None, "estimated_retail_price": 2000},
    {"brand": "Louis Vuitton", "item_type": "Handbag", "condition": "Excellent", "age_band": "6-10", "estimated_retail_price": 2030},
    {"brand": "Louis Vuitton", "item_type": "Handbag", "condition": "Fair", "age_band": "Over 20", "estimated_retail_price": 1690},
    {"brand": "Chanel", "item_type": "Handbag", "condition": "Pristine", "age_band": "5 or less", "estimated_retail_price": 10800},
    {"brand": "Chanel", "item_type": "Handbag", "condition": "Pristine", "age_band": "5 or less", "estimated_retail_price": 2000},
    {"brand": "Saint Laurent", "item_type": "Handbag", "condition": "Great", "age_band": None, "estimated_retail_price": 2350},
    {"brand": "Tiffany & Co.", "item_type": "Jewelry", "condition": "Excellent", "age_band": None, "estimated_retail_price": 14800},
    {"brand": "Omega", "item_type": "Watch", "condition": "Good", "age_band": None, "estimated_retail_price": 6500},
    {"brand": "Balenciaga", "item_type": "Shoes", "condition": "Great", "age_band": None, "estimated_retail_price": 1150},
    {"brand": "Gucci", "item_type": "Handbag", "condition": "Very Good", "age_band": None, "estimated_retail_price": 500000},
]
INVALID_CASES = [
    {**VALID_CASES[0], "brand": "Prada"},
    {**VALID_CASES[0], "condition": "Mint"},
    {**VALID_CASES[0], "estimated_retail_price": -5},
]


def main():
    rows, ok = [], True
    with TestClient(app) as local, httpx.Client(base_url=URL, timeout=90) as remote:
        info_local, info_remote = local.get("/pipeline/info").json(), remote.get("/pipeline/info").json()
        same_build = info_local["built_at"] == info_remote["built_at"]
        print(f"artifact built_at  local={info_local['built_at']}  deployed={info_remote['built_at']}  match={same_build}")
        print(f"scikit-learn       local={info_local['server_sklearn_version']}  deployed={info_remote['server_sklearn_version']}")
        ok &= same_build and info_local["server_sklearn_version"] == info_remote["server_sklearn_version"]

        for case in VALID_CASES + INVALID_CASES:
            a, b = local.post("/predict", json=case), remote.post("/predict", json=case)
            match = a.status_code == b.status_code and (a.status_code != 200 or a.json() == b.json())
            ok &= match
            rows.append({
                **case,
                "local_status": a.status_code, "deployed_status": b.status_code,
                "local_pct": a.json().get("predicted_percentage") if a.status_code == 200 else None,
                "deployed_pct": b.json().get("predicted_percentage") if b.status_code == 200 else None,
                "identical": match,
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(df[["brand", "item_type", "condition", "age_band", "estimated_retail_price",
              "local_status", "deployed_status", "local_pct", "deployed_pct", "identical"]].to_string(index=False))
    print("\nALL MATCH" if ok else "\nMISMATCH FOUND")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
