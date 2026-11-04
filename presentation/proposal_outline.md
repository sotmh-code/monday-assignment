# Crestview Client Onboarding Transformation: Proposal Outline and Talk Track

**Audience:** Claire Nakamura (COO) and Crestview leadership (David Holloway, Priya Sharma, Marcus Leung).
**Length:** 8 slides, ~17 minutes, plus 1 appendix slide used as the bridge into the live POC demo.
**Sources:** All Crestview figures come from the assignment's scenario materials (account brief, 14 Jan 2026 discovery transcript, Q4 2025 operations dashboard). Targets are Crestview's stated goals, not outcomes this proposal guarantees. Product feedback items are requests to validate, not claims about current monday.com capabilities.

Deck file: [crestview_transformation_proposal.pptx](crestview_transformation_proposal.pptx) (built by `python presentation/build_deck.py`; speaker notes embedded).

---

## Slide 1: The decision (1.5 min)

**Headline:** Onboard clients in days, not weeks, with every compliance decision still made by a person.

- One shared onboarding workflow on monday.com, connecting the five systems that exist today.
- AI does the reading, checking and status-chasing. Compliance keeps the authority.
- **Decision requested today:** approve a gated six-month pilot, with three named owners and a go/no-go gate at the end of Month 1.

**Talk track:** "Last quarter a $200 million mandate went to a competitor who onboarded in five days while we took four weeks. I'm not here to sell AI. I'm asking for a pilot that puts one accountable workflow in front of onboarding, uses AI for the clerical work, and keeps Priya's team in charge of every compliance call. Each phase has a gate. If a gate isn't met, we stop or adjust, not hope."

## Slide 2: Why now: the cost of a slow, invisible process (2.5 min)

**Headline:** Onboarding takes 23 business days because work waits between five disconnected systems.

KPI row (Q4 2025 baseline → Crestview target):

| Metric | Baseline | Industry benchmark | Target |
|---|---:|---:|---:|
| Avg. onboarding time | 23 business days | 8 | 5 |
| Compliance review backlog | 85 pending | - | < 10 |
| Onboarding NPS | 24 | 52 | 55+ |
| Abandonment | 18% | 5% | < 5% |
| Annual revenue at risk | ~$12M | - | < $2M |

Root causes from discovery:
- Every handoff is manual: email → SharePoint → ClientHub → compliance request → Word findings → email → ClientHub again.
- ~60% of onboarding work is data handling (Claire). ~70% of the operations team's day is data handling (David).
- Compliance is a black box: complex reviews take a full day, and nobody can see where a client is.
- People cost: two senior RMs left last quarter, citing administrative burden.

**Talk track:** "The time isn't lost in typing. It's lost in waiting: queues nobody can see and handoffs nobody owns. That's why the fix is a workflow backbone first and AI second. Revenue at risk is $12M a year. That's exposure, not a promise of recovered revenue."

## Slide 3: The future-state journey (2 min)

**Headline:** One tracked path from signed mandate to funded account, with exceptions routed, not lost.

Happy path (each step is a monday.com status with an owner and an SLA):
1. RM submits the package (from Salesforce or forwarded email).
2. AI intake: extract key fields, check the package against the client-type checklist, flag gaps (minutes, not hours).
3. Operations review on the onboarding board. Prep work runs **in parallel** with compliance.
4. ComplianceOne screening plus an AI-prepared evidence pack. **The compliance analyst decides.**
5. ClientHub account set up through an integration adapter.
6. Automatic status updates to the RM and client via Outlook and Teams.
7. Activation and funding.

Exception paths: missing documents → drafted client request for RM approval. Elevated risk → enhanced due diligence queue. Integration failure → manual queue plus alert, never silent.

**Talk track:** "Two changes do most of the work: parallelising operations prep with compliance review, and removing re-keying. The RPA bot failed because it followed layouts. This design reads meaning, says how confident it is, and hands anything uncertain to a person."

## Slide 4: Architecture: monday.com as the system of work (2.5 min)

**Headline:** monday.com coordinates the work. Existing systems stay the systems of record.

- **monday.com (system of work):** Onboarding Pipeline board, Compliance Review queue, Document Requests board, automations, dashboards for Claire and David.
- **Systems of record stay where they are:** Salesforce (CRM, pipeline trigger), ClientHub (client master), SharePoint (documents; monday.com stores links, not copies), Outlook (communications), ComplianceOne (authoritative KYC/sanctions screening).
- **Integration layer:** a small set of idempotent adapters with retries, a dead-letter queue and reconciliation reports, built on Crestview's standard Microsoft stack.
- **AI service:** a provider endpoint approved by Marcus. Only the minimum necessary fields are sent; documents stay in SharePoint.
- **ClientHub is the main technical risk:** a 12-year-old custom system with a thin API. Weeks 1-2 include an API assessment; writes go through one adapter with read-back verification.

