import argparse
import csv
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple

TIME_FORMAT = "%H:%M:%S"


def parse_time(time_str: str):
    if not time_str or time_str.strip().lower() == "null":
        return None
    try:
        return datetime.strptime(time_str.strip(), TIME_FORMAT)
    except ValueError:
        return None


class TradeFeedValidator:
    def __init__(self):
        self.seen_tx_hashes = set()
        self.seen_event_ids = set()

    def process_csv(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        valid_records = []
        dlq_records = []

        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                event_id = row["event_id"].strip()
                tx_hash = row["tx_hash"].strip()
                block_time_str = row["block_time"].strip()
                ingested_at_str = row["ingested_at"].strip()

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
                        "reason": "DUPLICATE_TRANSACTION_HASH",
                        "raw_data": row
                    })
                    continue

                block_time = parse_time(block_time_str)
                if block_time is None:
                    dlq_records.append({
                        "event_id": event_id,
                        "tx_hash": tx_hash,
                        "reason": "MISSING_BLOCK_TIME",
                        "raw_data": row
                    })
                    continue

                ingested_at = parse_time(ingested_at_str)
                if ingested_at is None:
                    dlq_records.append({
                        "event_id": event_id,
                        "tx_hash": tx_hash,
                        "reason": "INVALID_INGESTED_AT_TIME",
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

                self.seen_event_ids.add(event_id)
                self.seen_tx_hashes.add(tx_hash)
                valid_records.append(row)

        return valid_records, dlq_records


def main():
    parser = argparse.ArgumentParser(description="Trade Feed Data Quality Validator")
    parser.add_argument("--input", default="sample_feed.csv", help="Input CSV file path")
    parser.add_argument("--valid-out", default="valid_feed.csv", help="Output path for valid CSV records")
    parser.add_argument("--dlq-out", default="dlq_feed.json", help="Output path for DLQ JSON records")

    args = parser.parse_args()

    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(args.input)

    if valid:
        fieldnames = valid[0].keys()
        with open(args.valid_out, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(valid)

    with open(args.dlq_out, mode="w", encoding="utf-8") as f:
        json.dump(dlq, f, indent=2)

    print(f"=== Trade Feed Validation Results ===")
    print(f"Valid Records: {len(valid)} -> Saved to '{args.valid_out}'")
    print(f"DLQ Records:   {len(dlq)} -> Saved to '{args.dlq_out}'\n")


if __name__ == "__main__":
    main()