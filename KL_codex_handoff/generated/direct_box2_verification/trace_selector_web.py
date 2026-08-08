from __future__ import annotations

import argparse
import html
import json
import math
import threading
import webbrowser
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer
from itertools import product
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, quote_plus, urlencode, urlsplit

import verify_direct_box2 as trace


HOST = "127.0.0.1"
BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR / "interactive_results"
EXPANDED_PAGE_SIZE = 60
EXPANSION_TERMS_PER_LINE = 2
TRACE_TERMS_PER_MATH_NODE = 220

FIELD_OPERATOR_LATEX = {
    "T": "T",
    "phi": r"\phi",
    "BLL": r"B_{LL}",
    "BRR": r"B_{RR}",
    "UL": r"U_L",
    "UR": r"U_R",
    "ULLR": r"U_{LLR}",
    "ULRR": r"U_{LRR}",
}


CSS = r"""
:root {
  color-scheme: light;
  --ink: #172338;
  --muted: #64748b;
  --line: #dce4ee;
  --paper: #ffffff;
  --wash: #f4f7fb;
  --navy: #17355c;
  --blue: #245fa6;
  --blue-soft: #edf5ff;
  --teal: #087e75;
  --gold: #d7a83e;
  --shadow: 0 14px 36px rgba(23, 53, 92, .09);
}
* { box-sizing: border-box; }
html { min-height: 100%; background: var(--wash); }
body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  background:
    radial-gradient(circle at 92% 3%, rgba(36,95,166,.11), transparent 30rem),
    linear-gradient(180deg, #fbfdff 0, var(--wash) 24rem);
  font-family: "Pretendard", "Noto Sans KR", "Malgun Gothic", system-ui, sans-serif;
  line-height: 1.58;
}
a { color: inherit; }
.shell { width: min(1280px, calc(100% - 32px)); margin: 0 auto; padding-bottom: 64px; }
.topbar {
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  min-height: 76px; border-bottom: 1px solid rgba(23,53,92,.10);
}
.brand { display: inline-flex; align-items: center; gap: 12px; text-decoration: none; font-weight: 780; letter-spacing: -.02em; }
.brand-mark {
  display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px;
  color: white; background: linear-gradient(145deg, var(--navy), var(--blue)); box-shadow: 0 8px 20px rgba(36,95,166,.23);
  font-family: Georgia, serif; font-size: 19px;
}
.step { color: var(--muted); font-size: 13px; font-weight: 650; letter-spacing: .02em; }
.hero { padding: 54px 0 30px; }
.eyebrow { margin: 0 0 10px; color: var(--blue); font-size: 13px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
h1 { margin: 0; color: var(--navy); font-family: Georgia, "Times New Roman", serif; font-size: clamp(34px, 5vw, 58px); line-height: 1.08; letter-spacing: -.035em; }
.lede { max-width: 760px; margin: 17px 0 0; color: var(--muted); font-size: 17px; }
.field-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.field-card {
  position: relative; min-height: 225px; padding: 22px; overflow: hidden;
  border: 1px solid var(--line); border-radius: 18px; background: rgba(255,255,255,.90);
  box-shadow: 0 7px 22px rgba(23,53,92,.055); text-decoration: none;
  transition: transform .16s ease, border-color .16s ease, box-shadow .16s ease;
}
.field-card::after {
  content: ""; position: absolute; right: -35px; bottom: -50px; width: 120px; height: 120px; border-radius: 50%;
  background: rgba(36,95,166,.055); transition: transform .18s ease;
}
.field-card:hover, .field-card:focus-visible { transform: translateY(-3px); border-color: #9ebddd; box-shadow: var(--shadow); outline: none; }
.field-card:hover::after { transform: scale(1.18); }
.card-number { color: var(--blue); font-size: 12px; font-weight: 850; letter-spacing: .12em; }
.field-symbol { display: grid; min-height: 76px; place-items: center; color: var(--navy); font-size: 22px; overflow-x: auto; }
.representation { padding-top: 13px; border-top: 1px solid #e9eef5; color: var(--muted); font-size: 14px; }
.meta-row { display: flex; justify-content: space-between; gap: 12px; margin-top: 14px; color: var(--muted); font-size: 12px; }
.choose { color: var(--blue); font-weight: 750; }
.breadcrumb { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 28px 0 0; color: var(--muted); font-size: 14px; }
.breadcrumb a { color: var(--blue); text-decoration: none; }
.panel { border: 1px solid var(--line); border-radius: 20px; background: var(--paper); box-shadow: var(--shadow); }
.selected-field { display: grid; grid-template-columns: minmax(220px, .8fr) 1.2fr; overflow: hidden; }
.selected-symbol { display: grid; min-height: 210px; place-items: center; padding: 28px; color: var(--navy); background: linear-gradient(145deg, #f2f7ff, #ffffff); font-size: 28px; overflow-x: auto; }
.selected-copy { padding: 30px; align-self: center; }
.selected-copy h2, .section-title { margin: 0; color: var(--navy); font-family: Georgia, "Times New Roman", serif; }
.selected-copy p { margin: 9px 0 0; color: var(--muted); }
.order-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 22px; }
.order-card { display: block; padding: 25px; border: 1px solid var(--line); border-radius: 18px; background: white; text-decoration: none; transition: .16s ease; }
.order-card:hover, .order-card:focus-visible { border-color: #91b4db; transform: translateY(-2px); box-shadow: var(--shadow); outline: none; }
.order-kicker { color: var(--blue); font-size: 13px; font-weight: 820; letter-spacing: .1em; }
.order-math { margin: 20px 0; color: var(--navy); font-size: 22px; overflow-x: auto; }
.order-copy { color: var(--muted); font-size: 14px; }
.result-head { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; padding: 34px; }
.result-title { margin: 0 0 9px; color: var(--navy); font: 700 clamp(26px,4vw,42px)/1.1 Georgia, serif; }
.result-meta { color: var(--muted); }
.switches { display: flex; flex-wrap: wrap; gap: 8px; }
.pill { display: inline-flex; align-items: center; min-height: 38px; padding: 7px 13px; border: 1px solid var(--line); border-radius: 999px; background: white; color: var(--blue); font-size: 13px; font-weight: 760; text-decoration: none; }
.pill.active { border-color: var(--blue); color: white; background: var(--blue); }
.formula-box { margin: 0 34px 34px; padding: 25px; border: 1px solid #bfd5eb; border-radius: 16px; color: var(--navy); background: var(--blue-soft); font-size: clamp(17px,2.1vw,24px); overflow-x: auto; }
.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }
.metric { padding: 18px; border: 1px solid var(--line); border-radius: 14px; background: white; }
.metric-label { display: block; color: var(--muted); font-size: 12px; }
.metric-value { display: block; margin-top: 4px; color: var(--navy); font-size: 25px; font-weight: 780; }
.moment-strip { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 16px; }
.moment { min-width: 92px; padding: 10px 13px; border: 1px solid var(--line); border-radius: 12px; background: white; text-align: center; }
.moment b { display: block; color: var(--navy); font-size: 18px; }
.moment span { color: var(--muted); font-size: 12px; }
.section { margin-top: 24px; }
.section-card { padding: 28px; }
.section-top { display: flex; justify-content: space-between; align-items: baseline; gap: 18px; margin-bottom: 17px; }
.section-note { color: var(--muted); font-size: 13px; }
.artifact-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.button { appearance: none; min-height: 43px; padding: 10px 16px; border: 0; border-radius: 11px; color: white; background: var(--blue); font: 750 14px/1.2 inherit; cursor: pointer; text-decoration: none; }
.button:hover { background: var(--navy); }
.button.secondary { border: 1px solid var(--line); color: var(--blue); background: white; }
.button.secondary:hover { border-color: #9ebddd; background: var(--blue-soft); }
.notice { margin: 18px 0; padding: 13px 16px; border-left: 4px solid var(--teal); border-radius: 8px; color: #14564f; background: #ecfaf7; }
.notice.error { border-color: #bc4b51; color: #84333a; background: #fff1f2; }
.table-wrap { overflow: auto; border: 1px solid var(--line); border-radius: 13px; }
table { width: 100%; border-collapse: collapse; background: white; font-size: 13px; }
th { position: sticky; top: 0; z-index: 1; padding: 11px 12px; color: #42536b; background: #f2f6fa; text-align: left; white-space: nowrap; }
td { padding: 11px 12px; border-top: 1px solid #e8edf3; vertical-align: top; }
tbody tr:hover { background: #fafcff; }
.math-cell { min-width: 190px; color: var(--navy); }
.formula-cell { min-width: 560px; overflow-wrap: anywhere; }
.combined-formula {
  position: relative; max-height: 68vh; padding: 22px 24px; overflow: auto;
  border: 1px solid #bfd5eb; border-radius: 14px; color: var(--navy); background: #f8fbff;
  font-size: 15px;
}
.combined-formula mjx-container[display="true"] { margin: 0; text-align: left; }
.combined-formula-note { margin: -5px 0 16px; color: var(--muted); font-size: 13px; }
.formula-stack { padding: 0; }
.formula-part-wrap + .formula-part-wrap { border-top: 1px solid #d9e6f3; }
.formula-continuation-label { margin: 0; padding: 12px 24px 0; color: var(--muted); font-size: 12px; font-weight: 750; }
.formula-part { padding: 10px 24px 22px; min-width: max-content; }
.lazy-math[aria-busy="true"] { min-height: 180px; display: grid; place-items: center; color: var(--muted); }
.expansion-summary { display: flex; flex-wrap: wrap; gap: 9px; margin: 0 0 16px; }
.expansion-badge { padding: 7px 11px; border: 1px solid var(--line); border-radius: 999px; color: var(--navy); background: white; font-size: 12px; font-weight: 750; }
.pagination { display: flex; justify-content: space-between; align-items: center; gap: 14px; margin-top: 15px; color: var(--muted); font-size: 13px; }
.empty { padding: 24px; color: var(--muted); text-align: center; }
.footnote { margin-top: 22px; color: var(--muted); font-size: 12px; }
@media (max-width: 1020px) { .field-grid { grid-template-columns: repeat(2,1fr); } .metrics { grid-template-columns: repeat(2,1fr); } }
@media (max-width: 680px) {
  .shell { width: min(100% - 22px, 1280px); }
  .topbar { min-height: 64px; }
  .hero { padding-top: 36px; }
  .field-grid, .order-grid, .selected-field { grid-template-columns: 1fr; }
  .field-card { min-height: 205px; }
  .selected-symbol { min-height: 150px; }
  .result-head { display: block; padding: 24px; }
  .switches { margin-top: 20px; }
  .formula-box { margin: 0 24px 24px; padding: 18px; }
  .metrics { grid-template-columns: 1fr 1fr; }
  .section-card { padding: 20px; }
  .section-top, .pagination { align-items: flex-start; flex-direction: column; }
}
"""


MATHJAX = r"""
<script>
window.MathJax = {
  tex: {
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    maxBuffer: 1024 * 1024
  },
  svg: {fontCache: 'global'},
  options: {skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']}
};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<script>
document.addEventListener('DOMContentLoaded', () => {
  const render = async (node) => {
    if (node.dataset.rendered === 'true' || node.dataset.rendering === 'true') return;
    node.dataset.rendering = 'true';
    try {
      await window.MathJax.startup.promise;
      const output = await window.MathJax.tex2svgPromise(node.dataset.latex, {display: true});
      node.replaceChildren(output);
      node.dataset.rendered = 'true';
      node.setAttribute('aria-busy', 'false');
    } catch (error) {
      node.textContent = '수식을 렌더링하지 못했습니다.';
      node.classList.add('notice', 'error');
      node.setAttribute('aria-busy', 'false');
      console.error(error);
    } finally {
      delete node.dataset.rendering;
    }
  };
  const nodes = [...document.querySelectorAll('.lazy-math[data-latex]')];
  if (!nodes.length) return;
  if (!('IntersectionObserver' in window)) {
    nodes.forEach(render);
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      observer.unobserve(entry.target);
      render(entry.target);
    });
  }, {rootMargin: '320px 0px'});
  nodes.forEach((node) => observer.observe(node));
});
</script>
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def math_html(latex: str, *, display: bool = False) -> str:
    delimiters = (r"\[", r"\]") if display else (r"\(", r"\)")
    return f'{delimiters[0]}{esc(latex)}{delimiters[1]}'


def shell(title: str, body: str, step: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{esc(title)} · Box Trace</title>
  <style>{CSS}</style>
  {MATHJAX}
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <a class="brand" href="/"><span class="brand-mark">□</span><span>Box Trace Selector</span></a>
      <span class="step">{esc(step)}</span>
    </header>
    {body}
  </div>
</body>
</html>"""


