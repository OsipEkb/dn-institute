import pytest
import csv
import json
from validator import TradeFeedValidator, parse_time


def create_temp_csv(tmp_path, rows):
    file_path = tmp_path / "test_feed.csv"
    fieldnames = ["event_id", "tx_hash", "block_time", "wallet", "side", "amount", "ingested_at"]
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(file_path)


def test_valid_records_pass(tmp_path):
    rows = [
        {"event_id": "evt_001", "tx_hash": "0xaa1", "block_time": "09:14:02", "wallet": "0xD4", "side": "BUY", "amount": "120000", "ingested_at": "09:14:05"},
        {"event_id": "evt_002", "tx_hash": "0xaa2", "block_time": "09:41:20", "wallet": "0xD4", "side": "BUY", "amount": "120000", "ingested_at": "09:41:23"},
    ]
    file_path = create_temp_csv(tmp_path, rows)
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(file_path)

    assert len(valid) == 2
    assert len(dlq) == 0


def test_duplicate_tx_hash(tmp_path):
    rows = [
        {"event_id": "evt_002", "tx_hash": "0xaa2", "block_time": "09:41:20", "wallet": "0xD4", "side": "BUY", "amount": "120000", "ingested_at": "09:41:23"},
        {"event_id": "evt_003", "tx_hash": "0xaa2", "block_time": "09:41:20", "wallet": "0xD4", "side": "BUY", "amount": "120000", "ingested_at": "09:44:01"},
    ]
    file_path = create_temp_csv(tmp_path, rows)
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(file_path)

    assert len(valid) == 1
    assert len(dlq) == 1
    assert dlq[0]["event_id"] == "evt_003"
    assert dlq[0]["reason"] == "DUPLICATE_TRANSACTION_HASH"


def test_missing_block_time(tmp_path):
    rows = [
        {"event_id": "evt_005", "tx_hash": "0xaa4", "block_time": "null", "wallet": "0xE5", "side": "SELL", "amount": "300000", "ingested_at": "09:58:30"},
    ]
    file_path = create_temp_csv(tmp_path, rows)
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(file_path)

    assert len(valid) == 0
    assert len(dlq) == 1
    assert dlq[0]["reason"] == "MISSING_BLOCK_TIME"


def test_time_inversion(tmp_path):
    rows = [
        {"event_id": "evt_008", "tx_hash": "0xaa6", "block_time": "10:10:00", "wallet": "0xF6", "side": "SELL", "amount": "900000", "ingested_at": "09:59:50"},
    ]
    file_path = create_temp_csv(tmp_path, rows)
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(file_path)

    assert len(valid) == 0
    assert len(dlq) == 1
    assert dlq[0]["reason"] == "TIME_INVERSION_INGESTED_BEFORE_BLOCK"