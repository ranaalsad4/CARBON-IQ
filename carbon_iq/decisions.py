"""v1.1 decision reporting: the three decision objectives side by side, the reporting-basis comparison, capital-cost
risk, and the tariff and grid-factor scenarios. Nothing here changes an equation of v1.0; it re-uses engine,
optimize and uncertainty and reports their results under clearly labelled alternative assumptions."""
import numpy as np

from . import engine as E
from . import optimize as O
from . import uncertainty as U
from .assumptions import (A5_CHANGE_LABELS, EF_GRID_SCENARIOS, GAS_SCENARIOS, P, PV_CAPEX_SCENARIOS, TARIFF_SCENARIOS, V12_CHANGES,
                          base_values, use_profile)


def _f(x):
    return float(x) if x is not None else None


def mean_inputs():
    """Base values with every uncertain input replaced by the mean of its distribution."""
    p = base_values()
    for k, prm in P.items():
        d = prm.dist
        if d is None:
            continue
        if d[0] == "uniform":
            p[k] = (d[1] + d[2]) / 2
        elif d[0] == "triangular":
            p[k] = (d[1] + d[2] + d[3]) / 3
        # normal_rel and mean-preserving lognormal already have mean = value (ignoring the 5% clip, negligible)
    return p


# ------------------------------------------------------------------ v1.2: probabilities for every portfolio
def portfolio_probs(sc, budget, target):
    """E[NPV], P(target), P(actual capex <= budget), P(both) and P90 capex for all 64 portfolios on one sample."""
    hit = sc.PT12 >= target
    ok = sc.PCAP <= budget + 1e-6
    return {"e_npv": sc.PNPV.mean(axis=1), "p_target": hit.mean(axis=1), "p_budget": ok.mean(axis=1),
            "p_both": (hit & ok).mean(axis=1), "p90_capex": np.percentile(sc.PCAP, 90, axis=1), "quote": sc.capex.copy(),
            "n": sc.n}


def choose(pr, budget, alpha=None, beta=None):
    """Index of the max-E[NPV] portfolio with quoted capex <= budget and the given reliability levels (None = no
    requirement). Returns None when no portfolio qualifies (infeasible) - no recommendation is forced."""
    cand = [k for k in range(len(pr["quote"])) if pr["quote"][k] <= budget + 1e-6
            and (alpha is None or pr["p_target"][k] >= alpha - 1e-12)
            and (beta is None or pr["p_budget"][k] >= beta - 1e-12)]
    return max(cand, key=lambda k: pr["e_npv"][k]) if cand else None


def validation_sample(n=200_000, seed=20261025, basis="reporting"):
    """Independent large sample used to validate chance-constraint feasibility (SAA practice)."""
    return U.Scenarios(n, seed=seed, basis=basis)


