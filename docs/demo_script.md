# Crestview AI Client Intake — POC Demo Script (11:30 target)

**Objective:** Show the business result in monday.com, trace Apex's two model stages, explain the code, demonstrate actual prompt iteration and a failure test, then address production limitations.

**Board:** https://andrelimyoukwans-team.monday.com/boards/5032266463

**Scope:** The 15 applications are fictional. The board shows results from a previously recorded run, not fresh inference. The saved sync report recorded 15 successful creations on board 5032266463, from run 048b9e150ceb; confirm the board's current contents before the interview. This POC uses structured CSV data, not PDFs; it performs advisory triage, not screening, KYC disposition, client approval or account opening.

## Run of show — 11:30, with 30 seconds of contingency in a 12-minute slot

| Time | Screen | Point |
|---|---|---|
| **0:00–1:00** | monday.com overview | A usable workflow, not just AI output |
| **1:00–2:40** | Greenfield, Apex, Heritage | Risk and complexity are separate |
| **2:40–3:35** | **Apex board: Stage 1 → Stage 2** | **Preserves original stage-output walkthrough** |
| **3:35–6:05** | **VS Code: pipeline, prompts, evidence checks** | **Mandatory code and architecture walkthrough** |
| **6:05–7:20** | Development log and prompt | **Before/after prompt iteration** |
| **7:20–8:20** | Recorded injected application | **Failure mode and guardrail defect** |
| **8:20–9:10** | **monday_client.py** | **Actual GraphQL mapping/upsert** |
| **9:10–10:25** | Board or architecture reference | **Production hardening and limits** |
| **10:25–11:30** | Apex board | **Business close and human decision** |

No dedicated seven-guardrail recitation or second “why monday.com?” lecture; those are addressed where they naturally matter. Detailed control coverage remains in Q&A.

## Preflight — prepare views before the panel arrives

1. **Board:** Confirm 15 items, including Greenfield APP-2026-0301, Apex APP-2026-0303 and Heritage APP-2026-0310. Make Apex's Risk Rationale & Evidence, Gaps / Blockers, AI Onboarding Summary, Next Actions, Routing and Compliance Decision fields easy to open.
2. **VS Code tabs in order:** src/pipeline.py at process_application() and route_for(); src/risk_assessment.py at RISK_SYSTEM_PROMPT; src/onboarding_summary.py at SUMMARY_SYSTEM_PROMPT and summarize(); src/guardrails.py at evidence_in_source() and check_evidence(); src/monday_client.py at column_values() and upsert().
3. **Evidence tabs:** ai_development_log.md §3.5; output/evaluation_report_sample.md; recorded adversarial case APP-2026-0901. Don't sync adversarial cases to the board.
4. **Run tests in advance**, not on stage. Check monday.com board schema only with working credentials. Read-only demo_trace replays existing JSON and makes no network requests. It is not a live Claude run.

~~~bash
git switch feature/customer-review-demo
git pull
python -m pytest -q
python -m src.monday_sync --check
python -m src.demo_trace --application-id APP-2026-0303
python -m src.demo_trace --input output/adversarial/enriched_applications.json --application-id APP-2026-0901
~~~

If the live board is inaccessible: run python -m src.report --input output/enriched_applications.json and open output/crestview_review_dashboard.html. The fallback is read-only and offline.

---

## 0:00–1:00 — Lead with the result

**Show:** board with advisory risk, routing, complexity and Compliance Decision.

**Say:**

> "This is the operational result. Fifteen fictional onboarding applications have been processed by the AI pipeline and synchronized into monday.com.
>
> "Operations can identify outstanding work; Compliance can see which cases need attention. Crucially, these are recommendations, not screening results or client approvals.
>
> "I'll show three cases, trace Apex through both model stages, then show you the code, how we improved it, and what's still missing for production."

## 1:00–2:40 — Three cases, one important distinction

**Show Greenfield (20 seconds):** APP-2026-0301. LOW advisory risk, STANDARD priority, MEDIUM operational complexity, STANDARD_KYC_QUEUE. Human KYC is still required.

**Show Apex (60 seconds):** APP-2026-0303. HIGH advisory risk, ESCALATE priority, MEDIUM complexity, COMPLIANCE_ESCALATION. Open Risk Rationale & Evidence: the description raises layered ownership, apparent nominee directors, source-of-funds gaps and reluctance to provide details. These are statements within the supplied application, not independently verified facts.

**Show Heritage (20 seconds):** APP-2026-0310. LOW advisory risk, HIGH operational complexity.

**Say:**

> "Greenfield looks straightforward, but still needs standard Compliance review.
>
> "Apex has ownership and funding questions that justify escalation to a human reviewer.
>
> "Heritage is the contrast: coordinating multiple entities is operationally complex, but that alone doesn't make the client higher compliance risk. Otherwise, we would escalate every complicated case and recreate the backlog."

