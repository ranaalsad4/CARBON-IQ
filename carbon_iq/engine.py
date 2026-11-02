"""Carbon accounting, uncertainty propagation, project economics and the shared activity ledger.

All functions accept a parameter mapping whose values are floats (deterministic case) or equal-length
numpy arrays (Monte Carlo scenarios); arithmetic is vectorised.
"""
import math

import numpy as np

from .assumptions import P, PROJECTS, SCOPE12_PROJECTS, Z95, base_values, gas_price_sar_per_gj


# ------------------------------------------------------------------ finance primitives
def annuity_factor(r, n):
    """Present value of 1 SAR per year for n years at real rate r (end-of-year cash flows)."""
    r = np.asarray(r, dtype=float)
    return np.where(np.abs(r) < 1e-12, n, (1 - (1 + r) ** (-n)) / np.where(np.abs(r) < 1e-12, 1, r)) * 1.0


def degraded_annuity_factor(r, n, d):
    """Present value of an output that is 1 in year 1 and declines by a fraction d per year: sum_t (1-d)^(t-1)/(1+r)^t
    = (1 - ((1-d)/(1+r))^n) / (r + d). Equals annuity_factor(r, n) when d = 0."""
    r = np.asarray(r, dtype=float); d = np.asarray(d, dtype=float)
    den = r + d
    safe = np.where(np.abs(den) < 1e-12, 1.0, den)
    # r + d = 0: every term equals 1/(1+r), so the sum is n/(1+r) (A6: was n, wrong unless r = 0)
    return np.where(np.abs(den) < 1e-12, n / (1 + r), (1 - ((1 - d) / (1 + r)) ** n) / safe) * 1.0


def npv(capex, annual_cf, r, n):
    return -capex + annual_cf * annuity_factor(r, n)


def simple_payback(capex, annual_cf):
    return capex / annual_cf if annual_cf > 0 else float("inf")


def irr(capex, annual_cf, n, lo=-0.99, hi=1.0):
    """IRR of -capex followed by n equal flows (bisection). None if no sign change."""
    f = lambda r: -capex + annual_cf * float(annuity_factor(r, n))
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def project_irr(d, degradation=0.0, lo=-0.99, hi=1.0):
    """IRR of a project record from projects(): for a degrading output (A) the energy-related flows decline by
    `degradation` per year, so the constant-flow irr() would overstate it (A6 finding). None if no sign change."""
    if "energy_af" not in d or degradation == 0:
        return irr(d["capex"], d["annual_cf"], int(d["life"]), lo, hi)
    n, fixed = int(d["life"]), float(d["fixed_cf"])
    var = float(d["annual_cf"]) - fixed
    f = lambda r: -d["capex"] + var * float(degraded_annuity_factor(r, n, degradation)) + fixed * float(annuity_factor(r, n))
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------ Method 1: baseline accounting
def baseline(p=None):
    p = p or base_values()
    rows = [
        ("S1-GAS", "Scope 1", "Natural gas, process heat", p["gas_gj"], "GJ", p["ef_gas"]),
        ("S1-DSL-FL", "Scope 1", "Diesel, forklifts", p["diesel_forklift_l"], "L", p["ef_diesel"]),
        ("S1-DSL-GEN", "Scope 1", "Diesel, backup generators", p["diesel_genset_l"], "L", p["ef_diesel"]),
        ("S2-ELEC", "Scope 2", "Grid electricity (location-based)", p["elec_mwh"], "MWh", p["ef_grid"]),
        ("S3-C1-STEEL", "Scope 3 Cat 1", "Purchased steel", p["steel_t"], "t", p["ef_steel_incumbent"]),
        ("S3-C4-FRT", "Scope 3 Cat 4", "Inbound road freight", p["freight_tkm"], "t-km", p["ef_freight"]),
    ]
    out = [{"source_id": a, "scope": b, "source": c, "activity": d, "unit": e, "ef_t_per_unit": f, "emissions_t": d * f}
           for a, b, c, d, e, f in rows]
    return out


