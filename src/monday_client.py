"""Isolated monday.com GraphQL adapter (optional extension).

Design choices
  * Direct GraphQL over HTTPS (https://api.monday.com/v2) with an explicit API-Version header,
    stdlib only, so Crestview's team can read every request this code makes.
  * Idempotent upsert keyed on the Application ID text column (items_page_by_column_values):
    re-running updates the existing item instead of creating duplicates.
  * Governance: the "Compliance Decision" column is set to "Pending Human Review" only when an
    item is created. Updates never touch it, so a human decision recorded on the board is never
    overwritten by a pipeline rerun, and the pipeline has no code path that writes an approval.
  * Rate limits: monday returns errors carrying retry_in_seconds; we honour it with a bounded
    number of retries. Other GraphQL errors raise MondayAPIError for per-item reporting.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from .schemas import EnrichedRecord

log = logging.getLogger(__name__)

API_URL = "https://api.monday.com/v2"
BOARD_NAME = "Crestview - Client Onboarding POC"
COMPLIANCE_PENDING = "Pending Human Review"
LONG_TEXT_LIMIT = 2000  # monday long_text column limit (characters)

# (column id, title, type). IDs: lowercase + underscores, <= 20 chars, unique per board.
BOARD_COLUMNS: list[tuple[str, str, str]] = [
    ("app_id", "Application ID", "text"),
    ("client_type", "Client Type", "text"),
    ("aum_usd", "Est. AUM (USD)", "numbers"),
    ("submitted", "Submitted", "date"),
    ("ai_risk", "AI Risk Triage (advisory)", "status"),
    ("review_priority", "Review Priority", "status"),
    ("routing", "Routing", "status"),
    ("complexity", "Onboarding Complexity", "status"),
    ("compliance", "Compliance Decision", "status"),
    ("pipeline_status", "Pipeline Status", "status"),
    ("gaps", "Gaps / Blockers", "long_text"),
    ("next_actions", "Next Actions", "long_text"),
    ("summary", "AI Onboarding Summary", "long_text"),
    ("risk_evidence", "Risk Rationale & Evidence", "long_text"),
    ("provenance", "AI Provenance", "text"),
]
COLUMN_IDS = {c[0] for c in BOARD_COLUMNS}
CREATE_ONLY_COLUMNS = {"compliance"}


class MondayAPIError(Exception):
    pass


Transport = Callable[[dict, dict], tuple[int, dict, dict]]  # (payload, headers) -> (status, json, headers)


def urllib_transport(payload: dict, headers: dict, timeout: float = 30.0) -> tuple[int, dict, dict]:
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}"), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read() or b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"errors": [{"message": body.decode(errors="replace")[:300]}]}
        return exc.code, data, dict(exc.headers or {})


@dataclass
class UpsertResult:
    application_id: str
    action: str  # created | updated | failed
    item_id: str | None = None
    error: str | None = None


class MondayClient:
    def __init__(
        self,
        token: str,
        api_version: str = "2026-10",
        transport: Transport | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._headers = {"Authorization": token, "Content-Type": "application/json", "API-Version": api_version}
        self._transport = transport or urllib_transport
        self._max_retries = max_retries
        self._sleep = sleep

    def execute(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query, "variables": variables or {}}
        for attempt in range(self._max_retries + 1):
            status, body, headers = self._transport(payload, self._headers)
            errors = body.get("errors") or []
            retry_in = _retry_seconds(status, errors, headers)
            if retry_in is not None and attempt < self._max_retries:
                log.warning("monday rate limited; retrying in %.1fs", retry_in)
                self._sleep(min(retry_in, 60.0))
                continue
            if status == 401 or status == 403:
                raise MondayAPIError(f"HTTP {status}: check MONDAY_API_TOKEN permissions")
            if errors:
                raise MondayAPIError("; ".join(str(e.get("message", e)) for e in errors)[:500])
            if status >= 400:
                raise MondayAPIError(f"HTTP {status}")
            return body.get("data") or {}
        raise MondayAPIError("Rate limit retries exhausted")

    # ---- board setup / inspection ----------------------------------------------------------

    def create_board(self, name: str = BOARD_NAME) -> str:
        data = self.execute(
            "mutation ($name: String!) { create_board(board_name: $name, board_kind: private) { id } }",
            {"name": name},
        )
        return str(data["create_board"]["id"])

    def create_column(self, board_id: str, column_id: str, title: str, column_type: str) -> None:
        # column_type is an enum literal from our own constant list, never user input.
        assert column_type in {"text", "numbers", "date", "status", "long_text"}
        self.execute(
            f"mutation ($board: ID!, $title: String!, $id: String!) {{ create_column(board_id: $board, "
            f"title: $title, column_type: {column_type}, id: $id) {{ id }} }}",
            {"board": board_id, "title": title, "id": column_id},
        )

    def board_columns(self, board_id: str) -> dict[str, str]:
        data = self.execute("query ($ids: [ID!]) { boards(ids: $ids) { id name columns { id title type } } }", {"ids": [board_id]})
        boards = data.get("boards") or []
        if not boards:
            raise MondayAPIError(f"Board {board_id} not found or not accessible with this token")
        return {c["id"]: c["type"] for c in boards[0]["columns"]}

    def verify_schema(self, board_id: str) -> list[str]:
        """Return problems with the board schema (missing columns / wrong types)."""
        existing = self.board_columns(board_id)
        problems = []
        for cid, title, ctype in BOARD_COLUMNS:
            if cid not in existing:
                problems.append(f"missing column {cid!r} ({title})")
            elif existing[cid] != ctype:
                problems.append(f"column {cid!r} has type {existing[cid]!r}, expected {ctype!r}")
        return problems

    # ---- items -----------------------------------------------------------------------------

    def find_item_by_app_id(self, board_id: str, app_id: str) -> str | None:
        data = self.execute(
            "query ($board: ID!, $val: String!) { items_page_by_column_values(board_id: $board, limit: 5, "
            'columns: [{column_id: "app_id", column_values: [$val]}]) { items { id name } } }',
            {"board": board_id, "val": app_id},
        )
        items = (data.get("items_page_by_column_values") or {}).get("items") or []
        if len(items) > 1:
            log.warning("Duplicate items for %s on board %s: %s", app_id, board_id, [i["id"] for i in items])
        return str(items[0]["id"]) if items else None

    def upsert(self, board_id: str, rec: EnrichedRecord) -> UpsertResult:
        try:
            item_id = self.find_item_by_app_id(board_id, rec.application_id)
            values = column_values(rec, include_create_only=item_id is None)
            if item_id is None:
                data = self.execute(
                    "mutation ($board: ID!, $name: String!, $vals: JSON!) { create_item(board_id: $board, "
                    "item_name: $name, column_values: $vals, create_labels_if_missing: true) { id } }",
                    {"board": board_id, "name": rec.source.client_name, "vals": json.dumps(values)},
                )
                return UpsertResult(rec.application_id, "created", str(data["create_item"]["id"]))
            self.execute(
                "mutation ($board: ID!, $item: ID!, $vals: JSON!) { change_multiple_column_values(board_id: $board, "
                "item_id: $item, column_values: $vals, create_labels_if_missing: true) { id } }",
                {"board": board_id, "item": item_id, "vals": json.dumps(values)},
            )
            return UpsertResult(rec.application_id, "updated", item_id)
        except MondayAPIError as exc:
            return UpsertResult(rec.application_id, "failed", error=str(exc))


def _retry_seconds(status: int, errors: list[dict], headers: dict) -> float | None:
    for e in errors:
        ext = e.get("extensions") or {}
        secs = ext.get("retry_in_seconds", e.get("retry_in_seconds"))
        if secs is not None:
            return float(secs)
        code = str(ext.get("code", ""))
        if code in {"COMPLEXITY_BUDGET_EXHAUSTED", "RATE_LIMIT_EXCEEDED", "ComplexityException"}:
            return 5.0
    if status == 429:
        try:
            return float(headers.get("Retry-After") or headers.get("retry-after") or 5)
        except ValueError:
            return 5.0
    return None


# ---- mapping ---------------------------------------------------------------------------------


def _label(value: str) -> dict:
    # Status labels are max 30 characters.
    return {"label": value.replace("_", " ").title()[:30]}


def _clip(text: str) -> str:
    return text if len(text) <= LONG_TEXT_LIMIT else text[: LONG_TEXT_LIMIT - 20] + "\n[...truncated]"


def column_values(rec: EnrichedRecord, include_create_only: bool = True) -> dict:
    risk, summ = rec.risk_assessment, rec.onboarding_summary
    values: dict = {
        "app_id": rec.application_id,
        "client_type": rec.source.client_type,
        "ai_risk": _label(rec.triage_risk_level.value),
        "review_priority": _label(rec.review_priority.value if rec.review_priority else "NOT_AVAILABLE"),
        "routing": _label(rec.routing.value),
        "pipeline_status": _label(rec.processing_status.value),
    }
    if rec.source.estimated_aum.strip().isdigit():
        values["aum_usd"] = rec.source.estimated_aum.strip()
    try:
        m, d, y = rec.source.submission_date.split("/")
        values["submitted"] = {"date": f"{y}-{int(m):02d}-{int(d):02d}"}
    except ValueError:
        pass
    if summ:
        values["complexity"] = _label(summ.onboarding_complexity.value)
        values["summary"] = {"text": _clip(summ.summary_text)}
        values["next_actions"] = {
            "text": _clip(
                "\n".join(
                    f"- [{a.suggested_owner.value}] {a.action}{' (BLOCKS ACCOUNT OPENING)' if a.blocks_account_opening else ''}"
                    for a in summ.next_actions
                )
            )
        }
    gaps: list[str] = []
    if risk:
        gaps += [f"- {m.item} [{m.status.value.replace('_', ' ').lower()}]" for m in risk.missing_information]
        evidence = "\n".join(f'- [{f.severity.value}] {f.factor}: "{f.source_evidence}"' for f in risk.risk_factors)
        values["risk_evidence"] = {"text": _clip(f"{risk.rationale}\n\nEvidence:\n{evidence or '- none identified'}")}
    gaps += [f"! {w}" for w in rec.warnings] + [f"x {e.stage}: {e.message}" for e in rec.errors]
    if gaps:
        values["gaps"] = {"text": _clip("\n".join(gaps))}
    models = ",".join(sorted({c.model_responded or c.model_requested for c in rec.llm_calls})) or "none"
    values["provenance"] = f"{models} | {rec.prompt_versions.get('risk_assessment', '')} | {rec.processed_at}"[:250]
    if include_create_only:
        values["compliance"] = {"label": COMPLIANCE_PENDING}
    assert set(values) <= COLUMN_IDS, set(values) - COLUMN_IDS
    return values

