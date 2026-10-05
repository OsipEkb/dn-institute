# Trade Feed Validator

A lightweight data quality validation tool designed to sanitize blockchain trade event feeds before ingestion into downstream analytics tables.

---

## 1. Data-Quality Issues Found

| Event ID | Issue Identified | Downstream Impact |
| :--- | :--- | :--- |
| **evt_003** | **Duplicate Transaction Hash (`0xaa2`)** | Re-ingested transaction. Inflates volume metrics, corrupts VWAP calculations, and doubles wallet balances. |
| **evt_005** | **Missing `block_time` (`null`)** | Breaks temporal windowing, candlestick generation (OHLCV), and time-series aggregation models. |
| **evt_007** | **Duplicate Transaction Hash (`0xaa5`)** | Duplicate payload event. Skews wallet activity clustering and double-counts trade volume. |
| **evt_008** | **Time Inversion (`ingested_at` < `block_time`)** | Ingestion timestamp precedes block creation ($09:59:50 < 10:10:00$). Breaks causality assumptions and stream processing watermarks. |

---

## 2. Handling `evt_005`

### Strategy: Dead-Letter Queue (DLQ)
We route `evt_005` directly to a **Dead-Letter Queue (DLQ)** rather than dropping it or blindly backfilling it.

* **Why DLQ?** Dropping event loss hides financial volume. Silent backfilling (e.g., setting `block_time = ingested_at`) risks misrepresenting block-level metrics.
* **What would change this answer?** If downstream indexer APIs provide deterministic backfilling endpoints (e.g., querying RPC nodes by `tx_hash` `0xaa4` to resolve the exact block header), an automated retry mechanism with enrichment would be implemented prior to DLQ routing.

---

## 3. General Practice for Automated Pipeline Protection (<150 words)

To catch this entire class of issues automatically before analysts detect them downstream:

1. **Schema Registry & Pre-Ingestion Validation:** Enforce strict schema validation (using Great Expectations or Pydantic) at the pipeline entry point (e.g., Kafka / Flink deserialization layer).
2. **Automated DLQ Isolation:** Divert non-conforming rows immediately to an isolated Dead-Letter Queue with structured metadata (`error_code`, `timestamp`, `raw_payload`) to ensure operational visibility without interrupting pipeline flow.
3. **Data Quality SLA Alerting:** Trigger real-time Prometheus / Slack alerts whenever DLQ thresholds or anomaly ratios exceed tolerance (e.g., >0.01% corrupted records over a 5-minute sliding window).

---

## 4. Setup & Running Instructions

### Installation
```bash
pip install pytest