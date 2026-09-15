# Data Automation Samples

Practical examples of small data and office-automation workflows built with Python and common business file formats.

The focus here is not on large frameworks or demo-only code. Each sample is meant to represent the kind of repetitive data task that can be turned into a simple, maintainable tool.

## Current sample

### 1. CSV / Excel Data Cleaner & Merger

[Open the project](./01_csv_excel_cleaner/)

A command-line utility that:

- combines multiple CSV/XLSX files
- normalizes inconsistent column names
- cleans text values
- removes duplicate records using business keys
- preserves source-file traceability
- exports a clean result and a JSON processing report

The repository includes synthetic input data, expected output, and tests.

## Tools used

- Python
- pandas
- openpyxl
- CSV / Excel / JSON
- pytest

## Why this repository exists

Many useful automation jobs are not large software projects. They are small workflows that save someone from repeatedly copying, cleaning, checking, merging, or reformatting data by hand.

This repository collects examples of that kind of work. More samples will be added over time around file conversion, reporting, validation, SQL, and lightweight business automation.

> All example data in this repository is synthetic. No client or confidential data is included.
