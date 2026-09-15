from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests


class ApiError(RuntimeError):
    """Raised when an API response cannot be safely processed."""


class PaginatedApiClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.25,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def _get_json(self, url: str) -> dict[str, Any]:
        """Fetch one page, retrying only failures that are reasonably transient."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.backoff_seconds * (2**attempt))
                continue

            if response.status_code >= 500:
                last_error = ApiError(f"Server error {response.status_code} for {url}")
                if attempt >= self.max_retries:
                    break
                time.sleep(self.backoff_seconds * (2**attempt))
                continue

            if response.status_code >= 400:
                raise ApiError(f"HTTP {response.status_code} for {url}")

            try:
                payload = response.json()
            except ValueError as exc:
                raise ApiError(f"Invalid JSON response from {url}") from exc

            if not isinstance(payload, dict):
                raise ApiError("Expected a JSON object response")
            return payload

        raise ApiError(f"Request failed after retries: {last_error}")

    def iter_pages(self, start_url: str) -> Iterable[dict[str, Any]]:
        url: str | None = start_url
        while url:
            page = self._get_json(url)
            yield page
            next_url = page.get("next")
            if next_url is not None and not isinstance(next_url, str):
                raise ApiError("'next' must be a URL string or null")
            url = next_url


class FixturePageSource:
    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir

    def iter_pages(self) -> Iterable[dict[str, Any]]:
        files = sorted(self.fixture_dir.glob("page*.json"))
        if not files:
            raise FileNotFoundError(f"No page*.json fixtures found in {self.fixture_dir}")
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"Fixture must contain a JSON object: {path}")
            yield payload


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            synced_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sync_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            source TEXT NOT NULL,
            pages_fetched INTEGER NOT NULL,
            records_received INTEGER NOT NULL,
            inserted INTEGER NOT NULL,
            updated INTEGER NOT NULL
        );
        """
    )


def normalize_customer(record: dict[str, Any]) -> dict[str, Any]:
    required = ("id", "name", "email", "status", "updated_at")
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError("Customer record missing fields: " + ", ".join(missing))

    name = str(record["name"]).strip()
    email = str(record["email"]).strip().lower()
    status = str(record["status"]).strip().lower()
    updated_at = str(record["updated_at"]).strip()
    if not name or not email or not status or not updated_at:
        raise ValueError("Customer record contains empty required values")

    return {
        "id": int(record["id"]),
        "name": name,
        "email": email,
        "status": status,
        "updated_at": updated_at,
    }


def upsert_customers(
    conn: sqlite3.Connection, records: list[dict[str, Any]], synced_at: str
) -> tuple[int, int]:
    inserted = 0
    updated = 0

    for record in records:
        row = normalize_customer(record)
        exists = conn.execute(
            "SELECT 1 FROM customers WHERE id = ?", (row["id"],)
        ).fetchone()
        conn.execute(
            """
            INSERT INTO customers (id, name, email, status, updated_at, synced_at)
            VALUES (:id, :name, :email, :status, :updated_at, :synced_at)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                email = excluded.email,
                status = excluded.status,
                updated_at = excluded.updated_at,
                synced_at = excluded.synced_at
            """,
            {**row, "synced_at": synced_at},
        )
        if exists:
            updated += 1
        else:
            inserted += 1

    return inserted, updated


def sync_pages(
    pages: Iterable[dict[str, Any]],
    db_path: Path,
    report_path: Path,
    source: str,
) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    pages_fetched = 0
    records_received = 0
    inserted = 0
    updated = 0

    with sqlite3.connect(db_path) as conn:
        init_db(conn)
        for page in pages:
            pages_fetched += 1
            records = page.get("results")
            if not isinstance(records, list) or not all(
                isinstance(item, dict) for item in records
            ):
                raise ValueError("Every page must contain a 'results' array of objects")

            records_received += len(records)
            synced_at = datetime.now(timezone.utc).isoformat()
            page_inserted, page_updated = upsert_customers(conn, records, synced_at)
            inserted += page_inserted
            updated += page_updated

        completed = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO sync_runs (
                started_at, completed_at, source, pages_fetched,
                records_received, inserted, updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                started,
                completed,
                source,
                pages_fetched,
                records_received,
                inserted,
                updated,
            ),
        )
        total_rows = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        conn.commit()

    report = {
        "source": source,
        "started_at": started,
        "completed_at": completed,
        "pages_fetched": pages_fetched,
        "records_received": records_received,
        "inserted": inserted,
        "updated": updated,
        "rows_in_database": total_rows,
        "database": db_path.name,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize a paginated REST API into SQLite with retries "
            "and idempotent upserts."
        )
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--url", help="First API page URL")
    source_group.add_argument(
        "--fixture-dir", type=Path, help="Offline page fixture directory"
    )
    parser.add_argument("--database", type=Path, default=Path("customers.sqlite"))
    parser.add_argument("--report", type=Path, default=Path("sync_report.json"))
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    if args.fixture_dir:
        source = f"fixture:{args.fixture_dir}"
        pages = FixturePageSource(args.fixture_dir).iter_pages()
    else:
        source = str(args.url)
        client = PaginatedApiClient(timeout=args.timeout, max_retries=args.retries)
        pages = client.iter_pages(str(args.url))

    report = sync_pages(pages, args.database, args.report, source)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
