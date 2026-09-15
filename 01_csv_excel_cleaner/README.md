# CSV / Excel Data Cleaner & Merger

A small practical Python utility for combining tabular files that do not arrive perfectly clean or consistently formatted.

This sample uses synthetic customer/order data and demonstrates a common office/data-automation workflow: collect several CSV or Excel files, normalize them, remove duplicates, and produce one clean output plus a processing report.

## What it does

- Reads `.csv` and `.xlsx` files from one input directory
- Normalizes column names to `snake_case`
- Trims unnecessary whitespace from text values
- Merges files even when header formatting differs
- Removes duplicate records using one or more business keys
- Keeps the source filename for traceability
- Writes the cleaned result as CSV or Excel
- Generates a JSON summary report

## Example

The two sample input files intentionally use different header styles:

- `Customer ID` vs. `customer_id`
- `Full Name` vs. `full-name`
- extra whitespace around headers and values

They also contain one repeated customer record.

Run from this directory:

```bash
python -m pip install -r requirements.txt
python cleaner.py sample_data/input sample_data/output/merged_cleaned.csv \
  --report sample_data/output/cleaning_report.json \
  --dedup-key customer_id
```

The example processes 7 input rows and produces 6 unique rows.

## Files

```text
01_csv_excel_cleaner/
├── cleaner.py
├── requirements.txt
├── requirements-dev.txt
├── sample_data/
│   ├── input/
│   └── output/
└── tests/
```

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The current tests cover column normalization, whitespace cleanup, and key-based deduplication.

## Notes

This is a portfolio sample, so the data is synthetic. In real client work, the same workflow can be extended with business-specific validation rules, column mappings, date/number normalization, exception reports, and scheduled processing.
