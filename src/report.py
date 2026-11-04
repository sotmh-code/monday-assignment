"""Generate an offline, customer-facing review report from existing POC results.

Run: python -m src.report --input output/enriched_applications.json

The HTML report works offline (file://), needs no server, model API, or UI dependencies.
It is READ ONLY; it does not approve clients or write back to monday.com.
"""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _label(value: object) -> str:
    return str(value or "Unavailable").replace("_", " ").title()


def _tag(text: object, kind: str = "muted") -> str:
    return '<span class="tag ' + _esc(kind) + '">' + _esc(text) + "</span>"


def _list(items: list[str], empty: str = "None identified in the supplied text.") -> str:
    if not items:
        return '<p class="muted">' + _esc(empty) + "</p>"
    return "<ul>" + "".join("<li>" + _esc(x) + "</li>" for x in items) + "</ul>"


def _risk_kind(value: str) -> str:
    return {"LOW": "low", "MEDIUM": "medium", "HIGH": "high"}.get(value, "attention")


def _case(rec: dict, visible: bool) -> str:
    app_id = str(rec.get("application_id") or "")
    src = rec.get("source") or {}
    risk = rec.get("risk_assessment") or {}
    summary = rec.get("onboarding_summary") or {}
    guard = rec.get("guardrails") or {}
    checks = {(x.get("kind"), x.get("index")): bool(x.get("verified_in_source"))
              for x in guard.get("evidence_checks") or []}
    risk_level = str(rec.get("triage_risk_level") or "NEEDS_REVIEW")
    sections = []
    sections.append('<article class="case-detail" data-detail="' + _esc(app_id) + '"' +
                    ("" if visible else " hidden") + '>')
    sections.append('<div class="row"><div><p class="eyebrow">APPLICATION ' + _esc(app_id) + '</p><h2>' +
                    _esc(src.get("client_name")) + '</h2><p class="muted">' +
                    _esc(src.get("client_type")) + ' · ' + _esc(src.get("requested_services")) +
                    '</p></div><div class="right">' + _tag(_label(risk_level) + " advisory triage",
                    _risk_kind(risk_level)) + '<p class="muted">Compliance decision: pending</p></div></div>')
    sections.append('<div class="stages"><div><small>STAGE 1 · AI RISK TRIAGE</small><b>' +
                    _esc(_label(risk_level)) + '</b></div><div><small>STAGE 2 · OPERATIONS SUMMARY</small><b>' +
                    ("Generated from Stage 1" if summary else "Unavailable") +
                    '</b></div><div><small>FINAL DECISION</small><b>Human Compliance analyst</b></div></div>')
    sections.append('<section><h3>1 · Risk triage and source evidence</h3>')
    if not risk:
        sections.append('<div class="alert">Risk assessment unavailable. This case must be reviewed manually; do not infer LOW risk.</div>')
    else:
        sections.append("<p>" + _esc(risk.get("rationale")) + '</p><p class="small"><b>Review priority:</b> ' +
                        _esc(_label(risk.get("review_priority"))) + ' &nbsp; <b>Suggested queue:</b> ' +
                        _esc(_label(rec.get("routing"))) + "</p>")
        factors = risk.get("risk_factors") or []
        sections.append("<h4>Risk indicators</h4>")
        if not factors:
            sections.append('<p class="muted">No explicit risk indicators identified in the provided application text. Standard KYC is still required.</p>')
        for i, f in enumerate(factors):
            verified = checks.get(("risk_factor", i), False)
            sections.append('<div class="finding"><div class="row"><b>' + _esc(f.get("factor")) +
                            '</b>' + _tag(_label(f.get("severity")), _risk_kind(str(f.get("severity")))) +
                            '</div><blockquote>“' + _esc(f.get("source_evidence")) + '”</blockquote><small class="' +
                            ("good" if verified else "bad") + '">' +
                            ("Exact quotation found in source text" if verified else "Quotation not verified — review required") +
                            "</small></div>")
        sections.append("<h4>Information the analyst should obtain or confirm</h4>")
        missing = risk.get("missing_information") or []
        sections.append(_list([str(x.get("item") or "") + " (" + _label(x.get("status")) + ")" for x in missing]))
        if risk.get("mitigating_factors"):
            sections.append('<details><summary>Mitigating facts and evidence</summary>' +
                            _list([str(x.get("factor")) + ': "' + str(x.get("source_evidence")) + '"'
                                   for x in risk["mitigating_factors"]]) + "</details>")
    sections.append("</section><section><h3>2 · Risk-informed onboarding summary</h3>")
    if summary:
        sections.append('<p class="summary-box">' + _esc(summary.get("summary_text")) + '</p>')
        sections.append('<p class="small"><b>Operational complexity:</b> ' +
                        _esc(_label(summary.get("onboarding_complexity"))) +
                        ' &nbsp; <b>Stage 1 triage acknowledged:</b> ' +
                        _esc(_label(summary.get("risk_level_acknowledged"))) + "</p>")
        sections.append("<h4>Next actions and owners</h4><ol>")
        for a in summary.get("next_actions") or []:
            sections.append('<li><b>' + _esc(_label(a.get("suggested_owner"))) + "</b>: " +
                            _esc(a.get("action")) + (" " + _tag("Blocks account opening", "attention")
                            if a.get("blocks_account_opening") else "") + "</li>")
        sections.append("</ol>")
    else:
        sections.append('<div class="alert">Operations summary unavailable; use manual review.</div>')
    sections.append("</section><section><h3>3 · Guardrails and review boundaries</h3>")
    evidence = guard.get("evidence_checks") or []
    bad_quotes = int(guard.get("unverified_evidence_count") or 0)
    flags = len(guard.get("policy_flags") or [])
    mismatch = bool(summary and risk and summary.get("risk_level_acknowledged") != risk.get("risk_level"))
    tiles = [
        ("Structured output", "Schema-validated when processing succeeds"),
        ("Source quotation checks", str(max(0, len(evidence) - bad_quotes)) + " / " + str(len(evidence)) + " matched"),
        ("Prohibited compliance claims", str(flags) + " flagged by deterministic checks"),
        ("Stage dependency", "Mismatch — analyst attention needed" if mismatch else
         "Summary acknowledges Stage 1 triage" if summary else "Not available"),
        ("Authorization", "Human approval not performed by AI"),
    ]
    sections.append('<div class="controls">' + "".join('<div><b>' + _esc(k) +
                    '</b><span>' + _esc(v) + '</span></div>' for k, v in tiles) + "</div>")
    if bad_quotes or flags or mismatch or rec.get("warnings") or rec.get("errors"):
        warnings = [str(w) for w in rec.get("warnings") or []]
        warnings += [str(e.get("message")) for e in rec.get("errors") or []]
        sections.append('<div class="alert"><b>Reviewer attention required</b>' + _list(warnings,
                        "See the guardrail indicators above.") + "</div>")
    sections.append('<p class="footnote">A verbatim quote confirms text provenance, not that the model interpreted the quote correctly. '
                    'This demo does not perform screening or approve clients.</p>')
    sections.append('<details><summary>Original fictional application text</summary><p>' +
                    _esc(src.get("description")) + "</p></details></section></article>")
    return "".join(sections)


