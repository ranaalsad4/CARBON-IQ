"""Feed cleaned and estimated activity data into the existing CARBON IQ engines (no engine is modified).

Deterministic case: register base values with the activity totals replaced by the ledger's annual totals.
Monte Carlo: the v1.2 scenarios (same seed) with each activity draw rescaled to the new total, plus an independent
normal error z_k of the estimated part (sd from the ledger; separate random stream).
Target (A4 refinement): an estimated baseline makes the 15% target itself uncertain. Each scenario's target is
    T_s = T_det + share x sum_k ef_k x sd_k x z_k          (Scope 1+2 streams, fixed reporting factors)
so the carbon chance constraint accounts for errors in both the reductions and the baseline. With complete data
(sd = 0) T_s = T_det and every v1.2 number is reproduced exactly.
Primary decision rules as in v1.2: fixed reporting factors; tightened in-sample levels (alpha_saa).
Unresolved gaps block the run: missing data are never treated as zero.

Value of information (pre-posterior analysis, Raiffa & Schlaifer 1961; same decision rules as v1.2):
for a measurement that reveals (part of) the estimation error z_k, equal-probability nodes of the measurement result are
evaluated; at each node the scenarios are conditioned exactly (z_k fixed at the posterior mean, residual error kept)
and each rule is re-applied. Reported per rule: change in expected NPV of the chosen portfolio and change in the
probability of meeting the target, both against the prior choice evaluated on the same nodes. An irrelevant
measurement leaves every node identical to the prior, so this estimator has no binning noise floor (unlike EVPPI by
binning, A1-26); Monte Carlo error is reported from repeated scenario seeds.
"""
import numpy as np
from scipy.stats import norm

from .. import decisions as D
from .. import engine as E
from .. import optimize as O
from .. import uncertainty as U
from ..assumptions import base_values, v

ACTIVITY_KEYS = ("elec_mwh", "gas_gj", "diesel_forklift_l", "diesel_genset_l", "steel_t", "freight_tkm", "production_t")
S12_FACTOR = {"elec_mwh": "ef_grid", "gas_gj": "ef_gas", "diesel_forklift_l": "ef_diesel", "diesel_genset_l": "ef_diesel"}
KEY_PORTFOLIOS = (("A", "B"), ("A", "C", "D"), ("A", "B", "C"))   # A+B+C added in A6 (the v1.3 choice)
RULES = ("D1", "D2", "D3", "D4")


class IncompleteData(Exception):
    pass


def _key(r):
    """Register key of an annual-total row (production maps to production_t; operating hours have no key)."""
    reg = r["register"]
    if isinstance(reg, str) and reg:
        return reg
    return "production_t" if r["stream"] == "production" else None


def activity_from_annual(annual, allow_incomplete=False):
    """{register key: (total, sd of estimated part)} from Ledger.annual(). Raises if a stream has unresolved gaps."""
    out, open_ = {}, []
    for _, r in annual.iterrows():
        key = _key(r)
        if key is None:
            continue
        if not r["complete"]:
            open_.append(f"{r['stream']} ({r['n_unresolved']} month(s))")
            continue
        out[key] = (float(r["total"]), float(r["sd_estimate"]))
    if open_ and not allow_incomplete:
        raise IncompleteData("unresolved data gaps - collect or approve data for: " + ", ".join(open_))
    return out


def naive_zero_activity(ledger):
    """DEMONSTRATION OF A COMMON ERROR ONLY: every unresolved or estimated month counted as zero."""
    f = ledger.final()
    out = {}
    for _, r in ledger.annual().iterrows():
        key = _key(r)
        if key is None:
            continue
        g = f[f.stream == r["stream"]]
        out[key] = (float(g[g.status.isin(["measured", "converted"])].value.sum()), 0.0)
    return out


def register_activity():
    b = base_values()
    return {k: (float(b[k]), 0.0) for k in ACTIVITY_KEYS}


