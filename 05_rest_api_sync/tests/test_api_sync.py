import json
import sqlite3
from pathlib import Path

from api_sync import FixturePageSource, PaginatedApiClient, sync_pages


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        return self.responses.pop(0)


def test_paginated_client_follows_next_link():
    session = FakeSession(
        [
            FakeResponse(200, {"results": [{"id": 1}], "next": "page2"}),
            FakeResponse(200, {"results": [{"id": 2}], "next": None}),
        ]
    )
    client = PaginatedApiClient(session=session, backoff_seconds=0)
    pages = list(client.iter_pages("page1"))
    assert len(pages) == 2
    assert [call[0] for call in session.calls] == ["page1", "page2"]


def test_client_retries_server_errors():
    session = FakeSession(
        [FakeResponse(503, {}), FakeResponse(200, {"results": [], "next": None})]
    )
    client = PaginatedApiClient(session=session, max_retries=1, backoff_seconds=0)
    assert client._get_json("page1")["results"] == []
    assert len(session.calls) == 2


def test_fixture_sync_is_idempotent_and_audited(tmp_path: Path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "page1.json").write_text(
        json.dumps(
            {
                "results": [
                    {
                        "id": 1,
                        "name": " Alice ",
                        "email": "A@EXAMPLE.COM",
                        "status": "Active",
                        "updated_at": "v1",
                    }
                ],
                "next": None,
            }
        ),
        encoding="utf-8",
    )
    db = tmp_path / "customers.sqlite"
    report = tmp_path / "report.json"

    first = sync_pages(FixturePageSource(fixture_dir).iter_pages(), db, report, "fixture")
    second = sync_pages(FixturePageSource(fixture_dir).iter_pages(), db, report, "fixture")

    assert first["inserted"] == 1 and first["updated"] == 0
    assert second["inserted"] == 0 and second["updated"] == 1
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT name, email, status FROM customers WHERE id = 1").fetchone()
        runs = conn.execute("SELECT COUNT(*) FROM sync_runs").fetchone()[0]
    assert row == ("Alice", "a@example.com", "active")
    assert runs == 2
    assert json.loads(report.read_text(encoding="utf-8"))["rows_in_database"] == 1
