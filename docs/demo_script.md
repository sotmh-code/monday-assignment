# Live POC demo script (10-12 minutes)

**Before the interview (T-30 min), from a fresh terminal**

```bash
cd <repo>
source .venv/bin/activate
python -m pytest -q                       # expect: 86 passed
python -m src.main --replay | tail -12     # confirms recorded 15-record output is present
python -m src.main --ids APP-2026-0301 --show   # one live call to confirm key/network (~15 s)
```

Have these open in editor tabs: `crestview_client_applications.csv`, `src/schemas.py`, `src/pipeline.py` (function `process_application`), `src/risk_assessment.py` (system prompt), `output/enriched_applications.json`, `output/evaluation_report_sample.md`. Increase the terminal font size.

**Fallback rule:** if the network or API fails, say so and switch to `python -m src.main --replay --show ...`. The banner states that it shows recorded output from run `048b9e150ceb` and makes no API calls. Never present replay as live.

---

## 0:00-1:00 Input
- Open the CSV: 15 fictional applications, 8 columns, free-text descriptions.
- "The real input would be emails, PDFs and scans. Here the description stands in for the document package, so the system can only reason about what's written, and it says so."

## 1:00-3:00 Live run on three contrasting cases
```bash
python -m src.main --ids APP-2026-0301 APP-2026-0303 APP-2026-0310
```
- Point at the `LIVE run ... model=claude-sonnet-5-5` line and per-record progress (about 15-20 s, 3 in parallel).
- "Two real model calls per application. The full 15 ran earlier in ~83 s, about 3¢ per application."
- Note that subset runs write `*_subset` files, so the full results stay intact.

## 3:00-6:00 Inspect the risk triage
```bash
python -m src.main --replay --show APP-2026-0303 APP-2026-0310
```
(Or re-run live with `--show` if time allows.)
- **Apex 0303**: HIGH / ESCALATE. Each factor shows a quote and `[ok]`, meaning code found the quote verbatim in the application. "Priya can defend each line in an audit: here's the sentence it came from."
- Missing information distinguishes `REPORTED_MISSING_OR_PENDING` from `NOT_STATED_IN_APPLICATION`.
- **Heritage 0310**: LOW risk, HIGH complexity. "22 accounts and three advisors is operational work, not a red flag. Separating the two is what keeps compliance from being flooded with false positives."
- Advisory notice and `PENDING_HUMAN_REVIEW` on every record: no screening performed, no approvals.

## 6:00-8:00 Stage 2 consumes Stage 1
- Open `src/pipeline.py` → `process_application`: Stage 1 → guardrails → `summarize(app, risk, llm)`.
- Open `src/onboarding_summary.py`: the validated Stage 1 JSON goes into `<risk_triage>`, and the schema forces `risk_level_acknowledged`.
- Show `summary_consumed_risk_sha256` equal to `risk_assessment_sha256` in the JSON, and the test `test_stage2_receives_exact_validated_stage1_output`.
- In the 0303 summary: "Account opening and funding wait for a human compliance decision; the expedite request should be routed to Compliance." Mention that an earlier prompt version had the model reject the expedite request itself, which was overreach, and the prompt was fixed (AI log, story 3).

## 8:00-10:00 Structured output → monday.com
- Open `output/enriched_applications.csv` (or JSON): stable `application_id`, routing queue, complexity, next actions with owner and a "blocks account opening" flag.
- `python -m src.monday_sync --dry-run` → `output/monday_payloads.json`. Walk through the column mapping.
- Explain the idempotent upsert keyed on Application ID, and that the "Compliance Decision" column is set to *Pending Human Review* on create only and is never overwritten. (If a sandbox board is live, show it.)

## 10:00-12:00 Robustness, tests, limits
```bash
python -m pytest -q
cat output/evaluation_report_sample.md | head -30
```
- 86 tests: schema contracts, Stage 1→2 dependency, failure isolation, auth abort, 429/5xx retry via the real SDK with a mocked transport, invalid-JSON repair, refusal, prompt injection, prohibited claims, export round-trip, monday idempotency.
- Adversarial set: an injected "SYSTEM OVERRIDE" was ignored, recorded as `EMBEDDED_INSTRUCTION`, and routed to manual triage. The messy forwarded email was rated HIGH. The blank description was never sent to the model.
- Limitations: no documents, no real screening, priority varies by one level at the margins, a lexical claim scanner, and a small self-authored eval. Then the production path (README §6).

## Likely live requests and how to handle them
| Request | Command / answer |
|---|---|
| "Run all 15 now" | `python -m src.main --expect-count 15` (~85 s) |
| "Try a prompt injection" | Add a row to a copy of the CSV, or run `--input evals/adversarial_applications.csv --output-dir output/adversarial --show APP-2026-0901` |
| "What if the API is down?" | `CRESTVIEW_LLM_API_KEY=bad python -m src.main --ids APP-2026-0301`: shows an auth error, NEEDS_REVIEW, and the batch stops. Restore the key afterwards. |
| "Change the model" | `CRESTVIEW_LLM_MODEL=claude-opus-5-5 python -m src.main --ids APP-2026-0303 --show` |
| "Show the prompt" | `src/risk_assessment.py` → `RISK_SYSTEM_PROMPT` |
