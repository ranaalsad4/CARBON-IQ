"""Method 3 - Monte Carlo evaluation and stochastic (chance-constrained) portfolio selection.

Evaluation: every portfolio whose QUOTED capital cost fits the budget is simulated over the same S scenarios (common
random numbers): expected NPV, 5th percentile, CVaR(5%) = mean of the worst 5%, P(NPV < 0),
P(Scope 1+2 reduction >= target), and (v1.1) the distribution of the ACTUAL capital cost: P(actual capex > budget)
and its 95th percentile.

Three decision objectives are reported side by side (they answer different questions and may legitimately differ):
  1. deterministic optimum      max NPV at base inputs        s.t. quoted capex <= budget, reduction >= target
  2. maximum expected NPV       max E[NPV]                    s.t. quoted capex <= budget   (no target requirement)
  3. chance-constrained (SAA)   max E[NPV]                    s.t. quoted capex <= budget, P(reduction >= target) >= alpha
With 64 portfolios the sample-average approximation is solved exactly by enumeration.

Budget feasibility (v1.1): the decision rules above check the QUOTED capex against the budget (baseline budget
feasibility, the usual capital-approval rule). Feasibility under uncertain costs is reported separately as
P(actual capex <= budget); `decide(..., budget_reliability=b)` adds the requirement P(actual capex <= budget) >= b.

Counting basis for the carbon target:
  basis="reporting"  PRIMARY from v1.2 (management decision, 25 Oct 2026): reductions are counted with the fixed
                     reference (reporting) emission factors against the fixed reporting baseline, as when a target is
                     verified against a fixed-factor inventory. Activity and savings uncertainty still apply.
  basis="physical"   sensitivity (v1.0/v1.1 primary): reductions counted with the sampled emission factors.
  basis="baseline"   sensitivity: the target is 15% of the SIMULATED baseline (activity and factor uncertainty) and
                     reductions use sampled factors, i.e. baseline uncertainty is tested separately.
The class default stays "physical" for backward compatibility; pipeline.py selects the primary basis explicitly.

Chance constraints estimated from S scenarios carry sampling error. `alpha_saa` returns the tightened in-sample level
alpha + z*sqrt(alpha(1-alpha)/S) (one-sided 95%), following the sample-average-approximation practice of solving with
a stricter risk level and validating the solution on an independent sample (Pagnoncelli, Ahmed & Shapiro 2009).
"""
import math
import numpy as np

from .assumptions import P, base_values
from .engine import ALL, projects
from .optimize import all_portfolios

def alpha_saa(alpha, n, conf_z=1.6449):
    """Tightened in-sample reliability level for a chance constraint estimated from n scenarios."""
    return min(1.0, alpha + conf_z * math.sqrt(alpha * (1 - alpha) / n))


EF_KEYS = ("ef_grid", "ef_gas", "ef_diesel", "ef_freight", "ef_steel_incumbent", "ef_steel_alt")


def _draw(rng, p, n):
    d = p.dist
    if d is None:
        return np.full(n, p.value)
    if d[0] == "normal_rel":
        return p.value * np.clip(1 + d[1] * rng.standard_normal(n), 0.05, None)
    if d[0] == "uniform":
        return rng.uniform(d[1], d[2], n)
    if d[0] == "triangular":
        lo, mode, hi = d[1:]
        return rng.triangular(lo, mode, hi, n) if hi > lo else np.full(n, mode)
    if d[0] == "lognormal":
        return p.value * np.exp(d[1] * rng.standard_normal(n) - d[1] ** 2 / 2)
    raise ValueError(d)


def sample(n=20000, seed=20261024, fixed=None):
    """Draw n joint scenarios from the assumption register's distributions (independent inputs).

    Parameters on stream 1 use the v1.0 generator in register order, so their draws are unchanged from v1.0.
    Distributions added in v1.1 (stream 2) and v1.3 (stream 3) use independent generators, so their effect can be isolated
    and the earlier draws of every other input are unchanged."""
    rng = np.random.default_rng(seed)
    rng2 = np.random.default_rng([seed, 2])
    rng3 = np.random.default_rng([seed, 3])
    out = {}
    for k, p in P.items():
        if fixed and k in fixed:
            if p.dist is not None and p.stream == 1:
                _draw(rng, p, n)          # keep the stream-1 sequence aligned for the other parameters
            out[k] = np.full(n, float(fixed[k])); continue
        out[k] = _draw({2: rng2, 3: rng3}.get(p.stream, rng), p, n)
    return out


