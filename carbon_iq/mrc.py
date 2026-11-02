"""v2 - Ma'aden Rolling Company (MRC) real-data case study.

Three kinds of numbers, never mixed up:
  REPORTED      values copied from the Ma'aden Sustainability Data Book 2025 (page and table given for each). They are
                annual totals for 2025; the book gives no monthly data, no production volume for MRC, no end-use split,
                no emission-factor list and no project costs.
  CALCULATED    values CARBON IQ derives from the reported ones with published factors (IPCC 2006) or simple arithmetic.
  HYPOTHETICAL  the investment scenario (project sizes, costs, budget, target). These are NOT Ma'aden values: they are
                benchmark-based assumptions taken from the CARBON IQ assumption register and scaled to MRC's reported
                energy use, so that the existing methods can be demonstrated on a real energy profile.

The investment scenario reuses the unchanged engine (engine.projects, engine.portfolio, optimize.all_portfolios) and the
register's probability distributions (uncertainty._draw); nothing in the model v1.3 calculations is altered.
"""
import math
from dataclasses import dataclass

import numpy as np

from . import engine as E
from . import optimize as O
from .assumptions import P, base_values
from .uncertainty import _draw, alpha_saa

DATABOOK = "Ma'aden Sustainability Data Book 2025"
DATABOOK_NOTE = ("Annual 2025 values. Ma'aden's data book has no printed page numbers; 'PDF page' counts the pages of the file "
                 "supplied (14 pages). Energy, Scope 1 and Scope 2 are covered by Bureau Veritas' limited assurance (ISAE 3000 / "
                 "ISAE 3410) for Ma'aden and seven affiliates including MRC (PDF pages 11-13).")
COMPANY = "Ma'aden Rolling Company (MRC), Saudi Arabia"
YEAR = 2025
GJ_PER_MWH = 3.6                  # definition: 1 MWh = 3,600 MJ = 3.6 GJ
GWP_CH4, GWP_N2O = 28, 265        # IPCC AR5 100-year values, as in the CARBON IQ register and Saudi BTR1


@dataclass(frozen=True)
class Item:
    key: str
    label: str
    value: float
    unit: str
    kind: str                     # reported | calculated | benchmark | hypothetical
    source: str
    page: str = ""
    note: str = ""
    url: str = ""


T51 = "table 'ASI 5.1 - GHG emissions & energy use', column MRC, year 2025"
REPORTED = {
    "energy_total_gj": Item("energy_total_gj", "Total energy consumption", 2_172_929, "GJ", "reported", DATABOOK, "PDF page 5", T51),
    "natural_gas_gj": Item("natural_gas_gj", "Natural gas", 1_104_220, "GJ", "reported", DATABOOK, "PDF page 5", T51),
    "diesel_heating_gj": Item("diesel_heating_gj", "Diesel and heating fuel", 26_749, "GJ", "reported", DATABOOK, "PDF page 5", T51),
    "gasoline_gj": Item("gasoline_gj", "Gasoline", 1_568, "GJ", "reported", DATABOOK, "PDF page 5", T51),
    "crude_oil_gj": Item("crude_oil_gj", "Crude oil", 0, "GJ", "reported", DATABOOK, "PDF page 5", T51),
    "explosive_gj": Item("explosive_gj", "Explosive", 0, "GJ", "reported", DATABOOK, "PDF page 5", T51),
    "electricity_gj": Item("electricity_gj", "Electricity use", 1_040_392, "GJ", "reported", DATABOOK, "PDF page 5", T51),
    "waste_heat_gj": Item("waste_heat_gj", "Self-generated (waste heat)", 0, "GJ", "reported", DATABOOK, "PDF page 5", T51),
    "scope12_t": Item("scope12_t", "Total Scope 1 & 2 GHG emissions", 160_632, "tCO2e", "reported", DATABOOK, "PDF page 5", T51),
    "scope1_t": Item("scope1_t", "Direct (Scope 1) GHG emissions", 63_961, "tCO2e", "reported", DATABOOK, "PDF page 5", T51),
    "scope2_t": Item("scope2_t", "Indirect (Scope 2) GHG emissions", 96_671, "tCO2e", "reported", DATABOOK, "PDF page 5", T51),
}
CONTEXT = [   # reported context, not used in calculations
    Item("alu_intensity", "Aluminium BU Scope 1+2 intensity (MAC, MRC and MBAC together)", 1.561, "tCO2e per t production", "reported",
         DATABOOK, "PDF page 2", "table 'GHG emissions (GRI 305-1, 2 & 4)', 2025; MRC's own production is not reported, so MRC's intensity cannot be calculated"),
    Item("alu_target", "Ma'aden Aluminium target: cut Scope 1+2 intensity by 50% by 2030; net zero by 2050", 50, "% intensity cut by 2030",
         "reported", DATABOOK, "PDF page 5", "section 'ASI 5.3 - GHG emissions reduction plans' (business-unit target, not an MRC target)"),
    Item("iso50001", "MRC holds ISO 50001:2018 (energy management) certification", 1, "yes", "reported", DATABOOK, "PDF page 10",
         "certificates table (listed as 'Maaden Rolling')"),
    Item("assurance", "Energy, Scope 1 and Scope 2 within Bureau Veritas limited assurance; MRC listed in Annexure 1", 1, "yes", "reported",
         DATABOOK, "PDF pages 11-13", "independent assurance statement, 27 Jan 2026"),
]

