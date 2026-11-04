"""Shared fixtures: a scripted fake LLM that records every call (a spy) and canned model outputs."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.io_utils import load_applications
from src.llm_client import LLMError, LLMResult
from src.schemas import (
    Application,
    OnboardingSummary,
    RiskAssessment,
)

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = ROOT / "crestview_client_applications.csv"


def make_risk(**overrides) -> RiskAssessment:
    data = {
        "risk_level": "LOW",
        "review_priority": "STANDARD",
        "risk_factors": [],
        "mitigating_factors": [
            {"factor": "Existing relationship", "source_evidence": "Existing relationship with our fixed income team"}
        ],
        "missing_information": [{"item": "Sanctions screening results", "status": "NOT_STATED_IN_APPLICATION"}],
        "operational_complexity_notes": [],
        "rationale": "Public pension fund with a stated complete documentation package and an existing relationship.",
        "compliance_review_required": True,
        "suggested_next_steps": ["Run standard sanctions and PEP screening in ComplianceOne"],
    }
    data.update(overrides)
    return RiskAssessment.model_validate(data)


def make_summary(**overrides) -> OnboardingSummary:
    data = {
        "client_overview": "State pension fund allocating $750M.",
        "service_needs": ["Equity management", "Fixed income management"],
        "onboarding_complexity": "LOW",
        "complexity_drivers": ["Two strategies"],
        "risk_level_acknowledged": "LOW",
        "risk_context": "Standard KYC review by Compliance is still required before account opening.",
        "documentation_or_review_gaps": ["Screening not yet performed"],
        "next_actions": [
            {"action": "Submit standard KYC review request", "suggested_owner": "COMPLIANCE", "blocks_account_opening": True},
            {"action": "Prepare account setup forms", "suggested_owner": "CLIENT_OPERATIONS", "blocks_account_opening": False},
            {"action": "Confirm timeline with client", "suggested_owner": "RELATIONSHIP_MANAGER", "blocks_account_opening": False},
        ],
        "summary_text": "Standard institutional onboarding pending standard KYC review.",
    }
    data.update(overrides)
    return OnboardingSummary.model_validate(data)


@dataclass
class Call:
    system: str
    user: str
    schema: type
    purpose: str


Responder = Callable[[Call], object]  # returns a BaseModel instance or raises LLMError


class FakeLLM:
    """Scripted StructuredLLM. `responder` decides the output per call; every call is recorded."""

    model = "fake-model"

    def __init__(self, responder: Responder | None = None) -> None:
        self.calls: list[Call] = []
        self._lock = threading.Lock()
        self.responder = responder or default_responder

    def generate(self, *, system, user, schema, purpose):
        call = Call(system=system, user=user, schema=schema, purpose=purpose)
        with self._lock:
            self.calls.append(call)
        out = self.responder(call)
        return LLMResult(parsed=out, model="fake-model-2026", request_ids=[f"req_{purpose}"], input_tokens=10, output_tokens=5)

    def calls_for(self, app_id: str) -> list[Call]:
        return [c for c in self.calls if c.purpose.endswith(app_id)]


def default_responder(call: Call):
    if call.schema is RiskAssessment:
        return make_risk()
    return make_summary()


@pytest.fixture
def sample_apps() -> list[Application]:
    return load_applications(SAMPLE_CSV, expected_count=15)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


def raise_for(app_id: str, stage_schema: type, error: LLMError) -> Responder:
    def responder(call: Call):
        if call.purpose.endswith(app_id) and call.schema is stage_schema:
            raise error
        return default_responder(call)

    return responder