def params_for(activity, n=20000, seed=20261024):
    """(deterministic params, Monte Carlo params, error draws z per key)."""
    base = base_values()
    p_det = dict(base)
    for k, (val, _) in activity.items():
        p_det[k] = val
    prm = U.sample(n, seed)
    z = {}
    for j, k in enumerate(ACTIVITY_KEYS):
        if k not in activity:
            continue
        rng = np.random.default_rng([seed, 4, j])
        z[k] = rng.standard_normal(n)
    return p_det, prm, z


def _apply(activity, prm0, z, base):
    """Scenario parameters and per-scenario target offsets for given error draws z (dict key -> array)."""
    prm = dict(prm0)
    dT = 0.0
    share = base["target_share"]
    for k, (val, sd) in activity.items():
        if k not in z:
            continue
        prm[k] = prm0[k] * (val / base[k]) + sd * z[k]
        if k in S12_FACTOR and sd > 0:
            dT = dT + share * base[S12_FACTOR[k]] * sd * z[k]
    return prm, dT


def _choices(pr, budget, a_eff, b_eff):
    return {"D2": D.choose(pr, budget), "D3": D.choose(pr, budget, a_eff), "D4": D.choose(pr, budget, a_eff, b_eff)}


def run_decisions(activity, n=20000, seed=20261024, budget=None, alpha=None, beta=None, uncertain_target=True):
    budget = v("budget") if budget is None else budget
    alpha = v("chance_level") if alpha is None else alpha
    beta = v("budget_chance_level") if beta is None else beta
    base = base_values()
    p_det, prm0, z = params_for(activity, n, seed)
    prm, dT = _apply(activity, prm0, z, base)
    rows = E.baseline(p_det)
    tot = E.scope_totals(rows)
    T = E.target_t(p_det)
    Ts = T + (dT if uncertain_target else 0.0)
    prj, inter = E.projects(p_det)
    best, _ = O.enumerate_best(prj, inter, budget, T)
    sc = U.Scenarios(params=prm, basis="reporting")
    pr = D.portfolio_probs(sc, budget, Ts)
    a_eff, b_eff = U.alpha_saa(alpha, n), U.alpha_saa(beta, n)
    ch = _choices(pr, budget, a_eff, b_eff)
    nm = lambda k: sc.name(k) if k is not None else "none feasible"  # noqa: E731
    need = []
    for k in range(len(sc.ports)):
        if pr["p_target"][k] >= a_eff:
            need.append((max(float(np.quantile(sc.PCAP[k], b_eff, method="higher")), float(sc.capex[k])), sc.name(k)))
    need.sort()
    res = dict(scope1=tot["Scope 1"], scope2=tot["Scope 2"], scope3=tot["Scope 3"], scope12=tot["Scope 1+2"], total=tot["Total"],
               target_t=T, target_sd=float(np.std(dT)) if (uncertain_target and np.ndim(dT)) else 0.0,
               D1=best["portfolio"] if best else "infeasible", D1_npv=float(best["npv"]) if best else None,
               D2=nm(ch["D2"]), D2_e_npv=float(pr["e_npv"][ch["D2"]]), D3=nm(ch["D3"]),
               D3_e_npv=float(pr["e_npv"][ch["D3"]]) if ch["D3"] is not None else None,
               D4=nm(ch["D4"]), min_budget=need[0][0] if need else None, min_budget_portfolio=need[0][1] if need else None,
               alpha_saa=a_eff, beta_saa=b_eff, n=n)
    for ids in KEY_PORTFOLIOS:
        k = sc.index(ids); name = "+".join(ids)
        res[f"p_target[{name}]"] = float(pr["p_target"][k]); res[f"p_budget[{name}]"] = float(pr["p_budget"][k])
        res[f"e_npv[{name}]"] = float(pr["e_npv"][k])
    ctx = dict(sc=sc, pr=pr, z=z, T=T, Ts=Ts, prm0=prm0, base=base, choices=ch, budget=budget, a_eff=a_eff, b_eff=b_eff,
               best=best, prj=prj, inter=inter, p_det=p_det)
    return res, ctx


