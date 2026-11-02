"""v2 - MRC real-data case study screens (workspace and guided-demo steps). Calculations live in carbon_iq/mrc.py."""
import pandas as pd
import streamlit as st

from .. import engine as E
from .. import mrc as M
from .learn_ui import guide_step, is_learning, learn, param_rows, result_row, source
from .theme import box, chip, sar, style_fig

MC_N = 20_000                # v2.1: same sample size as the synthetic plant's primary run (the choice is near a threshold)

PAGE = "Ma'aden Sustainability Data Book 2025, PDF page 5 (ASI 5.1 table, MRC column)"
LABEL = ("**Ma'aden Rolling Company (MRC), 2025 reported data.** Energy and emissions are Ma'aden's published figures; "
         "every investment number below is a **hypothetical CARBON IQ scenario, not a Ma'aden value.**")


@st.cache_data(show_spinner=False)
def _det(items):
    p = M.params(dict(items))
    best, rows = M.portfolios(p)
    prj, _ = M.projects(p)
    return p, best, rows, {k: {kk: (float(vv) if not isinstance(vv, str) else vv) for kk, vv in d.items()} for k, d in prj.items()}


@st.cache_data(show_spinner=False)
def _mc(items, n, alpha, beta):
    return M.monte_carlo(M.params(dict(items)), n=n, alpha=alpha, beta=beta)


@st.cache_data(show_spinner=False)
def _feas(items, n):
    p = M.params(dict(items))
    return M.budget_feasibility(p, M.monte_carlo(p, n=n))


@st.cache_data(show_spinner=False)
def _tor(items, ids):
    return M.tornado(ids, M.params(dict(items)))


def overrides_from_state():
    ss = st.session_state
    o = {}
    if "mrc_pv" in ss:
        o.update(pv_kwp=float(ss["mrc_pv"]), budget=float(ss["mrc_budget"]) * 1e6, target_share=float(ss["mrc_target"]) / 100,
                 grid_basis=1.0 if ss["mrc_grid"].startswith("Implied") else 0.0, tariff=float(ss["mrc_tariff"]))
    return tuple(sorted(o.items()))


def scenario_controls():
    d = {i.key: i.value for i in M.scenario_defaults()}
    with st.expander("⚙️ Hypothetical scenario settings (not Ma'aden values)", expanded=False):
        c = st.columns(5)
        c[0].number_input("Solar size (kWp)", 1_000, 50_000, int(d["pv_kwp"]), 1_000, key="mrc_pv")
        c[1].number_input("Budget (SAR million)", 10, 200, int(d["budget"] / 1e6), 5, key="mrc_budget")
        c[2].number_input("Target (% of reported Scope 1+2)", 1, 20, int(round(d["target_share"] * 100)), 1, key="mrc_target")
        c[3].selectbox("Grid factor for savings", ["Implied by MRC's report (0.335)", "Saudi national average (0.573)"], key="mrc_grid")
        c[4].number_input("Electricity tariff (SAR/kWh)", 0.10, 0.40, 0.18, 0.01, key="mrc_tariff")
        st.caption("All five settings are CARBON IQ assumptions for demonstration. Ma'aden publishes no project costs, roof areas, "
                   "budgets or MRC-level targets.")


# ------------------------------------------------------------------ content blocks (shared by workspace and guided demo)
def block_reported():
    rows = [{"Item": i.label, "2025 value": f"{i.value:,.0f}", "Unit": i.unit, "Type": "Reported", "Where": f"{i.source}, {i.page}"}
            for i in M.REPORTED.values()]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    chk = M.energy_check()
    st.markdown(f"**Data-quality check:** the seven energy lines add up to {chk['sum_of_lines']:,.0f} GJ; the reported total is "
                f"{chk['reported_total']:,.0f} GJ (difference {chk['difference']:,.0f} GJ).")
    st.caption(M.DATABOOK_NOTE)
    source(st, "MRC reported figures", [
        result_row(i.label, f"{i.value:,.0f} {i.unit}", "reported", f"{i.source} — {i.note}", f"{M.YEAR} · {M.COMPANY}",
                   "mrc.REPORTED", "not stated in the source (limited assurance by Bureau Veritas)", "inputs to every MRC calculation")
        for i in M.REPORTED.values()] + [
        result_row(i.label, f"{i.value:,}", "reported", f"{i.source}, {i.page} — {i.note}", f"{M.YEAR} · Ma'aden", "context only", "—",
                   "not used in calculations") for i in M.CONTEXT])


