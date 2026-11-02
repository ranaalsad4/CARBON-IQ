"""Decision stability: is a recommendation robust to Monte Carlo sampling error and to estimation error in the data?

Three checks per decision rule (D1-D4), all on the existing engines:
  1. Margins to the thresholds that define the choice, in natural units and in Monte Carlo standard errors
     (chance constraints: p - alpha_saa with SE = sqrt(p(1-p)/n); D2: E[NPV] gap to the runner-up with the paired SE;
     D1: target slack and NPV gap; D4 infeasibility: best budget probability vs beta and minimum budget vs budget).
  2. Data perturbation: K plausible 'true' datasets are drawn from the estimates' uncertainty (total_k + sd_k * w_k);
     each is treated as known (sd = 0) and the rules are re-applied. Agreement = share of draws giving the same choice.
  3. Switch points: the smallest change of each estimated stream total (in % and in estimate sds) that changes the
     choice of each rule (grid search then bisection).
A rule is flagged UNSTABLE when |margin| < 2 SE (sampling), agreement < 95% (data), or a switch point lies within
1.96 sd of an estimate (data). Flags describe the decision; they never change it.
"""
import numpy as np

from . import integrate as I

SE_LIMIT = 2.0
AGREE_LIMIT = 0.95
SWITCH_GRID = (0.0025, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10)


