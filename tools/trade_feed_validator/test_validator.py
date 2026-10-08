import json
import pytest
from validator import TradeFeedValidator


def test_valid_records_pass(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "event_id,tx_hash,block_time,wallet,side,amount,ingested_at\n"
        "evt_001,0xaa1,09:14:02,0xD4,BUY,120000,09:14:05\n"
    )
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(str(csv_file))
    assert len(valid) == 1
    assert len(dlq) == 0


def test_duplicate_tx_hash(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "event_id,tx_hash,block_time,wallet,side,amount,ingested_at\n"
        "evt_002,0xaa2,09:41:20,0xD4,BUY,120000,09:41:23\n"
        "evt_003,0xaa2,09:41:20,0xD4,BUY,120000,09:44:01\n"
    )
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(str(csv_file))
    assert len(valid) == 1
    assert len(dlq) == 1
    assert dlq[0]["reason"] == "DUPLICATE_TX_HASH"


def test_duplicate_event_id(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "event_id,tx_hash,block_time,wallet,side,amount,ingested_at\n"
        "evt_001,0xaa1,09:14:02,0xD4,BUY,120000,09:14:05\n"
        "evt_001,0xaa9,09:14:02,0xD4,BUY,120000,09:14:05\n"
    )
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(str(csv_file))
    assert len(valid) == 1
    assert len(dlq) == 1
    assert dlq[0]["reason"] == "DUPLICATE_EVENT_ID"


def test_missing_block_time(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "event_id,tx_hash,block_time,wallet,side,amount,ingested_at\n"
        "evt_005,0xaa4,null,0xE5,SELL,300000,09:58:30\n"
    )
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(str(csv_file))
    assert len(valid) == 0
    assert len(dlq) == 1
    assert dlq[0]["reason"] == "MISSING_BLOCK_TIME"


def test_time_inversion(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "event_id,tx_hash,block_time,wallet,side,amount,ingested_at\n"
        "evt_008,0xaa6,10:10:00,0xF6,BUY,90000,09:59:50\n"
    )
    validator = TradeFeedValidator()
    valid, dlq = validator.process_csv(str(csv_file))
    assert len(valid) == 0
    assert len(dlq) == 1
    assert dlq[0]["reason"] == "TIME_INVERSION_INGESTED_BEFORE_BLOCK"