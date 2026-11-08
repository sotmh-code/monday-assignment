"""Read-only recorded-case trace tests: no model or monday credentials needed."""
import json

import pytest

from src.demo_trace import load_case, main, render_trace


def sample_record():
    return {
        "application_id": "APP-2026-0303",
        "source": {"client_name": "Apex", "description": "Ownership is opaque."},
        "risk_assessment": {
            "risk_level": "HIGH", "review_priority": "ESCALATE",
            "risk_factors": [{"factor": "Opaque ownership", "source_evidence": "Ownership is opaque."}],
        },
        "onboarding_summary": {
            "risk_level_acknowledged": "HIGH", "onboarding_complexity": "MEDIUM",
            "summary_text": "Refer to Compliance.",
            "next_actions": [{"suggested_owner": "COMPLIANCE", "action": "Review ownership", "blocks_account_opening": True}],
        },
        "guardrails": {"evidence_checks": [{"verified_in_source": True}], "policy_flags": []},
        "routing": "COMPLIANCE_ESCALATION",
        "risk_assessment_sha256": "abc", "summary_consumed_risk_sha256": "abc",
        "processing_status": "COMPLETED", "human_review_status": "PENDING_HUMAN_REVIEW",
    }


def test_trace_shows_stage_contracts_without_implying_live_processing():
    result = render_trace({"run_id": "run1"}, sample_record())
    assert "RECORDED CASE TRACE — NOT A LIVE MODEL RUN" in result
    assert "eight structured CSV fields" in result
    assert "Claude risk assessment" in result
    assert "Source quotes matched: 1/1" in result
    assert "Stage 1 level acknowledged: HIGH" in result
    assert "[BLOCKS ACCOUNT OPENING]" in result
    assert "matched" in result
    assert "Unverified quotes may be warnings" in result
    assert "no network calls" in result


def test_trace_missing_stage_is_explicit():
    rec = sample_record()
    rec["onboarding_summary"] = None
    rec["processing_status"] = "FAILED_SUMMARY"
    rec["warnings"] = ["Stage 2 failed"]
    output = render_trace({}, rec)
    assert "unavailable" in output
    assert "FAILED_SUMMARY" in output
    assert "Stage 2 failed" in output


def test_cli_reads_case_and_does_not_modify_input(tmp_path, capsys):
    path = tmp_path / "recorded.json"
    original = json.dumps({"run": {"run_id": "run1"}, "records": [sample_record()]})
    path.write_text(original, encoding="utf-8")
    assert main(["--input", str(path), "--application-id", "APP-2026-0303"]) == 0
    assert "Apex" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == original


def test_cli_unknown_case_fails_clear(tmp_path):
    path = tmp_path / "recorded.json"
    path.write_text(json.dumps({"records": [sample_record()]}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--input", str(path), "--application-id", "APP-2026-9999"])
    assert exc.value.code == 2


def test_load_case_rejects_bad_format(tmp_path):
    path = tmp_path / "recorded.json"
    path.write_text(json.dumps({"not_records": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="records list"):
        load_case(path, "APP-2026-0303")
