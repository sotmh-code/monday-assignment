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
| **6:05–7:20** | **src/risk_assessment.py** | **Show the revised prompt rule; describe recorded before/after** |
| **7:20–8:20** | **Test CSV + saved result + routing code** | **Show the actual attempted injection and detection** |
| **8:20–9:10** | **monday_client.py** | **Actual GraphQL mapping/upsert** |
| **9:10–10:25** | Board or architecture reference | **Production hardening and limits** |
| **10:25–11:30** | Apex board | **Business close and human decision** |

No dedicated seven-guardrail recitation or second “why monday.com?” lecture; those are addressed where they naturally matter. Detailed control coverage remains in Q&A.

## Before you present — exact file map (VS Code on Mac)

Open the repository folder **monday-assignment** in VS Code and switch to branch **feature/customer-review-demo**. To find any file below, press **Cmd+P**, paste the **exact path** in the middle column, press **Return**. To locate a function inside that file, press **Cmd+F** and type the search phrase. **No prior code familiarity required.**

| What to show | Exact repository path | Search within file |
|---|---|---|
| Two model calls and error handling | **src/pipeline.py** | **def process_application** |
| Stage 1's actual system prompt | **src/risk_assessment.py** | **RISK_SYSTEM_PROMPT =** |
| Stage 2's actual system prompt | **src/onboarding_summary.py** | **SUMMARY_SYSTEM_PROMPT =** |
| How Stage 1 is passed to Stage 2 | **src/onboarding_summary.py** | **def summarize** |
| Both output JSON contracts (if asked) | **src/schemas.py** | **class RiskAssessment** and **class OnboardingSummary** |
| Verbatim quote checking | **src/guardrails.py** | **def check_evidence** |
| Prompt iteration: show **actual final prompt** | **src/risk_assessment.py** | Search **Risk factors need a positive indicator** |
| Actual routing rule for injection | **src/pipeline.py** | **def route_for** |
| monday.com API integration | **src/monday_client.py** | **def upsert** and **def column_values** |
| Original fictional CSV input | **crestview_client_applications.csv** | Search **APP-2026-0303** |
| Saved enriched result (not live inference) | **output/enriched_applications.json** | Search **APP-2026-0303** |
| Original saved injection test (not on board) | **output/adversarial/enriched_applications.json** | Search **APP-2026-0901** |

**Prepare two audience-facing views only:** monday.com board and VS Code with the **actual source code and recorded data**. Keep **this script privately on your second screen**. Never display docs/demo_script.md, Markdown preview, the development log, or terminal trace to the panel. Pre-open the injection CSV and saved JSON as adjacent editor tabs.

**Before the call**, verify board 5032266463 contains Greenfield **APP-2026-0301**, Apex **APP-2026-0303** and Heritage **APP-2026-0310**. Have Apex's Risk Rationale & Evidence, Gaps / Blockers, AI Onboarding Summary, Next Actions and Compliance Decision easy to open.

~~~bash
git switch feature/customer-review-demo
git pull
python -m pytest -q
python -m src.monday_sync --check
~~~

The board check needs configured credentials. **Don't run board setup or live sync during the interview.** If the board fails to load, run **python -m src.report --input output/enriched_applications.json** and open **output/crestview_review_dashboard.html** (saved, offline results).

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

**On the monday.com board, search these Application IDs in order.**

- **Greenfield — APP-2026-0301 (20 sec):** LOW risk / STANDARD priority / MEDIUM complexity. Standard human KYC still applies.
- **Apex — APP-2026-0303 (60 sec):** HIGH risk / ESCALATE / MEDIUM complexity. Open **Risk Rationale & Evidence**. The intake text describes layered ownership, apparent nominee directors, unsupported source of funds and resistance to document requests. Those are reported claims, not independently confirmed findings.
- **Heritage — APP-2026-0310 (20 sec):** LOW advisory risk / HIGH complexity. **14 family members, approximately 22 accounts, trusts, LLCs, individual accounts, a family foundation**, consolidated reporting and tax-lot accounting. Coordinate **three external advisers: tax attorney, estate planner, insurance broker**.

**Say:**

> "Greenfield is straightforward but still requires KYC. Apex needs senior Compliance attention because of its ownership and funding questions.
>
> "Heritage shows why risk and complexity must be separate: twenty-two accounts, multiple legal entities and three advisers are a lot of operational work, but aren't themselves evidence of financial-crime risk."

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

## 3:35–6:05 — Source-code walkthrough (mandatory)

