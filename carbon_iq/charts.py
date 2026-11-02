"""Static charts for the report and workbook (matplotlib, PNG). Every number comes from pipeline.run()."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NAVY, BLUE, ORANGE, GREEN, GREY, RED, LIGHT = "#1F3A5F", "#2E6F9E", "#D9822B", "#3E8E7E", "#8A94A6", "#C8553D", "#DCE3EC"
SCOPE_COL = {"Scope 1": "#2E6F9E", "Scope 2": "#D9822B", "Scope 3 Cat 1": "#3E8E7E", "Scope 3 Cat 4": "#7FB8A8"}
LABEL = {"tariff": "Electricity tariff", "b_saving_frac": "Motor-system savings (B)", "pv_capex_kw": "Solar capex per kW",
         "b_capex": "Motor project capex (B)", "pv_yield": "Solar yield", "elec_mwh": "Electricity use", "diesel_price": "Diesel price",
         "gas_price_usd": "Gas price", "c_saving_frac": "Compressed-air savings (C)", "d_saving_frac": "Heat-recovery share (D)",
         "d_capex": "Heat-recovery capex (D)", "ef_grid": "Grid emission factor", "c_capex": "Compressed-air capex (C)",
         "gas_gj": "Gas use", "e_capex": "Forklift capex (E)", "e_kwh_per_l": "Forklift kWh per litre (E)"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 10, "axes.titleweight": "bold"})


def _save(fig, out, name):
    fig.tight_layout()
    path = Path(out) / name
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def make_all(res, out):
    Path(out).mkdir(parents=True, exist_ok=True)
    files = []
    # 1 emissions by source
    rows = sorted(res["baseline"], key=lambda r: r["emissions_t"])
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    ax.barh([r["source"] for r in rows], [r["emissions_t"] for r in rows], color=[SCOPE_COL[r["scope"]] for r in rows])
    for i, r in enumerate(rows):
        ax.text(r["emissions_t"] + 120, i, f"{r['emissions_t']:,.0f} t  ({r['scope']})", va="center", fontsize=8)
    ax.set_xlim(0, max(r["emissions_t"] for r in rows) * 1.45)
    ax.set_xlabel("tCO2e per year (synthetic facility)")
    ax.set_title("Baseline emissions by source")
    files.append(_save(fig, out, "c1_emissions_by_source.png"))
    # 2 data quality
    u = sorted(res["uncertainty"], key=lambda r: r["u_combined_pct"])
    fig, ax = plt.subplots(figsize=(7.6, 2.8))
    col = {"High": GREEN, "Good": BLUE, "Fair": ORANGE, "Poor": RED}
    ax.barh([r["source"] for r in u], [r["u_combined_pct"] for r in u], color=[col[r["quality"]] for r in u])
    for i, r in enumerate(u):
        ax.text(r["u_combined_pct"] + 0.6, i, f"±{r['u_combined_pct']:.1f}%  {r['quality']}", va="center", fontsize=8)
    ax.set_xlim(0, 48)
    ax.set_xlabel("95% uncertainty of the source estimate (±%, first-order propagation)")
    ax.set_title("Emissions data quality by source")
    files.append(_save(fig, out, "c2_data_quality.png"))
    # 3 MAC curve (Scope 1+2 projects + F on Scope 3)
    pr = sorted(res["projects"], key=lambda p: p["mac_sar_per_t"])
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    x = 0
    for p in pr:
        w = p["scope12_t"] + p["scope3_t"]
        c = GREEN if p["mac_sar_per_t"] < 0 else (ORANGE if p["id"] != "F" else GREY)
        ax.bar(x, p["mac_sar_per_t"], width=w, align="edge", color=c, edgecolor="white")
        ax.text(x + w / 2, p["mac_sar_per_t"] + (25 if p["mac_sar_per_t"] >= 0 else -55), f"{p['id']}\n{p['mac_sar_per_t']:,.0f}",
                ha="center", fontsize=8)
        x += w
    ax.axhline(0, color="#444", lw=0.8)
    ax.set_xlabel("Annual reduction, tCO2e (bar width)   -   F reduces Scope 3 only")
    ax.set_ylabel("SAR per tCO2e")
    ax.set_title("Marginal abatement cost by project (negative = net saving)")
    ax.set_ylim(min(p["mac_sar_per_t"] for p in pr) - 120, max(p["mac_sar_per_t"] for p in pr) + 130)
    files.append(_save(fig, out, "c3_mac_curve.png"))
    # 4 frontier and methods
    fr = [r for r in res["frontier"] if r["npv"] is not None]
    fig, ax = plt.subplots(figsize=(7.6, 3.2))
    ax.step([r["target_t"] for r in fr], [r["npv"] / 1e6 for r in fr], where="post", color=NAVY, lw=1.8, label="Optimal NPV for each target")
    for b, m in zip(res["baselines"], ("o", "s", "^")):
        ax.scatter(b["scope12_t"], b["npv"] / 1e6, marker=m, s=50, color=ORANGE, zorder=3, label=f"{b['method']} ({b['portfolio']})")
    o = res["optimal"]
    ax.scatter(o["scope12_t"], o["npv"] / 1e6, s=90, color=GREEN, zorder=4, label=f"Optimised with target ({o['portfolio']})")
    ax.axvline(res["target_t"], color=RED, ls="--", lw=1)
    ax.text(res["target_t"] + 15, ax.get_ylim()[1] * 0.85 if ax.get_ylim()[1] > 0 else 0.3, "15% Scope 1+2 target", color=RED, fontsize=8)
    ax.set_xlabel("Scope 1+2 reduction, tCO2e/yr")
    ax.set_ylabel("NPV, SAR million")
    ax.set_title("Optimised portfolio vs one-by-one ranking (budget SAR 5M)")
    ax.legend(fontsize=7, loc="lower left", frameon=False)
    files.append(_save(fig, out, "c4_frontier_methods.png"))
    # 5 MC distributions
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    for (name, vals), c in zip(res["mc_hist"].items(), (BLUE, ORANGE)):
        st = next(r for r in res["mc_portfolios"] if r["portfolio"] == name)
        ax.hist(np.array(vals) / 1e6, bins=60, alpha=0.55, color=c,
                label=f"{name}: mean {st['e_npv']/1e6:.2f}M, 5th pct {st['p5_npv']/1e6:.2f}M, target met {st['p_target']:.0%}")
    ax.axvline(0, color="#444", lw=0.8)
    ax.set_xlabel("Portfolio NPV, SAR million (20,000 scenarios)")
    ax.set_ylabel("Scenarios")
    ax.set_title("Uncertainty: highest expected NPV vs carbon-reliable choice")
    ax.legend(fontsize=7, frameon=False)
    files.append(_save(fig, out, "c5_mc_distribution.png"))
    # 6 VOI
    vv = res["voi"]
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    names = [r["information"] for r in vv][::-1]
    ax.barh(names, [r["evppi_sar"] / 1e3 for r in vv][::-1], color=BLUE, label="Expected value of perfect information (EVPPI)")
    costs = [(r["collection_cost_sar"] or 0) / 1e3 for r in vv][::-1]
    ax.scatter(costs, range(len(names)), color=RED, marker="|", s=200, zorder=3, label="Cost of collecting it")
    if res.get("voi_noise_floor"):
        ax.axvline(res["voi_noise_floor"] / 1e3, color="#555555", ls="--", lw=1, label="Estimator noise floor (irrelevant variable)")
    ax.set_xlabel("SAR thousand")
    ax.set_title("Which information is worth collecting before investing?")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    files.append(_save(fig, out, "c6_value_of_information.png"))
    # 7 tornado
    tor = res["tornado_det_opt"][:8][::-1]
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    base = tor[0]["base_npv"] / 1e6
    for i, r in enumerate(tor):
        lo, hi = r["npv_low"] / 1e6, r["npv_high"] / 1e6
        ax.barh(i, hi - base, left=base, color=GREEN if hi >= base else RED)
        ax.barh(i, lo - base, left=base, color=RED if lo < base else GREEN)
    ax.set_yticks(range(len(tor)), [LABEL.get(r["parameter"], r["parameter"]) for r in tor])
    ax.axvline(base, color="#444", lw=0.8)
    ax.set_xlabel(f"NPV of {res['optimal']['portfolio']}, SAR million (5th / 95th percentile of each input)")
    ax.set_title("One-way sensitivity of the recommended portfolio")
    files.append(_save(fig, out, "c7_tornado.png"))
    # 8 timing
    sw = res["timing_tree_sweep"]
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 2.9))
    ax = axs[0]
    ax.plot([r["p_reform"] for r in sw], [r["npv_invest_now"] / 1e3 for r in sw], "o-", color=ORANGE, label="Invest now")
    ax.plot([r["p_reform"] for r in sw], [r["value_wait_one_year"] / 1e3 for r in sw], "s-", color=NAVY, label="Wait one year")
    ax.axhline(0, color="#444", lw=0.8)
    ax.set_xlabel("Probability of gas-price reform")
    ax.set_ylabel("SAR thousand")
    ax.set_title("Heat recovery: decision tree")
    ax.legend(fontsize=7, frameon=False)
    ax = axs[1]
    if "timing_scan" in res:
        rows = res["timing_scan"]["rows"]
        ax.plot([r["gbar"] for r in rows], [r["value_invest_now"] / 1e3 for r in rows], color=ORANGE, label="Invest now")
        ax.plot([r["gbar"] for r in rows], [r["value_wait"] / 1e3 for r in rows], color=NAVY, label="Optimal waiting (LSMC)")
        ax.axvline(res["timing_scan"]["static_breakeven_usd"], color=GREY, ls=":", lw=1)
        if res["timing_scan"]["trigger_usd"]:
            ax.axvline(res["timing_scan"]["trigger_usd"], color=RED, ls="--", lw=1)
        ax.set_xlabel("Long-run gas price, USD/MMBtu")
        ax.set_title("KAPSARC-style log-OU extension")
        ax.legend(fontsize=7, frameon=False)
    files.append(_save(fig, out, "c8_timing.png"))
    # 9 sobol for decision
    sb = list(res["sobol_decision"].items())[:7][::-1]
    fig, ax = plt.subplots(figsize=(7.6, 2.6))
    ax.barh([LABEL.get(k, k) for k, _ in sb], [v * 100 for _, v in sb], color=NAVY)
    for i, (_, val) in enumerate(sb):
        ax.text(val * 100 + 0.8, i, f"{val:.0%}", va="center", fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of variance explained (first-order index, %)")
    pair = res.get("sobol_decision_pair", ["A+B", "A+C+D"])
    ax.set_title(f"What drives the choice between {pair[0]} and {pair[1]}?")
    files.append(_save(fig, out, "c9_sobol_decision.png"))
    return files