IPCC_T23 = ("IPCC 2006 Guidelines, Vol. 2, Ch. 2, Table 2.3 (default factors, manufacturing industries and construction; "
            "CO2 range = 95% interval)")
IPCC_URL = "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf"
# kg per TJ of fuel (net calorific value): CO2 default, CO2 lower, CO2 upper, CH4, N2O
FUEL_FACTORS = {
    "natural_gas_gj": ("Natural gas", 56_100, 54_300, 58_300, 1, 0.1),
    "diesel_heating_gj": ("Gas/diesel oil (used for 'diesel and heating fuel')", 74_100, 72_600, 74_800, 3, 0.6),
    "gasoline_gj": ("Motor gasoline (stationary defaults; vehicle use would add < 2 t)", 69_300, 67_500, 73_000, 3, 0.6),
}


def gj_to_mwh(gj):
    """Unit conversion: 1 MWh = 3.6 GJ."""
    return gj / GJ_PER_MWH


def fuel_factor_t_per_gj(key):
    """IPCC default CO2e factor in tCO2e per GJ: (CO2 + CH4 x 28 + N2O x 265) kg/TJ / 1e6."""
    _, co2, _, _, ch4, n2o = FUEL_FACTORS[key]
    return (co2 + ch4 * GWP_CH4 + n2o * GWP_N2O) / 1e6


def fuel_factor_u95(key):
    """Half-width of the IPCC CO2 range as a percentage of the default (treated as a 95% interval)."""
    _, co2, lo, hi, _, _ = FUEL_FACTORS[key]
    return 100 * (hi - lo) / 2 / co2


def v(key):
    return float(REPORTED[key].value)


def energy_check():
    """The reported fuel and electricity lines must add up to the reported total (a basic data-quality check)."""
    parts = ["natural_gas_gj", "diesel_heating_gj", "crude_oil_gj", "gasoline_gj", "explosive_gj", "electricity_gj", "waste_heat_gj"]
    s = sum(v(k) for k in parts)
    return dict(sum_of_lines=s, reported_total=v("energy_total_gj"), difference=s - v("energy_total_gj"))


def scope1_recalc(activity_u95=2.0):
    """Scope 1 recalculated from reported fuel energy x IPCC default factors, with first-order uncertainty
    (engine.u_mult per fuel, engine.u_add for the total). activity_u95 is an ASSUMED metering uncertainty (+/-%, 95%)."""
    rows = []
    for k in FUEL_FACTORS:
        ef = fuel_factor_t_per_gj(k)
        e = v(k) * ef
        u = E.u_mult(activity_u95, fuel_factor_u95(k))
        rows.append(dict(key=k, fuel=FUEL_FACTORS[k][0], activity_gj=v(k), ef_t_per_gj=ef, emissions_t=e, u95_pct=u))
    tot = sum(r["emissions_t"] for r in rows)
    u_tot = E.u_add([(r["emissions_t"], r["u95_pct"]) for r in rows])
    rep = v("scope1_t")
    return dict(rows=rows, total_t=tot, u95_pct=u_tot, reported_t=rep, diff_t=tot - rep, diff_pct=100 * (tot / rep - 1))