STYLE = """<style>
:root{font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;background:#f2f6fb;color:#1d314e}
*{box-sizing:border-box}body{margin:0}.top{padding:23px 34px;background:#102846;border-top:5px solid #00a091;color:white}
.top h1{font-size:27px;margin:5px 0}.top p{margin:0;color:#c9dced}.eyebrow{font-size:10px;font-weight:800;letter-spacing:.1em;color:#009e91}
.top .eyebrow{color:#89e3d9}.wrap{max-width:1440px;margin:auto;padding:22px}
.warning{border-radius:9px;background:#fff1d9;padding:12px 16px;font-size:13px;margin-bottom:14px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}
.metric,.sidebar,.case-detail{border-radius:11px;background:white;border:1px solid #d9e5f1}
.metric{padding:15px}.metric b{display:block;font-size:27px;color:#226ab4}.metric small,.muted{color:#667c93}
.layout{display:grid;grid-template-columns:294px minmax(0,1fr);gap:17px}
.sidebar{padding:13px;align-self:start;position:sticky;top:14px;max-height:calc(100vh - 36px);overflow:auto}
.sidebar h2{font-size:15px;margin:2px 0 10px}input,select{width:100%;padding:10px;margin:3px 0 8px;border:1px solid #cad8e7;border-radius:8px;background:white}
.case-button{display:block;text-align:left;width:100%;margin:3px 0;padding:10px;border-radius:8px;border:1px solid transparent;background:transparent;cursor:pointer;font:inherit}
.case-button:hover{background:#f0f6ff}.case-button.active{background:#e9f4ff;border-color:#95bee6}
.case-button b{display:block;font-size:12px}.case-button small{font-size:11px;color:#688096}
.case-detail{padding:24px 27px}.case-detail[hidden],.case-button[hidden]{display:none}
.row{display:flex;justify-content:space-between;gap:12px;align-items:start}.right{text-align:right}.right p{font-size:12px}
h2{margin:4px 0;font-size:23px}.tag{border-radius:20px;font-size:11px;font-weight:700;padding:5px 8px;background:#eaf0f7;color:#41617f;white-space:nowrap;display:inline-block}
.low{background:#dff3e7;color:#16744b}.medium{background:#fff0cc;color:#805408}.high{background:#fbe1e1;color:#982f39}.attention{background:#ffe8df;color:#9d4f2a}
.stages{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:19px 0}
.stages div{background:#edf5fc;border-radius:8px;padding:11px}.stages small{font-size:10px;color:#688299;display:block}.stages b{font-size:12px;display:block;margin-top:5px}
section{border-top:1px solid #e0e7f0;margin-top:18px;padding-top:17px}section h3{font-size:17px;color:#1b5487;margin:0 0 10px}h4{font-size:13px;margin:15px 0 8px}
p,li{line-height:1.55}.small{font-size:12px}.finding{background:#f6f9fd;border-left:3px solid #2478be;padding:12px;margin:9px 0;border-radius:4px}
.finding blockquote{margin:8px 0;font-size:13px;line-height:1.5}.good{color:#16885e}.bad{color:#a24127}
.summary-box{background:#e6f8f2;border-radius:8px;padding:13px 16px;line-height:1.7}
li{margin:6px 0}.controls{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}
.controls div{border:1px solid #e1e7ed;border-radius:8px;padding:10px}.controls b,.controls span{display:block;font-size:12px}.controls span{color:#678099;margin-top:5px}
.alert{background:#fff0e8;border-radius:7px;padding:13px;margin:10px 0}.footnote{font-size:12px;color:#60778c}
details{padding:11px;border-radius:7px;background:#f2f6fc;margin:11px 0}summary{font-weight:600;cursor:pointer}
.links a{font-size:12px;color:#226ab4;display:block;margin:10px 0}.footer{color:#71849b;font-size:11px;text-align:center;margin:25px}
@media(max-width:900px){.metrics{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}.sidebar{position:static;max-height:290px}.stages{grid-template-columns:1fr}.row{display:block}.right{text-align:left}}
</style>"""