def energy_chart(go):
    keys = ["natural_gas_gj", "electricity_gj", "diesel_heating_gj", "gasoline_gj"]
    fig = go.Figure(go.Bar(x=[M.REPORTED[k].label for k in keys], y=[M.v(k) / 1e3 for k in keys], marker_color=["#F2A33A", "#1F6B5C", "#8A5A12", "#A33F22"],
                           text=[f"{M.v(k) / M.v('energy_total_gj'):.1%}" for k in keys], textposition="outside"))
    fig.update_yaxes(title="thousand GJ (2025, reported)")
    return style_fig(fig, 330, "MRC energy use by source, 2025 (reported)")


def block_scope1(go):
    s = M.scope1_recalc()
    df = pd.DataFrame([{"Fuel": r["fuel"], "Reported energy (GJ)": f"{r['activity_gj']:,.0f}", "IPCC factor (tCO₂e/GJ)": f"{r['ef_t_per_gj']:.5f}",
                        "Calculated (tCO₂e)": f"{r['emissions_t']:,.0f}", "± (95%)": f"{r['u95_pct']:.1f}%"} for r in s["rows"]])
    st.dataframe(df, hide_index=True, width="stretch")
    c = st.columns(3)
    c[0].metric("Scope 1 recalculated by CARBON IQ", f"{s['total_t']:,.0f} t"); c[0].caption(f"±{s['u95_pct']:.1f}% (95%)")
    c[1].metric("Scope 1 reported by Ma'aden", f"{s['reported_t']:,.0f} t")
    c[2].metric("Difference", f"{s['diff_t']:+,.0f} t"); c[2].caption(f"{s['diff_pct']:+.2f}%")
    r = M.scope1_reconciliation()
    st.markdown("**Reconciliation: where the 144 t difference sits**")
    st.dataframe(pd.DataFrame([
        ("CO₂ from the three fuels at IPCC default CO₂ factors", f"{r['co2_only']:,.0f}", "calculated"),
        ("+ CH₄ and N₂O (IPCC defaults, AR5 GWPs 28 and 265)", f"{r['non_co2']:+,.0f}", "calculated"),
        ("= Scope 1 recalculated by CARBON IQ", f"{r['recalculated']:,.0f}", "calculated"),
        ("Scope 1 reported by Ma'aden (PDF page 5)", f"{r['reported']:,.0f}", "reported"),
        ("Difference", f"{r['diff_t']:+,.0f} ({r['diff_pct']:+.2f}%)", "calculated"),
        ("95% uncertainty of the recalculation", f"±{r['u95_t']:,.0f} (±{r['u95_pct']:.1f}%)", "calculated"),
    ], columns=["Item", "tCO₂e", "Type"]), hide_index=True, width="stretch")
    st.markdown(f"**Verdict:** the difference is {r['diff_share_of_u95']:.0%} of the recalculation's own uncertainty — the reported "
                "value and the IPCC-based recalculation are **consistent**. The exact cause cannot be identified without Ma'aden's "
                "emission factors.")
    if is_learning(st):
        box(st, "<b>Explaining the 144 t, step by step.</b><br>"
            f"• <b>Not the greenhouse-gas weights:</b> AR4 or AR6 GWPs instead of AR5 change the total by only "
            f"{r['ar4'] - r['recalculated']:+.1f} t and {r['ar6'] - r['recalculated']:+.1f} t.<br>"
            f"• <b>Not CH₄ and N₂O alone:</b> even CO₂ alone ({r['co2_only']:,.0f} t) is already {r['co2_only'] - r['reported']:,.0f} t above "
            "the reported value.<br>"
            f"• <b>Most likely the gas carbon factor:</b> a natural-gas factor {abs(r['gas_change_pct']):.2f}% below the IPCC default "
            f"({r['gas_factor_to_close']:,.0f} instead of 56,100 kg CO₂/TJ — well inside IPCC's 54,300–58,300 range) closes the gap "
            "exactly. Companies often use supplier- or country-specific gas factors; Ma'aden's is not published.<br>"
            f"• <b>Energy basis:</b> if the GJ were gross (higher) heating values, the recalculation would fall to about "
            f"{r['if_gross_cv']:,.0f} t, 10% below the reported figure — so net heating values are more consistent (an inference, not a fact).<br>"
            "• <b>Other sources</b> (e.g. refrigerant leaks) are not itemised; if included in the reported figure, the fuel-only gap "
            "would be slightly larger, not smaller.")
    learn(st, "reconcile")
    learn(st, "ghg", examples="MRC: 1,104,220 GJ × 0.05615 = 62,007 t from gas; adding diesel (1,989 t) and gasoline (109 t) gives "
                              "64,105 t, 0.22% above the reported 63,961 t.")
    learn(st, "uncertainty")
    source(st, "Scope 1 recalculation", [
        result_row("Natural gas factor", "0.0561545 tCO₂e/GJ", "benchmark", M.IPCC_T23 + " — " + M.IPCC_URL, "generic, IPCC 2006",
                   "mrc.fuel_factor_t_per_gj()", f"±{M.fuel_factor_u95('natural_gas_gj'):.1f}% (IPCC CO2 range)",
                   "≈ 97% of recalculated Scope 1"),
        result_row("Diesel/heating-fuel factor", f"{M.fuel_factor_t_per_gj('diesel_heating_gj'):.6f} tCO₂e/GJ", "benchmark",
                   M.IPCC_T23, "generic, IPCC 2006", "mrc.fuel_factor_t_per_gj()", f"±{M.fuel_factor_u95('diesel_heating_gj'):.1f}%", "≈ 3%"),
        result_row("Metering uncertainty", "±2% (95%)", "hypothetical", "CARBON IQ assumption (MRC does not state it)", "—",
                   "mrc.scope1_recalc(activity_u95=2)", "—", "widens the ± range only"),
        result_row("Recalculated Scope 1", f"{s['total_t']:,.0f} t", "calculated", "Σ reported GJ × IPCC factor", f"{M.YEAR} · MRC",
                   "mrc.scope1_recalc() with engine.u_mult / engine.u_add", f"±{s['u95_pct']:.1f}%",
                   "a check of the reported figure; MRC's own value is used everywhere else")],
        note="IPCC factors assume net calorific value (NCV). The data book does not say whether its GJ are NCV or GCV; the 0.2% "
             "match suggests NCV, but this is an inference.")


