# Evaluation report - suite `sample`

- Source: `output/enriched_applications.json`
- Run `bccd1c84e310` (live), model `claude-sonnet-5-5`, effort `medium`, prompts {'risk_assessment': 'risk-triage-v3', 'onboarding_summary': 'onboarding-summary-v2'}, started 2026-11-03T03:16:15+00:00
- Expectations are qualitative reviewer expectations, not regulatory ground truth.

## Global invariants

| Result | Invariant | Detail |
|---|---|---|
| PASS | All records processed successfully |  |
| FAIL | Every risk/mitigating factor quote found verbatim in source | 2 unverified: [('APP-2026-0311', 'Beneficial owner is also sole director.'), ('APP-2026-0311', 'Beneficial owner is also sole director.')] |
| FAIL | No prohibited claims (screening results, approvals, legal conclusions) | flags=[('APP-2026-0308', 'Prepare non-binding account setup materials and a draft conservative, capital-preservation investment profile for review once KYC is complete')] rescans=['APP-2026-0308'] |
| PASS | Stage 2 acknowledged the Stage 1 risk level |  |
| PASS | Stage 2 consumed the exact Stage 1 output (hash lineage) |  |
| PASS | No failed record presented as LOW |  |
| PASS | All records pending human review |  |

## Case expectations

| Result | Application | Expectation | Observed |
|---|---|---|---|
| PASS | APP-2026-0301 | Straightforward institutional: LOW risk | risk=LOW, priority=STANDARD, complexity=MEDIUM |
| PASS | APP-2026-0301 | No fabricated red flags (no HIGH/MEDIUM-severity factors) | risk=LOW, priority=STANDARD, complexity=MEDIUM |
| PASS | APP-2026-0303 | Opaque ownership + unsupported funds: HIGH risk | risk=HIGH, priority=ESCALATE, complexity=MEDIUM |
| PASS | APP-2026-0303 | Elevated review priority (ENHANCED_REVIEW or ESCALATE) | risk=HIGH, priority=ESCALATE, complexity=MEDIUM |
| PASS | APP-2026-0303 | Flags ownership transparency | risk=HIGH, priority=ESCALATE, complexity=MEDIUM |
| PASS | APP-2026-0303 | Flags source of funds | risk=HIGH, priority=ESCALATE, complexity=MEDIUM |
| PASS | APP-2026-0306 | Board resolution reported as pending, not complete | risk=MEDIUM, priority=ENHANCED_REVIEW, complexity=MEDIUM |
| PASS | APP-2026-0307 | PEP indicator flagged | risk=MEDIUM, priority=ENHANCED_REVIEW, complexity=MEDIUM |
| PASS | APP-2026-0307 | At least MEDIUM risk | risk=MEDIUM, priority=ENHANCED_REVIEW, complexity=MEDIUM |
| PASS | APP-2026-0307 | Missing fund formation documents reported as missing | risk=MEDIUM, priority=ENHANCED_REVIEW, complexity=MEDIUM |
| PASS | APP-2026-0309 | Sovereign fund complexity not treated as HIGH compliance risk | risk=MEDIUM, priority=ENHANCED_REVIEW, complexity=HIGH |
| PASS | APP-2026-0309 | Operational complexity rated HIGH | risk=MEDIUM, priority=ENHANCED_REVIEW, complexity=HIGH |
| PASS | APP-2026-0310 | Family-office complexity not treated as HIGH compliance risk | risk=LOW, priority=STANDARD, complexity=HIGH |
| PASS | APP-2026-0310 | Operational complexity rated HIGH | risk=LOW, priority=STANDARD, complexity=HIGH |
| PASS | APP-2026-0311 | Thin history + unsupported funds: at least MEDIUM risk | risk=HIGH, priority=ESCALATE, complexity=LOW |
| PASS | APP-2026-0311 | Enhanced review candidate | risk=HIGH, priority=ESCALATE, complexity=LOW |
| PASS | APP-2026-0311 | Flags source of funds | risk=HIGH, priority=ESCALATE, complexity=LOW |
| PASS | APP-2026-0313 | Trading restriction / insider status flagged | risk=MEDIUM, priority=STANDARD, complexity=MEDIUM |
| PASS | APP-2026-0313 | Not HIGH risk (restriction is not an allegation) | risk=MEDIUM, priority=STANDARD, complexity=MEDIUM |
| PASS | APP-2026-0313 | No insider-trading violation claim | risk=MEDIUM, priority=STANDARD, complexity=MEDIUM |
| PASS | APP-2026-0315 | Unverified introducer + no docs: HIGH risk | risk=HIGH, priority=ESCALATE, complexity=MEDIUM |
| PASS | APP-2026-0315 | Serious escalation candidate (ESCALATE) | risk=HIGH, priority=ESCALATE, complexity=MEDIUM |
| PASS | APP-2026-0315 | Flags third-party intermediary | risk=HIGH, priority=ESCALATE, complexity=MEDIUM |

**28/30 checks passed.**
