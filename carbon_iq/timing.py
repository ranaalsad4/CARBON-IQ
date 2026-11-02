"""Method 4 - investment timing (real options) for the deferrable heat-recovery project D.

Adapted from KAPSARC DP49 (Albalawi & Sirin, 2026): an irreversible investment whose payoff is affine in the
gas price G, valued as an optimal-stopping problem.
  * Maintained process: log-Ornstein-Uhlenbeck on G (Schwartz 1997), d lnG = kappa (alpha - lnG) dt + sigma dZ,
    alpha = ln(G_bar) - sigma^2 / (4 kappa)  (so the long-run mean of G is G_bar); exact monthly discretisation.
    Solved with Longstaff-Schwartz least-squares Monte Carlo (basis 1, G, G^2) over the deferral window.
  * Closed-form benchmark: GBM on G with drift mu, Dixit-Pindyck trigger
        G* = lambda/(lambda-1) * (capex + O&M * C) / (A * q),   A = (1-e^{-(r-mu)T})/(r-mu), C = (1-e^{-rT})/r,
        lambda = [-(mu - s^2/2) + sqrt((mu - s^2/2)^2 + 2 r s^2)] / s^2        (KAPSARC DP49 Eq. C.7, C.13)
ADAPTATION CAVEATS: DP49 models the market-equivalent opportunity cost of gas for offshore power; here the same
calibration (kappa 0.5, sigma 0.522) is borrowed, with G_bar = the current regulated price (v1.3: $2.15/MMBtu;
DP49 used $3), as a proxy for uncertainty in the future
industrial gas price a Saudi manufacturer pays. Administered prices move in policy steps, so results are an
illustration of the method, not a forecast. The electricity tariff is NOT modelled as a stochastic process for
the same reason; tariff changes are treated as scenarios (Methods 3 and 6).
"""
import math

import numpy as np

from .assumptions import GJ_PER_MMBTU, SAR_PER_USD, v

USD_MMBTU_TO_SAR_GJ = SAR_PER_USD / GJ_PER_MMBTU


def project_d():
    q_gj = v("gas_gj") * v("d_saving_frac")
    return dict(capex=v("d_capex"), om=v("d_om"), life=int(v("d_life")), q_gj=q_gj)


def exercise_value(G, d=None, r=None, kappa=None, sigma=None, gbar=None):
    """NPV (SAR) of investing now when today's gas price is G (USD/MMBtu), using log-OU expected prices,
    annual end-of-year cash flows discounted at (1+r)^-k (same convention as the financial engine)."""
    d = d or project_d()
    r = v("discount_rate") if r is None else r
    kappa = v("ro_kappa") if kappa is None else kappa
    sigma = v("ro_sigma") if sigma is None else sigma
    gbar = v("gas_price_usd") if gbar is None else gbar        # v1.3: long-run level = current regulated price
    alpha = math.log(gbar) - sigma ** 2 / (4 * kappa)
    G = np.asarray(G, dtype=float)
    x = np.log(G)
    total = np.zeros_like(G) - d["capex"]
    for k in range(1, d["life"] + 1):
        mean = alpha + (x - alpha) * math.exp(-kappa * k)
        var = sigma ** 2 / (2 * kappa) * (1 - math.exp(-2 * kappa * k))
        eg = np.exp(mean + var / 2)
        total = total + (d["q_gj"] * USD_MMBTU_TO_SAR_GJ * eg - d["om"]) / (1 + r) ** k
    return total


def static_npv(G, d=None, r=None):
    """Traditional NPV with the gas price held constant at G for the project life."""
    d = d or project_d()
    r = v("discount_rate") if r is None else r
    af = (1 - (1 + r) ** -d["life"]) / r
    return -d["capex"] + (d["q_gj"] * USD_MMBTU_TO_SAR_GJ * G - d["om"]) * af


def static_breakeven_usd(d=None, r=None):
    d = d or project_d()
    r = v("discount_rate") if r is None else r
    af = (1 - (1 + r) ** -d["life"]) / r
    return (d["capex"] / af + d["om"]) / (d["q_gj"] * USD_MMBTU_TO_SAR_GJ)


def simulate_logou(n, years, g0=None, gbar=None, kappa=None, sigma=None, steps_per_year=12, seed=2026):
    kappa = v("ro_kappa") if kappa is None else kappa
    sigma = v("ro_sigma") if sigma is None else sigma
    g0 = v("gas_price_usd") if g0 is None else g0
    gbar = v("gas_price_usd") if gbar is None else gbar
    rng = np.random.default_rng(seed)
    dt = 1 / steps_per_year
    m = int(round(years * steps_per_year))
    alpha = math.log(gbar) - sigma ** 2 / (4 * kappa)
    a = math.exp(-kappa * dt)
    s = sigma * math.sqrt((1 - math.exp(-2 * kappa * dt)) / (2 * kappa))
    x = np.empty((n, m + 1))
    x[:, 0] = math.log(g0)
    z = rng.standard_normal((n, m))
    for t in range(m):
        x[:, t + 1] = alpha + (x[:, t] - alpha) * a + s * z[:, t]
    return np.exp(x), dt


