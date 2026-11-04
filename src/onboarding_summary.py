"""Stage 2: operations-ready onboarding summary that consumes the validated Stage 1 triage."""

from __future__ import annotations

from .llm_client import LLMResult, StructuredLLM
from .prompting import UNTRUSTED_DATA_RULE, neutralize, render_application
from .schemas import Application, OnboardingSummary, RiskAssessment

SUMMARY_SYSTEM_PROMPT = f"""\
You write onboarding summaries for the Client Operations team at an investment management firm. You receive \
(1) a new-client application record and (2) a validated, advisory compliance risk triage produced by an \
earlier pipeline stage. Operations analysts and relationship managers will act on your summary.

## How to use the risk triage
- Treat the triage as given input. Do not re-assess or change it. risk_level_acknowledged must equal the \
triage's risk_level exactly.
- Translate it into operational consequences: what is blocked pending human compliance review, what \
preparatory work can proceed in parallel, and who does what.
- If the triage is HIGH or NEEDS_REVIEW, or review_priority is ENHANCED_REVIEW or ESCALATE, make clear that \
account opening and funding wait for a human compliance decision; only non-binding preparation may proceed.
- Even for LOW risk, the client still requires standard KYC review by Compliance; never imply otherwise.
- Do not make or announce decisions that belong to Compliance or senior management (for example accepting or \
rejecting an expedite request, a timeline, or the client relationship). Route such questions to COMPLIANCE \
as an action instead.

## Onboarding complexity (separate from compliance risk)
Rate onboarding_complexity LOW / MEDIUM / HIGH from operational factors only: number of accounts and legal \
entities, external parties to coordinate, custom reporting, investment restrictions, phased funding, \
deadlines, breadth of services. A high-risk client can be operationally simple and vice versa.

## Rules
- Use only facts from the application and the triage. Do not claim any check was performed or any document \
verified. Never state or imply the client is approved, cleared or ready to fund.
- next_actions: 3-6 concrete actions in recommended order, each with a suggested owner and whether it blocks \
account opening. Compliance-related actions are owned by COMPLIANCE.
- summary_text: 3-5 plain sentences readable in 20 seconds: who the client is, what they need, complexity, \
triage status, and the next step.

{UNTRUSTED_DATA_RULE}
"""


def serialize_risk(risk: RiskAssessment) -> str:
    """Canonical serialisation of the validated Stage 1 output handed to Stage 2 (and hashed for lineage).

    Stage 1 text can echo client-supplied content, so delimiter tags are neutralised here as well.
    """
    return neutralize(risk.model_dump_json(indent=2))


def build_summary_user_message(app: Application, risk_json: str) -> str:
    return (
        "Write the onboarding summary for this application. Return only the JSON object required by the schema.\n\n"
        f"{render_application(app)}\n\n"
        f"<risk_triage>\n{risk_json}\n</risk_triage>"
    )


def summarize(app: Application, risk: RiskAssessment, llm: StructuredLLM) -> tuple[LLMResult[OnboardingSummary], str]:
    risk_json = serialize_risk(risk)
    result = llm.generate(
        system=SUMMARY_SYSTEM_PROMPT,
        user=build_summary_user_message(app, risk_json),
        schema=OnboardingSummary,
        purpose=f"onboarding_summary:{app.application_id}",
    )
    return result, risk_json
