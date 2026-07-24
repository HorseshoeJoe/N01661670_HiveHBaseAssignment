"""
analytics.py

Loblaw Retail Operations and Customer Shopping Analytics Platform
Part XV-XVIII, XXI - Python Statistical Analysis

Standalone version of the analysis performed in the Zeppelin notebook's
%pyspark paragraphs (zeppelin/loblaw_retail_analytics.json, Sections 18-21).
Reads retail_events.csv directly (no HBase/Hive dependency), so this can
be run and reviewed independently of the live cluster.

Compatible with both Python 2.7 (matches the HDP sandbox's Zeppelin
PySpark interpreter) and Python 3.

Usage:
    python analytics.py ../data/retail_events.csv
"""

from __future__ import print_function

import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless-safe; writes PNGs instead of showing a window
import matplotlib.pyplot as plt


# ----------------------------------------------------------------------
def load_data(csv_path):
    df = pd.read_csv(csv_path)
    df["final_price"] = pd.to_numeric(df["final_price"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    return df


# ----------------------------------------------------------------------
# PART XV - Transaction-level statistical analysis
# ----------------------------------------------------------------------
def transaction_statistics(df):
    transaction_totals = df.groupby("transaction_id")["final_price"].sum().reset_index()
    transaction_totals.columns = ["transaction_id", "transaction_total"]

    stats = {
        "count": transaction_totals["transaction_total"].count(),
        "mean": transaction_totals["transaction_total"].mean(),
        "median": transaction_totals["transaction_total"].median(),
        "min": transaction_totals["transaction_total"].min(),
        "max": transaction_totals["transaction_total"].max(),
        "std": transaction_totals["transaction_total"].std(),
    }

    print("\n===== PART XV: TRANSACTION STATISTICS =====")
    print("Transaction count: {}".format(stats["count"]))
    print("Mean:     {:.2f}".format(stats["mean"]))
    print("Median:   {:.2f}".format(stats["median"]))
    print("Min:      {:.2f}".format(stats["min"]))
    print("Max:      {:.2f}".format(stats["max"]))
    print("Std Dev:  {:.2f}".format(stats["std"]))

    skew_note = "right-skewed (mean > median)" if stats["mean"] > stats["median"] else \
                "left-skewed (mean < median)" if stats["mean"] < stats["median"] else \
                "approximately symmetric"
    print("Distribution shape: {}".format(skew_note))

    return transaction_totals, stats


# ----------------------------------------------------------------------
# PART XVI - Histogram of transaction totals
# ----------------------------------------------------------------------
def plot_transaction_histogram(transaction_totals, out_path="transaction_histogram.png"):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(transaction_totals["transaction_total"], bins=30,
            color="steelblue", edgecolor="black")
    ax.set_title("Distribution of Transaction Totals")
    ax.set_xlabel("Transaction Total ($)")
    ax.set_ylabel("Number of Transactions")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print("\nHistogram saved to: {}".format(out_path))


# ----------------------------------------------------------------------
# PART XVII - Store-level outlier detection (Z-score)
# ----------------------------------------------------------------------
def detect_store_outliers(df, out_path="store_outliers.png", z_threshold=2.0):
    txn_totals = df.groupby(["transaction_id", "store_id"])["final_price"].sum().reset_index()
    txn_totals.columns = ["transaction_id", "store_id", "transaction_total"]

    store_avg = txn_totals.groupby("store_id")["transaction_total"].mean().reset_index()
    store_avg.columns = ["store_id", "avg_transaction_value"]

    mean_val = store_avg["avg_transaction_value"].mean()
    std_val = store_avg["avg_transaction_value"].std()
    store_avg["z_score"] = (store_avg["avg_transaction_value"] - mean_val) / std_val
    store_avg["is_outlier"] = store_avg["z_score"].abs() > z_threshold

    print("\n===== PART XVII: STORE OUTLIER DETECTION (Z-SCORE) =====")
    print(store_avg.sort_values("z_score", ascending=False).to_string(index=False))

    colors = ["crimson" if flag else "steelblue" for flag in store_avg["is_outlier"]]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(store_avg["store_id"], store_avg["avg_transaction_value"], color=colors)
    ax.set_title("Store Average Transaction Value with Outlier Detection (Z-score)")
    ax.set_xlabel("Store ID")
    ax.set_ylabel("Average Transaction Value ($)")
    ax.axhline(mean_val, color="gray", linestyle="--", linewidth=1, label="Mean")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print("\nOutlier chart saved to: {}".format(out_path))

    return store_avg


# ----------------------------------------------------------------------
# PART XI (percentage calc) - Category breakdown with % of total
# ----------------------------------------------------------------------
def category_breakdown(df):
    cat = df.groupby("category")["final_price"].sum().reset_index()
    cat.columns = ["category", "total_sales"]
    cat = cat.sort_values("total_sales", ascending=False)
    total = cat["total_sales"].sum()
    cat["pct_of_total"] = (cat["total_sales"] / total * 100).round(2)

    print("\n===== CATEGORY BREAKDOWN =====")
    print(cat.to_string(index=False))
    return cat


# ----------------------------------------------------------------------
# PART XIX - Calgary investigation: category mix + promotion ratio,
# compared against network-wide figures
# ----------------------------------------------------------------------
def investigate_store(df, store_id="ST-CAL-001"):
    store_df = df[df["store_id"] == store_id]

    store_cat = store_df.groupby("category")["final_price"].sum().reset_index()
    store_cat.columns = ["category", "sales"]
    store_total = store_cat["sales"].sum()
    store_cat["pct_of_store_sales"] = (store_cat["sales"] / store_total * 100).round(2)

    network_cat = category_breakdown(df)[["category", "pct_of_total"]]
    comparison = store_cat.merge(network_cat, on="category", how="left")
    comparison["difference_pp"] = (comparison["pct_of_store_sales"] - comparison["pct_of_total"]).round(2)

    print("\n===== {} CATEGORY MIX vs NETWORK-WIDE =====".format(store_id))
    print(comparison.sort_values("sales", ascending=False).to_string(index=False))

    store_promo = store_df["promotion_flag"].value_counts()
    store_promo_pct = round(store_promo.get("Y", 0) * 100.0 / store_promo.sum(), 2)

    network_promo = df["promotion_flag"].value_counts()
    network_promo_pct = round(network_promo.get("Y", 0) * 100.0 / network_promo.sum(), 2)

    print("\n{} promoted-event ratio: {}%".format(store_id, store_promo_pct))
    print("Network-wide promoted-event ratio: {}%".format(network_promo_pct))

    return comparison


# ----------------------------------------------------------------------
# PART XXI - Product demand: top/bottom 10
# ----------------------------------------------------------------------
def product_demand(df):
    demand = df.groupby(["product_id", "product_name"])["quantity"].sum().reset_index()
    demand.columns = ["product_id", "product_name", "total_quantity"]

    top10 = demand.sort_values("total_quantity", ascending=False).head(10)
    bottom10 = demand.sort_values("total_quantity", ascending=True).head(10)

    print("\n===== TOP 10 HIGHEST-DEMAND PRODUCTS =====")
    print(top10.to_string(index=False))
    print("\n===== TOP 10 LOWEST-DEMAND PRODUCTS =====")
    print(bottom10.to_string(index=False))

    return top10, bottom10


# ----------------------------------------------------------------------
def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/retail_events.csv"
    print("Loading: {}".format(csv_path))
    df = load_data(csv_path)

    transaction_totals, stats = transaction_statistics(df)
    plot_transaction_histogram(transaction_totals)
    detect_store_outliers(df)
    category_breakdown(df)
    investigate_store(df, "ST-CAL-001")
    product_demand(df)

    print("\nDone. Chart PNGs written to the current directory.")


if __name__ == "__main__":
    main()