# ------------------------------------------------------------------ value of information (pre-posterior)
# HYPOTHETICAL costs of obtaining the missing records (assumptions, not quotations): staff time at an assumed
# SAR 150/hour loaded rate; hours per request are assumptions for illustration.
STAFF_RATE_SAR_H = 150
MEASUREMENTS = [
    dict(id="M1", label="Duplicate electricity bills for the missing months (utility portal / account manager)", keys=("elec_mwh",),
         post_sd_frac=0.0, hours=4, extra_sar=0),
    dict(id="M2", label="Gas supplier statements for the missing months", keys=("gas_gj",), post_sd_frac=0.0, hours=4, extra_sar=0),
    dict(id="M3", label="Fuel-card statements for forklift diesel", keys=("diesel_forklift_l",), post_sd_frac=0.0, hours=3, extra_sar=0),
    dict(id="M4", label="Steel delivery notes / supplier invoices", keys=("steel_t",), post_sd_frac=0.0, hours=6, extra_sar=0),
    dict(id="M5", label="Production records for the missing month", keys=("production_t",), post_sd_frac=0.0, hours=2, extra_sar=0),
    dict(id="M6", label="Engineering reconstruction of electricity from equipment run-hours (no bills; residual error 50% of the estimate's)",
         keys=("elec_mwh",), post_sd_frac=0.5, hours=16, extra_sar=0),
    dict(id="M7", label="All missing records (M1-M5 together)", keys=("elec_mwh", "gas_gj", "diesel_forklift_l", "steel_t", "production_t"),
         post_sd_frac=0.0, hours=19, extra_sar=0),
]


def measurement_cost(m):
    return m["hours"] * STAFF_RATE_SAR_H + m["extra_sar"]


def _nodes(n_keys, n_nodes, seed=11):
    """Equal-probability nodes of a standard normal (1 key: mid-quantiles; several keys: Latin hypercube)."""
    u = (np.arange(n_nodes) + 0.5) / n_nodes
    if n_keys == 1:
        return norm.ppf(u)[:, None]
    rng = np.random.default_rng(seed)
    return np.column_stack([norm.ppf(rng.permutation(u)) for _ in range(n_keys)])


def _rule_eval(sc, pr, k, Ts):
    """(E[NPV], P(target)) of portfolio k on the given scenarios; k None = no investment (NPV 0, target missed)."""
    if k is None:
        return 0.0, 0.0
    return float(sc.PNPV[k].mean()), float((sc.PT12[k] >= Ts).mean())


def preposterior(activity, keys, post_sd_frac=0.0, n=20000, seed=20261024, n_nodes=16, budget=None, alpha=None, beta=None):
    """Value of revealing the estimation error of `keys` (post_sd_frac = remaining error as a fraction of the prior sd).
    Returns per rule: prior and posterior expected NPV and P(target), their differences, and the node choices."""
    res, ctx = run_decisions(activity, n, seed, budget, alpha, beta)
    sc, z, base, prm0 = ctx["sc"], ctx["z"], ctx["base"], ctx["prm0"]
    keys = [k for k in keys if k in activity and activity[k][1] > 0]
    out = {r: dict(prior_choice=res[r]) for r in ("D2", "D3", "D4")}
    if not keys:
        for r in out:
            out[r].update(d_npv=0.0, d_p_target=0.0, choices={res[r]: 1.0}, note="no estimated value to measure")
        return out
    f = post_sd_frac
    nodes = _nodes(len(keys), n_nodes)
    k0 = ctx["choices"]
    acc = {r: dict(npv_post=0.0, p_post=0.0, npv_prior=0.0, p_prior=0.0, ch={}) for r in out}
    for row in nodes:
        zc = dict(z)
        for j, k in enumerate(keys):
            zc[k] = np.sqrt(1 - f * f) * row[j] + f * z[k]
        prm, dT = _apply(activity, prm0, zc, base)
        Ts = ctx["T"] + dT
        scn = U.Scenarios(params=prm, basis="reporting")
        prn = D.portfolio_probs(scn, ctx["budget"], Ts)
        chn = _choices(prn, ctx["budget"], ctx["a_eff"], ctx["b_eff"])
        for r in out:
            e1, p1 = _rule_eval(scn, prn, chn[r], Ts)
            e0, p0 = _rule_eval(scn, prn, k0[r], Ts)
            a = acc[r]
            a["npv_post"] += e1 / len(nodes); a["p_post"] += p1 / len(nodes)
            a["npv_prior"] += e0 / len(nodes); a["p_prior"] += p0 / len(nodes)
            nm = scn.name(chn[r]) if chn[r] is not None else "none feasible"
            a["ch"][nm] = a["ch"].get(nm, 0) + 1 / len(nodes)
    for r in out:
        a = acc[r]
        out[r].update(npv_prior=a["npv_prior"], npv_post=a["npv_post"], d_npv=a["npv_post"] - a["npv_prior"],
                      p_prior=a["p_prior"], p_post=a["p_post"], d_p_target=a["p_post"] - a["p_prior"], choices=a["ch"])
    return out


