import json
from pathlib import Path

from reconcile import run_reconciliation


def write_fixture_files(tmp_path: Path) -> tuple[Path, Path]:
    invoices = tmp_path / "invoices.csv"
    payments = tmp_path / "payments.csv"
    invoices.write_text(
        "invoice_id,customer,invoice_date,due_date,invoice_amount\n"
        "I1,A,2026-01-01,2026-01-31,100.00\n"
        "I2,B,2026-01-01,2026-01-31,200.00\n"
        "I3,C,2026-01-01,2026-01-31,300.00\n",
        encoding="utf-8",
    )
    payments.write_text(
        "payment_id,invoice_id,payment_date,amount\n"
        "P1,I1,2026-01-10,100.00\n"
        "P2,I2,2026-01-10,50.00\n"
        "P3,I2,2026-01-11,50.00\n"
        "P4,I3,2026-01-12,310.00\n"
        "P5,UNKNOWN,2026-01-12,15.00\n",
        encoding="utf-8",
    )
    return invoices, payments


def test_reconciliation_classifies_matches_and_exceptions(tmp_path: Path):
    invoices, payments = write_fixture_files(tmp_path)
    output = tmp_path / "recon.csv"
    summary = tmp_path / "summary.json"
    db = tmp_path / "audit.sqlite"

    result = run_reconciliation(invoices, payments, output, summary, db)

    assert result["status_counts"] == {
        "matched": 1,
        "orphan_payment": 1,
        "overpaid": 1,
        "partial": 1,
    }
    assert result["exceptions"] == 3
    assert result["invoice_total"] == 600.0
    assert db.exists()
    assert output.exists()
    assert json.loads(summary.read_text(encoding="utf-8"))["net_variance"] == -90.0


def test_tolerance_allows_small_rounding_difference(tmp_path: Path):
    invoices = tmp_path / "invoices.csv"
    payments = tmp_path / "payments.csv"
    invoices.write_text(
        "invoice_id,customer,invoice_date,due_date,invoice_amount\n"
        "I1,A,2026-01-01,2026-01-31,100.00\n",
        encoding="utf-8",
    )
    payments.write_text(
        "payment_id,invoice_id,payment_date,amount\n"
        "P1,I1,2026-01-10,99.99\n",
        encoding="utf-8",
    )
    result = run_reconciliation(
        invoices,
        payments,
        tmp_path / "recon.csv",
        tmp_path / "summary.json",
        tolerance=0.02,
    )
    assert result["status_counts"] == {"matched": 1}
