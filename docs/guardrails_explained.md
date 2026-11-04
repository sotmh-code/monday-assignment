# Guardrails and review boundaries

The Crestview POC uses Anthropic structured outputs and Pydantic schemas for structural validation, plus explicit domain-specific policies in `src/guardrails.py`. It is an advisory intake-triage workflow, not an autonomous compliance agent.

This layered approach exists because generic guardrail packages do not decide Crestview-specific policy: whether screening claims are prohibited, which evidence must be quoted, whether KYC approval is human-only, and how suspicious input should be routed. A framework such as Guardrails AI or NeMo Guardrails could be added after requirements justify it, but would not replace policy checks and tests.

Current checks include source quote verification, prohibited screening/approval claims, risk/priority consistency, prompt-delimiter neutralization, schema validation, deterministic routing, and manual-review fallback on failures. A quote match verifies text provenance, **not the correctness of the model's interpretation**. Production requires a Compliance-owned policy taxonomy, independently labeled evals, access controls, document provenance, and a reviewer override audit.

See `src/report.py` (once added) and `docs/demo_script.md` for the intended customer-facing review demonstration.
