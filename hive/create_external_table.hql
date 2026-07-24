-- ========================================================================
-- create_external_table.hql
-- Part VIII: Hive Integration
--
-- Creates an EXTERNAL Hive table that reads directly from the existing
-- HBase 'retail_events' table via the HBaseStorageHandler. No data is
-- copied — Hive queries hit HBase live. This is proven in Part IX
-- (see hive/analytics.hql, Integration Validation section).
-- ========================================================================

CREATE EXTERNAL TABLE retail_events_hive (
  row_key         STRING,
  transaction_id  STRING,
  event_timestamp STRING,
  payment_type    STRING,
  loyalty_flag    STRING,
  product_id      STRING,
  product_name    STRING,
  category        STRING,
  store_id        STRING,
  store_city      STRING,
  province        STRING,
  store_region    STRING,
  quantity        STRING,
  unit_price      STRING,
  discount_amount STRING,
  final_price     STRING,
  promotion_flag  STRING,
  promotion_id    STRING
)
STORED BY 'org.apache.hadoop.hive.hbase.HBaseStorageHandler'
WITH SERDEPROPERTIES (
  "hbase.columns.mapping" =
  ":key,transaction:transaction_id,transaction:event_timestamp,transaction:payment_type,transaction:loyalty_flag,product:product_id,product:product_name,product:category,store:store_id,store:city,store:province,store:region,sales:quantity,sales:unit_price,sales:discount_amount,sales:final_price,sales:promotion_flag,sales:promotion_id"
)
TBLPROPERTIES ("hbase.table.name" = "retail_events");

-- All columns are typed STRING because HBase stores everything as raw
-- bytes; numeric casting (CAST(... AS DOUBLE/INT)) happens at query time
-- in analytics.hql rather than in the table definition, to avoid silent
-- failures on any value that isn't perfectly numeric.

-- Verify row count matches the ingestion total (38,143):
SELECT COUNT(*) FROM retail_events_hive;

-- Spot-check a handful of rows:
SELECT * FROM retail_events_hive LIMIT 5;