def scope_totals(rows):
    t = {}
    for r in rows:
        key = r["scope"].split(" Cat")[0]
        t[key] = t.get(key, 0.0) + r["emissions_t"]
    t["Scope 1+2"] = t.get("Scope 1", 0) + t.get("Scope 2", 0)
    t["Total"] = t["Scope 1+2"] + t.get("Scope 3", 0)
    return t


def u95(key):
    """+/- % (95% confidence) of a parameter, from its distribution (GHG Protocol convention)."""
    p = P[key]
    if p.dist is None:
        return 0.0
    kind = p.dist[0]
    if kind == "normal_rel":
        return 100 * Z95 * p.dist[1]
    if kind == "uniform":
        lo, hi = p.dist[1], p.dist[2]
        return 100 * 0.95 * (hi - lo) / 2 / p.value
    if kind == "triangular":
        lo, _, hi = p.dist[1:]
        return 100 * (hi - lo) / 2 / p.value
    if kind == "lognormal":
        return 100 * (math.exp(Z95 * p.dist[1]) - 1)
    return 0.0


def u_mult(*u_pct):
    """GHG Protocol first-order rule for products (A x EF): U = sqrt(sum U_i^2), U in +/- %."""
    return math.sqrt(sum(u ** 2 for u in u_pct))


def u_add(pairs):
    """GHG Protocol first-order rule for sums: U = sqrt(sum (E_i U_i)^2) / sum E_i, pairs = [(E_i, U_i%), ...]."""
    tot = sum(e for e, _ in pairs)
    return math.sqrt(sum((e * u) ** 2 for e, u in pairs)) / tot


ACTIVITY_KEY = {"S1-GAS": ("gas_gj", "ef_gas"), "S1-DSL-FL": ("diesel_forklift_l", "ef_diesel"),
                "S1-DSL-GEN": ("diesel_genset_l", "ef_diesel"), "S2-ELEC": ("elec_mwh", "ef_grid"),
                "S3-C1-STEEL": ("steel_t", "ef_steel_incumbent"), "S3-C4-FRT": ("freight_tkm", "ef_freight")}
DQ_LABEL = [(5, "High"), (15, "Good"), (30, "Fair"), (1e9, "Poor")]   # GHG Protocol guidance Table 2 scale


def uncertainty_table(rows=None):
    """First-order (Gaussian) propagation per GHG Protocol uncertainty guidance:
    source: U = sqrt(U_A^2 + U_EF^2); total: U = sqrt(sum (E_i U_i)^2) / sum E_i."""
    rows = rows or baseline()
    out = []
    for r in rows:
        ka, ke = ACTIVITY_KEY[r["source_id"]]
        ua = u95(ka)   # v1.1: every activity uncertainty comes from the assumption register (same inputs as the Monte Carlo)
        ue = u95(ke)
        uc = u_mult(ua, ue)
        label = next(lab for lim, lab in DQ_LABEL if uc <= lim)
        out.append({**r, "u_activity_pct": ua, "u_ef_pct": ue, "u_combined_pct": uc, "quality": label,
                    "first_order_valid": ua < 60 and ue < 60})
    def agg(sel):
        pairs = [(r["emissions_t"], r["u_combined_pct"]) for r in out if sel(r)]
        return sum(e for e, _ in pairs), u_add(pairs)
    tot = {"Scope 1": agg(lambda r: r["scope"] == "Scope 1"), "Scope 2": agg(lambda r: r["scope"] == "Scope 2"),
           "Scope 3": agg(lambda r: r["scope"].startswith("Scope 3")),
           "Scope 1+2": agg(lambda r: not r["scope"].startswith("Scope 3")), "Total": agg(lambda r: True)}
    return out, tot


