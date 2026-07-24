import csv
import base64
import sys
from datetime import datetime

import requests

# Configuration
HDP_IP = "10.118.12.193"
REST_PORT = 60080
TABLE_NAME = "retail_events"
BASE_URL = f"http://{HDP_IP}:{REST_PORT}"

DATA_DIR = "data"
RETAIL_EVENTS_CSV = f"{DATA_DIR}/retail_events.csv"
MALFORMED_EVENTS_CSV = f"{DATA_DIR}/malformed_retail_events.csv"
STORES_CSV = f"{DATA_DIR}/stores.csv"
PRODUCTS_CSV = f"{DATA_DIR}/products.csv"

BATCH_SIZE = 200          # rows per REST PUT request
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
REVERSE_TS_CEILING = 99_999_999_999_999   # 14 nines, larger than any real epoch-ms value

# Column family mapping: (csv_field -> "family:qualifier")
FIELD_TO_COLUMN = {
    "transaction_id":   "transaction:transaction_id",
    "event_timestamp":  "transaction:event_timestamp",
    "payment_type":     "transaction:payment_type",
    "loyalty_flag":     "transaction:loyalty_flag",
    "product_id":       "product:product_id",
    "product_name":     "product:product_name",
    "category":         "product:category",
    "store_id":         "store:store_id",
    "store_city":       "store:city",
    "province":         "store:province",
    "store_region":     "store:region",
    "quantity":         "sales:quantity",
    "unit_price":       "sales:unit_price",
    "discount_amount":  "sales:discount_amount",
    "final_price":      "sales:final_price",
    "promotion_flag":   "sales:promotion_flag",
    "promotion_id":     "sales:promotion_id",
}

MANDATORY_FIELDS = [
    "event_id", "transaction_id", "store_id", "event_timestamp",
    "product_id", "quantity", "unit_price", "final_price",
]

NUMERIC_FIELDS = ["quantity", "unit_price", "discount_amount", "final_price"]


# ----------------------------------------------------------------------
# REFERENCE DATA (for unknown store / unknown product validation)
# ----------------------------------------------------------------------
def load_reference_ids(path, id_field):
    """Load a set of valid IDs from a reference CSV (stores.csv / products.csv)."""
    ids = set()
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get(id_field):
                    ids.add(row[id_field].strip())
    except FileNotFoundError:
        print(f"WARNING: reference file not found: {path} "
              f"(skipping {id_field} cross-validation)")
    return ids


# ----------------------------------------------------------------------
# VALIDATION
# ----------------------------------------------------------------------
def validate_record(row, valid_store_ids, valid_product_ids):
    """
    Validate a single CSV record.
    Returns (is_valid: bool, reason: str or None)
    """
    # 1. Mandatory fields present
    for field in MANDATORY_FIELDS:
        if not row.get(field, "").strip():
            return False, f"missing mandatory field: {field}"

    # 2. Numeric fields must parse as numbers and be non-negative
    for field in NUMERIC_FIELDS:
        value = row.get(field, "").strip()
        try:
            num = float(value)
            if num < 0:
                return False, f"negative value in {field}: {value}"
            if field == "quantity" and num == 0:
                return False, f"quantity cannot be zero"
        except ValueError:
            return False, f"invalid numeric value in {field}: '{value}'"

    # 3. Timestamp must be parseable
    ts_raw = row.get("event_timestamp", "").strip()
    try:
        datetime.strptime(ts_raw, TIMESTAMP_FORMAT)
    except ValueError:
        return False, f"invalid timestamp format: '{ts_raw}'"

    # 4. Store must be known (only checked if reference data loaded)
    store_id = row.get("store_id", "").strip()
    if valid_store_ids and store_id not in valid_store_ids:
        return False, f"unknown store_id: '{store_id}'"

    # 5. Product must be known (only checked if reference data loaded)
    product_id = row.get("product_id", "").strip()
    if valid_product_ids and product_id not in valid_product_ids:
        return False, f"unknown product_id: '{product_id}'"

    return True, None


# ----------------------------------------------------------------------
# ROW KEY GENERATION
# ----------------------------------------------------------------------
def build_row_key(row):
    """store_id#reverse_timestamp#event_id"""
    dt = datetime.strptime(row["event_timestamp"].strip(), TIMESTAMP_FORMAT)
    epoch_ms = int(dt.timestamp() * 1000)
    reverse_ts = REVERSE_TS_CEILING - epoch_ms
    return f"{row['store_id'].strip()}#{reverse_ts:014d}#{row['event_id'].strip()}"


# ----------------------------------------------------------------------
# HBASE REST HELPERS
# ----------------------------------------------------------------------
def b64(value: str) -> str:
    return base64.b64encode(str(value).encode("utf-8")).decode("ascii")


def build_cell_row(row_key, row):
    """Build one 'Row' entry (HBase REST CellSet JSON format) for a record."""
    cells = []
    for csv_field, column in FIELD_TO_COLUMN.items():
        value = row.get(csv_field, "")
        if value is None:
            value = ""
        cells.append({"column": b64(column), "$": b64(value)})
    return {"key": b64(row_key), "Cell": cells}


def put_batch(session, rows_payload):
    """Send a batch of rows to HBase via REST. Returns True on success."""
    url = f"{BASE_URL}/{TABLE_NAME}/fake-row-key"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    body = {"Row": rows_payload}
    resp = session.put(url, json=body, headers=headers, timeout=30)
    return resp.status_code in (200, 201)


# ----------------------------------------------------------------------
# MAIN INGESTION
# ----------------------------------------------------------------------
def ingest(csv_path):
    valid_store_ids = load_reference_ids(STORES_CSV, "store_id")
    valid_product_ids = load_reference_ids(PRODUCTS_CSV, "product_id")

    processed = 0
    inserted = 0
    rejected = 0
    errors = []

    batch = []
    session = requests.Session()

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed += 1
            is_valid, reason = validate_record(row, valid_store_ids, valid_product_ids)

            if not is_valid:
                rejected += 1
                errors.append({
                    "event_id": row.get("event_id", "<missing>"),
                    "reason": reason,
                })
                continue

            row_key = build_row_key(row)
            batch.append(build_cell_row(row_key, row))

            if len(batch) >= BATCH_SIZE:
                if put_batch(session, batch):
                    inserted += len(batch)
                else:
                    rejected += len(batch)
                    errors.append({"event_id": "<batch>", "reason": "HBase PUT failed"})
                batch = []

        # flush remaining rows
        if batch:
            if put_batch(session, batch):
                inserted += len(batch)
            else:
                rejected += len(batch)
                errors.append({"event_id": "<batch>", "reason": "HBase PUT failed"})

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n===== INGESTION SUMMARY =====")
    print(f"Source file:        {csv_path}")
    print(f"Records processed:  {processed}")
    print(f"Records inserted:   {inserted}")
    print(f"Records rejected:   {rejected}")
    print(f"Distinct error types logged: {len(errors)}")

    if errors:
        print("\nSample rejected records (up to 15 shown):")
        for e in errors[:15]:
            print(f"  event_id={e['event_id']:<15} reason={e['reason']}")

    return {
        "processed": processed,
        "inserted": inserted,
        "rejected": rejected,
        "errors": errors,
    }


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else RETAIL_EVENTS_CSV
    print(f"Starting ingestion from: {target}")
    ingest(target)
