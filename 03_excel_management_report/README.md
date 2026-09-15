# Excel Management Report Builder

A repeatable reporting workflow that converts raw sales transactions into a formatted Excel workbook for management review.

## Business problem

Teams often receive transactional exports as CSV or Excel and then spend time rebuilding the same summary workbook every week or month. Manual copying also makes reports difficult to reproduce and easy to break.

## What it does

- validates the required source columns
- parses dates and numeric fields
- calculates line revenue
- produces monthly, regional, and product summaries
- calculates management KPIs such as total revenue, order count, units sold, average order value, top region, and top product
- creates a multi-sheet `.xlsx` workbook
- adds Excel tables, filters, frozen headers, number formats, conditional formatting, and a management chart
- writes the same KPI set to JSON for downstream automation or validation

## Run the sample

```bash
python -m pip install -r requirements.txt
python report_builder.py sample_data/sales.csv output/management_report.xlsx \
  --summary-json output/summary.json
```

## Workbook layout

1. `Executive Summary` — management KPIs and a revenue-by-region chart
2. `Monthly` — monthly order, unit, and revenue totals
3. `Region` — regional performance
4. `Product` — product performance
5. `Transactions` — cleaned source data with calculated revenue

## Test

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests verify the KPI calculations, workbook structure, Excel tables, frozen panes, and missing-column validation.

All sample data is synthetic.