def canonical_field(value: str | None):
    return trace.resolve_field(value or "")


def field_query(field, trace_order: int | None = None, **extra: object) -> str:
    values: dict[str, object] = {"field": field[0]}
    if trace_order is not None:
        values["n"] = trace_order
    values.update(extra)
    return "/trace?" + urlencode(values)


def render_home() -> str:
    cards = []
    for number, field in enumerate(trace.FIELDS, 1):
        name, a, b, _ = field
        details = trace.FIELD_DETAILS[name]
        field_symbol_html = math_html(details["latex"], display=True)
        representation_html = math_html(details["representation"])
        slots_text = f"unbarred {a} · barred {b}"
        cards.append(f"""
        <a class="field-card" href="{field_query(field)}" aria-label="{esc(name)} 필드 선택">
          <div class="card-number">FIELD {number:02d}</div>
          <div class="field-symbol">{field_symbol_html}</div>
          <div class="representation">{representation_html}</div>
          <div class="meta-row">
            <span>{slots_text}</span>
            <span class="choose">선택 →</span>
          </div>
        </a>""")
    body = f"""
    <main>
      <section class="hero">
        <p class="eyebrow">Finite-dimensional representation trace</p>
        <h1>계산할 필드를 선택하세요</h1>
        <p class="lede">모든 필드 기호와 표현을 LaTeX로 확인한 뒤, 원하는 카드를 눌러 {math_html('n=1')} 또는 {math_html('n=2')} trace 계산으로 진행합니다.</p>
      </section>
      <section class="field-grid" aria-label="선택 가능한 필드">
        {''.join(cards)}
      </section>
      <p class="footnote">범위: raw tensor product, density weight 0, functional trace 이전의 유한차원 spinor/tensor trace.</p>
    </main>"""
    return shell("필드 선택", body, "1 / 3 · 필드")


def render_order(field) -> str:
    name, a, b, _ = field
    details = trace.FIELD_DETAILS[name]
    field_symbol_html = math_html(details["latex"], display=True)
    representation_html = math_html(details["representation"])
    n1_trace_html = math_html(main_trace_prefix_latex(field) + r"\Box", display=True)
    n2_trace_html = math_html(
        main_trace_prefix_latex(field) + r"(\Box\circ\Box)", display=True
    )
    body = f"""
    <main>
      <nav class="breadcrumb"><a href="/">필드 선택</a><span>›</span><span>{esc(name)}</span></nav>
      <section class="hero">
        <p class="eyebrow">Field selected</p>
        <h1>trace 차수를 선택하세요</h1>
      </section>
      <section class="selected-field panel">
        <div class="selected-symbol">{field_symbol_html}</div>
        <div class="selected-copy">
          <h2>{esc(name)}</h2>
          <p>표현 {representation_html}</p>
          <p>unbarred spinor slots {a} · barred spinor slots {b}</p>
        </div>
      </section>
      <section class="order-grid" aria-label="trace 차수">
        <a class="order-card" href="{field_query(field, 1)}">
          <div class="order-kicker">ORDER 01</div>
          <div class="order-math">{n1_trace_html}</div>
          <div class="order-copy">main.pdf 표기로 완전히 평가한 유한차원 spinor-index trace를 표시합니다.</div>
        </a>
        <a class="order-card" href="{field_query(field, 2)}">
          <div class="order-kicker">ORDER 02</div>
          <div class="order-math">{n2_trace_html}</div>
          <div class="order-copy">모든 covariant-D를 보통 편미분으로 풀고, spinor trace의 local metric을 배경 텐서 지표에 흡수한 Einstein 수축 ledger를 표시합니다.</div>
        </a>
      </section>
    </main>"""
    return shell(f"{name} · 차수 선택", body, "2 / 3 · trace 차수")


def artifact_specs(field, trace_order: int) -> dict[str, tuple[str, str, str]]:
    stem = f"trace_{field[0]}_n{trace_order}"
    return {
        "pdf": (f"{stem}.pdf", "application/pdf", "PDF"),
        "details_csv": (f"{stem}_details.csv", "text/csv; charset=utf-8", "trace 상세 CSV"),
        "expanded_csv": (f"{stem}_expanded.csv", "text/csv; charset=utf-8", "primitive 기여항 CSV"),
        "tex": (f"{stem}.tex", "application/x-tex; charset=utf-8", "LaTeX 원문"),
        "summary_json": (f"{stem}_summary.json", "application/json; charset=utf-8", "요약 JSON"),
    }


def artifact_path(field, trace_order: int, kind: str) -> tuple[Path, str, str] | None:
    spec = artifact_specs(field, trace_order).get(kind)
    if spec is None:
        return None
    filename, content_type, label = spec
    return ARTIFACT_DIR / filename, content_type, label


def artifact_section(field, trace_order: int, *, generated: bool = False, error: str | None = None) -> str:
    links = []
    for kind, (filename, _content_type, label) in artifact_specs(field, trace_order).items():
        path = ARTIFACT_DIR / filename
        if not path.is_file():
            continue
        base = "/artifact?" + urlencode({"field": field[0], "n": trace_order, "kind": kind})
        if kind == "pdf":
            links.append(f'<a class="button secondary" href="{base}" target="_blank" rel="noopener">PDF 열기</a>')
            links.append(f'<a class="button secondary" href="{base}&amp;download=1">PDF 다운로드</a>')
        else:
            links.append(f'<a class="button secondary" href="{base}&amp;download=1">{esc(label)} 다운로드</a>')
    notice = ""
    if generated:
        notice = '<div class="notice">XeLaTeX PDF와 CSV 산출물을 새로 생성했습니다.</div>'
    elif error:
        notice = f'<div class="notice error">산출물 생성 중 오류가 발생했습니다: {esc(error)}</div>'
    existing = "".join(links) if links else '<span class="section-note">아직 생성된 산출물이 없습니다.</span>'
    return f"""
    <section class="section panel section-card">
      <div class="section-top">
        <div><p class="eyebrow">Artifacts</p><h2 class="section-title">PDF · CSV 산출물</h2></div>
        <span class="section-note">현재 화면 계산과 같은 필드·차수</span>
      </div>
      {notice}
      <form method="post" action="/generate">
        <input type="hidden" name="field" value="{esc(field[0])}">
        <input type="hidden" name="n" value="{trace_order}">
        <button class="button" type="submit">XeLaTeX PDF · CSV 생성</button>
      </form>
      <div class="artifact-actions">{existing}</div>
    </section>"""


def table_rows(rows: Iterable[dict]) -> str:
    output = []
    for row in rows:
        output.append(f"""
          <tr>
            <td>{esc(row['term_id'])}</td>
            <td>{esc(row['source'])}</td>
            <td>{esc(row['block_signature'])}</td>
            <td class="math-cell">{math_html(row['word_latex'])}</td>
            <td class="math-cell">{math_html(row['trace_tensor_latex'])}</td>
            <td>{esc(row['trace_basis'])}</td>
            <td>{esc(row['moment'])}</td>
          </tr>""")
    return "".join(output)


def expanded_table_rows(rows: Iterable[dict]) -> str:
    output = []
    for row in rows:
        signed = primitive_contribution(row)
        if signed is None:
            continue
        negative, body = signed
        contribution = ("-" if negative else "") + body
        contribution_html = math_html(r"\displaystyle " + contribution)
        output.append(f"""
          <tr>
            <td>{esc(row['term_id'])}</td>
            <td>{esc(row['component_index'])}.{esc(row['primitive_index'])}</td>
            <td>{esc(row['source'])}</td>
            <td>{esc(row['block_signature'])}</td>
            <td class="formula-cell">{contribution_html}</td>
          </tr>""")
    return "".join(output)


def primitive_contribution(row: dict) -> tuple[bool, str] | None:
    """Return the sign and absolute LaTeX body of one selected contribution."""
    scalar = Fraction(row["selected_scalar_num"], row["selected_scalar_den"])
    if scalar == 0:
        return None

    magnitude = abs(scalar)
    # ``\allowbreak`` is useful in the generated TeX/PDF but MathJax renders it
    # as an unknown command.  The aligned web equation already supplies breaks.
    formula = row["formula_latex"].replace(r"\allowbreak", "")
    if formula == "1":
        body = trace.frac_latex(magnitude)
    elif magnitude == 1:
        body = formula
    else:
        body = rf"{trace.frac_latex(magnitude)}\,{formula}"
    return scalar < 0, body


def selected_trace_lhs_latex(field, trace_order: int) -> str:
    field_symbol = FIELD_OPERATOR_LATEX[field[0]]
    representation = rf"\mathcal R_{{{field_symbol}}}"
    box = rf"\Box_{{{field_symbol}}}"
    if trace_order == 1:
        return rf"\operatorname{{tr}}_{{{representation}}}{box}"
    return rf"\operatorname{{tr}}_{{{representation}}}\!\left({box}\circ {box}\right)"


def combined_expansion_latex(field, trace_order: int, rows: Iterable[dict]) -> str:
    """Combine every nonzero primitive contribution into one aligned equation."""
    terms = []
    for row in rows:
        signed = primitive_contribution(row)
        if signed is not None:
            terms.append(signed)

    lhs = selected_trace_lhs_latex(field, trace_order)
    if not terms:
        return rf"{lhs}=0"

    rendered_terms = []
    for index, (negative, body) in enumerate(terms):
        if index == 0:
            prefix = "-" if negative else ""
        else:
            prefix = r"{}-" if negative else r"{}+"
        rendered_terms.append(prefix + body)

    lines = []
    for start in range(0, len(rendered_terms), EXPANSION_TERMS_PER_LINE):
        group = r"\quad ".join(rendered_terms[start: start + EXPANSION_TERMS_PER_LINE])
        lines.append((rf"{lhs}&={group}") if start == 0 else (rf"&\quad {group}"))
    return r"\begin{aligned}" + r"\\[0.45em]".join(lines) + r"\end{aligned}"


def main_trace_prefix_latex(field) -> str:
    """Finite-dimensional spinor-index trace, using the index style of main.pdf."""
    _, a, b, _ = field
    indices = []
    if a == 1:
        indices.append(r"\alpha")
    elif a > 1:
        indices.append(rf"\alpha_1\cdots\alpha_{a}")
    if b == 1:
        indices.append(r"\bar\alpha")
    elif b > 1:
        indices.append(rf"\bar\alpha_1\cdots\bar\alpha_{b}")
    subscript = ",".join(indices) if indices else r"\mathbf 1"
    return rf"\operatorname{{tr}}_{{{subscript}}}"


def _signed_latex_terms(terms: Iterable[tuple[Fraction, str]]) -> list[str]:
    rendered = []
    for index, (coefficient, body) in enumerate(terms):
        coefficient = Fraction(coefficient)
        if coefficient == 0:
            continue
        magnitude = abs(coefficient)
        coefficient_latex = "" if magnitude == 1 else trace.frac_latex(magnitude) + r"\,"
        if index == 0:
            sign = "-" if coefficient < 0 else ""
        else:
            sign = r"{}-" if coefficient < 0 else r"{}+"
        rendered.append(sign + coefficient_latex + body)
    return rendered


