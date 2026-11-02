"""Estimation of missing monthly values, refusal rules, uncertainty and the lineage ledger.

Methods (all transparent; parameters and errors are recorded):
  intensity         value = (sum of measured values / sum of measured production) x production of the month.
                    Appropriate when the stream scales with output (electricity, gas, purchased steel, freight) AND
                    production is measured in the missing month.
  seasonal_history  value = same month of the previous year x (this year / last year, over months measured in both).
                    Appropriate for seasonal streams (cooling-driven electricity, generators) with a stable year-on-year
                    pattern and at least 6 overlapping months.
  mean              value = mean of the measured months of the year. Appropriate for flat streams (forklift diesel,
                    operating hours) only.
Uncertainty: leave-one-out (LOO) prediction error of the chosen method on the same stream's measured months, i.e.
the stream's own back-test: sd = RMSE_LOO x sqrt(1 + 1/n) x t(0.975, n-1)/1.96 x CAL_MONTHLY. The method with the lowest
LOO error among the eligible ones is chosen. Annual totals combine the monthly sds with a common within-stream error
correlation RHO_ANNUAL. CAL_MONTHLY (split-conformal) and RHO_ANNUAL are fitted on SYNTHETIC calibration facilities
(tools/calibrate_a4.py) and evaluated on held-out synthetic sets; they must be re-fitted on real data. calibrate=False
reproduces the first A4 release (factor 1, linear annual sum).
Operational change (A4 refinement): the quantity each method assumes constant (log intensity, log year-on-year ratio,
log level) is tested for a single mean shift with a permutation test. After a material change (p < CP_ALPHA, shift >=
CP_MIN_SHIFT) all methods are trained on months of the gap's regime only; estimation is refused (OPERATIONAL_CHANGE)
with fewer than MIN_REGIME such months or when the gap sits at the change point. A reviewer can override a refusal
('override_change'); the label records it. Months whose production deviates by more than PROD_ANOMALY from the median
month are estimated by production intensity only, when available.
Estimation is refused (the gap stays open and the decision run is blocked) when:
  * fewer than MIN_MEASURED months of the stream are usable                       TOO_FEW_MEASURED
  * the month is part of a run of more than MAX_GAP_RUN consecutive missing months  GAP_TOO_LONG
  * no method is eligible (e.g. production missing for an intensity estimate)      NO_ELIGIBLE_METHOD
  * the best method's LOO error exceeds MAX_REL_ERR of the mean monthly value     ESTIMATE_UNRELIABLE
  * an operational change leaves too few same-regime months, or the gap is at it    OPERATIONAL_CHANGE
Outliers and suspected zeros are never replaced automatically: an estimate is proposed and a user must decide.
"""
import datetime as dt
import hashlib
import json

import numpy as np
from scipy.stats import t as T_DIST
import pandas as pd

from .quality import STREAMS, assess

MIN_MEASURED = 6
MAX_GAP_RUN = 3
MAX_REL_ERR = 0.25
# operational-change detection (A4 refinement): single mean shift in the series each method assumes constant
CP_ALPHA = 0.01             # permutation p-value threshold (false-alarm control)
CP_MIN_SHIFT = 0.10         # ignore shifts smaller than 10% (not material for annual totals)
CP_MIN_SEGMENT = 3          # at least 3 measured months before a split ...
CP_MIN_SEGMENT_END = 2      # ... and 2 after it (recent changes matter most; the permutation test still controls false alarms)
CP_PERMUTATIONS = 499
MIN_REGIME = 4              # minimum measured months in the current regime to estimate after a change
PROD_ANOMALY = 0.30         # month's production more than 30% from the median month
# calibration (A4 refinement): split-conformal factor on monthly sds and within-stream error correlation for annual
# totals, both estimated on SYNTHETIC calibration facilities (seed 5501) and checked on held-out sets - see validate.py.
CAL_MONTHLY = 1.0898        # tools/calibrate_a4.py: conformal |z| quantile / 1.96 on 5,658 synthetic gaps (100 facilities)
RHO_ANNUAL = 0.12           # tools/calibrate_a4.py: smallest rho with 95% annual coverage on 1,465 stream-years
                            # (directly estimated pooled error correlation on the same set: 0.129)