def block_scope2(go):
    g = M.implied_grid_factor()
    c = st.columns(3)
    c[0].metric("Electricity (converted)", f"{g['electricity_mwh']:,.0f} MWh"); c[0].caption("1,040,392 GJ ÷ 3.6")
    c[1].metric("Factor implied by MRC's report", f"{g['implied_t_per_mwh']:.3f} tCO₂e/MWh")
    c[2].metric("Saudi national grid average (register)", f"{g['national_t_per_mwh']:.3f} tCO₂e/MWh")
    fig = go.Figure()
    fig.add_bar(x=["Reported Scope 2", "Same electricity × national average"], y=[g["scope2_t"], g["scope2_at_national_t"]],
                marker_color=["#1F6B5C", "#B0B7C3"], text=[f"{g['scope2_t']:,.0f} t", f"{g['scope2_at_national_t']:,.0f} t"], textposition="outside")
    fig.update_yaxes(title="tCO₂e (2025)")
    st.plotly_chart(style_fig(fig, 320, "Scope 2 depends on the emission factor chosen"), width="stretch")
    st.warning(f"The national average would give {g['scope2_at_national_t']:,.0f} t, {g['scope2_at_national_t'] / g['scope2_t'] - 1:+.0%} more than "
               "reported. The data book does not state which factor or method Ma'aden used (its 'GHG Reporting Methodology' is not "
               "included). Possible explanations - a supplier-specific factor, a different year, or partly self-generated power - "
               "are **unverified**; ask MRC before relying on either number.")
    st.markdown("**Three different 'grid factors' — do not confuse them**")
    st.dataframe(pd.DataFrame([{"Factor": x["factor"], "tCO₂e/MWh": f"{x['value']:.3f}" if x["value"] is not None else "not available",
                                "How it is obtained": x["how"], "Independently verified?": x["verified"]} for x in M.grid_factor_comparison()]),
                 hide_index=True, width="stretch")
    if is_learning(st):
        box(st, "<b>Derived is not the same as verified.</b> The 0.335 figure is <i>derived</i>: CARBON IQ divides one reported number "
            "by another. It tells us what factor Ma'aden's numbers <i>imply</i>, not which factor Ma'aden used or whether it is right. "
            "The 0.573 national average is also <i>derived</i> (from national statistics) and is a location-based average, not a "
            "verified factor for MRC's actual supply. Bureau Veritas' limited assurance covers Ma'aden's reported Scope 2 total, "
            "not a factor CARBON IQ calculates from it. Only the supplier's or Ma'aden's documented factor can settle the question.")
    learn(st, "factors", examples="MRC: 96,671 t ÷ 288,998 MWh = 0.335 tCO₂e/MWh implied, versus 0.573 national average.")
    source(st, "Scope 2 and the implied grid factor", [
        result_row("Electricity (MWh)", f"{g['electricity_mwh']:,.0f} MWh", "calculated", f"reported 1,040,392 GJ ({PAGE}) ÷ 3.6",
                   f"{M.YEAR} · MRC", "mrc.gj_to_mwh()", "as reported", "basis of projects A, B, C savings"),
        result_row("Implied factor", f"{g['implied_t_per_mwh']:.4f} tCO₂e/MWh", "calculated", "reported Scope 2 ÷ electricity in MWh",
                   f"{M.YEAR} · MRC", "mrc.implied_grid_factor()", "method not stated by Ma'aden",
                   "used to value electricity savings (default); switch to national in the scenario settings"),
        param_rows(["ef_grid"], used_by="mrc.implied_grid_factor() (comparison)")[0]])


