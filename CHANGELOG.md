# CARBON IQ change log

## v2.1 — final quality-improvement pass (30 October 2026; model v1.3 unchanged)

No analytical module, input, equation or decision rule changed; the synthetic results are identical (tested).

1. **MRC emissions reconciliation** (`mrc.scope1_reconciliation`, `mrc.grid_factor_comparison`): the +144 tCO2e (+0.22%) Scope 1
   difference is decomposed (CO2 at IPCC defaults 64,038 t + CH4/N2O 67 t vs 63,961 t reported) and tested against causes: the
   GWP set (< 4 t), CH4/N2O alone (CO2 alone is already 77 t above), the gas carbon factor (0.23% lower — inside the IPCC range —
   closes the gap), gross vs net heating values (gross would give ~10% less). Verdict: consistent (gap = 6% of the ±2,535 t
   uncertainty); exact cause unknown without Ma'aden's factors. The 0.335 tCO2e/MWh Scope 2 factor is now shown as **derived
   (back-calculated), not verified**, next to the derived national average and the missing independently verified factor.
   Explanations appear in Learning Mode; tables in both modes.
2. **Budget feasibility** (`mrc.budget_feasibility`; `budget_needed` and `budget_margin_se` per plan in `mrc.monte_carlo`; synthetic
   portfolio step): the budget is never raised automatically. Infeasible cases explain why and show the minimum budget under
   the model's assumptions (deterministic and with the 90% rules), or state that the target is unreachable at any budget. The
   default MRC scenario's choice (A+B+C needs SAR 69.9M of SAR 70M; 1.4 standard errors from the threshold) is flagged as a
   knife-edge. The MRC simulation now uses 20,000 futures (as the synthetic plant), because 5,000 gave a different choice.
3. **Method accuracy:** "Multi-criteria investment ranking" was split into *Single-criterion project ranking* (fully
   implemented, comparison baselines) and *Multi-criteria decision analysis (weighted scoring)* (**not implemented**); "Risk
   register and decision stability" into *Decision-stability checks* (fully implemented) and *Risk register* (**not
   implemented**). New entries: *Reconciling recalculated and reported emissions*, *Budget feasibility and minimum budget*.
   Status now: 17 fully, 1 partially (timing), 3 not implemented (ROI, MCDA, risk register).
4. **Learning:** every method has a numerical example, at least one methodology reference, its code references, the **actual
   Python source** of its main function (read live from the code: "Show the actual Python code" toggle, Learning Center
   expander, learning guide) and a 20-second judge script (42-60 words, tested 40-75).
5. **Presentation:** the MRC guided demo is one story — a "story so far" strip carries the key numbers from the reported baseline
   (160,632 t) through the checks, the hypothetical options and simulation to a recommendation with confidence, knife-edge
   warning, what MRC must verify and limitations; each step ends with a bridge to the next. New MRC workspace step
   "8 · Recommendation & limits".
6. **Tests:** 153 → 161 (8 new in `tests/test_v2.py`: reconciliation, derived-vs-verified labels, budget never raised,
   knife-edge flag, synthetic infeasible-budget message, dataset separation, MRC demo story, method script/code/reference checks).

## v2.0 — learning-friendly decision-support dashboard (30 October 2026; model v1.3 unchanged)

**Preserved (no change):** every input in `assumptions.py`, every equation, constraint, decision rule and analytical
module (`engine`, `optimize`, `uncertainty`, `decisions`, `voi`, `sensitivity`, `timing`, `pipeline`, `dataquality/`,
`independent/`), all saved outputs, the workbook, the A4 missing-data review and all A6 checks. The synthetic plant's
results are identical (A+B+C under D1–D4; tested in `tests/test_v2.py::test_mrc_scenario_uses_the_unchanged_engine`).

**Upgraded:**
- Navigation: sidebar with **Mode** (Learning / Presentation, same calculations), **Dataset** (synthetic plant / MRC) and
  **Go to** (Guided demo, Analysis workspace, Learning Center). The ten Phase B analysis tabs are re-ordered as a numbered
  workflow (1 Emissions → 8 Timing, then Evidence & scenarios, Assumptions); their code is unchanged apart from position.
  Decision settings moved into a collapsible "Advanced settings" sidebar section (same widget keys).
- Visual design: theme (`.streamlit/config.toml`), header, cards, consistent chart styling, readable SAR formatting.
- Guided demo: the eight required steps (meet the factory → explain the recommendation and its limitations), each with an
  introduction, chart or table, plain-language explanation, small example, key takeaway and Next/Back buttons; works for
  both datasets; numbers still read from the reproducible run outputs.