def main_n1_trace_latex(field) -> str:
    """Fully evaluated n=1 representation trace in main.pdf notation."""
    _, a, b, _ = field
    dimension = trace.D_SPIN ** (a + b)
    lhs = main_trace_prefix_latex(field) + r"\Box"
    terms = [
        (Fraction(1), r"\mathcal H^{AB}\partial_A\partial_B"),
        (Fraction(1), r"\mathcal H^{AB}\Gamma_{AB}{}^{C}\partial_C"),
        (Fraction(-a, 8), r"\mathcal H^{AB}\Phi_{A pq}\Phi_B{}^{pq}"),
        (Fraction(a, 4), r"\Gamma^{C}{}_{pq}\Phi_C{}^{pq}"),
        (Fraction(-a, 8), r"\Gamma_{A pq}\Gamma^{A pq}"),
        (Fraction(-b, 8), r"\mathcal H^{AB}\bar\Phi_{A\bar p\bar q}\bar\Phi_B{}^{\bar p\bar q}"),
        (Fraction(-b, 4), r"\Gamma^{C}{}_{\bar p\bar q}\bar\Phi_C{}^{\bar p\bar q}"),
        (Fraction(b, 8), r"\Gamma_{A\bar p\bar q}\Gamma^{A\bar p\bar q}"),
    ]
    rendered = _signed_latex_terms(terms)
    scale = "" if dimension == 1 else rf"{dimension}\,"
    lines = [rf"{lhs}&={scale}\Bigl\{{{rendered[0]}"]
    lines.extend(rf"&\quad {term}" for term in rendered[1:])
    lines[-1] += r"\Bigr\}"
    return r"\begin{aligned}" + r"\\[0.45em]".join(lines) + r"\end{aligned}"


def main_delta_latex(*, barred: bool) -> str:
    """Equation (2.1) or (2.2) from main.pdf, without internal shorthand."""
    if not barred:
        return (
            r"\begin{aligned}"
            r"\Delta T={}&\mathcal D_q\mathcal D^qT"
            r"+\left(\mathfrak R_{[q_1q_2]}-\Gamma^{B}{}_{q_1q_2}\mathcal D_B\right)G^{q_1q_2}T\\"
            r"&+\frac14\Gamma_{Bq_1q_2}\Gamma^{B}{}_{q_3q_4}"
            r"G^{q_1q_2}G^{q_3q_4}T"
            r"+\frac12\mathfrak R_{\bar q_1\bar q_2q_3q_4}"
            r"\bar G^{\bar q_1\bar q_2}G^{q_3q_4}T"
            r"\end{aligned}"
        )
    return (
        r"\begin{aligned}"
        r"\bar\Delta T={}&\mathcal D_{\bar q}\mathcal D^{\bar q}T"
        r"+\left(\mathfrak R_{[\bar q_1\bar q_2]}-\Gamma^{B}{}_{\bar q_1\bar q_2}\mathcal D_B\right)"
        r"\bar G^{\bar q_1\bar q_2}T\\"
        r"&+\frac14\Gamma_{B\bar q_1\bar q_2}\Gamma^{B}{}_{\bar q_3\bar q_4}"
        r"\bar G^{\bar q_1\bar q_2}\bar G^{\bar q_3\bar q_4}T"
        r"+\frac12\mathfrak R_{q_1q_2\bar q_3\bar q_4}"
        r"G^{q_1q_2}\bar G^{\bar q_3\bar q_4}T"
        r"\end{aligned}"
    )


def main_n2_trace_latex(field) -> str:
    trace_prefix = main_trace_prefix_latex(field)
    return (
        r"\begin{aligned}"
        + trace_prefix
        + r"(\Box\circ\Box)={}&"
        + trace_prefix
        + r"\!\left(\Delta\circ\Delta-\Delta\circ\bar\Delta"
        + r"-\bar\Delta\circ\Delta+\bar\Delta\circ\bar\Delta\right)"
        + r"\end{aligned}"
    )


def main_box_summands_latex(*, stem: str, coordinate_index: str) -> list[tuple[int, str]]:
    """Return the eight explicit summands of Box=Delta-barDelta.

    ``stem`` keeps the dummy Lorentz indices of the outer and inner operators
    disjoint when the two operators are composed.  The returned signs already
    include the minus sign in front of every summand of barDelta.
    """
    q = stem
    bar_q = rf"\bar {stem}"
    c = coordinate_index
    return [
        (1, rf"\mathcal D_{{{q}}}\mathcal D^{{{q}}}"),
        (
            1,
            rf"\left(\mathfrak R_{{[{q}_1{q}_2]}}"
            rf"-\Gamma^{{{c}}}{{}}_{{{q}_1{q}_2}}\mathcal D_{{{c}}}\right)"
            rf"G^{{{q}_1{q}_2}}",
        ),
        (
            1,
            rf"\frac14\Gamma_{{{c}{q}_1{q}_2}}\Gamma^{{{c}}}{{}}_{{{q}_3{q}_4}}"
            rf"G^{{{q}_1{q}_2}}G^{{{q}_3{q}_4}}",
        ),
        (
            1,
            rf"\frac12\mathfrak R_{{{bar_q}_1{bar_q}_2{q}_3{q}_4}}"
            rf"\bar G^{{{bar_q}_1{bar_q}_2}}G^{{{q}_3{q}_4}}",
        ),
        (-1, rf"\mathcal D_{{{bar_q}}}\mathcal D^{{{bar_q}}}"),
        (
            -1,
            rf"\left(\mathfrak R_{{[{bar_q}_1{bar_q}_2]}}"
            rf"-\Gamma^{{{c}}}{{}}_{{{bar_q}_1{bar_q}_2}}\mathcal D_{{{c}}}\right)"
            rf"\bar G^{{{bar_q}_1{bar_q}_2}}",
        ),
        (
            -1,
            rf"\frac14\Gamma_{{{c}{bar_q}_1{bar_q}_2}}"
            rf"\Gamma^{{{c}}}{{}}_{{{bar_q}_3{bar_q}_4}}"
            rf"\bar G^{{{bar_q}_1{bar_q}_2}}\bar G^{{{bar_q}_3{bar_q}_4}}",
        ),
        (
            -1,
            rf"\frac12\mathfrak R_{{{q}_1{q}_2{bar_q}_3{bar_q}_4}}"
            rf"G^{{{q}_1{q}_2}}\bar G^{{{bar_q}_3{bar_q}_4}}",
        ),
    ]


def main_n2_ordered_terms(field) -> list[tuple[int, str]]:
    """Expand all 8 x 8 ordered compositions without evaluating their action.

    This is deliberately an operator-level expansion.  Keeping ``circ`` is
    essential: by main.pdf equation (2.5), the outer total generator also acts
    on free Lorentz labels carried by the inner operator.
    """
    del field  # The operator terms are universal; only the trace indices vary.
    outer = main_box_summands_latex(stem="q", coordinate_index="B")
    inner = main_box_summands_latex(stem="p", coordinate_index="C")
    return [
        (
            outer_sign * inner_sign,
            rf"\Bigl({outer_body}\Bigr)\circ\Bigl({inner_body}\Bigr)",
        )
        for outer_sign, outer_body in outer
        for inner_sign, inner_body in inner
    ]


def main_n2_full_expansion_latex(field) -> str:
    """One deterministic, MathJax-safe equation containing all 64 terms."""
    terms = main_n2_ordered_terms(field)
    lhs = main_trace_prefix_latex(field) + r"(\Box\circ\Box)"
    trace_prefix = main_trace_prefix_latex(field)
    lines = []
    for index, (sign, body) in enumerate(terms):
        if index == 0:
            prefix = "-" if sign < 0 else ""
            lines.append(rf"{lhs}&={trace_prefix}\Bigl[{prefix}{body}")
        else:
            prefix = r"{}-" if sign < 0 else r"{}+"
            lines.append(rf"&\quad {prefix}{body}")
    lines[-1] += r"\Bigr]"
    return r"\begin{aligned}" + r"\\[0.65em]".join(lines) + r"\end{aligned}"


def main_pair_latex(label: str) -> str:
    """Translate an internal antisymmetric-pair label to main.pdf indices."""
    match = trace.re.fullmatch(r"([IJ])(\d+)", label)
    if match is None:
        raise ValueError(f"Unsupported generator-pair label: {label}")
    sector, number_text = match.groups()
    number = int(number_text)
    first, second = 2 * number - 1, 2 * number
    if sector == "I":
        return rf"q_{first}q_{second}"
    return rf"\bar q_{first}\bar q_{second}"


def main_index_latex(value: str, coordinate_map: dict[str, str] | None = None) -> str:
    if coordinate_map is not None and value in coordinate_map:
        return coordinate_map[value]
    return trace.latex_index(value)


def main_coordinate_map(monomial) -> dict[str, str]:
    """Compact engine-generated dummy coordinates within one primitive term."""
    candidates = []
    for factor in monomial:
        candidates.extend(
            value for value in factor.indices
            if trace.re.fullmatch(r"[a-z]+\d+", value)
        )
        candidates.extend(
            value for value in factor.derivs
            if trace.re.fullmatch(r"[a-z]+\d+", value)
        )
    unique = list(dict.fromkeys(candidates))
    symbols = list("MNPQRSUVWXYZ")
    if len(unique) > len(symbols):
        raise ValueError("Too many primitive dummy coordinate indices")
    return dict(zip(unique, symbols))


def main_factor_latex(factor, coordinate_map: dict[str, str] | None = None) -> str:
    """Render one primitive AST factor without any audit-only shorthand."""
    idx = [main_index_latex(value, coordinate_map) for value in factor.indices]
    kind = factor.kind
    if kind == "H":
        base = rf"\mathcal H^{{{idx[0]}{idx[1]}}}"
    elif kind == "GammaABC":
        base = rf"\Gamma_{{{idx[0]}{idx[1]}}}{{}}^{{{idx[2]}}}"
    elif kind == "GammaLUp":
        base = rf"\Gamma^{{{idx[0]}}}{{}}_{{{main_pair_latex(factor.indices[1])}}}"
    elif kind == "GammaRUp":
        base = rf"\Gamma^{{{idx[0]}}}{{}}_{{{main_pair_latex(factor.indices[1])}}}"
    elif kind == "GammaLDown":
        base = rf"\Gamma_{{{idx[0]}{main_pair_latex(factor.indices[1])}}}"
    elif kind == "GammaRDown":
        base = rf"\Gamma_{{{idx[0]}{main_pair_latex(factor.indices[1])}}}"
    elif kind == "Phi":
        base = rf"\Phi_{{{idx[0]}{main_pair_latex(factor.indices[1])}}}"
    elif kind == "BarPhi":
        base = rf"\bar\Phi_{{{idx[0]}{main_pair_latex(factor.indices[1])}}}"
    elif kind == "RicL":
        base = rf"\mathfrak R_{{[{main_pair_latex(factor.indices[0])}]}}"
    elif kind == "RicR":
        base = rf"\mathfrak R_{{[{main_pair_latex(factor.indices[0])}]}}"
    elif kind == "MixRL":
        base = rf"\mathfrak R_{{{main_pair_latex(factor.indices[0])}{main_pair_latex(factor.indices[1])}}}"
    elif kind == "MixLR":
        base = rf"\mathfrak R_{{{main_pair_latex(factor.indices[0])}{main_pair_latex(factor.indices[1])}}}"
    else:
        raise ValueError(f"Unsupported primitive factor: {kind}")
    derivatives = "".join(
        rf"\partial_{{{main_index_latex(value, coordinate_map)}}}" for value in factor.derivs
    )
    return derivatives + base


def main_t_gamma_trace_latex(word: tuple[tuple[str, str], ...]) -> tuple[Fraction, list[str]] | None:
    """Specialize total generators to the T endomorphism of E.9--E.11.

    Left generators multiply T from the left in ledger order.  Barred
    generators multiply from the right, so their gamma word is reversed.
    A sector containing exactly one generator has zero spinor trace.
    """
    left_labels = [label for sector, label in word if sector == "L"]
    right_labels = [label for sector, label in word if sector == "R"]
    if len(left_labels) == 1 or len(right_labels) == 1:
        return None

    scale = Fraction((-1) ** len(right_labels), 2 ** (len(left_labels) + len(right_labels)))
    factors = []
    if left_labels:
        gamma_word = r"\,".join(
            rf"\gamma^{{{main_pair_latex(label)}}}" for label in left_labels
        )
        factors.append(rf"\operatorname{{tr}}_{{\alpha}}\!\left({gamma_word}\right)")
    else:
        scale *= trace.D_SPIN
    if right_labels:
        gamma_word = r"\,".join(
            rf"\bar\gamma^{{{main_pair_latex(label)}}}"
            for label in reversed(right_labels)
        )
        factors.append(rf"\operatorname{{tr}}_{{\bar\alpha}}\!\left({gamma_word}\right)")
    else:
        scale *= trace.D_SPIN
    return scale, factors