MISSING = [
    ("Monthly records", "Annual totals only", "Missing-data estimation cannot run; CARBON IQ will not invent monthly values"),
    ("MRC production volume", "Only the Aluminium BU total is reported", "No MRC emissions intensity can be calculated"),
    ("Scope 2 factor / method", "Implied 0.335 vs national 0.573 tCO₂e/MWh", "Electricity savings could be worth 71% more tonnes"),
    ("Net or gross calorific value (GJ)", "Not stated", "Scope 1 recalculation could shift by about 10%"),
    ("End-use split (motors, compressed air, furnaces)", "Not reported", "Project savings use the synthetic plant's shares (hypothetical)"),
    ("Project costs, roof area, budget, target", "Not reported", "Investment scenario is hypothetical; replace with quotations"),
    ("Uncertainty of reported values", "Not stated (limited assurance)", "± ranges use IPCC factor ranges and an assumed ±2% metering"),
]


def block_missing():
    st.dataframe(pd.DataFrame(MISSING, columns=["What is missing", "What the report gives", "Consequence in CARBON IQ"]), hide_index=True,
                 width="stretch")
    learn(st, "dataquality", examples="For MRC the method is not applicable: the data book publishes annual totals only, and "
                                      "CARBON IQ does not fabricate monthly observations.")


def block_projects(go, items):
    p, best, rows, prj = _det(items)
    view = []
    for k, d in prj.items():
        irr = E.project_irr({**d, "life": d["life"]}, degradation=p.get("pv_degradation", 0.0)) if k == "A" else E.irr(d["capex"], d["annual_cf"], int(d["life"]))
        view.append({"Project (hypothetical)": f"{k} {d['name']}", "Capex": sar(d["capex"]), "Yearly net saving": sar(d["annual_cf"]),
                     "NPV": sar(d["npv"]), "IRR": f"{irr:.1%}" if irr is not None else "n/a",
                     "Payback (yr)": f"{E.simple_payback(d['capex'], d['annual_cf']):.1f}" if d["annual_cf"] > 0 else "never",
                     "Scope 1+2 cut (t/yr)": f"{d['scope12_t']:,.0f}", "MAC (SAR/t)": f"{E.mac(d):,.0f}"})
    st.dataframe(pd.DataFrame(view), hide_index=True, width="stretch")
    fig = go.Figure(go.Bar(x=list(prj), y=[d["npv"] / 1e6 for d in prj.values()],
                           marker_color=["#1F6B5C" if d["npv"] > 0 else "#A33F22" for d in prj.values()]))
    fig.update_yaxes(title="NPV, SAR million")
    st.plotly_chart(style_fig(fig, 300, "Hypothetical MRC projects: NPV"), width="stretch")
    st.caption("A rooftop solar · B high-efficiency motors + drives · C compressed-air leak programme · D furnace heat recovery. "
               "E (forklifts) and F (steel supplier) are left out: MRC's reported data give no basis for them.")
    learn(st, "npv")
    learn(st, "mac")
    sd = {i.key: i for i in M.scenario_defaults()}
    source(st, "MRC investment scenario inputs", [
        result_row(i.label, f"{i.value:,.4g} {i.unit}", i.kind if i.kind != "calculated" else "calculated", f"{i.source}. {i.note}",
                   "not an MRC value", "mrc.params()", "user-adjustable", "changes project size, cost or tonnes") for i in sd.values()]
        + param_rows(["pv_capex_kw", "pv_yield", "b_saving_frac", "c_saving_frac", "d_saving_frac", "tariff", "gas_price_usd", "discount_rate"],
                     company="transferred to MRC (hypothetical use)", used_by="engine.projects() via mrc.params()"),
        note="'Effect on decision' entries for register inputs describe the synthetic plant's switch-point sweep; MRC's own "
             "sensitivity is in the sensitivity step.")


