# Crestview — executive presentation script (final)
**Audience:** Claire (COO), David (Client Operations), Priya (Compliance), Marcus (Technology)  
**Format:** Seven proposal slides + POC handoff; approximately 13–15 minutes including the diagram walk-through and pauses, then the board demonstration  
**Central argument:** Time is lost at handoffs, not just in data entry. monday.com coordinates the case; AI prepares evidence and next actions; humans decide. Test it on real work before scaling.
---

## Slide 1 — From 23 business days to 5
**One point:** Five days is a workflow target, not an AI promise.

**Say:**
“Last quarter, Crestview lost a prospective $200 million allocation because a competitor onboarded the client in five days while Crestview took four weeks.

“The target is to cut the average from 23 business days to five. Buying another AI tool won't do that. The time savings come from eliminating repeated entry, making delays visible and allowing Operations to prepare its part while Compliance reviews.

“My proposal is simple. monday.com owns the onboarding workflow. AI prepares the information and next actions. Compliance keeps the decision. Once Compliance approves and ClientHub setup is complete, the account can be activated for funding. AI never makes that final call.”

**Bridge:** “Here's where those 23 days are going.”

## Slide 2 — The delay is between systems

**One point:** The delay sits between departments; exceptions are where the current process fails.

**Say:**

“A relationship manager collects the client package. Operations re-enters its contents in ClientHub, stores documents in SharePoint and requests screening. Compliance checks the case in ComplianceOne and emails findings back; Operations updates ClientHub again. The process stops at each handoff, but nobody has a single view of who is waiting on whom.

“Much of that time is avoidable. As soon as the required information is received, Operations should be able to start preparing the account while Compliance conducts its independent checks. Account activation still waits for approval; ordinary preparation does not.

“The cost is visible: 85 pending compliance reviews, 18% abandonment, and about $12 million in annual revenue at risk. These are the client's baseline figures—not savings we've delivered.

“David's team already tried RPA. It looked promising in the demo, but failed when document layouts changed or cases needed exception handling. Staff spent more time fixing it than entering the data themselves. Our design must expose exceptions instead of hiding them. If a signatory document is missing, the case creates a visible request for the RM and remains blocked until it is resolved—not buried in an email thread.”

**Bridge:** “That calls for one accountable workflow, not five system replacements.”

## Slide 3 — One system of work. Five systems of record.
**One point:** One visible case replaces the manual coordination layer; existing platforms keep their specialist roles.

**Say:**
“Today an application exists in fragments: a Salesforce opportunity, documents in SharePoint, client data in ClientHub, screening in ComplianceOne and correspondence in Outlook. We bring the *work* together in monday.com. Each client has one visible case: the current stage, the outstanding request, the responsible team, and the next action.

“We aren't asking Marcus to replace five established systems in six months. They already perform different jobs. Replacing ComplianceOne would mean revalidating a regulated screening function; migrating ClientHub would add risk before we've even understood its ageing API. We're replacing manual coordination, not authoritative records.

“Take one example. ComplianceOne finishes screening. monday.com records that the next step is ready. If Compliance needs another document, the RM sees the request and the case cannot quietly advance. If a write to ClientHub fails, we retain the same application ID, flag the error and retry safely—otherwise an outage could silently lose or duplicate an account. We'll assess ClientHub's API in the first two weeks rather than assume it supports this.

“Marcus, we'd also use Crestview's Microsoft investment. SharePoint remains the document repository; Outlook and Teams handle communication; Entra ID provides the identity foundation. One experiment is to connect Copilot to monday.com using MCP, a tool interface for fetching a permitted board status. A relationship manager could ask, ‘Which of my clients are blocked, and what do they need?’ We start read-only: the assistant can explain a case, but cannot change or approve one. First we verify each person sees only the records they are entitled to see.”

**Bridge:** “With the work visible in one place, this is where AI can remove the manual effort.”

## Slide 4 — AI prepares the work; people make the decisions
**One point:** AI helps prepare a defensible decision. The POC proves two of the four proposed steps
The production design has four jobs. 
1. First, read incoming PDFs and emails and extract names, signatories, dates and investment restrictions, linked to the source documents. Output: Structured JSON containing extracted client information, document metadata and source references.
2. Second, check those facts against the required package for that client type. That turns ‘we think the paperwork is complete’ into a specific list of what is present, missing or unclear. Gap detection means identifying what's missing, incomplete, or inconsistent in a client's onboarding package before it moves to Compliance. This step is determinstic (using python rules and leaning on domain expertise).

These first two capabilities are proposed; our POC starts with structured CSV data, not actual documents.

