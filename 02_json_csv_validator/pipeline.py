from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

DEFAULT_FIELD_MAP = {
    "order_id": "order.id",
    "customer_id": "customer.id",
    "customer_name": "customer.name",
    "email": "customer.email",
    "order_date": "order.date",
    "currency": "order.currency",
    "amount": "order.amount",
    "country": "customer.country",
}

OUTPUT_FIELDS = list(DEFAULT_FIELD_MAP)


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    row: dict[str, Any]
    errors: list[str]


def get_nested(record: dict[str, Any], dotted_path: str) -> Any:
    value: Any = record
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def load_records(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise ValueError("JSON input must be an array of objects")
        return payload
    if suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"JSONL line {line_no} is not an object")
            records.append(item)
        return records
    raise ValueError("Input must be .json or .jsonl")


def load_field_map(path: Path | None) -> dict[str, str]:
    if path is None:
        return DEFAULT_FIELD_MAP.copy()
    mapping = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict):
        raise ValueError("Field map must be a JSON object")
    missing = [field for field in OUTPUT_FIELDS if field not in mapping]
    if missing:
        raise ValueError("Field map is missing canonical fields: " + ", ".join(missing))
    if not all(isinstance(value, str) for value in mapping.values()):
        raise ValueError("Every field-map value must be a dotted source path string")
    return mapping


def normalize_record(record: dict[str, Any], field_map: dict[str, str]) -> dict[str, Any]:
    row = {target: get_nested(record, source) for target, source in field_map.items()}

    for key in ("order_id", "customer_id", "customer_name", "email", "currency", "country"):
        if isinstance(row.get(key), str):
            row[key] = row[key].strip()

    if isinstance(row.get("email"), str):
        row["email"] = row["email"].lower()
    if isinstance(row.get("currency"), str):
        row["currency"] = row["currency"].upper()
    if isinstance(row.get("country"), str):
        row["country"] = row["country"].upper()

    return row


def validate_and_coerce(row: dict[str, Any]) -> ValidationResult:
    normalized = row.copy()
    errors: list[str] = []

    for field in ("order_id", "customer_id", "email", "order_date", "currency", "amount"):
        if normalized.get(field) in (None, ""):
            errors.append(f"{field}: required")

    email = normalized.get("email")
    if email not in (None, "") and (not isinstance(email, str) or not EMAIL_RE.match(email)):
        errors.append("email: invalid format")

    currency = normalized.get("currency")
    if currency not in (None, "") and (
        not isinstance(currency, str) or not CURRENCY_RE.match(currency)
    ):
        errors.append("currency: expected 3-letter ISO-style code")

    raw_date = normalized.get("order_date")
    if raw_date not in (None, ""):
        try:
            normalized["order_date"] = date.fromisoformat(str(raw_date)).isoformat()
        except ValueError:
            errors.append("order_date: expected YYYY-MM-DD")

    raw_amount = normalized.get("amount")
    if raw_amount not in (None, ""):
        try:
            amount = Decimal(str(raw_amount))
            if amount < 0:
                errors.append("amount: must be non-negative")
            else:
                normalized["amount"] = f"{amount.quantize(Decimal('0.01')):.2f}"
        except (InvalidOperation, ValueError):
            errors.append("amount: expected a numeric value")

    return ValidationResult(accepted=not errors, row=normalized, errors=errors)


def process_records(
    records: Iterable[dict[str, Any]], field_map: dict[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_order_ids: set[str] = set()
    error_counts: dict[str, int] = {}

    for index, raw in enumerate(records, start=1):
        result = validate_and_coerce(normalize_record(raw, field_map))
        errors = list(result.errors)

        order_id = result.row.get("order_id")
        if result.accepted and isinstance(order_id, str):
            if order_id in seen_order_ids:
                errors.append("order_id: duplicate")
            else:
                seen_order_ids.add(order_id)

        if errors:
            for error in errors:
                key = error.split(":", 1)[0]
                error_counts[key] = error_counts.get(key, 0) + 1
            rejected.append({"record_number": index, "errors": errors, "record": raw})
        else:
            accepted.append({field: result.row.get(field) for field in OUTPUT_FIELDS})

    report = {
        "input_records": len(accepted) + len(rejected),
        "accepted_records": len(accepted),
        "rejected_records": len(rejected),
        "acceptance_rate": round(
            len(accepted) / (len(accepted) + len(rejected)), 4
        )
        if accepted or rejected
        else 0.0,
        "error_counts_by_field": dict(sorted(error_counts.items())),
        "output_fields": OUTPUT_FIELDS,
    }
    return accepted, rejected, report


def write_outputs(
    accepted: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    report: dict[str, Any],
    valid_csv: Path,
    rejected_json: Path,
    report_json: Path,
) -> None:
    valid_csv.parent.mkdir(parents=True, exist_ok=True)
    with valid_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(accepted)

    rejected_json.parent.mkdir(parents=True, exist_ok=True)
    rejected_json.write_text(json.dumps(rejected, indent=2), encoding="utf-8")
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")


def run_pipeline(
    input_path: Path,
    valid_csv: Path,
    rejected_json: Path,
    report_json: Path,
    field_map_path: Path | None = None,
) -> dict[str, Any]:
    records = load_records(input_path)
    field_map = load_field_map(field_map_path)
    accepted, rejected, report = process_records(records, field_map)
    write_outputs(accepted, rejected, report, valid_csv, rejected_json, report_json)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and transform nested JSON/JSONL orders into clean CSV output."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--valid", type=Path, default=Path("valid_orders.csv"))
    parser.add_argument("--rejected", type=Path, default=Path("rejected_orders.json"))
    parser.add_argument("--report", type=Path, default=Path("validation_report.json"))
    parser.add_argument("--field-map", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = run_pipeline(
        input_path=args.input,
        valid_csv=args.valid,
        rejected_json=args.rejected,
        report_json=args.report,
        field_map_path=args.field_map,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
