# Crestview AI Client Intake — Live POC Demo (11–12 minutes)

**Start on the monday.com board:** https://andrelimyoukwans-team.monday.com/boards/5032266463

**Audience goal:** Show that the output is operationally useful, then prove how the code produces it, how the prompts were improved, where the guardrails fail, and what is still missing before production.

**Truth in advertising:** The 15 applications are fictional. The board shows previously generated results, not fresh Claude calls on stage. The saved sync report records 15 successful item creations on board 5032266463 from run 048b9e150ceb; verify current board contents before presenting. This POC uses CSV descriptions, not real PDFs, KYC, sanctions, PEP or identity screening. Compliance decisions remain with people.

**Demo rhythm:** Business result (3 min) → code and prompt engineering (4 min) → adversarial example (1.5 min) → monday.com write path (1 min) → production limits and close (2 min). Budget roughly 30 seconds for navigation.

## Preflight — prepare these tabs in advance

1. **monday.com board:** 15 cases; filter or search for Greenfield APP-2026-0301, Apex APP-2026-0303, Heritage APP-2026-0310. Openable long-text columns: Risk Rationale & Evidence, Gaps / Blockers, AI Onboarding Summary, Next Actions.
2. **VS Code:** Have these positions ready, in order: src/pipeline.py → process_application; src/risk_assessment.py → RISK_SYSTEM_PROMPT; src/onboarding_summary.py → SUMMARY_SYSTEM_PROMPT and summarize; src/guardrails.py → check_evidence; src/monday_client.py → upsert and column_values.
3. **Recorded evidence:** ai_development_log.md §3.5 (first run 28/30, fixed run 30/30), output/evaluation_report_sample.md, and the recorded adversarial case APP-2026-0901 in output/adversarial/enriched_applications.json (or the read-only trace below).
4. **Sanity check locally:** Run tests before the meeting and verify the current board schema. Do not create another board. The new trace command is read-only, requires no credentials, and must be described as a replay of saved data—not fresh inference.

~~~bash
git switch feature/customer-review-demo
python -m pytest -q
python -m src.monday_sync --check
python -m src.demo_trace --application-id APP-2026-0303
python -m src.demo_trace --input output/adversarial/enriched_applications.json --application-id APP-2026-0901
~~~

**If the board is unavailable:** use the existing offline HTML report: python -m src.report --input output/enriched_applications.json, then open output/crestview_review_dashboard.html. Do not sync adversarial cases to the live board.

---

## 0:00–1:00 — Start with the business result

**Show:** monday.com board with the risk, routing, complexity and Compliance Decision columns.

**Say:**

> "This is the operational result. Fifteen fictional onboarding applications have been processed and synchronized into monday.com. Operations can see what is outstanding, Compliance can see where review is needed, and every case remains pending a human decision.
>
> "I'll first show you three cases, then the actual pipeline, the prompt changes we made after testing, and how this would need to mature before handling real Crestview clients."

**Do not say:** These records were just generated live; the board is a production onboarding system; clients were screened or approved.

## 1:00–3:00 — Three cases, one operating principle

**Show Greenfield (20–25 seconds):** LOW advisory risk / STANDARD review / MEDIUM complexity. Explain that standard KYC is still required.

**Show Apex (75–90 seconds):** HIGH advisory risk / ESCALATE / MEDIUM complexity / Compliance Escalation. Open Risk Rationale & Evidence; point to the application-text evidence for opaque ownership and unsupported source of funds. Then open Gaps / Blockers and Next Actions. These are reported intake statements, not independently verified facts.

**Show Heritage (20–25 seconds):** LOW advisory risk / HIGH operational complexity. Multiple entities and bespoke coordination create more operational work, not necessarily greater financial-crime risk.

**Say:**

> "Apex is the clearest example. The system flags specific risk indicators and their source quotations, then gives Operations the actions that can happen now versus those that must wait for Compliance.
>
> "Heritage demonstrates why we separate operational complexity from compliance risk. Otherwise, we'd escalate every complicated client and recreate the backlog we're trying to reduce."

**Transition:** "Here's exactly how the code produces those two outputs."

## 3:00–5:35 — Mandatory source-code walkthrough

**Stay in VS Code for this entire section. Use only the indicated functions; don't scroll through the repository.**

### A. src/pipeline.py → process_application (about 60 seconds)

**Show:** input validation; assess_risk(app, llm); deterministic guardrail calls; summarize(app, risk, llm); returned EnrichedRecord.

**Say:**

