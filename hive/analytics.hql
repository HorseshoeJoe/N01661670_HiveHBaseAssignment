-- ========================================================================
-- analytics.hql
-- All HiveQL analytical queries used across Parts IX-XIV, XXI.
-- Run against retail_events_hive (see create_external_table.hql).
--
-- NOTE: avoid window functions (OVER()) against this table — the HBase
-- storage handler does not push WHERE filters down efficiently under
-- window functions and queries can hang for a very long time. Where a
-- percentage/ratio is needed, compute it in Python after a plain
-- GROUP BY instead (see python/analytics.py).
-- ========================================================================


-- ========================================================================
-- PART IX — Integration Validation (mandatory proof)
-- Run AFTER inserting the test record directly into HBase
-- (see hbase/validation_commands.txt)
-- ========================================================================

-- Record count before/after comparison
SELECT COUNT(*) FROM retail_events_hive;

-- Confirm the HBase-only insert is visible in Hive
SELECT * FROM retail_events_hive WHERE store_id = 'ST-TEST-999';

-- After deleting the test record from HBase, re-run the count query
-- above again to confirm it drops back to 38143.


-- ========================================================================
-- PART X — Store Performance Analytics
-- ========================================================================

-- Total sales, transaction count, and quantity by store
SELECT
  store_id,
  ROUND(SUM(CAST(final_price AS DOUBLE)), 2) AS total_sales,
  COUNT(DISTINCT transaction_id) AS transaction_count,
  SUM(CAST(quantity AS INT)) AS total_quantity
FROM retail_events_hive
GROUP BY store_id
ORDER BY total_sales DESC;

-- Average transaction value — CORRECT two-step method.
-- retail_events.csv is product-level; averaging final_price directly
-- would understate real transaction value. Collapse to transaction
-- totals first, then average those totals per store.

CREATE VIEW transaction_totals AS
SELECT
  transaction_id,
  store_id,
  SUM(CAST(final_price AS DOUBLE)) AS transaction_total
FROM retail_events_hive
GROUP BY transaction_id, store_id;

SELECT
  store_id,
  ROUND(AVG(transaction_total), 2) AS avg_transaction_value,
  COUNT(*) AS transaction_count
FROM transaction_totals
GROUP BY store_id
ORDER BY avg_transaction_value DESC;


-- ========================================================================
-- PART XI — Product Category Analytics
-- ========================================================================

SELECT
  category,
  ROUND(SUM(CAST(final_price AS DOUBLE)), 2) AS total_sales,
  SUM(CAST(quantity AS INT)) AS total_quantity
FROM retail_events_hive
GROUP BY category
ORDER BY total_sales DESC;

-- Percentage of total sales per category is calculated in Python
-- (python/analytics.py) from these totals, rather than via OVER()
-- in Hive, for performance reasons noted above.


-- ========================================================================
-- PART XII — Regional Analytics
-- ========================================================================

SELECT
  store_region,
  ROUND(SUM(CAST(final_price AS DOUBLE)), 2) AS total_sales,
  COUNT(DISTINCT transaction_id) AS transaction_count,
  SUM(CAST(quantity AS INT)) AS total_quantity,
  ROUND(SUM(CAST(final_price AS DOUBLE)) / COUNT(DISTINCT transaction_id), 2) AS avg_transaction_value
FROM retail_events_hive
GROUP BY store_region
ORDER BY total_sales DESC;


-- ========================================================================
-- PART XIII — Time-Based Analytics
-- ========================================================================

SELECT
  HOUR(event_timestamp) AS hour_of_day,
  COUNT(DISTINCT transaction_id) AS transaction_count
FROM retail_events_hive
GROUP BY HOUR(event_timestamp)
ORDER BY hour_of_day;


-- ========================================================================
-- PART XIV — Promotion Analysis
-- ========================================================================

SELECT
  promotion_flag,
  SUM(CAST(quantity AS INT)) AS total_quantity,
  ROUND(SUM(CAST(final_price AS DOUBLE)), 2) AS total_sales,
  ROUND(AVG(CAST(final_price AS DOUBLE)), 2) AS avg_item_value,
  COUNT(DISTINCT transaction_id) AS transaction_count
FROM retail_events_hive
GROUP BY promotion_flag;


-- ========================================================================
-- PART XIX — Integrated Investigation follow-up queries (Calgary)
-- Plain GROUP BY only — deliberately avoids OVER() for performance;
-- percentages computed in Python (python/analytics.py).
-- ========================================================================

-- Calgary's category mix, to compare against Part XI's network-wide mix
SELECT
  category,
  ROUND(SUM(CAST(final_price AS DOUBLE)), 2) AS calgary_sales
FROM retail_events_hive
WHERE store_id = 'ST-CAL-001'
GROUP BY category
ORDER BY calgary_sales DESC;

-- Calgary's promotion ratio, to compare against Part XIV's network-wide ratio
SELECT
  promotion_flag,
  COUNT(*) AS event_count,
  ROUND(AVG(CAST(quantity AS INT)), 2) AS avg_quantity
FROM retail_events_hive
WHERE store_id = 'ST-CAL-001'
GROUP BY promotion_flag;


-- ========================================================================
-- PART XXI — Product Demand Analysis
-- ========================================================================

-- Top 10 highest-demand products
SELECT
  product_id,
  product_name,
  SUM(CAST(quantity AS INT)) AS total_quantity
FROM retail_events_hive
GROUP BY product_id, product_name
ORDER BY total_quantity DESC
LIMIT 10;

-- Top 10 lowest-demand products
SELECT
  product_id,
  product_name,
  SUM(CAST(quantity AS INT)) AS total_quantity
FROM retail_events_hive
GROUP BY product_id, product_name
ORDER BY total_quantity ASC
LIMIT 10;