def _fit_policy(G, ev, disc):
    """Backward induction on fitting paths: regression coefficients of continuation value per time step."""
    m = G.shape[1] - 1
    cash = np.where(ev[:, m] > 0, ev[:, m], 0.0)
    betas = {}
    for t in range(m - 1, 0, -1):
        cash = cash * disc
        itm = ev[:, t] > 0
        if itm.sum() > 30:
            X = np.column_stack([np.ones(itm.sum()), G[itm, t], G[itm, t] ** 2])
            beta, *_ = np.linalg.lstsq(X, cash[itm], rcond=None)
            betas[t] = beta
            ex = ev[itm, t] > X @ beta
            idx = np.where(itm)[0][ex]
            cash[idx] = ev[idx, t]
    return betas


def _apply_policy(G, ev, disc, betas):
    """Forward valuation on INDEPENDENT paths (removes LSMC in-sample foresight bias)."""
    n, m1 = G.shape
    m = m1 - 1
    value = np.zeros(n)
    tau = np.full(n, -1)
    alive = np.ones(n, bool)
    for t in range(1, m + 1):
        if t == m:
            ex = alive & (ev[:, t] > 0)
        elif t in betas:
            cont = betas[t][0] + betas[t][1] * G[:, t] + betas[t][2] * G[:, t] ** 2
            ex = alive & (ev[:, t] > 0) & (ev[:, t] > cont)
        else:
            continue
        value[ex] = ev[ex, t] * disc ** t
        tau[ex] = t
        alive &= ~ex
    return value, tau


def _lsmc_run(n, years, g0, gbar, kappa, sigma, seed):
    r = v("discount_rate")
    Gf, dt = simulate_logou(n, years, g0=g0, gbar=gbar, kappa=kappa, sigma=sigma, seed=seed)
    Ge, _ = simulate_logou(n, years, g0=g0, gbar=gbar, kappa=kappa, sigma=sigma, seed=seed + 1)
    disc = (1 + r) ** (-dt)
    evf = np.vstack([exercise_value(Gf[:, t], kappa=kappa, sigma=sigma, gbar=gbar) for t in range(Gf.shape[1])]).T
    eve = np.vstack([exercise_value(Ge[:, t], kappa=kappa, sigma=sigma, gbar=gbar) for t in range(Ge.shape[1])]).T
    betas = _fit_policy(Gf, evf, disc)
    value, tau = _apply_policy(Ge, eve, disc, betas)
    now = float(exercise_value(np.array([g0]), kappa=kappa, sigma=sigma, gbar=gbar)[0])
    return now, value, tau, Ge, dt


def lsmc(n=None, years=None, g0=None, gbar=None, kappa=None, sigma=None, seed=2026):
    """Option to invest in D within `years` (monthly decisions); policy fitted and valued on separate path sets."""
    n = int(v("ro_paths")) if n is None else int(n)
    years = v("ro_horizon") if years is None else years
    kappa = v("ro_kappa") if kappa is None else kappa
    sigma = v("ro_sigma") if sigma is None else sigma
    g0 = v("gas_price_usd") if g0 is None else g0
    gbar = v("gas_price_usd") if gbar is None else gbar
    now, value, tau, G, dt = _lsmc_run(n, years, g0, gbar, kappa, sigma, seed)
    wait = float(value.mean())
    se = float(value.std() / np.sqrt(n))
    t_y = np.where(tau >= 0, tau * dt, np.nan)
    exercised_g = G[np.arange(n)[tau >= 0], tau[tau >= 0]] if (tau >= 0).any() else np.array([])
    return {"g0": g0, "gbar": gbar, "value_now_invest": now, "value_wait": wait, "value_wait_se": se,
            "value_with_flexibility": max(now, wait), "option_premium": max(now, wait) - now, "invest_now": now >= wait,
            "p_invest_1y": float(np.mean(np.nan_to_num(t_y, nan=1e9) <= 1)),
            "p_invest_5y": float(np.mean(np.nan_to_num(t_y, nan=1e9) <= 5)),
            "p_invest_horizon": float(np.mean(tau >= 0)),
            "median_wait_y_if_invest": float(np.nanmedian(t_y)) if np.isfinite(t_y).any() else None,
            "median_exercised_gas_usd": float(np.median(exercised_g)) if len(exercised_g) else None,
            "paths": n, "horizon_y": years, "kappa": kappa, "sigma": sigma}


