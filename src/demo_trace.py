"""Read-only trace of a previously recorded POC case for interview demonstrations.

Usage:
    python -m src.demo_trace --application-id APP-2026-0303
    python -m src.demo_trace --input output/adversarial/enriched_applications.json --application-id APP-2026-0901

No LLM calls, monday.com API calls, imports of live clients, or writes.
This displays existing run artifacts; it does not process an application live.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_case(path: Path, application_id: str) -> tuple[dict, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise ValueError("Expected enriched run JSON with a records list")
    matches = [r for r in data["records"] if isinstance(r, dict) and r.get("application_id") == application_id]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one record for {application_id}; found {len(matches)}")
    return data.get("run") or {}, matches[0]


def render_trace(run: dict, rec: dict, max_factors: int = 2) -> str:
    source = rec.get("source") or {}
    risk = rec.get("risk_assessment") or {}
    summary = rec.get("onboarding_summary") or {}
    guard = rec.get("guardrails") or {}
    checks = guard.get("evidence_checks") or []
    flag_count = len(guard.get("policy_flags") or [])
    verified_count = sum(c.get("verified_in_source") is True for c in checks)
    factors = risk.get("risk_factors") or []
    actions = summary.get("next_actions") or []
    warnings = rec.get("warnings") or []
    errors = rec.get("errors") or []
    lines = [
        "RECORDED CASE TRACE — NOT A LIVE MODEL RUN",
        f"Run: {run.get('run_id', 'unknown')} | Case: {rec.get('application_id', 'unknown')}",
        f"Client: {source.get('client_name', 'unknown')}",
        "",
        "INPUT — eight structured CSV fields",
        "application_id, client_name, client_type, requested_services, estimated_aum,",
        "submission_date, status, description (source text; not independently verified)",
        "",
        "STAGE 1 — Claude risk assessment → validated RiskAssessment JSON",
        f"Advisory risk: {risk.get('risk_level', 'unavailable')} | Priority: {risk.get('review_priority', 'unavailable')}",
        f"Routing: {rec.get('routing', 'unavailable')}",
    ]
    for i, factor in enumerate(factors[:max_factors], 1):
        lines.append(f"  Factor {i}: {factor.get('factor', '')}")
        lines.append(f"  Source quote: {factor.get('source_evidence', '')}")
    if len(factors) > max_factors:
        lines.append(f"  (+{len(factors) - max_factors} more factors in stored result)")
    lines.extend([
        "",
        "DETERMINISTIC CHECKS — after Stage 1",
        f"Source quotes matched: {verified_count}/{len(checks)} (presence, not correctness of interpretation)",
        f"Prohibited-claim flags: {flag_count} | Warnings: {len(warnings)} | Errors: {len(errors)}",
        "IMPORTANT: Unverified quotes may be warnings without automatically changing routing.",
        "",
        "STAGE 2 — original application + Stage 1 JSON → OnboardingSummary JSON",
        f"Stage 1 level acknowledged: {summary.get('risk_level_acknowledged', 'unavailable')}",
        f"Operational complexity: {summary.get('onboarding_complexity', 'unavailable')}",
        f"Summary: {summary.get('summary_text', 'unavailable')}",
    ])
    for action in actions[:3]:
        lines.append(
            f"  - [{action.get('suggested_owner', 'unassigned')}] {action.get('action', '')}"
            + (" [BLOCKS ACCOUNT OPENING]" if action.get("blocks_account_opening") else "")
        )
    if len(actions) > 3:
        lines.append(f"  (+{len(actions) - 3} more actions in stored result)")
    stage1_hash = rec.get("risk_assessment_sha256")
    consumed_hash = rec.get("summary_consumed_risk_sha256")
    lineage = "matched" if stage1_hash and stage1_hash == consumed_hash else "unavailable / mismatch"
    lines.extend([
        "",
        f"LINEAGE — Stage 2 input matches stored Stage 1 serialization: {lineage}",
        f"FINAL — processing status: {rec.get('processing_status', 'unknown')}",
        f"Human review: {rec.get('human_review_status', 'not recorded')}",
        "monday.com sync is a SEPARATE command; this trace makes no network calls or changes.",
    ])
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in warnings[:3])
    if errors:
        lines.append("Errors:")
        lines.extend(f"  - {e.get('stage', 'unknown')}: {e.get('kind', 'unknown')}" for e in errors[:3])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect existing, fictional POC results without calling APIs")
    parser.add_argument("--input", type=Path, default=Path("output/enriched_applications.json"))
    parser.add_argument("--application-id", required=True)
    parser.add_argument("--max-factors", type=int, choices=range(1, 6), default=2, metavar="1..5")
    args = parser.parse_args(argv)
    try:
        run, record = load_case(args.input, args.application_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(render_trace(run, record, args.max_factors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
