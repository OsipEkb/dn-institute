import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

TIME_FORMAT = "%H:%M:%S"


def parse_time(time_str: str):
    if not time_str or time_str.strip().lower() == "null":
        return None
    val = time_str.strip()
    if len(val) != 8:
        return None
    try:
        return datetime.strptime(val, TIME_FORMAT)
    except ValueError:
        return None


class TradeFeedValidator:
    def __init__(self):
        self.seen_event_ids = set()
        self.seen_tx_hashes = set()

    def process_csv(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        valid_records = []
        dlq_records = []

        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                event_id = row.get("event_id", "").strip() if row.get("event_id") else ""
                tx_hash = row.get("tx_hash", "").strip() if row.get("tx_hash") else ""
                block_time_str = row.get("block_time", "").strip() if row.get("block_time") else ""
                ingested_at_str = row.get("ingested_at", "").strip() if row.get("ingested_at") else ""

                if not event_id or not tx_hash:
                    dlq_records.append({
                        "event_id": event_id,
                        "tx_hash": tx_hash,
                        "reason": "MISSING_REQUIRED_FIELDS",
                        "raw_data": row
                    })
                    continue

                if event_id in self.seen_event_ids:
                    dlq_records.append({
                        "event_id": event_id,
                        "tx_hash": tx_hash,
                        "reason": "DUPLICATE_EVENT_ID",
                        "raw_data": row
                    })
                    continue

                if tx_hash in self.seen_tx_hashes:
                    dlq_records.append({
                        "event_id": event_id,
                        "tx_hash": tx_hash,
                        "reason": "DUPLICATE_TX_HASH",
                        "raw_data": row
                    })
                    continue

                self.seen_event_ids.add(event_id)
                self.seen_tx_hashes.add(tx_hash)

                block_time = parse_time(block_time_str)
                if block_time is None:
                    reason = "MISSING_BLOCK_TIME" if not block_time_str or block_time_str.lower() == "null" else "INVALID_BLOCK_TIME"
                    dlq_records.append({
                        "event_id": event_id,
                        "tx_hash": tx_hash,
                        "reason": reason,
                        "raw_data": row
                    })
                    continue

                ingested_at = parse_time(ingested_at_str)
                if ingested_at is None:
                    dlq_records.append({
                        "event_id": event_id,
                        "tx_hash": tx_hash,
                        "reason": "INVALID_INGESTION_TIME",
                        "raw_data": row
                    })
                    continue

                if ingested_at < block_time:
                    dlq_records.append({
                        "event_id": event_id,
                        "tx_hash": tx_hash,
                        "reason": "TIME_INVERSION_INGESTED_BEFORE_BLOCK",
                        "raw_data": row
                    })
                    continue

                valid_records.append(row)

        return valid_records, dlq_records


def main():
    default_input = str(Path(__file__).resolve().with_name("sample_feed.csv"))
    parser = argparse.ArgumentParser(description="Trade Feed Validator")
    parser.add_argument("--input", default=default_input, help="Input CSV file path")
    parser.add_argument("--valid-out", default="valid_feed.csv", help="Output path for valid CSV records")
    parser.add_argument("--dlq-out", default="dlq_feed.json", help="Output path for DLQ JSON records")

    args = parser.parse_args()

    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(args.input)

    fieldnames = valid[0].keys() if valid else ["event_id", "tx_hash", "block_time", "wallet", "side", "amount", "ingested_at"]
    with open(args.valid_out, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if valid:
            writer.writerows(valid)

    with open(args.dlq_out, mode="w", encoding="utf-8") as f:
        json.dump(dlq, f, indent=2)

    print(f"Processing complete. Valid records: {len(valid)}, DLQ records: {len(dlq)}")


if __name__ == "__main__":
    main()