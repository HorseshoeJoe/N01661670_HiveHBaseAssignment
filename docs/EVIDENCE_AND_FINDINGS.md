# Evidence & Findings
## Loblaw Retail Operations and Customer Shopping Analytics Platform

This document consolidates the evidence, results, and business findings produced across the
assignment, cross-referenced to the relevant screenshots (in `screenshots/`) and Zeppelin
notebook sections (in `zeppelin/loblaw_retail_analytics.json`).

---

## Part I — Environment Validation
Ambari confirmed HDFS, HBase, Hive, and Zeppelin all running (green "Started"). HBase shell,
Hive View, Zeppelin UI, and Python runtimes verified accessible.
*Screenshots: 'docs/screenshots.docx'*

## Parts II–IV — HBase Data Model, Row-Key Design, Table Creation
Table `retail_events` created with four column families (`transaction`, `product`, `store`,
`sales`). Row key format `store_id#reverse_timestamp#event_id`, verified with `list` and
`describe 'retail_events'`.
*Screenshot evidence: `create`, `list`, `describe` output.*
*Full rationale: Zeppelin notebook Sections 05–06.*

## Part V — Python Data Ingestion
`python/load_hbase.py` run against `retail_events.csv` via HBase REST API:

| Metric | Value |
|---|---|
| Records processed | 38,143 |
| Records inserted | 38,143 |
| Records rejected | 0 |

## Part VI — Error Handling
Run against `malformed_retail_events.csv`:

| Metric | Value |
|---|---|
| Records processed | 2 |
| Records inserted | 0 |
| Records rejected | 2 |

| Validation Rule | Rejected Record | Reason |
|---|---|---|
| Mandatory field check | EVT-BAD-0001 | missing mandatory field: transaction_id |
| Numeric validity check | EVT-BAD-0002 | negative value in quantity: -1 |

## Part VII — HBase Validation
`scan 'retail_events', {LIMIT => 10}` and targeted `get`/`scan` by row key confirmed correct
data and row-key structure, e.g. row `ST-BRA-001#98215146838999#EVT-0003` with all four
column families populated.

## Part VIII — Hive Integration
External table `retail_events_hive` created over the HBase table via
`HBaseStorageHandler`. `SELECT COUNT(*)` returned **38,143**, matching the ingestion total
exactly.

## Part IX — Integration Validation (mandatory)
A record was inserted **directly into HBase only**, for store `ST-TEST-999`. Hive's count
rose from 38,143 → 38,144 without any Hive-side load, and querying by `store_id =
'ST-TEST-999'` returned exactly the values written via HBase (nulls elsewhere, as expected
for a sparsely-populated row). The record was then deleted from HBase, and Hive's count
returned to 38,143. **This proves Hive is reading live from HBase, not a separate copy.**

## Part X — Store Performance

**Total sales (top 5):** ST-CAL-001 $55,573.77 · ST-TOR-001 $54,080.88 · ST-TOR-002
$49,425.30 · ST-OTT-001 $48,425.04 · ST-MIS-001 $47,075.34

**Avg transaction value (top 5):** ST-CAL-001 $47.62 · ST-TOR-002 $42.94 · ST-OTT-002 $42.64
· ST-HAM-001 $42.51 · ST-SCA-001 $42.44

**Finding:** Calgary leads both total sales and avg transaction value despite fewer
transactions than Toronto — value-driven, not volume-driven.

## Part XI — Product Category

| Category | Total Sales | % of Total |
|---|---|---|
| Grocery | $171,287.76 | 31.74% |
| Produce | $73,399.93 | 13.60% |
| Dairy | $70,165.09 | 13.00% |
| Household | $61,643.25 | 11.42% |
| Frozen | $60,305.89 | 11.17% |
| Bakery | $41,660.92 | 7.72% |
| Meat | $32,212.84 | 5.97% |
| Personal Care | $29,055.27 | 5.38% |

## Part XII — Regional Analysis

| Region | Total Sales | Transactions | Avg Txn Value |
|---|---|---|---|
| Central | $349,345.03 | 8,367 | $41.75 |
| Western | $101,882.22 | 2,261 | $45.06 |
| Eastern | $88,503.70 | 2,097 | $42.20 |

**Finding:** Western leads on avg transaction value despite the fewest transactions,
reinforcing the Calgary (Western) pattern from Part X.

