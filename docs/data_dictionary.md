# Data dictionary

Source column legend: **R** = real (UCI Online Retail II), **D** = derived from real data, **S** = synthetic (seed 42), **P** = public calendar (gov.uk).

## sales (fact, one row per cleaned invoice line)
| Column | Type | Src | Description |
|---|---|---|---|
| transaction_id | int | D | Row id |
| invoice_id | text | R | Invoice number |
| invoice_ts / date | timestamp | R | Invoice time / day |
| customer_id | int, nullable | R | Customer ID (null for guest orders) |
| product_id | int | D | FK → products |
| region_id | int | D | FK → regions (from Country) |
| quantity | int | R | Units |
| unit_price | float | R | Price in GBP |
| revenue | float | D | quantity × unit_price |
| discount_pct | float | D | max(0, 1 − unit_price / product median price) |
| campaign_id | int, nullable | S | Synthetic campaign active for that region group, category and date |

## products
product_id, stock_code (R), product_name (R, most frequent description), category (D, keyword rules), base_price (D, median price), pack_size (S).

## regions
region_id, country (R), region_group (D, geographic grouping), market_type (S).

## customers
customer_id (R), first_purchase_date (D), region_id (D, most frequent country).

## campaigns (all S)
campaign_id, campaign_name, channel, campaign_type, start_date, end_date, budget (GBP), target_region_group, target_category.

## calendar
date, year, month, quarter, week, week_start, weekday, is_weekend (D); holiday_flag (P, UK bank holidays); is_pre_christmas (D).