def implied_grid_factor():
    """Scope 2 emission factor implied by the reported numbers: reported Scope 2 / reported electricity (in MWh).
    The data book does not state which factor or method Ma'aden used."""
    mwh = gj_to_mwh(v("electricity_gj"))
    return dict(electricity_mwh=mwh, scope2_t=v("scope2_t"), implied_t_per_mwh=v("scope2_t") / mwh,
                national_t_per_mwh=float(P["ef_grid"].value), scope2_at_national_t=mwh * float(P["ef_grid"].value))


def summary():
    s1 = scope1_recalc()
    g = implied_grid_factor()
    return dict(scope1=s1, grid=g, energy=energy_check(), s12_reported=v("scope12_t"),
                electricity_share_of_s12=v("scope2_t") / v("scope12_t"))


# ------------------------------------------------------------------ hypothetical investment scenario
MRC_PROJECTS = ("A", "B", "C", "D")     # E (forklifts) and F (steel supplier) do not fit MRC's reported data
SYN = base_values()


def scenario_defaults():
    """Hypothetical scenario inputs. kind: hypothetical = CARBON IQ assumption; benchmark = external source in the register."""
    eratio = gj_to_mwh(v("electricity_gj")) / SYN["elec_mwh"]
    gratio = v("natural_gas_gj") / SYN["gas_gj"]
    return [
        Item("pv_kwp", "A · Rooftop solar size", 10_000, "kWp", "hypothetical", "CARBON IQ assumption",
             note="MRC roof area is not reported; 10 MWp is an illustrative size (about 6% of MRC's electricity in year 1)"),
        Item("motor_share", "Share of electricity used by non-compressor motors", float(P["motor_share"].value), "fraction",
             "hypothetical", "CARBON IQ register (synthetic plant)", note="MRC's end-use split is not reported"),
        Item("compressed_air_share", "Share of electricity used by compressed air", float(P["compressed_air_share"].value), "fraction",
             "hypothetical", "CARBON IQ register (synthetic plant)", note="MRC's end-use split is not reported"),
        Item("cost_scale_elec", "Cost scaling for B and C (MRC electricity ÷ synthetic plant electricity)", eratio, "×",
             "hypothetical", "calculated from reported MRC electricity",
             note="B and C costs = synthetic placeholder costs × this ratio (linear scaling; economies of scale ignored)"),
        Item("cost_scale_gas", "Cost scaling for D (MRC gas ÷ synthetic plant gas)", gratio, "×", "hypothetical",
             "calculated from reported MRC natural gas", note="D cost = synthetic placeholder cost × this ratio"),
        Item("budget", "Capital budget", 70_000_000, "SAR", "hypothetical", "CARBON IQ assumption", note="Not a Ma'aden budget"),
        Item("target_share", "Scope 1+2 reduction target", 0.08, "fraction of reported Scope 1+2", "hypothetical", "CARBON IQ assumption",
             note="Not an MRC target. Ma'aden Aluminium's published goal is an intensity target (PDF page 5)"),
        Item("grid_basis", "Grid factor used to value electricity savings", 1, "1 = implied by MRC's report, 0 = national average",
             "calculated", "implied_grid_factor()", note="The choice changes the tonnes saved by A, B and C"),
    ]


BENCHMARKS = ["tariff", "gas_price_usd", "discount_rate", "pv_yield", "pv_capex_kw", "pv_degradation", "pv_life", "pv_om_frac",
              "b_saving_frac", "b_comp_frac", "b_life", "c_saving_frac", "c_life", "d_saving_frac", "d_life", "ef_gas"]