def main_t_n2_symbolic_gamma_terms() -> list[tuple[int, Fraction, str]]:
    """Return T's 329 pre-Clifford symbolic-gamma audit rows."""
    rendered = []
    for term in trace.generate_exact_terms():
        gamma_trace = main_t_gamma_trace_latex(term.word)
        if gamma_trace is None:
            continue
        generator_scale, gamma_factors = gamma_trace
        ordered_monomials = sorted(
            term.coefficient.terms.items(),
            key=lambda item: tuple(factor.text() for factor in item[0]),
        )
        for monomial, coefficient in ordered_monomials:
            coordinate_map = main_coordinate_map(monomial)
            factors = [main_factor_latex(factor, coordinate_map) for factor in monomial]
            factors.extend(gamma_factors)
            factors.extend(
                rf"\partial_{{{trace.latex_index(index)}}}"
                for index in term.derivative_indices
            )
            rendered.append(
                (
                    term.derivative_order,
                    coefficient * generator_scale,
                    r"\,".join(factors) if factors else "1",
                )
            )
    return rendered


def main_t_n2_primitive_terms() -> list[tuple[int, Fraction, str]]:
    """Return T's fully absorbed D=10 Einstein-contraction rows."""
    return main_raw_field_n2_primitive_terms(trace.resolve_field("T"))


def main_t_n2_full_trace_latex() -> str:
    """Render T's Einstein-contracted rows as one complete sum."""
    terms = main_t_n2_primitive_terms()
    lhs = main_trace_prefix_latex(trace.resolve_field("T")) + r"(\Box\circ\Box)"
    lines = []
    for index, (_derivative_order, coefficient, body) in enumerate(terms):
        magnitude = abs(coefficient)
        scalar = "" if magnitude == 1 else trace.frac_latex(magnitude) + r"\,"
        if index == 0:
            sign = "-" if coefficient < 0 else ""
            lines.append(rf"{lhs}&={sign}{scalar}{body}")
        else:
            sign = r"{}-" if coefficient < 0 else r"{}+"
            lines.append(rf"&\quad {sign}{scalar}{body}")
    return r"\begin{aligned}" + r"\\[0.65em]".join(lines) + r"\end{aligned}"


def main_phi_n2_primitive_terms() -> list[tuple[int, Fraction, str]]:
    """Return the exact scalar n=2 trace after expanding every covariant D.

    The scalar representation has no spinor slots, so both total generators
    annihilate ``phi``.  Consequently an exact composition term contributes
    if and only if its ordered generator word is empty.  Unlike the generic
    8 x 8 operator display, these rows are therefore a fully evaluated
    finite-dimensional trace; product-rule derivatives of H and Gamma are
    retained as separate ordinary-partial terms.
    """
    rendered = []
    for term in trace.generate_exact_terms():
        if term.word:
            continue
        ordered_monomials = sorted(
            term.coefficient.terms.items(),
            key=lambda item: tuple(factor.text() for factor in item[0]),
        )
        for monomial, coefficient in ordered_monomials:
            coordinate_map = main_coordinate_map(monomial)
            factors = [main_factor_latex(factor, coordinate_map) for factor in monomial]
            factors.extend(
                rf"\partial_{{{trace.latex_index(index)}}}"
                for index in term.derivative_indices
            )
            rendered.append(
                (
                    term.derivative_order,
                    coefficient,
                    r"\,".join(factors) if factors else "1",
                )
            )
    return rendered


def main_phi_n2_full_trace_latex() -> str:
    """Render the scalar's complete 14-term ordinary-partial trace."""
    terms = main_phi_n2_primitive_terms()
    lhs = main_trace_prefix_latex(trace.resolve_field("phi")) + r"(\Box\circ\Box)"
    lines = []
    for index, (_derivative_order, coefficient, body) in enumerate(terms):
        magnitude = abs(coefficient)
        scalar = "" if magnitude == 1 else trace.frac_latex(magnitude) + r"\,"
        if index == 0:
            sign = "-" if coefficient < 0 else ""
            lines.append(rf"{lhs}&={sign}{scalar}{body}")
        else:
            sign = r"{}-" if coefficient < 0 else r"{}+"
            lines.append(rf"&\quad {sign}{scalar}{body}")
    return r"\begin{aligned}" + r"\\[0.65em]".join(lines) + r"\end{aligned}"


def main_phi_box_latex() -> str:
    """Weight-zero scalar specialization of Box in ordinary derivatives."""
    return (
        r"\left.\Box\right|_{\mathbf 1}="
        r"\mathcal H^{AB}\partial_A\partial_B"
        r"+\mathcal H^{AB}\Gamma_{AB}{}^{C}\partial_C"
    )


def main_slot_trace_expansion(
    word: tuple[tuple[str, str], ...],
    a: int,
    b: int,
) -> list[
    tuple[
        Fraction,
        tuple[tuple[str, ...], ...],
        tuple[tuple[str, ...], ...],
    ]
]:
    """Trace an ordered total-generator word over raw tensor slots.

    The word is interpreted after the selected field's single-Box
    endomorphism has been specialized with main.pdf equations (2.3)--(2.5).
    In particular, the same-sector symmetric connection contraction has
    already cancelled the label-action correction before the two Box
    endomorphisms are ordinarily composed.  The remaining ordered gamma word
    itself preserves the sequential action of equation (2.5).

    A left generator chooses one of the ``a`` upper unbarred spinor slots;
    a barred generator chooses one of the ``b`` lower barred slots.  Empty
    slots contribute ``D_SPIN``.  A slot hit exactly once vanishes by the
    single-gamma trace.  Left gamma words retain ledger order, while each
    right-acting barred word is reversed independently.  Slot labels are
    dummy trace indices, so signatures related only by a slot permutation
    are canonically sorted and combined.
    """
    if any(sector == "L" for sector, _label in word) and a == 0:
        return []
    if any(sector == "R" for sector, _label in word) and b == 0:
        return []

    choices = [
        range(a) if sector == "L" else range(b)
        for sector, _label in word
    ]
    assignments = product(*choices) if choices else [()]
    expanded = defaultdict(Fraction)
    right_count = sum(sector == "R" for sector, _label in word)
    generator_scale = Fraction((-1) ** right_count, 2 ** len(word))

    for assignment in assignments:
        left_slots = [[] for _index in range(a)]
        right_slots = [[] for _index in range(b)]
        for (sector, label), slot in zip(word, assignment):
            (left_slots if sector == "L" else right_slots)[slot].append(label)

        if any(len(slot_word) == 1 for slot_word in left_slots + right_slots):
            continue

        unused = sum(not slot_word for slot_word in left_slots + right_slots)
        left_words = tuple(
            sorted(tuple(slot_word) for slot_word in left_slots if slot_word)
        )
        right_words = tuple(
            sorted(tuple(reversed(slot_word)) for slot_word in right_slots if slot_word)
        )
        expanded[(left_words, right_words)] += (
            generator_scale * trace.D_SPIN ** unused
        )

    return [
        (coefficient, left_words, right_words)
        for (left_words, right_words), coefficient in sorted(expanded.items())
        if coefficient
    ]


@lru_cache(maxsize=None)
def _main_ordinary_gamma_pairings(
    atoms: tuple[int, ...],
) -> tuple[tuple[tuple[tuple[int, int], ...], Fraction], ...]:
    """D=10 chiral trace of an ordinary even gamma word.

    The Clifford normalization is fixed by main.pdf (B.9)--(B.10).  For at
    most eight ordinary gamma matrices, the chirality insertion cannot
    produce the ten-index epsilon tensor.  The 16-dimensional chiral trace is
    therefore the ordinary Wick pairing polynomial with base trace 16.
    """
    if not atoms:
        return (((), Fraction(trace.D_SPIN)),)
    if len(atoms) % 2:
        return ()

    first = atoms[0]
    expanded = defaultdict(Fraction)
    for partner_position in range(1, len(atoms)):
        partner = atoms[partner_position]
        sign = -1 if partner_position % 2 == 0 else 1
        remaining = atoms[1:partner_position] + atoms[partner_position + 1:]
        metric = tuple(sorted((first, partner)))
        for monomial, coefficient in _main_ordinary_gamma_pairings(remaining):
            expanded[tuple(sorted((metric,) + monomial))] += sign * coefficient
    return tuple(
        (monomial, coefficient)
        for monomial, coefficient in sorted(expanded.items())
        if coefficient
    )


def _main_bivector_atoms(label: str, sector: str) -> tuple[int, int]:
    match = trace.re.fullmatch(r"([IJ])(\d+)", label)
    if match is None:
        raise ValueError(f"Unsupported generator-pair label: {label}")
    prefix, number_text = match.groups()
    expected_prefix = "I" if sector == "L" else "J"
    if prefix != expected_prefix:
        raise ValueError(f"Generator sector mismatch: {sector} with {label}")
    number = int(number_text)
    return 2 * number - 1, 2 * number


@lru_cache(maxsize=None)
def main_bivector_trace_eta_terms(
    labels: tuple[str, ...],
    sector: str,
) -> tuple[tuple[Fraction, tuple[tuple[str, int, int], ...]], ...]:
    """Expand one chiral trace of 2--4 bivectors into eta monomials.

    Equations (B.9)--(B.10) fix the bivector normalization.  Expanding each
    bivector's two orientations and applying the chiral Wick trace yields 2,
    8, and 60 nonzero eta monomials for word lengths 2, 3, and 4.
    """
    if len(labels) == 1:
        return ()
    if not 2 <= len(labels) <= 4:
        raise ValueError(f"Unsupported bivector trace length: {len(labels)}")
    if sector not in {"L", "R"}:
        raise ValueError(f"Unsupported Lorentz sector: {sector}")

    expanded = defaultdict(Fraction)
    for orientations in product((0, 1), repeat=len(labels)):
        atoms = []
        orientation_sign = 1
        for label, reversed_orientation in zip(labels, orientations):
            pair = _main_bivector_atoms(label, sector)
            if reversed_orientation:
                pair = tuple(reversed(pair))
                orientation_sign *= -1
            atoms.extend(pair)
        bivector_scale = Fraction(orientation_sign, 2 ** len(labels))
        for monomial, coefficient in _main_ordinary_gamma_pairings(tuple(atoms)):
            tagged = tuple((sector, first, second) for first, second in monomial)
            expanded[tagged] += bivector_scale * coefficient
    return tuple(
        (coefficient, monomial)
        for monomial, coefficient in sorted(expanded.items())
        if coefficient
    )


@lru_cache(maxsize=None)
def main_slot_raw_eta_expansion(
    left_words: tuple[tuple[str, ...], ...],
    right_words: tuple[tuple[str, ...], ...],
) -> tuple[tuple[Fraction, tuple[tuple[str, int, int], ...]], ...]:
    """Multiply and fully distribute occupied-slot traces before pair flips."""
    expanded = {(): Fraction(1)}
    trace_words = [
        (labels, "L") for labels in left_words
    ] + [
        (labels, "R") for labels in right_words
    ]
    for labels, sector in trace_words:
        following = defaultdict(Fraction)
        for first_monomial, first_coefficient in expanded.items():
            for second_coefficient, second_monomial in main_bivector_trace_eta_terms(
                labels, sector
            ):
                monomial = tuple(sorted(first_monomial + second_monomial))
                following[monomial] += first_coefficient * second_coefficient
        expanded = {
            monomial: coefficient
            for monomial, coefficient in following.items()
            if coefficient
        }
    return tuple(
        (coefficient, monomial)
        for monomial, coefficient in sorted(expanded.items())
        if coefficient
    )


_PAIR_FACTOR_SLOTS = {
    ("GammaLUp", 1): "L",
    ("GammaRUp", 1): "R",
    ("GammaLDown", 1): "L",
    ("GammaRDown", 1): "R",
    ("Phi", 1): "L",
    ("BarPhi", 1): "R",
    ("RicL", 0): "L",
    ("RicR", 0): "R",
    ("MixRL", 0): "R",
    ("MixRL", 1): "L",
    ("MixLR", 0): "L",
    ("MixLR", 1): "R",
}


