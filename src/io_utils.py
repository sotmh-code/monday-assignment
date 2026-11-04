"""CSV loading/validation and JSON/CSV export.

File-level problems (wrong header, duplicate IDs, unreadable file) reject the whole input.
Row-level problems (blank description, unparseable AUM/date) keep the row but mark it so the
pipeline records it explicitly instead of sending it to the model or dropping it.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from .schemas import EXPECTED_COLUMNS, Application, EnrichedRecord, RunOutput

APPLICATION_ID_RE = re.compile(r"^APP-\d{4}-\d{4}$")
MIN_DESCRIPTION_CHARS = 20


class InputValidationError(Exception):
    """The input file as a whole cannot be trusted; nothing should be processed."""


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _parse_date(raw: str) -> datetime | None:
    # Source data uses month/day/year (e.g. 01/06/2026 = 6 January 2026).
    try:
        return datetime.strptime(raw.strip(), "%m/%d/%Y")
    except ValueError:
        return None


def load_applications(path: str | Path, expected_count: int | None = None) -> list[Application]:
    path = Path(path)
    if not path.is_file():
        raise InputValidationError(f"Input file not found: {path}")

    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, strict=True)
            header = reader.fieldnames or []
            if header != EXPECTED_COLUMNS:
                raise InputValidationError(
                    f"Unexpected CSV header. Expected {EXPECTED_COLUMNS}, got {header}"
                )
            rows = list(reader)
    except csv.Error as exc:
        raise InputValidationError(f"Malformed CSV: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InputValidationError(f"Input is not valid UTF-8: {exc}") from exc

    applications: list[Application] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        if None in row or any(v is None for v in row.values()):
            raise InputValidationError(f"Row {i} has the wrong number of fields")

        app_id = row["application_id"].strip()
        if not APPLICATION_ID_RE.match(app_id):
            raise InputValidationError(f"Row {i}: invalid application_id {app_id!r}")
        if app_id in seen:
            raise InputValidationError(f"Row {i}: duplicate application_id {app_id}")
        seen.add(app_id)

        issues: list[str] = []
        description = row["description"]
        if len(description.strip()) < MIN_DESCRIPTION_CHARS:
            issues.append("description is blank or too short to triage")
        if not row["client_name"].strip():
            issues.append("client_name is blank")

        aum_raw = row["estimated_aum"]
        try:
            aum = int(aum_raw.strip())
            if aum <= 0:
                issues.append(f"estimated_aum must be positive, got {aum_raw!r}")
        except ValueError:
            aum = None
            issues.append(f"estimated_aum is not an integer: {aum_raw!r}")

        date_raw = row["submission_date"]
        parsed = _parse_date(date_raw)
        if parsed is None:
            issues.append(f"submission_date is not MM/DD/YYYY: {date_raw!r}")

        applications.append(
            Application(
                row_number=i,
                application_id=app_id,
                client_name=row["client_name"],
                client_type=row["client_type"],
                requested_services=row["requested_services"],
                estimated_aum_raw=aum_raw,
                estimated_aum=aum,
                submission_date_raw=date_raw,
                submission_date=parsed.date() if parsed else None,
                status=row["status"],
                description=description,
                input_issues=issues,
            )
        )

    if not applications:
        raise InputValidationError("Input file contains no applications")
    if expected_count is not None and len(applications) != expected_count:
        raise InputValidationError(f"Expected {expected_count} applications, found {len(applications)}")
    return applications


def format_aum(amount: int | None) -> str:
    if amount is None:
        return "unknown"
    if amount >= 1_000_000_000:
        value, unit = amount / 1_000_000_000, "B"
    elif amount >= 1_000_000:
        value, unit = amount / 1_000_000, "M"
    else:
        return f"${amount:,}"
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"${text}{unit}"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "application_id",
    "client_name",
    "client_type",
    "requested_services",
    "estimated_aum",
    "submission_date",
    "source_status",
    "processing_status",
    "triage_risk_level",
    "review_priority",
    "routing",
    "human_review_status",
    "compliance_review_required",
    "onboarding_complexity",
    "risk_factors",
    "missing_information",
    "rationale",
    "next_actions",
    "summary_text",
    "unverified_evidence_count",
    "policy_flag_count",
    "warnings",
    "errors",
    "model",
    "prompt_versions",
    "processed_at",
    "advisory_notice",
    "description",
]


def _join(items: list[str]) -> str:
    return " | ".join(items)


def record_to_csv_row(rec: EnrichedRecord) -> dict[str, str]:
    risk = rec.risk_assessment
    summ = rec.onboarding_summary
    models = sorted({c.model_responded or c.model_requested for c in rec.llm_calls})
    return {
        "application_id": rec.application_id,
        "client_name": rec.source.client_name,
        "client_type": rec.source.client_type,
        "requested_services": rec.source.requested_services,
        "estimated_aum": rec.source.estimated_aum,
        "submission_date": rec.source.submission_date,
        "source_status": rec.source.status,
        "processing_status": rec.processing_status.value,
        "triage_risk_level": rec.triage_risk_level.value,
        "review_priority": rec.review_priority.value if rec.review_priority else "",
        "routing": rec.routing.value,
        "human_review_status": rec.human_review_status,
        "compliance_review_required": str(rec.compliance_review_required).lower(),
        "onboarding_complexity": summ.onboarding_complexity.value if summ else "",
        "risk_factors": _join(
            [f"[{f.severity.value}] {f.factor} (evidence: \"{f.source_evidence}\")" for f in risk.risk_factors]
        )
        if risk
        else "",
        "missing_information": _join([f"{m.item} [{m.status.value}]" for m in risk.missing_information]) if risk else "",
        "rationale": risk.rationale if risk else "",
        "next_actions": _join(
            [
                f"{a.action} (owner: {a.suggested_owner.value}{'; BLOCKING' if a.blocks_account_opening else ''})"
                for a in summ.next_actions
            ]
        )
        if summ
        else "",
        "summary_text": summ.summary_text if summ else "",
        "unverified_evidence_count": str(rec.guardrails.unverified_evidence_count),
        "policy_flag_count": str(len(rec.guardrails.policy_flags)),
        "warnings": _join(rec.warnings),
        "errors": _join([f"{e.stage}:{e.kind}: {e.message}" for e in rec.errors]),
        "model": ",".join(models),
        "prompt_versions": ",".join(f"{k}={v}" for k, v in sorted(rec.prompt_versions.items())),
        "processed_at": rec.processed_at,
        "advisory_notice": rec.advisory_notice,
        "description": rec.source.description,
    }


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_outputs(output: RunOutput, output_dir: str | Path, stem: str = "enriched_applications") -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    json_path = output_dir / f"{stem}.json"
    csv_path = output_dir / f"{stem}.csv"

    _atomic_write(json_path, output.model_dump_json(indent=2) + "\n")

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for rec in output.records:
        writer.writerow(record_to_csv_row(rec))
    _atomic_write(csv_path, buf.getvalue())
    return json_path, csv_path


def read_run_output(path: str | Path) -> RunOutput:
    return RunOutput.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