def params(overrides=None):
    """Parameter set for engine.projects(): the register values with MRC's reported energy use and the scenario sizing."""
    sc = {i.key: i.value for i in scenario_defaults()}
    sc.update(overrides or {})
    p = dict(SYN)
    g = implied_grid_factor()
    p.update(elec_mwh=g["electricity_mwh"], gas_gj=v("natural_gas_gj"), pv_kwp=sc["pv_kwp"], motor_share=sc["motor_share"],
             compressed_air_share=sc["compressed_air_share"],
             ef_grid=g["implied_t_per_mwh"] if sc["grid_basis"] >= 0.5 else g["national_t_per_mwh"],
             b_capex=SYN["b_capex"] * sc["cost_scale_elec"], c_capex=SYN["c_capex"] * sc["cost_scale_elec"],
             c_om=SYN["c_om"] * sc["cost_scale_elec"], d_capex=SYN["d_capex"] * sc["cost_scale_gas"], d_om=SYN["d_om"] * sc["cost_scale_gas"],
             budget=sc["budget"], target_share=sc["target_share"])
    for k in ("tariff", "gas_price_usd", "discount_rate"):
        if k in (overrides or {}):
            p[k] = overrides[k]
    return p


def target_t(p):
    return p["target_share"] * v("scope12_t")


def projects(p):
    prj, inter = E.projects(p)
    return {k: prj[k] for k in MRC_PROJECTS}, inter


def portfolios(p):
    """All 16 combinations of A-D with engine.portfolio() (B-C overlap counted once); best = max NPV within budget and target."""
    prj, inter = E.projects(p)
    T = target_t(p)
    rows = []
    for c in O.all_portfolios(MRC_PROJECTS):
        t = E.portfolio(c, prj, inter)
        rows.append(dict(portfolio="+".join(c) or "(none)", ids=c, capex=float(t["capex"]), npv=float(t["npv"]),
                         scope12_t=float(t["scope12_t"]), within_budget=float(t["capex"]) <= p["budget"] + 1e-6,
                         meets_target=float(t["scope12_t"]) >= T - 1e-9))
    for r in rows:
        r["feasible"] = r["within_budget"] and r["meets_target"]
    feas = [r for r in rows if r["feasible"]]
    return (max(feas, key=lambda r: r["npv"]) if feas else None), rows


SCALED = {"b_capex": "cost_scale_elec", "c_capex": "cost_scale_elec", "c_om": "cost_scale_elec", "d_capex": "cost_scale_gas",
          "d_om": "cost_scale_gas"}


def monte_carlo(p, n=5000, seed=20261024, alpha=0.9, beta=0.9):
    """Monte Carlo on the MRC scenario using the register's distributions (same _draw as uncertainty.sample).
    Reporting basis: emission factors fixed, as in the synthetic plant's primary rule. Returns one row per portfolio and
    the chance-constrained choice (max expected NPV with P(target) >= alpha and P(capex <= budget) >= beta, both tightened
    for sampling with uncertainty.alpha_saa)."""
    rng = np.random.default_rng(seed)
    s = {k: np.full(n, float(val)) for k, val in p.items() if isinstance(val, (int, float))}
    for k in ("tariff", "gas_price_usd", "pv_yield", "pv_capex_kw", "b_saving_frac", "c_saving_frac", "d_saving_frac"):
        s[k] = _draw(rng, P[k], n)
    s["tariff"] = s["tariff"] + (p["tariff"] - SYN["tariff"])
    s["gas_price_usd"] = s["gas_price_usd"] * p["gas_price_usd"] / SYN["gas_price_usd"]
    for k in ("b_capex", "c_capex", "d_capex"):                # cost uncertainty: register's relative spread around the scaled cost
        s[k] = p[k] * _draw(rng, P[k], n) / P[k].value
    s["elec_mwh"] = p["elec_mwh"] * _draw(rng, P["elec_mwh"], n) / P["elec_mwh"].value
    s["gas_gj"] = p["gas_gj"] * _draw(rng, P["gas_gj"], n) / P["gas_gj"].value
    prj, inter = E.projects(s)
    T = target_t(p)
    a, b = alpha_saa(alpha, n), alpha_saa(beta, n)
    base_best, base_rows = portfolios(p)
    quote = {r["portfolio"]: r["capex"] for r in base_rows}
    rows = []
    for c in O.all_portfolios(MRC_PROJECTS):
        t = E.portfolio(c, prj, inter)
        npv_ = np.broadcast_to(t["npv"], (n,)); t12 = np.broadcast_to(t["scope12_t"], (n,)); cap = np.broadcast_to(t["capex"], (n,))
        name = "+".join(c) or "(none)"
        p_budget = float((cap <= p["budget"]).mean())
        se = math.sqrt(beta * (1 - beta) / n)          # Monte Carlo standard error of a probability near the required level
        rows.append(dict(portfolio=name, quoted_capex=quote[name], e_npv=float(npv_.mean()), p5_npv=float(np.quantile(npv_, 0.05)),
                         p_loss=float((npv_ < 0).mean()), e_t12=float(t12.mean()), p_target=float((t12 >= T).mean()),
                         p_budget=p_budget,
                         # v2.1: smallest budget at which this plan passes the budget rule = its tightened-quantile actual cost
                         budget_needed=max(float(np.quantile(cap, b, method="higher")), quote[name]),
                         budget_margin_se=(p_budget - b) / se))
    ok = [r for r in rows if r["quoted_capex"] <= p["budget"] + 1e-6 and r["p_target"] >= a and r["p_budget"] >= b]
    choice = max(ok, key=lambda r: r["e_npv"]) if ok else None
    reliable = [r for r in rows if r["p_target"] >= a and r["portfolio"] != "(none)"]
    min_budget = min(reliable, key=lambda r: r["budget_needed"]) if reliable else None
    return dict(rows=rows, choice=choice, alpha_eff=a, beta_eff=b, n=n, target_t=T, budget=p["budget"],
                min_budget=min_budget, max_cut=max(r["e_t12"] for r in rows))


