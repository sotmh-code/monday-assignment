"""Pydantic models for input records, model outputs (per stage), and enriched output records.

Two kinds of model live here:
  * LLM output contracts (RiskAssessment, OnboardingSummary). These are sent to the provider as
    a JSON schema (structured outputs) and validated again locally. Field descriptions are part
    of the prompt contract, so keep them precise.
  * Pipeline records (Application, EnrichedRecord, ...). These are built by our code, never by
    the model.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = [
    "application_id",
    "client_name",
    "client_type",
    "requested_services",
    "estimated_aum",
    "submission_date",
    "status",
    "description",
]


class Application(BaseModel):
    """One row from the intake CSV. Source strings are preserved verbatim."""

    model_config = ConfigDict(frozen=True)

    row_number: int
    application_id: str
    client_name: str
    client_type: str
    requested_services: str
    estimated_aum_raw: str
    estimated_aum: int | None
    submission_date_raw: str
    submission_date: date | None
    status: str
    description: str
    input_issues: list[str] = Field(default_factory=list)

    @property
    def is_processable(self) -> bool:
        return not self.input_issues


# ---------------------------------------------------------------------------
# Stage 1 - risk triage (LLM output contract)
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ReviewPriority(str, Enum):
    STANDARD = "STANDARD"
    ENHANCED_REVIEW = "ENHANCED_REVIEW"
    ESCALATE = "ESCALATE"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskCategory(str, Enum):
    OWNERSHIP_TRANSPARENCY = "OWNERSHIP_TRANSPARENCY"
    SOURCE_OF_FUNDS_OR_WEALTH = "SOURCE_OF_FUNDS_OR_WEALTH"
    PEP_EXPOSURE = "PEP_EXPOSURE"
    JURISDICTION_OR_OFFSHORE = "JURISDICTION_OR_OFFSHORE"
    KYC_DOCUMENTATION_GAP = "KYC_DOCUMENTATION_GAP"
    DUE_DILIGENCE_RESISTANCE = "DUE_DILIGENCE_RESISTANCE"
    THIRD_PARTY_INTERMEDIARY = "THIRD_PARTY_INTERMEDIARY"
    LIMITED_OPERATING_HISTORY = "LIMITED_OPERATING_HISTORY"
    TRADING_RESTRICTION_OR_INSIDER_STATUS = "TRADING_RESTRICTION_OR_INSIDER_STATUS"
    EMBEDDED_INSTRUCTION = "EMBEDDED_INSTRUCTION"
    OTHER = "OTHER"


class InfoStatus(str, Enum):
    REPORTED_MISSING_OR_PENDING = "REPORTED_MISSING_OR_PENDING"
    NOT_STATED_IN_APPLICATION = "NOT_STATED_IN_APPLICATION"


NOT_STATED_EVIDENCE = "NOT STATED IN APPLICATION"


class RiskFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor: str = Field(description="Short name of the compliance risk indicator, e.g. 'Nominee directors obscure control'.")
    category: RiskCategory
    severity: Severity
    source_evidence: str = Field(
        description=(
            "Exact, contiguous quote copied verbatim from the application record that supports this factor "
            f"(no paraphrase, no ellipses). Use the literal string '{NOT_STATED_EVIDENCE}' only when the factor "
            "is the absence of information."
        )
    )


class MitigatingFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor: str
    source_evidence: str = Field(description="Exact, contiguous quote copied verbatim from the application record.")


class MissingInformation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str = Field(description="Information or document a KYC analyst would need.")
    status: InfoStatus = Field(
        description=(
            "REPORTED_MISSING_OR_PENDING if the record says it is missing, pending, partial or not provided; "
            "NOT_STATED_IN_APPLICATION if the record simply does not mention it."
        )
    )


class RiskAssessment(BaseModel):
    """Advisory, evidence-based intake triage. Not a KYC/AML determination."""

    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel
    review_priority: ReviewPriority
    risk_factors: list[RiskFactor] = Field(description="Compliance risk indicators only. Empty list if none.")
    mitigating_factors: list[MitigatingFactor] = Field(description="Facts in the record that reduce concern.")
    missing_information: list[MissingInformation]
    operational_complexity_notes: list[str] = Field(
        description="Operational complexity observed that was deliberately NOT treated as compliance risk."
    )
    rationale: str = Field(
        description="2-4 sentences naming the observable facts that drove the level, written for an auditor."
    )
    compliance_review_required: bool = Field(
        description="Whether human compliance review is required. Every new client requires KYC review."
    )
    suggested_next_steps: list[str] = Field(
        description="Concrete actions for human reviewers. Never approve or clear the client."
    )


# ---------------------------------------------------------------------------
# Stage 2 - onboarding summary (LLM output contract)
# ---------------------------------------------------------------------------


class Complexity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Owner(str, Enum):
    RELATIONSHIP_MANAGER = "RELATIONSHIP_MANAGER"
    CLIENT_OPERATIONS = "CLIENT_OPERATIONS"
    COMPLIANCE = "COMPLIANCE"
    LEGAL = "LEGAL"
    PORTFOLIO_MANAGEMENT = "PORTFOLIO_MANAGEMENT"
    CLIENT_REPORTING = "CLIENT_REPORTING"


class NextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    suggested_owner: Owner
    blocks_account_opening: bool = Field(
        description="True if account opening/funding must wait for this action to be completed."
    )


class OnboardingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_overview: str = Field(description="1-2 sentences: who the client is.")
    service_needs: list[str] = Field(description="What the client is asking Crestview to do.")
    onboarding_complexity: Complexity = Field(
        description="Operational complexity (accounts, entities, parties, reporting, deadlines). Not compliance risk."
    )
    complexity_drivers: list[str]
    risk_level_acknowledged: RiskLevel = Field(
        description="Must exactly equal risk_level from the provided risk triage."
    )
    risk_context: str = Field(description="1-2 sentences translating the risk triage into operational consequences.")
    documentation_or_review_gaps: list[str]
    next_actions: list[NextAction] = Field(description="3-6 concrete actions in recommended order.")
    summary_text: str = Field(description="3-5 plain-language sentences an operations analyst can read in 20 seconds.")


# ---------------------------------------------------------------------------
# Output record (built by code)
# ---------------------------------------------------------------------------


class ProcessingStatus(str, Enum):
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED_RISK_ASSESSMENT = "FAILED_RISK_ASSESSMENT"
    FAILED_SUMMARY = "FAILED_SUMMARY"
    SKIPPED_INVALID_INPUT = "SKIPPED_INVALID_INPUT"
    NOT_PROCESSED = "NOT_PROCESSED"


class Routing(str, Enum):
    STANDARD_KYC_QUEUE = "STANDARD_KYC_QUEUE"
    ENHANCED_DUE_DILIGENCE = "ENHANCED_DUE_DILIGENCE"
    COMPLIANCE_ESCALATION = "COMPLIANCE_ESCALATION"
    MANUAL_TRIAGE = "MANUAL_TRIAGE"


ADVISORY_NOTICE = (
    "AI-generated preliminary intake triage based only on the application text. No sanctions, watchlist, PEP or "
    "identity screening has been performed by this system. Final KYC/AML disposition is made by Crestview Compliance."
)


class StageError(BaseModel):
    stage: Literal["input", "risk_assessment", "onboarding_summary", "batch"]
    kind: str
    message: str
    retryable: bool = False


class EvidenceCheck(BaseModel):
    kind: Literal["risk_factor", "mitigating_factor"]
    index: int
    factor: str
    source_evidence: str
    verified_in_source: bool


class PolicyFlag(BaseModel):
    stage: Literal["risk_assessment", "onboarding_summary"]
    field: str
    rule: str
    excerpt: str


class Guardrails(BaseModel):
    evidence_checks: list[EvidenceCheck] = Field(default_factory=list)
    unverified_evidence_count: int = 0
    policy_flags: list[PolicyFlag] = Field(default_factory=list)


class LLMCallAudit(BaseModel):
    stage: Literal["risk_assessment", "onboarding_summary"]
    model_requested: str
    model_responded: str | None = None
    request_ids: list[str] = Field(default_factory=list)
    attempts: int = 0
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    latency_ms: int | None = None


class SourceRecord(BaseModel):
    application_id: str
    client_name: str
    client_type: str
    requested_services: str
    estimated_aum: str
    submission_date: str
    status: str
    description: str


class EnrichedRecord(BaseModel):
    application_id: str
    source: SourceRecord
    processing_status: ProcessingStatus
    # Effective values downstream systems should use. Never LOW unless Stage 1 succeeded and said LOW.
    triage_risk_level: RiskLevel
    review_priority: ReviewPriority | None
    routing: Routing
    compliance_review_required: bool = True
    human_review_status: Literal["PENDING_HUMAN_REVIEW"] = "PENDING_HUMAN_REVIEW"
    advisory_notice: str = ADVISORY_NOTICE
    risk_assessment: RiskAssessment | None = None
    onboarding_summary: OnboardingSummary | None = None
    guardrails: Guardrails = Field(default_factory=Guardrails)
    warnings: list[str] = Field(default_factory=list)
    errors: list[StageError] = Field(default_factory=list)
    # Lineage: hash of the exact Stage 1 JSON handed to Stage 2.
    risk_assessment_sha256: str | None = None
    summary_consumed_risk_sha256: str | None = None
    llm_calls: list[LLMCallAudit] = Field(default_factory=list)
    processed_at: str
    prompt_versions: dict[str, str]
    schema_version: str


class RunMetadata(BaseModel):
    run_id: str
    mode: Literal["live", "replay"]
    started_at: str
    finished_at: str | None = None
    provider: str
    model_requested: str
    effort: str
    pipeline_version: str
    prompt_versions: dict[str, str]
    schema_version: str
    input_file: str
    input_sha256: str
    record_count: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    risk_level_counts: dict[str, int] = Field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    notes: list[str] = Field(default_factory=list)


class RunOutput(BaseModel):
    run: RunMetadata
    records: list[EnrichedRecord]