def gbm_trigger(mu=None, sigma=None, d=None, r_cont=None):
    """Closed-form Dixit-Pindyck trigger (USD/MMBtu) under GBM on G (KAPSARC DP49 Eq. C.7/C.13), continuous discounting."""
    d = d or project_d()
    mu = v("ro_mu_gbm") if mu is None else mu
    sigma = v("ro_sigma") if sigma is None else sigma
    r = math.log(1 + v("discount_rate")) if r_cont is None else r_cont
    T = d["life"]
    A = (1 - math.exp(-(r - mu) * T)) / (r - mu)
    C = (1 - math.exp(-r * T)) / r
    b = mu - sigma ** 2 / 2
    lam = (-b + math.sqrt(b ** 2 + 2 * r * sigma ** 2)) / sigma ** 2
    unit = d["q_gj"] * USD_MMBTU_TO_SAR_GJ
    be = (d["capex"] + d["om"] * C) / (A * unit)
    return {"lambda": lam, "multiplier": lam / (lam - 1), "breakeven_usd": be, "trigger_usd": lam / (lam - 1) * be,
            "mu": mu, "sigma": sigma, "r_continuous": r}


def sensitivity(kappas=(0.2, 0.5, 1.0), sigmas=(0.3, 0.522, 0.75), n=3000):
    out = []
    for k in kappas:
        for s in sigmas:
            res = lsmc(n=n, kappa=k, sigma=s)
            out.append({"kappa": k, "sigma": s, "option_premium": res["option_premium"], "invest_now": res["invest_now"],
                        "p_invest_5y": res["p_invest_5y"]})
    return out


def lsmc_level(gbar, n=4000, years=None, kappa=None, sigma=None, seed=2026):
    """Today's price equals the long-run level gbar (e.g. after a price reform): invest now or keep waiting?"""
    r = lsmc(n=n, years=years, g0=gbar, gbar=gbar, kappa=kappa, sigma=sigma, seed=seed)
    return {"gbar": gbar, "value_invest_now": r["value_now_invest"], "value_wait": r["value_wait"],
            "invest_now": r["invest_now"], "option_premium": r["option_premium"]}


def trigger_scan(levels=None, n=4000, kappa=None, sigma=None):
    """Smallest long-run gas-price level at which investing now dominates waiting (option-adjusted trigger)."""
    start = min(3.0, round(v("gas_price_usd"), 1))      # v1.3: scan starts at the current price (v1.2: 3.0)
    levels = levels if levels is not None else np.round(np.arange(start, 6.01, 0.1), 2)
    rows = [lsmc_level(float(g), n=n, kappa=kappa, sigma=sigma) for g in levels]
    trig = next((r["gbar"] for r in rows if r["invest_now"]), None)
    return {"rows": rows, "trigger_usd": trig, "static_breakeven_usd": static_breakeven_usd()}


def decision_tree(p_reform=None, g_reform=None, g_now=None, d=None, r=None):
    """Prototype timing method for an ADMINISTERED price: a one-period reform tree.
    Invest now: year-1 savings at today's price, years 2..L at the expected post-decision price.
    Wait one year: invest only in the states where the full-life NPV is positive."""
    p_reform = v("tree_p_reform") if p_reform is None else p_reform
    g_reform = v("tree_g_reform") if g_reform is None else g_reform
    g_now = v("gas_price_usd") if g_now is None else g_now
    d = d or project_d()
    r = v("discount_rate") if r is None else r
    unit = d["q_gj"] * USD_MMBTU_TO_SAR_GJ
    L = d["life"]
    eg = p_reform * g_reform + (1 - p_reform) * g_now
    now = -d["capex"] + (unit * g_now - d["om"]) / (1 + r) + sum((unit * eg - d["om"]) / (1 + r) ** k for k in range(2, L + 1))
    npv_hi, npv_lo = static_npv(g_reform, d, r), static_npv(g_now, d, r)
    wait = (p_reform * max(npv_hi, 0.0) + (1 - p_reform) * max(npv_lo, 0.0)) / (1 + r)
    return {"p_reform": p_reform, "g_reform_usd": g_reform, "g_now_usd": g_now, "npv_invest_now": now,
            "npv_if_reform_at_t1": npv_hi, "npv_if_no_reform_at_t1": npv_lo, "value_wait_one_year": wait,
            "option_premium": max(now, wait) - now, "decision": "invest now" if now >= wait else "wait for the price decision",
            "static_breakeven_usd": static_breakeven_usd(d, r), "deferred_t_year1": d["q_gj"] * v("ef_gas")}