def budget_feasibility(p, mc=None):
    """v2.1 - never raises the budget. Explains feasibility at the budget the user set:
    deterministic: cheapest plan meeting the target at most-likely inputs (or the largest possible cut if none can);
    probabilistic: smallest budget at which some plan meets both confidence rules, and the budget the most valuable plan needs."""
    best, rows = portfolios(p)
    T = target_t(p)
    meet = [r for r in rows if r["meets_target"]]
    out = dict(budget=p["budget"], target_t=T, det_best=best,
               det_min_budget=min(r["capex"] for r in meet) if meet else None,
               det_max_cut=max(r["scope12_t"] for r in rows))
    if mc is not None:
        top = max((r for r in mc["rows"] if r["p_target"] >= mc["alpha_eff"]), key=lambda r: r["e_npv"], default=None)
        robust = [r for r in mc["rows"] if r["portfolio"] != "(none)" and r["quoted_capex"] <= p["budget"] + 1e-6
                  and r["p_target"] >= mc["alpha_eff"] and r["budget_margin_se"] >= 2]
        out.update(cc_choice=mc["choice"], cc_min_budget=mc["min_budget"], best_value_plan=top,
                   robust_alternative=max(robust, key=lambda r: r["e_npv"]) if robust else None,
                   knife_edge=bool(mc["choice"] and abs(mc["choice"]["budget_margin_se"]) < 2))
    return out


def scope1_reconciliation():
    """v2.1 - explains the gap between the recalculated and the reported Scope 1 (all values in tCO2e)."""
    s = scope1_recalc()
    co2 = sum(v(k) * FUEL_FACTORS[k][1] / 1e6 for k in FUEL_FACTORS)
    gwp = lambda ch4, n2o: sum(v(k) * (FUEL_FACTORS[k][1] + FUEL_FACTORS[k][4] * ch4 + FUEL_FACTORS[k][5] * n2o) / 1e6 for k in FUEL_FACTORS)
    co2_lo = sum(v(k) * FUEL_FACTORS[k][2] / 1e6 for k in FUEL_FACTORS)
    co2_hi = sum(v(k) * FUEL_FACTORS[k][3] / 1e6 for k in FUEL_FACTORS)
    gcv = sum(v(k) * fuel_factor_t_per_gj(k) * (0.90 if k == "natural_gas_gj" else 0.95) for k in FUEL_FACTORS)
    gas_close = s["diff_t"] / v("natural_gas_gj") * 1e6          # kg CO2 per TJ change that closes the gap
    return dict(reported=s["reported_t"], recalculated=s["total_t"], diff_t=s["diff_t"], diff_pct=s["diff_pct"],
                co2_only=co2, non_co2=s["total_t"] - co2, u95_t=s["total_t"] * s["u95_pct"] / 100, u95_pct=s["u95_pct"],
                diff_share_of_u95=abs(s["diff_t"]) / (s["total_t"] * s["u95_pct"] / 100),
                ar4=gwp(25, 298), ar6=gwp(29.8, 273), co2_range=(co2_lo, co2_hi), if_gross_cv=gcv,
                gas_factor_to_close=FUEL_FACTORS["natural_gas_gj"][1] - gas_close, gas_change_pct=-100 * gas_close / FUEL_FACTORS["natural_gas_gj"][1])


