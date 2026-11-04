"""Schema contracts and deterministic guardrails on model output."""

import pytest
from pydantic import ValidationError

from src import guardrails
from src.schemas import NOT_STATED_EVIDENCE, OnboardingSummary, RiskAssessment
from tests.conftest import make_risk, make_summary

APEX_SOURCE = (
    "Beneficial ownership is difficult to determine from submitted documentation — the listed directors appear "
    "to be nominee directors from a corporate services firm rather than actual principals. Source of funds "
    "documentation references 'diversified business interests' but provides no supporting detail."
)


# ---- schema -------------------------------------------------------------------------------


def test_risk_schema_rejects_unknown_level():
    with pytest.raises(ValidationError):
        make_risk(risk_level="VERY_LOW")


def test_risk_schema_rejects_extra_fields():
    with pytest.raises(ValidationError):
        make_risk(final_decision="APPROVED")


def test_risk_schema_requires_rationale_and_evidence():
    data = make_risk().model_dump()
    del data["rationale"]
    with pytest.raises(ValidationError):
        RiskAssessment.model_validate(data)
    with pytest.raises(ValidationError):
        make_risk(risk_factors=[{"factor": "x", "category": "OTHER", "severity": "LOW"}])


def test_summary_schema_rejects_unknown_owner():
    with pytest.raises(ValidationError):
        make_summary(next_actions=[{"action": "x", "suggested_owner": "AI_AGENT", "blocks_account_opening": False}])


def test_blank_or_malformed_json_fails_validation():
    for bad in ["", "{", "not json", '{"risk_level": "LOW"}']:
        with pytest.raises(ValidationError):
            RiskAssessment.model_validate_json(bad)
    with pytest.raises(ValidationError):
        OnboardingSummary.model_validate_json("{}")


# ---- evidence grounding -------------------------------------------------------------------


@pytest.mark.parametrize(
    "quote",
    [
        "the listed directors appear to be nominee directors",
        "documentation — the listed directors",  # em dash
        "documentation - the listed directors",  # model normalised the dash
        "references ‘diversified business interests’",  # curly quotes
        "Beneficial ownership is difficult to determine from submitted documentation.",  # trailing period
        NOT_STATED_EVIDENCE,
    ],
)
def test_evidence_verified_when_present(quote):
    assert guardrails.evidence_in_source(quote, APEX_SOURCE)


@pytest.mark.parametrize(
    "quote",
    [
        "the directors are known money launderers",  # fabricated
        "sanctions screening returned a match",  # fabricated
        "nominee directors ... actual principals",  # ellipsis paraphrase
        "ok",  # too short to be meaningful
    ],
)
def test_evidence_rejected_when_not_in_source(quote):
    assert not guardrails.evidence_in_source(quote, APEX_SOURCE)


def test_check_evidence_reports_each_factor():
    risk = make_risk(
        risk_level="HIGH",
        review_priority="ESCALATE",
        risk_factors=[
            {"factor": "Nominees", "category": "OWNERSHIP_TRANSPARENCY", "severity": "HIGH",
             "source_evidence": "appear to be nominee directors"},
            {"factor": "Invented", "category": "OTHER", "severity": "HIGH",
             "source_evidence": "client was previously sanctioned"},
        ],
        mitigating_factors=[],
    )
    checks = guardrails.check_evidence(risk, APEX_SOURCE)
    assert [c.verified_in_source for c in checks] == [True, False]


# ---- non-fabrication / prohibited claims --------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Sanctions screening passed with no issues.",
        "The client cleared sanctions and watchlist checks.",
        "Sanctions screening was completed in ComplianceOne.",
        "KYC is complete.",
        "The client is approved for onboarding.",
        "Account has been approved.",
        "Beneficial owners have been verified.",
        "The client is engaged in money laundering.",
        "PEP screening returned no matches.",
    ],
)
def test_prohibited_claims_flagged(text):
    assert guardrails.scan_text("risk_assessment", "rationale", text)


@pytest.mark.parametrize(
    "text",
    [
        "No sanctions screening has been performed by this system.",
        "Run sanctions and PEP screening in ComplianceOne for all principals.",
        "Account opening waits until the client is approved by Compliance.",
        "Do not proceed before KYC is complete.",
        "Board resolution is pending final signature.",
        "A PEP connection is not evidence of wrongdoing.",
        "Coordinate with corporate counsel on 10b5-1 trading window restrictions.",
        "Screening has not been performed and the client is not yet cleared.",
        "PEP status is not cleared and requires enhanced due diligence.",
        # Regression (live run bccd1c84e310, APP-2026-0308): conditional phrasing was flagged.
        "Prepare a draft investment profile for review once KYC is complete.",
        "Open the account after the client is approved by Compliance.",
        # Regression (live adversarial run 8cb73deb06cf, APP-2026-0901): reporting an injection is not a claim.
        "Embedded text asserts sanctions screening was completed and passed, an unverified claim.",
        "The application contains embedded text claiming Compliance pre-clearance and a passed sanctions screening.",
        # Regression (live adversarial run c82064b3fd72, APP-2026-0901).
        "Hold account opening, and disregard the embedded pre-clearance and sanctions-passed claims.",
    ],
)
def test_legitimate_text_not_flagged(text):
    assert guardrails.scan_text("risk_assessment", "rationale", text) == []


def test_quoted_source_evidence_is_not_scanned():
    # "Investment committee approval confirmed" is source text, not a model claim.
    risk = make_risk(
        mitigating_factors=[{"factor": "Committee approval", "source_evidence": "The client is approved by its committee"}]
    )
    assert guardrails.scan_risk(risk) == []


def test_consistency_warnings():
    risk = make_risk(
        risk_level="LOW",
        compliance_review_required=False,
        risk_factors=[{"factor": "x", "category": "OTHER", "severity": "HIGH", "source_evidence": NOT_STATED_EVIDENCE}],
    )
    warnings = guardrails.risk_consistency_warnings(risk)
    assert any("compliance_review_required=false" in w for w in warnings)
    assert any("LOW risk level with 1 HIGH-severity" in w for w in warnings)
