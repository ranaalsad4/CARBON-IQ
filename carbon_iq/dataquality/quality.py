"""Schema, unit handling and data-quality assessment.

Input: monthly activity records in long format
    record_id, site, period (YYYY-MM), stream, value, unit, source, note
The raw table is never modified; `assess` returns a new per-(site, period, stream) table with a status and issue codes.

Zero handling (never equate missing with zero):
  * blank / non-numeric / absent row          -> missing
  * 0 in an INTERMITTENT stream                -> legitimate zero (e.g. backup generators)
  * 0 in a CONTINUOUS stream when production
    in the same month is 0 or the note says
    'shutdown'                                 -> legitimate zero (documented shutdown)
  * 0 in a CONTINUOUS stream while production
    is positive                                -> suspected missing (treated as missing until a user confirms it)
"""
import re

import numpy as np
import pandas as pd

# stream -> configuration
STREAMS = {
    "production":       dict(unit="t", kind="driver", register=None, label="Finished output"),
    "operating_hours":  dict(unit="h", kind="continuous", register=None, label="Operating hours"),
    "electricity":      dict(unit="MWh", kind="continuous", register="elec_mwh", label="Grid electricity"),
    "natural_gas":      dict(unit="GJ", kind="continuous", register="gas_gj", label="Natural gas (NCV)"),
    "diesel_forklift":  dict(unit="L", kind="continuous", register="diesel_forklift_l", label="Diesel, forklifts"),
    "diesel_genset":    dict(unit="L", kind="intermittent", register="diesel_genset_l", label="Diesel, backup generators"),
    "steel_purchased":  dict(unit="t", kind="lumpy", register="steel_t", label="Purchased steel"),
    "freight":          dict(unit="t-km", kind="lumpy", register="freight_tkm", label="Inbound road freight"),
}
# unit -> (canonical unit, multiplier). Only exact, documented conversions; anything else is flagged, not guessed.
UNITS = {
    "t": ("t", 1.0), "tonne": ("t", 1.0), "tonnes": ("t", 1.0), "kg": ("t", 0.001),
    "h": ("h", 1.0), "hours": ("h", 1.0),
    "mwh": ("MWh", 1.0), "kwh": ("MWh", 0.001), "gwh": ("MWh", 1000.0),
    "gj": ("GJ", 1.0), "mj": ("GJ", 0.001), "mmbtu": ("GJ", 1.055056),
    "l": ("L", 1.0), "litre": ("L", 1.0), "liter": ("L", 1.0), "litres": ("L", 1.0), "m3": ("L", 1000.0),
    "gal_us": ("L", 3.785411784),
    "t-km": ("t-km", 1.0), "tkm": ("t-km", 1.0),
}
REQUIRED = ["site", "period", "stream", "value", "unit"]
ROBUST_Z = 3.5          # Iglewicz & Hoaglin (1993) modified z-score threshold
UNIT_SCALE_SUSPECT = (500.0, 1 / 500.0)


def _num(x):
    try:
        if x is None or (isinstance(x, str) and x.strip() == ""):
            return np.nan
        v = float(x)
        return v
    except (TypeError, ValueError):
        return np.nan


def validate_schema(raw):
    miss = [c for c in REQUIRED if c not in raw.columns]
    if miss:
        raise ValueError(f"missing columns: {miss}")
    unknown = sorted(set(raw["stream"]) - set(STREAMS))
    return unknown


def periods_for(year):
    return [f"{year}-{m:02d}" for m in range(1, 13)]


def assess(raw, year, site=None):
    """Return (cells, issues): one row per (site, period, stream) for the reporting year, and a list of issues.

    cells columns: site, period, stream, unit, raw_values, raw_units, record_ids, value (canonical, after exact
    unit conversion; NaN if unusable), status, issues"""
    validate_schema(raw)
    df = raw.copy()
    if "record_id" not in df.columns:
        df["record_id"] = [f"R{i+1:05d}" for i in range(len(df))]
    for c in ("source", "note"):
        if c not in df.columns:
            df[c] = ""
    df["note"] = df["note"].astype(object).where(df["note"].notna(), "").astype(str)
    sites = [site] if site else sorted(df["site"].dropna().unique())
    issues = []
    for s in sorted(set(df["stream"]) - set(STREAMS)):
        issues.append(dict(site="*", period="*", stream=s, code="UNKNOWN_STREAM", severity="error",
                           detail="stream not in schema; records ignored"))
    rows = []
    groups = {k: g for k, g in df.groupby(["site", "stream", "period"], sort=False)}
    empty = df.iloc[0:0]
    for st in sites:
        for stream, cfg in STREAMS.items():
            for per in periods_for(year):
                sub = groups.get((st, stream, per), empty)
                cell = dict(site=st, period=per, stream=stream, unit=cfg["unit"], raw_values=list(sub["value"]),
                            raw_units=list(sub["unit"]), record_ids=list(sub["record_id"]), notes=" | ".join(n for n in sub["note"] if n),
                            value=np.nan, status="missing", issues=[])
                if len(sub) == 0:
                    cell["issues"].append("MISSING_ROW")
                    rows.append(cell); continue
                vals = []
                for _, r in sub.iterrows():
                    v = _num(r["value"])
                    u = str(r["unit"]).strip().lower() if pd.notna(r["unit"]) else ""
                    if np.isnan(v):
                        cell["issues"].append("BLANK_OR_NONNUMERIC"); continue
                    if u not in UNITS or UNITS[u][0] != cfg["unit"]:
                        cell["issues"].append(f"UNKNOWN_UNIT:{r['unit']}"); continue
                    conv = v * UNITS[u][1]
                    if UNITS[u][1] != 1.0:
                        cell["issues"].append(f"UNIT_CONVERTED:{r['unit']}->{cfg['unit']}")
                    if conv < 0:
                        cell["issues"].append("NEGATIVE_VALUE"); continue
                    vals.append(conv)
                if len(sub) > 1:
                    uniq = sorted(set(round(x, 9) for x in vals))
                    if len(uniq) <= 1:
                        cell["issues"].append("DUPLICATE_IDENTICAL")
                        vals = vals[:1]
                    else:
                        cell["issues"].append("DUPLICATE_CONFLICT")
                        vals = []
                if vals:
                    cell["value"] = vals[0]
                    cell["status"] = "converted" if any(i.startswith("UNIT_CONVERTED") for i in cell["issues"]) else "measured"
                rows.append(cell)
    cells = pd.DataFrame(rows)
    _zero_rules(cells)
    _outliers(cells)
    cells.attrs.pop("_prod", None)
    for _, c in cells.iterrows():
        for code in c["issues"]:
            issues.append(dict(site=c["site"], period=c["period"], stream=c["stream"], code=code.split(":")[0],
                               severity=_severity(code), detail=code))
    return cells, pd.DataFrame(issues, columns=["site", "period", "stream", "code", "severity", "detail"])