JAVASCRIPT = """<script>
(()=>{const buttons=[...document.querySelectorAll('.case-button')],cards=[...document.querySelectorAll('.case-detail')];
const search=document.getElementById('search'),filter=document.getElementById('risk-filter');
function select(id){buttons.forEach(b=>{let yes=b.dataset.id===id;b.classList.toggle('active',yes);b.setAttribute('aria-pressed',yes?'true':'false')});
cards.forEach(c=>{c.hidden=c.dataset.detail!==id});}
function refresh(){let query=search.value.toLowerCase().trim(),level=filter.value,first='';
buttons.forEach(b=>{let ok=b.dataset.lookup.includes(query)&&(!level||b.dataset.risk===level);b.hidden=!ok;if(ok&&!first)first=b.dataset.id});
let active=buttons.find(b=>b.classList.contains('active')&&!b.hidden);
if(active)select(active.dataset.id);else if(first)select(first);else cards.forEach(c=>{c.hidden=true});
document.getElementById('none').hidden=!!first;}
buttons.forEach(b=>b.addEventListener('click',()=>select(b.dataset.id)));
search.addEventListener('input',refresh);filter.addEventListener('change',refresh);
})();
</script>"""


def render_html(run_output: dict) -> str:
    records = run_output.get("records") or []
    if not records:
        raise ValueError("No application records in the run")
    run = run_output.get("run") or {}
    counts = Counter(str(r.get("triage_risk_level") or "") for r in records)
    completed = sum(r.get("processing_status") in ("COMPLETED", "COMPLETED_WITH_WARNINGS")
                    for r in records)
    pending = sum(r.get("human_review_status") == "PENDING_HUMAN_REVIEW" for r in records)
    tiles = [(len(records), "Applications"), (completed, "AI summaries generated"),
             (counts.get("HIGH", 0) + counts.get("NEEDS_REVIEW", 0), "High risk / needs review"),
             (pending, "Awaiting human decision")]
    metrics = "".join('<div class="metric"><b>' + str(num) + '</b><small>' + _esc(text) +
                      "</small></div>" for num, text in tiles)
    buttons = []
    for i, r in enumerate(records):
        src = r.get("source") or {}
        app_id = str(r.get("application_id") or "")
        risk = str(r.get("triage_risk_level") or "NEEDS_REVIEW")
        buttons.append('<button type="button" class="case-button' + (" active" if i == 0 else "") +
                       '" aria-pressed="' + ("true" if i == 0 else "false") + '" data-id="' +
                       _esc(app_id) + '" data-risk="' + _esc(risk) + '" data-lookup="' +
                       _esc((str(src.get("client_name") or "") + " " + app_id).lower()) +
                       '"><b>' + _esc(src.get("client_name")) + '</b><small>' +
                       _esc(app_id) + " · " + _esc(_label(risk)) + " · " +
                       _esc(_label(r.get("routing"))) + "</small></button>")
    cards = "".join(_case(r, i == 0) for i, r in enumerate(records))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Crestview | Client Intake Review</title>' + STYLE + '</head><body>'
        '<header class="top"><p class="eyebrow">CRESTVIEW CAPITAL GROUP · AI-ASSISTED ONBOARDING</p>'
        '<h1>Client Intake Review</h1><p>Grounded risk observations → actionable operations → human compliance approval</p></header>'
        '<main class="wrap"><div class="warning"><b>Read-only fictional-data POC.</b> '
        'Advisory AI triage is not sanctions screening, document verification, or a final KYC/AML decision.</div>'
        '<div class="metrics">' + metrics + '</div><div class="layout"><aside class="sidebar">'
        '<h2>Applications</h2><input id="search" type="search" placeholder="Search client or ID">'
        '<select id="risk-filter"><option value="">All risk levels</option>'
        '<option value="LOW">Low</option><option value="MEDIUM">Medium</option>'
        '<option value="HIGH">High</option><option value="NEEDS_REVIEW">Needs review</option></select>' +
        "".join(buttons) + '<div class="links">'
        '<a href="risk_assessments.json" download>Export Stage 1 risk assessments</a>'
        '<a href="onboarding_summaries.json" download>Export Stage 2 summaries</a></div></aside>'
        '<div><div id="none" class="warning" hidden>No matching applications.</div>' +
        cards + '</div></div><p class="footer">Recorded run ' +
        _esc(run.get("run_id")) + " · Model: " + _esc(run.get("model_requested")) +
        " · No network calls are made by this dashboard.</p></main>" + JAVASCRIPT + "</body></html>"
    )


