# Luxury Goods: Which SouthPark Mall Items Retain Their Value Over Time?

DTSC 3602 (Fall 2026) group project.

**Research question:** For luxury goods from brands sold in SouthPark Mall in Charlotte, NC, how well do brand, item type, condition and age predict resale value retention, compared with using the brand's median?

## Dataset

- **Preview in the browser:** [`data/sample_200_rows.csv`](data/sample_200_rows.csv), 200 SouthPark-brand rows that GitHub shows as a table.
- **Full dataset (6.8 MB):** [download `rebag_all_listings.csv`](https://raw.githubusercontent.com/ebut11/dtsc3602-luxury-resale/main/data/rebag_all_listings.csv). GitHub can't preview a file this large, so it downloads instead. It opens in Excel.

[`data/rebag_all_listings.csv`](data/rebag_all_listings.csv) has 25,000 resale listings collected on **October 20, 2026** from Rebag's public product feed ([shop.rebag.com/products.json](https://shop.rebag.com/products.json)). The site's `robots.txt` does not block this feed. The file is a snapshot of every listing for sale that day. About 88% were first posted in September–October 2026, and the rest were posted between August 2024 and August 2026.

| Count | Listings |
| --- | --- |
| All listings | 25,000 |
| Brands sold at SouthPark (`southpark_brand = True`) | 15,888 |
| SouthPark brands with an estimated retail price | 2,317 |
| SouthPark brands with a decoded production year | 5,197 |

### Columns

| Column | Description |
| --- | --- |
| `listing_id` | Rebag product ID |
| `brand` | Designer |
| `southpark_brand` | True if the brand has a store at SouthPark Mall |
| `model` | Item model name |
| `item_type` | Handbag, Jewelry, Accessory, Shoes, Apparel, Watch |
| `product_type` | Rebag's finer category (Totes, Wallets, ...) |
| `condition` | Rebag grade: Fair, Good, Very Good, Great, Excellent, Pristine |
| `resale_price` | Rebag asking price, USD |
| `estimated_retail_price` | Rebag's estimated retail price, USD (blank when not listed) |
| `value_retention_pct` | **Target:** resale_price / estimated_retail_price x 100 |
| `production_year` | Decoded from Louis Vuitton date codes, Chanel serial numbers ([Rebag's chart](https://rebag.com/magazine/chanel-101-serial-codes)) or Hermès stamps |
| `item_age_years` | 2026 minus production_year |
| `year_source` | How the year was decoded. "2021 or later" means a microchipped item, with 2021 used as its year |
| `brand_code` | Raw date code or serial from the listing |
| `exterior_material`, `exterior_color`, `hardware_color` | Item details |
| `accessories` | Extras included (dust bag, strap, authenticity card, ...). Blank means unknown, not none |
| `size` | Size tag, when given |
| `available` | Whether the item was still for sale at collection |
| `listed_at` | Date Rebag first posted the listing |
| `dropship_partner` | True for partner listings, which have shorter descriptions |
| `url` | Link to the listing |

### Known limitations

- Prices are asking prices, not final sale prices. Older listings may include markdowns.
- `estimated_retail_price` is Rebag's estimate and likely reflects today's retail price, not the original purchase price.
- Production year is only available for Louis Vuitton, Chanel and Hermès.
- Data is used for coursework only. Rebag is the source of all listing data.

## Reproducing the data

Requires Python 3 with pandas and xlsxwriter.

```
python scripts/crawl_shopify.py https://shop.rebag.com raw/rebag
python scripts/parse_rebag.py raw/rebag data
```

`crawl_shopify.py` downloads the feed 250 listings per page, waiting 1.5 seconds between requests. Shopify stops at page 100, so the crawl returns up to 25,000 listings. `parse_rebag.py` turns the raw pages into the CSV. A new crawl will return different listings, since Rebag's inventory changes daily.

## AI disclosure

The data collection and cleaning scripts were written with Claude Code (Anthropic), within the course AI policy.