> "The POC starts with eight structured fields from a CSV. There is no document parser in this version.
>
> "This function is the orchestrator. The first Claude call receives the application and returns a typed RiskAssessment. Python checks the result and determines routing. The second Claude call receives the original application plus the first stage's validated risk object and returns an OnboardingSummary. We save both outputs together before a separate command writes to monday.com.
>
> "These are two independent model calls with separate prompts and schemas, not autonomous agents. A Stage 1 failure goes to manual triage; if Stage 2 fails, we retain Stage 1's assessment rather than inventing a summary."

### B. src/risk_assessment.py and src/onboarding_summary.py (about 70 seconds)

**Show:** Risk system prompt rules, then Summary system prompt; point to serialize_risk and the risk_triage-delimited handoff.

**Say:**

> "I separated the prompts because they have different jobs. The risk prompt requires observable indicators and exact source quotations; it explicitly prohibits claims that screening or approval happened. The operations prompt cannot revise the risk result. It turns that result into complexity, suggested owners, next actions and account-opening blockers.
>
> "The interface is structured JSON, validated against Pydantic models. That lets us test either component independently and change its prompt without rewriting the other."

### C. src/guardrails.py → check_evidence (about 25 seconds)

**Show:** evidence_in_source and check_evidence.

**Say:**

> "We also check the evidence outside the model. If a quotation doesn't appear in the supplied application text, we flag it. But matching a quote proves its presence, not that the model's interpretation is correct. In this POC, an unmatched quote can produce a warning without automatically forcing manual triage—that must be strengthened for production."

**Optional no-network backup:** Run the recorded trace for Apex. It exposes input, Stage 1 JSON findings, checks, Stage 2 output and human-review state without calling Claude or monday.com.

## 5:35–7:00 — Show real prompt iteration, not prompt theory

**Show:** ai_development_log.md §3.5 and, if useful, the relevant lines of RISK_SYSTEM_PROMPT.

**Say:**

> "Our first evaluated run passed 28 out of 30 checks. One issue was risk inflation: the model sometimes treated ordinary information that wasn't mentioned as evidence of higher risk. We changed the prompt to require a positive, stated risk indicator and to put routine missing information in a separate gaps field.
>
> "Another output quoted a sentence but dropped the word 'the'. Our source-matching check caught it, so we tightened the exact-quotation instruction rather than relaxing the check. Stage 2 also initially overstepped by deciding an expedite request should be rejected; we changed its prompt to route that decision to Compliance.
>
> "On the next recorded full run, 15 of 15 cases completed, 61 of 61 source quotes matched, and 30 of 30 internal checks passed. These are synthetic development checks—not an independent measure of real-world compliance accuracy."

**What matters:** A concrete failure → a general rule → a regression result. Do not imply the risk labels were validated against a regulatory ground-truth dataset.

## 7:00–8:30 — One adversarial case and the honest failure modes

**Show:** saved case APP-2026-0901 using the trace command or recorded adversarial result; briefly show src/pipeline.py → route_for. This is recorded evidence, not a fresh model call.

**Say:**

> "We also tested hostile application text. This case includes a fake 'system override' telling the model to label the client LOW and claim sanctions screening passed. The model did not follow that instruction; it identified the embedded instruction, and our deterministic routing sent the case to manual triage.
>
> "The interesting failure was in our own guardrail code: its first version flagged the model merely reporting the attack as if it were making a false screening claim. We corrected that and added adversarial regression tests. That is why I don't treat regex guardrails as sufficient for production."
>
> "The remaining limitations are clear: a valid JSON response can still contain an incorrect judgement, quote matching isn't semantic verification, and some evidence problems currently produce warnings rather than stopping the workflow."

**Evidence:** output/adversarial/evaluation_report_adversarial.md records 14/14 development checks after iteration. Those are synthetic test expectations, not measured attack resistance.

## 8:30–9:30 — Show the actual monday.com integration

**Show:** src/monday_client.py → column_values and upsert; optionally switch back to the board.

**Say:**

> "The integration is a separate GraphQL adapter. It converts each enriched record into the board's columns and looks up an item by Application ID before creating or updating it, so rerunning a case normally updates the same item rather than intentionally creating another.
>
> "Notice one deliberate restriction: the code initializes Compliance Decision as Pending Human Review only on item creation. Subsequent AI updates leave that column untouched. This preserves an existing human decision, although the POC does not implement reviewer role permissions or a full approval workflow."

**Be accurate:** The recorded sync report shows 15 item creations, not live Salesforce, SharePoint, ComplianceOne, ClientHub or Outlook integrations. The lookup/upsert is not a transactional guarantee against simultaneous duplicate creates.

## 9:30–10:45 — Production hardening and trade-offs