def decision_scenarios(det_best, sc_rep, sc_phys, sc_base, prv, budget, target, alpha, beta):
    """All decision rules on the same scenarios. Primary basis = fixed reporting baseline (sc_rep).
    prv = portfolio_probs on the independent validation sample (reporting basis)."""
    n = sc_rep.n
    a_eff, b_eff = U.alpha_saa(alpha, n), U.alpha_saa(beta, n)
    pr = portfolio_probs(sc_rep, budget, target)
    pph = portfolio_probs(sc_phys, budget, target)
    pbs = portfolio_probs(sc_base, budget, target)
    prj0, inter0 = E.projects(base_values())
    rules = [
        ("D1", "Deterministic optimisation", "comparison", sc_rep.index(det_best["ids"]), pr,
         "max NPV at base inputs; quoted capex <= budget; reduction >= target (no uncertainty)"),
        ("D2", "Maximum expected NPV", "comparison", choose(pr, budget), pr,
         "max E[NPV]; quoted capex <= budget; no reliability requirement"),
        ("D3a", f"Carbon chance constraint {alpha:.0%}, in-sample only (v1.1 method)", "comparison", choose(pr, budget, alpha), pr,
         f"max E[NPV]; P(target) >= {alpha:.0%} on the {n:,} scenarios, no correction for sampling error"),
        ("D3", f"Carbon chance constraint {alpha:.0%} (validated)", "primary (carbon only)", choose(pr, budget, a_eff), pr,
         f"max E[NPV]; P(target) >= {a_eff:.4f} in-sample (= {alpha:.0%} + sampling margin) and >= {alpha:.0%} on the validation sample"),
        ("D4", f"Carbon {alpha:.0%} + budget {beta:.0%} chance constraints", "PRIMARY RECOMMENDATION RULE", choose(pr, budget, a_eff, b_eff), pr,
         f"as D3, plus P(actual capex <= SAR {budget/1e6:.1f}M) >= {b_eff:.4f} in-sample and >= {beta:.0%} on validation"),
        ("S1", f"Carbon chance constraint {alpha:.0%}, sampled emission factors", "sensitivity (v1.1 primary)", choose(pph, budget, a_eff), pph,
         "as D3 but reductions counted with sampled emission factors"),
        ("S2", f"Carbon chance constraint {alpha:.0%}, uncertain baseline", "sensitivity (baseline uncertainty)", choose(pbs, budget, a_eff), pbs,
         "as D3 but target = 15% of the simulated baseline and reductions with sampled factors"),
    ]
    rows = []
    for rid, label, cat, k, own, form in rules:
        row = {"id": rid, "rule": label, "category": cat, "formulation": form}
        if k is None:
            row.update({"portfolio": "none feasible", "status": "infeasible"})
            rows.append(row); continue
        det = E.portfolio(sc_rep.ports[k], prj0, inter0)
        row.update({"portfolio": sc_rep.name(k), "capex_quote": float(pr["quote"][k]), "npv_base_inputs": float(det["npv"]),
                    "meets_target_base_inputs": bool(det["scope12_t"] >= target - 1e-9),
                    "e_npv": float(pr["e_npv"][k]), "p_target": float(pr["p_target"][k]), "p_target_own_basis": float(own["p_target"][k]),
                    "p_budget": float(pr["p_budget"][k]), "p_both": float(pr["p_both"][k]), "p90_capex": float(pr["p90_capex"][k]),
                    "p_target_val": float(prv["p_target"][k]), "p_budget_val": float(prv["p_budget"][k]), "e_npv_val": float(prv["e_npv"][k])})
        if rid in ("D3a", "D3"):
            row["status"] = "meets target reliability on validation" if prv["p_target"][k] >= alpha else "FAILS validation (P(target) < %.0f%%)" % (100 * alpha)
        elif rid == "D4":
            row["status"] = "feasible (validated)" if (prv["p_target"][k] >= alpha and prv["p_budget"][k] >= beta) else "FAILS validation"
        elif rid.startswith("S"):
            row["status"] = "sensitivity (in-sample)"
        else:
            row["status"] = "comparison"
        rows.append(row)
    return rows, {"alpha": alpha, "beta": beta, "alpha_saa": a_eff, "beta_saa": b_eff, "n": n, "n_validation": int(prv["n"])}


def budget_analysis(sc_rep, val, target, alpha, beta, budget, budgets=None):
    """When the joint rule is infeasible: minimum budget that makes it feasible, the budget curve, and the
    choices at alternative risk thresholds (all on the primary reporting basis)."""
    budgets = budgets if budgets is not None else np.round(np.arange(budget, budget * 1.3 + 1, 25_000), 0)
    a_eff, b_eff = U.alpha_saa(alpha, sc_rep.n), U.alpha_saa(beta, sc_rep.n)
    curve, min_b = [], None
    for B in budgets:
        pr, pv = portfolio_probs(sc_rep, B, target), portfolio_probs(val, B, target)
        k = choose(pr, B, a_eff, b_eff)
        validated = k is not None and pv["p_target"][k] >= alpha and pv["p_budget"][k] >= beta
        curve.append({"budget": float(B), "portfolio": sc_rep.name(k) if k is not None else "none feasible",
                      "e_npv": float(pr["e_npv"][k]) if k is not None else None,
                      "p_target": float(pr["p_target"][k]) if k is not None else None,
                      "p_budget": float(pr["p_budget"][k]) if k is not None else None,
                      "p_budget_val": float(pv["p_budget"][k]) if k is not None else None, "validated": bool(validated)})
        if validated and min_b is None:
            min_b = curve[-1]
    # exact minimum budget for each target-reliable portfolio: its 90th-percentile actual capex
    pr0, pv0 = portfolio_probs(sc_rep, budget, target), portfolio_probs(val, budget, target)
    exact = []
    for k in range(len(sc_rep.ports)):
        if pr0["p_target"][k] >= a_eff and pv0["p_target"][k] >= alpha:
            need = max(float(np.quantile(sc_rep.PCAP[k], b_eff, method="higher")), float(np.quantile(val.PCAP[k], beta, method="higher")),
                       float(sc_rep.capex[k]))
            exact.append({"portfolio": sc_rep.name(k), "budget_needed": need, "e_npv": float(pr0["e_npv"][k]),
                          "p_target": float(pr0["p_target"][k]), "p_target_val": float(pv0["p_target"][k])})
    exact.sort(key=lambda r: r["budget_needed"])
    grid = []
    for a in (0.80, 0.85, 0.90, 0.95):
        for b in (0.50, 0.60, 0.70, 0.75, 0.80, 0.90):
            k = choose(pr0, budget, U.alpha_saa(a, sc_rep.n), U.alpha_saa(b, sc_rep.n))
            ok = k is not None and pv0["p_target"][k] >= a and pv0["p_budget"][k] >= b
            grid.append({"alpha": a, "beta": b, "portfolio": sc_rep.name(k) if ok else "infeasible",
                         "e_npv": float(pr0["e_npv"][k]) if ok else None})
    return {"min_budget_grid": min_b, "min_budget_by_portfolio": exact[:8], "curve": curve, "thresholds": grid}


