"""End-to-end CARBON IQ analysis: one function returns every result used by the outputs, workbook, report and app."""
import numpy as np

from . import decisions as D
from . import engine as E
from . import optimize as O
from . import sensitivity as S
from . import timing as TM
from . import uncertainty as U
from . import voi as V
from .assumptions import EF_GRID_EVIDENCE, MODEL_VERSION, P, PROJECTS, TARIFF_SCENARIOS, base_values, v

N_SCENARIOS = 20000
SEED = 20261024
N_VALIDATION = 200_000          # independent sample (seed + 1) for chance-constraint validation


def f(x):
    return float(x) if isinstance(x, (np.floating, np.ndarray)) and np.ndim(x) == 0 else x


def run(n=N_SCENARIOS, seed=SEED, timing_detail=True, n_validation=N_VALIDATION):
    p = base_values()
    budget, alpha = v("budget"), v("chance_level")
    res = {"meta": {"scenarios": n, "seed": seed, "budget": budget, "chance_level": alpha}}

    # Method 1
    rows = E.baseline(p)
    res["baseline"] = rows
    res["scope_totals"] = E.scope_totals(rows)
    unc, unc_tot = E.uncertainty_table(rows)
    res["uncertainty"] = unc
    res["uncertainty_totals"] = {k: {"emissions_t": a, "u95_pct": b} for k, (a, b) in unc_tot.items()}
    T = E.target_t(p)
    res["target_t"] = T

    # projects
    prj, inter = E.projects(p)
    res["projects"] = [{"id": k, "name": d["name"], "capex": f(d["capex"]), "annual_cf": f(d["annual_cf"]), "life": f(d["life"]),
                        "npv": f(d["npv"]), "scope12_t": f(d["scope12_t"]), "scope3_t": f(d["scope3_t"]),
                        "mac_sar_per_t": f(E.mac(d)), "payback_y": f(E.simple_payback(d["capex"], d["annual_cf"])) if d["annual_cf"] > 0 else None,
                        "irr": E.project_irr(d, p.get("pv_degradation", 0.0) if k == "A" else 0.0) if d["annual_cf"] > 0 else None,
                        "d_elec_mwh": f(d["d_elec_mwh"]), "d_gas_gj": f(d["d_gas_gj"]), "d_diesel_l": f(d["d_diesel_l"])}
                       for k, d in prj.items()]
    res["interaction"] = {k: {kk: f(vv) for kk, vv in d.items()} for k, d in inter.items()}

    # Method 2
    best, allp = O.enumerate_best(prj, inter, budget, T)
    milp = O.solve_milp(prj, inter, budget, T)
    best_nt, _ = O.enumerate_best(prj, inter, budget, 0.0)
    res["optimal"] = {k: (list(vv) if isinstance(vv, tuple) else f(vv)) for k, vv in best.items()}
    res["optimal_no_target"] = {"portfolio": best_nt["portfolio"], "npv": best_nt["npv"], "scope12_t": best_nt["scope12_t"]}
    res["milp"] = {"portfolio": milp["portfolio"], "npv": milp["npv"], "agrees_with_enumeration": milp["portfolio"] == best["portfolio"]}
    res["portfolios"] = [{k: (list(vv) if isinstance(vv, tuple) else f(vv)) for k, vv in r.items()} for r in allp]
    res["baselines"] = [{k: (list(vv) if isinstance(vv, tuple) else f(vv)) for k, vv in b.items()} for b in O.baselines(prj, inter, budget, T)]
    res["frontier"] = O.frontier(prj, inter, budget, sorted(list(np.arange(0, 1801, 50)) + [round(T, 1)]))
    led = E.ledger(best["ids"], p)
    led0 = E.ledger((), p)
    res["ledger_check"] = {"portfolio": best["portfolio"], "ledger_scope12_reduction": led0["scope12_t"] - led["scope12_t"],
                           "sum_with_overlap": best["scope12_t"],
                           "naive_sum_without_overlap": sum(float(prj[i]["scope12_t"]) for i in best["ids"]),
                           "abc_ledger": led0["scope12_t"] - E.ledger(("A", "B", "C"), p)["scope12_t"],
                           "abc_naive": sum(float(prj[i]["scope12_t"]) for i in "ABC")}

    # Method 3 - primary counting basis = fixed reporting baseline (management decision, 25 Oct 2026)
    beta = v("budget_chance_level")
    res["meta"].update({"budget_chance_level": beta, "primary_basis": "reporting", "n_validation": n_validation,
                        "seed_validation": seed + 1})
    sc_phys = U.Scenarios(n, seed)                                   # v1.0/v1.1 sample, sampled factors
    sc = U.Scenarios(params=sc_phys.p, basis="reporting")            # PRIMARY: same scenarios, fixed reporting factors
    sc_base = U.Scenarios(params=sc_phys.p, basis="baseline")        # sensitivity: uncertain baseline
    a_eff, b_eff = U.alpha_saa(alpha, n), U.alpha_saa(beta, n)
    val = D.validation_sample(n_validation, seed + 1, "reporting")   # independent validation sample
    prv = D.portfolio_probs(val, budget, T)
    tab = sorted(sc.table(budget, T), key=lambda r: -r["e_npv"])
    for r in tab:
        k = sc.index(tuple(r["portfolio"].split("+")) if r["portfolio"] != "(none)" else ())
        r["p_budget"] = 1 - r["p_over_budget"]
        r["p_target_physical"] = float((sc_phys.PT12[k] >= T).mean())
        r["p_target_val"], r["p_budget_val"] = float(prv["p_target"][k]), float(prv["p_budget"][k])
    res["mc_portfolios"] = [{k: f(vv) for k, vv in r.items()} for r in tab]
    kb = sc.best_expected(budget)
    kc, ec, pc, okc = sc.decide(budget, T, a_eff)                    # carbon rule, tightened in-sample level
    res["mc_best_expected"] = sc.stats(kb, T, budget=budget)
    res["mc_chance_constrained"] = {**sc.stats(kc, T, budget=budget), "feasible": okc, "alpha_saa": a_eff,
                                    "p_target_val": float(prv["p_target"][kc]), "p_budget_val": float(prv["p_budget"][kc])}
    res["mc_deterministic_optimum"] = sc.stats(sc.index(best["ids"]), T, budget=budget)
    kj, ej, pj, okj = sc.decide(budget, T, a_eff, budget_reliability=b_eff)
    res["mc_joint"] = ({**sc.stats(kj, T, budget=budget), "feasible": True} if kj is not None and okj
                       else {"portfolio": "none feasible", "feasible": False})

    # decision scenarios, budget analysis, sampling check
    pm = D.mean_inputs()
    prm_, inm_ = E.projects(pm)
    bm, _ = O.enumerate_best(prm_, inm_, budget, E.target_t(pm))
    res["deterministic_mean_inputs"] = {"portfolio": bm["portfolio"], "npv": bm["npv"], "scope12_t": bm["scope12_t"],
                                        "tariff_mean": pm["tariff"]}
    rows, levels = D.decision_scenarios(best, sc, sc_phys, sc_base, prv, budget, T, alpha, beta)
    res["decision_scenarios"], res["decision_levels"] = rows, levels
    res["knife_edge"] = D.knife_edge(sc, val, T)
    res["objectives_explanation"] = D.why_they_differ(rows, res["deterministic_mean_inputs"], res["knife_edge"], alpha)
    res["budget_analysis"] = D.budget_analysis(sc, val, T, alpha, beta, budget)
    del val
    res["capex_risk"] = D.capex_risk(sc, budget, T, a_eff)
    res["regret"] = sc.regret(budget, T)
    res["mc_inputs"] = {k: {"mean": float(sc.p[k].mean()), "p5": float(np.percentile(sc.p[k], 5)),
                            "p95": float(np.percentile(sc.p[k], 95))} for k in P if P[k].dist is not None}
    res["mc_hist"] = {sc.name(k): sc.PNPV[k].tolist()[:5000] for k in (kb, kc)}
    s12 = sc.p["elec_mwh"] * sc.p["ef_grid"] + sc.p["gas_gj"] * sc.p["ef_gas"] + (sc.p["diesel_forklift_l"] + sc.p["diesel_genset_l"]) * sc.p["ef_diesel"]
    res["mc_baseline_scope12"] = {"mean": float(s12.mean()), "p2_5": float(np.percentile(s12, 2.5)), "p97_5": float(np.percentile(s12, 97.5)),
                                  "u95_pct": float((np.percentile(s12, 97.5) - np.percentile(s12, 2.5)) / 2 / s12.mean() * 100)}

    # Method 5 - value of information under the primary carbon rule (tightened), with the v1.1 rule as comparison
    res["evpi"] = V.evpi(sc, budget, T, a_eff)
    rk, noise = V.ranking(sc, budget, T, a_eff)
    for r in rk:
        r["net_of_noise_floor"] = r["evppi_sar"] - noise
    res["voi"], res["voi_noise_floor"] = rk, noise
    evsi, choices, _ = V.evsi_audit(sc, budget, T, a_eff)
    res["evsi_audit"] = {"evsi": evsi, "audit_cost": v("cost_motor_audit"), "net": evsi - v("cost_motor_audit"),
                         "net_of_noise_floor": evsi - noise, "error_sd": v("audit_error_sd"), "choices_by_signal_bin": choices}
    rk_c, noise_c = V.ranking(sc_phys, budget, T, alpha)
    evsi_c, _, _ = V.evsi_audit(sc_phys, budget, T, alpha)
    res["voi_comparison_v11"] = {"rule": "carbon chance constraint 90%, sampled factors, in-sample (v1.1)",
                                 "evpi": V.evpi(sc_phys, budget, T, alpha), "noise_floor": noise_c, "evsi_audit": evsi_c,
                                 "ranking": [{"parameter": r["parameter"], "information": r["information"], "evppi_sar": r["evppi_sar"]} for r in rk_c]}

    # Method 6
    res["tornado_det_opt"] = S.tornado(tuple(best["ids"]))
    res["tornado_cc"] = S.tornado(tuple(sc.ports[kc]))
    # decision contrast: the expected-NPV choice vs the carbon-rule choice when they differ (v1.2: A+B vs A+C+D);
    # otherwise the carbon-rule choice vs the best other portfolio within budget by E[NPV] (A5: was hard-coded)
    if kb != kc:
        k1, k2 = kb, kc
    else:
        others = [k for k in sc.candidates(budget) if k != kc]
        k1, k2 = kc, max(others, key=lambda k: float(sc.PNPV[k].mean()))
    res["sobol_decision_pair"] = [sc.name(k1), sc.name(k2)]
    y_diff = sc.PNPV[k1] - sc.PNPV[k2]
    res["sobol_decision"] = S.first_order(sc, y_diff)
    res["sobol_npv_cc"] = S.first_order(sc, sc.PNPV[kc])
    res["sobol_t12_det"] = S.first_order(sc, sc.PT12[sc.index(best["ids"])])
    sw = S.switch_points(budget, ["tariff", "b_saving_frac", "pv_yield", "pv_capex_kw", "b_capex", "c_saving_frac",
                                  "gas_price_usd", "ef_grid", "c_capex", "d_saving_frac"])
    res["switch_points"] = {k: {"range": x["range"], "changes": x["changes"], "robust": x["robust"]} for k, x in sw.items()}
    res["discount_robustness"] = S.discount_rate_robustness(budget)

    # Method 4
    res["timing_tree"] = TM.decision_tree()
    res["timing_tree_sweep"] = [{"p_reform": pr, **{k: TM.decision_tree(p_reform=pr)[k] for k in ("npv_invest_now", "value_wait_one_year", "decision")}}
                                for pr in (0.1, 0.3, 0.5, 0.7, 0.9)]
    res["timing_lsmc_now"] = TM.lsmc()
    res["timing_gbm"] = TM.gbm_trigger()
    if timing_detail:
        scan = TM.trigger_scan(levels=np.round(np.arange(3.0, 8.01, 0.25), 2), n=4000)
        res["timing_scan"] = scan
        res["timing_sens"] = [{"kappa": k, "sigma": s_, "trigger_usd": TM.trigger_scan(levels=np.round(np.arange(3.0, 10.01, 0.25), 2), n=2500, kappa=k, sigma=s_)["trigger_usd"]}
                              for k, s_ in ((0.2, 0.522), (1.0, 0.522), (0.5, 0.3), (0.5, 0.75))]
    # v1.1 scenarios for evidence-limited inputs (no single rate asserted)
    res["tariff_scenarios"] = D.tariff_scenarios(n, seed, budget, alpha, beta)
    res["tariff_evidence"] = TARIFF_SCENARIOS
    res["ef_scenarios"] = D.ef_scenarios(n, seed, budget, alpha, beta)
    res["ef_evidence"] = EF_GRID_EVIDENCE
    res["gas_scenarios"] = D.gas_scenarios(n, seed, budget, alpha, beta)
    res["pv_capex_scenarios"] = D.pv_capex_scenarios(n, seed, budget, alpha, beta)
    res["a5_attribution"] = D.a5_attribution(n, seed, budget, alpha, beta)
    res["meta"]["model_version"] = MODEL_VERSION
    res["assumptions"] = [{"key": k, "value": p_.value, "unit": p_.unit, "status": p_.status, "evidence": p_.evidence,
                           "group": p_.group, "source": p_.source, "note": p_.note, "dist": str(p_.dist) if p_.dist else "",
                           "published": p_.published, "effective": p_.effective, "geography": p_.geography, "url": p_.url}
                          for k, p_ in P.items()]
    res["project_names"] = PROJECTS
    return res, sc
