# Crestview AI Client Intake — monday.com Demo Script (10–12 minutes)

**Primary demo:** [Crestview Client Onboarding POC — monday.com board 5032266463](https://andrelimyoukwans-team.monday.com/boards/5032266463).

**What has been demonstrated:** `output/monday_sync_report.json` records **15/15 items created, no errors**, on board `5032266463` from AI run `048b9e150ceb`. That is a historical sync result. Confirm the board's *current* contents just before the interview.

**Scope:** All case data is fictional. Claude provides **advisory intake risk triage**, not sanctions, identity, PEP or KYC screening. Compliance approves clients; the AI never does.

## Preflight — before the panel arrives

1. Open the monday.com board. Confirm **15 application items**, including `APP-2026-0301`, `APP-2026-0303` and `APP-2026-0310`.
2. Check these actual board columns: **Application ID**, **AI Risk Triage (advisory)**, **Review Priority**, **Routing**, **Onboarding Complexity**, **Compliance Decision**, **Pipeline Status**, **Risk Rationale & Evidence**, **Gaps / Blockers**, **AI Onboarding Summary**, **Next Actions**, **AI Provenance**.
3. Rehearse opening the long-text fields for Apex. Adjust column widths or your board view so the panel can read the text. Show the board, not the terminal.
4. Check that Compliance Decision displays **Pending Human Review**. This field is initialized on item creation and excluded from subsequent pipeline updates; the POC does **not** implement authorization or complete an approval workflow.
5. Have a code/evaluation tab ready only for Q&A. No need to run `--setup-board` again—it creates a different board.

Optional local validation (credentials required for the second command):

```bash
git switch feature/customer-review-demo
python -m pytest -q
python -m src.monday_sync --check
```

If the live board is inaccessible, use the read-only offline fallback (recorded results, **not live model calls**):

```bash
python -m src.report --input output/enriched_applications.json
python -m src.report --input output/adversarial/enriched_applications.json
```

Open `output/crestview_review_dashboard.html`. For adversarial tests, open `output/adversarial/crestview_review_dashboard.html`. The reports are not a second operational integration.

---

## 0:00–1:15 — Show the real workflow

**Show:** monday.com board with 15 applications and the risk, complexity, routing, status and compliance columns.

**Say:** “Here's the result of using AI to accelerate intake without creating another inbox. The pipeline processed 15 synthetic applications, then synchronized findings to the team's monday.com board. Operations can identify the next actions, Compliance can see escalation candidates, and nobody has been cleared by AI.”

**Avoid:** Claiming the POC includes working Salesforce, ClientHub, SharePoint, Outlook or ComplianceOne connections; these belong to the proposed six-month rollout. Likewise, suggested owners are text in `Next Actions`, not proof of actual monday.com assignee automation.

## 1:15–3:30 — Compare three cases: risk is not complexity

Use board search for:

- **Greenfield State Pension Fund — `APP-2026-0301`:** **Low** advisory risk / **Standard** priority / **Medium** complexity / **Standard KYC Queue**. Normal human KYC still applies.
- **Apex Global Holdings Ltd — `APP-2026-0303`:** **High** / **Escalate** / **Medium** complexity / **Compliance Escalation**. Open **Risk Rationale & Evidence** and **Gaps / Blockers**. Point to the layered structure, apparent nominee directors, unsupported source-of-funds details and resistance to information requests *as claims from the supplied intake description*, not independent findings.
- **Heritage Family Office — `APP-2026-0310`:** **Low** advisory risk, **High** operational complexity. More accounts/entities and coordination do not by themselves imply financial-crime risk.

**Say:** “Separating compliance indicators from operational complexity matters because escalating every complicated relationship would recreate today's Compliance backlog.”

The labels above match the saved `output/monday_payloads.json`. If your live board differs, identify the current values instead.

## 3:30–5:40 — Show Stage 1 informing Stage 2

Stay on **Apex**.

**Stage 1 — AI triage:** Show **AI Risk Triage (advisory)**, **Review Priority**, **Risk Rationale & Evidence**, **Gaps / Blockers**, **Routing**.

**Stage 2 — Operations follow-through:** Show **AI Onboarding Summary**, **Next Actions**, **Onboarding Complexity**, alongside **Compliance Decision**.

**Say:** “The first model stage extracts risk observations and supporting quotes. The second receives that validated assessment and uses it to write a practical operations brief, with named suggested owners and tasks that block account opening. For Apex, non-binding file preparation can proceed, but funding and account activation await a human Compliance decision.”

**Technical clarification:** `src/pipeline.py` runs `assess_risk(app, llm)` before `summarize(app, risk, llm)`. Inside the second prompt, the serialized Stage 1 JSON appears between **`<risk_triage>` tags**. That's a prompt delimiter, not a file. The canonical stored results are the `risk_assessment` and `onboarding_summary` objects in `output/enriched_applications.json`. Optional separate JSON exports are generated by `python -m src.report`.

**Do not show SHA-256 comparisons.** They belong to test/audit lineage, not the customer workflow.

## 5:40–7:50 — Demonstrate guardrails and human ownership

**Show:** Source quotes in Apex's **Risk Rationale & Evidence**, its **Pending Human Review** decision, and the **Pipeline Status** / **Routing** columns.

**Say:** “We don't rely on the model to mark its own homework. There are checks before, at, and after each model call. If input is invalid, evidence is unverified or an output claims a client has been cleared, we expose that issue and route it to human review rather than silently treating the case as low risk.”

| Failure to prevent | Implemented check | Honest limitation |
|---|---|---|
| Malformed output | Provider JSON schema + local Pydantic validation, bounded repair | A valid structure can still contain incorrect claims |
| Invented quotations | Verbatim source-quote matching | Quote presence doesn't prove the interpretation |
| False claim of screening or approval | Deterministic prohibited-claim scanner | Lexical scanner can miss or overflag phrasing |
| Prompt injection | Untrusted input delimiting, neutralized forged tags, adversarial tests | No universal guarantee against every injection |
| Inconsistent risk / priority | Warnings and conservative deterministic routing | Risk taxonomy still needs Compliance sign-off |
| API failure misread as Low | Explicit NEEDS_REVIEW / MANUAL_TRIAGE states | Manual follow-up is required |
| Overwriting human decision | `Compliance Decision` set only on item creation | Role-based approval permissions aren't implemented |

**Framework question:** “This is a small two-stage pipeline, not an autonomous multi-agent system. We chose targeted business-rule checks, Anthropic structured output and Pydantic rather than introducing Guardrails AI or NeMo Guardrails without a specific proven gap. In production we'd evaluate frameworks against policy-owned tests and threat scenarios.”

**Optional red-team example:** Present the recorded offline adversarial case `APP-2026-0901` (injected instruction) or `APP-2026-0903` (blank invalid description). Do **not** sync adversarial cases into the client demo board.

## 7:50–9:10 — Why monday.com, not another AI dashboard?

**Show:** The board's **Routing**, **Gaps / Blockers**, **Next Actions** and **Compliance Decision** columns.

**Say:** “monday.com is the work surface. Our GraphQL adapter maps structured findings into board columns and upserts by Application ID, avoiding duplicates on reruns. Crucially, it does not overwrite a previously recorded human Compliance Decision. Production rollout adds approved system integrations, ownership automation, SLAs and monitoring.”

**Be precise:** The source repository documents live board item creation. It does not prove live enterprise data connectors, fully automated status transitions or access-controlled reviewer approvals.

## 9:10–10:45 — Technical validation (brief, or on request)

**Say:** “This is a maintainable Python system: two Claude calls per valid case, strongly typed results, evidence checks, explicit failure states and isolated monday.com GraphQL writes. The recorded full run reports **15/15 completed**, **61/61 source quotations matched** and **30/30 internal evaluation checks**. These are small synthetic development metrics, not production risk-prediction accuracy.”

Show code only if the panel wants it: `src/pipeline.py`, `src/guardrails.py`, `src/monday_client.py`, `output/evaluation_report_sample.md`. Run `pytest` before the session; the previously reported 86 tests predate this feature branch.

## 10:45–12:00 — Close and transition to the roadmap

**Say:** “The product outcome isn't an AI risk score—it is an evidence-linked recommendation that immediately becomes a visible next action, with human decisions preserved. The six-month pilot should measure whether we reduce manual touches and cycle time without weakening Compliance oversight. The 23-to-5-business-day objective remains a target, not a result of these 15 synthetic cases.”

---

## Technical Q&A cheat sheet

- **Actual monday.com write?** `output/monday_sync_report.json` records 15 successful creations on board `5032266463`. Cross-check visually with the live board.
- **Stage 1 and Stage 2 files?** Combined canonical `output/enriched_applications.json`; optional `output/risk_assessments.json` and `output/onboarding_summaries.json` exported by `src.report`.
- **What is `<risk_triage>`?** The Stage 2 prompt section enclosing Stage 1 JSON. Not a file, agent or folder.
- **What is the SHA-256 for?** Internal audit lineage of Stage 1's serialized input to Stage 2. Not customer-facing.
- **What does the monday.com adapter protect?** Idempotent Application-ID upsert; Compliance Decision is create-only. It does *not* enforce role permissions.
- **Can we run the model live?** Only if explicitly requested: `python -m src.main --ids APP-2026-0301 APP-2026-0303 APP-2026-0310`. This writes separate `*_subset` output. Don't replace board data during an unprepared live demo.
