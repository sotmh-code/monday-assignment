"""Two-stage pipeline orchestration: validate -> Stage 1 risk triage -> guardrails -> Stage 2 summary.

Failure semantics (never a silent LOW):
  * invalid input row        -> SKIPPED_INVALID_INPUT, NEEDS_REVIEW, MANUAL_TRIAGE, no model call
  * Stage 1 fails            -> FAILED_RISK_ASSESSMENT, NEEDS_REVIEW, MANUAL_TRIAGE, Stage 2 not run
  * Stage 2 fails            -> FAILED_SUMMARY, Stage 1 result kept and routed normally
  * fatal provider error     -> remaining records NOT_PROCESSED (e.g. bad key) instead of 15 identical failures
  * one record failing never stops the others.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import guardrails
from .config import RISK_PROMPT_VERSION, SCHEMA_VERSION, SUMMARY_PROMPT_VERSION
from .io_utils import format_aum
from .llm_client import LLMError, LLMResult, StructuredLLM
from .onboarding_summary import serialize_risk, summarize
from .prompting import evidence_corpus
from .risk_assessment import assess_risk
from .schemas import (
    Application,
    EnrichedRecord,
    Guardrails,
    LLMCallAudit,
    ProcessingStatus,
    ReviewPriority,
    RiskAssessment,
    RiskCategory,
    RiskLevel,
    Routing,
    SourceRecord,
    StageError,
)

log = logging.getLogger(__name__)

PROMPT_VERSIONS = {"risk_assessment": RISK_PROMPT_VERSION, "onboarding_summary": SUMMARY_PROMPT_VERSION}

_ROUTE_ORDER = [
    Routing.STANDARD_KYC_QUEUE,
    Routing.ENHANCED_DUE_DILIGENCE,
    Routing.COMPLIANCE_ESCALATION,
    Routing.MANUAL_TRIAGE,
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def source_record(app: Application) -> SourceRecord:
    return SourceRecord(
        application_id=app.application_id,
        client_name=app.client_name,
        client_type=app.client_type,
        requested_services=app.requested_services,
        estimated_aum=app.estimated_aum_raw,
        submission_date=app.submission_date_raw,
        status=app.status,
        description=app.description,
    )


def route_for(risk: RiskAssessment, policy_flagged: bool) -> Routing:
    """Deterministic routing. Takes the more conservative of risk level and priority."""
    if policy_flagged or risk.risk_level == RiskLevel.NEEDS_REVIEW:
        return Routing.MANUAL_TRIAGE
    # Text trying to steer the system is an integrity concern for a human, whatever the level.
    if any(f.category == RiskCategory.EMBEDDED_INSTRUCTION for f in risk.risk_factors):
        return Routing.MANUAL_TRIAGE
    by_priority = {
        ReviewPriority.STANDARD: Routing.STANDARD_KYC_QUEUE,
        ReviewPriority.ENHANCED_REVIEW: Routing.ENHANCED_DUE_DILIGENCE,
        ReviewPriority.ESCALATE: Routing.COMPLIANCE_ESCALATION,
    }[risk.review_priority]
    by_level = {
        RiskLevel.LOW: Routing.STANDARD_KYC_QUEUE,
        RiskLevel.MEDIUM: Routing.STANDARD_KYC_QUEUE,
        RiskLevel.HIGH: Routing.ENHANCED_DUE_DILIGENCE,
    }[risk.risk_level]
    return max(by_priority, by_level, key=_ROUTE_ORDER.index)


def _audit(stage: str, llm: StructuredLLM, result: LLMResult | None = None, err: LLMError | None = None) -> LLMCallAudit:
    if result is not None:
        return LLMCallAudit(
            stage=stage,
            model_requested=llm.model,
            model_responded=result.model,
            request_ids=result.request_ids,
            attempts=result.attempts,
            stop_reason=result.stop_reason,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cache_read_input_tokens=result.cache_read_input_tokens,
            latency_ms=result.latency_ms,
        )
    return LLMCallAudit(
        stage=stage,
        model_requested=llm.model,
        request_ids=err.request_ids if err else [],
        attempts=err.attempts if err else 0,
    )


def _base_record(app: Application, **kwargs) -> EnrichedRecord:
    defaults = dict(
        application_id=app.application_id,
        source=source_record(app),
        triage_risk_level=RiskLevel.NEEDS_REVIEW,
        review_priority=None,
        routing=Routing.MANUAL_TRIAGE,
        processed_at=_now(),
        prompt_versions=PROMPT_VERSIONS,
        schema_version=SCHEMA_VERSION,
    )
    defaults.update(kwargs)
    return EnrichedRecord(**defaults)


def not_processed_record(app: Application, reason: str) -> EnrichedRecord:
    return _base_record(
        app,
        processing_status=ProcessingStatus.NOT_PROCESSED,
        errors=[StageError(stage="batch", kind="not_processed", message=reason)],
        warnings=["Not processed by AI; route to manual triage"],
    )


def process_application(
    app: Application,
    llm: StructuredLLM,
    abort: threading.Event | None = None,
) -> EnrichedRecord:
    abort = abort or threading.Event()

    if not app.is_processable:
        return _base_record(
            app,
            processing_status=ProcessingStatus.SKIPPED_INVALID_INPUT,
            errors=[StageError(stage="input", kind="invalid_input", message="; ".join(app.input_issues))],
            warnings=["Input failed validation; not sent to the AI model"],
        )
    if abort.is_set():
        return not_processed_record(app, "Batch aborted after a fatal provider error")

    # ---- Stage 1 ---------------------------------------------------------
    try:
        risk_result = assess_risk(app, llm)
    except LLMError as err:
        if err.fatal_for_batch:
            abort.set()
        return _base_record(
            app,
            processing_status=ProcessingStatus.FAILED_RISK_ASSESSMENT,
            errors=[StageError(stage="risk_assessment", kind=err.kind, message=err.message, retryable=err.retryable)],
            warnings=["Risk triage unavailable; route to manual triage (not treated as low risk)"],
            llm_calls=[_audit("risk_assessment", llm, err=err)],
        )

    risk = risk_result.parsed
    calls = [_audit("risk_assessment", llm, result=risk_result)]
    warnings = guardrails.risk_consistency_warnings(risk)
    evidence = guardrails.check_evidence(risk, evidence_corpus(app))
    unverified = [c for c in evidence if not c.verified_in_source]
    if unverified:
        warnings.append(f"{len(unverified)} evidence quote(s) not found verbatim in the application; review before relying on them")
    flags = guardrails.scan_risk(risk)
    if flags:
        warnings.append(f"Risk triage contains {len(flags)} prohibited claim(s); routed to manual triage")

    routing = route_for(risk, policy_flagged=bool(flags))
    risk_sha = None
    summary = None
    consumed_sha = None
    errors: list[StageError] = []

    # ---- Stage 2 (consumes validated Stage 1 output) ----------------------
    if abort.is_set():
        errors.append(StageError(stage="batch", kind="not_processed", message="Summary skipped: batch aborted"))
        status = ProcessingStatus.FAILED_SUMMARY
    else:
        try:
            summary_result, risk_json = summarize(app, risk, llm)
            summary = summary_result.parsed
            consumed_sha = sha256_text(risk_json)
            risk_sha = consumed_sha
            calls.append(_audit("onboarding_summary", llm, result=summary_result))
            if summary.risk_level_acknowledged != risk.risk_level:
                warnings.append(
                    f"Summary acknowledged risk {summary.risk_level_acknowledged.value} but triage was "
                    f"{risk.risk_level.value}; triage value is authoritative"
                )
            summary_flags = guardrails.scan_summary(summary)
            if summary_flags:
                flags += summary_flags
                routing = Routing.MANUAL_TRIAGE
                warnings.append(f"Summary contains {len(summary_flags)} prohibited claim(s); routed to manual triage")
            status = ProcessingStatus.COMPLETED_WITH_WARNINGS if warnings else ProcessingStatus.COMPLETED
        except LLMError as err:
            if err.fatal_for_batch:
                abort.set()
            calls.append(_audit("onboarding_summary", llm, err=err))
            errors.append(StageError(stage="onboarding_summary", kind=err.kind, message=err.message, retryable=err.retryable))
            status = ProcessingStatus.FAILED_SUMMARY

    if risk_sha is None:
        risk_sha = sha256_text(serialize_risk(risk))

    return _base_record(
        app,
        processing_status=status,
        triage_risk_level=risk.risk_level,
        review_priority=risk.review_priority,
        routing=routing,
        risk_assessment=risk,
        onboarding_summary=summary,
        guardrails=Guardrails(evidence_checks=evidence, unverified_evidence_count=len(unverified), policy_flags=flags),
        warnings=warnings,
        errors=errors,
        risk_assessment_sha256=risk_sha,
        summary_consumed_risk_sha256=consumed_sha,
        llm_calls=calls,
    )


def run_batch(
    applications: list[Application],
    llm: StructuredLLM,
    *,
    max_concurrency: int = 3,
    reuse: dict[str, EnrichedRecord] | None = None,
    on_record: Callable[[int, int, EnrichedRecord, bool], None] | None = None,
) -> list[EnrichedRecord]:
    """Process applications concurrently; return records in input order.

    `reuse` maps application_id -> previously successful record (skip-on-success reruns).
    `on_record(done, total, record, reused)` is called as each record completes (for progress output).
    """
    reuse = reuse or {}
    abort = threading.Event()
    results: dict[str, EnrichedRecord] = {}
    lock = threading.Lock()
    total = len(applications)

    def _emit(rec: EnrichedRecord, reused: bool) -> None:
        with lock:
            results[rec.application_id] = rec
            if on_record:
                on_record(len(results), total, rec, reused)

    def _work(app: Application) -> None:
        try:
            rec = process_application(app, llm, abort)
        except Exception as exc:  # defensive: a bug must not lose the record
            log.exception("Unexpected error processing %s", app.application_id)
            rec = _base_record(
                app,
                processing_status=ProcessingStatus.FAILED_RISK_ASSESSMENT,
                errors=[StageError(stage="batch", kind="unexpected", message=f"{type(exc).__name__}: {exc}")],
                warnings=["Unexpected pipeline error; route to manual triage"],
            )
        _emit(rec, False)

    todo = []
    for app in applications:
        if app.application_id in reuse:
            _emit(reuse[app.application_id], True)
        else:
            todo.append(app)

    with ThreadPoolExecutor(max_workers=max(1, max_concurrency)) as pool:
        list(pool.map(_work, todo))

    return [results[a.application_id] for a in applications]


def describe_application(app: Application) -> str:
    return f"{app.application_id} {app.client_name} ({app.client_type}, {format_aum(app.estimated_aum)})"