def block_portfolio(go, items):
    p, best, rows, _ = _det(items)
    T = M.target_t(p)
    if best:
        st.success(f"**Best plan at most-likely inputs (hypothetical scenario): {best['portfolio']}** · NPV {sar(best['npv'])} · "
                   f"{best['scope12_t']:,.0f} t/yr cut (target {T:,.0f}) · capex {sar(best['capex'])} of {sar(p['budget'])}")
    else:
        f = M.budget_feasibility(p)
        if f["det_min_budget"] is None:
            st.error(f"**Target not reachable at any budget** under these assumptions: all four projects together cut at most "
                     f"{f['det_max_cut']:,.0f} t/yr, below the {T:,.0f} t/yr target. CARBON IQ does not change the target or the budget; "
                     "management must lower the target or add other projects.")
        else:
            st.error(f"**No plan meets the target within {sar(p['budget'])}.** The cheapest plan that reaches {T:,.0f} t/yr costs "
                     f"{sar(f['det_min_budget'])} at most-likely inputs — the minimum budget under these assumptions. CARBON IQ does not "
                     "raise the budget itself; that is a management decision.")
    fig = go.Figure(go.Scatter(x=[r["scope12_t"] for r in rows], y=[r["npv"] / 1e6 for r in rows], mode="markers+text",
                               text=[r["portfolio"] for r in rows], textposition="top center",
                               marker=dict(size=11, color=["#1F6B5C" if r["feasible"] else ("#B0B7C3" if r["within_budget"] else "#E7B7A8") for r in rows])))
    fig.add_vline(x=T, line_dash="dash", line_color="#A33F22", annotation_text="target")
    fig.update_xaxes(title="Scope 1+2 cut, tCO₂e/yr"); fig.update_yaxes(title="NPV, SAR million")
    st.plotly_chart(style_fig(fig, 380, "All 16 MRC combinations (green = within budget and meets target)"), width="stretch")
    learn(st, "portfolio")
    source(st, "MRC best plan", [result_row("Best plan NPV", sar(best["npv"]) if best else "none", "calculated",
                                            "engine.projects() + engine.portfolio() on hypothetical inputs", "scenario, not MRC",
                                            "mrc.portfolios()", "see uncertainty step", "the deterministic recommendation")])


