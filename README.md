# Crestview Capital Group: AI-Assisted Client Intake POC

A working proof of concept for the monday.com FDE take-home. It reads the 15 sample client applications, runs a **two-stage AI pipeline** (evidence-based risk triage, then an onboarding summary that consumes that triage), applies **deterministic guardrails**, and exports structured JSON/CSV that a monday.com board can consume. An optional, isolated GraphQL adapter does an idempotent upsert of the records to a monday.com board.

> All Crestview data is fictional scenario data from the assignment. Risk labels are **advisory intake triage, not KYC/AML decisions**. No sanctions, watchlist, PEP or identity screening is performed by this system; every record stays `PENDING_HUMAN_REVIEW`.

| Deliverable | Location |
|---|---|
| Pipeline source | [src/](src/) |
| Tests (86, mocked; no network) | [tests/](tests/) |
| Live results (15 applications) | [output/enriched_applications.json](output/enriched_applications.json), [.csv](output/enriched_applications.csv) |
| Evaluation reports | [output/evaluation_report_sample.md](output/evaluation_report_sample.md), [output/adversarial/evaluation_report_adversarial.md](output/adversarial/evaluation_report_adversarial.md), [evals/stability/stability_table.md](evals/stability/stability_table.md) |
| monday.com dry-run payloads | [output/monday_payloads.json](output/monday_payloads.json) |
| Executive deck + outline + Q&A | [presentation/](presentation/) |
| monday.com-first demo script (10-12 min) | [docs/demo_script.md](docs/demo_script.md) |
| AI-assisted development log | [ai_development_log.md](ai_development_log.md) |

---

## 1. Setup

Requires Python 3.11+ (built and tested on 3.13.1, macOS).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set CRESTVIEW_LLM_API_KEY
```

Configuration ([.env.example](.env.example)). Process environment variables override `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `CRESTVIEW_LLM_PROVIDER` | `anthropic` | Only provider implemented |
| `CRESTVIEW_LLM_API_KEY` | (required for live runs) | Passed **explicitly** to the SDK; the POC never reads an ambient `ANTHROPIC_API_KEY` |
| `CRESTVIEW_LLM_MODEL` | `claude-sonnet-5-5` | Any Messages-API model that supports structured outputs |
| `CRESTVIEW_LLM_EFFORT` | `medium` | `low` / `medium` / `high` |
| `CRESTVIEW_LLM_TIMEOUT_SECONDS` | `120` | Per request |
| `CRESTVIEW_LLM_MAX_RETRIES` | `3` | SDK transport retries (429/5xx/timeouts, exponential backoff + jitter) |
| `CRESTVIEW_MAX_CONCURRENCY` | `3` | Applications in flight |
| `MONDAY_API_TOKEN`, `MONDAY_BOARD_ID`, `MONDAY_API_VERSION` | empty, empty, `2026-10` | Optional board sync |

`.env` is gitignored. No key appears in source, output files, logs or slides.

## 2. Commands

```bash
# Full live batch (all 15): writes output/enriched_applications.{json,csv}, appends output/run_log.jsonl
python -m src.main --expect-count 15

# Live demo subset with detailed review cards (writes *_subset files, never overwrites the full results)
python -m src.main --ids APP-2026-0301 APP-2026-0303 APP-2026-0310 --show

# Rerun only records that did not succeed (or whose prompt/model/source changed)
python -m src.main --skip-existing

# REPLAY recorded output. Clearly labelled, makes NO API calls (fallback if network/API is unavailable)
python -m src.main --replay --show APP-2026-0303

# Evaluate recorded output against expected qualitative indicators + global invariants
python -m src.evaluate
python -m src.main --input evals/adversarial_applications.csv --output-dir output/adversarial
python -m src.evaluate --input output/adversarial/enriched_applications.json --suite adversarial

# Tests (no network, no key needed)
python -m pytest -q

# monday.com (optional)
python -m src.monday_sync --dry-run       # builds payloads only
python -m src.monday_sync --setup-board   # creates a private sandbox board + typed columns
python -m src.monday_sync --check         # verifies column IDs/types before writing
python -m src.monday_sync                 # idempotent upsert keyed on Application ID
```

Exit codes: `0` all succeeded; `2` some records need attention (they are still written, with explicit errors); `1` configuration or input-file error.

## 3. Architecture