def knife_edge(sc_rep, val, target, ids=("A", "B"), seeds=(1, 2, 3, 777, 2026)):
    """Sampling check for a portfolio whose target probability is close to the required level."""
    k = sc_rep.index(ids)
    p_in = float((sc_rep.PT12[k] >= target).mean())
    p_val = float((val.PT12[k] >= target).mean())
    other = []
    for sd in seeds:
        z = U.Scenarios(sc_rep.n, seed=sd, basis=sc_rep.basis)
        other.append({"seed": sd, "p_target": float((z.PT12[k] >= target).mean())})
    return {"portfolio": "+".join(ids), "n": sc_rep.n, "n_validation": val.n, "p_in_sample": p_in, "se_in_sample": float(np.sqrt(p_in * (1 - p_in) / sc_rep.n)),
            "p_validation": p_val, "ci95_validation": [p_val - 1.96 * np.sqrt(p_val * (1 - p_val) / val.n),
                                                      p_val + 1.96 * np.sqrt(p_val * (1 - p_val) / val.n)],
            "other_seeds": other}


def why_they_differ(rows, mean_opt, ke, alpha):
    r = {x["id"]: x for x in rows}
    same = "both choose" if r["D1"]["portfolio"] == r["D2"]["portfolio"] else "choose"
    d12 = r["D1"]["portfolio"] if same == "both choose" else f"{r['D1']['portfolio']} and {r['D2']['portfolio']}"
    out = [f"D1 and D2 {same} {d12}. The deterministic NPV (SAR {r['D1']['npv_base_inputs']:,.0f}) is below the "
           f"expected NPV (SAR {r['D2']['e_npv']:,.0f}) because the deterministic case uses most-likely values while the tariff "
           f"range is skewed upwards (mode 0.18, mean 0.207 SAR/kWh); at mean inputs the deterministic optimum is "
           f"{mean_opt['portfolio']} (NPV SAR {mean_opt['npv']:,.0f})."]
    if ke["p_validation"] < alpha:
        out.append(f"With fixed reporting factors, {ke['portfolio']} meets the target in {ke['p_in_sample']:.2%} of the {ke['n']:,} scenarios, so the "
                   f"in-sample rule D3a accepts it. On an independent validation sample of {ke['n_validation']:,} scenarios its probability is "
                   f"{ke['p_validation']:.2%} (95% CI {ke['ci95_validation'][0]:.2%}-{ke['ci95_validation'][1]:.2%}), below {alpha:.0%}: the in-sample "
                   f"pass is a sampling artefact. The validated carbon rule D3 therefore chooses {r['D3']['portfolio']}.")
    else:
        out.append(f"With fixed reporting factors, {ke['portfolio']} meets the target in {ke['p_in_sample']:.2%} of the {ke['n']:,} scenarios "
                   f"and {ke['p_validation']:.2%} on an independent validation sample of {ke['n_validation']:,} (95% CI "
                   f"{ke['ci95_validation'][0]:.2%}-{ke['ci95_validation'][1]:.2%}), above {alpha:.0%}. The validated carbon rule D3 chooses "
                   f"{r['D3']['portfolio']}, which has a higher expected NPV among the portfolios that pass.")
    if r["D4"]["portfolio"] == "none feasible":
        out.append(f"No portfolio meets both the {alpha:.0%} carbon and the budget-compliance requirement within the budget: the "
                   "target-reliable portfolios within the budget (A+C+D, alone or with the steel switch) use 94-95% of it at quoted cost, so cost "
                   "uncertainty pushes them over it too often. No recommendation is forced; the budget and risk-threshold analysis shows what would make the rule feasible.")
    return out


