"""v2 - CARBON IQ Learning Center: glossary, one-page method explanations, how methods connect, examples, speaking notes,
references, and what the prototype proves vs what still needs real-world validation. Presentation only."""
import json
from pathlib import Path

import pandas as pd

from .. import learning as LC
from .. import mrc as M
from .learn_ui import code_of, method_markdown, ref_md
from .theme import status_chip

ROOT = Path(__file__).resolve().parents[2]


def _examples():
    """Side-by-side numbers for the synthetic plant (saved model outputs) and MRC (reported data / hypothetical scenario)."""
    f = ROOT / "outputs" / "results.json"
    R = json.load(open(f)) if f.exists() else None
    s1 = M.scope1_recalc()
    g = M.implied_grid_factor()
    rows = [
        ("Scope 1+2 accounting", f"{R['scope_totals']['Scope 1+2']:,.0f} t (synthetic)" if R else "—",
         f"{M.v('scope12_t'):,.0f} t (reported, PDF p. 5)"),
        ("Emission factors & units", "12,000 MWh × 0.573 = 6,876 t", "1,040,392 GJ ÷ 3.6 = 288,998 MWh; implied 0.335 t/MWh"),
        ("Uncertainty propagation", f"±{R['uncertainty_totals']['Scope 1+2']['u95_pct']:.1f}% on Scope 1+2" if R else "—",
         f"±{s1['u95_pct']:.1f}% on recalculated Scope 1 (assumed ±2% metering)"),
        ("Data quality & missing data", "3 months of electricity unresolved; zero-filling hides 25%", "Not applicable: annual totals only"),
        ("Scope 1 cross-check", "—", f"{s1['total_t']:,.0f} t recalculated vs {s1['reported_t']:,.0f} t reported ({s1['diff_pct']:+.2f}%)"),
        ("Scope 2 factor check", "national 0.573 t/MWh (derived from national statistics)",
         f"implied {g['implied_t_per_mwh']:.3f} (derived, not verified) vs national 0.573 → {g['scope2_at_national_t']:,.0f} t"),
        ("Budget feasibility", "Solar at SAR 3,750/kWp: no plan passes within SAR 5M; minimum SAR 5.44M",
         "Hypothetical: A+B+C needs SAR 69.9M of SAR 70M (knife-edge, flagged)"),
        ("Single-criterion ranking", "Cheapest tonne first: A+B+C+D+F, NPV −SAR 0.56M", "not run"),
        ("Multi-criteria analysis (weighted)", "not implemented", "not implemented"),
        ("NPV / IRR / MAC", "Solar: NPV SAR 1.25M, IRR 11.0%, MAC −97 SAR/t", "Hypothetical 10 MWp solar valued with the same functions"),
        ("Portfolio optimisation", "A+B+C of 64 plans", "Hypothetical scenario: best of 16 plans of A-D"),
        ("Monte Carlo & probabilities", "Target >99.99%, budget 98.8% (A+B+C)", "Hypothetical scenario, register ranges"),
        ("Value of information", "EVPI SAR 55,670; only C sub-metering matters", "Not run (no real cost or uncertainty data)"),
        ("Real options", "Wait on heat recovery; break-even gas USD 3.85", "Not run"),
    ]
    return pd.DataFrame(rows, columns=["Method", "Synthetic plant", "MRC (2025 reported data)"])


def render(st):
    st.markdown("Everything here explains the methods that the analysis actually runs. Each method page uses the same seven parts; "
                "the code references are checked automatically by the test suite.")
    tabs = st.tabs(["How the methods connect", "Method pages", "Method status", "Glossary", "Examples", "Speaking notes",
                    "What it proves", "References"])
    with tabs[0]:
        st.graphviz_chart(LC.CONNECTIONS_DOT)
        st.markdown("**Read it left to right.** Data are checked and completed, converted to emissions, valued as projects, combined "
                    "into the best portfolio, then tested in simulated futures against the target and budget. Value of information "
                    "can send you back to collect better data; sensitivity, stability and timing check how robust and how urgent the "
                    "recommendation is. This is a teaching order; in the code, optimisation, simulation and the confidence rules run "
                    "together on the same scenarios.")
    with tabs[1]:
        titles = [f"{i + 1}. {m['title']}" for i, m in enumerate(LC.METHODS)]
        pick = st.selectbox("Choose a method", titles, key="lc_method")
        m = LC.METHODS[titles.index(pick)]
        st.markdown(f"### {m['title']}")
        st.markdown(status_chip(m["status"]), unsafe_allow_html=True)
        for block in method_markdown(m):
            st.markdown(block)
        with st.expander(f"Actual Python code: {m['code'][0][1]}() in {m['code'][0][0]}"):
            st.code(code_of(m["code"][0][0], m["code"][0][1], max_lines=80), language="python")
        if m.get("advanced"):
            st.caption("Advanced: " + m["advanced"])
    with tabs[2]:
        st.dataframe(pd.DataFrame([{"Method": m["title"], "Status": m["status"], "What exactly": m["status_note"]} for m in LC.METHODS]),
                     hide_index=True, width="stretch")
        n = {s: sum(m["status"] == s for m in LC.METHODS) for s in (LC.STATUS_FULL, LC.STATUS_PART, LC.STATUS_NONE)}
        st.caption(" · ".join(f"{k}: {v}" for k, v in n.items()) + ". Status is judged from the code, not from plans.")
    with tabs[3]:
        st.dataframe(pd.DataFrame(LC.GLOSSARY, columns=["Term", "Meaning"]), hide_index=True, width="stretch", height=520)
    with tabs[4]:
        st.dataframe(_examples(), hide_index=True, width="stretch")
        st.caption("Synthetic numbers come from the saved model run (outputs/results.json). MRC energy and emissions are reported "
                   "values; MRC investment results are a hypothetical scenario, not Ma'aden data.")
    with tabs[5]:
        for m in LC.METHODS:
            st.markdown(f"**{m['title']}** — _{m['status']}_")
            st.markdown(f'<div class="ciq-quote">{m["judges"]}</div>', unsafe_allow_html=True)
    with tabs[6]:
        c = st.columns(2)
        c[0].markdown("#### What the prototype proves\n" + "\n".join(f"- {x}" for x in LC.PROVES))
        c[1].markdown("#### What still needs real-world validation\n" + "\n".join(f"- {x}" for x in LC.NEEDS_VALIDATION))
        st.info("CARBON IQ uses statistics, simulation and optimisation. It does not contain a trained machine-learning model, and it "
                "is a research prototype, not production software or investment advice.")
    with tabs[7]:
        st.markdown("\n".join(f"- {ref_md(k)}" for k in LC.R))
        st.caption("References were checked by web search (28-30 Oct 2026). Open each link yourself before quoting it.")
