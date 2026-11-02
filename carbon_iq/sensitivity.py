"""Method 6 - sensitivity analysis and decision robustness (Saltelli et al. 2008).

  uncertainty analysis : spread of outputs (Monte Carlo, uncertainty.py)
  sensitivity analysis : which inputs drive that spread
      - one-way (tornado): each input at its 5th / 95th percentile, all others at base
      - first-order variance share S_i = Var(E[Y|X_i]) / Var(Y), estimated by quantile binning on the
        Monte Carlo sample (valid for independent inputs; total-effect indices are a documented extension)
  robustness testing   : does the RECOMMENDED portfolio change? one-way sweeps record the switch points
"""
import numpy as np

from .assumptions import P, base_values
from .engine import projects, target_t
from .optimize import enumerate_best
from .voi import bins


def pct_values(key):
    p = P[key]
    d = p.dist
    if d is None:
        return None
    if d[0] == "normal_rel":
        return p.value * (1 - 1.645 * d[1]), p.value * (1 + 1.645 * d[1])
    if d[0] == "uniform":
        lo, hi = d[1], d[2]
        return lo + 0.05 * (hi - lo), lo + 0.95 * (hi - lo)
    if d[0] == "triangular":
        lo, mode, hi = d[1:]
        def ppf(q):
            c = (mode - lo) / (hi - lo) if hi > lo else 0
            return lo + np.sqrt(q * (hi - lo) * (mode - lo)) if q < c else hi - np.sqrt((1 - q) * (hi - lo) * (hi - mode))
        return float(ppf(0.05)), float(ppf(0.95))
    if d[0] == "lognormal":
        return p.value * np.exp(-1.645 * d[1] - d[1] ** 2 / 2), p.value * np.exp(1.645 * d[1] - d[1] ** 2 / 2)
    return None


def portfolio_npv(ids, p):
    prj, inter = projects(p)
    from .engine import portfolio
    return float(portfolio(ids, prj, inter)["npv"]), float(portfolio(ids, prj, inter)["scope12_t"])


def tornado(ids, keys=None):
    base = base_values()
    b_npv, b_t = portfolio_npv(ids, base)
    rows = []
    for k in (keys or [k for k in P if P[k].dist is not None]):
        lv = pct_values(k)
        if lv is None:
            continue
        res = []
        for val in lv:
            q = dict(base); q[k] = val
            res.append(portfolio_npv(ids, q))
        rows.append({"parameter": k, "low": lv[0], "high": lv[1], "npv_low": res[0][0], "npv_high": res[1][0],
                     "t12_low": res[0][1], "t12_high": res[1][1], "swing": abs(res[1][0] - res[0][0]),
                     "base_npv": b_npv, "base_t12": b_t})
    rows.sort(key=lambda r: -r["swing"])
    return rows


def first_order(sc, y, nb=25):
    out = {}
    vy = y.var()
    for k, p in P.items():
        if p.dist is None:
            continue
        x = sc.p[k]
        groups = bins(x, nb)
        m = np.array([y[g].mean() for g in groups if g.any()])
        w = np.array([g.mean() for g in groups if g.any()])
        out[k] = float(((m - y.mean()) ** 2 * w).sum() / vy) if vy > 0 else 0.0
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def switch_points(budget, keys, n=41):
    """Deterministic optimum (with target) across each input's 1st-99th percentile-like range."""
    base = base_values()
    T = target_t(base)
    out = {}
    for k in keys:
        d = P[k].dist
        if d is None:
            continue
        if d[0] == "uniform":
            lo, hi = d[1], d[2]
        elif d[0] == "triangular":
            lo, hi = d[1], d[3]
        elif d[0] == "normal_rel":
            lo, hi = P[k].value * (1 - 2.33 * d[1]), P[k].value * (1 + 2.33 * d[1])
        else:
            lo, hi = P[k].value * np.exp(-2.33 * d[1]), P[k].value * np.exp(2.33 * d[1])
        grid = np.linspace(lo, hi, n)
        seq = []
        for g in grid:
            q = dict(base); q[k] = float(g)
            prj, inter = projects(q)
            best, _ = enumerate_best(prj, inter, budget, T)
            seq.append((float(g), best["portfolio"] if best else "infeasible"))
        changes = [(seq[i][0], seq[i - 1][1], seq[i][1]) for i in range(1, len(seq)) if seq[i][1] != seq[i - 1][1]]
        out[k] = {"range": (float(lo), float(hi)), "sequence": seq, "changes": changes,
                  "robust": not changes}
    return out


def discount_rate_robustness(budget, rates=(0.04, 0.05, 0.06, 0.08, 0.10, 0.12)):
    base = base_values()
    T = target_t(base)
    out = []
    for r in rates:
        q = dict(base); q["discount_rate"] = r
        prj, inter = projects(q)
        best, _ = enumerate_best(prj, inter, budget, T)
        nt, _ = enumerate_best(prj, inter, budget, 0.0)
        out.append({"rate": r, "with_target": best["portfolio"] if best else "infeasible",
                    "npv_with_target": best["npv"] if best else None, "without_target": nt["portfolio"]})
    return out