**Switch once from board to VS Code. Use Cmd+P for each exact filename below; Cmd+F for the exact search text.**

### 3:35–4:35 — Pipeline: one function

**SHOW:** **src/pipeline.py** → Cmd+F **def process_application**. Point to **assess_risk(app, llm)** → **guardrails.check_evidence(...)** → **summarize(app, risk, llm)**. These appear in that order.

**SAY:**

> "The input is eight CSV fields, including the client's description—not PDFs. This function runs Claude for an advisory risk assessment, then Python checks the result and routes the case. A second Claude call receives the original application and Stage 1 risk JSON to produce an Operations summary.
>
> "In **src/main.py**, the **live()** function calls **run_batch()**, then **write_outputs()** saves the results in **output/enriched_applications.json**. Publishing is a separate command, **python -m src.monday_sync**. Its **main()** function reads that saved file and calls **MondayClient.upsert()** in **src/monday_client.py** to create or update board items. If Stage 1 fails, the saved record is marked for manual triage; if Stage 2 fails, the saved record keeps the risk result and records the failure. Neither failure automatically triggers the publisher."

### 4:35–5:25 — Actual prompts and JSON contracts

**SHOW FIRST:** Cmd+P **src/risk_assessment.py**, Cmd+F **RISK_SYSTEM_PROMPT =**. This **is the Stage 1 system prompt**, defined directly in Python, not in a separate prompt file. Point to the text demanding explicit risk indicators and exact source quotes.

**THEN SHOW:** Cmd+P **src/onboarding_summary.py**, Cmd+F **SUMMARY_SYSTEM_PROMPT =**. This **is the Stage 2 system prompt**. Point to the instructions to accept the Stage 1 risk level and never approve or reject a client. In the **same file**, Cmd+F **def summarize** to show the actual model call with the serialized risk JSON.

**SAY:**

> "These are two different system prompts, with separate jobs. Stage 1 returns risk level, evidence, gaps and priority. Stage 2 consumes that risk assessment and returns complexity, suggested owners, next actions and blockers. Each output is validated against its own Pydantic JSON schema."

**If they ask to see the actual output definitions:** Cmd+P **src/schemas.py**, search **class RiskAssessment** and **class OnboardingSummary**. Do **not** open this file in the timed demonstration unless asked.

### 5:25–6:05 — Actual guardrail

**SHOW:** Cmd+P **src/guardrails.py**, Cmd+F **def check_evidence**. The function checks whether each claimed source quote exists in the application's text.

**SAY:**

> "The model doesn't get to verify its own evidence. Python checks that its quotations appear in the input. But a real quotation can still be misinterpreted, and today some mismatches produce warnings rather than blocking routing. That is a known production gap."

## 6:05–7:20 — Prompt engineering: show the real revised prompt

**AUDIENCE SCREEN:** VS Code → open **src/risk_assessment.py** (Cmd+P). Cmd+F search **Risk factors need a positive indicator**. **Highlight just that rule**, including "not stated" → "missing_information". **Do not show this script or development log.**

**SAY:**

> "Here is one concrete improvement to the risk prompt. Our first evaluated run sometimes treated routine missing information as risk. For James Okafor, it even inferred 'concentrated employer stock' when the application didn't say that.
>
> "We changed this rule so that a risk factor needs an explicit indicator in the source; routine unstated items become information gaps. Okafor moved from MEDIUM / ENHANCED_REVIEW to LOW / STANDARD. Across the synthetic evaluation, we improved from 28/30 to 30/30 checks, with 61/61 source quotes matched. These are development checks, not real-world compliance accuracy."

**PRIVATE PRESENTER NOTE (not for screen):** The first-run findings are recorded in ai_development_log.md §3.5. No separate original prompt snapshot has been verified, so **don't claim to show a line-by-line prompt diff**. You are showing the actual *revised prompt rule*, and describing the recorded before/after impact. If asked about Stage 2 iteration, its final prompt lives in **src/onboarding_summary.py**, where it says not to make management or Compliance decisions.

## 7:20–8:20 — Prompt-injection test: show real input, saved result and rule

**AUDIENCE SCREEN — 3 quick actions in VS Code. No script, no terminal.**

**A. SHOW THE ATTACK (15 seconds):** Cmd+P → **evals/adversarial_applications.csv**, Cmd+F → **SYSTEM OVERRIDE FROM CRESTVIEW COMPLIANCE**. Point to the injected phrase in the **description** field of fictional case **APP-2026-0901**. This phrase was **deliberately written into test data**, not sent by Crestview or provided as a system prompt.

