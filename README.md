# Luxury Goods: Asking Prices vs Retail for SouthPark Mall Brands on Rebag

DTSC 3602 (Fall 2026) group project.

**Research question:** How accurately can brand, item type, condition, and age predict the asking-price-to-estimated-retail-price ratio of luxury goods from SouthPark Mall brands listed on Rebag, compared with a brand-level median benchmark?

The target is based on Rebag's **advertised asking prices**, not completed sales, so it describes how items are listed, not what buyers paid.

## Data

We collected 25,000 listings on **October 20, 2026** from Rebag's public product feed ([shop.rebag.com/products.json](https://shop.rebag.com/products.json)). The site's `robots.txt` does not block this feed. The file is a snapshot of every listing for sale that day.

| File | Rows | What it is |
| --- | --- | --- |
| [`data/sample_200_rows.csv`](data/sample_200_rows.csv) | 200 | Preview of the cleaned training data that GitHub shows as a table |
| [`data/rebag_all_listings.csv`](https://raw.githubusercontent.com/ebut11/dtsc3602-luxury-resale/main/data/rebag_all_listings.csv) | 25,000 | Raw listings, all brands (6.8 MB; downloads instead of previewing) |
| [`data/clean/southpark_listings_clean.csv`](https://raw.githubusercontent.com/ebut11/dtsc3602-luxury-resale/main/data/clean/southpark_listings_clean.csv) | 15,863 | Cleaned SouthPark-brand listings, with a `split` column |
| [`data/clean/train.csv`](https://raw.githubusercontent.com/ebut11/dtsc3602-luxury-resale/main/data/clean/train.csv) | 12,557 | Rows for analysis and model development (1,839 with a target) |
| `data/clean/test.csv` | 3,306 | **Final test set. Do not open or use until D6** (464 with a target) |
| [`data/clean/cleaning_log.csv`](data/clean/cleaning_log.csv) | 5 | Rows removed or changed at each cleaning step |

- **[Data dictionary](docs/data_dictionary.md):** every column, its type, values and source, plus the cleaning rules.
- **[Audit report](reports/audit_report.md):** completeness and representativeness checks.

### Final test set

The test set is 20% of bag models, chosen at random (seed 3602) so that no model appears in both `train.csv` and `test.csv`. All exploration, plots and model choices use `train.csv` only. The test set is used once, in D6, to evaluate the frozen model and the brand-median benchmark.

### Known limitations

- Prices are advertised asking prices, not completed sales. Older listings may include markdowns.
- Only 14.5% of rows have an estimated retail price, and all of them are partner (dropship) listings.
- `estimated_retail_price` is Rebag's estimate and likely reflects today's retail price; the ratio never exceeds 83.3%.
- Production year is only available for Louis Vuitton and Chanel.
- Data is used for coursework only. Rebag is the source of all listing data.

## Running the project

Uses [uv](https://docs.astral.sh/uv/). Install the dependencies with `uv sync`, then:

```
uv run python scripts/clean_data.py data/rebag_all_listings.csv data/clean
uv run python scripts/audit_checks.py data/clean reports/audit_report.md
uv run python scripts/build_excel.py data/clean docs/data_dictionary.md rebag_southpark_brands.xlsx
```

`build_excel.py` makes a readable Excel workbook (training rows only) with summary, age, data dictionary and cleaning-log tabs.

### EDA figures (D2)

```
uv run python scripts/eda_plots.py data/clean/train.csv reports/figures
```

Writes the five figures in [`reports/figures/`](reports/figures). They use training rows only.

### Dashboard (Supabase + Streamlit + Modal)

**Live dashboard:** https://ebut11--dtsc3602-luxury-dashboard-dashboard.us-east.modal.run

The dashboard reads the cleaned **training** rows from a Supabase table. The test set never goes to Supabase.

1. In a Supabase project, open the SQL Editor and run [`supabase/schema.sql`](supabase/schema.sql). It creates `listings_train` with row level security and read-only public access.
2. Copy `.env.example` to `.env` and fill in your project URL and keys. `.env` is git-ignored, so never commit it.
3. Load the rows: `uv run python scripts/load_supabase.py data/clean/train.csv`
4. Run it locally: `uv run streamlit run app/dashboard.py`
5. Deploy on Modal. This uses only the read-only publishable key:
   ```
   uv run modal secret create supabase-dtsc3602 SUPABASE_URL=... SUPABASE_KEY=...
   uv run modal deploy modal_app.py
   ```

To test without Supabase, set `LOCAL_CSV=data/clean/train.csv` before step 4. The page then says the data source is a local CSV.

To collect a fresh copy of the raw data (results will differ, since Rebag's inventory changes daily):

```
uv run python scripts/crawl_shopify.py https://shop.rebag.com raw/rebag
uv run python scripts/parse_rebag.py raw/rebag data
```

`crawl_shopify.py` downloads the feed 250 listings per page, waiting 1.5 seconds between requests. Shopify stops at page 100, so the crawl returns up to 25,000 listings. `parse_rebag.py` turns the raw pages into the CSV.

## AI disclosure

The data collection, cleaning and audit scripts were written with Claude Code (Anthropic), within the course AI policy.