SETTINGS = dict(detect_changes=True, calibrate=True)
GAP_STATUSES = ("missing", "suspected_zero", "outlier")
USABLE = ("measured", "converted")
METHODS = {
    "production": ["seasonal_history", "mean"],
    "operating_hours": ["mean", "seasonal_history"],
    "electricity": ["seasonal_history", "intensity", "mean"],
    "natural_gas": ["intensity", "seasonal_history", "mean"],
    "diesel_forklift": ["mean", "intensity", "seasonal_history"],
    "diesel_genset": ["seasonal_history"],
    "steel_purchased": ["intensity"],
    "freight": ["intensity"],
}
METHOD_TEXT = {
    "intensity": "production-intensity: (measured stream / measured production) x production of the month",
    "seasonal_history": "seasonal history: same month last year x year-on-year ratio over months measured in both years",
    "mean": "mean of measured months of the year",
}


def _series(cells, stream):
    g = cells[cells.stream == stream].set_index("period").sort_index()
    usable = g.status.isin(USABLE)
    return g, usable


def _fit_predict(method, stream, month, cur, cur_ok, prod, prod_ok, hist, hist_ok, exclude=None, allowed=None, min_train=None):
    """Return the prediction for `month` (or None if ineligible), using training months that exclude `exclude` and,
    after an operational change, only months of the same regime (`allowed`)."""
    need = (MIN_MEASURED if min_train is None else min_train) - (1 if exclude else 0)
    train = [m for m in sorted(cur) if cur_ok[m] and m != month and m != exclude and (allowed is None or m in allowed)]
    if method == "intensity":
        if not (prod_ok.get(month, False) and prod.get(month, 0) > 0):
            return None
        tr = [m for m in train if prod_ok.get(m, False) and prod[m] > 0]
        if len(tr) < need:
            return None
        return float(sum(cur[m] for m in tr) / sum(prod[m] for m in tr) * prod[month])
    if method == "seasonal_history":
        hm = _prev(month)
        if hist is None or not hist_ok.get(hm, False):
            return None
        ov = [m for m in train if hist_ok.get(_prev(m), False)]
        if len(ov) < need:
            return None
        den = sum(hist[_prev(m)] for m in ov)
        if den <= 0:
            return None
        return float(hist[hm] * sum(cur[m] for m in ov) / den)
    if method == "mean":
        if len(train) < need:
            return None
        return float(np.mean([cur[m] for m in train]))
    raise ValueError(method)


def _prev(period):
    y, m = period.split("-")
    return f"{int(y) - 1}-{m}"


def _loo(method, stream, cur, cur_ok, prod, prod_ok, hist, hist_ok, allowed=None, min_train=None):
    """Leave-one-out back-test on measured months (of the same regime). Returns (rmse_abs, n, mean_level) or None."""
    need = MIN_MEASURED if min_train is None else min_train
    errs, acts = [], []
    for m in sorted(cur):
        if not cur_ok[m] or (allowed is not None and m not in allowed):
            continue
        p = _fit_predict(method, stream, m, cur, cur_ok, prod, prod_ok, hist, hist_ok, exclude=m, allowed=allowed, min_train=min_train)
        if p is None:
            continue
        errs.append(p - cur[m]); acts.append(cur[m])
    if len(errs) < need - 1:
        return None
    return float(np.sqrt(np.mean(np.square(errs)))), len(errs), float(np.mean(acts))


def _runs(flags):
    """Lengths of consecutive True runs, mapped back to each position."""
    out, i = [0] * len(flags), 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j < len(flags) and flags[j]:
                j += 1
            for k in range(i, j):
                out[k] = j - i
            i = j
        else:
            i += 1
    return out


