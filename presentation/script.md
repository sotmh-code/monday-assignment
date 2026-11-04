# Crestview Capital Group — Transformation Proposal Speaker Script

**Format:** 8 executive slides (~17–18 minutes) + 1 appendix slide transitioning into the live POC (~10–12 minutes).  
**Audience:** Claire Nakamura (COO), David Holloway (Client Operations), Priya Sharma (Compliance), Marcus Leung (Technology).  
**Presentation principle:** Lead with the AI-enabled future, establish why the current process fails, show a safer operating model, then request approval. The targets below are *Crestview's objectives*, not results we guarantee.

## Slide 1 — AI changes the work. monday.com makes it accountable. (~1.5 min)

> Our proposal is to change how onboarding work gets done—not deploy another chatbot or automate a few isolated forms. AI will read incoming applications, extract relevant facts, identify missing information and prepare an evidence-based triage. monday.com will make each handoff visible, assign an owner, and track progress. Compliance will retain authority over every regulatory decision.
>
> Our ambition is to help Crestview move from **23 business days to a five-business-day target**. That's the destination we'll measure against, not a promise made before discovery. The approach is simple: **read, triage, route, review and activate**, with humans accountable throughout.

**Transition:** To understand why that matters, look at where the time is lost today.

## Slide 2 — The real bottleneck is the handoff—not the form. (~2.5 min)

> Crestview's onboarding work crosses **Salesforce, SharePoint, ClientHub, ComplianceOne and Outlook**, but the handoffs are largely manual. Relationship managers email documents; operations uploads and re-enters information; compliance performs checks; findings travel back through email; and operations updates the client record again. There is no shared, real-time picture of the case.
>
> The result is **23 business days** of average onboarding time, **85 pending compliance reviews**, **18% abandonment**, and approximately **12 million of annual revenue at risk**. The 12 million is exposure, not guaranteed revenue recovery. One prospective **200 million allocation** was lost to a faster competitor, and two senior relationship managers left citing administrative burden.
>
> Claire estimated that **60% of onboarding activity** is data handling; David said **70% of his team's day** is spent on it. Those are separate observations, not one combined statistic.
>
> The previous RPA effort failed because **form layouts changed and it could not cope with exceptions**, creating more corrective work. The lesson isn't that automation is impossible. It's that we must design for messy inputs, uncertainty and recovery—not only a clean demonstration.

**Transition:** Here's how we redesign the journey around that lesson.

## Slide 3 — AI works inside the flow—not beside it. (~2 min)

> A relationship manager submits the onboarding package once. AI extracts structured fields and checks the document package for gaps. It then produces an **advisory risk triage** that explains which facts need attention.
>
> Operations can begin permitted preparation while compliance review is underway, reducing avoidable waiting. **ComplianceOne remains the screening system**, and a **human compliance analyst makes the decision**. Once approvals are in place, an integration updates ClientHub and the relationship manager receives an accurate status update.
>
> Crucially, the exception paths are as visible as the happy path. Missing documents trigger an RM follow-up; elevated concerns move into an enhanced-due-diligence queue; integration failures create an alert and manual fallback. Nothing should disappear silently into an automation.

**Transition:** That operating model only works if each system has a clear responsibility.

## Slide 4 — One system of work. Five systems of record. (~2.5 min)

> **monday.com is the system of work**: it tracks onboarding cases, assignments, deadlines, exceptions, review queues and operational dashboards. We do not propose replacing Crestview's existing investments.
>
> **Salesforce** remains the CRM and an intake trigger. **ClientHub** remains the authoritative client master. **SharePoint** stores the source documents; monday.com holds references, not unnecessary copies. **Outlook** handles communications. **ComplianceOne** remains responsible for KYC and sanctions screening.
>
> Between these systems, I would build a small number of governed integration adapters, with **idempotent writes, retry handling, reconciliation, and clear error ownership**. The highest integration risk is ClientHub's poorly maintained API, which we assess in the first two weeks before relying on it for critical writes.
>
> Any AI endpoint must be approved by Marcus's team, and we should minimize the information sent outside Crestview's approved boundaries.

**Transition:** With those boundaries established, we can specify exactly what AI is—and is not—allowed to do.

## Slide 5 — Four useful AI tasks. Four explicit guardrails. (~3 min)

> I would start with **four narrow AI capabilities**, not a fully autonomous onboarding agent.
>
> **First, document extraction:** identify fields in onboarding packages and link them to source evidence. Low-confidence or disputed fields go to human validation.
>
> **Second, gap detection:** compare the submitted package against a checklist for that client type. Operations and Compliance own the checklist and can update it without rewriting model prompts.
>
> **Third, advisory risk triage:** surface patterns such as opaque beneficial ownership, insufficient source-of-funds information, or politically exposed person indicators, with source-backed explanations. This is **not a sanctions check or a compliance approval**. ComplianceOne screens, and Priya's analysts decide.
>
> **Fourth, status synthesis and outreach:** create concise case summaries and draft follow-ups, which relationship managers approve before sending.
>
> Across all four, we require structured outputs, evidence verification, prompt and model versioning, reviewer audit trails, and regression tests. We would also **reuse Microsoft 365 and SharePoint**, and evaluate a **read-only Copilot–monday.com MCP connection**, subject to security and permission validation—not assume that integration is production-ready today.