def grid_factor_comparison():
    """v2.1 - the three different things that are easy to confuse when talking about MRC's Scope 2 factor."""
    g = implied_grid_factor()
    return [
        dict(factor="Implied by MRC's report", value=g["implied_t_per_mwh"], kind="calculated",
             how="Reported Scope 2 (96,671 t) ÷ reported electricity converted to MWh (288,998). A back-calculation, not a published factor.",
             verified="No — the data book does not state the factor, its year, its source or whether it is location- or market-based."),
        dict(factor="Saudi national grid average (CARBON IQ register)", value=g["national_t_per_mwh"], kind="calculated",
             how="Power-sector emissions 2021 (KSA First Biennial Transparency Report, UNFCCC 2025) ÷ electricity generated 2021 (GASTAT).",
             verified="Derived by CARBON IQ from official national statistics; corroborated by a 0.568 Saudi DNA 2021 value cited by "
                      "KFUPM. Not a utility- or third-party-verified factor for MRC's supply."),
        dict(factor="Independently verified grid factor for MRC's electricity supply", value=None, kind="hypothetical",
             how="Would come from the electricity supplier, Saudi Electricity Company / ECRA publications or MRC's assured methodology.",
             verified="Not available to CARBON IQ. Needed before either number above is used for MRC decisions."),
    ]


def tornado(ids, p, keys=("tariff", "b_saving_frac", "c_saving_frac", "d_saving_frac", "pv_capex_kw", "pv_yield", "gas_price_usd")):
    """One-way sensitivity of the portfolio NPV: each register input at its 5th and 95th percentile (sensitivity.pct_values)."""
    from .sensitivity import pct_values
    prj, inter = E.projects(p)
    base = float(E.portfolio(ids, prj, inter)["npv"])
    out = []
    for k in keys:
        lo_hi = pct_values(k)
        if lo_hi is None:
            continue
        vals = []
        for x in lo_hi:
            q = dict(p)
            if k == "tariff":
                q[k] = x + (p["tariff"] - SYN["tariff"])
            elif k == "gas_price_usd":
                q[k] = x * p["gas_price_usd"] / SYN["gas_price_usd"]
            else:
                q[k] = x
            pr, it = E.projects(q)
            vals.append(float(E.portfolio(ids, pr, it)["npv"]))
        out.append(dict(parameter=k, low=lo_hi[0], high=lo_hi[1], npv_low=vals[0], npv_high=vals[1], base_npv=base,
                        swing=abs(vals[1] - vals[0])))
    return sorted(out, key=lambda r: -r["swing"])