# ------------------------------------------------------------------ operational-change detection
def _assumption_series(method, cur, cur_ok, prod, prod_ok, hist, hist_ok, hprod=None, hprod_ok=None):
    """The quantity each method assumes constant, on measured months: log intensity and log level over the history and
    current years (24 months when available), log year-on-year ratio over the current year."""
    out = {}
    pairs = [(cur, cur_ok, prod, prod_ok)]
    if method in ("intensity", "mean") and hist is not None:
        pairs.insert(0, (hist, hist_ok, hprod or {}, hprod_ok or {}))
    for vals, okd, pv, pok in pairs:
        for m in sorted(vals):
            if not okd.get(m, False) or vals[m] <= 0:
                continue
            if method == "intensity":
                if pok.get(m, False) and pv[m] > 0:
                    out[m] = np.log(vals[m] / pv[m])
            elif method == "seasonal_history":
                if hist is not None and hist_ok.get(_prev(m), False) and hist[_prev(m)] > 0:
                    out[m] = np.log(vals[m] / hist[_prev(m)])
            else:
                out[m] = np.log(vals[m])
    return out


def _shift_stats(X, min_seg, min_end=None):
    """Rows of X are series; returns (max |Welch t| over splits, argmax split) per row (vectorised)."""
    X = np.atleast_2d(np.asarray(X, float))
    n = X.shape[1]
    min_end = min_seg if min_end is None else min_end
    best = np.zeros(X.shape[0]); at = np.full(X.shape[0], -1)
    for s in range(min_seg, n - min_end + 1):
        a, b = X[:, :s], X[:, s:]
        se = np.sqrt(a.var(axis=1, ddof=1) / s + b.var(axis=1, ddof=1) / (n - s))
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(se > 0, np.abs(b.mean(axis=1) - a.mean(axis=1)) / se, 0.0)
        upd = t > best
        best = np.where(upd, t, best); at = np.where(upd, s, at)
    return best, at


def detect_change(series, key="", n_perm=None):
    """Single mean-shift test on a time-ordered series {period: value}: max |Welch t| over split points, with a
    permutation p-value (exchangeable under 'no change'). Returns None when no material change is found, else
    dict(split=first period of the new regime, shift, p, t)."""
    n_perm = CP_PERMUTATIONS if n_perm is None else n_perm
    months = sorted(series)
    x = np.array([series[m] for m in months])
    if len(x) < CP_MIN_SEGMENT + CP_MIN_SEGMENT_END + 1:
        return None
    t0, s = _shift_stats(x, CP_MIN_SEGMENT, CP_MIN_SEGMENT_END)
    t0, s = float(t0[0]), int(s[0])
    if s < 0:
        return None
    shift = float(np.exp(x[s:].mean() - x[:s].mean()) - 1)
    if abs(shift) < CP_MIN_SHIFT:
        return None
    rng = np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:8], 16))
    perms = np.array([rng.permutation(x) for _ in range(n_perm)])
    tp, _ = _shift_stats(perms, CP_MIN_SEGMENT, CP_MIN_SEGMENT_END)
    p = float((np.sum(tp >= t0 - 1e-12) + 1) / (n_perm + 1))
    if p >= CP_ALPHA:
        return None
    return dict(split=months[s], shift=shift, p=p, t=t0)