def capex_risk(sc, budget, target, alpha, levels=(0.8, 0.9, 0.95)):
    """Capital-cost risk table on the primary sample; `alpha` should already be the tightened level."""
    rows = []
    for st in sorted(sc.table(budget, target), key=lambda r: -r["e_npv"]):
        rows.append({k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in st.items()
                     if k in ("portfolio", "capex", "e_capex", "p90_capex", "p95_capex", "p_over_budget",
                              "p_target", "p_target_and_budget", "e_npv", "contingency_p90")})
    variants = []
    for b in levels:
        k, e, pt, ok = sc.decide(budget, target, alpha, budget_reliability=b)
        variants.append({"budget_reliability": b, "portfolio": sc.name(k) if (k is not None and ok) else "none feasible",
                         "e_npv": _f(e) if ok else None, "p_target": _f(pt) if ok else None})
    # smallest budget at which the chance-constrained choice also stays within budget with 90% probability
    kc, *_ = sc.decide(budget, target, alpha)
    return {"table": rows, "with_budget_reliability": variants,
            "cc_portfolio": sc.name(kc), "cc_p90_capex": float(np.percentile(sc.PCAP[kc], 90)),
            "cc_contingency_p90": max(0.0, float(np.percentile(sc.PCAP[kc], 90)) - budget)}


def _run_case(p_det, sc, budget, alpha, beta):
    target = E.target_t(p_det)
    prj, inter = E.projects(p_det)
    best, _ = O.enumerate_best(prj, inter, budget, target)
    pr = portfolio_probs(sc, budget, target)
    a_eff, b_eff = U.alpha_saa(alpha, sc.n), U.alpha_saa(beta, sc.n)
    kb, kc, kj = choose(pr, budget), choose(pr, budget, a_eff), choose(pr, budget, a_eff, b_eff)
    nm = lambda k: sc.name(k) if k is not None else "none feasible"
    return {"target_t": float(target),
            "deterministic": best["portfolio"] if best else "infeasible", "det_npv": float(best["npv"]) if best else None,
            "best_expected": nm(kb), "best_expected_e_npv": float(pr["e_npv"][kb]), "best_expected_p_target": float(pr["p_target"][kb]),
            "chance_constrained": nm(kc), "cc_e_npv": float(pr["e_npv"][kc]) if kc is not None else None,
            "cc_p_target": float(pr["p_target"][kc]) if kc is not None else None,
            "cc_p_budget": float(pr["p_budget"][kc]) if kc is not None else None,
            "joint": nm(kj), "joint_e_npv": float(pr["e_npv"][kj]) if kj is not None else None,
            "joint_min_budget": _min_budget(sc, pr, a_eff, b_eff)}


def _min_budget(sc, pr, a_eff, b_eff):
    """Smallest budget at which the joint rule D4 is feasible (carbon level met; b_eff quantile of actual capex)."""
    need = [max(float(np.quantile(sc.PCAP[k], b_eff, method="higher")), float(sc.capex[k]))
            for k in range(len(sc.ports)) if pr["p_target"][k] >= a_eff - 1e-12]
    return min(need) if need else None


def gas_scenarios(n, seed, budget, alpha, beta=0.9, basis="reporting"):
    """A5: industrial gas price scenarios (same relative uncertainty around each centre)."""
    out = []
    for s in GAS_SCENARIOS:
        p = base_values(); p["gas_price_usd"] = s["value"]
        prm = U.sample(n, seed)
        prm["gas_price_usd"] = prm["gas_price_usd"] * s["value"] / base_values()["gas_price_usd"]
        sc = U.Scenarios(params=prm, basis=basis)
        out.append({"id": s["id"], "gas_price_usd": s["value"], "label": s["label"], "status": s["status"], **_run_case(p, sc, budget, alpha, beta)})
    return out