- "📘 Learn how this works" (7 elements, Learning Mode) under every major feature; "🔎 Source & calculation" under every
  major result (origin, type, year/company, unit, function, uncertainty, effect on the decision from the switch-point sweep).
- Projects step shows IRR and payback as display columns (computed with the existing `engine.irr/project_irr` and
  `engine.simple_payback`).
- New `carbon_iq/mrc.py`: MRC 2025 reported figures with page references, verified against the data book; Scope 1
  recalculated with IPCC 2006 factors (64,105 vs 63,961 t, +0.22%); implied Scope 2 factor (0.335 vs 0.573 tCO2e/MWh);
  hypothetical investment scenario (projects A–D, sizes and costs scaled from the register, labelled) evaluated with the
  unchanged `engine.projects`, `engine.portfolio`, register distributions and `alpha_saa`.
- New `carbon_iq/learning.py` (17 methods with implementation status), `carbon_iq/ui/` (theme, panels, MRC screens,
  Learning Center), `tools/build_v2_docs.py`, `report/v2/learning_guide.js`, `docs/v2/`.

**Tests:** 127 → 153. New `tests/test_v2.py` (26: MRC import, unit conversions, recalculation, labelling, learning
content vs code, citations well-formed, every page in both modes and both datasets, Next button). Three existing app tests
now open the "Analysis workspace" page first and expect 10 workflow tabs instead of 11 (the guided demo became a page);
their content assertions are unchanged. `tools/consistency_a6.py` opens the same page.

**Not done (by design):** no monthly MRC data, project costs or MRC targets were invented, so missing-data estimation, value
of information and real options are not run for MRC. ROI is not added as a metric (no fixed definition; NPV, IRR and
payback cover it). No weighted multi-criteria score was added.

## Phase B — competition package (26 October 2026; model v1.3 unchanged)

No input, equation, constraint or result changed.
- App: new first tab "▶ Guided demo" (`carbon_iq/demo_view.py`, presentation of saved outputs; 8 steps; "show all" backup
  mode). The other tabs keep their indices (`demo_tab, *tabs = st.tabs(...)`); tab count 10 -> 11.
- New tools: `build_phase_b.py` (impact scorecard with traced sources), `phase_b_content.py` (demo script),
  `build_demo_guide.py` (PDF), `draw_architecture.py`; `docs/phase_b/` (script, screenshots, capture script, diagram);
  Word package builder `report/b/report_b.js`.
- Fixed a stale label in the A4 decision comparison ("must reproduce model v1.2" -> "the register model").
- Tests 123 -> 127 (tests/test_b.py).

## A6 — independent mathematical and integrated validation (26 October 2026; model v1.3, A5 inputs unchanged)

No input, equation or decision rule was changed to alter results; all decisions are unchanged (A+B+C under D1-D4).

- New `independent/indep.py`: separately written re-implementation (does not import `carbon_iq`; checked by a test) of the
  inventory, factor derivations, year-by-year ledger cash flows, NPV/IRR/payback/MAC, 64-portfolio enumeration and an
  inverse-CDF Monte Carlo sampler (MT19937 / scrambled Sobol).
- New `tools/run_a6.py` (emissions, finance, optimisation over 3,267 budget/target/exclusivity cases, independent Monte
  Carlo, convergence over 7 sample sizes x 10 seeds, budget closed form, EVPI/EVPPI/EVSI cross-checks, real options incl.
  the Longstaff-Schwartz American-put benchmark, missing-data coverage and an independent change test, Sobol indices),
  `tools/build_a6_workbook.py` (independent spreadsheet: 1,023 formulas, 52 checks), `tools/build_a6_tables.py`,
  `tools/consistency_a6.py` (Python/Excel/Streamlit/Word scan), report `docs/CARBON_IQ_A6_Mathematical_Validation_Report.docx`.
- Fixed: project IRR ignored PV degradation (A: 11.5% -> 11.0%; `engine.project_irr`); NaN inputs were optimised silently
  (now `ValueError`); degraded annuity factor at r = -d; MILP names the empty portfolio "(none)".
- Fixed v1.2 leftovers: A4 key portfolios now include A+B+C; A4 decision chart, workbook note, app data-gap table and
  stability flags (D1/D2 now flagged too); A4 study rerun and A4 report regenerated with the v1.3 register; timing docstring.
- Tests 103 -> 123 (20 in tests/test_a6.py); fault injections 24 -> 28.

## A5 — carbon and financial data strengthening (26 October 2026; model v1.3)

