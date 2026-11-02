"""Run the complete CARBON IQ prototype and write every output.

    python run_all.py            # results -> outputs/ (CSV, JSON, charts) and CARBON_IQ_Data_Model.xlsx
    python run_all.py --fast     # skip the slow real-options trigger scans (for quick checks)
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

from carbon_iq import charts, pipeline

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def jdefault(o):
    try:
        import numpy as np
        if isinstance(o, np.generic):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    if isinstance(o, tuple):
        return list(o)
    return str(o)


def write_csv(path, rows):
    rows = list(rows)
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys or ["empty"])
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, default=jdefault) if isinstance(v, (list, dict, tuple)) else v) for k, v in r.items()})


def main(fast=False):
    OUT.mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    res, sc = pipeline.run(timing_detail=not fast)
    tables = {
        "assumptions.csv": res["assumptions"], "baseline_emissions.csv": res["baseline"], "data_quality.csv": res["uncertainty"],
        "projects.csv": res["projects"], "portfolios_deterministic.csv": res["portfolios"], "ranking_baselines.csv": res["baselines"],
        "efficient_frontier.csv": res["frontier"], "monte_carlo_portfolios.csv": res["mc_portfolios"], "regret.csv": res["regret"],
        "value_of_information.csv": res["voi"], "tornado_recommended.csv": res["tornado_det_opt"],
        "sobol_decision.csv": [{"parameter": k, "first_order_index": v} for k, v in res["sobol_decision"].items()],
        "switch_points.csv": [{"parameter": k, **x} for k, x in res["switch_points"].items()],
        "discount_rate_robustness.csv": res["discount_robustness"], "timing_tree_sweep.csv": res["timing_tree_sweep"],
        "decision_scenarios.csv": res["decision_scenarios"], "capex_risk.csv": res["capex_risk"]["table"],
        "budget_curve.csv": res["budget_analysis"]["curve"], "risk_thresholds.csv": res["budget_analysis"]["thresholds"],
        "minimum_budget.csv": res["budget_analysis"]["min_budget_by_portfolio"],
        "tariff_scenarios.csv": res["tariff_scenarios"], "grid_factor_scenarios.csv": res["ef_scenarios"],
        "gas_price_scenarios.csv": res["gas_scenarios"], "pv_capex_scenarios.csv": res["pv_capex_scenarios"],
        "a5_attribution.csv": res["a5_attribution"],
    }
    if "timing_scan" in res:
        tables["timing_lsmc_scan.csv"] = res["timing_scan"]["rows"]
    for name, rows in tables.items():
        write_csv(OUT / name, rows)
    summary = {k: v for k, v in res.items() if k not in ("mc_hist", "portfolios")}
    (OUT / "results.json").write_text(json.dumps(summary, indent=1, default=jdefault))
    charts.make_all(res, OUT / "charts")
    from carbon_iq import workbook
    xlsx = HERE / "CARBON_IQ_Data_Model.xlsx"
    workbook.build(res, xlsx)
    from carbon_iq.recalc import recalc   # cache formula values (LibreOffice) so the Excel-agreement tests can run
    rc = recalc(xlsx)
    (OUT / "excel_recalc.json").write_text(json.dumps(rc, indent=1))
    if rc["status"] == "success":
        print(f"Excel recalculation: success ({rc['total_formulas']} formulas, {rc['total_errors']} errors)")
    else:
        print(f"Excel recalculation: {rc['status']} - {rc.get('reason')} ({rc['total_formulas']} formulas not evaluated)")
    data_files = sorted(p for p in OUT.glob("*.csv") if not p.name.startswith(("changes_", "crosscheck"))) + [OUT / "results.json"]
    # (changes_*.csv and crosscheck.csv are written by tools/, not by this run)
    chart_files = sorted((OUT / "charts").glob("*.png"))
    manifest = {"model_version": res["meta"].get("model_version"), "scenarios": res["meta"]["scenarios"], "seed": res["meta"]["seed"],
                "outputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data_files},
                "charts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in chart_files},
                "note": "Data outputs are bit-reproducible on repeated runs and in the requirements-lock.txt environment. "
                        "With other NumPy/SciPy versions the last floating-point digit can differ (A1 audit: largest "
                        "absolute difference below 1e-9 SAR at the minimum versions); decisions and reported figures are "
                        "unchanged. Chart hashes depend on the matplotlib version. The workbook and Word report embed "
                        "timestamps and are compared by content (tests/test_outputs.py, tools/crosscheck.py), not by hash.",
                "excel_recalc": rc["status"]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    o, cc = res["optimal"], res["mc_chance_constrained"]
    print(f"Baseline Scope 1+2 {res['scope_totals']['Scope 1+2']:,.1f} t; total {res['scope_totals']['Total']:,.1f} t")
    print(f"Deterministic optimum {o['portfolio']}: NPV SAR {o['npv']:,.0f}, {o['scope12_t']:,.1f} t/yr")
    print(f"Carbon chance constraint ({res['meta']['chance_level']:.0%}, fixed reporting baseline, validated) {cc['portfolio']}: "
          f"E[NPV] SAR {cc['e_npv']:,.0f}, P(target) {cc['p_target']:.1%}, P(capex <= budget) {1 - cc['p_over_budget']:.1%}")
    j = res["mc_joint"]
    mb = res["budget_analysis"]["min_budget_by_portfolio"]
    print(f"Carbon {res['meta']['chance_level']:.0%} + budget {res['meta']['budget_chance_level']:.0%} rule: "
          + (f"{j['portfolio']}" if j["feasible"] else
             f"INFEASIBLE at SAR {res['meta']['budget']:,.0f}; minimum budget SAR {mb[0]['budget_needed']:,.0f} ({mb[0]['portfolio']})" if mb else "INFEASIBLE"))
    print(f"EVPI SAR {res['evpi']:,.0f}; EVSI motor audit SAR {res['evsi_audit']['evsi']:,.0f}")

    print("Outputs written to", OUT)
    return res


if __name__ == "__main__":
    main(fast="--fast" in sys.argv)