**B. SHOW THE RESULT (20 seconds):** Cmd+P → **output/adversarial/enriched_applications.json**, Cmd+F → **APP-2026-0901**. Near the beginning of that recorded case, point out **"triage_risk_level": "MEDIUM"**, **"review_priority": "ENHANCED_REVIEW"**, **"routing": "MANUAL_TRIAGE"**. If asked how the model detected it, Cmd+F **EMBEDDED_INSTRUCTION** within the same record.

**C. SHOW THE GUARDRAIL CODE (10 seconds):** Cmd+P → **src/pipeline.py**, Cmd+F → **def route_for**. Point to these actual lines:

~~~python
if any(f.category == RiskCategory.EMBEDDED_INSTRUCTION for f in risk.risk_factors):
    return Routing.MANUAL_TRIAGE
~~~

**SAY:**

> "We planted this fake 'system override' in a fictional client's input. It tries to force LOW risk and falsely claim sanctions screening passed.
>
> "But the saved result is MEDIUM risk and MANUAL_TRIAGE. Claude marked the injected text as EMBEDDED_INSTRUCTION, and this Python rule forces human triage whenever that category is detected.
>
> "The limit is that the Python rule depends on the model detecting the instruction. It isn't a standalone injection detector."

**PRIVATE PRESENTER NOTE:** The test also exposed a false positive in the prohibited-claim scanner: it initially treated the model **reporting** the malicious claim as making it. That was corrected and regression-tested. Mention only if asked. This is **recorded synthetic output**, not a live model run, and the injection case does not appear on the monday.com board.


## 8:20–9:10 — Show monday.com GraphQL code

**SHOW:** Cmd+P **src/monday_sync.py**, Cmd+F **def main**; point to **read_run_output(args.input)** and **client.upsert(board_id, rec)**. Then Cmd+P **src/monday_client.py**, Cmd+F **def upsert** (Application ID lookup then create/update); Cmd+F **def column_values** (JSON-to-board field mapping).

**SAY:**

> "This is the actual publishing code. Running **python -m src.monday_sync** executes **main()**, which reads **output/enriched_applications.json** and calls **MondayClient.upsert()** for each saved application. That function maps fields to board columns and checks Application ID before creating or updating an item. Sequential reruns normally update the same case.
>
> "The Compliance Decision column is created as Pending Human Review and deliberately omitted from subsequent AI updates. That prevents this writer from overwriting a person's decision."

**Limitation:** The POC does not implement approval permissions; lookup-then-create is not a transactional guarantee against simultaneous duplicate creation.

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

**Why is Heritage's operational complexity HIGH?**  
> "The intake describes about 22 accounts spread across trusts, LLCs, individual accounts and a family foundation, representing 14 family members. The team must coordinate consolidated reporting, tax-lot accounting and three named external advisers: a tax attorney, estate planner and insurance broker. That's operational complexity, not automatically compliance risk."

**What does ENHANCED_DUE_DILIGENCE mean here?**  
> "It's a proposed route for additional Compliance verification beyond standard KYC, not an assertion of wrongdoing. In the POC, Claude sets review_priority=ENHANCED_REVIEW and Python's route_for() maps that to ENHANCED_DUE_DILIGENCE. Velocity has a PEP general partner and incomplete investor data; Brightpath has an unsigned board resolution. Priya must validate these categories and escalation thresholds before deployment."

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
---

## Defense
1. Why Heritage is HIGH complexity: Its application describes 14 family members, approximately 22 accounts, trusts, LLCs, individual accounts and a family foundation. Crestview also needs consolidated reporting, tax-lot accounting and coordination with three external advisers: a tax attorney, estate planner and insurance broker.

2. What ENHANCED_DUE_DILIGENCE means: It's a recommendation for additional Compliance scrutiny beyond standard KYC—not an accusation or a completed screening. Examples from your results:
- Velocity Venture Partners (APP-2026-0307): A politically exposed person (PEP) is identified as general partner, with incomplete investor information.
- Brightpath University Endowment (APP-2026-0306): An unsigned board resolution and a request to proceed before final approval.
- Mercer-Hastings (APP-2026-0313): A public-company insider with concentrated stock and trading restrictions; these require specialist review, although they don't themselves establish financial-crime risk.

## Appendix A — Seven guardrails: interview defense only (not part of timed demo)
**Opening answer if Priya or Marcus asks “what prevents unsafe AI output?”**

