"""SYNTHETIC facility data with known true values (demonstration and validation only - not real observations).

`truth_case()` builds two years (2025 history, 2026 reporting) for the CARBON IQ case plant whose 2026 annual totals
equal the assumption register exactly, so a complete dataset reproduces the v1.2 baseline. Monthly profiles reuse the
workbook's synthetic weights; month-to-month noise is drawn from a fixed seed. `random_facility()` draws other
synthetic facility-years for the validation study. `demo_incomplete()` degrades the truth in documented ways.
"""
import numpy as np
import pandas as pd

from ..assumptions import base_values

MONTHS = range(1, 13)
W_PROD = np.array([0.080, 0.078, 0.084, 0.086, 0.088, 0.083, 0.078, 0.080, 0.085, 0.088, 0.087, 0.083])
W_EL = np.array([0.072, 0.070, 0.078, 0.084, 0.092, 0.095, 0.098, 0.098, 0.090, 0.082, 0.072, 0.069])
W_GEN = np.array([0, 0, 0.02, 0.03, 0.08, 0.25, 0.30, 0.25, 0.05, 0.02, 0, 0])      # backup generators: zero in winter
DAYS = np.array([22, 22, 20, 20, 22, 22, 22, 22, 22, 22, 22, 22])
UNITS = dict(production="t", operating_hours="h", electricity="MWh", natural_gas="GJ", diesel_forklift="L",
             diesel_genset="L", steel_purchased="t", freight="t-km")


def _year(rng, totals, w_prod, w_el, noise):
    prod = w_prod * (1 + rng.normal(0, noise["prod"], 12)); prod = prod / prod.sum() * totals["production"]
    hours = 2 * 8 * DAYS * 1.0
    el = (0.55 * prod / prod.sum() + 0.45 * w_el / w_el.sum()) * (1 + rng.normal(0, noise["el"], 12))
    gas = prod / prod.sum() * (1 + rng.normal(0, noise["gas"], 12))
    fl = hours / hours.sum() * (1 + rng.normal(0, noise["fl"], 12))
    gen = W_GEN * (1 + rng.normal(0, noise["gen"], 12)) * (W_GEN > 0)
    steel = prod / prod.sum() * (1 + rng.normal(0, noise["steel"], 12))
    fr = steel * (1 + rng.normal(0, noise["fr"], 12))
    out = dict(production=prod, operating_hours=hours, electricity=el, natural_gas=gas, diesel_forklift=fl,
               diesel_genset=gen, steel_purchased=steel, freight=fr)
    for k, v in out.items():
        if k not in ("production", "operating_hours"):
            out[k] = v / v.sum() * totals[k]
    return out


NOISE = dict(prod=0.04, el=0.03, gas=0.04, fl=0.05, gen=0.15, steel=0.08, fr=0.05)


def case_totals():
    b = base_values()
    return dict(production=b["production_t"], electricity=b["elec_mwh"], natural_gas=b["gas_gj"], diesel_forklift=b["diesel_forklift_l"],
                diesel_genset=b["diesel_genset_l"], steel_purchased=b["steel_t"], freight=b["freight_tkm"])


def truth_case(seed=4401, growth=1.04):
    """Long-format truth for 2025 and 2026; 2026 annual totals equal the assumption register."""
    rng = np.random.default_rng(seed)
    t26 = case_totals()
    t25 = {k: v / growth for k, v in t26.items()}
    y25 = _year(rng, t25, W_PROD, W_EL, NOISE)
    y26 = _year(rng, t26, W_PROD, W_EL, NOISE)
    return _long({2025: y25, 2026: y26}, site="PLANT-01", source="SYNTHETIC truth (seed %d)" % seed)


def _long(years, site, source):
    rows, rid = [], 0
    for y, d in years.items():
        for stream, vals in d.items():
            for m, v in zip(MONTHS, vals):
                rid += 1
                rows.append(dict(record_id=f"R{rid:05d}", site=site, period=f"{y}-{m:02d}", stream=stream, value=float(v),
                                 unit=UNITS[stream], source=source, note=""))
    return pd.DataFrame(rows)


def demo_incomplete(truth=None):
    """Documented degradations of the 2026 truth (the history year is left complete). Returns (raw, changes)."""
    t = truth_case() if truth is None else truth.copy()
    raw = t.copy()
    raw["source"] = "SYNTHETIC demo dataset (degraded copy of truth)"
    ch = []

    def rec(per, stream):
        return raw[(raw.period == per) & (raw.stream == stream)].index[0]
    # electricity: peak-season months missing; one month entered in kWh; December entered as 0
    for per in ("2026-06", "2026-07"):
        raw = raw.drop(rec(per, "electricity")); ch.append((per, "electricity", "row deleted (missing bill)"))
    i = rec("2026-10", "electricity"); raw.at[i, "value"] = raw.at[i, "value"] * 1000; raw.at[i, "unit"] = "kWh"
    ch.append(("2026-10", "electricity", "reported in kWh"))
    i = rec("2026-12", "electricity"); raw.at[i, "value"] = 0.0; ch.append(("2026-12", "electricity", "entered as 0 (bill not yet received)"))
    # natural gas: blank month, conflicting duplicate, typing error x10
    i = rec("2026-03", "natural_gas"); raw.at[i, "value"] = None; ch.append(("2026-03", "natural_gas", "blank value"))
    i = rec("2026-09", "natural_gas"); dup = raw.loc[[i]].copy(); dup["record_id"] = "R99001"; dup["value"] = dup["value"] * 1.08
    raw = pd.concat([raw, dup]); ch.append(("2026-09", "natural_gas", "second, conflicting record (+8%)"))
    i = rec("2026-05", "natural_gas"); raw.at[i, "value"] = raw.at[i, "value"] * 10; ch.append(("2026-05", "natural_gas", "typing error x10"))
    # forklift diesel: one fuel-card month missing; identical duplicate in another
    raw = raw.drop(rec("2026-11", "diesel_forklift")); ch.append(("2026-11", "diesel_forklift", "row deleted"))
    i = rec("2026-04", "diesel_forklift"); dup = raw.loc[[i]].copy(); dup["record_id"] = "R99002"
    raw = pd.concat([raw, dup]); ch.append(("2026-04", "diesel_forklift", "identical duplicate"))
    # production: negative entry (sign error)
    i = rec("2026-02", "production"); raw.at[i, "value"] = -raw.at[i, "value"]; ch.append(("2026-02", "production", "negative value"))
    # purchased steel: one delivery month missing
    raw = raw.drop(rec("2026-08", "steel_purchased")); ch.append(("2026-08", "steel_purchased", "row deleted"))
    # backup generators: genuine zero months are kept as zeros (legitimate)
    raw = raw.reset_index(drop=True)
    return raw, pd.DataFrame(ch, columns=["period", "stream", "change"])