# ------------------------------------------------------------------ project models
def projects(p=None):
    """Per-project economics and reductions (stand-alone). Returns dict of dicts (values may be arrays)."""
    p = p or base_values()
    r = p["discount_rate"]
    tariff_mwh = p["tariff"] * 1000
    gas_sar_gj = gas_price_sar_per_gj(p["gas_price_usd"])
    comp_mwh = p["elec_mwh"] * p["compressed_air_share"]
    motor_mwh = p["elec_mwh"] * p["motor_share"]
    out = {}
    # A solar PV (self-consumed; output < daytime load by construction)
    a_capex = p["pv_kwp"] * p["pv_capex_kw"]
    a_mwh = p["pv_kwp"] * p["pv_yield"] / 1000
    a_cf = a_mwh * tariff_mwh - p["pv_om_frac"] * a_capex
    # v1.3: output declines by pv_degradation per year; reductions are reported for year 1 (the target year)
    a_afd = degraded_annuity_factor(r, p["pv_life"], p.get("pv_degradation", 0.0))
    out["A"] = dict(capex=a_capex, annual_cf=a_cf, life=p["pv_life"], d_elec_mwh=-a_mwh, d_gas_gj=0.0, d_diesel_l=0.0,
                    d_steel_t_ef=0.0, energy_af=a_afd, fixed_cf=-p["pv_om_frac"] * a_capex)
    # B motors + VSDs (non-compressor motors + compressor motors)
    b_mwh = motor_mwh * p["b_saving_frac"] + comp_mwh * p["b_comp_frac"]
    out["B"] = dict(capex=p["b_capex"], annual_cf=b_mwh * tariff_mwh, life=p["b_life"], d_elec_mwh=-b_mwh,
                    d_gas_gj=0.0, d_diesel_l=0.0, d_steel_t_ef=0.0)
    # C compressed air
    c_mwh = comp_mwh * p["c_saving_frac"]
    out["C"] = dict(capex=p["c_capex"], annual_cf=c_mwh * tariff_mwh - p.get("c_om", 0.0), life=p["c_life"], d_elec_mwh=-c_mwh,
                    d_gas_gj=0.0, d_diesel_l=0.0, d_steel_t_ef=0.0)
    # D heat recovery
    d_gj = p["gas_gj"] * p["d_saving_frac"]
    out["D"] = dict(capex=p["d_capex"], annual_cf=d_gj * gas_sar_gj - p["d_om"], life=p["d_life"], d_elec_mwh=0.0,
                    d_gas_gj=-d_gj, d_diesel_l=0.0, d_steel_t_ef=0.0)
    # E forklift electrification (removes forklift diesel, adds electricity)
    e_l = p["diesel_forklift_l"]
    e_mwh = e_l * p["e_kwh_per_l"] / 1000
    e_cf = e_l * p["diesel_price"] - e_mwh * tariff_mwh + p["e_maint_saving"]
    out["E"] = dict(capex=p["e_capex"], annual_cf=e_cf, life=p["e_life"], d_elec_mwh=e_mwh, d_gas_gj=0.0,
                    d_diesel_l=-e_l, d_steel_t_ef=0.0)
    # F lower-carbon steel supplier (Scope 3 Cat 1; annual premium, small one-time onboarding)
    out["F"] = dict(capex=p["f_onboard"], annual_cf=-p["f_steel_t"] * p["f_premium"], life=p["f_life"], d_elec_mwh=0.0,
                    d_gas_gj=0.0, d_diesel_l=0.0, d_steel_t_ef=p["f_steel_t"] * (p["ef_steel_alt"] - p["ef_steel_incumbent"]))
    for k, d in out.items():
        d["af"] = annuity_factor(r, d["life"])
        if "energy_af" in d:            # degrading output: energy-related flows discounted with the degraded factor
            d["npv"] = -d["capex"] + (d["annual_cf"] - d["fixed_cf"]) * d["energy_af"] + d["fixed_cf"] * d["af"]
            d["af_t"] = d["energy_af"]
        else:
            d["npv"] = npv(d["capex"], d["annual_cf"], r, d["life"])
            d["af_t"] = d["af"]
        d["scope12_t"] = -(d["d_elec_mwh"] * p["ef_grid"] + d["d_gas_gj"] * p["ef_gas"] + d["d_diesel_l"] * p["ef_diesel"])
        d["scope3_t"] = -d["d_steel_t_ef"]
        d["name"] = PROJECTS[k]
    # interaction: B's compressor-motor saving applies only to the load left after C (shared activity ledger)
    ov_mwh = comp_mwh * p["b_comp_frac"] * p["c_saving_frac"]
    inter = {"BC": dict(mwh=ov_mwh, npv=ov_mwh * tariff_mwh * annuity_factor(r, np.minimum(p["b_life"], p["c_life"])),
                        scope12_t=ov_mwh * p["ef_grid"])}
    return out, inter


