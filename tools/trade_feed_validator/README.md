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

- **Valid Records (`valid_feed.csv`):** Fully compliant trades meeting schema and deduplication rules are preserved. Output file is always truncated/created per run.
- **Dead-Letter Queue (`dlq_feed.json`):** Rejected rows are isolated into a DLQ payload containing standard taxonomy codes (`DUPLICATE_EVENT_ID`, `DUPLICATE_TX_HASH`, `MISSING_BLOCK_TIME`, `INVALID_BLOCK_TIME`, `TIME_INVERSION_INGESTED_BEFORE_BLOCK`) along with raw original data.

## Setup & Running

### 1. Install Dependencies

```bash
pip install pytest