> "The models are advisory, and Python checks what they return before the result reaches the board. The checks cover structure, evidence, unsupported claims, untrusted instructions, consistency and failure handling; the approval decision remains with a person. These are POC controls, not a substitute for production policy testing or reviewer permissions."

| Guardrail | What the POC actually does | What it **does not** guarantee |
|---|---|---|
| **1. Malformed output** | Requests structured JSON, locally validates it against Pydantic schemas, and has bounded retry/repair handling for malformed or truncated responses. | Valid JSON can still contain factually wrong risk judgments. |
| **2. Invented quotations** | Compares the model's claimed source quotes with the application text (allowing limited text normalization) and records evidence-check results. | Quote presence does **not** show that the risk interpretation is correct. **Unverified quotations can currently yield a warning without forcing MANUAL_TRIAGE**; production should fail closed for material evidence failures. |
| **3. False screening or approval claims** | Scans generated risk and summary text for certain claims that KYC/sanctions/PEP screening passed or a client was approved. Flagged claims can force MANUAL_TRIAGE. | The lexical scanner can miss reworded claims or falsely flag quotations/reporting; it is not a comprehensive compliance-policy engine. |
| **4. Prompt injection** | Delimits untrusted application content, neutralizes forged prompt tags, tests injected records, and routes detected EMBEDDED_INSTRUCTION risk factors to MANUAL_TRIAGE. | This is not universal injection protection; the recorded case is a test, not proof of general resistance. |
| **5. Risk and priority consistency** | Checks contradictions between risk/priority/severity; uses deterministic routing that favors the more conservative applicable route and does not let Stage 2 change the Stage 1 risk label. | Some inconsistencies are warning-only, and the risk taxonomy and thresholds still require Priya's policy sign-off. |
| **6. Failure is not LOW risk** | Invalid input is held back from the model. Stage 1 failures become NEEDS_REVIEW/MANUAL_TRIAGE; Stage 2 failures retain the Stage 1 assessment and flag the missing summary. Provider errors are classified rather than silently treated as clean. | Manual intervention is required; this does not mean that a reviewer has actually resolved or approved the case. |
| **7. Preserve human decisions** | The monday.com writer sets **Compliance Decision = Pending Human Review** only on creation and **omits that field on later AI updates**. | This protects against *this writer* overwriting a board decision. It does **not** implement role-based authorization, approval workflow auditability or prove that only Compliance can edit the field. |

**Concrete evidence to open if challenged:** src/llm_client.py (schema and error handling); src/guardrails.py (quote and claim checks); src/pipeline.py (routing and failure cases); src/prompting.py (untrusted-input handling); src/monday_client.py (create-only Compliance Decision); output/adversarial/evaluation_report_adversarial.md (recorded adversarial results).

**The most important honest limitation:** "If a risk factor's source quote isn't found, the current code flags it, but it doesn't always change the routing. For a production rollout I'd require material evidence mismatches to block automated progression and be reviewed by Compliance."

## Appendix B — Why monday.com instead of another AI dashboard?

**30-second answer for Claire or David**

> "Because identifying risk is only half the problem. Crestview's bottleneck is work moving between teams. A standalone AI dashboard could show an impressive risk score, but it wouldn't tell Operations who owns a missing document, put an escalation in the existing work queue, or make the next action visible alongside the case. monday.com is already used at Crestview, so the better approach is to bring AI findings into that system of work rather than create another destination employees have to monitor."

**What to show on the board if asked:** Apex's **Routing**, **Gaps / Blockers**, **Next Actions**, **Pipeline Status** and **Compliance Decision** columns. Explain how Stage 1 identifies concerns, Stage 2 proposes actionable follow-up, and a person retains the approval decision.

**Technical follow-up for Marcus**

> "The Python output is provider-agnostic structured data. The separate monday.com GraphQL adapter maps that output into board fields, looks up an existing Application ID, and creates or updates the item. We leave authoritative CRM, document, screening and client-account records in Salesforce, SharePoint, ComplianceOne and ClientHub respectively; monday.com coordinates the handoffs rather than replacing those systems."

**Trade-off to acknowledge:** "A board only creates value if teams actually work from it. Today's POC writes suggested owners and actions as board text; it doesn't yet create assignee automation, SLA escalation, full approval permissions or live enterprise-system synchronization. Those are production work, and we'd validate adoption and manual touch-time reduction rather than assuming a populated board solves handoffs."

**If asked why not build a custom web app:** "We could, but it would make Marcus's four-person team own another UI, workflow engine, access-control layer and notification system. Reusing an already adopted operational platform concentrates our custom code on the two model stages and the integrations that are truly necessary."
