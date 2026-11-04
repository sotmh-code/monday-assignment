"""Deterministic post-model checks. The model is never the last line of defence.

  * Evidence grounding: each quoted source_evidence must appear in the text the model was shown.
  * Prohibited claims: model-written prose must not claim screening happened / passed, or that the
    client is approved/cleared, or make legal conclusions. Quoted evidence is excluded because it is
    copied from the source (e.g. "Investment committee approval confirmed").
  * Consistency: e.g. LOW risk with a HIGH-severity factor, Stage 2 changing the Stage 1 level.

Checks never silently fix model output; they add warnings / flags and can downgrade routing.
"""

from __future__ import annotations

import re
import unicodedata

from .schemas import (
    NOT_STATED_EVIDENCE,
    EvidenceCheck,
    OnboardingSummary,
    PolicyFlag,
    RiskAssessment,
    RiskLevel,
    Severity,
)

_QUOTE_MAP = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        " ": " ",
    }
)


def normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_MAP).lower()
    text = re.sub(r"\s+", " ", text)
    # Spacing around dashes varies ("documentation — the" vs "documentation-the").
    text = re.sub(r"\s*-\s*", "-", text)
    return text.strip()


def evidence_in_source(quote: str, source_text: str) -> bool:
    if quote.strip().upper() == NOT_STATED_EVIDENCE:
        return True
    q = normalize_for_match(quote).strip(" \"'.,;:")
    if len(q) < 4:
        return False
    return q in normalize_for_match(source_text)


def check_evidence(risk: RiskAssessment, source_text: str) -> list[EvidenceCheck]:
    checks = [
        EvidenceCheck(
            kind="risk_factor",
            index=i,
            factor=f.factor,
            source_evidence=f.source_evidence,
            verified_in_source=evidence_in_source(f.source_evidence, source_text),
        )
        for i, f in enumerate(risk.risk_factors)
    ]
    checks += [
        EvidenceCheck(
            kind="mitigating_factor",
            index=i,
            factor=f.factor,
            source_evidence=f.source_evidence,
            verified_in_source=evidence_in_source(f.source_evidence, source_text),
        )
        for i, f in enumerate(risk.mitigating_factors)
    ]
    return checks


# (rule name, pattern). Patterns target affirmative claims; negations such as "no screening has been
# performed" are excluded by _NEGATION below.
_PROHIBITED: list[tuple[str, re.Pattern[str]]] = [
    (
        "claims_screening_result",
        re.compile(
            r"\b(sanctions?|watch\s?lists?|pep|aml|kyc|adverse[- ]media)\b[^.]{0,40}?"
            r"\b(passed|cleared|came back clean|returned no|no (hits?|matches?)|negative result|is clear)\b",
            re.I,
        ),
    ),
    (
        "claims_screening_result",
        re.compile(r"\b(passed|cleared)\b[^.]{0,30}?\b(sanctions?|watch\s?lists?|screening|kyc|aml)\b", re.I),
    ),
    (
        "claims_screening_performed",
        re.compile(
            r"\b(sanctions?|watch\s?list|pep|screening)\b[^.]{0,30}?\b(was|were|has been|have been)\s+"
            r"(completed|performed|run|conducted|done)\b",
            re.I,
        ),
    ),
    ("claims_kyc_complete", re.compile(r"\b(kyc|aml|due diligence)\b[^.]{0,20}?\b(is |are )?(complete|completed|satisfied)\b", re.I)),
    (
        "claims_approval",
        re.compile(
            r"\b(client|account|application|onboarding)\b[^.]{0,30}?\b(is|has been|was)\s+"
            r"(approved|cleared|compliant)\b",
            re.I,
        ),
    ),
    ("claims_approval", re.compile(r"\b(approved|cleared) (for|to) (onboard|onboarding|fund|funding|account opening)\b", re.I)),
    ("claims_verified_identity", re.compile(r"\b(beneficial owners?|identity|identities)\b[^.]{0,20}?\b(has been|have been|is|are|were) verified\b", re.I)),
    (
        "legal_conclusion",
        re.compile(
            r"\b(is|are|was|engaged in|committed|guilty of)\s+(money laundering|insider trading|fraud|sanctions evasion)\b",
            re.I,
        ),
    ),
]

