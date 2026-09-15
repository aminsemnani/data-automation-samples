from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    customer TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    invoice_amount REAL NOT NULL CHECK(invoice_amount >= 0)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);
"""

RECONCILIATION_SQL = """
WITH payment_totals AS (
    SELECT invoice_id, ROUND(SUM(amount), 2) AS paid_amount, COUNT(*) AS payment_count
    FROM payments
    GROUP BY invoice_id
),
invoice_rows AS (
    SELECT
        'invoice' AS record_type,
        i.invoice_id,
        i.customer,
        i.invoice_date,
        i.due_date,
        ROUND(i.invoice_amount, 2) AS invoice_amount,
        ROUND(COALESCE(p.paid_amount, 0), 2) AS paid_amount,
        ROUND(COALESCE(p.paid_amount, 0) - i.invoice_amount, 2) AS variance,
        COALESCE(p.payment_count, 0) AS payment_count,
        CASE
            WHEN p.invoice_id IS NULL THEN 'unpaid'
            WHEN ABS(p.paid_amount - i.invoice_amount) <= :tolerance THEN 'matched'
            WHEN p.paid_amount < i.invoice_amount THEN 'partial'
            ELSE 'overpaid'
        END AS status
    FROM invoices i
    LEFT JOIN payment_totals p ON p.invoice_id = i.invoice_id
),
orphan_rows AS (
    SELECT
        'orphan_payment' AS record_type,
        p.invoice_id,
        '' AS customer,
        '' AS invoice_date,
        '' AS due_date,
        0.0 AS invoice_amount,
        ROUND(SUM(p.amount), 2) AS paid_amount,
        ROUND(SUM(p.amount), 2) AS variance,
        COUNT(*) AS payment_count,
        'orphan_payment' AS status
    FROM payments p
    LEFT JOIN invoices i ON i.invoice_id = p.invoice_id
    WHERE i.invoice_id IS NULL
    GROUP BY p.invoice_id
)
SELECT * FROM invoice_rows
UNION ALL
SELECT * FROM orphan_rows
ORDER BY record_type, invoice_id;
"""


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No header row in {path}")
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path.name} missing columns: {', '.join(sorted(missing))}")
        return list(reader)


def load_data(conn: sqlite3.Connection, invoices_path: Path, payments_path: Path) -> None:
    invoices = _read_csv(
        invoices_path,
        {"invoice_id", "customer", "invoice_date", "due_date", "invoice_amount"},
    )
    payments = _read_csv(
        payments_path,
        {"payment_id", "invoice_id", "payment_date", "amount"},
    )

    conn.executemany(
        "INSERT INTO invoices VALUES (:invoice_id, :customer, :invoice_date, :due_date, :invoice_amount)",
        invoices,
    )
    conn.executemany(
        "INSERT INTO payments VALUES (:payment_id, :invoice_id, :payment_date, :amount)",
        payments,
    )
    conn.commit()


def reconcile(conn: sqlite3.Connection, tolerance: float = 0.01) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(RECONCILIATION_SQL, {"tolerance": tolerance}).fetchall()
    return [dict(row) for row in rows]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    invoice_total = 0.0
    paid_total = 0.0
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        if row["record_type"] == "invoice":
            invoice_total += float(row["invoice_amount"])
            paid_total += float(row["paid_amount"])

    return {
        "records": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "invoice_total": round(invoice_total, 2),
        "payments_applied_to_invoices": round(paid_total, 2),
        "net_variance": round(paid_total - invoice_total, 2),
        "exceptions": sum(count for status, count in counts.items() if status != "matched"),
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_reconciliation(
    invoices_path: Path,
    payments_path: Path,
    output_csv: Path,
    summary_json: Path,
    database_path: Path | None = None,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    db_target = str(database_path) if database_path else ":memory:"
    if database_path:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        if database_path.exists():
            database_path.unlink()

    with sqlite3.connect(db_target) as conn:
        conn.executescript(SCHEMA_SQL)
        load_data(conn, invoices_path, payments_path)
        rows = reconcile(conn, tolerance=tolerance)
        summary = summarize(rows)

    write_csv(rows, output_csv)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile invoice and payment exports using SQLite and produce an exception report."
    )
    parser.add_argument("invoices", type=Path)
    parser.add_argument("payments", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reconciliation.csv"))
    parser.add_argument("--summary", type=Path, default=Path("reconciliation_summary.json"))
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--tolerance", type=float, default=0.01)
    args = parser.parse_args()

    summary = run_reconciliation(
        args.invoices,
        args.payments,
        args.output,
        args.summary,
        args.database,
        args.tolerance,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