def _main_validate_pair_flip_monomial(
    monomial,
    word: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, int], ...]:
    """Fail closed unless every word label has one antisymmetric AST slot."""
    expected = {label: sector for sector, label in word}
    if len(expected) != len(word):
        raise ValueError("Generator labels must be unique inside one exact word")
    occurrences = defaultdict(list)
    for factor in monomial:
        for index_position, value in enumerate(factor.indices):
            match = trace.re.fullmatch(r"([IJ])(\d+)", value)
            if match is None:
                continue
            prefix, _number_text = match.groups()
            sector = "L" if prefix == "I" else "R"
            allowed_sector = _PAIR_FACTOR_SLOTS.get((factor.kind, index_position))
            if allowed_sector != sector:
                raise ValueError(
                    f"Pair label {value} occurs in a non-antisymmetric slot: "
                    f"{factor.kind}[{index_position}]"
                )
            if value not in expected or expected[value] != sector:
                raise ValueError(f"Unexpected pair label {value} in coefficient monomial")
            occurrences[value].append((factor.kind, index_position))
    for label, sector in expected.items():
        if len(occurrences[label]) != 1:
            raise ValueError(
                f"Pair-flip requires exactly one antisymmetric occurrence of {label}; "
                f"found {len(occurrences[label])}"
            )
    if set(occurrences) != set(expected):
        raise ValueError("Coefficient monomial contains an unmatched pair label")
    return tuple(
        sorted(
            (sector, int(label[1:]))
            for label, sector in expected.items()
        )
    )