def source_register():
    """Every MRC-related number with its kind, source, page and the function that uses it (deliverable: source-to-variable register)."""
    rows = []
    uses = {"natural_gas_gj": "scope1_recalc(); params() -> engine.projects() (project D)",
            "diesel_heating_gj": "scope1_recalc()", "gasoline_gj": "scope1_recalc()",
            "electricity_gj": "gj_to_mwh(); implied_grid_factor(); params() -> engine.projects() (projects A, B, C)",
            "scope1_t": "scope1_recalc() (comparison)", "scope2_t": "implied_grid_factor()",
            "scope12_t": "target_t() (hypothetical target = share x reported Scope 1+2)", "energy_total_gj": "energy_check()"}
    for i in list(REPORTED.values()) + CONTEXT:
        rows.append(dict(variable=f"mrc.REPORTED['{i.key}']" if i.key in REPORTED else f"mrc.CONTEXT ({i.key})", description=i.label,
                         value=i.value, unit=i.unit, kind=i.kind, company_year=f"MRC / Ma'aden, {YEAR}", source=i.source, page=i.page,
                         location=i.note, used_by=uses.get(i.key, "displayed only"), uncertainty="not stated in the source"))
    for k, (name, co2, lo, hi, ch4, n2o) in FUEL_FACTORS.items():
        rows.append(dict(variable=f"mrc.FUEL_FACTORS['{k}']", description=f"IPCC default factor: {name}",
                         value=round(fuel_factor_t_per_gj(k), 7), unit="tCO2e/GJ", kind="benchmark",
                         company_year="generic (IPCC 2006)", source=IPCC_T23, page="Vol. 2, Ch. 2, Table 2.3", location=IPCC_URL,
                         used_by="scope1_recalc()", uncertainty=f"±{fuel_factor_u95(k):.1f}% (95%, from the IPCC CO2 range)"))
    g = implied_grid_factor()
    rows.append(dict(variable="mrc.implied_grid_factor()", description="Scope 2 factor implied by MRC's report", value=round(g["implied_t_per_mwh"], 4),
                     unit="tCO2e/MWh", kind="calculated", company_year="MRC, 2025", source="reported Scope 2 ÷ reported electricity (MWh)",
                     page="PDF page 5", location="", used_by="params() (grid_basis = 1)", uncertainty="method not stated by Ma'aden"))
    r = scope1_reconciliation()
    for name, val, desc in [("co2_only", r["co2_only"], "Scope 1 CO2 only, IPCC default CO2 factors"),
                            ("non_co2", r["non_co2"], "CH4 + N2O from the same fuels (AR5 GWPs)"),
                            ("recalculated", r["recalculated"], "Scope 1 recalculated by CARBON IQ"),
                            ("diff_t", r["diff_t"], "Recalculated minus reported Scope 1"),
                            ("u95_t", r["u95_t"], "95% uncertainty of the recalculation (assumed ±2% metering + IPCC ranges)"),
                            ("gas_factor_to_close", r["gas_factor_to_close"], "Gas CO2 factor (kg/TJ) that would close the gap; IPCC range 54,300-58,300")]:
        rows.append(dict(variable=f"mrc.scope1_reconciliation()['{name}']", description=desc, value=round(val, 1),
                         unit="kg CO2/TJ" if name == "gas_factor_to_close" else "tCO2e", kind="calculated", company_year="MRC, 2025",
                         source="reported fuel GJ (PDF page 5) x IPCC 2006 Table 2.3", page="PDF page 5", location=IPCC_URL,
                         used_by="mrc.scope1_reconciliation() (explanation only)", uncertainty=f"±{r['u95_pct']:.1f}% on the total"))
    for x in grid_factor_comparison():
        rows.append(dict(variable="mrc.grid_factor_comparison()", description=x["factor"], value=x["value"] if x["value"] is not None else "n/a",
                         unit="tCO2e/MWh", kind=x["kind"], company_year="MRC 2025 / Saudi Arabia 2021",
                         source=x["how"], page="PDF page 5" if "MRC's report" in x["factor"] else "", location="",
                         used_by="comparison only", uncertainty=x["verified"]))
    for i in scenario_defaults():
        rows.append(dict(variable=f"mrc.scenario_defaults()['{i.key}']", description=i.label, value=i.value, unit=i.unit, kind=i.kind,
                         company_year="not an MRC value", source=i.source, page="", location=i.note, used_by="params()",
                         uncertainty="user-adjustable"))
    for k in BENCHMARKS:
        x = P[k]
        rows.append(dict(variable=f"assumptions.P['{k}']", description=x.source[:160], value=x.value, unit=x.unit,
                         kind="benchmark" if x.evidence in ("external", "derived") else "hypothetical",
                         company_year=f"{x.geography or 'generic'}; published {x.published or 'n/a'}", source=x.source, page="",
                         location=x.url, used_by="engine.projects() via mrc.params()", uncertainty=str(x.dist or "none")))
    return rows