**Talk track:** "We're not moving documents into monday.com, and we're not replacing ComplianceOne with an LLM. monday.com becomes the place where work is assigned, tracked and escalated. Marcus, what leaves the network is the extracted fields the model needs, through an endpoint your team approves."

## Slide 5: AI capabilities and controls, plus your Microsoft investment (3 min)

**Headline:** Four narrow AI jobs, each with a control Priya can audit.

| Capability | What it does | Control |
|---|---|---|
| Document understanding | Extracts fields from IPS, board resolutions and signatory lists, with page references and confidence | Low confidence → human; never auto-written to ClientHub without review in the pilot |
| Gap detection | Compares the package to a checklist per client type (policy as configuration) | Checklist owned by Compliance and Ops |
| Evidence-led risk triage | Advisory LOW/MEDIUM/HIGH with every factor quoted from the source | Analyst decides; **no autonomous clearance**; screening stays in ComplianceOne |
| Status synthesis | Daily pipeline summaries; drafted client updates | RM approves outbound messages |

Controls across all four: strict output schemas, code-verified evidence quotes, prompt-injection handling, versioned prompts, a full audit trail (model, prompt version, request ID, reviewer), and an evaluation gate before any change ships.

**Microsoft 365 / Copilot:** reuse Copilot for drafting and summarisation where it already works. Evaluate monday.com MCP so Copilot can answer "where is my client?" from board data, starting **read-only**, scoped by Entra ID, in Month 3, and only if security approves.

**Talk track:** "Claire asked what's realistic and what's hype about agents. The realistic part is narrow, checkable tasks inside a workflow humans control. The hype is an autonomous agent approving clients. We won't build that. The POC I'll show in a moment does the risk triage piece today."

## Slide 6: Six-month roadmap with release gates (2.5 min)

**Headline:** Each phase earns the next. Gates are business and compliance acceptance, not demo quality.

| When | Phase | Gate to proceed |
|---|---|---|
| Weeks 1-2 (from 3 Feb) | Deep discovery: shadow ~10 live onboardings, time-and-motion baseline, data map, ClientHub API assessment | Baseline agreed with David |
| Rest of Month 1 | Design & approvals: board design, security/data review, provider approval, control design with Priya | **Gate 1:** security + compliance sign-off |
| Month 2 | MVP: onboarding board live for Ops; AI intake runs in **shadow mode** (compared with humans, not used) | **Gate 2:** shadow accuracy thresholds met |
| Month 3 | Integrations + UAT: Salesforce trigger, ComplianceOne API, ClientHub adapter; Copilot/MCP read-only trial | **Gate 3:** UAT sign-off, runbooks |
| Month 4 | Controlled production pilot: one client segment, AI-assisted with human review | **Gate 4:** pilot metrics vs baseline |
| Month 5 | Scale: more client types, RMs and Compliance on the boards | Seat expansion decision |
| Month 6 | Optimise + handover: runbooks, training, ownership with Marcus's four-person team; playbook for portfolio operations | Handover accepted |

**Talk track:** "Shadow mode in Month 2 is the answer to David's RPA experience: the AI runs alongside his team on real packages and we measure where it's wrong before anyone depends on it."

## Slide 7: How we'll measure success, and what could go wrong (2 min)

**Headline:** Leading indicators tell us early. The lagging targets are the board's scorecard.

- **Claire:** onboarding cycle time 23 → 5 business days; a scalable story for the board.
- **David:** manual touch time per onboarding; rework rate; team time on data handling (70% → 30%).
- **Priya:** 100% human sign-off on compliance decisions; evidence completeness; audit findings down; override rate tracked.
- **Marcus:** standard tooling, documented adapters, incidents and integration failure rate, supportable by four people.
- **Leading indicators:** extraction accuracy on critical fields, AI triage override rate, backlog age, integration error rate, cost per onboarding.
- **Lagging:** cycle time, backlog < 10, NPS 55+, abandonment < 5%, revenue at risk < $2M. *These depend on more than this system* (compliance staffing, client responsiveness), so we'll report contribution honestly.

| Risk | Mitigation |
|---|---|
| Repeat of the brittle RPA | Meaning-based extraction with confidence; shadow mode; human fallback; rework measured |
| Regulatory defensibility | Advisory AI only; quoted evidence; audit trail; Compliance owns the policy |
| Data security | Approved endpoint; minimal fields; no training on Crestview data; DLP review |
| ClientHub API fragility | Early assessment; single adapter; reconciliation; manual fallback |
| Adoption | Co-designed with Ops; RMs get status visibility first |
| Model change or drift | Pinned model; versioned prompts; regression evaluation before release |

## Slide 8: Scaling, and what we'll bring back to monday.com (1.5 min)