def demo_severe(truth=None):
    """A dataset that SHOULD NOT be estimated: six consecutive months of electricity missing."""
    t = truth_case() if truth is None else truth.copy()
    raw = t.copy()
    raw["source"] = "SYNTHETIC severe-gap dataset"
    drop = raw[(raw.stream == "electricity") & raw.period.isin([f"2026-{m:02d}" for m in range(3, 9)])].index
    return raw.drop(drop).reset_index(drop=True)


def suppliers_demo():
    """Synthetic supplier table. No supplier-specific factors are invented: both factors are blank, so the
    documented worldsteel proxy is used and labelled."""
    b = base_values()
    return pd.DataFrame([
        dict(supplier="Supplier S1 (synthetic)", material="steel", quantity_t=b["steel_t"] * 0.6, ef_tco2_per_t=None, ef_source=""),
        dict(supplier="Supplier S2 (synthetic)", material="steel", quantity_t=b["steel_t"] * 0.4, ef_tco2_per_t=None, ef_source=""),
    ])


VARIANTS = {
    "base": "generator used for the first A4 study: random scale, growth 0.95-1.10, noise 0.5-2x, seasonality shift",
    "high_noise": "month-to-month noise 2-4x the base level",
    "flat_season": "electricity without the summer cooling peak (flat monthly profile)",
    "trend": "within-year trend: 2026 values drift linearly by -15% to +15% from January to December",
    "break_intensity": "operational change: one energy stream's intensity shifts by 10-50% (up or down) from a month in Apr-Oct",
    "break_production": "operational change: output and output-linked streams shift by 20-40% from a month in Apr-Oct",
}
BREAK_STREAMS = ("electricity", "natural_gas", "diesel_forklift")


def random_facility(rng, scale=1.0, variant="base", info=None):
    """A random synthetic facility-year pair (2025, 2026) for the validation study. `variant` selects the generator
    family (VARIANTS); `info` (dict) receives the break month, stream and size for the break variants."""
    base = {k: v * scale * rng.uniform(0.6, 1.6) for k, v in case_totals().items()}
    growth = rng.uniform(0.95, 1.10)
    nm = (2.0, 4.0) if variant == "high_noise" else (0.5, 2.0)
    noise = {k: v * rng.uniform(*nm) for k, v in NOISE.items()}
    shift = rng.integers(-1, 2)
    w_el = np.full(12, 1 / 12) if variant == "flat_season" else np.roll(W_EL, shift) * (1 + rng.normal(0, 0.02, 12))
    w_prod = W_PROD * (1 + rng.normal(0, 0.03, 12))
    y25 = _year(rng, {k: v / growth for k, v in base.items()}, w_prod, w_el, noise)
    y26 = _year(rng, base, w_prod, w_el, noise)
    if variant == "trend":
        tr = rng.uniform(-0.15, 0.15)
        f = 1 + tr * (np.arange(12) - 5.5) / 11
        for k in y26:
            if k != "operating_hours":
                y26[k] = y26[k] * f
    if variant in ("break_intensity", "break_production"):
        b = int(rng.integers(3, 10))                       # first month of the new regime (index 3..9 = Apr..Oct)
        if variant == "break_intensity":
            st = BREAK_STREAMS[int(rng.integers(0, len(BREAK_STREAMS)))]
            size = float(rng.choice([-1, 1]) * rng.choice([0.10, 0.20, 0.30, 0.50]))
            y26[st] = y26[st].copy(); y26[st][b:] *= 1 + size
            streams = [st]
        else:
            size = float(rng.choice([-1, 1]) * rng.uniform(0.20, 0.40))
            streams = ["production", "natural_gas", "steel_purchased", "freight"]
            for st in streams:
                y26[st] = y26[st].copy(); y26[st][b:] *= 1 + size
            y26["electricity"] = y26["electricity"].copy(); y26["electricity"][b:] *= 1 + 0.55 * size   # 55% production-linked
            streams.append("electricity")
        if info is not None:
            info.update(break_month=f"2026-{b + 1:02d}", break_streams=streams, break_size=size)
    return _long({2025: y25, 2026: y26}, site="SYN", source=f"SYNTHETIC validation facility ({variant})")