## 2:40–3:35 — Stage 1 → Stage 2, shown in monday.com

**Stay on Apex. This restores the original dedicated stage-output walkthrough.**

**Stage 1 fields:** AI Risk Triage (advisory), Review Priority, Risk Rationale & Evidence, Gaps / Blockers, Routing.

**Stage 2 fields:** AI Onboarding Summary, Onboarding Complexity, Next Actions. End on Compliance Decision = Pending Human Review.

**Say:**

> "Stage 1 produces the advisory risk assessment: the risk level, the evidence supporting it, outstanding questions and review priority.
>
> "Stage 2 consumes that assessment and turns it into the Operations brief: complexity, suggested owners, next steps and actions that block account opening.
>
> "For Apex, non-binding preparation can continue, but funding and account activation wait for human Compliance approval. The output doesn't stop at an AI report; it becomes visible work."

**Transition:** "Now let me show how those two results are generated."

## 3:35–6:05 — Mandatory code and architecture walkthrough

**Stay in VS Code for this entire block. Only visit the functions listed below; don't browse the entire repository.**

### 3:35–4:35 — src/pipeline.py: how data moves

**Point to:** process_application() → input check → assess_risk(app, llm) → evidence and routing checks → summarize(app, risk, llm) → EnrichedRecord.

**Say:**

> "The input is eight structured CSV fields, including a free-text description. This POC doesn't extract data from PDFs.
>
> "This Python function orchestrates two Claude calls. The first returns a structured RiskAssessment. Python checks it, computes routing and passes that risk object—along with the original application—into the second model call. The second returns a structured OnboardingSummary.
>
> "Both outputs are stored together, and a separate command synchronizes them into monday.com. These are independent components, not an autonomous agent choosing tools or next steps. If Stage 1 fails, it routes to manual triage; if Stage 2 fails, we preserve the risk result and record a summary failure."

### 4:35–5:25 — Two independent prompts and JSON contracts

**Point to:** RISK_SYSTEM_PROMPT and SUMMARY_SYSTEM_PROMPT; show summarize().

**Say:**

> "The risk prompt asks for observable indicators, exact source quotes, missing information and review priority. It prohibits claiming that real screening occurred.
>
> "The operations prompt has a different job: consume the Stage 1 JSON, acknowledge its risk level, then produce complexity, suggested owners, blockers and next actions. It cannot change the risk assessment or approve the client.
>
> "Each model stage has its own system prompt and Pydantic schema, so we can test or change one without rewriting the other."

**If asked:** The Stage 1 JSON is serialized into a risk_triage-delimited section inside Stage 2's prompt. That isn't a third call or agent.

### 5:25–6:05 — The check outside the model

**Point to:** src/guardrails.py → evidence_in_source() and check_evidence().

**Say:**

> "We don't rely on the model to validate its own evidence. The code checks that each quoted source passage appears in the application text. The model response is also schema-validated.
>
> "But quote matching proves that text appeared—not that the model interpreted it correctly. In today's POC, some unverified quotes produce warnings rather than forcing manual review. That's a gap we'd close before production."

## 6:05–7:20 — Prompt engineering: real before and after

**Show:** ai_development_log.md §3.5 and, briefly, the final RISK_SYSTEM_PROMPT.

**Say:**

> "Our first full evaluated run passed 28 of 30 checks. One weakness was risk inflation: the model treated routine details that hadn't been mentioned as evidence of higher risk.
>
> "We changed the prompt to require a positive, stated risk indicator. Routine missing details belong under missing information, not risk factors. Another case contained a supposedly verbatim quote that dropped the word 'the'; our evidence check caught it. We tightened the quotation instruction rather than relaxing the check.
>
> "We also corrected the second prompt when it tried to reject an expedite request itself, instead of referring that decision to Compliance.
>
> "The next full recorded run passed 30 of 30 internal checks, and 61 of 61 quotations matched. These are synthetic development tests, not production compliance accuracy."

## 7:20–8:20 — One prompt-injection failure test

**Show:** saved output for APP-2026-0901; use the read-only trace command prepared in advance. Optionally show route_for() in src/pipeline.py.

**Say:**

> "We also tested malicious source text. This fictional application contains a fake system override instructing Claude to mark the case LOW and falsely claim sanctions screening had passed.
>
> "The model didn't follow it. It identified the embedded instruction, and deterministic routing sent the case to MANUAL_TRIAGE.
>
> "But our first guardrail had its own bug: it treated the model's report of that fake claim as if the model were asserting the claim. We corrected the false positive and added adversarial regression tests. The lesson is that guardrails need testing just as much as the model."

**If asked:** The final synthetic adversarial suite passed 14/14 checks. This does not prove universal prompt-injection resistance.

## 8:20–9:10 — Actual monday.com GraphQL integration

