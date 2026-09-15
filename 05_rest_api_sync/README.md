# REST API to SQLite Sync Pipeline

A compact but production-oriented example of synchronizing a paginated REST API into a local database.

## Business problem

Business integrations rarely stop at a single request. Real data sync jobs need pagination, timeouts, retry behavior, normalization, repeatable upserts, and enough run metadata to answer the question: “What happened during the last sync?”

## What it does

- follows paginated responses using a `next` link
- applies request timeouts
- retries transient server/network errors with exponential backoff
- fails clearly on permanent HTTP errors or malformed payloads
- normalizes incoming customer fields
- upserts by stable record ID, making repeated runs idempotent
- stores synchronized rows in SQLite
- records each synchronization run in a `sync_runs` audit table
- writes a JSON run report
- includes an offline fixture mode so the full sample can be demonstrated without relying on an external service

## Offline demo

```bash
python -m pip install -r requirements.txt
python api_sync.py --fixture-dir sample_data --database output/customers.sqlite --report output/sync_report.json
```

## Real API mode

The example expects a response shape like:

```json
{
  "results": [{"id": 1, "name": "...", "email": "...", "status": "...", "updated_at": "..."}],
  "next": "https://api.example.com/customers?page=2"
}
```

Run it with:

```bash
python api_sync.py --url "https://api.example.com/customers"
```

Authentication can be added to the `requests.Session` without changing the database or pagination logic.

## Test

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover pagination, retry handling, idempotent upserts, normalization, and persisted audit history. They use fake HTTP responses and make no network calls.

All fixtures are synthetic.