Register inputs changed; methods unchanged apart from two documented formula corrections. The v1.2 register is kept as
a profile (`assumptions.use_profile("v1.2")`), which reproduces every v1.2 decision and NPV exactly.

- **Grid factor 0.55 -> 0.573 tCO2e/MWh (derived)**: KSA First Biennial Transparency Report (UNFCCC, Mar 2025) 2021
  electricity-generation emissions 205,579 Gg CO2e / GASTAT 2021 generation 358,640 GWh. Corroborated by the DNA 2021
  factor 0.568. The 0.55 source was never located. Target 1,316.7 -> 1,358.1 t.
- **Methane price USD 3.00 -> 2.15/MMBtu (provisional)**: regulated price from 1 Jan 2025 (Al Jazira Capital summary
  of Aramco notices); 2026 rise reported but unconfirmed (scenario G1); v1.2 anchor kept as G2. Reform price 4.5 -> 3.225.
- **Rooftop PV capex SAR 3,750 -> 2,500/kWp (transferred benchmark)**: Knight Frank 2025, Riyadh providers SAR 2.5/W.
  Not a quotation; sd widened 10% -> 15%; v1.2 value kept as scenario P1.
- **PV degradation 0.5%/yr added** (Jordan & Kurtz 2013; range 0.3-1.0%) via a degraded annuity factor (formula
  correction: v1.2 assumed constant output for 25 years).
- **Compressed-air savings 25% -> 20%** (range 10-30%; leaks cannot be eliminated) and a **leak-management cost
  SAR 15,000/yr** (hypothetical) so that savings persist.
- PV yield upper bound 1,950 -> 2,010 (Alzahrani & Nahhas 2021).
- **MAC** now divides by discounted tonnes (identical for constant-output projects).
- Forklift kWh/L relabelled derived -> hypothetical (no source). Sources, publication dates, effective periods and
  geography added; new evidence class (measured / external / derived / hypothetical / estimated) on every input.
- New scenario sets: gas price (G0-G2), PV capex (P0-P1); attribution of each change (`a5_attribution.csv`).
- Workbook: Source Register and A5 Changes sheets (19 sheets), degraded discount factor column, C leak cost.
- New `tools/build_a5_register.py`: source register and before/after workbooks, GHG boundary review, independent
  financial-formula checks (17/17 pass).