def propose(cells, hist_cells=None, detect_changes=None, calibrate=None):
    """Add proposal columns to a copy of `cells` (one proposal per gap, outlier or suspected zero).
    detect_changes / calibrate default to the module SETTINGS; both False reproduces the first A4 release."""
    detect_changes = SETTINGS["detect_changes"] if detect_changes is None else detect_changes
    cal = (CAL_MONTHLY if (SETTINGS["calibrate"] if calibrate is None else calibrate) else 1.0)
    led = cells.copy()
    for col, default in (("method", ""), ("estimate", np.nan), ("sd", np.nan), ("low95", np.nan), ("high95", np.nan),
                         ("candidates", ""), ("refusal", ""), ("warning", ""), ("fallback_method", ""), ("fallback_estimate", np.nan),
                         ("fallback_sd", np.nan), ("decision", ""), ("decided_by", ""),
                         ("decided_at", ""), ("decision_note", "")):
        led[col] = default
    for site in led.site.unique():
        sc = led[led.site == site]
        pg, pok = _series(sc, "production")
        prod = pg["value"].to_dict(); prod_ok = pok.to_dict()
        prod_med = float(np.median([prod[m] for m in prod if prod_ok[m] and prod[m] > 0])) if any(prod_ok.values()) else np.nan
        for stream in STREAMS:
            g, ok = _series(sc, stream)
            cur, cur_ok = g["value"].to_dict(), ok.to_dict()
            hist = hist_ok = None
            if hist_cells is not None:
                hg, hok = _series(hist_cells[hist_cells.site == site], stream)
                hist, hist_ok = hg["value"].to_dict(), hok.to_dict()
            gaps = [m for m in g.index if g.at[m, "status"] in GAP_STATUSES]
            if not gaps:
                continue
            missing_flags = [g.at[m, "status"] in ("missing", "suspected_zero") for m in g.index]
            run = dict(zip(g.index, _runs(missing_flags)))
            n_ok = int(ok.sum())
            # operational change: test the series each method assumes constant; the most significant shift defines the
            # stream's regimes (a change in energy use breaks every method's assumption, not only the one that detects it)
            change, found = None, []
            if detect_changes and STREAMS[stream]["kind"] != "intermittent":
                hp = hpok = None
                if hist_cells is not None:
                    hpg, hpk = _series(hist_cells[hist_cells.site == site], "production")
                    hp, hpok = hpg["value"].to_dict(), hpk.to_dict()
                # flagged outliers are included here: a run of 'outliers' in one direction is evidence of a change
                cp_ok = {m: bool(cur_ok[m] or (g.at[m, "status"] == "outlier" and cur[m] == cur[m])) for m in cur}
                for meth in METHODS[stream]:
                    ser = _assumption_series(meth, cur, cp_ok, prod, prod_ok, hist, hist_ok, hp, hpok)
                    d = detect_change(ser, key=f"{site}|{stream}|{meth}")
                    if d:
                        found.append((d["p"], -d["t"], meth, d))
                if found:
                    change = dict(sorted(found)[0][3], method=sorted(found)[0][2])
                    if change["split"] <= min(cur):            # level change between years only: no effect on training
                        between = change; change = None
            loo_all = {meth: _loo(meth, stream, cur, cur_ok, prod, prod_ok, hist, hist_ok) for meth in METHODS[stream]}
            for m in gaps:
                idx = led[(led.site == site) & (led.stream == stream) & (led.period == m)].index[0]
                led.at[idx, "decision"] = "pending"
                if n_ok < MIN_MEASURED:
                    led.at[idx, "refusal"] = f"TOO_FEW_MEASURED: {n_ok} usable months (< {MIN_MEASURED})"; continue
                if run[m] > MAX_GAP_RUN:
                    led.at[idx, "refusal"] = f"GAP_TOO_LONG: run of {run[m]} consecutive missing months (> {MAX_GAP_RUN})"; continue
                warn, cands, blocked = [], {}, []
                # production anomaly: methods that ignore the month's production are unreliable when output moved sharply
                anomaly = (stream not in ("production", "operating_hours", "diesel_genset") and prod_ok.get(m, False)
                           and prod_med > 0 and abs(prod[m] / prod_med - 1) > PROD_ANOMALY)
                if detect_changes and anomaly:
                    warn.append(f"PRODUCTION_ANOMALY: output {prod[m] / prod_med - 1:+.0%} vs median month; "
                                "methods that ignore production excluded")
                if found and change is None:
                    warn.append(f"LEVEL_CHANGE_BETWEEN_YEARS: {between['method']} assumption shifts {between['shift']:+.0%} "
                                f"from {between['split']} (p={between['p']:.3f}); current-year data only are used")
                allowed, mt = None, None
                ambiguous = bool(change) and m < change["split"] and all(
                    not cp_ok[x] for x in sorted(cur) if m <= x < change["split"])
                if ambiguous:
                    # the gap sits at the change itself: it may belong to either regime, so no method is trusted
                    warn.append(f"OPERATIONAL_CHANGE: {change['method']} assumption shifts {change['shift']:+.0%} at "
                                f"{change['split']} (p={change['p']:.3f}) and this gap is at the change point")
                    blocked = list(METHODS[stream])
                if change and not ambiguous:
                    after = m >= change["split"]
                    allowed = {x for x in cur if (x >= change["split"]) == after}
                    mt = MIN_REGIME
                    warn.append(f"OPERATIONAL_CHANGE: {change['method']} assumption shifts {change['shift']:+.0%} from "
                                f"{change['split']} (permutation p={change['p']:.3f}); all methods trained on the "
                                f"{'new' if after else 'old'} regime only")
                for meth in ([] if ambiguous else METHODS[stream]):
                    if detect_changes and anomaly and meth != "intensity" and "intensity" in METHODS[stream]:
                        blocked.append(meth); continue
                    loo = (_loo(meth, stream, cur, cur_ok, prod, prod_ok, hist, hist_ok, allowed=allowed, min_train=mt)
                           if change else loo_all[meth])
                    p = _fit_predict(meth, stream, m, cur, cur_ok, prod, prod_ok, hist, hist_ok, allowed=allowed, min_train=mt)
                    if p is None or loo is None:
                        if change:
                            blocked.append(meth)
                        continue
                    rmse, nn, level = loo
                    cands[meth] = dict(estimate=p, rmse=rmse, n=nn, rel=rmse / level if level else np.inf, regime_only=bool(change))
                led.at[idx, "candidates"] = json.dumps({k: {kk: (round(vv, 6) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                                                        for k, v in cands.items()})
                led.at[idx, "warning"] = " | ".join(dict.fromkeys(warn))
                if not cands:
                    if blocked and detect_changes:
                        led.at[idx, "refusal"] = ("OPERATIONAL_CHANGE: gap at the change point; regime unknown" if ambiguous else
                                                  "OPERATIONAL_CHANGE: too few months in the current operating regime "
                                                  f"(< {MIN_REGIME}) for " + ", ".join(blocked))
                        # fallback ignoring the detected change, available only through an explicit reviewer override
                        fb = {}
                        for meth in METHODS[stream]:
                            pp = _fit_predict(meth, stream, m, cur, cur_ok, prod, prod_ok, hist, hist_ok)
                            if pp is not None and loo_all[meth] is not None:
                                r_, n_, lv_ = loo_all[meth]
                                fb[meth] = (r_ / lv_ if lv_ else np.inf, pp, r_, n_)
                        if fb:
                            bm = min(fb, key=lambda k: (fb[k][0], METHODS[stream].index(k)))
                            _, pp, r_, n_ = fb[bm]
                            led.at[idx, "fallback_method"] = bm
                            led.at[idx, "fallback_estimate"] = pp
                            led.at[idx, "fallback_sd"] = r_ * np.sqrt(1 + 1 / n_) * T_DIST.ppf(0.975, max(n_ - 1, 1)) / 1.96 * cal
                    else:
                        led.at[idx, "refusal"] = "NO_ELIGIBLE_METHOD: data required by every method are missing"
                    continue
                best = min(cands, key=lambda k: (cands[k]["rel"], METHODS[stream].index(k)))
                c = cands[best]
                if c["rel"] > MAX_REL_ERR:
                    led.at[idx, "refusal"] = f"ESTIMATE_UNRELIABLE: best LOO error {c['rel']:.0%} of monthly mean (> {MAX_REL_ERR:.0%})"
                    continue
                # prediction sd: back-test RMSE x sqrt(1 + 1/n), widened by t(0.975, n-1)/1.96 because the RMSE is itself
                # estimated from few months, then multiplied by the empirical calibration factor (see CAL_MONTHLY)
                sd = c["rmse"] * np.sqrt(1 + 1 / c["n"]) * T_DIST.ppf(0.975, max(c["n"] - 1, 1)) / 1.96 * cal
                led.at[idx, "method"] = best
                led.at[idx, "estimate"] = c["estimate"]
                led.at[idx, "sd"] = sd
                led.at[idx, "low95"] = max(0.0, c["estimate"] - 1.96 * sd)
                led.at[idx, "high95"] = c["estimate"] + 1.96 * sd
    return led


def annual_sd(sds, rho=None):
    """sd of a sum of monthly estimate errors with common pairwise correlation rho (1 = linear sum, 0 = root-sum-square)."""
    rho = (RHO_ANNUAL if SETTINGS["calibrate"] else 1.0) if rho is None else rho
    sds = np.asarray(sds, float)
    if not len(sds):
        return 0.0
    s1, s2 = sds.sum(), np.square(sds).sum()
    return float(np.sqrt(max(s2 + rho * (s1 * s1 - s2), 0.0)))


class Ledger:
    """Raw data (immutable copy + hash), assessed cells, proposals, decisions and an append-only event log."""

    def __init__(self, raw, year, site=None, source_name="uploaded data", detect_changes=None, calibrate=None):
        self.raw = raw.copy(deep=True)
        self.raw_hash = hashlib.sha256(self.raw.to_csv(index=False).encode()).hexdigest()
        self.year, self.source_name = year, source_name
        self.cells, self.issues = assess(self.raw, year, site)
        hist = assess(self.raw, year - 1, site)[0] if (self.raw["period"].astype(str).str.startswith(str(year - 1))).any() else None
        self.hist_cells = hist
        self.calibrate = SETTINGS["calibrate"] if calibrate is None else calibrate
        self.table = propose(self.cells, hist, detect_changes=detect_changes, calibrate=self.calibrate)
        self.events = [dict(time=_now(), action="load", by="system", detail=f"{len(self.raw)} records from {source_name}; sha256 {self.raw_hash[:12]}")]

    # ---- decisions
    def _idx(self, site, period, stream):
        m = self.table[(self.table.site == site) & (self.table.period == period) & (self.table.stream == stream)]
        if len(m) != 1:
            raise KeyError((site, period, stream))
        return m.index[0]

    def decide(self, site, period, stream, decision, by, note=""):
        """decision: 'approve' (use the proposed estimate), 'reject' (leave the gap open), 'keep' (keep an outlier as
        measured), 'confirm_zero' (a suspected zero is a true zero), 'override_change' (reviewer states that a detected
        operational change is not real; the estimate that ignores it is used and labelled)."""
        i = self._idx(site, period, stream)
        row = self.table.loc[i]
        if row["decision"] == "":
            raise ValueError("no decision needed for this cell")
        allowed = {"approve", "reject"}
        if row["status"] == "outlier":
            allowed |= {"keep"}
        if row["status"] == "suspected_zero":
            allowed |= {"confirm_zero"}
        if str(row["refusal"]).startswith("OPERATIONAL_CHANGE") and not np.isnan(row["fallback_estimate"]):
            allowed |= {"override_change"}
        if decision not in allowed:
            raise ValueError(f"{decision} not allowed for status {row['status']}")
        if decision == "approve" and (row["refusal"] or np.isnan(row["estimate"])):
            raise ValueError(f"no estimate to approve: {row['refusal']}")
        self.table.at[i, "decision"] = {"approve": "approved", "reject": "rejected", "keep": "kept", "confirm_zero": "confirmed_zero",
                                        "override_change": "change_overridden"}[decision]
        self.table.at[i, "decided_by"], self.table.at[i, "decided_at"], self.table.at[i, "decision_note"] = by, _now(), note
        self.events.append(dict(time=_now(), action=decision, by=by, detail=f"{site} {period} {stream}: {note}"))

    def approve_all(self, by, include_outliers=False):
        for i, r in self.table[self.table.decision == "pending"].iterrows():
            if r["refusal"]:
                continue
            if r["status"] == "outlier" and not include_outliers:
                continue
            self.decide(r.site, r.period, r.stream, "approve", by, "bulk approval")

    # ---- results
    def final(self):
        """Per-cell final value and label (original value columns untouched)."""
        t = self.table.copy()
        val, lab, sd = [], [], []
        for _, r in t.iterrows():
            if r.status in ("measured", "converted"):
                val.append(r.value); lab.append(r.status); sd.append(0.0)
            elif r.decision == "approved":
                val.append(r.estimate); lab.append(f"estimated ({r.method})"); sd.append(r.sd)
            elif r.decision == "change_overridden":
                val.append(r.fallback_estimate); lab.append(f"estimated ({r.fallback_method}; change override)"); sd.append(r.fallback_sd)
            elif r.decision == "kept":
                val.append(r.value); lab.append("outlier kept (user)"); sd.append(0.0)
            elif r.decision == "confirmed_zero":
                val.append(0.0); lab.append("zero confirmed (user)"); sd.append(0.0)
            else:
                val.append(np.nan); lab.append("UNRESOLVED (" + (r.refusal.split(":")[0] if r.refusal else r.decision or r.status) + ")"); sd.append(np.nan)
        t["final_value"], t["final_label"], t["final_sd"] = val, lab, sd
        return t

    def annual(self, site=None):
        f = self.final()
        if site:
            f = f[f.site == site]
        rows = []
        for stream, cfg in STREAMS.items():
            g = f[f.stream == stream]
            unresolved = g[g.final_value.isna()]
            est = g[g.final_label.str.startswith("estimated")]
            rows.append(dict(stream=stream, register=cfg["register"], unit=cfg["unit"],
                             n_measured=int(g.status.isin(["measured", "converted"]).sum()), n_estimated=len(est),
                             n_unresolved=len(unresolved), measured_total=float(g[~g.final_label.str.startswith("estimated")].final_value.sum()),
                             estimated_total=float(est.final_value.sum()), total=float(g.final_value.sum()) if not len(unresolved) else np.nan,
                             sd_estimate=annual_sd(est.final_sd.values, None if self.calibrate else 1.0),
                             sd_linear=float(est.final_sd.sum()), complete=len(unresolved) == 0))
        return pd.DataFrame(rows)

    def lineage(self):
        f = self.final()
        cols = ["site", "period", "stream", "unit", "record_ids", "raw_values", "raw_units", "notes", "status", "issues", "value",
                "method", "candidates", "estimate", "sd", "low95", "high95", "refusal", "warning", "fallback_method", "fallback_estimate", "fallback_sd", "decision", "decided_by", "decided_at",
                "decision_note", "final_value", "final_label", "final_sd"]
        out = f[cols].copy()
        out["method_text"] = out["method"].map(METHOD_TEXT).fillna("")
        return out

    def export(self, path_prefix):
        lin = self.lineage()
        lin.to_csv(f"{path_prefix}_lineage.csv", index=False)
        with open(f"{path_prefix}_lineage.json", "w") as fh:
            json.dump(dict(source=self.source_name, raw_sha256=self.raw_hash, year=self.year,
                           rules=dict(MIN_MEASURED=MIN_MEASURED, MAX_GAP_RUN=MAX_GAP_RUN, MAX_REL_ERR=MAX_REL_ERR, CP_ALPHA=CP_ALPHA, CP_MIN_SHIFT=CP_MIN_SHIFT, MIN_REGIME=MIN_REGIME, PROD_ANOMALY=PROD_ANOMALY, CAL_MONTHLY=CAL_MONTHLY, RHO_ANNUAL=RHO_ANNUAL, calibrated=self.calibrate),
                           methods=METHOD_TEXT, events=self.events,
                           cells=json.loads(lin.to_json(orient="records", default_handler=str))), fh, indent=1)


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ supplier factors
def supplier_factors(sup, proxy_value, proxy_low, proxy_high, proxy_source):
    """Weighted supplier emission factor. Missing supplier-specific factors use the documented proxy (labelled);
    a missing quantity is never estimated (the supplier is flagged and the weighted factor is not computed)."""
    s = sup.copy()
    s["quantity_t"] = pd.to_numeric(s["quantity_t"], errors="coerce")
    s["ef_tco2_per_t"] = pd.to_numeric(s.get("ef_tco2_per_t"), errors="coerce")
    s["ef_label"] = np.where(s["ef_tco2_per_t"].notna(), "supplier-specific", f"proxy: {proxy_source}")
    s["ef_used"] = s["ef_tco2_per_t"].fillna(proxy_value)
    s["ef_low"] = np.where(s["ef_tco2_per_t"].notna(), s["ef_tco2_per_t"], proxy_low)
    s["ef_high"] = np.where(s["ef_tco2_per_t"].notna(), s["ef_tco2_per_t"], proxy_high)
    bad = s[s["quantity_t"].isna() | (s["quantity_t"] < 0)]
    if len(bad):
        return s, dict(complete=False, reason=f"quantity missing or invalid for {', '.join(bad['supplier'].astype(str))}; not estimated")
    q = s["quantity_t"].sum()
    w = float((s["quantity_t"] * s["ef_used"]).sum() / q)
    return s, dict(complete=True, quantity_t=float(q), ef_weighted=w, share_proxy=float(s.loc[s.ef_label != "supplier-specific", "quantity_t"].sum() / q),
                   ef_low=float((s["quantity_t"] * s["ef_low"]).sum() / q), ef_high=float((s["quantity_t"] * s["ef_high"]).sum() / q))