```text
crestview_client_applications.csv
  -> io_utils.load_applications      exact 8-column header, unique APP-YYYY-NNNN IDs, MM/DD/YYYY dates;
                                     row problems are kept and flagged (never dropped, never sent to the model)
  -> Stage 1  risk_assessment        system prompt = policy; application rendered inside <application> as untrusted data
                                     -> RiskAssessment (Pydantic, JSON-schema structured output, validated locally)
  -> guardrails                      evidence quotes must appear verbatim in the source; prohibited-claim scan;
                                     consistency checks; deterministic routing
  -> Stage 2  onboarding_summary     receives the application + the serialized, validated Stage 1 JSON
                                     -> OnboardingSummary (must echo Stage 1 risk level; hash lineage recorded)
  -> guardrails (summary scan)
  -> EnrichedRecord                  source fields + both stage outputs + routing + warnings/errors + audit metadata
  -> output/enriched_applications.json / .csv  (+ run_log.jsonl)
  -> OPTIONAL monday_sync            idempotent GraphQL upsert to a sandbox board
```

| Module | Role |
|---|---|
| [src/schemas.py](src/schemas.py) | Pydantic contracts for model outputs (sent as JSON schema) and for pipeline records |
| [src/llm_client.py](src/llm_client.py) | Anthropic adapter: structured output, error classification, one repair attempt, audit metadata |
| [src/prompting.py](src/prompting.py) | Renders records as delimited untrusted data; neutralises forged delimiter tags |
| [src/risk_assessment.py](src/risk_assessment.py) | Stage 1 prompt (policy) + call |
| [src/onboarding_summary.py](src/onboarding_summary.py) | Stage 2 prompt + call; serialises Stage 1 output it consumes |
| [src/guardrails.py](src/guardrails.py) | Evidence verification, prohibited-claim tripwire, consistency warnings |
| [src/pipeline.py](src/pipeline.py) | Orchestration, failure semantics, routing, concurrency, skip-on-success reuse |
| [src/main.py](src/main.py) | CLI: live / subset / replay / review cards |
| [src/evaluate.py](src/evaluate.py) | Expected-indicator checks and invariants -> Markdown report |
| [src/monday_client.py](src/monday_client.py), [src/monday_sync.py](src/monday_sync.py) | Optional monday.com GraphQL adapter + CLI |

### Key design decisions

- **Two causally linked stages.** Stage 2 gets the exact validated Stage 1 JSON, must restate its risk level (`risk_level_acknowledged`), and the record stores the SHA-256 of what Stage 2 consumed (`summary_consumed_risk_sha256`). A test proves Stage 2's prompt contains Stage 1's serialized output.
- **Compliance risk ≠ operational complexity.** Stage 1 rates financial-crime indicators only and lists complexity separately (`operational_complexity_notes`). Stage 2 rates `onboarding_complexity`. Heritage Family Office (22 accounts) comes out LOW risk / HIGH complexity.
- **Evidence or it didn't happen.** Every risk and mitigating factor carries a verbatim quote, and code checks each quote against the text the model was shown. In run 1 this caught a quote that had dropped the word "the" (see the AI log).
- **No silent LOW.** API failures, invalid JSON, refusals, truncation and invalid input all produce explicit statuses with `triage_risk_level = NEEDS_REVIEW` and `routing = MANUAL_TRIAGE`. A fatal error (bad key, unknown model) stops further calls instead of producing 15 identical failures.
- **Deterministic routing.** Code, not the model, maps level + priority to a queue (taking the more conservative of the two). Prohibited claims and embedded instructions always go to `MANUAL_TRIAGE`.
- **Untrusted input.** Descriptions sit inside `<application>` tags, forged closing tags are neutralised, and the system prompt tells the model to record injection attempts as `EMBEDDED_INSTRUCTION`. Guardrails back this up in case the model complied anyway (tested).
- **Structured outputs via `messages.create` + `output_config.format`,** validated locally with Pydantic instead of `messages.parse`, so a refusal or truncation is classified from `stop_reason` before parsing.
- **Retries.** Transport retries (429/5xx/timeouts/connection) are delegated to the SDK (bounded, exponential backoff with jitter, honours `retry-after`). The pipeline adds one *output* repair attempt when JSON fails validation.
- **Audit metadata per record:** model requested/responded, provider request IDs, attempts, tokens (incl. cache reads), latency, prompt and schema versions, timestamps. Descriptions are not logged to the console.
- **Single provider, minimal dependencies** (`anthropic`, `pydantic`, `python-dotenv`; `pytest` and `python-pptx` for tests/deck). No agent framework. That keeps it maintainable by a four-person IT team.
- **Server-side refusal fallbacks deliberately not enabled.** For an auditable compliance workflow the model of record should be fixed, so a refusal is reported and routed to a human instead of silently re-running on another model.

## 4. Results (actual runs, 2026-11-03)

