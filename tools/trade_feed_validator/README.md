# Trade Feed Validator (`tools/trade_feed_validator`)

An automated data-quality validation pipeline designed to screen blockchain trade feed records prior to downstream aggregation and analytics ingestion.

## Identified Data Quality Issues

| Event ID | Issue Identified | Impact |
| :--- | :--- | :--- |
| **evt_003** | **Duplicate Transaction Hash (`0xaa2`)** | Re-ingested transaction. Distorts trade activity metrics, skews VWAP, and double-counts volume. |
| **evt_005** | **Missing `block_time` (`null`)** | Breaks temporal aggregation windows, OHLCV candlestick generation, and time-series models. |
| **evt_007** | **Duplicate Transaction Hash (`0xaa5`)** | Duplicate payload event. Inflates volume and skews wallet interaction history. |
| **evt_008** | **Time Inversion (`ingested_at` < `block_time`)** | Ingestion timestamp precedes block timestamp ($09:59:50 < 10:10:00$). Violates stream processing watermarks and causality. |

## Execution Architecture & Routing Strategy

- **Valid Records (`valid_feed.csv`):** Fully compliant trades meeting schema and deduplication rules are preserved. Output file is always created or truncated per execution run.
- **Dead-Letter Queue (`dlq_feed.json`):** Rejected rows are isolated into a DLQ payload containing standard taxonomy codes (`MISSING_REQUIRED_FIELDS`, `DUPLICATE_EVENT_ID`, `DUPLICATE_TX_HASH`, `MISSING_BLOCK_TIME`, `INVALID_BLOCK_TIME`, `INVALID_INGESTION_TIME`, `TIME_INVERSION_INGESTED_BEFORE_BLOCK`) along with raw original data.

## Dead-Lettering Rationale for `evt_005`

`evt_005` is routed to the Dead-Letter Queue (DLQ) rather than silently dropped because missing critical temporal metadata (`block_time = null`) renders on-chain trade indexing impossible for time-series analytics, yet the transaction itself may represent legitimate activity requiring audit visibility. Preserving the raw payload in DLQ enables offline enrichment, backfilling, or manual investigation.

**Conditions to Change Decision:**
This record could be safely re-routed to the primary pipeline if an upstream enrichment worker can reliably backfill the exact `block_time` via RPC indexers using `tx_hash` (`0xaa4`), or if downstream systems explicitly support ingestion with a synthetic block timestamp fallback.

## General-Practice Proposal for Automated Safeguards

To automatically detect data quality degradation before downstream ingestion, implement pre-ingestion schema validation combined with anomaly detection. Enforce strict JSON Schema / Protobuf type checks at the edge (e.g., API Gateway or Kafka Streams filter). Monitor real-time stream metrics using sliding watermarks to alert on elevated DLQ rates, missing mandatory fields, or timestamps deviating significantly from expected clock skew thresholds. Integrated Prometheus alerts with Slack/PagerDuty ensure instant developer notification before corrupted feeds poison analytical datamarts.

## Setup & Running

### 1. Install Dependencies

```bash
pip install pytest