- App: gas and PV scenario tables, evidence class and v1.3 change column; corrected stale grid-factor text.
- Text and analysis no longer hard-coded to the v1.2 result: objectives explanation conditional on validation; the
  first-order variance contrast follows the decision (v1.3: A+B+C vs A+B; C's savings fraction explains 81%).
- Result: all four rules choose A+B+C (solar + motors + compressed air); D4 becomes feasible at SAR 5M. This change is
  driven by the PV cost benchmark (with the v1.2 PV cost, D4 stays infeasible). Tests 100 -> 103; fault injections 24.

## A4 refinement (26 October 2026; decision model v1.2 unchanged)

- **Decision stability** (`dataquality/stability.py`): margins in Monte Carlo standard errors, plausible-true-dataset
  agreement, switch points; dashboard warnings. Result: D1, D2, D4 stable; D3 unstable (complete data: sampling; demo
  estimates: 85% agreement, switch at -0.8% electricity).
- **Calibration**: split-conformal monthly factor 1.090 and within-stream correlation 0.12 (fitted on seed 5501).
  Held-out base set: monthly coverage 93.3% -> 94.9%; annual 96.9% -> 95.1% with
  29% narrower annual intervals (the linear sum was overly wide). Under-coverage remains with mid-year production shifts.
- **Uncertain target**: an estimated baseline now makes the 15% target uncertain in the Monte Carlo.
- **Value of information**: pre-posterior analysis replaces the binning EVPPI for missing records (zero value for
  irrelevant records by construction); only electricity records have decision value (D3: about SAR 49k, sd 22k across
  seeds; hypothetical cost SAR 600).
- **Operational change detection** with regime-restricted estimation, refusal and labelled reviewer override; on
  clean synthetic data 0.8% of stream-years warned; after injected energy-use changes the error of estimated gaps
  fell from 17.9% to 8.9% (30% refused).
- Synthetic generator variants (high noise, flat season, trend, two change types); faster quality assessment.
- Streamlit tab: before/after comparison, warnings, stability and information toggles (20,000 scenarios).
- Workbook: Calibration, Change detection, Stability and Information value sheets; correlated annual sd formula.
- Tests 78 -> 90; fault injections 15 -> 20; all v1.2 outputs bit-identical.

## A4 — missing-data intelligence (25 October 2026; decision model v1.2 unchanged)

New sub-package `carbon_iq/dataquality/` (quality, estimate, integrate, synth, validate, workbook_a4), new tab
**Data gaps (A4)** in `app.py`, `tools/run_a4.py`, `CARBON_IQ_A4_Data_Quality.xlsx`, `outputs/a4/`, 19 new tests and 5 new
fault injections. No existing module, equation, assumption or v1.2 output changed: all 24 v1.2 data files and 9 charts
are bit-identical to the v1.2 manifest.

- Data-quality assessment: missing rows, blanks, unknown units (never guessed), exact unit conversions, negative values,
  identical and conflicting duplicates, robust z-score outliers on intensity, probable unit-scale errors, legitimate vs
  suspected-missing zeros.
- Estimation: production intensity, seasonal history, mean of measured months; selection by leave-one-out back-test;
  95% prediction intervals (t-widened); refusal rules (≥6 measured months, ≤3 consecutive missing, back-test error ≤25%).
- Approval workflow and lineage: original table hashed and never modified; every proposal, decision and reviewer logged.
- Decision integration: approved totals and estimation sd enter the unchanged Monte Carlo; unresolved gaps block the
  decision. Complete data reproduce v1.2 exactly.
- Synthetic demonstration: 9 gaps, all estimates within 8.7% of truth, 9/9 inside 95% intervals; D1, D2, D4 unchanged and
  D3 stays A+C+D with approved estimates; counting gaps as zero understates Scope 1+2 by 24.6% and makes D4 falsely feasible.
- Validation on 150 synthetic facility-years: monthly MAPE 6.5–6.9%, monthly 95% coverage
  91.4–93.8%; annual error 0.5–1.3% vs 9.5–41.9% when gaps are counted as zero.
  Synthetic only - not evidence of real-world accuracy.
- Development finding fixed before release: an empty register key was read as NaN, silently dropping production from the
  activity mapping (A4-10); now tested.
- Word report regenerated so its test and fault counts (78 tests, 15 faults) match the suite.

## v1.2 — management decisions on A1 (25 October 2026)

Two decisions by the project owner, implemented without changing any project equation:

1. **Carbon target counted against the fixed reporting baseline** (reductions at fixed reporting emission factors).
   This becomes the primary basis. The v1.1 sampled-factor basis (S1) and a new uncertain-baseline basis (S2:
   target = 15% of the simulated baseline) are reported as sensitivities.
2. **90% budget chance constraint**: P(actual capital cost ≤ SAR 5M) ≥ 90%, jointly with the 90% carbon constraint
   (rule D4, primary recommendation rule). Both probabilities are reported for every portfolio. When no portfolio
   qualifies, none is forced; the minimum budget, budget curve and alternative risk thresholds are reported.

Method strengthening required by decision 1: with fixed reporting factors A+B's target probability is 90.3% on the
20,000 scenarios but 89.9% (95% CI 89.8–90.0%) on an independent 200,000-scenario sample, and below 90% on four of five
other 20,000-scenario samples. Chance constraints are therefore imposed at a sampling-tightened level
α + 1.645·√(α(1−α)/S) and validated out of sample (Pagnoncelli, Ahmed & Shapiro 2009).

Effect on results (all from the decisions; see `outputs/changes_v1_1_to_v1_2.csv`):

| Result | v1.1 | v1.2 |
|---|---|---|
| D1 deterministic / D2 highest E[NPV] | A+B / A+B | unchanged |
| Carbon rule | A+C+D (sampled factors, in-sample) | A+C+D (fixed reporting baseline, tightened and validated); in-sample-only rule would give A+B |
| Primary recommendation | A+C+D | **none feasible at SAR 5M**; minimum budget ≈ SAR 5.20M (A+C+D) |
| P(target) column of the Monte Carlo table | sampled factors | fixed reporting baseline (sampled-factor values kept in an extra column) |
| EVPI / EVSI motor audit | SAR 651,383 / 551,262 | SAR 654,323 / 584,081 under the new carbon rule |
| VOI noise floor | SAR 0 | SAR 269,985 (near-threshold estimator noise; method revision in A6) |

New: `budget_chance_level` parameter; `uncertainty.alpha_saa`; `Scenarios(basis="baseline")`; decision rules D1–D4,
S1–S2 in `decisions.py`; `outputs/decision_scenarios.csv`, `minimum_budget.csv`, `budget_curve.csv`,
`risk_thresholds.csv`; app defaults to the primary basis and the budget rule; two new injected faults (10/10 detected).

## v1.1 — Phase A1 corrections (25 October 2026)

No equation of v1.0 was changed. Every changed assumption and its effect on results is listed below; the full
machine-generated comparison is `outputs/changes_v1_0_to_v1_1.csv` (`python tools/compare_versions.py`).

### Changed assumptions

| Parameter | v1.0 | v1.1 | Why | Effect on results |
|---|---|---|---|---|
| `diesel_forklift_l`, `diesel_genset_l`, `steel_t`, `freight_tkm` | ±5 / ±10 / ±2 / ±20 % (95%) hard-coded in `engine.py`, used only by the analytic table | same values, now in the register as normal distributions (1 s.d. = U/1.96), sampled in the Monte Carlo on an independent stream | analytic and Monte Carlo methods used different inputs (A1-09) | analytic uncertainty unchanged (±7.59% Scope 1+2, ±12.58% total); Monte Carlo check ±7.502% → ±7.501%; EVPI SAR 651,351 → 651,383; all decisions unchanged |
| `tariff` | 0.18, status verified | 0.18 reference, status **provisional**; scenarios 0.18 / 0.20 / 0.23 / 0.26 | 0.18 is documented for 2018–2026; a rise to 0.23 from 1 Jan 2027 was reported on 25 Oct 2026 by news sources; official schedule not obtained (A1-08) | reference results unchanged; scenario results added |
| `ef_grid` | 0.55, status verified | 0.55, status **provisional**; scenario 0.568 | primary SEC table never located; Saudi DNA 2021 factor 0.568 found only as cited by KFUPM (A1-07) | reference results unchanged; with 0.568 the target rises to 1,349 t/yr and no choice changes |
| `gas_price_usd`, `discount_rate`, `pv_life`, `ef_diesel`, `ef_freight`, `ef_steel_incumbent`, `ef_steel_alt`, `ro_kappa`, `ro_sigma`, `ro_mu_gbm` | status verified | status **transferred** | cited values from another country, sector or study (A1-13) | none (labels only) |

### Model and reporting changes

- Three decision objectives reported side by side (deterministic, maximum expected NPV, 90% chance-constrained),
  with an explanation of why they differ (`decisions.py`, workbook sheet *Decision Objectives*, app, report).
- Counting basis for reductions made explicit: `Scenarios(basis="physical")` (primary, v1.0 method) or
  `"reporting"` (fixed reference factors). With the reporting basis the chance-constrained choice is A+B (A1-02).
- Actual (uncertain) capital cost reported: P(actual capex > budget), mean, 90th and 95th percentile; optional
  constraint `budget_reliability`. Quoted-cost feasibility is unchanged (A1-10).
- Deterministic optimum at mean inputs reported to explain the deterministic vs expected NPV gap (A1-12).
- Value-of-information collection costs linked to the inputs in the workbook; the solar-capex row is labelled
  "cost not estimated" instead of "not collectable" (A1-18).
- `sample(fixed=...)` keeps the other inputs' draws aligned (v1.0 shifted the random stream; used only in tests).

### Reproducibility, tests and documentation

- Google Colab cell fixed (`%cd` on its own line) and `CARBON_IQ_Colab.ipynb` added (A1-01).
- `requirements.txt` floors corrected (NumPy ≥ 2.0, SciPy ≥ 1.13, pandas ≥ 2.2.2, Matplotlib ≥ 3.9,
  Streamlit ≥ 1.49); `requirements-lock.txt` added (A1-03).
- Portable workbook recalculation `carbon_iq/recalc.py` (LibreOffice); status written to
  `outputs/excel_recalc.json`; tests report skips explicitly; workbook set to recalculate on open (A1-06).
- Formula count corrected: v1.0's "920" included 24 TRUE/FALSE constants that LibreOffice stores as formulas; v1.0
  had 896 formulas, v1.1 has 906.
- `tools/fault_injection.py` (8 faults, all detected), `tools/run_tests.py`, `tools/crosscheck.py`,
  `tools/compare_versions.py` added (A1-05).
- Tests 39 → 57; statement coverage 57% → 97% (workbook and chart builders now tested) (A1-14).
- Manifest also hashes charts and documents what is and is not hash-compared (A1-15).
- "AI-Enabled" removed from all titles; the README, app and report state that no machine-learning model is
  included (A1-04).
- App: default 5,000 scenarios with a notice; counting-basis and budget-reliability controls; scenarios tab (A1-17).
- Word report builder included under `report/` so the report can be regenerated.

## v1.0 — 24 October 2026

Initial complete prototype.
