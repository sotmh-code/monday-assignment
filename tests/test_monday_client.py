"""monday.com adapter tests with an in-memory fake GraphQL board (no network)."""

import json

from src.monday_client import BOARD_COLUMNS, COMPLIANCE_PENDING, MondayClient, column_values
from src.pipeline import run_batch
from tests.conftest import FakeLLM


class FakeBoard:
    """Minimal stand-in for the monday GraphQL API, enough to exercise upsert semantics."""

    def __init__(self):
        self.items: dict[str, dict] = {}
        self.calls: list[dict] = []
        self.rate_limit_next = 0
        self.columns = [{"id": c, "title": t, "type": ty} for c, t, ty in BOARD_COLUMNS]

    def __call__(self, payload, headers):
        self.calls.append({"payload": payload, "headers": headers})
        if self.rate_limit_next:
            self.rate_limit_next -= 1
            return 200, {"errors": [{"message": "Complexity budget exhausted",
                                     "extensions": {"code": "COMPLEXITY_BUDGET_EXHAUSTED", "retry_in_seconds": 1}}]}, {}
        q, v = payload["query"], payload["variables"]
        if "boards(ids" in q:
            return 200, {"data": {"boards": [{"id": "1", "name": "b", "columns": self.columns}]}}, {}
        if "items_page_by_column_values" in q:
            hits = [{"id": i, "name": it["name"]} for i, it in self.items.items() if it["values"].get("app_id") == v["val"]]
            return 200, {"data": {"items_page_by_column_values": {"items": hits}}}, {}
        if "create_item" in q:
            item_id = str(100 + len(self.items))
            self.items[item_id] = {"name": v["name"], "values": json.loads(v["vals"])}
            return 200, {"data": {"create_item": {"id": item_id}}}, {}
        if "change_multiple_column_values" in q:
            self.items[v["item"]]["values"].update(json.loads(v["vals"]))
            return 200, {"data": {"change_multiple_column_values": {"id": v["item"]}}}, {}
        return 200, {"errors": [{"message": "unsupported query in fake"}]}, {}


def _records(sample_apps, n=3):
    return run_batch(sample_apps[:n], FakeLLM())


def test_upsert_is_idempotent_and_never_duplicates(sample_apps):
    board = FakeBoard()
    client = MondayClient("tok", transport=board, sleep=lambda s: None)
    recs = _records(sample_apps)
    first = [client.upsert("1", r).action for r in recs]
    second = [client.upsert("1", r).action for r in recs]
    assert first == ["created"] * 3
    assert second == ["updated"] * 3
    assert len(board.items) == 3


def test_human_compliance_decision_is_not_overwritten_on_rerun(sample_apps):
    board = FakeBoard()
    client = MondayClient("tok", transport=board, sleep=lambda s: None)
    rec = _records(sample_apps, 1)[0]
    item_id = client.upsert("1", rec).item_id
    assert board.items[item_id]["values"]["compliance"] == {"label": COMPLIANCE_PENDING}
    board.items[item_id]["values"]["compliance"] = {"label": "Approved by Compliance"}  # a human acts on the board
    client.upsert("1", rec)
    assert board.items[item_id]["values"]["compliance"] == {"label": "Approved by Compliance"}


def test_pipeline_never_writes_an_approval(sample_apps):
    for rec in _records(sample_apps, 15):
        create, update = column_values(rec, include_create_only=True), column_values(rec, include_create_only=False)
        assert create["compliance"] == {"label": COMPLIANCE_PENDING}
        assert "compliance" not in update
        labels = [v["label"].lower() for v in create.values() if isinstance(v, dict) and "label" in v]
        assert not any("approv" in lbl or "clear" in lbl for lbl in labels)


def test_column_value_formats(sample_apps):
    rec = _records(sample_apps, 1)[0]
    v = column_values(rec)
    assert v["app_id"] == "APP-2026-0301"
    assert v["aum_usd"] == "750000000"
    assert v["submitted"] == {"date": "2026-01-06"}
    assert v["ai_risk"] == {"label": "Low"}
    assert set(v["summary"]) == {"text"}
    assert all(len(x["label"]) <= 30 for x in v.values() if isinstance(x, dict) and "label" in x)
    assert all(len(x["text"]) <= 2000 for x in v.values() if isinstance(x, dict) and "text" in x)


def test_rate_limit_retry_in_seconds_is_honoured(sample_apps):
    board = FakeBoard()
    board.rate_limit_next = 2
    slept = []
    client = MondayClient("tok", transport=board, sleep=slept.append)
    res = client.upsert("1", _records(sample_apps, 1)[0])
    assert res.action == "created"
    assert slept == [1.0, 1.0]


def test_api_errors_are_reported_per_item_not_raised(sample_apps):
    def broken(payload, headers):
        return 200, {"errors": [{"message": "Column not found"}]}, {}

    res = MondayClient("tok", transport=broken).upsert("1", _records(sample_apps, 1)[0])
    assert res.action == "failed" and "Column not found" in res.error


def test_headers_and_schema_check(sample_apps):
    board = FakeBoard()
    client = MondayClient("secret-token", api_version="2026-10", transport=board)
    assert client.verify_schema("1") == []
    assert board.calls[0]["headers"]["API-Version"] == "2026-10"
    assert board.calls[0]["headers"]["Authorization"] == "secret-token"
    board.columns = board.columns[:-1]
    assert client.verify_schema("1") == ["missing column 'provenance' (AI Provenance)"]
