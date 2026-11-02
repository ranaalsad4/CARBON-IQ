"""Phase B1 / v2 - guided demonstration (eight steps). Presentation only: no new calculation.

Every number shown is read from the reproducible run outputs (python run_all.py and python tools/run_a4.py, register
defaults, 20,000 scenarios, seed 20261024), so the demo is identical on every machine and matches the reports, the
workbook and the A6 validation. The other tabs remain available for live what-if questions.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STEPS = ["1 · Meet the factory", "2 · Understand the data", "3 · Find missing or uncertain information", "4 · Calculate emissions",
         "5 · Explore investment options", "6 · Simulate uncertain outcomes", "7 · Select the best portfolio",
         "8 · Explain the recommendation and its limitations"]
PROJECT_SHORT = {"A": "Rooftop solar", "B": "Motors + VSDs", "C": "Compressed-air leaks", "D": "Furnace heat recovery",
                 "E": "Electric forklifts", "F": "Lower-carbon steel"}


def pct(p, d=1):
    """Probability text that never rounds a non-certain value up to 100%."""
    lim = 1 - 0.5 * 10 ** -(d + 2)
    return f">{1 - 10 ** -(d + 2):.{d}%}" if p >= lim and p < 1 else f"{p:.{d}%}"


def load(root=ROOT):
    """All demo data; returns None if the run outputs are missing."""
    o = Path(root) / "outputs"
    if not (o / "results.json").exists() or not (o / "a4" / "demo_issues.csv").exists():
        return None
    R = json.load(open(o / "results.json"))
    d = dict(R=R, ds={x["id"]: x for x in R["decision_scenarios"]}, mc={x["portfolio"]: x for x in R["mc_portfolios"]},
             issues=pd.read_csv(o / "a4" / "demo_issues.csv"), status=pd.read_csv(o / "a4" / "demo_status_summary.csv"),
             est=pd.read_csv(o / "a4" / "demo_estimates_vs_truth.csv"), changes=pd.read_csv(o / "a4" / "demo_changes_applied.csv"),
             cases=pd.read_csv(o / "a4" / "decision_comparison.csv"), stab=pd.read_csv(o / "a4" / "stability_rules.csv"),
             a6=json.load(open(o / "a6" / "a6_results.json")) if (o / "a6" / "a6_results.json").exists() else None,
             chart_elec=o / "a4" / "charts" / "a4_1_electricity_demo.png")
    return d


def comparison(d):
    """Traditional ranking rules vs the CARBON IQ primary rule, with the Monte Carlo probabilities of each portfolio."""
    rows = []
    for b in d["R"]["baselines"]:
        m = d["mc"].get(b["portfolio"])
        rows.append(dict(method=b["method"], portfolio=b["portfolio"], capex=b["capex"], npv=b["npv"], t12=b["scope12_t"],
                         e_npv=m["e_npv"] if m else None, p_target=m["p_target_val"] if m else None,
                         p_budget=m["p_budget_val"] if m else None, p_loss=m["p_loss"] if m else None))
    k = d["ds"]["D4"]
    m = d["mc"][k["portfolio"]]
    rows.append(dict(method="CARBON IQ (carbon ≥ 90% and budget ≥ 90%)", portfolio=k["portfolio"], capex=k["capex_quote"],
                     npv=k["npv_base_inputs"], t12=next(b["scope12_t"] for b in d["R"]["baselines"] if b["portfolio"] == k["portfolio"])
                     if any(b["portfolio"] == k["portfolio"] for b in d["R"]["baselines"]) else None,
                     e_npv=m["e_npv"], p_target=m["p_target_val"], p_budget=m["p_budget_val"], p_loss=m["p_loss"]))
    return pd.DataFrame(rows)




SYN_LABEL = ("Guided demonstration · **synthetic Saudi metal-fabrication plant (hypothetical; not company data)** · model v{v}, "
             "20,000 Monte Carlo scenarios, seed {seed} · numbers fixed for reproducibility; the analysis workspace answers live what-if questions.")


def _go_to(i):
    import streamlit as _st
    _st.session_state["demo_step"] = STEPS[i]


def render(st, go=None):
    """Eight-step guided experience. Dataset (synthetic or MRC) and mode (Learning / Presentation) come from st.session_state."""
    mrc = st.session_state.get("dataset", "").startswith("Ma'aden")
    d = None if mrc else load()
    if not mrc and d is None:
        st.warning("Run `python run_all.py` and `python tools/run_a4.py --fast` first: the guided demo reads their outputs.")
        return
    if mrc:
        from .ui.mrc_view import LABEL
        st.markdown(LABEL)
    else:
        R = d["R"]
        st.caption(SYN_LABEL.format(v=R["meta"]["model_version"], seed=R["meta"]["seed"]))
    if "demo_step" not in st.session_state:
        st.session_state["demo_step"] = STEPS[0]
    step = st.radio("Step", STEPS, horizontal=True, key="demo_step", label_visibility="collapsed")
    show_all = st.toggle("Show all steps on one page (backup / screenshots)", key="demo_all")
    for s in (STEPS if show_all else [step]):
        i = STEPS.index(s)
        st.markdown(f'<div class="ciq-step">Step {i + 1} of {len(STEPS)}</div>', unsafe_allow_html=True)
        st.subheader(s)
        if mrc:
            from .ui import mrc_view
            st.markdown(f'<div class="ciq-lead">{MRC_LEADS[i]}</div>', unsafe_allow_html=True)
            mrc_view.demo_step(i, go)
        else:
            _STEP[i](st, go, d, R, d["ds"], d["mc"], R["target_t"], R["scope_totals"])
    if not show_all:
        i = STEPS.index(step)
        c = st.columns([1, 1, 4])
        c[0].button("← Back", on_click=_go_to, args=(max(i - 1, 0),), disabled=i == 0, key="demo_back")
        c[1].button("Next →", on_click=_go_to, args=(min(i + 1, len(STEPS) - 1),), disabled=i == len(STEPS) - 1, key="demo_next",
                    type="primary")


MRC_LEADS = [
    "Our story starts with a real company: Ma'aden Rolling Company (MRC), part of Ma'aden's Aluminium business unit, and its 2025 "
    "energy and carbon footprint exactly as reported.",
    "Before trusting the baseline, we check where every number comes from and whether the numbers add up.",
    "Next we list what the published report does not tell us — and refuse to invent it.",
    "We test the baseline: CARBON IQ recalculates Scope 1 from fuel use and examines the factor behind Scope 2.",
    "With a tested baseline, we explore what could reduce it: four projects sized to MRC's real energy use (hypothetical costs).",
    "Every combination of those projects is tested in 20,000 possible futures.",
    "We choose the plan: the most valuable one that fits the budget and meets the target with the required confidence.",
    "Finally, the recommendation for this hypothetical scenario, how sure we are, and what MRC would have to verify.",
]


def _lg():
    from .ui import learn_ui
    return learn_ui


def _s1(st, go, d, R, ds, mc, T, st_):
    L = _lg()
    L.guide_step(st, "Meet our test factory: a synthetic metal-fabrication plant near Riyadh with a carbon target, six investment "
                     "ideas and a limited budget.")
    c = st.columns(4)
    c[0].metric("Scope 1+2 emissions", f"{st_['Scope 1+2']:,.0f} tCO₂e/yr")
    c[1].metric("Reduction target (15%)", f"{T:,.0f} tCO₂e/yr")
    c[2].metric("Capital budget", f"SAR {R['meta']['budget'] / 1e6:,.1f} M")
    c[3].metric("Candidate projects", "6")
    el = next(b for b in R["baseline"] if b["source_id"] == "S2-ELEC")
    if go is not None:
        from .ui.theme import style_fig
        rows = [b for b in R["baseline"]]
        fig = go.Figure(go.Bar(x=[b["source"] for b in rows], y=[b["emissions_t"] for b in rows],
                               marker_color=["#2F5597" if b["scope"].startswith("Scope 3") else "#1F6B5C" for b in rows]))
        fig.update_yaxes(title="tCO₂e per year")
        st.plotly_chart(style_fig(fig, 320, "Where the plant's emissions come from (synthetic; blue = Scope 3)"), width="stretch")
    st.markdown(f"The plant buys {el['activity']:,.0f} MWh of grid electricity a year (Scope 2: {st_['Scope 2']:,.0f} t at "
                f"{el['ef_t_per_unit']:.3f} tCO₂e/MWh, derived from the Kingdom's 2025 UNFCCC report and GASTAT), burns natural gas "
                f"and diesel (Scope 1: {st_['Scope 1']:,.0f} t) and buys steel (Scope 3: {st_['Scope 3']:,.0f} t). Management must cut "
                "Scope 1+2 by 15% with SAR 5 million — and its monthly records are incomplete.")
    L.guide_step(st, None, explain="All plant data are synthetic (hypothetical) so that every method can be tested against a known truth.",
                 example="15% of 9,054 t = 1,358 t per year must be cut.",
                 takeaway="Which projects should be funded, how sure can we be that target and budget hold, and which missing data "
                          "are worth collecting first?")


def _s2(st, go, d, R, ds, mc, T, st_):
    L = _lg()
    L.guide_step(st, "Before any calculation, CARBON IQ looks at the raw monthly records: what was measured, what is missing, "
                     "what looks wrong.")
    s = d["status"].rename(columns={"stream": "Stream", "measured": "Measured months", "missing": "Missing", "converted": "Unit converted",
                                    "outlier": "Outlier", "suspected_zero": "Suspected zero"})
    st.dataframe(s, hide_index=True, width="stretch")
    L.learn(st, "dataquality")
    L.guide_step(st, None, explain="Each row is one data stream (electricity bills, gas, diesel, production...). The columns count "
                                   "months by status.",
                 example="Electricity: 8 months measured, 1 converted from kWh, 2 missing and 1 suspicious zero → the annual total cannot simply be added up.",
                 takeaway="Real records arrive incomplete. CARBON IQ checks them before trusting them.")


def _s3(st, go, d, R, ds, mc, T, st_):
    L = _lg()
    L.guide_step(st, "CARBON IQ lists every problem it found, estimates each gap with a stated range, and refuses to decide on "
                     "hidden zeros.")
    st.markdown("**What was wrong in the uploaded 2026 records** (synthetic problems injected into a known truth):")
    st.dataframe(d["changes"].rename(columns={"period": "Month", "stream": "Stream", "change": "Problem"}), hide_index=True, width="stretch")
    blocked = d["cases"][d["cases"].case == "C1"].iloc[0]
    st.error(f"**Not decision-ready as uploaded:** {blocked.detail}. CARBON IQ never treats a missing month as zero; the data-gap step "
             "of the analysis workspace shows the live review.")
    e = d["est"]
    view = pd.DataFrame(dict(Month=e.period, Stream=e.stream, Method=e.method.fillna(e.fallback_method).fillna("—"),
                             Estimate=e.used_value.round(1), **{"95% interval": [f"{u - 1.96 * sd:,.0f} – {u + 1.96 * sd:,.0f}" if pd.notna(sd) else "—"
                                                                                for u, sd in zip(e.used_value, e.final_sd)]},
                             Status=e.final_label.fillna(e.status), Warning=e.warning.fillna("")))
    st.dataframe(view, hide_index=True, width="stretch")
    if d["chart_elec"].exists():
        st.image(str(d["chart_elec"]), caption="Electricity: measured months, estimates with calibrated 95% intervals, and the hidden synthetic truth.")
    c0 = d["cases"].set_index("case")
    zero = c0.loc["C3"]
    st.warning(f"**If the gaps were counted as zero** (common practice), Scope 1+2 would be {float(zero.scope12):,.0f} t instead of "
               f"{float(c0.loc['C0'].scope12):,.0f} t ({float(zero.scope12) / float(c0.loc['C0'].scope12) - 1:+.0%}), and the deterministic "
               f"choice would become {zero.D1} instead of {c0.loc['C0'].D1}.")
    st.caption("Estimation is statistical (seasonal history, production intensity, mean of measured months) with leave-one-out back-tests; "
               "intervals are calibrated on synthetic hold-out data only. A flagged operational change (forklift diesel) needed an explicit, "
               "labelled reviewer override.")
    L.guide_step(st, None, explain="Uncertain information is not only missing months: savings, prices and the grid factor are uncertain "
                                   "too. Those are handled by simulation in step 6.",
                 example="A missing March estimated from last March × this year's trend: 980 MWh × 1.03 ≈ 1,009 MWh (illustrative).",
                 takeaway="Missing is not zero: zero-filling would hide a quarter of the footprint and change the plan.")


def _s4(st, go, d, R, ds, mc, T, st_):
    L = _lg()
    L.guide_step(st, "Emissions = activity × emission factor, summed by scope — and every total comes with its uncertainty.")
    ut = R["uncertainty_totals"]
    rows = [{"Source": u["source"], "Scope": u["scope"], "Activity": f"{u['activity']:,.0f} {u['unit']}",
             "Factor": f"{u['ef_t_per_unit']:.5g}", "Emissions (t)": f"{u['emissions_t']:,.0f}", "± (95%)": f"{u['u_combined_pct']:.1f}%"}
            for u in R["uncertainty"]]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    c = st.columns(3)
    c[0].metric("Scope 1+2", f"{st_['Scope 1+2']:,.0f} t"); c[0].caption(f"±{ut['Scope 1+2']['u95_pct']:.1f}% (95%)")
    c[1].metric("Scope 3 (steel, freight)", f"{st_['Scope 3']:,.0f} t"); c[1].caption(f"±{ut['Scope 3']['u95_pct']:.1f}%")
    c[2].metric("Target cut (15% of Scope 1+2)", f"{T:,.0f} t/yr")
    L.learn(st, "ghg")
    L.learn(st, "uncertainty")
    L.source(st, "baseline emissions", L.param_rows(["elec_mwh", "ef_grid", "gas_gj", "ef_gas", "diesel_forklift_l", "ef_diesel"],
                                                    used_by="engine.baseline() → engine.scope_totals()"))
    L.guide_step(st, None, explain="The ± column combines meter and factor uncertainty (GHG Protocol first-order rule).",
                 example="12,000 MWh × 0.573 tCO₂e/MWh = 6,876 t; ±√(2² + 9.8²) ≈ ±10%.",
                 takeaway=f"{st_['Scope 1+2']:,.0f} t ± {ut['Scope 1+2']['u95_pct']:.1f}%: the grid factor, not the meter, drives the uncertainty.")


def _s5(st, go, d, R, ds, mc, T, st_):
    L = _lg()
    L.guide_step(st, "Six possible projects, each valued in riyals and in riyals per tonne.")
    rows = []
    for p in R["projects"]:
        rows.append({"Project": f"{p['id']} {PROJECT_SHORT[p['id']]}", "Capex (SAR)": f"{p['capex']:,.0f}", "NPV (SAR)": f"{p['npv']:,.0f}",
                     "IRR": f"{p['irr']:.1%}" if p["irr"] is not None else "n/a",
                     "Payback (yr)": f"{p['payback_y']:.1f}" if p["payback_y"] and p["payback_y"] < 1e6 else "never",
                     "Scope 1+2 cut (t/yr)": f"{p['scope12_t']:,.1f}", "Abatement cost (SAR/t)": f"{p['mac_sar_per_t']:,.0f}"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if go is not None:
        from .ui.theme import style_fig
        fig = go.Figure(go.Bar(x=[f"{p['id']} {PROJECT_SHORT[p['id']]}" for p in R["projects"]], y=[p["npv"] / 1e6 for p in R["projects"]],
                               marker_color=["#1F6B5C" if p["npv"] > 0 else "#A33F22" for p in R["projects"]]))
        fig.update_yaxes(title="NPV, SAR million")
        st.plotly_chart(style_fig(fig, 300, "Net present value by project (green = creates value)"), width="stretch")
    st.caption("Capex values other than solar are hypothetical (no supplier quotations); solar uses a Riyadh market benchmark of SAR 2.5/W "
               "(Knight Frank 2025). Negative abatement cost = the project saves money. F reduces Scope 3 only.")
    L.learn(st, "npv")
    L.learn(st, "mac")
    L.learn(st, "irr")
    L.guide_step(st, None, explain="NPV = today's value of all future savings minus the cost; MAC = cost per tonne avoided.",
                 example="Solar: SAR 2.5M cost, SAR 308,000 a year → payback 8.1 years, NPV ≈ SAR 1.25M, MAC −SAR 97/t.",
                 takeaway="All six cost SAR 5.6M together — more than the budget. A choice is needed.")


def _s6(st, go, d, R, ds, mc, T, st_):
    L = _lg()
    L.guide_step(st, "The plans are tested in 20,000 simulated futures with different tariffs, savings and costs.")
    k = ds["D4"]
    c = st.columns(4)
    c[0].metric("Recommended portfolio", k["portfolio"])
    c[1].metric("P(meet 15% target)", pct(k["p_target_val"], 2), help="Validation sample, 200,000 scenarios")
    c[2].metric("P(actual capex ≤ SAR 5M)", f"{k['p_budget_val']:.1%}", help="Validation sample, 200,000 scenarios")
    c[3].metric("Expected NPV", f"SAR {k['e_npv'] / 1e6:.2f} M")
    if go is not None:
        from .ui.theme import style_fig
        ports = [p for p in ("A+B", "A+B+C", "A+C+D", "A+B+C+D+F") if p in mc]
        fig = go.Figure()
        fig.add_bar(x=ports, y=[mc[p]["p_target_val"] for p in ports], name="P(meet target)", marker_color="#1F6B5C")
        fig.add_bar(x=ports, y=[mc[p]["p_budget_val"] for p in ports], name="P(capex ≤ budget)", marker_color="#F2A33A")
        fig.add_hline(y=0.9, line_dash="dash", line_color="#A33F22", annotation_text="90% requirement")
        fig.update_layout(barmode="group", yaxis_range=[0, 1.05], yaxis_tickformat=".0%")
        st.plotly_chart(style_fig(fig, 330, "How often each plan meets the target and the budget"), width="stretch")
    rules = pd.DataFrame([{"Rule": f"{x['id']} {x['rule']}", "Portfolio": x["portfolio"], "P(target)": pct(x["p_target"], 2),
                           "P(capex ≤ budget)": f"{x['p_budget']:.1%}", "Expected NPV (SAR M)": round(x["e_npv"] / 1e6, 2)}
                          for x in R["decision_scenarios"] if x["id"] in ("D1", "D2", "D3", "D4")])
    st.dataframe(rules, hide_index=True, width="stretch")
    L.learn(st, "montecarlo")
    L.learn(st, "ptarget")
    L.source(st, "probabilities and decision rules", [
        L.result_row("Scenarios", "20,000 (seed 20261024) + 200,000 validation (seed 20261025)", "calculated", "outputs/results.json (run_all.py)",
                     "synthetic plant", "uncertainty.sample(); decisions.validation_sample()", "sampling error < 0.2 pp at 90%", "all probabilities"),
    ] + L.param_rows(["chance_level", "budget_chance_level", "tariff", "b_saving_frac", "c_saving_frac", "pv_capex_kw"],
                     used_by="uncertainty.sample() → Scenarios.decide()"))
    if d["a6"]:
        st.caption(f"Phase A6: an independent sampler and evaluator reproduce these choices; optimiser = exhaustive enumeration in "
                   f"{d['a6']['optimization']['cases']:,} budget/target cases (synthetic case; mathematical validation, not field validation).")
    L.guide_step(st, None, explain="Each bar is the share of the 200,000 validation futures in which a plan meets the target (green) or "
                                   "stays within budget (amber). The dashed line is management's 90% requirement.",
                 example="A+B meets the target in the single best-guess calculation, but misses it in 6.5% of futures.",
                 takeaway="Probabilities replace 'we think it is fine' with a measured confidence — modelled, not guaranteed.")


def _s7(st, go, d, R, ds, mc, T, st_):
    L = _lg()
    L.guide_step(st, "Common ranking habits compared with CARBON IQ's optimised, confidence-checked choice.")
    c = comparison(d)
    view = pd.DataFrame({"Selection method": c.method, "Portfolio": c.portfolio, "Capex (SAR M)": (c.capex / 1e6).round(2),
                         "NPV at base inputs (SAR M)": (c.npv / 1e6).round(2), "Expected NPV (SAR M)": (c.e_npv / 1e6).round(2),
                         "P(meet target)": c.p_target.map(pct), "P(capex ≤ budget)": c.p_budget.map(pct),
                         "P(NPV < 0)": c.p_loss.map(pct)})
    st.dataframe(view, hide_index=True, width="stretch")
    mac = c[c.method.str.startswith("Rank by abatement")].iloc[0]
    ciq = c.iloc[-1]
    st.markdown(f"**Ranking by NPV gives the same portfolio ({ciq.portfolio}) in this case** — CARBON IQ's added value here is not a "
                f"different answer but the evidence behind it. **Ranking by abatement cost** (cheapest tonne first, the usual MAC-curve "
                f"practice) funds {mac.portfolio}: expected NPV SAR {mac.e_npv / 1e6:.2f} M vs {ciq.e_npv / 1e6:.2f} M, budget kept in "
                f"{mac.p_budget:.0%} of scenarios vs {ciq.p_budget:.0%}, and a {mac.p_loss:.0%} chance of losing money.")
    st.caption("Probabilities from the independent 200,000-scenario validation sample; NPV and expected NPV are modelled, not realised savings.")
    L.learn(st, "portfolio")
    L.learn(st, "ranking")
    L.learn(st, "multicriteria")
    L.guide_step(st, None, explain="Six projects make 64 possible plans; CARBON IQ checks all of them against budget, target and the "
                                   "two 90% confidence rules.",
                 example="Cheapest-tonne-first adds heat recovery and the steel switch: SAR 4.70M, and the budget holds only 3 times in 4.",
                 takeaway=f"Fund {ciq.portfolio}: the most valuable plan that meets both confidence requirements.")


def _s8(st, go, d, R, ds, mc, T, st_):
    L = _lg()
    L.guide_step(st, "The recommendation in plain words — with its trade-offs, the information worth buying, and its limits.")
    k = ds["D4"]
    dr = {x["rate"]: x for x in R["discount_robustness"]}
    c_sw = R["switch_points"]["c_saving_frac"]["changes"]
    pv_hi = next(x for x in R["pv_capex_scenarios"] if x["id"] == "P1")
    tar = R["tariff_scenarios"]
    tar_same = all(x["joint"] == k["portfolio"] for x in tar)
    unstable = d["stab"][d["stab"].status != "STABLE"]
    st.success(f"**Recommendation (synthetic case):** fund **{k['portfolio']}** — rooftop solar, high-efficiency motors with variable-speed "
               f"drives and compressed-air leak repair — for SAR {k['capex_quote'] / 1e6:.2f} M quoted. Modelled: "
               f"{next(b['scope12_t'] for b in R['baselines'] if b['portfolio'] == k['portfolio']):,.0f} tCO₂e/yr Scope 1+2 reduction "
               f"(target {T:,.0f}), expected NPV SAR {k['e_npv'] / 1e6:.2f} M, target met in {pct(k['p_target_val'], 2)} and budget kept in "
               f"{k['p_budget_val']:.1%} of scenarios.")
    rows = [{"Information": v["information"], "Value before investing (SAR)": f"{v['evppi_sar']:,.0f}",
             "Assumed cost (SAR)": f"{v['collection_cost_sar']:,.0f}" if v["collection_cost_sar"] else "not collectable / not estimated",
             "Can it change the decision?": "yes" if v["decision_changes"] else "no"} for v in R["voi"]]
    st.markdown(f"**Is any information worth buying first?** Resolving **all** uncertainty would be worth about SAR {R['evpi']:,.0f} "
                f"(EVPI) — small next to the SAR {k['e_npv'] / 1e6:.2f} M expected NPV.")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    L.learn(st, "evpi")
    L.learn(st, "voi")
    st.markdown("**Trade-offs management must accept or resolve:**")
    st.markdown(
        f"- **Compressed air (C) is marginal** (NPV SAR {next(p['npv'] for p in R['projects'] if p['id'] == 'C'):,.0f}): if its savings are below "
        f"{c_sw[0][0]:.0%} of compressed-air electricity it should be dropped (then {c_sw[0][1]}). Sub-meter before committing.\n"
        f"- **Solar cost rests on one public benchmark**, not a quotation: at SAR {pv_hi['pv_capex_kw']:,.0f}/kWp (the earlier assumption) "
        + (f"no portfolio meets the 90%/90% rule within SAR 5M (it would need SAR {pv_hi['joint_min_budget'] / 1e6:.2f} M)"
           if pv_hi["joint"] == "none feasible" else f"the 90%/90% rule chooses {pv_hi['joint']}") + ". Obtain a supplier quotation.\n"
        f"- **Discount rate:** at 8% or more the deterministic choice becomes {dr[0.08]['with_target']} (6% is a transferred energy-sector rate).\n"
        f"- **Tariff:** the 2027 schedule is announced but its rates were not retrieved; the choice "
        f"{'is ' + k['portfolio'] if tar_same else 'changes'} for {min(x['tariff'] for x in tar) * 100:.0f}–{max(x['tariff'] for x in tar) * 100:.0f} halalas/kWh.\n"
        + (f"- **Data sensitivity (demo with estimated months):** " + "; ".join(
            f"rule {r.rule}: {r.reasons.split('; ')[-1].replace('elec_mwh', 'an electricity total')}" for r in unstable.itertuples()) + ".\n"
           if len(unstable) else ""))
    L.learn(st, "sensitivity")
    L.learn(st, "stability")
    L.learn(st, "risk")
    st.markdown("**Limitations:** synthetic plant; five of six project costs hypothetical; missing-data intervals calibrated on synthetic "
                "data; inputs simulated independently; not externally validated; not investment advice.")
    st.caption("Modelled impacts on a hypothetical facility — not verified savings, not investment advice. Real deployment needs a pilot (B2).")
    L.guide_step(st, None, explain="EVPI caps what any study is worth; only compressed-air sub-metering could change the plan.",
                 example=f"Sub-metering is worth about SAR {next(v['evppi_sar'] for v in R['voi'] if v['parameter'] == 'c_saving_frac'):,.0f} "
                         "against an assumed cost of SAR 40,000 — close, not clearly worth it.",
                 takeaway="A recommendation with stated confidence, named trade-offs and honest limits — ready to be tested on real data.")


_STEP = [_s1, _s2, _s3, _s4, _s5, _s6, _s7, _s8]