**Transition:** A safe technical design still needs a disciplined path to production.

## Slide 6 — Earn the right to automate—with four release gates. (~2.5 min)

> The roadmap runs **left to right from Month 1 to Month 6**. The first month is discovery: shadow roughly ten real onboardings, map handoffs and data, assess ClientHub's API, and obtain security and compliance approval. **Gate 1** is agreement on scope and controls.
>
> **Month 2:** launch the operational board and run AI in **shadow mode**, comparing its outputs against human processing without letting the model make live decisions. **Gate 2** is a measured quality threshold, including difficult cases.
>
> **Month 3:** implement and test the prioritized integrations with Salesforce, ClientHub and ComplianceOne. **Gate 3** is integration UAT and operational readiness.
>
> **Month 4:** deploy a controlled production pilot for one client segment with human compliance sign-off. **Gate 4** is demonstrated operational value and acceptable risk.
>
> **Month 5:** expand by client type and train teams only where evidence justifies it. **Month 6:** optimize, complete runbooks, and formally transfer support to Marcus's four-person technology team.
>
> **The governing rule:** we don't move into a riskier phase simply because a demo looked good.

**Transition:** Each gate needs both technical measures and business measures.

## Slide 7 — Measure the transformation—not the demo. (~2 min)

> We will track **leading indicators** early: critical-field extraction accuracy, human override rate, manual touch time, rework, integration failures and recovery, backlog age, and cost per onboarding. These are the signals that tell us if the solution is actually helping—or creating hidden work.
>
> Crestview's **lagging business targets** are: onboarding time **23 to 5 business days**, compliance backlog **85 to under 10**, NPS **24 to 55+**, abandonment **18% to under 5%**, and annual revenue at risk **about 12 million to under 2 million**.
>
> I would report these by client segment, not hide complex cases inside an average. And I would not attribute all improvement to software: staffing, client responsiveness, and regulatory review capacity also affect outcomes.
>
> For Priya, **100% human sign-off on compliance decisions** is a non-negotiable control, not an optimization metric.

**Transition:** If the pilot works, its real value is a repeatable pattern beyond onboarding.

## Slide 8 — Prove one workflow. Build the next operating standard. (~1.5 min)

> The repeatable pattern is **intake → triage → route → human decision → sync**. Once validated, we can reuse board templates, governed checklists, integration adapters, evaluation tests, and audit patterns across Client Operations, Compliance and Relationship Management—subject to pilot results, with **600+ potential additional seats**. Portfolio operations can follow later.
>
> I'd also bring observed product friction back to monday.com's teams: evidence-linked AI fields, regulated approval/audit patterns, resilient connector templates, granular MCP permissions, and data-residency controls. These are **areas to validate**, not claims that features are missing today.
>
> **My request:** approve a **gated six-month pilot**, with named owners from Operations, Compliance and Technology. At the end of Month 1, we'll return with the measured baseline, the approved design and a go/no-go recommendation.

**Transition to demo:** Let me show how the first narrow capability—evidence-based intake triage—works on sample applications today.

## Slide 9 — Appendix / live POC handoff (~10–12 min demo)

> The prototype processes **15 fictional client applications**. It takes raw CSV data, calls an AI model for **advisory risk assessment** with specific source evidence, validates those evidence references in code, and passes the result into a second model stage that produces an actionable onboarding summary. Structured JSON/CSV is ready for a downstream system or a monday.com board.
>
> I'll contrast a straightforward institutional case, an elevated-risk case and an operationally complex case to show that **compliance risk is not the same as onboarding complexity**. No code path should autonomously approve KYC/AML clearance.

**Verification before presenting:** Claude's development outline *reports* **15/15 processed, 61/61 evidence quotations checked, 30/30 evaluation checks, 86 tests, approximately $0.03 and 16 seconds per application**. These are **unverified here**. Check actual run logs before quoting them; otherwise omit the figures and demonstrate the tests live. Be ready to explain prompt revisions, failure handling, API retries, and what would require further testing with real, messy documents.

---

## Short presenter reminders

- **Opening:** AI-first transformation; do *not* ask for approval on Slide 1.
- **RPA wording:** The brief says **form layouts changed and exceptions broke the implementation**. It does not establish screen-scraping as the mechanism.
- **Control boundary:** AI advises; ComplianceOne performs screening; a human approves regulated decisions.
- **Systems boundary:** monday.com orchestrates; existing platforms remain systems of record.
- **Timeline:** Speak strictly Month 1 → Month 6, with four explicit gates.
- **Closing:** Formal approval request belongs on Slide 8, immediately before the live POC.
- **Claims:** All target KPIs are ambitions. POC test/performance numbers require log verification.
