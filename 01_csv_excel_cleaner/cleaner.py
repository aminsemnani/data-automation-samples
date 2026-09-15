from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def normalize_column_name(name: object) -> str:
    """Convert a column name to lowercase snake_case."""
    text = str(name).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and trim surrounding whitespace in text cells."""
    cleaned = df.copy()
    cleaned.columns = [normalize_column_name(column) for column in cleaned.columns]

    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[column] = cleaned[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        cleaned[column] = cleaned[column].replace("", pd.NA)

    return cleaned


def read_table(path: Path) -> pd.DataFrame:
    """Read a CSV file or the first worksheet of an XLSX file."""
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def discover_input_files(input_dir: Path, excluded: Iterable[Path] = ()) -> list[Path]:
    """Return supported input files in deterministic filename order."""
    excluded_resolved = {path.resolve() for path in excluded}
    files = [
        path
        for path in input_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and path.resolve() not in excluded_resolved
    ]
    return sorted(files, key=lambda path: path.name.lower())


def merge_and_clean(
    input_dir: Path,
    output_path: Path,
    report_path: Path,
    dedup_keys: list[str] | None = None,
) -> dict:
    input_dir = input_dir.resolve()
    output_path = output_path.resolve()
    report_path = report_path.resolve()

    files = discover_input_files(input_dir, excluded=[output_path, report_path])
    if not files:
        raise FileNotFoundError(
            f"No CSV or XLSX files found in input directory: {input_dir}"
        )

    frames: list[pd.DataFrame] = []
    per_file_rows: dict[str, int] = {}

    for path in files:
        frame = clean_dataframe(read_table(path))
        frame["source_file"] = path.name
        frames.append(frame)
        per_file_rows[path.name] = len(frame)

    merged = pd.concat(frames, ignore_index=True, sort=False)
    input_rows = len(merged)

    normalized_keys = (
        [normalize_column_name(key) for key in dedup_keys] if dedup_keys else []
    )
    missing_keys = [key for key in normalized_keys if key not in merged.columns]
    if missing_keys:
        raise KeyError(
            "Deduplication key(s) not found after column normalization: "
            + ", ".join(missing_keys)
        )

    if normalized_keys:
        merged = merged.drop_duplicates(subset=normalized_keys, keep="last")
    else:
        comparable_columns = [
            column for column in merged.columns if column != "source_file"
        ]
        merged = merged.drop_duplicates(subset=comparable_columns, keep="last")

    merged = merged.reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".csv":
        merged.to_csv(output_path, index=False)
    elif output_path.suffix.lower() == ".xlsx":
        merged.to_excel(output_path, index=False)
    else:
        raise ValueError("Output file must end in .csv or .xlsx")

    report = {
        "files_processed": [path.name for path in files],
        "rows_per_file": per_file_rows,
        "input_rows": input_rows,
        "output_rows": len(merged),
        "duplicates_removed": input_rows - len(merged),
        "deduplication_keys": normalized_keys,
        "columns": list(merged.columns),
        "output_file": output_path.name,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge, clean, normalize, and deduplicate CSV/XLSX files."
    )
    parser.add_argument(
        "input_dir", type=Path, help="Directory containing CSV/XLSX files"
    )
    parser.add_argument("output", type=Path, help="Output .csv or .xlsx path")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("cleaning_report.json"),
        help="JSON report path (default: cleaning_report.json)",
    )
    parser.add_argument(
        "--dedup-key",
        nargs="+",
        default=None,
        help=(
            "One or more columns used to identify duplicates, "
            "e.g. --dedup-key customer_id"
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = merge_and_clean(
        input_dir=args.input_dir,
        output_path=args.output,
        report_path=args.report,
        dedup_keys=args.dedup_key,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