**Headline:** Onboarding becomes the playbook: intake → triage → route → human decision → sync.

- Expansion path: Client Operations → Compliance → Relationship Management (600+ seats, contingent on pilot results) → portfolio operations (account changes, transitions, corporate actions).
- Reusable assets: board templates, adapters, the evaluation harness, a control pattern Compliance has already approved.
- **Product feedback to validate with monday.com's product team** (from pilot friction, not assumed gaps):
  1. A regulated-grade approval step: who approved, when, on what evidence, immutable.
  2. AI fields that carry citations, confidence and a required reviewer.
  3. Connector templates for financial-services systems, with retries and dead-lettering.
  4. MCP governance: per-tool scopes, read-only modes, audit of AI-initiated actions.
  5. Residency and PII-redaction controls for AI features.

**Close:** "Approve the pilot, name the owners, and we'll be back at Gate 1 with a measured baseline and a signed-off design."

## Appendix A: POC evidence (bridge into the demo)

Live results on the 15 sample applications (run `048b9e150ceb`, `claude-sonnet-5-5`): 15/15 processed; 61/61 evidence quotes verified against source; 30/30 evaluation checks; prompt injection ignored and routed to a human; ~3¢ and ~16 s per application; 86 automated tests.

---

# Panel Q&A preparation (~20 min)

**"How is this different from the RPA that failed?"**
RPA matched layouts; this reads meaning and reports confidence. More importantly, the *process* is different: shadow mode before anyone relies on it, human fallback built in, and we measure rework. If rework goes up, Gate 2 fails. In the POC, a messy forwarded email (blurry passport, address mismatch, "pls rush") was triaged correctly. Real PDFs and scans are the next test, not something I'll claim today.

**"Can AI make compliance decisions?"**
No. It prepares evidence and an advisory triage, and every record stays "Pending Human Review". The pipeline has no code path that writes an approval, and on the board the Compliance Decision column can only be set by a person (reruns never overwrite it). Screening stays in ComplianceOne.

**"How do I defend an AI risk rating in an audit?" (Priya)**
Each factor quotes the application text, and code checks the quote exists verbatim. During development that check caught the model dropping a single word from a quote. Each record stores model, prompt version, request ID and timestamp. The policy (what triggers enhanced due diligence) should be written down by Compliance; in testing, a prompt change shifted how a sovereign wealth fund was rated, which is exactly why policy can't live in the FDE's head.

**"What data leaves our network?" (Marcus)**
In the pilot: the extracted fields and text needed for the task, sent to an endpoint you approve (options include an Azure-hosted model under Crestview's tenancy). Documents stay in SharePoint. No training on Crestview data, retention per contract, DLP review in Month 1. The POC sends only the fictional sample text.

**"What happens when an API fails?"**
Nothing silently defaults. In the POC: SDK retries with backoff for rate limits and outages, one repair attempt for malformed output, explicit NEEDS_REVIEW and manual triage on failure, and a bad credential stops the batch after one request. Integrations get idempotent adapters, dead-letter queues and reconciliation reports.

**"What does it cost?"**
POC model cost was ~3¢ per application at list price (two calls). Model cost is negligible next to analyst time. The real costs are integration build, seats and change management. ROI is a hypothesis to measure in Month 4, not a promise.

**"Can my four-person team run this?" (Marcus)**
That's the design constraint: plain Python or your standard Microsoft integration stack, no agent framework, three runtime dependencies in the POC, documented adapters, runbooks, and an evaluation suite your team runs before any change. Month 6 is a formal handover with acceptance criteria.

**"Why monday.com and not just Copilot or Salesforce?"**
Copilot is good at drafting and summarising for individuals. It doesn't give David a shared, owned, measurable workflow across five systems. Salesforce stays the CRM. monday.com is where cross-team work is assigned, tracked and escalated, and Copilot can read it via MCP.

**"Are AI agents realistic?" (Claire)**
For narrow, checkable steps inside a human-controlled workflow, yes. For autonomous multi-step onboarding with compliance judgement, not in a regulated setting this year. Earn autonomy step by step, measured by override rates.

**"Isn't this over-engineered for a POC?"**
The POC is one pipeline file, two prompts, deterministic checks and tests, with no distributed agents or vector database. Everything in it maps to a stakeholder requirement: evidence for Priya, failure handling for David, maintainability for Marcus.

**"What would you do differently with more time?"**
Real document ingestion with page-level citations; priority derived from Compliance rules rather than the model; a labelled evaluation set from Priya's team; a live monday.com board with reviewer override capture; multi-sample agreement for borderline cases.

**"Will this hit five days?"**
It's Crestview's target, not something I can guarantee. The design removes the waiting and re-keying we can see. Compliance capacity and client responsiveness also matter. The Month 1 baseline tells us how much of the 23 days is addressable.