## Part XIII — Time-Based Analysis
Activity spans hours 8–21 only. Peak: **6PM, 1,809 transactions**. Low point: 8AM, 239
transactions. Sharp decline after 7PM.

**Staffing implication:** scale up from 1PM, peak coverage 4–7PM, scale down after 8PM.

## Part XIV — Promotion Analysis

| | Quantity | Total Sales | Avg Item Value | Transactions |
|---|---|---|---|---|
| Non-promoted (N) | 57,261 | $522,320.56 | $14.10 | 12,686 |
| Promoted (Y) | 1,675 | $17,410.39 | $15.74 | 1,081 |

**Finding:** promoted items show a higher avg item value — likely because promotions run
more often on higher-priced categories. No causal claim is made.

## Part XV — Python Statistical Analysis
Transaction count: 12,725 · Mean: $42.42 · Median: $37.55 · Min: $1.85 · Max: $201.09 ·
Std Dev: $27.08

**Interpretation:** Mean > Median indicates a right-skewed distribution — a small number of
high-value transactions pull the average up. Median is the more representative "typical
transaction" figure.

## Part XVI — Transaction Distribution
Histogram confirms right-skew visually: peak density $25–$35, long tail extending past
$150–$200. Most transactions fall in the $15–$60 range.

## Part XVII — Outlier Detection
Z-score analysis on store-level average transaction value: **ST-CAL-001 is the sole outlier**
(z = 2.87, threshold ±2). All other 11 stores fall within a tight band (z from -1.05 to
+0.31).

## Part XVIII — Product Demand

**Top 10:** Large Eggs 12 (1,836) · 2% Milk 4L (1,819) · Tomato Sauce (1,816) · Peanut
Butter 1kg (1,813) · Olive Oil 1L (1,811) · Avocados 5pk (1,806) · Canned Beans (1,795) ·
Cheddar Cheese 400g (1,781) · Orange Juice 2.5L (1,781) · Bananas (1,760)

**Bottom 10:** Body Wash (867) · Dish Soap (897) · Chicken Breast (900) · Muffins 6pk (901)
· Bacon 500g (902) · Tortillas 10pk (907) · French Fries 1kg (907) · Hand Soap (911) ·
Frozen Vegetables 750g (925) · Frozen Pizza (928)

**Finding:** demand is broadly distributed (narrow top/bottom ranges), not concentrated in a
few hit products.

## Part XIX — Integrated Business Investigation: Calgary

| Stage | Result |
|---|---|
| Hive | Flagged Calgary's high avg transaction value (Part X) |
| Python | Confirmed statistically via Z-score (z = 2.87, Part XVII) |
| Zeppelin | Visualized as an isolated outlier bar chart |
| HBase | Retrieved Calgary's operational event records via store-first row-key scan |
| Analysis | Tested product-mix hypothesis (ruled out — categories match network average
  within ±0.6pp) and promotion-frequency hypothesis (ruled out — 3.0% vs 2.8% network-wide) |
| Business Recommendation | Monitor over a longer window; capture additional variables
  (basket size, customer segment) for future investigation |

---

## Summary of Key Findings

1. **Calgary generates the highest average transaction value** despite below-average
   transaction volume — confirmed as a statistical outlier; product mix and promotion
   frequency both ruled out as causes.
2. **Grocery dominates category sales** at 31.74%, more than double the next category.
3. **Transaction activity peaks sharply at 6PM** (1,809 transactions), with a clear
   staffing/checkout-capacity implication for the 4–7PM window.
4. **Transaction values are right-skewed** (mean $42.42 > median $37.55) — median is the
   more representative benchmark.
5. **Product demand is broadly distributed**, not concentrated — top/bottom 10 ranges are
   both narrow, suggesting replenishment-cadence tuning over SKU cuts.

## Summary of Business Recommendations

1. Investigate and potentially replicate Calgary's transaction-value drivers with additional
   data collection.
2. Align staffing and checkout capacity with the confirmed 4–7PM peak window.
3. Prioritize supply chain reliability for Grocery, Produce, and Dairy (~58% of sales).
4. Use median, not mean, transaction value as the primary cross-store performance benchmark.
5. Expand data collection (stockout/shelf data, controlled promotional tests) before
   automating inventory or promotion decisions.

*Full narrative, all queries, and complete interpretations are in
`zeppelin/loblaw_retail_analytics.json` (Sections 01–25).*