def block_mc(go, items, n):
    mc = _mc(items, n, 0.9, 0.9)
    rows = sorted(mc["rows"], key=lambda r: -r["e_npv"])
    st.dataframe(pd.DataFrame([{"Plan": r["portfolio"], "Quoted capex": sar(r["quoted_capex"]), "Expected NPV": sar(r["e_npv"]),
                                "5th-percentile NPV": sar(r["p5_npv"]), "P(meet target)": f"{r['p_target']:.1%}",
                                "P(capex ≤ budget)": f"{r['p_budget']:.1%}", "P(loss)": f"{r['p_loss']:.1%}",
                                "Budget needed for the 90% budget rule": sar(r["budget_needed"])} for r in rows[:10]]),
                 hide_index=True, width="stretch")
    ch = mc["choice"]
    if ch:
        st.success(f"**Confidence rule (target ≥ 90% and budget ≥ 90%, tightened to {mc['alpha_eff']:.4f} for {n:,} futures): "
                   f"{ch['portfolio']}** · expected NPV {sar(ch['e_npv'])} · target met in {ch['p_target']:.1%} · budget kept in {ch['p_budget']:.1%}")
    else:
        if mc["min_budget"] is None:
            st.error(f"**No plan meets the carbon target in 90% of futures at any budget** (largest expected cut "
                     f"{mc['max_cut']:,.0f} t/yr vs target {mc['target_t']:,.0f} t/yr). No recommendation is forced.")
        else:
            mb = mc["min_budget"]
            st.error(f"**No plan meets both 90% rules within {sar(mc['budget'])}.** No recommendation is forced and the budget is not "
                     f"raised automatically. Under these assumptions the smallest budget that would make the rule feasible is "
                     f"**{sar(mb['budget_needed'])}** ({mb['portfolio']}).")
    f = M.budget_feasibility(M.params(dict(items)), mc)
    bv = f["best_value_plan"]
    if ch and bv and bv["portfolio"] != ch["portfolio"]:
        st.info(f"The most valuable plan that meets the carbon rule is **{bv['portfolio']}** (expected NPV {sar(bv['e_npv'])}), but it keeps "
                f"the budget in only {bv['p_budget']:.1%} of futures; it would need **{sar(bv['budget_needed'])}** to pass the 90% budget "
                f"rule. Within {sar(mc['budget'])}, the rule therefore chooses {ch['portfolio']}. Raising the budget is a management decision.")
    if ch and abs(ch["budget_margin_se"]) < 2:
        st.warning(f"⚠ **Knife-edge choice:** {ch['portfolio']} passes the budget rule by only {ch['budget_margin_se']:.1f} Monte Carlo "
                   f"standard errors (it needs {sar(ch['budget_needed'])} of the {sar(mc['budget'])} budget). A different random sample or "
                   "a slightly higher cost estimate could change the recommendation; treat it as unsettled.")
    top = [r for r in rows if r["quoted_capex"] <= dict(items).get("budget", 70e6) + 1e-6][:5]
    fig = go.Figure()
    fig.add_bar(x=[r["portfolio"] for r in top], y=[r["p_target"] for r in top], name="P(meet target)", marker_color="#1F6B5C")
    fig.add_bar(x=[r["portfolio"] for r in top], y=[r["p_budget"] for r in top], name="P(capex ≤ budget)", marker_color="#F2A33A")
    fig.add_hline(y=0.9, line_dash="dash", line_color="#A33F22", annotation_text="90% requirement")
    fig.update_layout(barmode="group"); fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
    st.plotly_chart(style_fig(fig, 320, "Probabilities for the most valuable affordable plans"), width="stretch")
    learn(st, "montecarlo")
    learn(st, "ptarget")
    learn(st, "budget")
    source(st, "MRC Monte Carlo", [result_row("Number of simulated futures", f"{n:,}", "hypothetical", "user setting", "—", "mrc.monte_carlo()",
                                              f"sampling error ≈ ±{1.96 * (0.09 / n) ** 0.5:.1%} at 90%", "probabilities"),
                                   result_row("Input ranges", "register distributions", "benchmark",
                                              "assumptions.P (tariff, gas price, savings, PV cost and yield, capex spreads)", "transferred",
                                              "uncertainty._draw()", "as in the synthetic plant", "drive every probability")],
           note="Emission factors are held fixed (reporting basis), as in the synthetic plant's primary rule.")
    return mc


def block_sensitivity(go, items):
    p, best, rows, _ = _det(items)
    if not best:
        st.info("No feasible plan at these settings."); return
    tor = _tor(items, tuple(best["ids"]))
    fig = go.Figure()
    names = [r["parameter"] for r in tor][::-1]
    fig.add_bar(y=names, x=[(r["npv_low"] - r["base_npv"]) / 1e6 for r in tor][::-1], orientation="h", name="input at 5th percentile", marker_color="#A33F22")
    fig.add_bar(y=names, x=[(r["npv_high"] - r["base_npv"]) / 1e6 for r in tor][::-1], orientation="h", name="input at 95th percentile", marker_color="#1F6B5C")
    fig.update_layout(barmode="overlay"); fig.update_xaxes(title=f"change in NPV of {best['portfolio']}, SAR million")
    st.plotly_chart(style_fig(fig, 340, "What moves the value of the hypothetical MRC plan"), width="stretch")
    alt = dict(items); alt["grid_basis"] = 0.0 if alt.get("grid_basis", 1.0) >= 0.5 else 1.0
    p2, b2, _, _ = _det(tuple(sorted(alt.items())))
    other = "the Saudi national average (0.573)" if alt["grid_basis"] < 0.5 else "the factor implied by MRC's report (0.335)"
    st.markdown(f"**Grid-factor choice:** valuing electricity savings with {other} instead, the best plan is "
                + (f"**{b2['portfolio']}** ({b2['scope12_t']:,.0f} t/yr)." if b2 else "**none** (no plan meets budget and target)."))
    learn(st, "sensitivity")


def block_register():
    reg = pd.DataFrame(M.source_register())
    st.dataframe(reg, hide_index=True, width="stretch", height=420)
    st.download_button("Download the MRC source-to-variable register (CSV)", reg.to_csv(index=False), "carbon_iq_mrc_source_register.csv",
                       key="mrc_reg_dl")