| Run | What | Outcome |
|---|---|---|
| `bfa189f127ce` | Smoke test, APP-2026-0303 only | Completed; 7/7 evidence quotes verified |
| `bccd1c84e310` | Full 15, prompts `risk-triage-v3` / `onboarding-summary-v2` | 15/15 processed (13 completed, 2 with warnings); eval **28/30** ([archived](evals/history/run1_bccd1c84e310_evaluation.md)) |
| `048b9e150ceb` | Full 15, prompts `risk-triage-v4` / `onboarding-summary-v3` (current output) | **15/15 COMPLETED**, 0 warnings, 61/61 evidence quotes verified, eval **30/30** |
| `5ddd1e5ce11a` | Adversarial set (injection, sparse, blank, messy email, large clean) | eval **14/14** (after two guardrail fixes; earlier runs archived in [evals/history/](evals/history/)) |
| `e195dff5d8b9`, `69a13ff52e54` | Stability repeats of 5 borderline cases | Risk level identical across 3 runs; priority/complexity varied by one adjacent level on some cases |

Current classification (run `048b9e150ceb`): 9 LOW, 3 MEDIUM, 3 HIGH. Apex (0303), Eastbridge (0311) and R. Ashford (0315) are HIGH / ESCALATE. Velocity (0307), Brightpath (0306) and Mercer-Hastings (0313) are MEDIUM. Heritage (0310) and Northern Lights (0309) are LOW risk / HIGH complexity.

Approximate cost at list price for the 15-application batch: ~25.6K input + ~33.6K output tokens (output includes the model's thinking) ≈ **$0.40, about 3¢ per application**. Mean latency is ~16 s per application for both stages, and ~83 s for the batch at concurrency 3.

## 5. Limitations and failure modes (say these out loud)

- **The input is a one-paragraph description, not documents.** The model cannot verify anything, and "documentation provided" is only the application's claim. Real intake would extract from PDFs and scans, with per-field confidence.
- **No screening.** Sanctions/PEP/adverse-media checks belong to ComplianceOne; this POC only recommends running them.
- **Label variance at the margins.** Review priority and complexity sometimes move one level between runs ([stability table](evals/stability/stability_table.md)). For production, derive priority from Compliance-owned rules over the factor categories, or use multi-sample agreement.
- **Policy is encoded in a prompt.** The v3→v4 calibration moved Northern Lights (0309) from MEDIUM to LOW, which shows that whether state-owned funds trigger enhanced due diligence must be **Crestview policy owned by Compliance**, not something the model or the FDE decides.
- **The prohibited-claim scanner is a lexical tripwire.** It produced false positives on conditional and reported speech during development (fixed, with regression tests). It fails safe by routing to manual triage, but it is not a complete semantic check.
- **Evaluation is small and self-authored** (15 sample + 5 adversarial cases, qualitative expectations). Production needs a labelled set reviewed by Priya's team, with precision/recall per risk category and an override log.

## 6. Production hardening path

1. Data residency and provider approval (e.g. a cloud-hosted model endpoint inside Crestview's tenancy, zero/limited retention agreements), PII minimisation before the call, DLP review.
2. Document ingestion from SharePoint (OCR + extraction with per-field confidence and source page references) instead of free text.
3. Policy as configuration: risk taxonomy, EDD triggers and routing rules owned and versioned by Compliance; the model fills evidence, code applies policy.
4. ComplianceOne integration for authoritative screening; ClientHub adapter with a reconciliation job and idempotent writes (its API is poorly documented, so contract tests and defensive sync come first).
5. Observability: per-stage latency/error dashboards, override rate, evidence-verification failure rate, cost per case; alerting on drift.
6. Regression eval gate in CI on a labelled, growing case set before any prompt/model change ships. Prompt and schema versions are already recorded per record.
7. Human-in-the-loop UI on monday.com: reviewer accepts or overrides triage with a reason, captured as audit history.

## 7. monday.com integration status

The adapter ([src/monday_client.py](src/monday_client.py)) follows the current API docs (`https://api.monday.com/v2`, `API-Version: 2026-10`, raw token in `Authorization`). It uses `items_page_by_column_values` on the Application ID column for idempotent upsert, writes status values by label with `create_labels_if_missing`, writes `long_text` as `{"text": ...}` capped at 2,000 characters, and honours `retry_in_seconds` on rate limits. The "Compliance Decision" column is written only at item creation and never on update, so a human decision on the board survives reruns. The integration is unit-tested against a fake GraphQL board. **Live sandbox sync was completed after the initial development log:** [output/monday_sync_report.json](output/monday_sync_report.json) records 15 successful `created` items (zero reported errors) on [board 5032266463](https://andrelimyoukwans-team.monday.com/boards/5032266463) from run `048b9e150ceb`. This is saved point-in-time evidence; check the board's current state before presenting. The **primary customer-facing demo is the monday.com board**; follow [docs/demo_script.md](docs/demo_script.md). For internet outages, run `python -m src.report --input output/enriched_applications.json` and open `output/crestview_review_dashboard.html` (a read-only view of recorded results). The command also exports separate Stage 1 and Stage 2 JSON views.
