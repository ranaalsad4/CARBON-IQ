"""CARBON IQ v2 - Streamlit interface.   Run:  streamlit run app.py

v2 adds a Learning Mode / Presentation Mode switch, a dataset selector (synthetic plant or Ma'aden Rolling Company 2025
reported data), an eight-step guided demo, a Learning Center, and 'Learn how this works' / 'Source & calculation' panels.
The analysis code below is unchanged from Phase B except for its position in the numbered workflow tabs: every number is
still computed live by the carbon_iq package (model v1.3). Research prototype only.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from carbon_iq import decisions as D
from carbon_iq import engine as E
from carbon_iq import optimize as O
from carbon_iq import sensitivity as S
from carbon_iq import timing as TM
from carbon_iq import uncertainty as U
from carbon_iq import voi as V
from carbon_iq.dataquality import estimate as ES, integrate as DI, quality as DQ, synth as DS
from carbon_iq.assumptions import (A5_CHANGE_LABELS, EF_GRID_EVIDENCE, GAS_SCENARIOS, MODEL_VERSION, P, PROJECTS, PV_CAPEX_SCENARIOS,
                                   TARIFF_SCENARIOS, V12_CHANGES, base_values)

from carbon_iq.ui import learn_ui as LU, theme as TH

APP_VERSION = "2.1"
st.set_page_config(page_title="CARBON IQ", page_icon="🌿", layout="wide")
TH.inject(st)
st.session_state["_learn_n"] = 0                      # unique keys for the 'advanced details' toggles in this run
DATASETS = ["Synthetic Saudi metal-fabrication plant", "Ma'aden Rolling Company (MRC) – 2025 reported data"]
PAGES = ["Guided demo", "Analysis workspace", "Learning Center"]
with st.sidebar:
    st.markdown("## 🌿 CARBON IQ")
    st.caption(f"Carbon investment decision support · app v{APP_VERSION} · model v{MODEL_VERSION}")
    mode = st.radio("Mode", ["Learning Mode", "Presentation Mode"], key="mode",
                    help="Learning Mode adds 'Learn how this works' explanations. Both modes use exactly the same calculations.")
    dataset = st.radio("Dataset", DATASETS, key="dataset")
    page = st.radio("Go to", PAGES, key="nav")
    st.divider()
SYN = dataset == DATASETS[0]
TH.hero(st, "CARBON IQ — carbon investment decision support",
        ("Synthetic Saudi metal-fabrication plant (hypothetical data)" if SYN else
         "Ma'aden Rolling Company — 2025 reported energy and emissions; investment scenario hypothetical")
        + " · statistics, simulation and optimisation (no machine-learning model) · research prototype, not investment advice")
if page == "Guided demo":
    from carbon_iq import demo_view
    demo_view.render(st, go)
    st.stop()
if page == "Learning Center":
    from carbon_iq.ui import learning_center
    learning_center.render(st)
    st.stop()
if not SYN:
    from carbon_iq.ui import mrc_view
    mrc_view.render_workspace(go)
    st.stop()

base = base_values()
with st.sidebar, st.expander("⚙️ Advanced settings (synthetic plant)", expanded=False):
    st.header("Decision settings")
    budget = st.number_input("Capital budget (SAR)", 1_000_000, 10_000_000, int(base["budget"]), 250_000, key="budget")
    share = st.slider("Scope 1+2 reduction target", 0.0, 0.25, float(base["target_share"]), 0.01, key="target")
    alpha = st.slider("Required probability of meeting the target", 0.5, 0.99, float(base["chance_level"]), 0.01, key="alpha")
    rate = st.slider("Real discount rate", 0.02, 0.14, float(base["discount_rate"]), 0.005, key="rate")
    tariff = st.slider("Electricity tariff today (SAR/kWh)", 0.12, 0.30, float(base["tariff"]), 0.01, key="tariff")
    gas = st.slider("Gas price today (USD/MMBtu)", 1.5, 8.0, float(base["gas_price_usd"]), 0.05, key="gas")
    n = st.select_slider("Monte Carlo scenarios", options=[2000, 5000, 10000, 20000], value=5000, key="n")
    basis = st.radio("Carbon-target basis", ["reporting", "physical", "baseline"], key="basis",
                     format_func=lambda b: {"reporting": "fixed reporting baseline (primary)",
                                            "physical": "sampled emission factors (sensitivity)",
                                            "baseline": "uncertain baseline (sensitivity)"}[b])
    use_rel = st.checkbox("Require actual capex within budget (primary rule)", value=True, key="use_rel")
    rel = st.slider("…with probability at least", 0.5, 0.99, float(base["budget_chance_level"]), 0.01, key="rel", disabled=not use_rel)
    st.caption("Price settings shift the deterministic case and the centre of the Monte Carlo ranges.")
    if n != 20000:
        st.info(f"Using {n:,} scenarios for speed. The report and workbook use 20,000 (seed 20261024), so simulated "
                "figures here differ slightly; choose 20,000 to reproduce them.")

p = dict(base)
p.update(budget=budget, target_share=share, chance_level=alpha, discount_rate=rate, tariff=tariff, gas_price_usd=gas)
T = E.target_t(p)


@st.cache_resource(show_spinner=False)
def scenarios(n, rate, tariff, gas, basis):
    s = U.sample(n)
    s["discount_rate"] = np.full(n, rate)
    s["tariff"] = s["tariff"] + (tariff - base["tariff"])
    s["gas_price_usd"] = s["gas_price_usd"] * gas / base["gas_price_usd"]
    return U.Scenarios(params=s, basis=basis)


@st.cache_data(show_spinner=False)
def tariff_table(n, budget, alpha, beta):
    return D.tariff_scenarios(n, 20261024, budget, alpha, beta)


@st.cache_data(show_spinner=False)
def a5_scenario_tables(n, budget, alpha, beta):
    return D.gas_scenarios(n, 20261024, budget, alpha, beta), D.pv_capex_scenarios(n, 20261024, budget, alpha, beta)


prj, inter = E.projects(p)
best, rows = O.enumerate_best(prj, inter, budget, T)
sc = scenarios(n, rate, tariff, gas, basis)
a_eff = U.alpha_saa(alpha, n)                       # sampling-tightened in-sample levels (see uncertainty.alpha_saa)
breq = U.alpha_saa(rel, n) if use_rel else None

WS = ["1 · Emissions", "2 · Data gaps", "3 · Projects", "4 · Portfolio", "5 · Uncertainty & confidence", "6 · Value of information",
      "7 · Sensitivity", "8 · Timing", "Evidence & scenarios", "Assumptions"]
tabs = st.tabs(WS)                                    # v2: Phase B tabs re-ordered as a numbered workflow; contents unchanged
_T = {"emis": tabs[0], "gaps": tabs[1], "proj": tabs[2], "port": tabs[3], "unc": tabs[4], "voi": tabs[5], "sens": tabs[6],
      "time": tabs[7], "evid": tabs[8], "assum": tabs[9]}


def intro(text):
    if LU.is_learning(st):
        TH.box(st, text)

with _T["emis"]:
    intro("<b>Step 1 · Emissions.</b> Activity data × emission factors, summed by GHG Protocol scope, with the uncertainty of each "
          "source. The target is a share of Scope 1+2.")
    b = E.baseline(p)
    tot = E.scope_totals(b)
    unc, ut = E.uncertainty_table(b)
    k = st.columns(5)
    k[0].metric("Scope 1", f"{tot['Scope 1']:,.0f} t")
    k[1].metric("Scope 2", f"{tot['Scope 2']:,.0f} t")
    k[2].metric("Scope 3 (Cat 1 + 4)", f"{tot['Scope 3']:,.0f} t")
    k[3].metric("Scope 1+2 uncertainty", f"±{ut['Scope 1+2'][1]:.1f}%")
    k[4].metric("Reduction target", f"{T:,.0f} t/yr")
    df = pd.DataFrame([{"Source": r["source"], "Scope": r["scope"], "Activity": f"{r['activity']:,.0f} {r['unit']}",
                        "Emissions (t)": round(r["emissions_t"], 1), "±% (95%)": round(r["u_combined_pct"], 1), "Quality": r["quality"]}
                       for r in unc])
    st.dataframe(df, hide_index=True, width="stretch")
    st.caption("GHG Protocol first-order propagation: U = sqrt(Ua² + Uef²) per source; totals combine as sqrt(Σ(E·U)²)/ΣE.")
    LU.learn(st, "ghg")
    LU.learn(st, "factors")
    LU.learn(st, "uncertainty")
    LU.source(st, "emissions and target", [
        LU.result_row("Scope 1+2", f"{tot['Scope 1+2']:,.0f} t", "calculated", "Σ activity × factor (engine.baseline)", "synthetic plant",
                      "engine.scope_totals()", f"±{ut['Scope 1+2'][1]:.1f}% (95%)", "sets the target"),
        LU.result_row("Reduction target", f"{T:,.0f} t/yr", "calculated", f"{share:.0%} × Scope 1+2 (target share is a hypothetical "
                      "management choice)", "synthetic plant", "engine.target_t()", "none (fixed reporting baseline)",
                      "higher target → fewer feasible portfolios")]
        + LU.param_rows(["elec_mwh", "ef_grid", "gas_gj", "ef_gas", "diesel_forklift_l", "diesel_genset_l", "ef_diesel", "steel_t",
                         "ef_steel_incumbent"], used_by="engine.baseline()"))

with _T["proj"]:
    intro("<b>Step 3 · Projects.</b> Each project's cost, yearly saving, value today (NPV), return (IRR), payback and cost per "
          "tonne (MAC). Costs other than solar are hypothetical.")

    def _irr(i, d):
        r_ = E.project_irr(d, p.get("pv_degradation", 0.0)) if i == "A" else E.irr(float(d["capex"]), float(d["annual_cf"]), int(d["life"]))
        return f"{r_:.1%}" if r_ is not None else "n/a"
    st.dataframe(pd.DataFrame([{"Project": f"{i} {d['name']}", "Capex (SAR)": round(float(d["capex"])),
                                "Net cash flow (SAR/yr)": round(float(d["annual_cf"])), "Life (yr)": int(d["life"]),
                                "NPV (SAR)": round(float(d["npv"])), "IRR": _irr(i, d),
                                "Payback (yr)": round(E.simple_payback(float(d["capex"]), float(d["annual_cf"])), 1)
                                if float(d["annual_cf"]) > 0 else None,
                                "Scope 1+2 (t/yr)": round(float(d["scope12_t"]), 1),
                                "Scope 3 (t/yr)": round(float(d["scope3_t"]), 1), "MAC (SAR/t)": round(float(E.mac(d)))}
                               for i, d in prj.items()]), hide_index=True, width="stretch",
                 column_config={c_: st.column_config.NumberColumn(format="localized") for c_ in
                                ("Capex (SAR)", "Net cash flow (SAR/yr)", "NPV (SAR)", "MAC (SAR/t)")})
    fig = go.Figure(go.Bar(x=[f"{i}" for i in prj], y=[float(d["npv"]) / 1e6 for d in prj.values()],
                           marker_color=["#3E8E7E" if float(d["npv"]) > 0 else "#C8553D" for d in prj.values()]))
    fig.update_layout(title="NPV by project (SAR million)", yaxis_title="SAR million", xaxis_title="Project", height=320)
    st.plotly_chart(fig, width="stretch")
    st.caption("IRR and payback are display columns added in v2 from engine.irr()/project_irr() and engine.simple_payback(); "
               "the payback of a project with no positive yearly saving is left blank.")
    LU.learn(st, "npv")
    LU.learn(st, "irr")
    LU.learn(st, "mac")
    LU.learn(st, "roi")
    LU.source(st, "project inputs", LU.param_rows(["pv_kwp", "pv_capex_kw", "pv_yield", "pv_degradation", "tariff", "b_capex",
                                                   "b_saving_frac", "motor_share", "c_capex", "c_saving_frac", "compressed_air_share",
                                                   "d_capex", "d_saving_frac", "gas_price_usd", "e_capex", "f_premium", "discount_rate"],
                                                  used_by="engine.projects()"))

with _T["port"]:
    intro("<b>Step 4 · Portfolio.</b> All 64 combinations of the six projects are checked; the best is the highest NPV within the "
          "budget that meets the target. Common ranking rules are shown for comparison.")
    if best is None:
        _meet = [r_ for r_ in rows if r_["meets_target"]]          # v2.1: explain, never raise the budget automatically
        if _meet:
            _m = min(_meet, key=lambda r_: r_["capex"])
            st.error(f"No portfolio meets the target within SAR {budget:,.0f}. The cheapest plan that reaches {T:,.0f} t/yr is "
                     f"{_m['portfolio']} at SAR {_m['capex']:,.0f} (quoted capex, most-likely inputs) - the minimum budget under these "
                     "assumptions. CARBON IQ does not raise the budget itself; lower the target or change the budget in the settings.")
        else:
            st.error(f"No portfolio reaches {T:,.0f} t/yr at any budget: all six projects together cut at most "
                     f"{max(r_['scope12_t'] for r_ in rows):,.0f} t/yr. Lower the target or add projects.")
    else:
        st.success(f"Optimal portfolio: **{best['portfolio']}** · NPV SAR {best['npv']:,.0f} · "
                   f"{best['scope12_t']:,.0f} t/yr Scope 1+2 · capex SAR {best['capex']:,.0f}")
    bl = O.baselines(prj, inter, budget, T)
    st.dataframe(pd.DataFrame([{"Method": x["method"], "Portfolio": x["portfolio"], "Capex": round(x["capex"]),
                                "NPV (SAR)": round(x["npv"]), "Scope 1+2 (t/yr)": round(x["scope12_t"], 1),
                                "Meets target": x["meets_target"]} for x in bl]), hide_index=True, width="stretch")
    feas = [r for r in rows if r["within_budget"]]
    fig = go.Figure(go.Scatter(x=[r["scope12_t"] for r in feas], y=[r["npv"] / 1e6 for r in feas], mode="markers",
                               text=[r["portfolio"] for r in feas], marker=dict(color=["#1F3A5F" if r["feasible"] else "#B0B7C3" for r in feas])))
    fig.add_vline(x=T, line_dash="dash", line_color="#C8553D")
    fig.update_layout(title="All portfolios within budget (dark = meets target)", xaxis_title="Scope 1+2 reduction, t/yr",
                      yaxis_title="NPV, SAR million", height=380)
    st.plotly_chart(fig, width="stretch")
    LU.learn(st, "portfolio")
    LU.learn(st, "ranking")
    LU.learn(st, "multicriteria")
    LU.source(st, "optimal portfolio", [
        LU.result_row("Optimal portfolio NPV", f"SAR {best['npv']:,.0f}" if best else "none", "calculated",
                      "max NPV over all 64 portfolios with capex ≤ budget and cut ≥ target", "synthetic plant",
                      "optimize.enumerate_best() (checked by optimize.solve_milp())", "deterministic (see step 5)", "the D1 choice")]
        + LU.param_rows(["budget", "target_share"], used_by="optimize.enumerate_best()"))

with _T["unc"]:
    intro("<b>Step 5 · Uncertainty & confidence.</b> Every plan is simulated in many futures; decision rules D1–D4 differ in how much "
          "confidence they demand. D4 (carbon ≥ 90% and budget ≥ 90%) is the primary rule.")
    kb = sc.best_expected(budget)
    kc, ec, pc, okc = sc.decide(budget, T, a_eff)
    kj, ej, pj, okj = sc.decide(budget, T, a_eff, budget_reliability=breq) if use_rel else (None, None, None, False)
    kd = sc.index(best["ids"]) if best else None
    st.markdown("**Decision rules** — each answers a different question; both probabilities are shown for every portfolio.")
    c = st.columns(4)

    def card(col, title, k, note=""):
        if k is None:
            col.metric(title, "none feasible"); return
        x = sc.stats(k, T, budget=budget)
        col.metric(title, x["portfolio"], f"target {x['p_target']:.1%} · within budget {1 - x['p_over_budget']:.1%}")
        col.caption(f"E[NPV] SAR {x['e_npv']:,.0f}{note}")

    card(c[0], "D1 · Deterministic", kd, f" · NPV at base inputs SAR {best['npv']:,.0f}" if best else "")
    card(c[1], "D2 · Highest E[NPV]", kb)
    card(c[2], f"D3 · Carbon ≥{alpha:.0%}", kc if okc else None)
    card(c[3], f"D4 · Carbon ≥{alpha:.0%} + budget ≥{rel:.0%}" if use_rel else "D4 · (budget rule off)", kj if okj else None)
    if use_rel and not (kj is not None and okj):
        need = []
        for k in range(len(sc.ports)):
            if (sc.PT12[k] >= T).mean() >= a_eff:
                need.append((max(float(np.quantile(sc.PCAP[k], breq, method="higher")), float(sc.capex[k])), sc.name(k)))
        need.sort()
        msg = (f"No portfolio meets both requirements within SAR {budget:,.0f}. No recommendation is forced. "
               + (f"The smallest budget that would make the rule feasible is about SAR {need[0][0]:,.0f} ({need[0][1]})." if need else
                  "No portfolio meets the carbon requirement at any budget."))
        st.error(msg)
    st.caption(f"Chance constraints use sampling-tightened levels on these {n:,} scenarios (carbon {a_eff:.4f}"
               + (f", budget {breq:.4f}" if use_rel else "") + "). run_all.py also validates them on an independent 200,000-scenario sample.")
    tab = sorted(sc.table(budget, T), key=lambda r: -r["e_npv"])[:12]
    st.dataframe(pd.DataFrame([{"Portfolio": r["portfolio"], "Quoted capex": round(r["capex"]), "E[NPV]": round(r["e_npv"]),
                                "5th pct": round(r["p5_npv"]), "P(NPV<0)": f"{r['p_loss']:.1%}", "P(target)": f"{r['p_target']:.1%}",
                                "P(capex > budget)": f"{r['p_over_budget']:.1%}"} for r in tab]),
                 hide_index=True, width="stretch")
    st.caption("Quoted capex is checked against the budget (baseline feasibility); P(capex > budget) uses the uncertain actual cost.")
    fig = go.Figure()
    for k_ in {k for k in (kb, kc if okc else None) if k is not None}:
        fig.add_histogram(x=sc.PNPV[k_] / 1e6, name=sc.name(k_), opacity=0.6, nbinsx=60)
    fig.update_layout(barmode="overlay", title="NPV distribution", xaxis_title="SAR million", yaxis_title="Scenarios", height=340)
    st.plotly_chart(fig, width="stretch")
    LU.learn(st, "montecarlo")
    LU.learn(st, "ptarget")
    LU.learn(st, "budget")
    LU.source(st, "probabilities", [
        LU.result_row("Simulated futures", f"{n:,}", "hypothetical", "sidebar setting (report: 20,000, seed 20261024)", "synthetic plant",
                      "uncertainty.sample() → uncertainty.Scenarios", "sampling error shrinks with more futures", "all probabilities"),
        LU.result_row("Tightened levels", f"carbon {a_eff:.4f}" + (f", budget {breq:.4f}" if use_rel else ""), "calculated",
                      "required level + 1.645 × sampling standard error", "—", "uncertainty.alpha_saa()", "—",
                      "protects the 90% promise against sampling luck")]
        + LU.param_rows(["chance_level", "budget_chance_level", "tariff", "b_saving_frac", "c_saving_frac", "pv_capex_kw", "b_capex"],
                        used_by="uncertainty.sample() → Scenarios.decide()"))

with _T["voi"]:
    intro("<b>Step 6 · Value of information.</b> Which uncertainty, if resolved before investing, could change the decision — and is "
          "it worth its cost?")
    rk, noise = V.ranking(sc, budget, T, a_eff)
    c2 = st.columns(2)
    c2[0].metric("EVPI (all uncertainty resolved)", f"SAR {V.evpi(sc, budget, T, a_eff):,.0f}")
    c2[1].metric("Estimator noise floor (irrelevant variable)", f"SAR {noise:,.0f}")
    st.caption("Values are for the carbon rule D3. When a portfolio sits close to the required probability, the binning estimator "
               "picks up sampling noise; compare each EVPPI with the noise floor.")
    st.dataframe(pd.DataFrame([{"Information": r["information"], "EVPPI (SAR)": round(r["evppi_sar"]),
                                "Collection cost (SAR)": r["collection_cost_sar"], "Changes decision": r["decision_changes"]}
                               for r in rk]), hide_index=True, width="stretch")
    ev, _, _ = V.evsi_audit(sc, budget, T, a_eff)
    st.info(f"Imperfect motor-system audit (error ±3 pp): EVSI ≈ SAR {ev:,.0f} vs assumed cost SAR {P['cost_motor_audit'].value:,.0f}. "
            "Poor data quality alone does not make information valuable: only information that can change the choice has value.")
    LU.learn(st, "evpi")
    LU.learn(st, "voi")
    LU.source(st, "information costs", LU.param_rows(["cost_motor_audit", "cost_submeter", "cost_supplier_data", "cost_pv_study"],
                                                     used_by="voi.ranking() / voi.evsi_audit()"))

with _T["time"]:
    intro("<b>Step 8 · Timing.</b> Should heat recovery (project D) start now or wait for a possible gas-price reform? "
          "Implemented for this one project and one price only.")
    pr = st.slider("Probability of a gas-price reform within one year", 0.0, 1.0, float(base["tree_p_reform"]), 0.05, key="preform")
    gr = st.slider("Gas price after reform (USD/MMBtu)", 2.0, 9.0, float(base["tree_g_reform"]), 0.025, key="greform")
    t = TM.decision_tree(p_reform=pr, g_reform=gr, g_now=gas)
    c = st.columns(3)
    c[0].metric("Invest now (expected NPV)", f"SAR {t['npv_invest_now']:,.0f}")
    c[1].metric("Wait one year", f"SAR {t['value_wait_one_year']:,.0f}")
    c[2].metric("Decision", t["decision"])
    g = TM.gbm_trigger()
    st.caption(f"Static break-even ${t['static_breakeven_usd']:.2f}/MMBtu · GBM closed-form trigger ${g['trigger_usd']:.2f}/MMBtu "
               f"(multiplier {g['multiplier']:.2f}). The log-OU LSMC extension (KAPSARC DP49 calibration) is in run_all.py outputs.")
    LU.learn(st, "timing")
    LU.source(st, "timing inputs", LU.param_rows(["tree_p_reform", "tree_g_reform", "gas_price_usd", "ro_sigma", "ro_mu_gbm", "d_capex",
                                                  "d_saving_frac"], used_by="timing.decision_tree() / timing.gbm_trigger()"))

with _T["sens"]:
    intro("<b>Step 7 · Sensitivity.</b> Which assumptions move the value most, and where would the recommendation change?")
    ids = tuple(best["ids"]) if best else ("A", "B")
    tor = S.tornado(ids)[:8]
    fig = go.Figure()
    fig.add_bar(y=[r["parameter"] for r in tor][::-1], x=[(r["npv_low"] - r["base_npv"]) / 1e6 for r in tor][::-1], orientation="h", name="5th pct")
    fig.add_bar(y=[r["parameter"] for r in tor][::-1], x=[(r["npv_high"] - r["base_npv"]) / 1e6 for r in tor][::-1], orientation="h", name="95th pct")
    fig.update_layout(barmode="overlay", title=f"Change in NPV of {'+'.join(ids)} (SAR million)", height=360)
    st.plotly_chart(fig, width="stretch")
    st.caption("Each bar moves one input from its 5th to its 95th percentile with all others at their register values.")
    LU.learn(st, "sensitivity")
    LU.learn(st, "stability")
    LU.source(st, "sensitivity inputs", LU.param_rows([r_["parameter"] for r_ in tor if r_["parameter"] in P],
                                                      used_by="sensitivity.tornado()"))

with _T["evid"]:
    LU.learn(st, "factors")
    st.markdown("**Industrial electricity tariff scenarios** — no single rate is asserted for 2027 onwards.")
    tt = tariff_table(min(n, 5000), budget, alpha, rel)
    ev = {e["id"]: e for e in TARIFF_SCENARIOS}
    st.dataframe(pd.DataFrame([{"Scenario": f"{r['id']} {r['label']}", "SAR/kWh": r["tariff"], "Deterministic": r["deterministic"],
                                "Highest E[NPV]": r["best_expected"], "Carbon CC": r["chance_constrained"], "Carbon + budget CC": r["joint"],
                                "Evidence": ev[r["id"]]["status"], "Effective": ev[r["id"]]["effective"]} for r in tt]),
                 hide_index=True, width="stretch")
    gs_, ps_ = a5_scenario_tables(min(n, 5000), budget, alpha, rel)

    def _scen_df(rows_, col, unit, ev_):
        return pd.DataFrame([{"Scenario": f"{r['id']} {r['label']}", unit: r[col], "Deterministic": r["deterministic"],
                              "Highest E[NPV]": r["best_expected"], "Carbon CC": r["chance_constrained"], "Carbon + budget CC": r["joint"],
                              "Source": ev_[r["id"]]["url"]} for r in rows_])
    st.markdown("**Industrial methane price scenarios** — 2026 price not officially published.")
    st.dataframe(_scen_df(gs_, "gas_price_usd", "USD/MMBtu", {e["id"]: e for e in GAS_SCENARIOS}), hide_index=True, width="stretch")
    st.markdown("**Rooftop PV cost scenarios** — the reference is one public benchmark, not a quotation; the recommendation depends on it.")
    st.dataframe(_scen_df(ps_, "pv_capex_kw", "SAR/kWp", {e["id"]: e for e in PV_CAPEX_SCENARIOS}), hide_index=True, width="stretch")
    st.markdown(f"**Grid emission factor evidence** — reference {P['ef_grid'].value:.3f} tCO2e/MWh, derived from the KSA Biennial "
                "Transparency Report (2021 inventory) and GASTAT 2021 generation.")
    st.dataframe(pd.DataFrame([{"Evidence": e["what"], "Value": e["value"], "Use": e["use"]} for e in EF_GRID_EVIDENCE]),
                 hide_index=True, width="stretch")

with _T["assum"]:
    st.dataframe(pd.DataFrame([{"Key": k, "Value": x.value, "Unit": x.unit, "Evidence": x.evidence, "Status": x.status,
                                "Changed in v1.3": A5_CHANGE_LABELS.get(k, ""), "Published": x.published, "Geography": x.geography,
                                "Source / rationale": x.source} for k, x in P.items()]), hide_index=True, width="stretch", height=520)
    st.caption("Evidence: external = cited source; derived = computed from cited values; hypothetical = illustrative case assumption "
               "(not company data, not a quotation). No input is a measured factory observation. "
               f"{len(V12_CHANGES)} inputs changed from v1.2 (see the A5 report).")
    st.caption("Projects: " + "; ".join(f"{k} = {v}" for k, v in PROJECTS.items()))


# ------------------------------------------------------------------ A4: missing-data review
@st.cache_resource(show_spinner=False)
def a4_ledger(raw_csv, year, site, name):
    import io
    return ES.Ledger(pd.read_csv(io.StringIO(raw_csv)), year, site, source_name=name)


@st.cache_data(show_spinner=False)
def a4_decide(activity_items, n, budget, alpha, beta):
    r, _ = DI.run_decisions(dict(activity_items), n=n, budget=budget, alpha=alpha, beta=beta)
    return r


@st.cache_data(show_spinner=False)
def a4_margins(activity_items, n, budget, alpha, beta):
    from carbon_iq.dataquality import stability as ST
    return ST.margins(dict(activity_items), n=n, budget=budget, alpha=alpha, beta=beta)


@st.cache_data(show_spinner=False)
def a4_stability(activity_items, n, budget, alpha, beta):
    from carbon_iq.dataquality import stability as ST
    act = dict(activity_items)
    keys = [k for k in ("elec_mwh", "gas_gj") if act.get(k, (0, 0))[1] > 0]
    a = ST.assess(act, n=n, K=20, budget=budget, alpha=alpha, beta=beta, with_switch=bool(keys), switch_keys=keys or None)
    return a["rules"], a["switch_points"]


@st.cache_data(show_spinner=False)
def a4_voi(activity_items, n, budget, alpha, beta):
    return DI.information_value(dict(activity_items), n=n, seeds=(20261024,), n_nodes=8, budget=budget, alpha=alpha, beta=beta)


@st.cache_data(show_spinner=False)
def a4_edges(activity_items, n, budget, alpha, beta):
    """Rules whose choice changes when one estimated stream is at the edge of its 95% interval."""
    act = dict(activity_items)
    r0 = a4_decide(activity_items, n, budget, alpha, beta)
    out = {}
    for b in DI.sensitivity_bounds(act, n=n, budget=budget, alpha=alpha, beta=beta):
        for rule in DI.RULES:
            if b[rule] != r0[rule]:
                out.setdefault(rule, []).append(f"{b['key']} at the {b['bound']} end of its 95% interval gives {b[rule]}")
    return out


def a4_stability_flags(margin_rows):
    out = {}
    for m in margin_rows:
        if m["sampling_unstable"]:
            out.setdefault(m["rule"], []).append(f"{m['threshold']}: {m['value']:.4f} vs {m['limit']:.4f} "
                                                 f"({m['margin_se']:+.1f} Monte Carlo standard errors)")
    return out


A4N = 20000          # the data-gap analysis always uses the report's 20,000 scenarios: the knife-edge needs them

with _T["gaps"]:
    import copy
    st.markdown("**Missing-data review.** Monthly activity records are checked, gaps are estimated with documented statistical "
                "rules (no machine learning), and nothing enters the decision until a reviewer approves it. Missing values are "
                "never treated as zero; the uploaded records are never overwritten.")
    LU.learn(st, "dataquality")
    LU.learn(st, "stability")
    src = st.radio("Dataset", ["Synthetic demo (degraded copy of known truth)", "Synthetic severe gap (6 months missing)", "Upload CSV"],
                   key="a4_src", horizontal=True)
    tmpl = "record_id,site,period,stream,value,unit,source,note\nR00001,PLANT-01,2026-01,electricity,864.0,MWh,utility bill,\n"
    st.download_button("CSV template", tmpl, "carbon_iq_activity_template.csv", key="a4_tmpl")
    raw, truth = None, None
    if src.startswith("Synthetic demo"):
        raw = DS.demo_incomplete()[0]; name = "SYNTHETIC demo dataset"; truth = DS.truth_case()
    elif src.startswith("Synthetic severe"):
        raw = DS.demo_severe(); name = "SYNTHETIC severe-gap dataset"
    else:
        up = st.file_uploader("Long-format CSV: site, period (YYYY-MM), stream, value, unit [, record_id, source, note]", type="csv", key="a4_up")
        st.caption("Streams: " + ", ".join(f"{k} ({c['unit']})" for k, c in DQ.STREAMS.items()) + ". Include the previous year for "
                   "seasonal estimates and change detection.")
        if up is not None:
            raw = pd.read_csv(up); name = up.name
    if raw is not None:
        try:
            unknown = DQ.validate_schema(raw)
            years = sorted({int(str(x)[:4]) for x in raw["period"].dropna()})
            sites = sorted(raw["site"].dropna().astype(str).unique())
        except Exception as e:  # noqa: BLE001
            st.error(f"File not usable: {e}"); raw = None
    if raw is not None:
        c1, c2 = st.columns(2)
        year = c1.selectbox("Reporting year", years[::-1], key="a4_year")
        site = c2.selectbox("Site", sites, key="a4_site")
        L = copy.deepcopy(a4_ledger(raw.to_csv(index=False), year, site, name))
        if unknown:
            st.warning("Ignored unknown streams: " + ", ".join(unknown))
        st.caption(f"{len(L.raw)} records · sha256 {L.raw_hash[:16]}… (original kept unchanged) · intervals calibrated on synthetic "
                   f"data (factor {ES.CAL_MONTHLY:.3f}, within-stream correlation {ES.RHO_ANNUAL}) — re-fit on real data before relying on them")
        st.markdown("**1 · Data-quality findings**")
        sm = DQ.summary(L.cells)
        st.dataframe(sm, width="stretch")
        st.dataframe(L.issues, hide_index=True, width="stretch", height=220)
        warns = L.table[L.table.warning != ""]
        for _, w in warns.iterrows():
            st.warning(f"**{w.period} {w.stream}** — {w.warning}" + (f" → {w.refusal}" if w.refusal else ""))
        st.markdown("**2 · Proposed estimates — review and decide**")
        gaps = L.table[L.table.decision == "pending"].copy()
        bulk = st.checkbox("Approve every proposed estimate (outliers and refusals excluded)", key="a4_bulk")
        bulk_out = st.checkbox("…and replace flagged outliers with their estimates", key="a4_bulk_out", disabled=not bulk)
        bulk_cp = st.checkbox("…and I confirm that no operational change occurred where one was flagged (override; labelled in the lineage)",
                              key="a4_bulk_cp", disabled=not bulk)
        if len(gaps):
            view = pd.DataFrame(dict(period=gaps.period, stream=gaps.stream, status=gaps.status,
                                     issue=gaps.issues.map(lambda x: "; ".join(x)), reported=gaps.value, method=gaps.method,
                                     estimate=gaps.estimate, low95=gaps.low95, high95=gaps.high95, refusal=gaps.refusal,
                                     warning=gaps.warning, fallback=gaps.fallback_estimate))
            def _default(r, st_, fb):
                if not bulk:
                    return "pending"
                if r.startswith("OPERATIONAL_CHANGE") and bulk_cp and fb == fb:
                    return "override_change"
                if not r and (st_ != "outlier" or bulk_out):
                    return "approve"
                return "pending"
            view["decision"] = [_default(r, st_, fb) for r, st_, fb in zip(gaps.refusal, gaps.status, gaps.fallback_estimate)]
            ed = st.data_editor(view.round({"reported": 1, "estimate": 1, "low95": 1, "high95": 1, "fallback": 1}), hide_index=True,
                                width="stretch", key=f"a4_ed_{name}_{year}_{site}",
                                disabled=[c for c in view.columns if c != "decision"],
                                column_config={"decision": st.column_config.SelectboxColumn(
                                    "decision", options=["pending", "approve", "reject", "keep", "confirm_zero", "override_change"], required=True)})
            st.caption("approve = use the estimate · reject = leave the gap open · keep = an outlier is a real value · "
                       "confirm_zero = a suspected zero is a real zero · override_change = a flagged operational change did not happen "
                       "(the fallback estimate is used and labelled). Intervals: 95% prediction intervals from leave-one-out back-tests, "
                       "calibrated on synthetic hold-out data.")
            for _, r in ed.iterrows():
                if r.decision != "pending":
                    try:
                        L.decide(site, r.period, r.stream, r.decision, "dashboard reviewer")
                    except ValueError as e:
                        st.warning(f"{r.period} {r.stream}: {e}")
        else:
            st.success("No gaps, outliers or suspected zeros found.")
        ann = L.annual()
        st.markdown("**3 · Annual totals (measured vs estimated)**")
        st.dataframe(ann[["stream", "unit", "n_measured", "n_estimated", "n_unresolved", "measured_total", "estimated_total", "total",
                          "sd_estimate", "complete"]].round(1), hide_index=True, width="stretch")
        st.markdown("**4 · Before and after: carbon footprint and recommendation** (register prices; budget and probability rules "
                    f"from the sidebar; {A4N:,} scenarios, seed 20261024, as in the report)")
        base_act = {k: (float(base[k]), 0.0) for k in DI.ACTIVITY_KEYS}
        try:
            act = DI.activity_from_annual(ann)
        except DI.IncompleteData as e:
            act = None
            st.error(f"Decision blocked - {e}. Missing data are not counted as zero.")
        zero = dict(base_act); zero.update(DI.naive_zero_activity(L))
        cols_ = [(f"Register (model v{MODEL_VERSION} reference)", base_act), ("Gaps counted as zero (incorrect practice)", zero)]
        if act is not None:
            full = dict(base_act); full.update(act)
            cols_.append(("Estimates approved (uncertainty included)", full))
            if truth is not None:
                f_ = L.final()
                tv = truth.set_index(["period", "stream"]).value
                known = dict(full)
                for _, rr in ann.iterrows():
                    k_ = DI._key(rr)
                    if k_ is None or rr.n_estimated == 0:
                        continue
                    g_ = f_[f_.stream == rr.stream]
                    known[k_] = (float(sum(tv[(p_, rr.stream)] if lab_.startswith("estimated") else v_
                                           for p_, lab_, v_ in zip(g_.period, g_.final_label, g_.final_value))), 0.0)
                cols_.append(("After obtaining the missing records (synthetic truth)", known))
        res_ = [(lab, a_, a4_decide(tuple(sorted(a_.items())), A4N, budget, alpha, rel)) for lab, a_ in cols_]
        flags_ = {}
        for lab, a_, _ in res_:
            fl_ = a4_stability_flags(a4_margins(tuple(sorted(a_.items())), A4N, budget, alpha, rel))
            for rule, msgs in a4_edges(tuple(sorted(a_.items())), A4N, budget, alpha, rel).items():
                fl_.setdefault(rule, []).extend(msgs)
            flags_[lab] = fl_
        tab_ = []
        for lab, a_, r in res_:
            s12sd = float(np.sqrt(sum((P[DI.S12_FACTOR[k]].value * s) ** 2 for k, (_, s) in a_.items() if k in DI.S12_FACTOR)))
            tab_.append({"": lab, "Scope 1+2 (t)": f"{r['scope12']:,.0f} ± {1.96 * s12sd:,.0f}" if s12sd else f"{r['scope12']:,.0f}",
                         "Target cut (t)": f"{r['target_t']:,.0f}",
                         "D1 deterministic": r["D1"] + (" ⚠" if "D1" in flags_[lab] else ""),
                         "D2 max E[NPV]": r["D2"] + (" ⚠" if "D2" in flags_[lab] else ""),
                         "D3 carbon 90%": r["D3"] + (" ⚠" if "D3" in flags_[lab] else ""),
                         "D4 carbon + budget 90%": r["D4"] + (" ⚠" if "D4" in flags_[lab] else ""),
                         "P(target) A+B": round(r["p_target[A+B]"], 4), "P(target) A+B+C": round(r["p_target[A+B+C]"], 4),
                         "P(target) A+C+D": round(r["p_target[A+C+D]"], 4),
                         "P(capex ≤ budget) A+B": round(r["p_budget[A+B]"], 4)})
        st.dataframe(pd.DataFrame(tab_), hide_index=True, width="stretch")
        fig_ = go.Figure()
        for lab, a_, r in res_:
            s12sd = float(np.sqrt(sum((P[DI.S12_FACTOR[k]].value * s) ** 2 for k, (_, s) in a_.items() if k in DI.S12_FACTOR)))
            fig_.add_bar(x=[lab.split(" (")[0]], y=[r["scope12"]], error_y=dict(type="data", array=[1.96 * s12sd]),
                         text=[f"D3 {r['D3']} · D4 {r['D4']}"], textposition="outside", showlegend=False)
        fig_.update_layout(height=320, margin=dict(t=30, b=10), yaxis_title="Scope 1+2 (tCO2e/yr), ±95% from estimation",
                           title="Carbon footprint and recommendation under each data treatment")
        st.plotly_chart(fig_, width="stretch")
        st.caption("⚠ = not a stable choice: it sits within 2 Monte Carlo standard errors of a feasibility threshold, or it changes when "
                   "one estimated stream is at the edge of its 95% interval (see section 5). "
                   "Zero-filling understates emissions and can make a portfolio look sufficient or affordable when it is not.")
        if act is not None:
            full = dict(base_act); full.update(act)
            items = tuple(sorted(full.items()))
            st.markdown("**5 · Decision stability**")
            fl = a4_stability_flags(a4_margins(items, A4N, budget, alpha, rel))
            for rule, msgs in a4_edges(items, A4N, budget, alpha, rel).items():
                fl.setdefault(rule, []).extend(msgs)
            for rule, msgs in fl.items():
                st.warning(f"**{rule} is not a stable choice** — " + "; ".join(msgs) + ". A small change in the data or in the "
                           "random sample can change this recommendation; do not treat it as settled.")
            if not fl:
                st.success("Every rule keeps its choice across the estimates' 95% intervals and is more than 2 Monte Carlo "
                           "standard errors from its thresholds.")
            if st.toggle("Run the full stability check (plausible true datasets and switch points; about 30 s)", key="a4_stab"):
                rules_, sw_ = a4_stability(items, A4N, budget, alpha, rel)
                st.dataframe(pd.DataFrame(rules_)[["rule", "choice", "status", "agreement", "min_switch_rel", "reasons"]],
                             hide_index=True, width="stretch")
                for r_ in rules_:
                    if r_["status"] != "STABLE":
                        st.warning(f"**{r_['rule']} ({r_['choice']}) {r_['status']}**: {r_['reasons']}")
                if sw_:
                    st.dataframe(pd.DataFrame(sw_).dropna(subset=["switch_rel"]), hide_index=True, width="stretch")
            st.markdown("**6 · Which missing records are worth collecting?**")
            st.caption("Pre-posterior value of information under each rule (one scenario seed, 8 nodes in the app; the report uses "
                       "3 seeds and 16 nodes). Costs are hypothetical staff-time assumptions.")
            if st.toggle("Compute the value of collecting the missing records (about 20 s)", key="a4_voi"):
                vv = pd.DataFrame(a4_voi(items, A4N, budget, alpha, rel))
                if len(vv):
                    st.dataframe(vv[["measurement", "label", "rule", "prior_choice", "posterior_choices", "value_npv", "d_p_target",
                                     "cost_sar", "net_value"]].round({"value_npv": 0, "d_p_target": 4, "net_value": 0}),
                                 hide_index=True, width="stretch")
                else:
                    st.info("No estimated values: nothing to collect.")
        st.download_button("Download lineage (CSV)", L.lineage().to_csv(index=False), "carbon_iq_lineage.csv", key="a4_dl")