# ------------------------------------------------------------------ workspace
WS_STEPS = ["1 · Reported data", "2 · Emissions check", "3 · Gaps & limits", "4 · Investment scenario", "5 · Portfolio",
            "6 · Uncertainty & confidence", "7 · Sensitivity", "8 · Recommendation & limits", "Sources"]


def render_workspace(go):
    st.markdown(LABEL)
    scenario_controls()
    items = overrides_from_state()
    n = st.session_state.get("mrc_n", MC_N)
    tabs = st.tabs(WS_STEPS)
    with tabs[0]:
        st.plotly_chart(energy_chart(go), width="stretch")
        block_reported()
    with tabs[1]:
        block_scope1(go)
        st.divider()
        block_scope2(go)
    with tabs[2]:
        block_missing()
    with tabs[3]:
        block_projects(go, items)
    with tabs[4]:
        block_portfolio(go, items)
    with tabs[5]:
        st.select_slider("Simulated futures", [2000, 5000, 10000, 20000], value=MC_N, key="mrc_n")
        block_mc(go, items, n)
    with tabs[6]:
        block_sensitivity(go, items)
    with tabs[7]:
        render_recommendation(items, n)
    with tabs[8]:
        block_register()


# ------------------------------------------------------------------ guided demo: one story from the reported baseline to a recommendation
def _story_facts():
    p = M.params()
    r = M.scope1_reconciliation()
    g = M.implied_grid_factor()
    f = _feas(tuple(), MC_N)
    ch = f["cc_choice"]
    return [
        f"Baseline {M.v('scope12_t'):,.0f} tCO₂e (reported)",
        "Data consistent ✓",
        f"{len(MISSING)} gaps named",
        f"Scope 1 within {r['diff_pct']:+.2f}% ✓ · Scope 2 factor unverified",
        f"Target {M.target_t(p):,.0f} t/yr · budget {sar(p['budget'])} (hypothetical)",
        "Probabilities for 16 plans",
        f"Rule picks {ch['portfolio'] if ch else 'none'}",
        "Recommendation + limits",
    ]


def story_strip(i):
    facts = _story_facts()
    html = " → ".join((f"<b>{x}</b>" if k == i else x) for k, x in enumerate(facts[:i + 1]))
    st.markdown(f'<div class="ciq-box" style="font-size:0.9rem"><b>The MRC story so far:</b> {html}</div>', unsafe_allow_html=True)


def _next(text):
    st.caption(f"Next → {text}")


