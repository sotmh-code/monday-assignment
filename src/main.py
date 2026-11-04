"""CLI entry point.

    python -m src.main                                   # full live run (all applications)
    python -m src.main --ids APP-2026-0301 APP-2026-0303 --show   # live subset, detailed review cards
    python -m src.main --limit 3
    python -m src.main --skip-existing                   # rerun only records that did not succeed
    python -m src.main --replay --show APP-2026-0303     # recorded output, NO API calls
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import textwrap
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .config import ConfigError, load_llm_settings
from .io_utils import InputValidationError, file_sha256, format_aum, load_applications, read_run_output, write_outputs
from .llm_client import AnthropicStructuredLLM
from .pipeline import PROMPT_VERSIONS, run_batch
from .schemas import EnrichedRecord, ProcessingStatus, RunMetadata, RunOutput

SUCCESS = {ProcessingStatus.COMPLETED, ProcessingStatus.COMPLETED_WITH_WARNINGS}
FULL_STEM = "enriched_applications"
SUBSET_STEM = "enriched_applications_subset"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m src.main", description="Crestview AI-assisted client intake POC")
    p.add_argument("--input", default="crestview_client_applications.csv", help="Intake CSV path")
    p.add_argument("--output-dir", default="output", help="Directory for JSON/CSV outputs")
    p.add_argument("--limit", type=int, help="Process only the first N applications (writes *_subset files)")
    p.add_argument("--ids", nargs="+", metavar="APP_ID", help="Process only these application IDs (writes *_subset files)")
    p.add_argument("--expect-count", type=int, help="Fail if the input does not contain exactly N rows")
    p.add_argument("--skip-existing", action="store_true", help="Reuse successful records from the previous full run")
    p.add_argument("--concurrency", type=int, help="Applications processed in parallel (default from env, 3)")
    p.add_argument(
        "--replay",
        action="store_true",
        help="Show previously recorded output from output/enriched_applications.json. Makes NO API calls.",
    )
    p.add_argument("--show", nargs="*", metavar="APP_ID", help="Print detailed review cards (all records if no IDs)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Console rendering
# ---------------------------------------------------------------------------


def _short(rec: EnrichedRecord) -> str:
    complexity = rec.onboarding_summary.onboarding_complexity.value if rec.onboarding_summary else "-"
    priority = rec.review_priority.value if rec.review_priority else "-"
    return (
        f"risk={rec.triage_risk_level.value:<12} priority={priority:<15} complexity={complexity:<6} "
        f"route={rec.routing.value:<24} {rec.processing_status.value}"
    )


def print_table(records: list[EnrichedRecord]) -> None:
    header = f"{'APPLICATION':<14} {'CLIENT':<38} {'RISK':<12} {'PRIORITY':<15} {'CPLX':<6} {'ROUTING':<24} STATUS"
    print(header)
    print("-" * len(header))
    for r in records:
        complexity = r.onboarding_summary.onboarding_complexity.value if r.onboarding_summary else "-"
        priority = r.review_priority.value if r.review_priority else "-"
        print(
            f"{r.application_id:<14} {r.source.client_name[:38]:<38} {r.triage_risk_level.value:<12} "
            f"{priority:<15} {complexity:<6} {r.routing.value:<24} {r.processing_status.value}"
        )


def _wrap(text: str, indent: str = "    ") -> str:
    return textwrap.fill(text, width=110, initial_indent=indent, subsequent_indent=indent)


def print_card(rec: EnrichedRecord) -> None:
    src = rec.source
    print("=" * 110)
    try:
        aum = format_aum(int(src.estimated_aum))
    except ValueError:
        aum = src.estimated_aum
    print(f"{rec.application_id}  {src.client_name}  |  {src.client_type}  |  {aum}  |  {src.requested_services}")
    print(f"  Processing: {rec.processing_status.value}   Human review: {rec.human_review_status}   Routing: {rec.routing.value}")
    risk = rec.risk_assessment
    if risk is None:
        print("  RISK TRIAGE: unavailable -> NEEDS_REVIEW (manual triage). Errors:")
        for e in rec.errors:
            print(_wrap(f"- [{e.stage}/{e.kind}] {e.message}"))
        return
    print(f"  RISK TRIAGE (advisory): {risk.risk_level.value}   review priority: {risk.review_priority.value}")
    print(_wrap(f"Rationale: {risk.rationale}"))
    checks = {(c.kind, c.index): c.verified_in_source for c in rec.guardrails.evidence_checks}
    if risk.risk_factors:
        print("  Risk factors (evidence quoted from application; [ok] = found verbatim in source):")
        for i, f in enumerate(risk.risk_factors):
            mark = "ok" if checks.get(("risk_factor", i), False) else "UNVERIFIED"
            print(_wrap(f"- [{f.severity.value}] {f.factor} ({f.category.value})"))
            print(_wrap(f'evidence [{mark}]: "{f.source_evidence}"', indent="        "))
    else:
        print("  Risk factors: none identified in the application text")
    if risk.mitigating_factors:
        print("  Mitigating factors:")
        for f in risk.mitigating_factors:
            print(_wrap(f'- {f.factor}: "{f.source_evidence}"'))
    if risk.operational_complexity_notes:
        print("  Operational complexity (not treated as compliance risk):")
        for n in risk.operational_complexity_notes:
            print(_wrap(f"- {n}"))
    if risk.missing_information:
        print("  Missing information:")
        for m in risk.missing_information:
            print(_wrap(f"- {m.item} [{m.status.value}]"))
    summ = rec.onboarding_summary
    if summ:
        print(f"  ONBOARDING SUMMARY  (complexity: {summ.onboarding_complexity.value}; consumed triage sha256 "
              f"{(rec.summary_consumed_risk_sha256 or '')[:12]}...)")
        print(_wrap(summ.summary_text))
        print("  Next actions:")
        for a in summ.next_actions:
            block = " [BLOCKS ACCOUNT OPENING]" if a.blocks_account_opening else ""
            print(_wrap(f"- {a.suggested_owner.value}: {a.action}{block}"))
    if rec.warnings:
        print("  Warnings:")
        for w in rec.warnings:
            print(_wrap(f"! {w}"))
    for e in rec.errors:
        print(_wrap(f"x [{e.stage}/{e.kind}] {e.message}"))


def print_summary(run: RunMetadata, records: list[EnrichedRecord]) -> None:
    print()
    print_table(records)
    print()
    print(f"Run {run.run_id}  mode={run.mode}  model={run.model_requested}  records={run.record_count}")
    print(f"  status: {dict(run.status_counts)}")
    print(f"  risk:   {dict(run.risk_level_counts)}")
    if run.mode == "live":
        print(f"  tokens: input={run.total_input_tokens} output={run.total_output_tokens}")
    print("  All records remain PENDING_HUMAN_REVIEW. AI triage is advisory; no screening was performed.")


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def _select_cards(records: list[EnrichedRecord], show: list[str] | None) -> list[EnrichedRecord]:
    if show is None:
        return []
    if not show:
        return records
    wanted = set(show)
    return [r for r in records if r.application_id in wanted]


def replay(args: argparse.Namespace) -> int:
    path = Path(args.output_dir) / f"{FULL_STEM}.json"
    if not path.exists():
        print(f"No recorded output at {path}. Run a live batch first.", file=sys.stderr)
        return 1
    recorded = read_run_output(path)
    run = recorded.run
    print("#" * 110)
    print("# REPLAY MODE - showing RECORDED output. No API calls are made in this mode.")
    print(f"# Recorded run {run.run_id} | model {run.model_requested} | started {run.started_at} | finished {run.finished_at}")
    print("#" * 110)
    records = recorded.records
    if args.ids:
        records = [r for r in records if r.application_id in set(args.ids)]
    for rec in _select_cards(records, args.show):
        print_card(rec)
    print_summary(run.model_copy(update={"mode": "replay"}), records)
    return 0


def live(args: argparse.Namespace) -> int:
    settings = load_llm_settings()
    api_key = settings.require_api_key()
    apps = load_applications(args.input, expected_count=args.expect_count)
    print(f"Loaded {len(apps)} applications from {args.input} (sha256 {file_sha256(args.input)[:12]}...)")
    invalid = [a for a in apps if not a.is_processable]
    if invalid:
        print(f"  {len(invalid)} row(s) failed validation and will be recorded without AI processing")

    subset = bool(args.limit or args.ids)
    if args.ids:
        known = {a.application_id for a in apps}
        missing = [i for i in args.ids if i not in known]
        if missing:
            print(f"Unknown application IDs: {missing}", file=sys.stderr)
            return 1
        apps = [a for a in apps if a.application_id in set(args.ids)]
    if args.limit:
        apps = apps[: args.limit]

    reuse: dict[str, EnrichedRecord] = {}
    if args.skip_existing:
        prev_path = Path(args.output_dir) / f"{FULL_STEM}.json"
        if prev_path.exists():
            prev = read_run_output(prev_path)
            by_id = {a.application_id: a for a in apps}
            for rec in prev.records:
                app = by_id.get(rec.application_id)
                same_source = app is not None and rec.source.description == app.description
                same_versions = rec.prompt_versions == PROMPT_VERSIONS and rec.schema_version == config.SCHEMA_VERSION
                same_model = all(c.model_requested == settings.model for c in rec.llm_calls)
                if rec.processing_status in SUCCESS and same_source and same_versions and same_model:
                    reuse[rec.application_id] = rec
            print(f"  --skip-existing: reusing {len(reuse)} successful record(s) from {prev_path}")

    llm = AnthropicStructuredLLM(
        api_key=api_key,
        model=settings.model,
        effort=settings.effort,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )
    run = RunMetadata(
        run_id=uuid.uuid4().hex[:12],
        mode="live",
        started_at=_now(),
        provider=settings.provider,
        model_requested=settings.model,
        effort=settings.effort,
        pipeline_version=config.PIPELINE_VERSION,
        prompt_versions=PROMPT_VERSIONS,
        schema_version=config.SCHEMA_VERSION,
        input_file=str(args.input),
        input_sha256=file_sha256(args.input),
        record_count=len(apps),
    )
    print(f"LIVE run {run.run_id}: provider={settings.provider} model={settings.model} effort={settings.effort} "
          f"concurrency={args.concurrency or settings.max_concurrency}")
    t0 = time.monotonic()

    def progress(done: int, total: int, rec: EnrichedRecord, reused: bool) -> None:
        tag = "reused" if reused else f"{sum(c.latency_ms or 0 for c in rec.llm_calls) / 1000:.1f}s"
        print(f"  [{done:>2}/{total}] {rec.application_id} {rec.source.client_name[:34]:<34} {_short(rec)} ({tag})", flush=True)

    records = run_batch(
        apps,
        llm,
        max_concurrency=args.concurrency or settings.max_concurrency,
        reuse=reuse,
        on_record=progress,
    )

    run.finished_at = _now()
    run.status_counts = dict(Counter(r.processing_status.value for r in records))
    run.risk_level_counts = dict(Counter(r.triage_risk_level.value for r in records))
    fresh = [r for r in records if r.application_id not in reuse]
    run.total_input_tokens = sum(c.input_tokens or 0 for r in fresh for c in r.llm_calls)
    run.total_output_tokens = sum(c.output_tokens or 0 for r in fresh for c in r.llm_calls)
    if reuse:
        run.notes.append(f"{len(reuse)} record(s) reused from a previous run via --skip-existing")
    if subset:
        run.notes.append("Subset run (--limit/--ids); full results file left untouched")

    output = RunOutput(run=run, records=records)
    json_path, csv_path = write_outputs(output, args.output_dir, stem=SUBSET_STEM if subset else FULL_STEM)
    with (Path(args.output_dir) / "run_log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(run.model_dump(mode="json")) + "\n")

    for rec in _select_cards(records, args.show):
        print_card(rec)
    print_summary(run, records)
    print(f"  wrote {json_path} and {csv_path} in {time.monotonic() - t0:.1f}s")

    failed = [r for r in records if r.processing_status not in SUCCESS]
    if failed:
        print(f"  {len(failed)} record(s) need attention: {[r.application_id for r in failed]}")
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # The SDK's HTTP logger can include request details; keep it quiet unless debugging.
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    try:
        return replay(args) if args.replay else live(args)
    except (ConfigError, InputValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