def information_value(activity, measurements=None, n=20000, seeds=(20261024, 20261026, 20261027), n_nodes=16,
                      budget=None, alpha=None, beta=None):
    """Pre-posterior value of each candidate measurement under D2, D3 and D4, averaged over scenario seeds (sd
    across seeds reported), with hypothetical costs and net value (expected-NPV gain minus cost)."""
    rows = []
    for m in (measurements or MEASUREMENTS):
        if not any(k in activity and activity[k][1] > 0 for k in m["keys"]):
            continue
        per_seed = [preposterior(activity, m["keys"], m["post_sd_frac"], n, s, n_nodes, budget, alpha, beta) for s in seeds]
        cost = measurement_cost(m)
        for r in ("D2", "D3", "D4"):
            d = np.array([ps[r]["d_npv"] for ps in per_seed]); dp = np.array([ps[r]["d_p_target"] for ps in per_seed])
            ch = {}
            for ps in per_seed:
                for kk, w in ps[r]["choices"].items():
                    ch[kk] = ch.get(kk, 0) + w / len(per_seed)
            rows.append(dict(measurement=m["id"], label=m["label"], keys="+".join(m["keys"]), post_sd_frac=m["post_sd_frac"],
                             rule=r, prior_choice=per_seed[0][r]["prior_choice"], value_npv=float(d.mean()),
                             value_npv_sd_seeds=float(d.std(ddof=1)) if len(d) > 1 else np.nan,
                             d_p_target=float(dp.mean()), cost_sar=cost, cost_status="hypothetical (staff time)",
                             net_value=float(d.mean() - cost),
                             worth_it=bool(d.mean() - cost > 2 * (d.std(ddof=1) if len(d) > 1 else 0)),
                             posterior_choices="; ".join(f"{k} {w:.0%}" for k, w in sorted(ch.items(), key=lambda x: -x[1]))))
    return rows


def sensitivity_bounds(activity, keys=None, n=20000, seed=20261024, budget=None, alpha=None, beta=None):
    """Decisions with each estimated total at its estimate +/- 1.96 sd (one stream at a time)."""
    out = []
    for k, (val, sd) in activity.items():
        if sd <= 0 or (keys and k not in keys):
            continue
        for sign in (-1, 1):
            a = dict(activity); a[k] = (val + sign * 1.96 * sd, 0.0)
            r, _ = run_decisions(a, n, seed, budget, alpha, beta)
            out.append(dict(key=k, bound="low" if sign < 0 else "high", value=val + sign * 1.96 * sd,
                            D1=r["D1"], D2=r["D2"], D3=r["D3"], D4=r["D4"], target_t=r["target_t"], p_target_AB=r["p_target[A+B]"],
                            min_budget=r["min_budget"]))
    return out
