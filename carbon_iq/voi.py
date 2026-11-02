"""Method 5 - value of information (Howard 1966) under the SAME decision rule as Method 3.

Decision rule R(info): maximise E[NPV | info] subject to budget and P(target | info) >= alpha.
  EVPI  = E_theta[ value of R(theta) ]          - value of R(prior)     (all uncertainty resolved)
  EVPPI = E_X[ value of R(X) ]                  - value of R(prior)     (one input X resolved; 20 quantile bins)
  EVSI  = E_signal[ value of R(signal) ]        - value of R(prior)     (imperfect measurement, explicit error model)
Values are expected NPV of the chosen portfolio evaluated on the scenarios consistent with the information.
Binning estimators carry a small positive bias; a dummy (irrelevant) variable is evaluated to show the noise floor.
"""
import numpy as np

from .assumptions import v


def _value(sc, budget, target, alpha, groups):
    tot, choices = 0.0, []
    for m in groups:
        if not m.any():
            continue
        k, e, _, _ = sc.decide(budget, target, alpha, m)
        tot += m.mean() * e
        choices.append(sc.name(k))
    return tot, choices


def bins(x, nb=20):
    u = np.unique(x)
    if len(u) <= nb:
        return [x == val for val in u]
    q = np.quantile(x, np.linspace(0, 1, nb + 1))
    idx = np.clip(np.digitize(x, q[1:-1]), 0, nb - 1)
    return [idx == b for b in range(nb)]


def prior(sc, budget, target, alpha):
    k, e, pt, ok = sc.decide(budget, target, alpha)
    return k, e


def evpi(sc, budget, target, alpha):
    _, e0 = prior(sc, budget, target, alpha)
    cand = [k for k in range(len(sc.ports)) if sc.capex[k] <= budget + 1e-6]
    V = np.where(sc.PT12[cand] >= target, sc.PNPV[cand], -np.inf)
    best = V.max(axis=0)
    # scenarios where no portfolio can meet the target: choose the largest-reduction portfolio's NPV
    fallback = sc.PNPV[cand][np.argmax(sc.PT12[cand], axis=0), np.arange(sc.n)]
    best = np.where(np.isfinite(best), best, fallback)
    return float(best.mean() - e0)


def evppi(sc, x, budget, target, alpha, nb=20):
    _, e0 = prior(sc, budget, target, alpha)
    val, choices = _value(sc, budget, target, alpha, bins(x, nb))
    return float(val - e0), choices


def evsi_audit(sc, budget, target, alpha, err_sd=None, seed=7, nb=20):
    err_sd = v("audit_error_sd") if err_sd is None else err_sd
    rng = np.random.default_rng(seed)
    signal = sc.p["b_saving_frac"] + rng.normal(0, err_sd, sc.n)
    _, e0 = prior(sc, budget, target, alpha)
    val, choices = _value(sc, budget, target, alpha, bins(signal, nb))
    # switch point: lowest signal bin in which the posterior choice differs from the prior choice
    return float(val - e0), choices, signal


GROUPS = {
    "Motor-system savings (B audit)": ("b_saving_frac", "cost_motor_audit"),
    "Compressed-air savings (C sub-metering)": ("c_saving_frac", "cost_submeter"),
    "Solar yield (A site study)": ("pv_yield", "cost_pv_study"),
    "Steel supplier factors (F supplier data)": ("ef_steel_alt", "cost_supplier_data"),
    "Electricity tariff (policy; not collectable)": ("tariff", None),
    "Grid emission factor (external; not collectable)": ("ef_grid", None),
    "Solar capex (firm quotation; cost not estimated)": ("pv_capex_kw", None),
    "Gas price (policy; not collectable)": ("gas_price_usd", None),
}


def ranking(sc, budget, target, alpha, nb=20, seed=99):
    out = []
    for label, (key, cost_key) in GROUPS.items():
        val, ch = evppi(sc, sc.p[key], budget, target, alpha, nb)
        cost = v(cost_key) if cost_key else None
        out.append({"information": label, "parameter": key, "evppi_sar": val, "collection_cost_sar": cost,
                    "net_value_sar": (val - cost) if cost is not None else None,
                    "decision_changes": len(set(ch)) > 1, "choices": sorted(set(ch))})
    dummy = np.random.default_rng(seed).uniform(0, 1, sc.n)
    noise, _ = evppi(sc, dummy, budget, target, alpha, nb)
    out.sort(key=lambda r: -r["evppi_sar"])
    return out, float(noise)
