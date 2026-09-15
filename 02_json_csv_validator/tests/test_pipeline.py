import json
from pathlib import Path

from pipeline import DEFAULT_FIELD_MAP, process_records, run_pipeline


def test_process_records_accepts_valid_and_rejects_bad_rows():
    records = [
        {
            "order": {"id": "A1", "date": "2026-01-01", "currency": "usd", "amount": "10"},
            "customer": {"id": "C1", "name": " Alice ", "email": "ALICE@example.com", "country": "us"},
        },
        {
            "order": {"id": "A2", "date": "01/02/2026", "currency": "USD", "amount": "-1"},
            "customer": {"id": "C2", "name": "Bob", "email": "bad-email", "country": "us"},
        },
    ]

    accepted, rejected, report = process_records(records, DEFAULT_FIELD_MAP)

    assert len(accepted) == 1
    assert accepted[0]["customer_name"] == "Alice"
    assert accepted[0]["email"] == "alice@example.com"
    assert accepted[0]["currency"] == "USD"
    assert accepted[0]["amount"] == "10.00"
    assert len(rejected) == 1
    assert report["accepted_records"] == 1
    assert report["rejected_records"] == 1


def test_duplicate_order_id_is_rejected():
    template = {
        "order": {"id": "A1", "date": "2026-01-01", "currency": "USD", "amount": "10"},
        "customer": {"id": "C1", "name": "Alice", "email": "alice@example.com", "country": "US"},
    }
    accepted, rejected, _ = process_records([template, template], DEFAULT_FIELD_MAP)
    assert len(accepted) == 1
    assert rejected[0]["errors"] == ["order_id: duplicate"]


def test_run_pipeline_writes_audit_outputs(tmp_path: Path):
    input_path = tmp_path / "orders.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "order": {"id": "A1", "date": "2026-01-01", "currency": "USD", "amount": 12.5},
                    "customer": {"id": "C1", "name": "Alice", "email": "alice@example.com", "country": "US"},
                }
            ]
        ),
        encoding="utf-8",
    )

    valid = tmp_path / "valid.csv"
    rejected = tmp_path / "rejected.json"
    report = tmp_path / "report.json"
    result = run_pipeline(input_path, valid, rejected, report)

    assert result["accepted_records"] == 1
    assert valid.exists()
    assert json.loads(rejected.read_text(encoding="utf-8")) == []
    assert json.loads(report.read_text(encoding="utf-8"))["acceptance_rate"] == 1.0
