"""v2 'Learn how this works' and 'Source & calculation' panels. Presentation only."""
import ast
import importlib
import inspect
import json
from pathlib import Path

import pandas as pd

from ..assumptions import P
from ..learning import BY_KEY, R as REFS
from .theme import KIND_TEXT, chip, status_chip

ROOT = Path(__file__).resolve().parents[2]
LEARNING = "Learning Mode"
_SWITCH = None


def code_of(path, fn, max_lines=40):
    """The real source of a function or method, read from the code at run time (so it cannot drift from the explanation)."""
    if path.startswith("carbon_iq/"):
        obj = importlib.import_module(path[:-3].replace("/", "."))
        for part in fn.split("."):
            obj = getattr(obj, part)
        src = inspect.getsource(obj)
    else:
        text = (ROOT / path).read_text(encoding="utf-8")
        node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == fn)
        src = "\n".join(text.splitlines()[node.lineno - 1:node.end_lineno])
    lines = src.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"    # ... {len(lines) - max_lines} more lines in {path}"]
    return f"# {path} :: {fn}()\n" + "\n".join(lines)


def is_learning(st):
    return st.session_state.get("mode", LEARNING) == LEARNING


def ref_md(k):
    t, u = REFS[k]
    return f"{t} [{u}]({u})" if u else t


def method_markdown(m, examples=None):
    """The seven learning elements of one method as markdown (used by the panels, the Learning Center and the guide)."""
    out = [f"**1 · What is it?** {m['what']}",
           f"**2 · Where did it come from?** {m['origin']}" + "".join(f"\n- {ref_md(r)}" for r in m["refs"]),
           f"**3 · Why does CARBON IQ need it?** {m['why']}",
           "**4 · How does it work?**\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(m["how"], 1)),
           f"**5 · Simple example** {m['example']}" + (f"\n\n{examples}" if examples else ""),
           "**6 · How did we implement it?** " + m["status_note"] + "\n\n| File | Function | What goes in | What comes out |\n|---|---|---|---|\n"
           + "\n".join(f"| `{f}` | `{fn}()` | {i} | {o} |" for f, fn, i, o in m["code"]),
           f"**7 · How should I explain it to judges?**\n\n> {m['judges']}"]
    return out


def learn(st, key, examples=None):
    """Collapsible 'Learn how this works' section; shown in Learning Mode only."""
    if not is_learning(st):
        return
    m = BY_KEY[key]
    with st.expander(f"📘 Learn how this works — {m['title']}"):
        st.markdown(status_chip(m["status"]), unsafe_allow_html=True)
        for block in method_markdown(m, examples):
            st.markdown(block)
        n = st.session_state.get("_learn_n", 0) + 1          # reset to 0 at the top of every app run (unique widget keys)
        st.session_state["_learn_n"] = n
        if st.toggle("Show the actual Python code", key=f"code_{key}_{n}"):
            f, fn = m["code"][0][0], m["code"][0][1]
            st.code(code_of(f, fn), language="python")
        if m.get("advanced") and st.toggle("Show advanced details", key=f"adv_{key}_{n}"):
            st.caption(m["advanced"])


def switch_effect(key):
    """How the input affects the recommendation, from the saved switch-point sweep (register defaults)."""
    global _SWITCH
    if _SWITCH is None:
        f = ROOT / "outputs" / "results.json"
        _SWITCH = json.load(open(f)).get("switch_points", {}) if f.exists() else {}
    s = _SWITCH.get(key)
    if not s:
        return "Not part of the switch-point sweep; see the sensitivity step."
    lo, hi = s["range"]
    if s["robust"]:
        return f"Recommendation unchanged across {lo:,.4g} – {hi:,.4g} (switch-point sweep, register defaults)."
    return "; ".join(f"recommendation changes from {a} to {b} at about {v:,.4g}" for v, a, b in s["changes"]) + \
        f" (sweep {lo:,.4g} – {hi:,.4g}, register defaults)."


def _kind(x):
    return {"external": "benchmark", "derived": "calculated", "hypothetical": "hypothetical"}.get(x.evidence, "benchmark")


def param_rows(keys, company="Synthetic plant (hypothetical)", used_by=""):
    rows = []
    for k in keys:
        x = P[k]
        kind = _kind(x)
        unc = "none (fixed)" if x.dist is None else _dist_text(x)
        rows.append(dict(Number=k, Value=f"{x.value:,.6g} {x.unit}", Type=KIND_TEXT[kind],
                         Origin=(x.source + (f" — {x.url}" if x.url else ""))[:400],
                         **{"Year / company": f"{x.published or 'n/a'} · {x.geography or company}",
                            "Used by": used_by or "engine.projects() / engine.baseline()", "Uncertainty": unc,
                            "Effect on decision": switch_effect(k)}))
    return rows


def _dist_text(x):
    d = x.dist
    if d[0] == "normal_rel":
        return f"normal, ±{1.96 * d[1] * 100:.1f}% (95%)"
    if d[0] == "uniform":
        return f"uniform {d[1]:g} – {d[2]:g}"
    if d[0] == "triangular":
        return f"triangular {d[1]:g} / {d[2]:g} / {d[3]:g}"
    return str(d)


def source(st, title, rows, note=None):
    """Expandable 'Source & calculation' section below a result. rows: list of dicts with the Part E fields."""
    with st.expander(f"🔎 Source & calculation — {title}"):
        kinds = sorted({r.get("Type", "") for r in rows})
        st.markdown(" ".join(chip(k) for k, t in KIND_TEXT.items() if t in kinds), unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        if note:
            st.caption(note)


def result_row(name, value, kind, origin, year_company, used_by, uncertainty, effect):
    return {"Number": name, "Value": value, "Type": KIND_TEXT[kind], "Origin": origin, "Year / company": year_company,
            "Used by": used_by, "Uncertainty": uncertainty, "Effect on decision": effect}


def guide_step(st, lead, explain=None, example=None, takeaway=None):
    """Learning-friendly text blocks used by the guided demo."""
    if lead:
        st.markdown(f'<div class="ciq-lead">{lead}</div>', unsafe_allow_html=True)
    if explain and is_learning(st):
        st.markdown(f'<div class="ciq-box"><b>What this shows.</b> {explain}</div>', unsafe_allow_html=True)
    if example and is_learning(st):
        st.markdown(f'<div class="ciq-ex"><b>Small example.</b> {example}</div>', unsafe_allow_html=True)
    if takeaway:
        st.markdown(f'<div class="ciq-take">Key takeaway: {takeaway}</div>', unsafe_allow_html=True)
