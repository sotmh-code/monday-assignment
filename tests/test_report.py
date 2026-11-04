"""Offline dashboard tests. No model API calls, browser, or third-party dependencies."""
import json

import pytest

from src.report import generate, render_html


def _record(app_id="APP-2026-0303", name='Apex <script>alert("x")</script>'):
    return {
        "application_id": app_id,
        "source": {
            "client_name": name,
            "client_type": "Corporate",
            "requested_services": "Investment management",
            "estimated_aum": "500000000",
            "description": 'The <script>test</script> document names nominee directors.',
        },
        "processing_status": "COMPLETED",
        "triage_risk_level": "HIGH",
        "routing": "COMPLIANCE_ESCALATION",
        "human_review_status": "PENDING_HUMAN_REVIEW",
        "risk_assessment": {
            "risk_level": "HIGH",
            "review_priority": "ESCALATE",
            "rationale": "The description contains ownership concerns.",
            "risk_factors": [{
                "factor": "Nominee directors",
                "source_evidence": "nominee directors",
                "severity": "HIGH",
                "category": "OWNERSHIP_TRANSPARENCY",
            }],
            "missing_information": [{"item": "Beneficial owner identity", "status": "NOT_STATED_IN_APPLICATION"}],
            "mitigating_factors": [],
        },
        "onboarding_summary": {
            "summary_text": "Operations should ask for beneficial ownership documentation.",
            "risk_level_acknowledged": "HIGH",
            "onboarding_complexity": "LOW",
            "next_actions": [{
                "suggested_owner": "COMPLIANCE",
                "action": "Review ownership evidence",
                "blocks_account_opening": True,
            }],
        },
        "guardrails": {
            "evidence_checks": [{"kind": "risk_factor", "index": 0, "verified_in_source": True}],
            "unverified_evidence_count": 0,
            "policy_flags": [],
        },
        "warnings": [],
        "errors": [],
        "summary_consumed_risk_sha256": "internal-audit-only",
    }


def _output(records):
    return {"run": {"run_id": "test123", "model_requested": "fake"}, "records": records}


def test_render_dashboard_escapes_untrusted_application_text():
    text = render_html(_output([_record()]))
    assert "<script>alert" not in text
    assert "&lt;script&gt;alert" in text
    assert "&lt;script&gt;test&lt;/script&gt;" in text
    assert "Summary acknowledges Stage 1 triage" in text
    assert "Blocks account opening" in text
    assert "Pending human review" not in text or "Human Compliance" in text


def test_exports_stage_1_and_stage_2_as_separate_files(tmp_path):
    full = tmp_path / "enriched_applications.json"
    full.write_text(json.dumps(_output([_record()])), encoding="utf-8")
    html_file, risk_file, summary_file = generate(full)

    assert html_file.exists() and risk_file.exists() and summary_file.exists()
    risk = json.loads(risk_file.read_text())
    summary = json.loads(summary_file.read_text())
    assert risk["stage"] == "risk_assessment"
    assert risk["records"][0]["risk_assessment"]["risk_level"] == "HIGH"
    assert summary["stage"] == "onboarding_summary"
    assert summary["records"][0]["stage_1_risk_assessment_used"] == risk["records"][0]["risk_assessment"]
    assert summary["records"][0]["onboarding_summary"]["risk_level_acknowledged"] == "HIGH"
    assert "internal-audit-only" not in html_file.read_text()


def test_manual_review_and_failure_are_visible():
    rec = _record()
    rec["processing_status"] = "FAILED_SUMMARY"
    rec["onboarding_summary"] = None
    rec["triage_risk_level"] = "NEEDS_REVIEW"
    rec["warnings"] = ["Failed output validation"]
    text = render_html(_output([rec]))
    assert "summary unavailable" in text
    assert "Failed output validation" in text
    assert "Compliance decision: pending" in text
    assert "No network calls" in text


def test_nonempty_records_required(tmp_path):
    with pytest.raises(ValueError, match="No application records"):
        render_html(_output([]))
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(_output([])), encoding="utf-8")
    with pytest.raises(ValueError, match="no records"):
        generate(path)


def test_report_can_render_multiple_risks_and_filters():
    rec1 = _record("APP-2026-0303", "Apex")
    rec2 = _record("APP-2026-0310", "Heritage")
    rec2["triage_risk_level"] = "LOW"
    rec2["risk_assessment"]["risk_level"] = "LOW"
    html = render_html(_output([rec1, rec2]))
    assert 'data-risk="HIGH"' in html
    assert 'data-risk="LOW"' in html
    assert 'data-detail="APP-2026-0303"' in html
    assert 'data-detail="APP-2026-0310"' in html
    assert "2</b><small>Applications" in html