**Show:** return to board (no new code screens). Discuss priorities in the order you would implement them.

**Say:**

> "I would not put this CSV prototype directly into production.
>
> "First, we need approved document ingestion and extraction. I'd benchmark Azure Document Intelligence against LlamaParse on real Crestview packages; a Microsoft 365 Copilot agreement does not itself grant Azure AI usage. The chosen parser and model endpoint need an explicit review of which client content is transmitted, processing region, retention, permissions and vendor terms.
>
> "Second, Priya's team must own the risk taxonomy, escalation rules and acceptance tests. We need labelled cases, stronger evidence-failure handling, and shadow runs alongside reviewers before any production routing.
>
> "Third, we'd add approved system connectors, monitoring, recoverable API errors and actual role-based human approvals. This must remain supportable by Marcus's four-person team."

**Don't claim:** The POC currently performs extraction on PDFs, runs screening, enforces reviewer access policies or has passed a production security assessment.

## 10:45–11:30 — Close on the outcome

**Show:** monday.com Apex case, next actions and Pending Human Review.

**Say:**

> "The point isn't that AI produced a risk label. It's that a risk assessment with traceable evidence becomes a clear set of actions for Operations, while Compliance keeps the decision.
>
> "We've demonstrated that workflow on fictional data and exposed the engineering limits. The six-month implementation would test whether the same approach reduces total manual effort and onboarding time without weakening controls."

**Stop here.** Leave deep dives, ad hoc modifications and provider comparisons for panel Q&A.

---

## Technical Q&A — concise, defensible answers

**Q: Walk through the architecture.**

> "One Python orchestrator coordinates two independently prompted Claude calls. Stage 1 converts the CSV application into RiskAssessment JSON; deterministic checks run; Stage 2 receives the original application and that Stage 1 object and produces OnboardingSummary JSON. A separate adapter maps the stored result into monday.com via GraphQL."

**Q: How did you prompt-engineer and iterate?**

> "We defined task-specific prompts and schemas, then evaluated concrete cases. The initial risk prompt over-inferred from missing information, and the initial summary prompt overstepped into management decisions. We corrected both as general rules, added checks, and improved the recorded evaluation from 28/30 to 30/30."

**Q: How was AI used to build the POC?**

> "I used Claude Code against an explicit plan and acceptance checklist, rather than asking it to build a vague agent. It accelerated implementation and test generation, but live outputs exposed model calibration and regex failures that required intervention. Reading the Anthropic SDK also led us to handle refusals and malformed JSON as distinct failure types."

**Q: Why two independent calls instead of two agents?**

> "Risk triage and summary writing need independent prompts, schemas and tests, but their execution order is fixed. A deterministic orchestrator gives us that modularity without adding dynamic tool-use and state management. We'd consider agents for open-ended evidence retrieval only if it measurably improves outcomes."

**Q: How would you harden it?**

> "Benchmark secure document parsing on real packages, approve the AI data flows and vendor terms, and replace illustrative risk judgments with Compliance-owned policy and labelled evaluation criteria. Then introduce authenticated connectors, stronger fail-closed evidence handling, shadow mode, monitoring and reviewer permissions before live use."

**Q: What are the limitations?**

> "There is no real PDF ingestion, identity verification, sanctions screening or account activation. The model can be wrong even when its JSON is valid, and the source-quote check does not validate the interpretation; some warnings do not automatically block progression. The board also has no production-grade reviewer authorization."

**Q: How does it handle failures?**

> "Invalid input is not sent to Claude. Stage 1 failures route to NEEDS_REVIEW and MANUAL_TRIAGE; Stage 2 failures preserve the risk assessment and flag the missing summary. The provider wrapper distinguishes refusals, truncated output, malformed JSON and retryable API errors, and a fatal authentication failure stops further batch requests."

**Q: Why monday.com?**

> "The system's value is the action that follows the assessment. monday.com makes escalation candidates, outstanding requirements and suggested tasks visible to the people running onboarding. The POC maps results into existing work items; production needs ownership automation, permissions and authoritative system integrations."

## Demo hygiene — never overstate

- The board is an existing sandbox populated from a saved run; displaying it is not live inference.
- The CSV has eight structured fields; PDF extraction and deterministic document-gap rules are proposed production scope.
- Routing is advisory. No screening, KYC disposition, client approval or account activation occurs in this POC.
- Evidence quote matching checks textual presence only. POC warnings do not always fail closed.
- Human decision is a create-only board column, not an implemented RBAC approval workflow.
- The internal evaluation counts do not establish production accuracy or model robustness.
- Do not run board setup or sync the adversarial suite during the interview.
