"""Method 2 - investment portfolio optimization (binary integer program) and ranking baselines.

max  sum_i x_i NPV_i - y_BC NPV_overlap
s.t. sum_i x_i capex_i <= budget
     sum_i x_i dE_i - y_BC dE_overlap >= target            (Scope 1+2, tCO2e/yr)
     y_BC >= x_B + x_C - 1,  y_BC <= x_B,  y_BC <= x_C      (overlap counted once)
     optional feasibility rules (e.g. mutually exclusive projects), x, y binary

Solved with scipy.optimize.milp (HiGHS) and cross-checked by exhaustive enumeration (2^6 = 64 portfolios).
"""
import itertools

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .engine import ALL, portfolio


def all_portfolios(ids=ALL):
    return [tuple(c) for r in range(len(ids) + 1) for c in itertools.combinations(ids, r)]


def _check_finite(prj, inter):
    """A6: refuse non-finite inputs. Without this check a NaN in any input made every NPV NaN and the enumeration
    silently returned an arbitrary portfolio (the MILP raised an unrelated error)."""
    bad = [f"{i}.{k}" for i, d in prj.items() for k in ("npv", "capex", "scope12_t")
           if not np.all(np.isfinite(np.asarray(d[k], dtype=float)))]
    bad += [f"BC.{k}" for k in ("npv", "scope12_t") if not np.all(np.isfinite(np.asarray(inter["BC"][k], dtype=float)))]
    if bad:
        raise ValueError("non-finite project values (check the inputs for missing or invalid entries): " + ", ".join(bad))


def evaluate_all(prj, inter, budget, target, exclusive=()):
    _check_finite(prj, inter)
    rows = []
    for c in all_portfolios():
        t = portfolio(c, prj, inter)
        feas_budget = t["capex"] <= budget + 1e-6
        feas_rules = not any(set(pair) <= set(c) for pair in exclusive)
        rows.append({"portfolio": "+".join(c) or "(none)", "ids": c, **{k: float(v) for k, v in t.items()},
                     "within_budget": feas_budget, "meets_target": t["scope12_t"] >= target - 1e-9,
                     "feasible": feas_budget and feas_rules and t["scope12_t"] >= target - 1e-9})
    return rows


def enumerate_best(prj, inter, budget, target, exclusive=()):
    rows = evaluate_all(prj, inter, budget, target, exclusive)
    feas = [r for r in rows if r["feasible"]]
    return (max(feas, key=lambda r: r["npv"]) if feas else None), rows


def solve_milp(prj, inter, budget, target, exclusive=()):
    _check_finite(prj, inter)
    ids = list(ALL)
    n = len(ids)
    npv = np.array([float(prj[i]["npv"]) for i in ids] + [-float(inter["BC"]["npv"])])
    cap = np.array([float(prj[i]["capex"]) for i in ids] + [0.0])
    t12 = np.array([float(prj[i]["scope12_t"]) for i in ids] + [-float(inter["BC"]["scope12_t"])])
    iB, iC, iy = ids.index("B"), ids.index("C"), n
    A, lo, hi = [cap, t12], [-np.inf, target], [budget, np.inf]
    def row(d):
        r = np.zeros(n + 1)
        for k, val in d.items():
            r[k] = val
        return r
    A += [row({iy: 1, iB: -1, iC: -1}), row({iy: 1, iB: -1}), row({iy: 1, iC: -1})]
    lo += [-1, -np.inf, -np.inf]; hi += [np.inf, 0, 0]
    for a, b in exclusive:
        A.append(row({ids.index(a): 1, ids.index(b): 1})); lo.append(-np.inf); hi.append(1)
    res = milp(c=-npv, constraints=LinearConstraint(np.array(A), lo, hi), integrality=np.ones(n + 1),
               bounds=Bounds(0, 1))
    if not res.success:
        return None
    x = np.round(res.x).astype(int)
    sel = tuple(i for i, xi in zip(ids, x[:n]) if xi)
    return {"ids": sel, "portfolio": "+".join(sel) or "(none)", "npv": -res.fun, "status": res.message}


def greedy(prj, inter, budget, key, label, require_positive_npv=True):
    """Rank projects by `key` and fund down the list while budget allows (the usual one-by-one ranking)."""
    order = sorted(ALL, key=key)
    pick, spent = [], 0.0
    for i in order:
        if require_positive_npv and float(prj[i]["npv"]) <= 0:
            continue
        if spent + float(prj[i]["capex"]) <= budget + 1e-6:
            pick.append(i); spent += float(prj[i]["capex"])
    t = portfolio(pick, prj, inter)
    return {"method": label, "ids": tuple(sorted(pick)), "portfolio": "+".join(sorted(pick)) or "(none)",
            **{k: float(v) for k, v in t.items()}, "order": "".join(order)}


def baselines(prj, inter, budget, target):
    from .engine import mac
    out = [
        greedy(prj, inter, budget, lambda i: -float(prj[i]["npv"]) / float(prj[i]["capex"]), "Rank by NPV per riyal (profitability index)"),
        greedy(prj, inter, budget, lambda i: -float(prj[i]["npv"]), "Rank by NPV"),
        greedy(prj, inter, budget, lambda i: float(mac(prj[i])) if i != "F" else 1e9, "Rank by abatement cost (MAC), cheapest first",
               require_positive_npv=False),
    ]
    for o in out:
        o["meets_target"] = o["scope12_t"] >= target - 1e-9
    return out


def frontier(prj, inter, budget, targets):
    """Best NPV achievable for each Scope 1+2 reduction target (efficient frontier)."""
    out = []
    for T in targets:
        best, _ = enumerate_best(prj, inter, budget, T)
        out.append({"target_t": T, "portfolio": best["portfolio"] if best else "infeasible",
                    "npv": best["npv"] if best else None, "scope12_t": best["scope12_t"] if best else None})
    return out