def margins(activity, n=20000, seed=20261024, budget=None, alpha=None, beta=None, ctx=None, res=None):
    if ctx is None:
        res, ctx = I.run_decisions(activity, n, seed, budget, alpha, beta)
    sc, pr, ch = ctx["sc"], ctx["pr"], ctx["choices"]
    budget, a_eff, b_eff, n = ctx["budget"], ctx["a_eff"], ctx["b_eff"], sc.n
    afford = [k for k in range(len(sc.ports)) if pr["quote"][k] <= budget + 1e-6]
    se = lambda p: float(np.sqrt(max(p * (1 - p), 1e-12) / n))  # noqa: E731
    rows = []
    # D1 deterministic
    best = ctx["best"]
    if best:
        _, allrows = I.O.enumerate_best(ctx["prj"], ctx["inter"], budget, ctx["T"])
        others = sorted([r for r in allrows if r["feasible"] and r["portfolio"] != best["portfolio"]], key=lambda r: -r["npv"])
        red = float(best["scope12_t"])
        rows.append(dict(rule="D1", choice=best["portfolio"], threshold="Scope 1+2 reduction >= target (deterministic)",
                         value=red, limit=ctx["T"], margin=red - ctx["T"], margin_rel=(red - ctx["T"]) / ctx["T"],
                         margin_se=np.nan, runner_up=others[0]["portfolio"] if others else "",
                         runner_up_gap=float(best["npv"] - others[0]["npv"]) if others else np.nan,
                         sampling_unstable=False))
    # D2 expected NPV
    k2 = ch["D2"]
    alt = sorted([k for k in afford if k != k2], key=lambda k: -pr["e_npv"][k])[0]
    diff = sc.PNPV[k2] - sc.PNPV[alt]
    se2 = float(diff.std(ddof=1) / np.sqrt(n))
    rows.append(dict(rule="D2", choice=sc.name(k2), threshold="highest E[NPV] among affordable portfolios",
                     value=float(pr["e_npv"][k2]), limit=float(pr["e_npv"][alt]), margin=float(diff.mean()),
                     margin_rel=float(diff.mean() / abs(pr["e_npv"][k2])), margin_se=float(diff.mean() / se2) if se2 > 0 else np.inf,
                     runner_up=sc.name(alt), runner_up_gap=float(diff.mean()), sampling_unstable=bool(diff.mean() < SE_LIMIT * se2)))
    # D3 carbon chance constraint: chosen portfolio and the best-NPV portfolio it excludes
    for rule, need_b in (("D3", False), ("D4", True)):
        k = ch[rule]
        feas = lambda j: (pr["p_target"][j] >= a_eff - 1e-12) and (not need_b or pr["p_budget"][j] >= b_eff - 1e-12)  # noqa: E731
        excluded = sorted([j for j in afford if not feas(j) and (k is None or pr["e_npv"][j] > pr["e_npv"][k])],
                          key=lambda j: -pr["e_npv"][j])
        if k is not None:
            p = float(pr["p_target"][k])
            m_ch = p - a_eff
            rows.append(dict(rule=rule, choice=sc.name(k), threshold=f"P(target) >= {a_eff:.4f}", value=p, limit=a_eff,
                             margin=m_ch, margin_rel=np.nan, margin_se=m_ch / se(p), runner_up="", runner_up_gap=np.nan,
                             sampling_unstable=bool(abs(m_ch) < SE_LIMIT * se(p))))
        if excluded:
            # the excluded higher-value portfolio closest to becoming feasible: its distance is the most negative of
            # its failing margins (all of them must flip for it to qualify)
            def dist(j):
                fails = []
                pt, pb = float(pr["p_target"][j]), float(pr["p_budget"][j])
                if pt < a_eff - 1e-12:
                    fails.append((( pt - a_eff) / se(pt), pt, a_eff, f"P(target) >= {a_eff:.4f}"))
                if need_b and pb < b_eff - 1e-12:
                    fails.append(((pb - b_eff) / se(pb), pb, b_eff, f"P(capex <= budget) >= {b_eff:.4f}"))
                return min(fails)
            j = max(excluded, key=lambda j: dist(j)[0])
            m_se, val, lim, what = dist(j)
            rows.append(dict(rule=rule, choice=f"(excluded: {sc.name(j)})", threshold=what, value=val, limit=lim, margin=val - lim,
                             margin_rel=np.nan, margin_se=m_se, runner_up=sc.name(j),
                             runner_up_gap=float(pr["e_npv"][j] - (pr["e_npv"][k] if k is not None else 0.0)),
                             sampling_unstable=bool(abs(m_se) < SE_LIMIT)))
        if need_b and k is None:
            carbon_ok = [j for j in afford if pr["p_target"][j] >= a_eff - 1e-12]
            jb = max(carbon_ok, key=lambda j: pr["p_budget"][j]) if carbon_ok else None
            if jb is not None:
                pb = float(pr["p_budget"][jb])
                rows.append(dict(rule="D4", choice="none feasible", threshold=f"best P(capex <= budget) among carbon-feasible >= {b_eff:.4f}",
                                 value=pb, limit=b_eff, margin=pb - b_eff, margin_rel=np.nan, margin_se=(pb - b_eff) / se(pb),
                                 runner_up=sc.name(jb), runner_up_gap=np.nan, sampling_unstable=bool(abs(pb - b_eff) < SE_LIMIT * se(pb))))
            if res and res.get("min_budget"):
                rows.append(dict(rule="D4", choice="none feasible", threshold="minimum budget for D4 vs budget", value=res["min_budget"],
                                 limit=budget, margin=res["min_budget"] - budget, margin_rel=res["min_budget"] / budget - 1,
                                 margin_se=np.nan, runner_up=res["min_budget_portfolio"], runner_up_gap=np.nan, sampling_unstable=False))
    return rows


def perturbation(activity, K=40, n=20000, seed=20261024, draw_seed=909, budget=None, alpha=None, beta=None):
    """Share of plausible 'true' datasets (drawn from the estimation uncertainty) giving each rule's current choice."""
    base_res, _ = I.run_decisions(activity, n, seed, budget, alpha, beta)
    est = {k: (val, sd) for k, (val, sd) in activity.items() if sd > 0}
    if not est:
        return {r: dict(choice=base_res[r], agreement=1.0, draws=0, alternatives={}) for r in I.RULES}, []
    rng = np.random.default_rng(draw_seed)
    draws = []
    for _ in range(K):
        a = dict(activity)
        for k, (val, sd) in est.items():
            a[k] = (max(val + sd * rng.standard_normal(), 0.0), 0.0)
        r, _ = I.run_decisions(a, n, seed, budget, alpha, beta)
        draws.append({x: r[x] for x in I.RULES} | {"p_target[A+B]": r["p_target[A+B]"], "scope12": r["scope12"]})
    out = {}
    for rule in I.RULES:
        ch = [d[rule] for d in draws]
        alt = {c: ch.count(c) / K for c in set(ch)}
        out[rule] = dict(choice=base_res[rule], agreement=alt.get(base_res[rule], 0.0), draws=K, alternatives=alt)
    return out, draws