3. Third is risk triage, which we've built. The first Claude call reads eight supplied application fields—including a description—and returns an advisory risk level, specific risk factors, source quotations and missing information (Risk Assessment JSON). Python then validates the structure, checks that quotations occur in the supplied text, and assigns a review queue under fixed rules. A model opinion alone never becomes a compliance approval.

4. Fourth is the operations summary, our second Claude call. It receives both the application and the validated risk assessment. It produces a short client brief, the operational complexity, next actions, suggested owners and account-opening blockers (summary JSON). In Apex, elevated risk calls for Compliance escalation; in Heritage, numerous accounts increase operational work without implying elevated financial-crime risk. These outputs are then synchronized to monday.com. Two sequential calls—no autonomous agents.

“Why separate the calls? We can inspect the risk judgment before it shapes the operational instructions. Why the checks? Priya needs to trace a risk flag to its source and challenge it. Quote matching catches unsupported quotations, but it does not prove the model's interpretation. That is why the model only recommends: ComplianceOne performs actual screening, a person decides, and activation follows only after approval.”

**Presenter cue:** Trace a case through the four boxes, then point to the control line beneath them. Do not read the control labels one by one.

**Bridge:** “The question isn't whether that works in a demo. It's whether it survives real intake.”

## Slide 5 — Six-month implementation; one controlled pilot
**One point:** A controlled Month 4 pilot sits inside the six-month implementation—not the other way around.

**Say:**
“I'd use the six months in stages, with a stop/go decision before each major release.

“Month 1: watch real cases, measure where time is lost, inspect ClientHub's API and get the security and Compliance design approved. Month 2: build the board and run AI in shadow mode—on real packages, alongside human reviewers, without using AI judgments to move live clients. We test difficult documents and measure where the model gets things wrong.

“Month 3: integrate the core systems and test the workflow end to end. We test failure recovery deliberately: if ClientHub times out or ComplianceOne cannot respond, can Operations see the failure and recover without losing or duplicating a case? If not, it is not ready for production. Before any real client data reaches an AI provider, Marcus also signs off on what data is sent and how access is controlled.

“Month 4 is the controlled production pilot for one client segment. Every compliance decision remains human. We compare cycle time, manual effort, rework and reviewer corrections with Month 1. If the controls fail or the savings disappear once rework is counted, we stop expansion. Months 5 and 6 cover wider adoption, training, documentation and handover to Marcus's four-person team.

“David's team should help design those exception paths, not inherit another black box. We don't trust a good demo; we trust results from real cases and a process that handles its failures.”

**Bridge:** “So what results would justify the next release?”

## Slide 6 — Measure speed without sacrificing control
**One point:** Faster processing only counts if total onboarding effort falls without increasing compliance risk.

I would have three measures on the slide:
- Speed: End-to-end onboarding time and time spent waiting between teams.
- Efficiency: Total staff hours per application, including corrections and rework.
- Control: Compliance override rate, evidence errors and human approval coverage.

**Say:**
"The five-day target matters, but faster AI processing alone doesn't prove success.
"We need to measure the entire onboarding journey, including time spent correcting AI mistakes. That's precisely where Crestview's previous RPA initiative failed.
"So our pilot has three tests: are clients onboarded faster, are employees doing less total work, and is Compliance maintaining control?
"If AI makes the initial step faster but increases downstream rework, we haven't succeeded."

**Bridge:** “If onboarding meets those standards, the same operating pattern has value beyond onboarding.”

## Slide 7 — Prove onboarding; then scale the pattern
**One point:** Prove the onboarding model, reuse it across operations, and authorize the first implementation phase.

**Say:**
"The opportunity goes beyond client onboarding.
"Once we've established a reliable pattern for collecting information, identifying exceptions, assigning work and recording human decisions, we can reuse that model in other processes—starting with portfolio operations.
"For monday.com, the engagement also provides product feedback from a regulated enterprise. I'd focus on whether the platform adequately supports evidence-linked AI outputs, auditable approvals and controlled AI access.
"What I'm asking for today is agreement on the six-month implementation direction, named owners from Operations, Compliance and Technology, and authorization to begin Month 1 discovery and design.

**Bridge:** "Before that decision, let me show you what I've already built."

## Slide 8 — Live POC handoff
**One point:** Show the evidence, don't narrate the code.

**Say:**

“We processed 15 fictional applications with two linked Claude calls: risk triage first, then a summary that uses the risk assessment. The resulting records have been synchronized to this monday.com sandbox. Let's compare three: Greenfield for routine intake, Apex for elevated risk, and Heritage for operational complexity without an elevated risk flag. Every case is still waiting for a human compliance decision.”

**Open:** https://andrelimyoukwans-team.monday.com/boards/5032266463

**After the demo — decision line:** “You've seen the narrow proof. I'd like Claire's endorsement to start Month 1, with David, Priya and Marcus as named owners, so we can validate this on real workflows before any production rollout.”