def mac(d):
    """Marginal abatement cost, SAR per tCO2e: -NPV / discounted lifetime tonnes, i.e. -NPV / (AF_t x year-1 tonnes),
    where AF_t is the annuity factor (or the degraded factor for a declining output). Equals the equivalent annual cost
    divided by annual tonnes when tonnes are constant."""
    t = d["scope12_t"] + d["scope3_t"]
    return -d["npv"] / (d.get("af_t", d["af"]) * t) if np.all(np.abs(t) > 1e-9) else float("nan")


def portfolio(sel, prj, inter):
    """Totals for a selected set of project ids, with the B-C overlap removed once (no double counting)."""
    sel = set(sel)
    order = sorted(sel)   # fixed summation order -> bit-identical results across runs
    tot = {k: sum(prj[i][k] for i in order) if order else 0.0 for k in ("capex", "npv", "scope12_t", "scope3_t")}
    if {"B", "C"} <= sel:
        tot["npv"] = tot["npv"] - inter["BC"]["npv"]
        tot["scope12_t"] = tot["scope12_t"] - inter["BC"]["scope12_t"]
    return tot


def ledger(sel, p=None):
    """Recompute activity and emissions after a portfolio from first principles (independent check of portfolio())."""
    p = p or base_values()
    sel = set(sel)
    comp = p["elec_mwh"] * p["compressed_air_share"]
    motor = p["elec_mwh"] * p["motor_share"]
    elec = p["elec_mwh"]
    comp_after = comp * (1 - (p["c_saving_frac"] if "C" in sel else 0.0))
    if "C" in sel:
        elec -= comp * p["c_saving_frac"]
    if "B" in sel:
        elec -= motor * p["b_saving_frac"] + comp_after * p["b_comp_frac"]
    if "A" in sel:
        elec -= p["pv_kwp"] * p["pv_yield"] / 1000
    diesel = p["diesel_forklift_l"] + p["diesel_genset_l"]
    if "E" in sel:
        diesel -= p["diesel_forklift_l"]
        elec += p["diesel_forklift_l"] * p["e_kwh_per_l"] / 1000
    gas = p["gas_gj"] * (1 - (p["d_saving_frac"] if "D" in sel else 0.0))
    steel_alt = p["f_steel_t"] if "F" in sel else 0.0
    s12 = elec * p["ef_grid"] + gas * p["ef_gas"] + diesel * p["ef_diesel"]
    s3 = (p["steel_t"] - steel_alt) * p["ef_steel_incumbent"] + steel_alt * p["ef_steel_alt"] + p["freight_tkm"] * p["ef_freight"]
    return {"elec_mwh": elec, "gas_gj": gas, "diesel_l": diesel, "scope12_t": s12, "scope3_t": s3}


def target_t(p=None):
    p = p or base_values()
    return p["target_share"] * scope_totals(baseline(p))["Scope 1+2"]


ALL = tuple(PROJECTS)
SCOPE12 = SCOPE12_PROJECTS