def demo_step(i, go):
    items = tuple()
    story_strip(i)
    if i == 0:
        c = st.columns(4)
        c[0].metric("Scope 1 (reported)", f"{M.v('scope1_t'):,.0f} t")
        c[1].metric("Scope 2 (reported)", f"{M.v('scope2_t'):,.0f} t")
        c[2].metric("Scope 1+2 (reported)", f"{M.v('scope12_t'):,.0f} t")
        c[3].metric("Energy use (reported)", f"{M.v('energy_total_gj') / 1e6:,.2f} million GJ")
        st.plotly_chart(energy_chart(go), width="stretch")
        guide_step(st, None, explain="These are MRC's 2025 reported figures. 60% of its Scope 1+2 comes from purchased electricity, the "
                   "rest mostly from natural gas.",
                   example="1,104,220 GJ of natural gas is 51% of MRC's energy use.",
                   takeaway="Our starting point is a real, reported baseline: 160,632 tCO₂e in 2025.")
        _next("before using these numbers, check where they come from and whether they add up.")
    elif i == 1:
        block_reported()
        guide_step(st, None, explain="Every value has a page reference. Reported numbers are Ma'aden's; CARBON IQ only re-uses them.",
                   example="The energy lines add up exactly to the reported total of 2,172,929 GJ — a first quality check passed.",
                   takeaway="The data are consistent, annual and covered by limited assurance.")
        _next("what the report does not tell us.")
    elif i == 2:
        block_missing()
        guide_step(st, None, explain="CARBON IQ lists what the report does not say, and what that means for the analysis.",
                   example="Without MRC's production volume, its emissions intensity cannot be calculated.",
                   takeaway="Knowing what is missing is part of the answer; CARBON IQ never fills these gaps with invented data.")
        _next("recalculate the emissions ourselves to test the reported baseline.")
    elif i == 3:
        block_scope1(go)
        st.divider()
        block_scope2(go)
        guide_step(st, None, takeaway="Scope 1 is confirmed within its uncertainty. Scope 2 rests on a factor the report does not "
                                      "state — the first question to ask MRC.")
        _next("with the baseline tested, explore what could reduce it (hypothetical projects).")
    elif i == 4:
        p = M.params()
        st.warning(f"**Hypothetical scenario from here on** — target {M.target_t(p):,.0f} t/yr (8% of the reported baseline) and budget "
                   f"{sar(p['budget'])} are CARBON IQ assumptions; project sizes and costs are scaled from public benchmarks, not Ma'aden data.")
        block_projects(go, items)
        guide_step(st, None, example="Solar 10 MWp × 2,500 SAR/kWp = SAR 25M; it would cover about 6% of MRC's electricity.",
                   takeaway="Three projects create value; heat recovery cuts the most carbon but loses money at today's gas price.")
        _next("test every combination of these projects in thousands of possible futures.")
    elif i == 5:
        block_mc(go, items, MC_N)
        guide_step(st, None, explain=f"{MC_N:,} futures with the register's ranges for tariffs, savings and costs.",
                   takeaway="Probabilities show which plans survive savings and cost risk — and which only look good on average.")
        _next("choose the plan.")
    elif i == 6:
        block_portfolio(go, items)
        f = _feas(items, MC_N)
        det, ch = f["det_best"], f["cc_choice"]
        if det and ch:
            same = det["portfolio"] == ch["portfolio"]
            st.markdown(f"**Most-likely inputs:** {det['portfolio']} (NPV {sar(det['npv'])}). **With the 90%/90% confidence rule:** "
                        f"{ch['portfolio']} (expected NPV {sar(ch['e_npv'])}, target met in {ch['p_target']:.1%}, budget kept in "
                        f"{ch['p_budget']:.1%}). " + ("Both views agree." if same else "The confidence rule changes the choice."))
        guide_step(st, None, takeaway="The plan is chosen by value within budget, target and confidence — not by ranking projects one by one.")
        _next("turn this into a recommendation, with its limits.")
    else:
        render_recommendation()


def render_recommendation(items=tuple(), n=MC_N):
    p = M.params(dict(items))
    f = _feas(items, n)
    ch, bv = f["cc_choice"], f["best_value_plan"]
    if ch:
        st.success(f"**Recommendation for the hypothetical MRC scenario:** fund **{ch['portfolio']}** — expected NPV {sar(ch['e_npv'])}, "
                   f"expected cut {ch['e_t12']:,.0f} tCO₂e/yr against a {f['target_t']:,.0f} t target, target met in {ch['p_target']:.1%} "
                   f"and budget kept in {ch['p_budget']:.1%} of {n:,} simulated futures (SAR {p['budget'] / 1e6:,.0f}M budget).")
    else:
        st.error("No plan meets both confidence rules within the hypothetical budget; no recommendation is forced.")
    if f.get("knife_edge"):
        alt = f.get("robust_alternative")
        st.warning(f"⚠ **This choice is on a knife-edge:** it needs {sar(ch['budget_needed'])} of the {sar(p['budget'])} budget to pass the 90% "
                   "budget rule, so a different random sample or a slightly higher cost estimate can change the choice. Management "
                   "decides: accept a contingency above the budget, or choose the plan that passes clearly"
                   + (f" — **{alt['portfolio']}** (expected NPV {sar(alt['e_npv'])}, budget kept in {alt['p_budget']:.1%})" if alt else "")
                   + ". CARBON IQ does not raise the budget on its own.")
    st.markdown("**Before acting on it, MRC would need to verify:**\n"
                "1. The Scope 2 factor and method behind 96,671 t (it decides how many tonnes the electricity projects save).\n"
                "2. Supplier quotations for solar, motors and drives, and compressed air (all costs here are scaled assumptions).\n"
                "3. Sub-metered end-use shares (motors, compressed air) and roof area.\n"
                f"4. MRC's own target and budget ({p['target_share']:.0%} and SAR {p['budget'] / 1e6:,.0f}M are illustrative).")
    st.markdown("**Limitations:** reported data are annual totals (no missing-data estimation possible); value of information and "
                "timing were not run for MRC; inputs are simulated independently; the result illustrates the method on a real energy "
                "profile and is **not** a recommendation to Ma'aden.")
    learn(st, "budget")
    learn(st, "stability")
    guide_step(st, None, takeaway="From a reported baseline to a recommendation with stated confidence, named trade-offs and an "
                                  "honest list of what must be verified with real data.")