---

## Private defense notes — not spoken unless asked

**Why keep the five systems?** The bottleneck is their coordination, not proof that they all need replacement. Swapping screening or client-master platforms adds data migration and assurance work before addressing handoffs. Start with governed integration; revisit platform consolidation after we have usage and API evidence.

**What does ‘integrate’ mean?** For example, when a ComplianceOne review finishes, an adapter updates the same monday.com case; if the target is unavailable it retries and records the failure. On recovery, the same case is updated rather than creating duplicates. This is proposed behavior, not implemented for ComplianceOne in the POC.

**What exactly is the POC?** One Claude request for risk assessment; Python schema, quote and policy checks; one Claude request using that risk object to write an operations summary; deterministic routing; saved JSON/CSV; separately run GraphQL upsert into monday.com. No autonomous agents, PDF OCR, live screening or account activation.

**Why do two model calls instead of one?** A separate risk object can be validated, inspected and reused before the model writes operational actions. This keeps a clear lineage from finding to action. We pay for a second call to make that boundary explicit.

**How strong is the evidence check?** The code verifies that the quoted text occurs in the application. This catches fabricated quotations but cannot establish whether the quoted fact justifies the risk label. Today's POC may warn rather than hard-stop on some issues. Production needs policy-approved thresholds and human testing on real documents.

**Why not use a guardrails/agent framework?** There are only two sequential model calls; narrow deterministic rules and typed schemas are easier to audit than a general-purpose agent stack. Add a framework only if a concrete control or observability gap warrants it.

**What is MCP, and why read-only?** MCP is a protocol allowing an assistant to call approved tools; here, the candidate tool would retrieve status from monday.com. Read-only reduces the consequence of a mistake while we test connector compatibility, authorization, user-level permissions and audit logging. The trial is proposed, not currently implemented.

**What are the key risks?** Document variability (shadow evaluation); risk-model error (quote checks, labelled reviews and human sign-off); fragile ClientHub API (early assessment and recovery path); data sensitivity (approved endpoint and least-privilege access); adoption (co-design with Operations and Compliance, manual-touch measurement).

**What does Claire authorize?** Month 1 mobilization of the existing six-month FDE engagement, its owners and agreed decision gates—not six months of unrestricted production AI. Month 4 is the limited pilot.

**What product feedback?** Only report tested customer friction, such as evidence-linked AI fields and reviewer attribution, resilient integration status/recovery, or role-scoped AI tool access. Validate existing monday.com support before claiming a product gap.

**Why not use separate agents per LLM call?** -> do we need autonomous tool-directed execution?
Each model-backed service can have its own system prompt. There's no requirement for one global prompt.

Your actual POC already follows this pattern for its two stages:
- src/risk_assessment.py defines its own risk-triage system prompt.
- src/onboarding_summary.py defines a separate operational-summary system prompt.
- src/pipeline.py orchestrates the calls and applies deterministic checks.
- src/llm_client.py provides the shared Claude API interface.

**Data security & sovereignity**


## Design choices
1. Three specialized model-backed components, not a monolithic agent: Document extraction, risk triage and summary generation have separate prompts, schemas and evaluations. If risk assessments become unreliable, the team can isolate that component without redesigning the entire system.

2. Deterministic orchestration and business rules: The sequence is predictable. Compliance requirements live in versioned configuration rather than being buried in an LLM prompt. An engineer can update a checklist without retraining or redesigning the model.

3. One integration adapter per system: A ClientHub API change should affect the ClientHub adapter, not the AI pipeline or monday.com workflow logic. Failed writes should be visible and recoverable.

4. Use Azure Document Intelligence for document parsing and an Azure-hosted LLM for extraction, risk assessment and summarization. Keep the processing inside Crestview's approved Azure environment, with explicit controls over what data reaches each service. I would not introduce LlamaParse as another SaaS provider by default.

5. Do not build five custom integration adapters. Reuse standard monday.com and Microsoft connectors where they meet the requirements. Build custom adapters only for the systems whose APIs or business operations genuinely require them—most likely ClientHub and ComplianceOne.

## Where each stakeholder is addressed
The assignment's audience is mixed, so the slides shouldn't all try to address everyone equally.
Stakeholder	Their central concern	Where we answer it
Claire — COO	Business impact and scaling across Crestview	Slides 1, 2, 6, 7
David — Operations	Reduce manual work without another failed RPA	Slides 2, 4, 5, 6
Priya — Compliance	Explainability, evidence and human decisions	Slides 4, 5, 6
Marcus — Technology	Security, integration feasibility and four-person team sustainability	Slides 3 and 5, supported by technical Q&A