class Scenarios:
    """Project outcomes for every scenario plus fast portfolio evaluation (matrix form)."""

    def __init__(self, n=20000, seed=20261024, params=None, basis="physical"):
        assert basis in ("physical", "reporting", "baseline"), basis
        self.basis = basis
        self.p = params if params is not None else sample(n, seed)
        self.n = len(next(iter(self.p.values())))
        prj, inter = projects(self.p)
        self.prj, self.inter = prj, inter
        if basis == "reporting":
            base = base_values()
            pe = dict(self.p)
            pe.update({k: np.full(self.n, base[k]) for k in EF_KEYS})
            prj_e, inter_e = projects(pe)
        else:
            prj_e, inter_e = prj, inter
        self.ids = list(ALL)
        self.NPV = np.vstack([np.broadcast_to(prj[i]["npv"], (self.n,)) for i in self.ids])
        self.T12 = np.vstack([np.broadcast_to(prj_e[i]["scope12_t"], (self.n,)) for i in self.ids])
        self.T3 = np.vstack([np.broadcast_to(prj_e[i]["scope3_t"], (self.n,)) for i in self.ids])
        self.CAP = np.vstack([np.broadcast_to(prj[i]["capex"], (self.n,)) for i in self.ids])
        self.ov_npv = np.broadcast_to(inter["BC"]["npv"], (self.n,))
        self.ov_t = np.broadcast_to(inter_e["BC"]["scope12_t"], (self.n,))
        base_prj, _ = projects(base_values())
        self.capex_quote = {i: float(base_prj[i]["capex"]) for i in self.ids}
        self.ports = all_portfolios()
        X = np.array([[1.0 if i in c else 0.0 for i in self.ids] for c in self.ports])
        bc = np.array([1.0 if {"B", "C"} <= set(c) else 0.0 for c in self.ports])
        self.PNPV = X @ self.NPV - np.outer(bc, self.ov_npv)
        self.PT12 = X @ self.T12 - np.outer(bc, self.ov_t)
        self.PT3 = X @ self.T3
        if basis == "baseline":
            # target = share x simulated baseline  <=>  reduction x (reference baseline / simulated baseline) >= target
            p = self.p
            s12 = (p["elec_mwh"] * p["ef_grid"] + p["gas_gj"] * p["ef_gas"]
                   + (p["diesel_forklift_l"] + p["diesel_genset_l"]) * p["ef_diesel"])
            b = base_values()
            ref = b["elec_mwh"] * b["ef_grid"] + b["gas_gj"] * b["ef_gas"] + (b["diesel_forklift_l"] + b["diesel_genset_l"]) * b["ef_diesel"]
            self.baseline_s12 = np.broadcast_to(s12, (self.n,))
            self.PT12 = self.PT12 * (ref / self.baseline_s12)
        self.PCAP = X @ self.CAP                       # actual (uncertain) capital cost per portfolio and scenario
        self.capex = np.array([sum(self.capex_quote[i] for i in c) for c in self.ports])

    def name(self, k):
        return "+".join(self.ports[k]) or "(none)"

    def index(self, ids):
        return self.ports.index(tuple(i for i in self.ids if i in set(ids)))

    def p_within_budget(self, k, budget, mask=None):
        c = self.PCAP[k] if mask is None else self.PCAP[k][mask]
        return float((c <= budget + 1e-6).mean())

    def stats(self, k, target, mask=None, budget=None):
        v = self.PNPV[k] if mask is None else self.PNPV[k][mask]
        t = self.PT12[k] if mask is None else self.PT12[k][mask]
        c = self.PCAP[k] if mask is None else self.PCAP[k][mask]
        q5 = np.percentile(v, 5)
        out = {"portfolio": self.name(k), "capex": self.capex[k], "e_npv": v.mean(), "sd_npv": v.std(), "p5_npv": q5,
               "cvar5_npv": v[v <= q5].mean(), "p_loss": (v < 0).mean(), "e_t12": t.mean(), "p5_t12": np.percentile(t, 5),
               "p_target": (t >= target).mean(), "e_t3": (self.PT3[k] if mask is None else self.PT3[k][mask]).mean(),
               "e_capex": c.mean(), "p90_capex": np.percentile(c, 90), "p95_capex": np.percentile(c, 95)}
        if budget is not None:
            out["p_over_budget"] = float((c > budget + 1e-6).mean())
            out["p_target_and_budget"] = float(((t >= target) & (c <= budget + 1e-6)).mean())
            out["contingency_p90"] = max(0.0, float(np.percentile(c, 90)) - budget)
        return out

    def candidates(self, budget, budget_reliability=None, mask=None):
        cand = [k for k in range(len(self.ports)) if self.capex[k] <= budget + 1e-6]
        if budget_reliability is not None:
            cand = [k for k in cand if self.p_within_budget(k, budget, mask) >= budget_reliability - 1e-12]
        return cand

    def table(self, budget, target):
        return [self.stats(k, target, budget=budget) for k in self.candidates(budget)]

    def decide(self, budget, target, alpha, mask=None, budget_reliability=None):
        """SAA chance-constrained choice on the scenarios in `mask`. Falls back to the highest target probability.

        Returns (k, E[NPV], P(target), feasible). With budget_reliability=b, portfolios must also stay within budget
        in at least a share b of the scenarios; if none qualifies, k is None."""
        m = np.ones(self.n, bool) if mask is None else mask
        cand = self.candidates(budget, budget_reliability, m)
        if not cand:
            return None, None, None, False
        en = {k: self.PNPV[k][m].mean() for k in cand}
        pt = {k: (self.PT12[k][m] >= target).mean() for k in cand}
        ok = [k for k in cand if pt[k] >= alpha - 1e-12]
        k = max(ok, key=lambda k: en[k]) if ok else max(cand, key=lambda k: (pt[k], en[k]))
        return k, en[k], pt[k], bool(ok)

    def best_expected(self, budget, budget_reliability=None):
        cand = self.candidates(budget, budget_reliability)
        return max(cand, key=lambda k: self.PNPV[k].mean()) if cand else None

    def regret(self, budget, target):
        """For each candidate: mean shortfall of NPV vs the best target-meeting portfolio in each scenario."""
        cand = self.candidates(budget)
        V = np.where(self.PT12[cand] >= target, self.PNPV[cand], -np.inf)
        best = V.max(axis=0)
        has = np.isfinite(best)
        out = []
        for j, k in enumerate(cand):
            with np.errstate(invalid="ignore"):
                r = np.where(np.isfinite(V[j]), best - V[j], np.nan)[has]
            out.append({"portfolio": self.name(k), "share_best": float(np.mean(V[j][has] == best[has])),
                        "mean_regret_when_feasible": float(np.nanmean(r)) if np.isfinite(r).any() else None})
        return out
