# D4 — Fitted Pipeline and API

This API predicts an item's asking price as a percentage of its estimated retail price, plus the matching dollar amount. Predictions are Rebag **asking** prices, not sale prices.

## Live API

- Base URL: https://ebut11--luxury-resale-d4-web.us-east.modal.run
- Documentation: https://ebut11--luxury-resale-d4-web.us-east.modal.run/docs

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Whether the model loaded (`model_loaded`), and the load error if it didn't |
| GET | `/pipeline/info` | Bundle metadata: scikit-learn version, build time, steps, learned transformer state, CV results |
| POST | `/predict` | Predicted percentage and asking price, a `capped` flag and warnings |

## Model and training data

The pipeline is the model selected in D3: ridge regression (alpha=1.0) on brand, item type, condition, age band and log estimated retail price.

- **Training data:** `data/clean/train.csv`. Of 12,557 rows, 1,839 have a recorded asking-price percentage and were used for training.
- **Test set:** the reserved test set is not used. It stays untouched until D6.
- **Accuracy check:** a grouped 5-fold CV (same design as D3) gives **MAE 10.58** versus **12.33** for the brand-median baseline. This matches the D3 result (10.54 vs 12.37).

## Custom transformer

`ResaleFeatures` (`transformers.py`) turns the raw request into model features. It learns its state from the training rows in `fit()`:

- **`retail_bounds_`**: the 1st–99th percentile of retail price. Prices outside this range are clipped before the log, so a very large price can't push the linear model to an impossible ratio.
- **`brand_levels_` / `item_type_levels_`**: categories with at least 10 training rows. Rarer ones (e.g. Omega, Breitling) are pooled into "Other" and share one estimated effect.

In `transform()` it also fills a missing age band with "Unknown" and takes the log of retail price. Next, a one-hot encoder handles the categories, and ridge regression makes the prediction.

## Saved artifact

`resale_pipeline.joblib` is a bundle of `{"pipeline": ..., "metadata": ...}`. The metadata is also written to `metadata.json`.

- **Loading:** the API loads the bundle once when the server starts, and never retrains.
- **Version check:** if the bundle's scikit-learn version doesn't match the server's, the API refuses to serve.

## Validation and errors

| Situation | Response |
|---|---|
| Valid request | **200** |
| Brand, item type, condition or age band not in the allowed list (case-sensitive) | **422** |
| Retail price ≤ 0 or > $500,000 | **422** |
| Missing field, extra field or malformed JSON | **422** |
| Model artifact missing or unloadable | **503** on `/predict` and `/pipeline/info` (`/health` reports why) |

Predictions are capped to the range seen in training (0–83.3%), and `capped: true` says when that happened. Warnings flag rare brands, non-handbags and retail prices outside the training range.

CORS is enabled so the D5 website can call the API from the browser.

## Files

| File | What it does |
|---|---|
| `transformers.py` | Custom transformer |
| `train.py` | Fits the pipeline, runs grouped CV and saves the bundle |
| `resale_pipeline.joblib` | Fitted bundle (pipeline + metadata) |
| `metadata.json` | Readable copy of the bundle metadata |
| `api.py` | FastAPI application |
| `test_api.py` | Local tests for 200, 422 and 503 |
| `check_deployed.py` | Compares local and deployed outputs |
| `local_vs_deployed.csv` | Output of that comparison |
| `modal_app.py` | Modal deployment, with package versions pinned to the local environment |
| `requirements.txt` | Package versions, exported from `uv.lock` |

## Rebuild and run

Run these from the repository root. The project uses uv, and `uv sync` installs everything.

```bash
uv sync
uv run python -m d4.train                    # rebuild d4/resale_pipeline.joblib
uv run uvicorn d4.api:app --reload           # local API, docs at http://127.0.0.1:8000/docs
uv run python -m pytest d4 -q                # tests: 200 / 422 / 503 (503 uses a missing MODEL_PATH locally)
```

If you don't use uv: `python -m pip install -r d4/requirements.txt`, then run the same commands without `uv run`.

## Deploy and verify

```bash
uv run modal deploy d4/modal_app.py          # Windows: set PYTHONUTF8=1 first
uv run python -m d4.check_deployed           # compares local vs deployed and writes local_vs_deployed.csv
```

**Verification (Nov 19, 2026):** 10 valid requests and 3 invalid requests were sent to both the local pipeline and the deployed API.

- All 13 responses were identical: the same status codes and the same predictions.
- Both sides used the same artifact build and scikit-learn 1.9.1.

See `local_vs_deployed.csv`.

## Interpretation

- **Asking prices:** predictions estimate listing asking prices. Actual sale prices may differ.
- **Typical error:** about 10.6 percentage points, so the app should show a range, not just one number.
- **Weaker groups:** D3 found larger errors for small brand groups, Tiffany jewelry and Fair-condition items.