def generate(input_path: Path, html_path: Path | None = None) -> tuple[Path, Path, Path]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise ValueError("Expected a run JSON object with a records array")
    if not data["records"]:
        raise ValueError("Run contains no records")
    html_path = html_path or input_path.parent / "crestview_review_dashboard.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = (data.get("run") or {}).get("run_id")
    stage1 = {"run_id": run_id, "stage": "risk_assessment", "records": [
        {"application_id": r.get("application_id"), "client_name": (r.get("source") or {}).get("client_name"),
         "processing_status": r.get("processing_status"),
         "risk_assessment": r.get("risk_assessment"), "guardrails": r.get("guardrails")}
        for r in data["records"]
    ]}
    stage2 = {"run_id": run_id, "stage": "onboarding_summary", "records": [
        {"application_id": r.get("application_id"), "client_name": (r.get("source") or {}).get("client_name"),
         "stage_1_risk_assessment_used": r.get("risk_assessment"),
         "onboarding_summary": r.get("onboarding_summary"),
         "audit_only_stage_1_sha256": r.get("summary_consumed_risk_sha256")}
        for r in data["records"]
    ]}
    stage1_path = html_path.parent / "risk_assessments.json"
    stage2_path = html_path.parent / "onboarding_summaries.json"
    stage1_path.write_text(json.dumps(stage1, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stage2_path.write_text(json.dumps(stage2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(render_html(data), encoding="utf-8")
    return html_path, stage1_path, stage2_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an offline, customer-facing review dashboard")
    parser.add_argument("--input", default="output/enriched_applications.json")
    parser.add_argument("--output", help="Optional HTML destination; JSON exports are placed beside it")
    args = parser.parse_args(argv)
    html_path, stage1_path, stage2_path = generate(
        Path(args.input), Path(args.output) if args.output else None
    )
    print("Offline dashboard:", html_path)
    print("Stage 1 JSON:", stage1_path)
    print("Stage 2 JSON:", stage2_path)
    print("Open the dashboard in a browser. This reads recorded data; no AI calls are made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