def _severity(code):
    if code.startswith(("UNIT_CONVERTED", "DUPLICATE_IDENTICAL", "LEGITIMATE_ZERO")):
        return "info"
    if code.startswith(("OUTLIER", "SUSPECT_UNIT_SCALE", "ZERO_PRODUCTION")):
        return "warning"
    return "error"


def _prod(cells, site, period):
    look = cells.attrs.get("_prod")
    if look is None:
        pr = cells[cells.stream == "production"]
        look = {(a, b): float(v) for a, b, v in zip(pr.site, pr.period, pr.value)}
        cells.attrs["_prod"] = look
    v = look.get((site, period), np.nan)
    return v if not np.isnan(v) else np.nan


def _zero_rules(cells):
    for i, c in cells.iterrows():
        if c["status"] not in ("measured", "converted") or c["value"] != 0:
            continue
        kind = STREAMS[c["stream"]]["kind"]
        shutdown = "shutdown" in c["notes"].lower()
        prod = _prod(cells, c["site"], c["period"]) if c["stream"] != "production" else np.nan
        if c["stream"] == "production":
            cells.at[i, "issues"] = c["issues"] + (["LEGITIMATE_ZERO:documented shutdown"] if shutdown else ["ZERO_PRODUCTION:check"])
        elif kind in ("intermittent", "lumpy"):
            cells.at[i, "issues"] = c["issues"] + [f"LEGITIMATE_ZERO:{kind} stream"]
        elif shutdown or prod == 0:
            cells.at[i, "issues"] = c["issues"] + ["LEGITIMATE_ZERO:production zero/shutdown"]
        else:
            cells.at[i, "issues"] = c["issues"] + ["SUSPECTED_MISSING_ZERO"]
            cells.at[i, "status"] = "suspected_zero"


def _robust_z(x):
    x = np.asarray(x, float)
    if not np.isfinite(x).any():
        return np.zeros_like(x), np.nan
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))
    if not mad or np.isnan(mad):
        return np.zeros_like(x), med
    return 0.6745 * (x - med) / mad, med


def _outliers(cells):
    for (site, stream), g in cells.groupby(["site", "stream"]):
        if STREAMS[stream]["kind"] in ("intermittent", "lumpy"):
            continue
        ok = g[g.status.isin(["measured", "converted"]) & (g.value > 0)]
        if len(ok) < 6:
            continue
        if stream not in ("production",):
            prod = np.array([_prod(cells, site, p) for p in ok.period])
            with np.errstate(divide="ignore", invalid="ignore"):
                x = np.where(prod > 0, ok.value.values / prod, np.nan)
        else:
            x = ok.value.values
        z, med = _robust_z(x)
        for (idx, zz, xx) in zip(ok.index, z, x):
            if np.isnan(zz) or abs(zz) <= ROBUST_Z:
                continue
            ratio = xx / med if med else np.nan
            if ratio and (ratio > UNIT_SCALE_SUSPECT[0] or ratio < UNIT_SCALE_SUSPECT[1]):
                code = f"SUSPECT_UNIT_SCALE:value is {ratio:,.0f}x the median intensity; probable unit error"
            else:
                code = f"OUTLIER:robust z = {zz:.1f} ({'intensity' if stream != 'production' else 'value'})"
            cells.at[idx, "issues"] = cells.at[idx, "issues"] + [code]
            cells.at[idx, "status"] = "outlier"


def summary(cells):
    """Counts of cell statuses by stream."""
    t = cells.pivot_table(index="stream", columns="status", values="period", aggfunc="count", fill_value=0)
    return t.reindex(list(STREAMS)).fillna(0).astype(int)