# Negations and conditionals ("once KYC is complete", "after the client is approved") are not claims.
_NEGATION = re.compile(
    r"\b(not|no|never|without|cannot|can't|unable|yet to|until|pending|before|prior to|once|after|when|upon|if|unless|subject to)\b",
    re.I,
)


# Reported speech describes what the *application* says, not a claim by the model
# (e.g. "embedded text asserts screening was completed" when reporting a prompt injection).
_REPORTED = re.compile(
    r"\b(claim(s|ed|ing)?|assert(s|ed|ing)?|alleg(e|es|ed|ing)|purport(s|ed|ing)?|posing as|embedded|"
    r"disregard(s|ed|ing)?|ignor(e|es|ed|ing))\b",
    re.I,
)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+|\n+", text) if s.strip()]


def scan_text(stage: str, field: str, text: str) -> list[PolicyFlag]:
    flags: list[PolicyFlag] = []
    for sentence in _sentences(text):
        for rule, pattern in _PROHIBITED:
            m = pattern.search(sentence)
            if not m:
                continue
            # Look for a negation before the claimed result (not inside it: "returned no matches"
            # is itself a claim). m.lastindex is the final group of each pattern.
            window = sentence[max(0, m.start() - 40) : m.start(m.lastindex or 0)]
            # Reported speech anywhere in the sentence ("...disregard the embedded sanctions-passed claims").
            if _NEGATION.search(window) or _REPORTED.search(sentence):
                continue
            flags.append(PolicyFlag(stage=stage, field=field, rule=rule, excerpt=sentence[:240]))
            break
    return flags


def risk_prose_fields(risk: RiskAssessment) -> dict[str, str]:
    fields = {"rationale": risk.rationale}
    for i, step in enumerate(risk.suggested_next_steps):
        fields[f"suggested_next_steps[{i}]"] = step
    for i, f in enumerate(risk.risk_factors):
        fields[f"risk_factors[{i}].factor"] = f.factor
    for i, f in enumerate(risk.mitigating_factors):
        fields[f"mitigating_factors[{i}].factor"] = f.factor
    for i, note in enumerate(risk.operational_complexity_notes):
        fields[f"operational_complexity_notes[{i}]"] = note
    return fields


def summary_prose_fields(summary: OnboardingSummary) -> dict[str, str]:
    fields = {
        "client_overview": summary.client_overview,
        "risk_context": summary.risk_context,
        "summary_text": summary.summary_text,
    }
    for i, a in enumerate(summary.next_actions):
        fields[f"next_actions[{i}].action"] = a.action
    for i, g in enumerate(summary.documentation_or_review_gaps):
        fields[f"documentation_or_review_gaps[{i}]"] = g
    return fields


def scan_risk(risk: RiskAssessment) -> list[PolicyFlag]:
    return [flag for field, text in risk_prose_fields(risk).items() for flag in scan_text("risk_assessment", field, text)]


def scan_summary(summary: OnboardingSummary) -> list[PolicyFlag]:
    return [
        flag for field, text in summary_prose_fields(summary).items() for flag in scan_text("onboarding_summary", field, text)
    ]


def risk_consistency_warnings(risk: RiskAssessment) -> list[str]:
    warnings: list[str] = []
    if not risk.compliance_review_required:
        warnings.append("Model set compliance_review_required=false; overridden by policy (all new clients need KYC review)")
    high_factors = [f for f in risk.risk_factors if f.severity == Severity.HIGH]
    if risk.risk_level == RiskLevel.LOW and high_factors:
        warnings.append(f"Inconsistent triage: LOW risk level with {len(high_factors)} HIGH-severity factor(s)")
    if risk.risk_level == RiskLevel.LOW and risk.review_priority.value != "STANDARD":
        warnings.append(f"Inconsistent triage: LOW risk level with review_priority={risk.review_priority.value}")
    if risk.risk_level == RiskLevel.HIGH and risk.review_priority.value == "STANDARD":
        warnings.append("Inconsistent triage: HIGH risk level with STANDARD review priority")
    return warnings