@lru_cache(maxsize=None)
def _main_pair_flip_canonical(
    eta_monomial: tuple[tuple[str, int, int], ...],
    vertices: tuple[tuple[str, int], ...],
) -> tuple[tuple[tuple[str, int, int], ...], int]:
    """Canonicalize dummy pair orientations with the background flip sign."""
    expected_atoms = {
        (sector, atom)
        for sector, number in vertices
        for atom in (2 * number - 1, 2 * number)
    }
    actual_atoms = []
    for sector, first, second in eta_monomial:
        actual_atoms.extend(((sector, first), (sector, second)))
    if len(actual_atoms) != len(expected_atoms) or set(actual_atoms) != expected_atoms:
        raise ValueError("Eta monomial does not contain each generator-pair atom once")

    candidates = []
    for flips in product((0, 1), repeat=len(vertices)):
        flipped_vertices = {
            vertex for vertex, enabled in zip(vertices, flips) if enabled
        }

        def flip_atom(sector: str, atom: int) -> int:
            vertex = (sector, (atom + 1) // 2)
            if vertex not in flipped_vertices:
                return atom
            return atom + 1 if atom % 2 else atom - 1

        transformed = []
        for sector, first, second in eta_monomial:
            first = flip_atom(sector, first)
            second = flip_atom(sector, second)
            transformed.append((sector, *sorted((first, second))))
        candidates.append((tuple(sorted(transformed)), (-1) ** sum(flips)))

    canonical = min(monomial for monomial, _sign in candidates)
    signs = {sign for monomial, sign in candidates if monomial == canonical}
    if len(signs) != 1:
        raise ValueError("Odd pair-flip stabilizer makes this contraction vanish")
    return canonical, signs.pop()


def main_slot_eta_expansion(
    left_words: tuple[tuple[str, ...], ...],
    right_words: tuple[tuple[str, ...], ...],
    word: tuple[tuple[str, str], ...],
    monomial,
) -> tuple[tuple[Fraction, tuple[tuple[str, int, int], ...]], ...]:
    """Canonicalize one *background-contracted* slot-signature polynomial.

    This reduction is not an identity for a bare Clifford trace: the latter
    remains the 2/8/60-term polynomial.  Pair flips become equivalent only for
    the whole coefficient-times-trace monomial after the AST check proves that
    every generator label occurs in exactly one antisymmetric background-pair
    slot; ``background_sign`` accounts for that factor's sign.
    """
    vertices = _main_validate_pair_flip_monomial(monomial, word)
    traced_labels = [label for labels in left_words for label in labels]
    traced_labels.extend(label for labels in right_words for label in labels)
    if sorted(traced_labels) != sorted(label for _sector, label in word):
        raise ValueError("Slot trace signature does not contain the exact generator word")

    expanded = defaultdict(Fraction)
    for coefficient, eta_monomial in main_slot_raw_eta_expansion(
        left_words, right_words
    ):
        canonical, background_sign = _main_pair_flip_canonical(
            eta_monomial, vertices
        )
        expanded[canonical] += coefficient * background_sign
    return tuple(
        (coefficient, eta_monomial)
        for eta_monomial, coefficient in sorted(expanded.items())
        if coefficient
    )


def main_eta_factor_latex(metric: tuple[str, int, int]) -> str:
    """Render one main.pdf local-Lorentz metric contraction for audits only."""
    sector, first, second = metric
    if sector == "L":
        return rf"\eta^{{q_{first}q_{second}}}"
    if sector == "R":
        return rf"\bar\eta^{{\bar q_{first}\bar q_{second}}}"
    raise ValueError(f"Unsupported Lorentz sector: {sector}")


_MAIN_LOCAL_DUMMY_NAMES = ("p", "q", "r", "s")


def _main_pair_occurrences(monomial, word) -> dict[str, tuple[int, int, str]]:
    """Locate every generator pair in its unique antisymmetric factor slot."""
    _main_validate_pair_flip_monomial(monomial, word)
    expected = {label: sector for sector, label in word}
    occurrences = {}
    for factor_position, factor in enumerate(monomial):
        for index_position, value in enumerate(factor.indices):
            if value not in expected:
                continue
            if value in occurrences:
                raise ValueError(f"Duplicate pair occurrence after validation: {value}")
            occurrences[value] = (factor_position, index_position, expected[value])
    if set(occurrences) != set(expected):
        raise ValueError("Could not locate every validated pair occurrence")
    return occurrences


@lru_cache(maxsize=None)
def main_absorb_eta_contraction(
    monomial,
    word: tuple[tuple[str, str], ...],
    eta_monomial: tuple[tuple[str, int, int], ...],
) -> tuple[
    tuple[tuple[str, tuple[tuple[str, int, str], ...]], ...],
    tuple[tuple[str, tuple[tuple[str, int, str], ...]], ...],
]:
    """Absorb a metric perfect matching into background Lorentz indices.

    The returned immutable key is also the rendering assignment.  Each local
    atom is kept in its original antisymmetric-pair endpoint: endpoint order is
    never exchanged here, so this step introduces no extra antisymmetry sign.
    For a canonical edge ``(sector, first, second)``, the smaller atom is the
    lower occurrence and the larger atom is the upper occurrence.  Thus every
    dummy appears exactly once down and once up and no explicit eta remains.

    This function deliberately keeps generator-labelled contraction graphs.
    It therefore permits exact coalescing inside one exact word/background
    monomial, but does not assume cross-block tensor automorphisms.
    """
    occurrences = _main_pair_occurrences(monomial, word)
    atom_owners = {}
    for sector, label in word:
        match = trace.re.fullmatch(r"([IJ])(\d+)", label)
        if match is None:
            raise ValueError(f"Unsupported generator-pair label: {label}")
        expected_prefix = "I" if sector == "L" else "J"
        prefix, number_text = match.groups()
        if prefix != expected_prefix:
            raise ValueError(f"Generator sector mismatch: {sector} with {label}")
        number = int(number_text)
        for endpoint, atom in enumerate((2 * number - 1, 2 * number)):
            atom_key = (sector, atom)
            if atom_key in atom_owners:
                raise ValueError(f"Duplicate local-Lorentz atom: {atom_key}")
            atom_owners[atom_key] = (label, endpoint)

    expected_atoms = set(atom_owners)
    actual_atoms = []
    sorted_edges = tuple(sorted(eta_monomial))
    for sector, first, second in sorted_edges:
        if sector not in {"L", "R"} or first >= second:
            raise ValueError(f"Non-canonical local metric edge: {(sector, first, second)}")
        actual_atoms.extend(((sector, first), (sector, second)))
    if len(actual_atoms) != len(expected_atoms) or set(actual_atoms) != expected_atoms:
        raise ValueError("Metric matching does not contain every local atom exactly once")
    if len(set(actual_atoms)) != len(actual_atoms):
        raise ValueError("Metric matching repeats a local atom")

    assignments = {label: [None, None] for _sector, label in word}
    sector_edge_counts = defaultdict(int)
    for sector, first, second in sorted_edges:
        first_owner = atom_owners[(sector, first)]
        second_owner = atom_owners[(sector, second)]
        if first_owner[0] == second_owner[0]:
            raise ValueError(
                "A symmetric metric may not self-contract one antisymmetric pair"
            )
        edge_number = sector_edge_counts[sector]
        sector_edge_counts[sector] += 1
        if edge_number >= len(_MAIN_LOCAL_DUMMY_NAMES):
            raise ValueError("Too many local-Lorentz dummy contractions")
        first_label, first_endpoint = first_owner
        second_label, second_endpoint = second_owner
        assignments[first_label][first_endpoint] = (sector, edge_number, "down")
        assignments[second_label][second_endpoint] = (sector, edge_number, "up")

    for label, endpoints in assignments.items():
        if len(endpoints) != 2 or any(endpoint is None for endpoint in endpoints):
            raise ValueError(f"Incomplete Lorentz contraction assignment for {label}")

    flattened = [endpoint for endpoints in assignments.values() for endpoint in endpoints]
    dummy_variances = defaultdict(list)
    for sector, edge_number, variance in flattened:
        dummy_variances[(sector, edge_number)].append(variance)
    if any(sorted(variances) != ["down", "up"] for variances in dummy_variances.values()):
        raise ValueError("Every absorbed metric must produce one lower and one upper dummy")
    if 2 * len(sorted_edges) != len(flattened):
        raise ValueError("Absorbed metric and pair-endpoint counts disagree")

    occurrence_order = sorted(
        occurrences,
        key=lambda label: (*occurrences[label][:2], label),
    )
    key = tuple(
        (label, tuple(assignments[label]))
        for label in occurrence_order
    )
    return key, key


def _main_local_dummy_latex(endpoint: tuple[str, int, str]) -> tuple[str, str]:
    sector, edge_number, variance = endpoint
    if sector not in {"L", "R"}:
        raise ValueError(f"Unsupported Lorentz sector: {sector}")
    if not 0 <= edge_number < len(_MAIN_LOCAL_DUMMY_NAMES):
        raise ValueError(f"Unsupported Lorentz dummy number: {edge_number}")
    if variance not in {"down", "up"}:
        raise ValueError(f"Unsupported Lorentz variance: {variance}")
    symbol = _MAIN_LOCAL_DUMMY_NAMES[edge_number]
    if sector == "R":
        symbol = rf"\bar {symbol}"
    return symbol, variance


def _main_tensor_with_indices_latex(
    base: str,
    slots: list[tuple[str, str]],
) -> str:
    """Render ordered tensor slots, grouping only adjacent equal variances."""
    if any(variance not in {"down", "up"} for _index, variance in slots):
        raise ValueError("Tensor index variance must be 'down' or 'up'")
    groups = []
    for index, variance in slots:
        if groups and groups[-1][0] == variance:
            groups[-1][1].append(index)
        else:
            groups.append((variance, [index]))
    rendered = base
    for group_position, (variance, indices) in enumerate(groups):
        if group_position:
            rendered += "{}"
        script = "^" if variance == "up" else "_"
        rendered += script + "{" + "".join(indices) + "}"
    return rendered


def _main_antisymmetric_pair_latex(
    base: str,
    pair_slots: tuple[tuple[str, str], tuple[str, str]],
) -> str:
    """Render one ordered antisymmetric pair with arbitrary endpoint variance.

    Brackets are retained only when both endpoints have the same variance.
    After raising one endpoint, a mixed object is an endomorphism; writing an
    antisymmetrization bracket across different heights would be ambiguous.
    """
    (first, first_variance), (second, second_variance) = pair_slots
    if first_variance == second_variance == "down":
        return rf"{base}_{{[{first}{second}]}}"
    if first_variance == second_variance == "up":
        return rf"{base}^{{[{first}{second}]}}"
    if first_variance == "down" and second_variance == "up":
        return rf"{base}_{{{first}}}{{}}^{{{second}}}"
    if first_variance == "up" and second_variance == "down":
        return rf"{base}^{{{first}}}{{}}_{{{second}}}"
    raise ValueError("Unsupported antisymmetric-pair variance")


def main_contracted_factor_latex(
    factor,
    coordinate_map: dict[str, str],
    contraction_assignment: tuple[
        tuple[str, tuple[tuple[str, int, str], ...]], ...
    ],
) -> str:
    """Render one factor after all local metrics have been absorbed."""
    pair_assignments = dict(contraction_assignment)

    def pair_slots(label: str) -> tuple[tuple[str, str], tuple[str, str]]:
        endpoints = pair_assignments.get(label)
        if endpoints is None or len(endpoints) != 2:
            raise ValueError(f"Missing absorbed pair assignment for {label}")
        return tuple(_main_local_dummy_latex(endpoint) for endpoint in endpoints)

    idx = [main_index_latex(value, coordinate_map) for value in factor.indices]
    kind = factor.kind
    if kind == "H":
        base = _main_tensor_with_indices_latex(
            r"\mathcal H", [(idx[0], "up"), (idx[1], "up")]
        )
    elif kind == "GammaABC":
        base = _main_tensor_with_indices_latex(
            r"\Gamma",
            [(idx[0], "down"), (idx[1], "down"), (idx[2], "up")],
        )
    elif kind in {"GammaLUp", "GammaRUp"}:
        base = _main_tensor_with_indices_latex(
            r"\Gamma", [(idx[0], "up"), *pair_slots(factor.indices[1])]
        )
    elif kind in {"GammaLDown", "GammaRDown"}:
        base = _main_tensor_with_indices_latex(
            r"\Gamma", [(idx[0], "down"), *pair_slots(factor.indices[1])]
        )
    elif kind == "Phi":
        base = _main_tensor_with_indices_latex(
            r"\Phi", [(idx[0], "down"), *pair_slots(factor.indices[1])]
        )
    elif kind == "BarPhi":
        base = _main_tensor_with_indices_latex(
            r"\bar\Phi", [(idx[0], "down"), *pair_slots(factor.indices[1])]
        )
    elif kind in {"RicL", "RicR"}:
        base = _main_antisymmetric_pair_latex(
            r"\mathfrak R", pair_slots(factor.indices[0])
        )
    elif kind in {"MixRL", "MixLR"}:
        base = _main_tensor_with_indices_latex(
            r"\mathfrak R",
            [
                *pair_slots(factor.indices[0]),
                *pair_slots(factor.indices[1]),
            ],
        )
    else:
        raise ValueError(f"Unsupported primitive factor: {kind}")
    derivatives = "".join(
        rf"\partial_{{{main_index_latex(value, coordinate_map)}}}"
        for value in factor.derivs
    )
    return derivatives + base


def _main_contracted_factor_key(
    factor,
    coordinate_map: dict[str, str],
    contraction_assignment: tuple[
        tuple[str, tuple[tuple[str, int, str], ...]], ...
    ],
):
    """Return a renderer-independent key for one absorbed tensor factor."""
    pair_assignments = dict(contraction_assignment)
    indices = []
    for value in factor.indices:
        if value in pair_assignments:
            indices.append(("local-pair", pair_assignments[value]))
        else:
            if trace.re.fullmatch(r"[IJ]\d+", value):
                raise ValueError(f"Unassigned generator-pair index in factor key: {value}")
            indices.append(("coordinate", coordinate_map.get(value, value)))
    derivatives = tuple(
        sorted(coordinate_map.get(value, value) for value in factor.derivs)
    )
    return factor.kind, tuple(indices), derivatives


def main_contracted_body_key(
    derivative_order: int,
    monomial,
    coordinate_map: dict[str, str],
    contraction_assignment: tuple[
        tuple[str, tuple[tuple[str, int, str], ...]], ...
    ],
    derivative_indices: tuple[str, ...],
):
    """Canonical full-AST key used for safe cross-exact-term coalescing.

    Factor multiplication is commutative in the coefficient expression, so
    factor keys are sorted.  No symmetry of H, Gamma, Phi, or curvature and no
    reversal/automorphism of a contraction graph is assumed.
    """
    factor_keys = tuple(
        sorted(
            _main_contracted_factor_key(
                factor, coordinate_map, contraction_assignment
            )
            for factor in monomial
        )
    )
    external_derivatives = tuple(
        coordinate_map.get(value, value) for value in derivative_indices
    )
    return derivative_order, factor_keys, external_derivatives


def main_contracted_body_latex(
    monomial,
    coordinate_map: dict[str, str],
    contraction_assignment: tuple[
        tuple[str, tuple[tuple[str, int, str], ...]], ...
    ],
    derivative_indices: tuple[str, ...],
) -> str:
    """Render the same ordered slots encoded by ``main_contracted_body_key``."""
    ordered_factors = sorted(
        monomial,
        key=lambda factor: _main_contracted_factor_key(
            factor, coordinate_map, contraction_assignment
        ),
    )
    factors = [
        main_contracted_factor_latex(
            factor, coordinate_map, contraction_assignment
        )
        for factor in ordered_factors
    ]
    factors.extend(
        rf"\partial_{{{main_index_latex(index, coordinate_map)}}}"
        for index in derivative_indices
    )
    return r"\,".join(factors) if factors else "1"


def main_raw_field_n2_provenance_terms(field) -> list[tuple[int, Fraction, str]]:
    """Expand an n=2 raw tensor trace into Einstein-contracted provenance rows.

    Here ``exact`` has the sequential-action meaning of main.pdf equations
    (2.3)--(2.5): each single Box is first specialized to the raw-field
    endomorphism, including the label-action cancellation in symmetric
    same-sector connection contractions, and only then are the resulting
    ordinary differential operators composed.  This is not a naive
    replacement of the ordered total-generator action by a matrix word.

    Ordered blocks and their product-rule monomials remain separate ledger
    rows.  Only dummy tensor-slot permutations inside one generator word are
    combined.  Every chiral Clifford trace is first fully distributed into
    local metric pairings, and those metrics are then absorbed into the unique
    antisymmetric background-pair slots as explicit upper/lower Einstein dummy
    indices.  The result contains no covariant-D, total-generator, gamma,
    explicit local metric, or spinor-trace shorthand.
    """
    _name, a, b, _weight = field
    rendered = []
    for term in trace.generate_exact_terms():
        slot_traces = main_slot_trace_expansion(term.word, a, b)
        if not slot_traces:
            continue
        ordered_monomials = sorted(
            term.coefficient.terms.items(),
            key=lambda item: tuple(factor.text() for factor in item[0]),
        )
        for monomial, coefficient in ordered_monomials:
            coordinate_map = main_coordinate_map(monomial)
            for slot_coefficient, left_words, right_words in slot_traces:
                combined_contractions = defaultdict(Fraction)
                assignments = {}
                for clifford_coefficient, eta_monomial in main_slot_eta_expansion(
                    left_words, right_words, term.word, monomial
                ):
                    contraction_key, contraction_assignment = main_absorb_eta_contraction(
                        monomial, term.word, eta_monomial
                    )
                    combined_contractions[contraction_key] += clifford_coefficient
                    assignments[contraction_key] = contraction_assignment
                for contraction_key, contraction_coefficient in sorted(
                    combined_contractions.items()
                ):
                    if not contraction_coefficient:
                        continue
                    body = main_contracted_body_latex(
                        monomial,
                        coordinate_map,
                        assignments[contraction_key],
                        term.derivative_indices,
                    )
                    rendered.append(
                        (
                            term.derivative_order,
                            coefficient * slot_coefficient * contraction_coefficient,
                            body,
                        )
                    )
    return rendered


def main_raw_field_n2_primitive_terms(field) -> list[tuple[int, Fraction, str]]:
    """Return fully Einstein-contracted rows with exact AST coalescing.

    Slot signatures are combined inside one exact word/background monomial.
    Afterwards, rows from different exact terms are combined only when their
    complete absorbed factor AST and external derivative tuple are identical
    after deterministic dummy renaming and commuting factor-local ordinary
    partial derivatives.
    """
    _name, a, b, _weight = field
    combined_rows = defaultdict(Fraction)
    representative_bodies = {}
    for term in trace.generate_exact_terms():
        slot_traces = main_slot_trace_expansion(term.word, a, b)
        if not slot_traces:
            continue
        ordered_monomials = sorted(
            term.coefficient.terms.items(),
            key=lambda item: tuple(factor.text() for factor in item[0]),
        )
        for monomial, coefficient in ordered_monomials:
            coordinate_map = main_coordinate_map(monomial)
            combined_contractions = defaultdict(Fraction)
            assignments = {}
            for slot_coefficient, left_words, right_words in slot_traces:
                for clifford_coefficient, eta_monomial in main_slot_eta_expansion(
                    left_words, right_words, term.word, monomial
                ):
                    contraction_key, contraction_assignment = main_absorb_eta_contraction(
                        monomial, term.word, eta_monomial
                    )
                    combined_contractions[contraction_key] += (
                        slot_coefficient * clifford_coefficient
                    )
                    assignments[contraction_key] = contraction_assignment
            for contraction_key, trace_coefficient in sorted(
                combined_contractions.items()
            ):
                if not trace_coefficient:
                    continue
                contraction_assignment = assignments[contraction_key]
                row_key = main_contracted_body_key(
                    term.derivative_order,
                    monomial,
                    coordinate_map,
                    contraction_assignment,
                    term.derivative_indices,
                )
                combined_rows[row_key] += coefficient * trace_coefficient
                representative_bodies.setdefault(
                    row_key,
                    main_contracted_body_latex(
                        monomial,
                        coordinate_map,
                        contraction_assignment,
                        term.derivative_indices,
                    )
                )
    return [
        (row_key[0], coefficient, representative_bodies[row_key])
        for row_key, coefficient in combined_rows.items()
        if coefficient
    ]


def main_raw_field_n2_full_trace_latex(field) -> str:
    """Render one selected field's complete Einstein-contracted ledger."""
    terms = main_raw_field_n2_primitive_terms(field)
    lhs = main_trace_prefix_latex(field) + r"(\Box\circ\Box)"
    lines = []
    for index, (_derivative_order, coefficient, body) in enumerate(terms):
        magnitude = abs(coefficient)
        scalar = "" if magnitude == 1 else trace.frac_latex(magnitude) + r"\,"
        if index == 0:
            sign = "-" if coefficient < 0 else ""
            lines.append(rf"{lhs}&={sign}{scalar}{body}")
        else:
            sign = r"{}-" if coefficient < 0 else r"{}+"
            lines.append(rf"&\quad {sign}{scalar}{body}")
    return r"\begin{aligned}" + r"\\[0.65em]".join(lines) + r"\end{aligned}"


def main_n2_trace_latex_chunks(
    field,
    terms: list[tuple[int, Fraction, str]],
    *,
    terms_per_chunk: int = TRACE_TERMS_PER_MATH_NODE,
) -> list[tuple[int, int, int, int, str]]:
    """Split one full trace into derivative-order continuation nodes.

    The first node of each derivative order displays the corresponding
    component equality.  Later nodes start with an explicit signed
    continuation, so together the nodes are one fully distributed sum while
    keeping each MathJax input comfortably below its 1 MiB buffer.
    """
    if terms_per_chunk < 1:
        raise ValueError("terms_per_chunk must be positive")
    trace_lhs = main_trace_prefix_latex(field) + r"(\Box\circ\Box)"
    chunks = []
    for derivative_order in range(4, -1, -1):
        selected = [term for term in terms if term[0] == derivative_order]
        if not selected:
            continue
        parts = [
            selected[start:start + terms_per_chunk]
            for start in range(0, len(selected), terms_per_chunk)
        ]
        for part_index, part in enumerate(parts, 1):
            lines = []
            for term_index, (_order, coefficient, body) in enumerate(part):
                magnitude = abs(coefficient)
                scalar = "" if magnitude == 1 else trace.frac_latex(magnitude) + r"\,"
                first_component_term = part_index == 1 and term_index == 0
                if first_component_term:
                    sign = "-" if coefficient < 0 else ""
                    component_lhs = rf"\left.{trace_lhs}\right|_{{\partial^{derivative_order}}}"
                    lines.append(rf"{component_lhs}&={sign}{scalar}{body}")
                else:
                    sign = r"{}-" if coefficient < 0 else r"{}+"
                    lines.append(rf"&\quad {sign}{scalar}{body}")
            latex = r"\begin{aligned}" + r"\\[0.65em]".join(lines) + r"\end{aligned}"
            chunks.append(
                (derivative_order, part_index, len(parts), len(part), latex)
            )
    return chunks


def main_tensor_latex(field, *, left_slot: bool = False, right_slot: bool = False) -> str:
    name, a, b, _ = field
    if a == 0:
        upper = ""
    elif a == 1:
        upper = r"\rho" if left_slot else r"\alpha"
    else:
        upper = r"\alpha_1\cdots\rho\cdots\alpha_" + str(a) if left_slot else rf"\alpha_1\cdots\alpha_{a}"
    if b == 0:
        lower = ""
    elif b == 1:
        lower = r"\bar\rho" if right_slot else r"\bar\alpha"
    else:
        lower = r"\bar\alpha_1\cdots\bar\rho\cdots\bar\alpha_" + str(b) if right_slot else rf"\bar\alpha_1\cdots\bar\alpha_{b}"
    base = FIELD_OPERATOR_LATEX[name]
    upper_latex = rf"^{{{upper}}}" if upper else ""
    lower_latex = (rf"{{}}_{{{lower}}}" if "_" in base else rf"_{{{lower}}}") if lower else ""
    return base + upper_latex + lower_latex


def main_generator_action_latex(field) -> str:
    """Specialize main.pdf equations (2.3), (2.4) to the selected raw spinor field."""
    _, a, b, _ = field
    tensor = main_tensor_latex(field)
    if a == 1:
        left = (
            rf"G^{{q_1q_2}}{tensor}=\frac12"
            rf"(\gamma^{{q_1q_2}})^{{\alpha}}{{}}_{{\rho}}{main_tensor_latex(field, left_slot=True)}"
        )
    elif a:
        left = (
            rf"G^{{q_1q_2}}{tensor}=\frac12\sum_{{i=1}}^{{{a}}}"
            rf"(\gamma^{{q_1q_2}})^{{\alpha_i}}{{}}_{{\rho}}{main_tensor_latex(field, left_slot=True)}"
        )
    else:
        left = rf"G^{{q_1q_2}}{tensor}=0"
    if b == 1:
        right = (
            rf"\bar G^{{\bar q_1\bar q_2}}{tensor}=-\frac12"
            rf"{main_tensor_latex(field, right_slot=True)}"
            rf"(\bar\gamma^{{\bar q_1\bar q_2}})^{{\bar\rho}}{{}}_{{\bar\alpha}}"
        )
    elif b:
        right = (
            rf"\bar G^{{\bar q_1\bar q_2}}{tensor}=-\frac12\sum_{{j=1}}^{{{b}}}"
            rf"{main_tensor_latex(field, right_slot=True)}"
            rf"(\bar\gamma^{{\bar q_1\bar q_2}})^{{\bar\rho}}{{}}_{{\bar\alpha_j}}"
        )
    else:
        right = rf"\bar G^{{\bar q_1\bar q_2}}{tensor}=0"
    return r"\begin{aligned}" + left + r"\\[0.55em]" + right + r"\end{aligned}"


def pagination(field, trace_order: int, page: int, total_pages: int) -> str:
    if total_pages <= 1:
        return ""
    previous = (
        f'<a class="button secondary" href="{field_query(field, trace_order, page=page - 1)}">← 이전</a>'
        if page > 1 else "<span></span>"
    )
    following = (
        f'<a class="button secondary" href="{field_query(field, trace_order, page=page + 1)}">다음 →</a>'
        if page < total_pages else "<span></span>"
    )
    return f'<nav class="pagination" aria-label="primitive 기여항 페이지">{previous}<span>{page} / {total_pages} 페이지</span>{following}</nav>'


def render_result(
    field,
    trace_order: int,
    *,
    expanded_page: int = 1,
    generated: bool = False,
    generation_error: str | None = None,
) -> str:
    name, a, b, _ = field
    details = trace.FIELD_DETAILS[name]
    field_title_html = math_html(details["latex"])
    representation_html = math_html(details["representation"])
    order_label_html = math_html(f"n={trace_order}")
    n1_html = math_html("n=1")
    n2_html = math_html("n=2")
    boxed_html = math_html(r"\boxed{\Box=\Delta-\bar\Delta}", display=True)
    generator_action_html = math_html(
        r"\displaystyle " + main_generator_action_latex(field), display=True
    )
    if trace_order == 1:
        paper_trace_latex = main_n1_trace_latex(field)
        formula_container_html = (
            '<div class="combined-formula" data-notation-schema="main-2.1-2.6-E">'
            + math_html(r"\displaystyle " + paper_trace_latex, display=True)
            + "</div>"
        )
        expansion_summary = ""
        hero_eyebrow = "Computed finite-dimensional representation trace"
        hero_title = "선택한 n=1 trace 결과"
        result_title = "완전히 평가한 n=1 trace"
        result_note = (
            "D=10 Majorana-Weyl spinor 차원 16, weight 0, raw tensor product 조건의 "
            "유한차원 spinor-index trace입니다."
        )
        operator_definitions = ""
        scope_note = (
            "n=1 결과는 weight 0 raw tensor product의 finite-dimensional "
            "representation trace입니다."
        )
    else:
        if name == "T":
            pre_clifford_terms = main_t_n2_symbolic_gamma_terms()
            provenance_terms = main_raw_field_n2_provenance_terms(field)
            primitive_terms = main_t_n2_primitive_terms()
            t_block_terms = trace.generate_exact_terms()
            nonzero_blocks = sum(
                main_t_gamma_trace_latex(term.word) is not None
                for term in t_block_terms
            )
            zero_blocks = len(t_block_terms) - nonzero_blocks
            derivative_counts = {
                order: sum(1 for current_order, _coefficient, _body in primitive_terms if current_order == order)
                for order in range(4, -1, -1)
            }
            expansion_summary = f"""
            <div class="expansion-summary" aria-label="전개 완전성">
              <span class="expansion-badge">118개 ordered block</span>
              <span class="expansion-badge">trace 후보 block {nonzero_blocks}개 + 확정 0 block {zero_blocks}개</span>
              <span class="expansion-badge">Clifford trace 전 candidate {len(pre_clifford_terms)}개</span>
              <span class="expansion-badge">pair-canonical slot-signature provenance {len(provenance_terms)}항</span>
              <span class="expansion-badge">Einstein-contracted displayed {len(primitive_terms)} / {len(primitive_terms)}항</span>
              <span class="expansion-badge">외부 미분차수 4→0: {', '.join(str(derivative_counts[order]) for order in range(4, -1, -1))}</span>
              <span class="expansion-badge">남은 spinor trace와 gamma matrix 없음</span>
            </div>"""
            hero_eyebrow = "Complete T Einstein-contraction expansion"
            hero_title = "선택한 T, n=2 전체 전개"
            result_title = f"T, n=2 전체 {len(primitive_terms)}항 Einstein-contracted trace expansion"
            result_note = (
                "main.pdf 식 (B.9)–(B.10)의 Clifford convention과 (E.9)–(E.11)의 endomorphism을 "
                "현재 D=10 Majorana-Weyl, dim 16 specialization에 적용했습니다. "
                f"single-generator trace로 사라지는 {zero_blocks}개 block을 제외한 {len(pre_clifford_terms)}개 "
                "candidate 중 nonempty 길이 2–4 bivector trace를 식 (E.16)과 같은 부호의 "
                "local-Lorentz metric pairing으로 완전 분배하고, generator가 없는 empty-sector "
                "trace에는 dim 16을 적용한 뒤, 모든 metric을 배경 텐서의 위·아래 Lorentz 지표에 "
                "흡수했습니다. bare trace identity를 축약한 것이 아니라, 각 "
                "generator label이 coefficient AST의 정확히 한 antisymmetric background-pair slot에 있음을 "
                f"검사한 whole monomial에서만 dummy flip을 적용해 {len(provenance_terms)}개 provenance를 "
                f"만들고, factor 내부 보통 편미분의 교환성을 적용해 정렬한 full factor AST와 외부 "
                f"미분 tuple이 같은 항만 합쳐 {len(primitive_terms)}개 "
                "Einstein 수축항으로 정리했습니다. "
                "우측작용 순서와 모든 1/2 정규화는 각 coefficient에 이미 포함되어 있습니다."
            )
            scope_note = (
                "T, n=2 결과는 D=10 Majorana-Weyl, dim S=dim barred S=16에서 유한차원 index trace를 "
                "배경 텐서의 Einstein 수축으로 완전히 평가한 raw tensor-product ledger입니다. explicit "
                "local metric은 남지 않습니다. mixed-index curvature는 원래 antisymmetric two-form의 한 "
                "endpoint를 올린 성분이므로 높이가 다른 지표를 bracket으로 묶지 않습니다. factor 내부 "
                "보통 편미분을 commute-sort한 full AST가 동일한 ordered block 사이의 항만 결합했으며, "
                "그 밖의 tensor identity나 contraction-graph "
                "orientation 동치는 사용하지 않았습니다."
            )
        elif name == "phi":
            primitive_terms = main_phi_n2_primitive_terms()
            derivative_counts = {
                order: sum(
                    1
                    for current_order, _coefficient, _body in primitive_terms
                    if current_order == order
                )
                for order in range(4, -1, -1)
            }
            empty_word_blocks = sum(not term.word for term in trace.generate_exact_terms())
            expansion_summary = f"""
            <div class="expansion-summary" aria-label="전개 완전성">
              <span class="expansion-badge">generator-free block {empty_word_blocks}개</span>
              <span class="expansion-badge">ordinary-partial 14 / 14항</span>
              <span class="expansion-badge">외부 미분차수 4→0: {', '.join(str(derivative_counts[order]) for order in range(4, -1, -1))}</span>
              <span class="expansion-badge">남은 covariant-D, G, barred G 없음</span>
            </div>"""
            hero_eyebrow = "Complete scalar finite-dimensional trace"
            hero_title = "선택한 φ, n=2 전체 전개"
            result_title = "φ, n=2 전체 14항 ordinary-partial trace expansion"
            result_note = (
                "φ에는 unbarred/barred spinor slot이 없어 Gφ=0, barred Gφ=0입니다. 따라서 generator가 "
                "포함된 합성항은 정확히 0이고, 남는 9개 block의 Leibniz 전개 14항을 "
                "H, Gamma와 보통 편미분만으로 모두 표시합니다."
            )
            scope_note = (
                "φ, n=2 결과는 weight 0 scalar representation의 1차원 index trace를 완전히 평가한 "
                "14항 식입니다. coefficient에 작용하는 미분도 Leibniz 법칙에 따라 모두 전개했습니다."
            )
        else:
            provenance_terms = main_raw_field_n2_provenance_terms(field)
            primitive_terms = main_raw_field_n2_primitive_terms(field)
            exact_terms = trace.generate_exact_terms()
            slot_expansions = [
                main_slot_trace_expansion(term.word, a, b) for term in exact_terms
            ]
            nonzero_blocks = sum(bool(expansion) for expansion in slot_expansions)
            zero_blocks = len(exact_terms) - nonzero_blocks
            slot_signatures = sum(len(expansion) for expansion in slot_expansions)
            pre_clifford_rows = sum(
                len(term.coefficient.terms) * len(expansion)
                for term, expansion in zip(exact_terms, slot_expansions)
            )
            derivative_counts = {
                order: sum(
                    1
                    for current_order, _coefficient, _body in primitive_terms
                    if current_order == order
                )
                for order in range(4, -1, -1)
            }
            expansion_summary = f"""
            <div class="expansion-summary" aria-label="전개 완전성">
              <span class="expansion-badge">118개 ordered block</span>
              <span class="expansion-badge">trace 후보 block {nonzero_blocks}개 + 확정 0 block {zero_blocks}개</span>
              <span class="expansion-badge">raw-slot signature {slot_signatures}개</span>
              <span class="expansion-badge">Clifford trace 전 candidate {pre_clifford_rows}개</span>
              <span class="expansion-badge">pair-canonical slot-signature provenance {len(provenance_terms)}항</span>
              <span class="expansion-badge">Einstein-contracted displayed {len(primitive_terms)} / {len(primitive_terms)}항</span>
              <span class="expansion-badge">외부 미분차수 4→0: {', '.join(str(derivative_counts[order]) for order in range(4, -1, -1))}</span>
              <span class="expansion-badge">남은 covariant-D, spinor trace, gamma matrix 없음</span>
            </div>"""
            hero_eyebrow = "Complete raw tensor Einstein-contraction ledger"
            hero_title = f"선택한 {name}, n=2 전체 전개"
            result_title = f"{name}, n=2 전체 {len(primitive_terms)}항 Einstein-contracted trace expansion"
            result_note = (
                "main.pdf 식 (2.3)–(2.5)로 선택 필드의 single-Box endomorphism을 먼저 특수화하고, "
                "동일-sector symmetric connection contraction의 label-action 소거를 반영한 뒤 두 Box를 "
                "ordinary-compose했습니다. 118개 ordered block을 실제 raw spinor slot에 배분하고, 식 "
                "(B.9)–(B.10)의 Clifford convention을 현재 D=10 Majorana-Weyl, dim 16 specialization에 "
                "적용해 모든 길이 2–4 Clifford trace를 local-Lorentz metric pairing까지 "
                "완전 분배한 뒤 모든 metric을 배경 텐서의 위·아래 Lorentz 지표에 흡수했습니다. pair flip은 "
                "bare trace identity에 적용하지 않고, 각 generator label의 "
                "유일한 antisymmetric background-pair AST slot을 검사한 whole monomial에서만 적용합니다. "
                "그 뒤 같은 exact word와 배경 monomial 안의 slot-signature 결과를 합치고, factor 내부 "
                "보통 편미분의 교환성을 적용해 정렬한 full factor AST와 외부 미분 tuple이 같은 "
                f"ordered-block 항만 다시 합쳐 {len(primitive_terms)}개 "
                "Einstein 수축항을 얻었습니다. 우측작용 순서, 1/2 정규화, barred sector 부호와 빈 slot "
                "차원 16은 각 coefficient에 이미 포함되어 있습니다."
            )
            scope_note = (
                f"{name}, n=2 결과는 D=10, dim S=dim barred S=16, density weight 0의 unprojected raw "
                "tensor product를 사용합니다. 여기서 exact는 위 single-Box field endomorphism을 먼저 만든 뒤 "
                "ordinary-compose했다는 뜻이며, ordered total generator를 사후에 단순 행렬 word로 "
                "치환했다는 뜻이 아닙니다. 식 (2.5)의 sequential order를 반영한 뒤 Clifford trace와 explicit "
                "local metric을 배경 텐서의 Einstein 수축으로 완전히 평가했습니다. mixed-index "
                "curvature는 원래 antisymmetric two-form의 raised component이므로 mixed bracket을 쓰지 "
                "않습니다. factor 내부 보통 편미분을 commute-sort한 full AST가 동일한 ordered block "
                "사이의 항만 결합했으며, 그 밖의 tensor identity나 "
                "contraction-graph orientation 동치는 사용하지 않았습니다."
            )
        chunk_html = []
        for derivative_order, part_index, part_count, term_count, latex in main_n2_trace_latex_chunks(
            field, primitive_terms
        ):
            label = f"외부 미분차수 {derivative_order} · continuation {part_index}/{part_count} · {term_count}항"
            latex_attribute = esc(r"\displaystyle " + latex)
            chunk_html.append(
                '<div class="formula-part-wrap">'
                f'<p class="formula-continuation-label">{label}</p>'
                '<div class="lazy-math formula-part" aria-busy="true" tabindex="0" '
                f'data-derivative-order="{derivative_order}" data-continuation="{part_index}" '
                f'data-latex="{latex_attribute}">'
                '전체 전개식의 이 부분을 준비하고 있습니다…</div></div>'
            )
        formula_container_html = (
            '<div class="combined-formula formula-stack" '
            'data-notation-schema="main-2.1-2.6-E">'
            + "".join(chunk_html)
            + "</div>"
        )
        if name == "phi":
            scalar_box_html = math_html(
                r"\displaystyle " + main_phi_box_latex(), display=True
            )
            operator_definitions = f"""
            <section class="section panel section-card">
              <div class="section-top">
                <div><p class="eyebrow">scalar specialization</p><h2 class="section-title">보통 미분으로 전개한 연산자</h2></div>
                <span class="section-note">no covariant-D shorthand</span>
              </div>
              <div class="combined-formula">{scalar_box_html}</div>
            </section>"""
        elif name == "T":
            # The Einstein-contracted result above has already replaced every
            # covariant D and evaluated every spinor trace.
            operator_definitions = ""
        else:
            # Every displayed ledger row has already replaced covariant D by
            # ordinary partial derivatives.  Do not reintroduce D through the
            # generic Delta/bar-Delta definitions below the result.
            operator_definitions = ""
    generator_section = ""
    if trace_order == 1:
        generator_section = f"""
        <section class="section panel section-card">
          <div class="section-top">
            <div><p class="eyebrow">main.pdf equations (2.3), (2.4)</p><h2 class="section-title">선택 필드의 total-generator 작용</h2></div>
            <span class="section-note">field specialization</span>
          </div>
          <div class="combined-formula">{generator_action_html}</div>
        </section>"""
    body = f"""
    <main>
      <nav class="breadcrumb"><a href="/">필드 선택</a><span>›</span><a href="{field_query(field)}">{esc(name)}</a><span>›</span><span>{order_label_html}</span></nav>
      <section class="hero">
        <p class="eyebrow">{hero_eyebrow}</p>
        <h1>{hero_title}</h1>
      </section>
      <section class="panel">
        <div class="result-head">
          <div>
            <h2 class="result-title">{field_title_html}</h2>
            <div class="result-meta">{representation_html} · unbarred spinor slots {a} · barred spinor slots {b}</div>
          </div>
          <div class="switches">
            <a class="pill {'active' if trace_order == 1 else ''}" href="{field_query(field, 1)}">{n1_html}</a>
            <a class="pill {'active' if trace_order == 2 else ''}" href="{field_query(field, 2)}">{n2_html}</a>
          </div>
        </div>
        <div class="formula-box">{boxed_html}</div>
      </section>

      <section class="section panel section-card" id="combined-expansion">
        <div class="section-top">
          <div><p class="eyebrow">main.pdf notation only</p><h2 class="section-title">{result_title}</h2></div>
          <span class="section-note">paper-native result</span>
        </div>
        <p class="combined-formula-note">{result_note}</p>
        {expansion_summary}
        {formula_container_html}
      </section>

      {generator_section}

      {operator_definitions}
      <p class="footnote">표준 화면에는 main.pdf에 정의된 기호만 표시합니다. {scope_note} 좌표 functional trace, determinant prefactor, 운동량 적분, regularization 및 irreducible projection은 포함하지 않습니다.</p>
    </main>"""
    return shell(f"{name} · n={trace_order} 결과", body, "3 / 3 · 결과")


def render_message(title: str, message: str, *, status_hint: str = "요청 안내") -> str:
    body = f"""
    <main>
      <section class="hero"><p class="eyebrow">Box Trace Selector</p><h1>{esc(title)}</h1><p class="lede">{esc(message)}</p></section>
      <a class="button" href="/">필드 선택으로 돌아가기</a>
    </main>"""
    return shell(title, body, status_hint)


class TraceHTTPServer(HTTPServer):
    allow_reuse_address = True


class TraceHandler(BaseHTTPRequestHandler):
    server_version = "BoxTraceSelector/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def send_html(self, document: str, status: int = 200) -> None:
        payload = document.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(payload)

    def redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    @staticmethod
    def parse_order(raw: str | None) -> int | None:
        if raw in {"1", "2"}:
            return int(raw)
        return None

    def do_GET(self) -> None:
        request = urlsplit(self.path)
        params = parse_qs(request.query)
        try:
            if request.path == "/":
                self.send_html(render_home())
                return
            if request.path == "/health":
                payload = json.dumps({"status": "ok", "fields": len(trace.FIELDS)}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if request.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if request.path == "/trace":
                field = canonical_field(params.get("field", [None])[0])
                if field is None:
                    self.send_html(render_message("필드를 찾을 수 없습니다", "첫 화면에서 계산할 필드를 다시 선택해 주세요."), 400)
                    return
                raw_order = params.get("n", [None])[0]
                if raw_order is None:
                    self.send_html(render_order(field))
                    return
                trace_order = self.parse_order(raw_order)
                if trace_order is None:
                    self.send_html(render_message("지원하지 않는 trace 차수입니다", "n=1 또는 n=2를 선택해 주세요."), 400)
                    return
                try:
                    expanded_page = int(params.get("page", ["1"])[0])
                except ValueError:
                    expanded_page = 1
                generated = params.get("generated", [""])[0] == "1"
                self.send_html(render_result(field, trace_order, expanded_page=expanded_page, generated=generated))
                return
            if request.path == "/artifact":
                self.serve_artifact(params)
                return
            self.send_html(render_message("페이지를 찾을 수 없습니다", "요청한 로컬 페이지가 존재하지 않습니다."), 404)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            self.send_html(render_message("계산 중 오류가 발생했습니다", str(exc)), 500)

    def do_POST(self) -> None:
        request = urlsplit(self.path)
        if request.path != "/generate":
            self.send_html(render_message("허용되지 않은 요청입니다", "이 주소에서는 산출물을 생성할 수 없습니다."), 405)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length > 8192:
            self.send_html(render_message("요청이 너무 큽니다", "필드와 trace 차수만 전송할 수 있습니다."), 413)
            return
        form = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
        field = canonical_field(form.get("field", [None])[0])
        trace_order = self.parse_order(form.get("n", [None])[0])
        if field is None or trace_order is None:
            self.send_html(render_message("산출물 요청이 올바르지 않습니다", "필드와 n=1 또는 n=2를 다시 선택해 주세요."), 400)
            return
        try:
            trace.write_selected_trace(field, trace_order, ARTIFACT_DIR, open_pdf=False)
        except Exception as exc:
            try:
                self.send_html(render_result(field, trace_order, generation_error=str(exc)), 500)
            except Exception:
                self.send_html(render_message("산출물 생성에 실패했습니다", str(exc)), 500)
            return
        self.redirect(field_query(field, trace_order, generated=1))

    def serve_artifact(self, params: dict[str, list[str]]) -> None:
        field = canonical_field(params.get("field", [None])[0])
        trace_order = self.parse_order(params.get("n", [None])[0])
        kind = params.get("kind", [""])[0]
        if field is None or trace_order is None:
            self.send_html(render_message("산출물 요청이 올바르지 않습니다", "필드와 trace 차수를 확인해 주세요."), 400)
            return
        resolved = artifact_path(field, trace_order, kind)
        if resolved is None:
            self.send_html(render_message("지원하지 않는 산출물입니다", "결과 화면의 다운로드 버튼을 이용해 주세요."), 400)
            return
        path, content_type, _label = resolved
        if not path.is_file():
            self.send_html(render_message("산출물이 아직 없습니다", "결과 화면에서 XeLaTeX PDF · CSV 생성을 먼저 실행해 주세요."), 404)
            return
        payload = path.read_bytes()
        force_download = params.get("download", [""])[0] == "1" or kind != "pdf"
        disposition = "attachment" if force_download else "inline"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Disposition", f'{disposition}; filename="{path.name}"')
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)


def port_number(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("포트는 정수여야 합니다.") from exc
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("포트는 0부터 65535 사이여야 합니다.")
    return port


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="필드와 n=1/n=2 trace를 MathJax 화면에서 선택하고 계산합니다.")
    parser.add_argument("--port", type=port_number, default=0, help="로컬 포트. 기본값 0은 사용 가능한 포트를 자동 선택합니다.")
    parser.add_argument("--no-open", action="store_true", help="서버 시작 시 기본 브라우저를 자동으로 열지 않습니다.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    with TraceHTTPServer((HOST, args.port), TraceHandler) as server:
        port = server.server_address[1]
        url = f"http://{HOST}:{port}/"
        print(f"Box Trace Selector: {url}", flush=True)
        print("종료하려면 Ctrl+C를 누르세요.", flush=True)
        if not args.no_open:
            opener = threading.Timer(0.35, lambda: webbrowser.open(url, new=2))
            opener.daemon = True
            opener.start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n서버를 종료합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