def switch_points(activity, n=20000, seed=20261024, keys=None, budget=None, alpha=None, beta=None):
    """Smallest relative change of one stream total (other streams fixed) that changes each rule's choice."""
    base_res, _ = I.run_decisions(activity, n, seed, budget, alpha, beta)
    keys = keys or [k for k, (_, sd) in activity.items() if sd > 0]
    rows = []
    for k in keys:
        val, sd = activity[k]
        for sign in (-1, 1):
            cache = {}

            def dec(delta):
                if delta not in cache:
                    a = dict(activity); a[k] = (val * (1 + sign * delta), sd)
                    cache[delta] = I.run_decisions(a, n, seed, budget, alpha, beta)[0]
                return cache[delta]
            for rule in I.RULES:
                lo, hi = 0.0, None
                for d in SWITCH_GRID:
                    if dec(d)[rule] != base_res[rule]:
                        hi = d; break
                    lo = d
                if hi is not None:
                    for _ in range(5):
                        mid = (lo + hi) / 2
                        if dec(mid)[rule] != base_res[rule]:
                            hi = mid
                        else:
                            lo = mid
                rows.append(dict(key=k, direction="down" if sign < 0 else "up", rule=rule, choice=base_res[rule],
                                 switch_rel=hi, switch_abs=val * hi if hi else None,
                                 switch_in_sd=(val * hi / sd) if (hi and sd > 0) else None,
                                 new_choice=dec(hi)[rule] if hi else None,
                                 within_95=bool(hi is not None and sd > 0 and val * hi <= 1.96 * sd)))
    return rows


def assess(activity, n=20000, seed=20261024, K=40, budget=None, alpha=None, beta=None, with_switch=True, switch_keys=None):
    """Full stability assessment; returns dict(rules=[...], margins, perturbation, switch_points)."""
    res, ctx = I.run_decisions(activity, n, seed, budget, alpha, beta)
    mg = margins(activity, ctx=ctx, res=res)
    pt, draws = perturbation(activity, K, n, seed, budget=budget, alpha=alpha, beta=beta)
    sw = switch_points(activity, n, seed, keys=switch_keys, budget=budget, alpha=alpha, beta=beta) if with_switch else []
    rules = []
    for rule in I.RULES:
        ms = [m for m in mg if m["rule"] == rule]
        samp = any(m["sampling_unstable"] for m in ms)
        agree = pt[rule]["agreement"]
        sws = [s for s in sw if s["rule"] == rule and s["switch_rel"] is not None]
        near = [s for s in sws if s["within_95"]]
        data = agree < AGREE_LIMIT or bool(near)
        reasons = []
        if samp:
            m = min((x for x in ms if x["sampling_unstable"]), key=lambda x: abs(x["margin_se"]))
            reasons.append(f"{m['threshold']}: {m['value']:.4f} vs {m['limit']:.4f} ({m['margin_se']:+.1f} Monte Carlo SE)")
        if agree < AGREE_LIMIT:
            reasons.append(f"same choice in only {agree:.0%} of plausible true datasets ("
                           + ", ".join(f"{c} {w:.0%}" for c, w in sorted(pt[rule]['alternatives'].items(), key=lambda x: -x[1])) + ")")
        for s in near:
            reasons.append(f"{s['key']} {s['direction']} {s['switch_rel']:.1%} ({s['switch_in_sd']:.1f} sd) switches to {s['new_choice']}")
        status = "STABLE" if not (samp or data) else "UNSTABLE (" + " + ".join(
            x for x, f in (("sampling", samp), ("data", data)) if f) + ")"
        rules.append(dict(rule=rule, choice=res[rule], status=status, sampling_unstable=samp, data_unstable=data,
                          agreement=agree, min_switch_rel=min((s["switch_rel"] for s in sws), default=None), reasons="; ".join(reasons)))
    return dict(result=res, rules=rules, margins=mg, perturbation=pt, draws=draws, switch_points=sw)
