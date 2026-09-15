from pathlib import Path

import pandas as pd

from cleaner import clean_dataframe, merge_and_clean, normalize_column_name


def test_normalize_column_name():
    assert normalize_column_name(" EMAIL Address ") == "email_address"
    assert normalize_column_name("Order-Total") == "order_total"


def test_clean_dataframe_trims_text_and_normalizes_columns():
    frame = pd.DataFrame({" Full Name ": ["  Ada Lovelace  "]})
    cleaned = clean_dataframe(frame)
    assert list(cleaned.columns) == ["full_name"]
    assert cleaned.loc[0, "full_name"] == "Ada Lovelace"


def test_merge_and_clean_deduplicates_by_key(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "01.csv").write_text(
        "Customer ID,Name\n1,Alice\n2,Bob\n", encoding="utf-8"
    )
    (input_dir / "02.csv").write_text(
        "customer_id,name\n2, Bob Updated \n3,Carol\n", encoding="utf-8"
    )

    output_path = tmp_path / "merged.csv"
    report_path = tmp_path / "report.json"
    report = merge_and_clean(
        input_dir, output_path, report_path, ["customer_id"]
    )

    result = pd.read_csv(output_path)
    assert len(result) == 3
    assert result.loc[result["customer_id"] == 2, "name"].item() == "Bob Updated"
    assert report["duplicates_removed"] == 1


def test_reads_xlsx_and_writes_xlsx(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    pd.DataFrame(
        {
            "Customer ID": [1, 2],
            " Full Name ": ["Alice", " Bob "],
        }
    ).to_excel(input_dir / "customers.xlsx", index=False)

    output_path = tmp_path / "merged.xlsx"
    report_path = tmp_path / "report.json"
    merge_and_clean(input_dir, output_path, report_path, ["customer_id"])

    result = pd.read_excel(output_path)
    assert list(result["full_name"]) == ["Alice", "Bob"]
