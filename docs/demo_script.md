# Crestview AI Client Intake — Live Demo Script (10–12 minutes)

> **Audience:** Crestview COO, Client Operations, Compliance and Technology leaders, with the monday.com FDE interview panel. This is a **customer experience first** demonstration, followed by the architecture behind it.
>
> **Important:** All applications are fictional. Recorded results are real outputs of a prior model run, but replaying them is **not a live API call**. Risk ratings are advisory; no sanctions, PEP, KYC or identity screening has been performed. Human Compliance makes every final decision.

## Before the interview: preparation, not presentation

Run in your local repository:

\`\`\`bash
source .venv/bin/activate
python -m pytest -q
python -m src.report --input output/enriched_applications.json
\`\`\`

Open \`output/crestview_review_dashboard.html\` in a browser (double-click or \`open output/crestview_review_dashboard.html\` on macOS). Keep the PDF presentation ready to transition into the demo.

Open browser tabs for:
- **Client Intake Review** — the generated dashboard, your primary demo surface.
- Optional: your actual monday.com sandbox board, **only if a real sync has already been configured and verified**.
- Optional technical Q&A: \`src/pipeline.py\`, \`src/guardrails.py\`, \`src/risk_assessment.py\`, \`src/onboarding_summary.py\`, \`output/evaluation_report_sample.md\`.

**Do not** open the terminal, raw JSON, code, or SHA-256 fields as part of the initial customer walkthrough. The separate Stage 1 and Stage 2 files are available under \`output/risk_assessments.json\` and \`output/onboarding_summaries.json\` for reviewers who ask; the dashboard also links to them. The canonical original is \`output/enriched_applications.json\`.

Use \`python -m src.main --ids APP-2026-0301 APP-2026-0303 APP-2026-0310\` **only if the panel asks to see actual live API execution and the key/network are working**. This writes \`*_subset\` files, not the full results. Regenerate the report with \`--input output/enriched_applications_subset.json --output output/subset_review.html\` if you wish to show those new results. Say clearly when a displayed report is recorded rather than freshly generated.

## 0:00–1:15 | The problem and customer-facing experience

**Show:** Browser dashboard, top-level metrics and client list.

**Say:** “This is the operational experience we want Client Ops and Compliance to have, rather than a set of AI logs. Fifteen synthetic applications have already been processed. A reviewer can find a client, see what AI identified, understand what information is missing and track the handoff. None of these records has been cleared by AI.”

**Point out:** Completed results vs. cases needing review, pending human decisions, searchable and filterable client list. These counts reflect the recorded run, not live organizational KPIs.

## 1:15–3:45 | Compare three applicants: risk is not complexity

**Show:** Use the client list/search for:

1. **Greenfield State Pension Fund (APP-2026-0301):** Standard onboarding example. Say: “Transparent, familiar documentation still needs standard human KYC.”
2. **Apex Global Holdings Ltd (APP-2026-0303):** HIGH advisory risk. Say: “Opaque beneficial ownership and gaps in source-of-funds evidence warrant human escalation. The risk indicator shows the source sentence, so the analyst can investigate.”
3. **Heritage Family Office (APP-2026-0310):** LOW advisory risk but HIGH operational complexity. Say: “Multiple accounts and advisors may create operational work without automatically implying AML concerns. Separating those concepts prevents false escalation.”

**Do not say:** The model performed KYC, verified documents, or independently confirmed the client's claims. It only interprets the fictional intake descriptions.

## 3:45–5:45 | Stage 1 informs Stage 2

**Show:** Apex case in browser. Scroll from **Stage 1: Risk triage and source evidence** to **Stage 2: Risk-informed onboarding summary**.

**Say:** “Stage 1 produces a structured, evidence-backed advisory risk assessment. Stage 2 receives that assessment, together with the application, and creates an operations summary. It translates risk into specific actions, owners and blockers. Notice that account opening or funding stays blocked pending the appropriate human review.”

**Why this matters:** In \`src/pipeline.py\`, \`assess_risk\` runs before \`summarize(app, risk, llm)\`. The validated Stage 1 \`RiskAssessment\` object is serialized into the Stage 2 prompt under the **\`<risk_triage>\` delimiter**. That delimiter is a prompt section, **not a filename or separate agent**. The two individual JSON reports are **exports of the final persisted records**, not the actual transient prompt text.

**Do not demonstrate:** Comparing SHA-256 values on screen. That is an internal lineage check, covered by a unit test, useful only if the technical panel asks.

## 5:45–8:15 | Trust, guardrails and failure cases

**Show:** Apex case's **Guardrails and review boundaries** panel. Then discuss the adversarial dataset (see note).

**Say:** “The model isn't its own validator. We use strict structured output, verify source quotations exist, reject claims that screening was completed or a client approved, and route inconsistent or failed results to manual review. These checks address fabricated evidence, unauthorized compliance claims, prompt injection and silent failure. Importantly, a quoted sentence existing in the application does not prove the AI's interpretation is correct—that's the analyst's job.”

**Explain the guardrails as a sequence:**
- **Before the model:** input validation; application text is treated as untrusted data; forged prompt delimiters neutralized.
- **At the model boundary:** provider-enforced structured JSON schema; local Pydantic validation; bounded retries and explicit failures.
- **After Stage 1:** evidence quote matching, prohibited-claim scanning, consistency warnings, conservative routing.
- **After Stage 2:** acknowledged risk-level consistency and prohibited-claim scanning.
- **At the system boundary:** every application requires human review; the monday.com integration only initializes the Compliance Decision column on creation as **Pending Human Review** and does not overwrite reviewer decisions on updates.

**Adversarial evidence:** A pre-recorded run exists in \`output/adversarial/enriched_applications.json\`, including injected instructions and sparse/invalid inputs. To show it elegantly, generate a **separate dashboard** before the interview:
\`\`\`bash
python -m src.report --input output/adversarial/enriched_applications.json
\`\`\`
Then open \`output/adversarial/crestview_review_dashboard.html\` and select **Northgate Consulting LLC (APP-2026-0901)** for the injected-instruction case or **Blank Description Holdings (APP-2026-0903)** for a rejected invalid-input case. These results are pre-recorded; do not imply you just attacked the live model.

**On frameworks:** “I kept validation and policy checks explicit and testable in this small two-step workflow, rather than adopting an entire agent-orchestration stack. In production I'd evaluate Guardrails AI or NeMo Guardrails for controls they demonstrably improve, but no framework replaces Crestview-owned KYC policies, evidence checks or human authorization.” Do not imply a guardrail framework is already used.

## 8:15–9:45 | monday.com as the real operational home

**Show:** If available and previously verified, the live monday.com sandbox board. Otherwise continue to show the dashboard, and describe the **tested but not necessarily deployed** GraphQL adapter.

**Say:** “The report is our standalone review surface for the interview. In production, monday.com would be the system of work: each application becomes a tracked item with an owner, status, escalation queue and human Compliance Decision. Salesforce and ClientHub remain systems of record; screening stays in ComplianceOne. The existing GraphQL adapter supports an idempotent upsert keyed by application ID and deliberately leaves human compliance decisions alone on repeat runs.”

The repository includes \`output/monday_payloads.json\` from dry-run mapping. **Dry-run does not mean a monday.com board has been populated.** Never claim live sync without verifying it.

## 9:45–11:15 | Technical credibility and evaluation

**Show only if needed:** a pre-opened evaluation report or a short architecture diagram, not a running terminal.

**Say:** “This is a narrow, maintainable pipeline: Anthropic structured output, Pydantic contracts, deterministic checks and a separate monday adapter. It retries bounded transient failures, leaves invalid inputs visible, and never defaults an error to LOW risk. The sample runs and adversarial tests are documented; I can show test or code evidence if you'd like.”

The existing README reports 15/15 successful records in run \`048b9e150ceb\`, 61/61 matched evidence quotations and 30/30 evaluation checks. **Recheck test count with \`python -m pytest -q\` before quoting the current number.** Those are development metrics, not production accuracy or compliance outcomes.

## 11:15–12:00 | Transition

**Say:** “The value is not an AI-generated risk score on its own. It's an auditable, evidence-linked recommendation, followed by a useful next action, in a workflow where a person remains accountable. What we prove next in the pilot is whether that actually reduces manual touch time and onboarding cycle time without compromising risk controls.”

## Technical Q&A quick reference

| Question | Answer / source |
|---|---|
| Where are Stage 1 and 2 outputs? | \`output/risk_assessments.json\` and \`output/onboarding_summaries.json\` generated by \`python -m src.report\`; the original combined result remains \`output/enriched_applications.json\`. |
| What is \`<risk_triage>\`? | A delimiter in Stage 2's LLM prompt around the validated Stage 1 JSON, not a file or runtime framework. |
| What does the SHA-256 prove? | It records the serialized validated triage passed to Stage 2; the integrity/lineage test verifies it. Not a customer workflow. |
| Why not NeMo/Guardrails AI? | The POC has two sequential LLM stages, and its highest-value controls are firm-specific and deterministic. Framework adoption should follow a documented gap and evaluation. |
| Does the dashboard approve or edit? | No. It's read-only; human review is conceptual here. monday.com is the proposed operational review/approval surface. |
| Can I see new model output now? | If credentials/network permit, run \`python -m src.main --ids ...\` and regenerate a separate report from the subset JSON. Clearly label the run as live. |
| What are its limits? | Short fictional descriptions only; no document OCR, real screenings, live client workflows, production access policies or independently validated accuracy. |