def pv_capex_scenarios(n, seed, budget, alpha, beta=0.9, basis="reporting"):
    """A5: rooftop PV capital-cost scenarios (same relative uncertainty around each centre)."""
    out = []
    for s in PV_CAPEX_SCENARIOS:
        p = base_values(); p["pv_capex_kw"] = s["value"]
        prm = U.sample(n, seed)
        prm["pv_capex_kw"] = prm["pv_capex_kw"] * s["value"] / base_values()["pv_capex_kw"]
        sc = U.Scenarios(params=prm, basis=basis)
        out.append({"id": s["id"], "pv_capex_kw": s["value"], "label": s["label"], **_run_case(p, sc, budget, alpha, beta)})
    return out


def tariff_scenarios(n, seed, budget, alpha, beta=0.9, basis="reporting"):
    out = []
    for s in TARIFF_SCENARIOS:
        p = base_values(); p["tariff"] = s["value"]
        sc = U.Scenarios(params=U.sample(n, seed, fixed={"tariff": s["value"]}), basis=basis)
        out.append({"id": s["id"], "tariff": s["value"], "label": s["label"], "status": s["status"], "effective": s["effective"],
                    **_run_case(p, sc, budget, alpha, beta)})
    return out


def ef_scenarios(n, seed, budget, alpha, beta=0.9, basis="reporting"):
    out = []
    for s in EF_GRID_SCENARIOS:
        p = base_values(); p["ef_grid"] = s["value"]
        prm = U.sample(n, seed)
        prm["ef_grid"] = prm["ef_grid"] * s["value"] / base_values()["ef_grid"]   # same relative uncertainty, new centre
        sc = _reporting_with_factor(prm, s["value"]) if basis == "reporting" else U.Scenarios(params=prm, basis=basis)
        out.append({"id": s["id"], "ef_grid": s["value"], "label": s["label"], **_run_case(p, sc, budget, alpha, beta)})
    return out


def _reporting_with_factor(prm, ef):
    """Reporting-basis scenarios whose fixed grid factor is `ef` (other factors at reference values)."""
    base = base_values()
    n = len(prm["ef_grid"])
    sc = U.Scenarios(params=prm, basis="physical")
    pe = dict(prm)
    pe.update({k: np.full(n, base[k]) for k in U.EF_KEYS})
    pe["ef_grid"] = np.full(n, ef)
    z = U.Scenarios(params=pe, basis="physical")
    sc.T12, sc.PT12, sc.PT3, sc.basis = z.T12, z.PT12, z.PT3, "reporting"
    return sc


A5_GROUPS = [("ef_grid",), ("gas_price_usd", "tree_g_reform"), ("pv_capex_kw",), ("pv_yield",), ("pv_degradation",),
             ("c_saving_frac", "c_om")]


def _case_metrics(n, seed, budget, alpha, beta):
    p = base_values()
    sc = U.Scenarios(params=U.sample(n, seed), basis="reporting")
    out = _run_case(p, sc, budget, alpha, beta)
    tot = E.scope_totals(E.baseline(p))
    pr = portfolio_probs(sc, budget, E.target_t(p))
    prj, inter = E.projects(p)
    for ids in (("A", "B"), ("A", "C", "D"), ("A", "B", "C")):
        k = sc.index(ids); nm = "+".join(ids)
        out[f"p_target[{nm}]"] = float(pr["p_target"][k]); out[f"p_budget[{nm}]"] = float(pr["p_budget"][k])
        out[f"e_npv[{nm}]"] = float(pr["e_npv"][k])
        out[f"npv[{nm}]"] = float(E.portfolio(ids, prj, inter)["npv"]); out[f"t12[{nm}]"] = float(E.portfolio(ids, prj, inter)["scope12_t"])
    out.update(scope12=tot["Scope 1+2"], scope2=tot["Scope 2"], total=tot["Total"])
    return out


def a5_attribution(n, seed, budget, alpha, beta=0.9):
    """A5 before/after: the v1.2 register, each A5 change applied alone (others at v1.2), and all changes (v1.3)."""
    rows = []
    with use_profile("v1.2"):
        rows.append(dict(case="v1.2 register", change="-", **_case_metrics(n, seed, budget, alpha, beta)))
    for grp in A5_GROUPS:
        others = [k for k in V12_CHANGES if k not in grp]
        with use_profile("v1.2", keys=others):
            rows.append(dict(case="only: " + " + ".join(grp), change="; ".join(A5_CHANGE_LABELS[k] for k in grp),
                             **_case_metrics(n, seed, budget, alpha, beta)))
    rows.append(dict(case="v1.3 register (all A5 changes)", change="all", **_case_metrics(n, seed, budget, alpha, beta)))
    return rows