**Show:** src/monday_client.py → column_values() and MondayClient.upsert().

**Say:**

> "The API adapter converts the enriched JSON to monday.com columns. It looks up Application ID before deciding whether to create or update an item, so a normal rerun updates an existing case.
>
> "One deliberate safeguard: Compliance Decision is initialized as Pending Human Review only when the item is created. Subsequent AI updates don't touch it, preserving a decision entered by a person."

**Be precise:** The POC does not implement role-based approval permissions. Lookup-then-create is not a transactional guarantee against duplicates from concurrent writes. No production Salesforce, ClientHub, SharePoint, Outlook or ComplianceOne integration has been delivered.

## 9:10–10:25 — Production hardening: what we have not built

**Show:** board or proposed architecture slide, not more source files.

**Say:**

> "I wouldn't deploy this CSV prototype directly into a regulated workflow.
>
> "First, it needs document ingestion: I'd benchmark Azure Document Intelligence and LlamaParse against Crestview's actual onboarding documents, and extract typed fields with source references before running risk triage. A Microsoft 365/Copilot agreement doesn't automatically include Azure AI services.
>
> "Marcus would need to approve the data flows—what information reaches the parser and LLM, where it's processed, retention, permissions and contractual controls.
>
> "Priya would own risk rules and acceptance criteria, tested on labelled cases in shadow mode. We'd also make material evidence failures block automated progression, add monitored enterprise integrations and implement real reviewer permissions. That's the gap between this POC and a production system."

## 10:25–11:30 — Return to Apex and close

**Show:** Apex's Next Actions, Routing and Pending Human Review.

**Say:**

> "Back to Apex: we started with an application description, identified evidence-linked concerns, turned them into clear actions and surfaced them to the people responsible.
>
> "What I've proven is the two-stage pipeline, structured outputs, real sandbox synchronization and explicit failure testing on fictional cases. I haven't proven the five-day onboarding target or production compliance accuracy.
>
> "The six-month implementation would test whether this reduces total manual effort and end-to-end onboarding time, while preserving human accountability."

**Stop.** Leave deeper technical questions for the panel Q&A.

---

## Technical Q&A — concise defenses, not extra speaking material

**Walk through the code and architecture.**  
> "One Python orchestrator coordinates two independently prompted Claude calls. Stage 1 transforms the eight CSV fields into RiskAssessment JSON; deterministic checks run; Stage 2 receives that object plus the original application and returns OnboardingSummary JSON. The separate monday.com adapter maps stored results into board columns."

**How did you use AI to build it?**  
> "I used Claude Code against a written plan and acceptance checklist. It accelerated implementation and test generation, but case-by-case live evaluation revealed prompt-calibration and regex-guardrail failures requiring correction. I also checked the Anthropic SDK behavior to distinguish refusals from malformed responses."

**Why separate calls rather than agents?**  
> "The prompts and schemas are independent already, with no requirement for a single system prompt. The processing order is fixed, so deterministic orchestration is easier to test and maintain than dynamic tool use. Agents would be more justified for open-ended evidence retrieval."

**How did the prompts change?**  
> "We stopped treating routine unstated data as risk evidence, required exact quotations and stopped the summary model from making management decisions. The synthetic evaluation improved from 28/30 to 30/30 checks after these general rules were introduced."

**What fails today?**  
> "Structured JSON can still contain incorrect judgments. Exact source matching doesn't prove semantic support, and some unverified evidence currently results only in warnings. The POC also has no real screening or document parser, and the board has no production reviewer authorization."

**What happens when a call fails?**  
> "Invalid applications aren't sent to Claude. Stage 1 failures yield NEEDS_REVIEW and MANUAL_TRIAGE; Stage 2 failures preserve the Stage 1 result and mark the missing summary. The provider layer separately classifies refusals, malformed outputs and retryable API errors."

**Is the monday.com integration idempotent?**  
> "It uses Application ID lookup before create-or-update, so repeat sequential runs normally update the same item. It doesn't fully prevent concurrent duplicate creates and doesn't enforce approval permissions."

**What is the next technical milestone?**  
> "Approved document extraction, Compliance-owned rules, labelled evaluation cases, fail-closed evidence checks, secure enterprise connectors, monitoring and a controlled shadow evaluation before live rollout."

## Demo accuracy checklist

- Existing board: previously processed fictional data, not live inference.
- CSV with eight fields: no PDF extraction or deterministic document checklist implemented.
- Advisory triage only: no sanctions, PEP, identity, KYC screening, approval or account activation.
- Quote presence is checked, not semantic truth. Some warnings do not change routing.
- Compliance Decision is a create-only write field, not a real approval/RBAC implementation.
- 30/30 and 14/14 are internal synthetic development checks, not real-world model accuracy.
- Do not run board setup or sync the adversarial test suite during the demo.
