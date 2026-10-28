# Data Dictionary

Cleaned data: `data/clean/southpark_listings_clean.csv` (15,863 rows, one row per Rebag listing from a SouthPark Mall brand), made by `scripts/clean_data.py` from `data/rebag_all_listings.csv`. `data/clean/train.csv` and `data/clean/test.csv` hold the same columns.

- **Source:** Rebag's public product feed ([shop.rebag.com/products.json](https://shop.rebag.com/products.json)), collected October 20, 2026.
- **Unit of observation:** one listing (one physical item offered for sale).
- **Target:** `asking_price_ratio`. Prices are advertised asking prices, not completed sales.

| Column | Type | Description | Values / example | Source |
| --- | --- | --- | --- | --- |
| `listing_id` | integer | Rebag product ID, unique per row | 9139741884593 | Feed |
| `split` | text | `train` (development) or `test` (final test, unused until D6) | train | Derived |
| `brand` | text | Designer, limited to brands with a SouthPark store | Louis Vuitton | Feed `vendor` |
| `model` | text | Model name from the listing | Speedy Handbag Monogram Multicolor 30 | Feed description |
| `model_group` | text | Brand + model, lowercased; used to keep each model in one split | Louis Vuitton \| speedy handbag monogram multicolor 30 | Derived |
| `item_type` | text | Broad category | Handbag, Jewelry, Accessory, Apparel, Shoes, Watch | Feed tags |
| `product_type` | text | Rebag's finer category | Totes, Wallets, Bracelet | Feed |
| `condition` | text | Rebag's condition grade | Fair, Good, Very Good, Great, Excellent, Pristine | Feed description or tags |
| `condition_rank` | integer | Condition as a number, 1 = Fair to 6 = Pristine | 4 | Derived |
| `asking_price` | number | Advertised asking price, USD | 1260.0 | Feed |
| `estimated_retail_price` | number | Rebag's estimated retail price, USD; blank when not shown | 1950.0 | Feed description |
| `asking_price_ratio` | number | **Target.** asking_price ÷ estimated_retail_price × 100 | 64.6 (listed at 64.6% of estimated retail) | Derived |
| `has_target` | boolean | True when `asking_price_ratio` is available | True | Derived |
| `production_year` | integer | Year the item was made | 2016 | Decoded from `brand_code` |
| `item_age_years` | integer | 2026 − production_year | 10 | Derived |
| `age_band` | text | Age group | 5 or less, 6-10, 11-20, Over 20 | Derived |
| `year_is_lower_bound` | boolean | True for microchipped items: made 2021 or later, so age is at most 5 | False | Derived |
| `year_source` | text | How the year was decoded | LV date code, Chanel serial, LV/Chanel microchip (2021 or later) | Derived |
| `brand_code` | text | Raw date code or serial from the listing | SD1146, 24719517, NFC Only | Feed description |
| `accessories` | text | Extras included with the item; "Unknown" when the listing doesn't say | Dust Bag, With Strap | Feed description |
| `accessories_known` | boolean | False when the listing doesn't list extras | True | Derived |
| `has_dust_bag` | boolean | Dust bag included; blank when extras are unknown | True | Derived |
| `has_strap` | boolean | Any strap included (with, extra, detachable, chain); blank when unknown | True | Derived |
| `has_authenticity_card` | boolean | Authenticity card included; blank when unknown | False | Derived |
| `exterior_material` | text | Main material | Canvas Coated, Leather | Feed description |
| `exterior_color` | text | Main color | Brown | Feed description |
| `hardware_color` | text | Hardware color | Gold | Feed description |
| `size` | text | Size tag, when given | Small, MM, 25 | Feed tags |
| `available` | boolean | Still for sale at collection | True | Feed |
| `listed_at` | date | Date Rebag first posted the listing | 2026-09-16 | Feed `created_at` |
| `days_listed` | integer | Days between `listed_at` and collection (October 20, 2026) | 34 | Derived |
| `recent` | boolean | Posted September 1 – October 20, 2026 | True | Derived |
| `dropship_partner` | boolean | Listed by a partner seller rather than Rebag itself | True | Feed tags |
| `possible_duplicate` | boolean | Microchipped item with the same model, price and condition as another row; may be one item listed twice | False | Derived |
| `url` | text | Link to the listing | https://shop.rebag.com/products/… | Feed |

## Cleaning rules

Applied in `scripts/clean_data.py`; row counts are in `data/clean/cleaning_log.csv`.

1. Keep brands with a store at SouthPark Mall (25,000 → 15,888 rows).
2. Drop items graded "Outlet", which are new outlet stock rather than resale listings (−21).
3. Drop duplicate relistings: same brand, model, date code, asking price and condition; keep the earliest (−4).
4. Flag, but keep, microchipped lookalikes that may be duplicates (97 rows).
5. Blank the retail price and target where the ratio is under 5%, which signals a bad retail estimate (1 row).
6. Fill blank accessories with "Unknown" and leave the yes/no accessory columns blank for those rows.
7. Reserve 20% of model groups as the final test set (seed 3602).
