# CARBON IQ issue log (Phase A1 before v1.0 and after v1.2; Phases A2-A6, Phase B)

An issue is marked **Fixed** only when the verification column records the check that was run. Open items are carried to the stage named.

| ID | Priority | Issue | Status | Verification | Remaining |
|---|---|---|---|---|---|
| A1-01 | Critical | Colab instructions do not change into the project folder | Fixed (simulation); Google Colab run pending | README cell executed in IPython in a fresh Python 3.12 venv: unzip, %cd, pip install -r requirements.txt, run_all.py, run_tests.py (57 passed), Streamlit health check 'ok'. Not run on Google Colab itself (no access from this workspace). | Run once on Google Colab before submission; the apt-get LibreOffice line was not executed in the simulation. |
| A1-02 | Critical | Headline recommendation depends on an undisclosed modelling choice | Fixed | tests: test_reporting_basis_uses_fixed_factors, test_baseline_uncertainty_basis, test_decision_rules_structure_and_comparisons_preserved; fault injection detects an ignored basis; workbook, app, report and cross-check (144 checks, 0 mismatches) updated. | — |
| A1-03 | High | Minimum versions in requirements.txt are too low | Fixed | Python 3.11.17 with exactly the floor versions: run_all OK, 57 passed. Python 3.12.3 with current versions: 57 passed. Static test of the floors. | At the floor versions some values differ in the last floating-point digit (max 3.5e-10 SAR); documented (A1-23). |
| A1-04 | High | 'AI-Enabled' in titles although no ML model exists | Fixed | test_no_ai_or_ml_claims scans README, app and all modules; Word text searched: only the disclaimer and the change table mention the term. | Competitor table keeps 'AI analytics: planned (no ML)' for CARBON IQ, which is a labelled proposal. |
| A1-05 | High | 'Five injected faults all detected' cannot be reproduced | Fixed | Unmodified copy passes; 8 of 8 faults detected. | — |
| A1-06 | High | Excel-agreement tests skip silently in Colab; workbook loses cached values | Fixed | With LibreOffice: 906 formulas, 0 errors, 57 passed. Without LibreOffice (PATH stripped): run_all reports 'skipped', 54 passed, 3 skipped with explicit reasons. | Excel agreement is only tested where LibreOffice is installed (optional apt-get line in Colab). |
| A1-07 | High | Grid emission factor marked 'verified' without a located source | Fixed (label + evidence); source open | test_grid_factor_not_replaced_and_scenario_consistent; scenario E1: target 1,349 t/yr, no decision changes. | Obtain the DNA or SEC primary document and confirm the factor type (A5). |
| A1-08 | High | Industrial electricity tariff band and validity not confirmed | Partly resolved | test_tariff_scenarios_documented, test_tariff_scenarios_rerun_full_analysis; choices of objectives 1 and 3 unchanged in all scenarios; objective 2 becomes B+C if the tariff is certainly 0.18. | Official Saudi Energy 2027 schedule, industrial fixed fees and the 2-halala surcharge applicability not confirmed (A5). |
| A1-09 | High | Activity-data uncertainties hard-coded and not used in the Monte Carlo | Fixed | test_activity_uncertainty_in_register_and_used_by_both_methods; test_stream_one_draws_unchanged_by_new_distributions; effect: EVPI +SAR 31, MC check ±7.502% -> ±7.501%, decisions unchanged. | — |
| A1-10 | High | Capital-cost overrun risk not reported | Fixed | tests: test_joint_budget_constraint_infeasible_and_not_forced, test_minimum_budget_makes_rule_feasible; fault injection detects an ignored budget constraint; validated on 200,000 independent scenarios. | How to resolve the infeasibility (raise budget, relax compliance level, contingency) is a management decision (A1-27). |
| A1-11 | High | Competitor table has no sources, URLs or access dates | Open (deferred to A3) | Text check in the Word report. | Evidence-based benchmarking with per-claim sources and dates. |
| A1-12 | Medium | Deterministic vs Monte Carlo NPV gap not explained | Fixed | test_mean_inputs_use_distribution_means; explanation text in workbook, report and results.json. | — |
| A1-13 | Medium | 'Verified' sources used outside their context | Fixed | test_every_parameter_documented (transferred/provisional need a source link); compare_versions.py lists all 12 relabelled parameters. | — |
| A1-14 | Medium | Workbook and chart builders untested | Fixed | Statement coverage 57% -> 97% (workbook 0% -> 99%, charts 0% -> 93%). | — |
| A1-15 | Medium | Manifest hashes only CSV/JSON | Fixed | Clean re-run reproduced all 21 data files and 9 charts bit for bit (lock-file environment). | — |
| A1-16 | Medium | EVPPI binning error and LSMC trigger noise not quantified | Open (deferred to A6) | — | Bootstrap confidence intervals, bin-count sensitivity, LSMC standard error. |
| A1-17 | Medium | App default 5,000 scenarios vs report 20,000 | Fixed | AppTest runs; screenshot. | — |
| A1-18 | Medium | VOI collection costs typed values; inconsistent solar-capex label | Fixed | Cross-check: linked cost equals SAR 80,000 after recalculation. | — |
| A1-19 | Low | PV self-consumption not checked against load profile | Open (deferred to A5) | — | — |
| A1-20 | Low | UK proxy emission factors | Open (deferred to A5) | — | Saudi or international replacements. |
| A1-21 | Medium | NEW: v1.0 formula count (920) included 24 TRUE/FALSE constants | Fixed | recalc.check on the delivered v1.0 workbook: 896. | — |
| A1-22 | Low | NEW: fixing one input shifted the random draws of all others | Fixed | test_fixed_input_keeps_other_draws_aligned. Only tests used this in v1.0; no published result changed. | — |
| A1-23 | Low | NEW: outputs not bit-identical at the minimum NumPy/SciPy versions | Open (documented) | Largest absolute difference across results.json 3.5e-10 SAR; all decisions and printed figures identical. | Use requirements-lock.txt for bit-identical reproduction. |
| A1-24 | High | NEW: positive expected NPVs rely on the upward-skewed tariff range | Open (documented) | tariff_scenarios.csv (T0). | Revisit the tariff distribution once the 2027 schedule is confirmed (A5/A6). |
| A1-25 | Critical | NEW: carbon chance constraint decided by sampling noise near the 90% threshold | Fixed | A+B: 90.28% in-sample, 89.89% (95% CI 89.76-90.03%) on validation, below 90% on 4 of 5 other samples. Tests test_tightened_chance_constraint_and_validation; fault injection detects a missing margin. | A formal confidence-level choice for the margin (here one-sided 95%) can be reviewed in A6. |
| A1-26 | High | NEW: value-of-information estimator noisy under the new primary rule | Open (deferred to A6) | Dummy-variable EVPPI 269,985 vs 0 under v1.1 rule; motor audit EVPPI 622,481 (352,496 above noise). A pre-posterior MILP variant was tested and found to capture randomisation value, so it was not adopted. | Redesign VOI for chance-constrained rules near the threshold (e.g. larger samples per bin, pre-posterior policy with randomisation baseline). |
| A1-27 | High | NEW: primary rule (90% carbon + 90% budget) infeasible at SAR 5M | Open (management decision) | In-sample (tightened) and validation sample agree; infeasible in all four tariff and both grid-factor scenarios. | Choose: raise budget to about SAR 5.20M, accept about 75% budget compliance (A+C+D 77.8%), or fund a contingency outside the budget. |

## Detail

### A1-01 — Colab instructions do not change into the project folder (Critical; Fixed (simulation); Google Colab run pending)

- **Before (v1.0):** README line 42: !unzip ... && %cd /content/CARBON_IQ. A line starting with ! is passed whole to bash, so %cd is read as a job-control command (fg: no job control) and the working directory does not change (reproduced in IPython 9). The next lines (pip install -r requirements.txt, run_all.py) then run in /content and fail.
- **Proposed fix:** Split into !unzip -q -o CARBON_IQ.zip -d /content and a separate %cd /content/CARBON_IQ line; add a Colab notebook (CARBON_IQ_Colab.ipynb) and a test that executes the README commands with IPython.
- **After (v1.2):** Colab cell rewritten with %cd on its own line; CARBON_IQ_Colab.ipynb added; static test of the README cell.
- **Verification:** README cell executed in IPython in a fresh Python 3.12 venv: unzip, %cd, pip install -r requirements.txt, run_all.py, run_tests.py (57 passed), Streamlit health check 'ok'. Not run on Google Colab itself (no access from this workspace).
- **Remaining:** Run once on Google Colab before submission; the apt-get LibreOffice line was not executed in the simulation.

### A1-02 — Headline recommendation depends on an undisclosed modelling choice (Critical; Fixed)

- **Before (v1.0):** The chance-constrained choice (A+C+D, P(target) 0.980) treats grid emission-factor uncertainty as risk to target compliance. If reductions are counted with the fixed reporting factor (0.55 kg/kWh), as companies normally report them, P(target) for A+B rises from 0.874 to 0.903 and the 90% chance-constrained choice switches to A+B (E[NPV] SAR 1.28M vs 0.69M). The report does not say the recommendation depends on this choice.
- **Proposed fix:** Add a documented reporting_basis option (fixed reporting factor vs uncertain physical factor), report both results side by side, state which one the recommendation uses and why, and add a regression test for both. No change to equations.
- **After (v1.2):** Management decision (25 Oct 2026) applied: carbon chance constraint counts reductions at fixed reporting factors against the fixed reporting baseline (primary). Sampled-factor (S1) and uncertain-baseline (S2) bases reported as sensitivities.
- **Verification:** tests: test_reporting_basis_uses_fixed_factors, test_baseline_uncertainty_basis, test_decision_rules_structure_and_comparisons_preserved; fault injection detects an ignored basis; workbook, app, report and cross-check (144 checks, 0 mismatches) updated.
- **Remaining:** —

### A1-03 — Minimum versions in requirements.txt are too low (High; Fixed)

- **Before (v1.0):** With the stated floors (numpy 1.26, streamlit 1.40) outputs are identical, but the app test fails: pyarrow needs NumPy >= 2, and Streamlit 1.40-1.48 raise TypeError on width="stretch". Streamlit 1.49 and 1.50 pass. No lock file.
- **Proposed fix:** Set numpy>=2.0 and streamlit>=1.49; add requirements-lock.txt with the exact versions of the verified environment (Python 3.12.3).
- **After (v1.2):** Floors: numpy>=2.0, scipy>=1.13, pandas>=2.2.2, openpyxl>=3.1, matplotlib>=3.9, plotly>=5.18, streamlit>=1.49, pytest>=8.0; requirements-lock.txt (Python 3.12.3).
- **Verification:** Python 3.11.17 with exactly the floor versions: run_all OK, 57 passed. Python 3.12.3 with current versions: 57 passed. Static test of the floors.
- **Remaining:** At the floor versions some values differ in the last floating-point digit (max 3.5e-10 SAR); documented (A1-23).

### A1-04 — 'AI-Enabled' in titles although no ML model exists (High; Fixed)

- **Before (v1.0):** README title and Word report subtitle say 'AI-Enabled Carbon Investment Decision Support'. The package contains optimization, Monte Carlo and decision analysis only; no trained model. (The report's competitor table already corrects this to 'planned'.)
- **Proposed fix:** Retitle to 'Carbon Investment Decision Support (optimization and uncertainty analysis)'; keep ML only as a clearly labelled future direction.
- **After (v1.2):** Removed from README, Word report title and app; README, app caption and report state that no machine-learning model is included.
- **Verification:** test_no_ai_or_ml_claims scans README, app and all modules; Word text searched: only the disclaimer and the change table mention the term.
- **Remaining:** Competitor table keeps 'AI analytics: planned (no ML)' for CARBON IQ, which is a labelled proposal.

### A1-05 — 'Five injected faults all detected' cannot be reproduced (High; Fixed)

- **Before (v1.0):** Report Executive summary and Section 7 claim 5 deliberate faults were caught. No fault-injection script is in the package.
- **Proposed fix:** Add tools/fault_injection.py that applies each of the 5 mutations to a temporary copy, runs the tests and records that they fail; store the result in outputs. Otherwise remove the claim.
- **After (v1.2):** tools/fault_injection.py applies 8 faults (5 original + 3 for v1.1 features) to temporary copies and runs the targeted tests; results in outputs/fault_injection.json.
- **Verification:** Unmodified copy passes; 8 of 8 faults detected.
- **Remaining:** —

### A1-06 — Excel-agreement tests skip silently in Colab; workbook loses cached values (High; Fixed)

- **Before (v1.0):** run_all.py and tests use a hard-coded LibreOffice script path (/mnt/skills/...). Simulated Colab run: 37 passed, 2 skipped (Excel agreement not tested); the rebuilt workbook has no cached values; run_all does not report that recalculation was skipped or failed. The report states '0 skipped'.
- **Proposed fix:** Bundle a portable recalc helper (LibreOffice headless, installable in Colab with apt), make run_all print and record the recalc status, and report skipped tests explicitly in test_summary.json.
- **After (v1.2):** carbon_iq/recalc.py (portable LibreOffice); status in outputs/excel_recalc.json; run_all prints it; tests and test_summary.json list skipped tests with reasons; workbook set to recalculate on open.
- **Verification:** With LibreOffice: 906 formulas, 0 errors, 57 passed. Without LibreOffice (PATH stripped): run_all reports 'skipped', 54 passed, 3 skipped with explicit reasons.
- **Remaining:** Excel agreement is only tested where LibreOffice is installed (optional apt-get line in Colab).

### A1-07 — Grid emission factor marked 'verified' without a located source (High; Fixed (label + evidence); source open)

- **Before (v1.0):** assumptions.py: ef_grid status 'verified', while its own note says the SEC table/page was not located.
- **Proposed fix:** Change status to 'unverified (proxy)' now; find an official Saudi source in A5.
- **After (v1.2):** Status provisional. Evidence documented: Saudi DNA 2021 GEF 0.568 tCO2/MWh (cited by KFUPM inventories; primary PDF not retrievable); IFI 2019 combined margins 0.475/0.650 (context only). 0.55 retained, 0.568 run as scenario E1.
- **Verification:** test_grid_factor_not_replaced_and_scenario_consistent; scenario E1: target 1,349 t/yr, no decision changes.
- **Remaining:** Obtain the DNA or SEC primary document and confirm the factor type (A5).

### A1-08 — Industrial electricity tariff band and validity not confirmed (High; Partly resolved)

- **Before (v1.0):** Model uses 0.18 SAR/kWh. ESMAP-hosted SEC tariff table shows 18 halalas for the industrial 1-6,000 kWh band; the >6,000 kWh row is unclear. Al Arabiya (12 Dec 2017) says industrial tariffs were unchanged in the 2018 reform; Argaam (2021) reports 12/18/24 halala categories for electricity-intensive industry. The case plant uses about 1,000 MWh/month.
- **Proposed fix:** Keep 0.18 but mark 'needs confirmation'; obtain the current SEC/ECRA industrial tariff schedule in A5.
- **After (v1.2):** Band question settled: industrial is a flat 0.18 SAR/kWh 2018-2026 (ECRA via Argaam, 13 Dec 2017). Rise to 0.23 from 1 Jan 2027 reported by Attaqa and Saudi Life Guide (25 Oct 2026); rise confirmed without rates by The National. Status provisional; four scenarios (0.18/0.20/0.23/0.26) re-run through all three objectives.
- **Verification:** test_tariff_scenarios_documented, test_tariff_scenarios_rerun_full_analysis; choices of objectives 1 and 3 unchanged in all scenarios; objective 2 becomes B+C if the tariff is certainly 0.18.
- **Remaining:** Official Saudi Energy 2027 schedule, industrial fixed fees and the 2-halala surcharge applicability not confirmed (A5).

### A1-09 — Activity-data uncertainties hard-coded and not used in the Monte Carlo (High; Fixed)

- **Before (v1.0):** engine.EXTRA_ACTIVITY_U (diesel forklifts 5%, gensets 10%, steel 2%, freight 20%) feeds the analytic table but is not in the assumption register and these activities are fixed in the Monte Carlo. The analytic and MC uncertainty use different inputs.
- **Proposed fix:** Move the four values into the assumption register with source and status; either sample them in the MC or document why not; add a test that both methods use the same inputs.
- **After (v1.2):** Moved into the register (same ±% values) and sampled on an independent random stream so v1.0 draws are unchanged.
- **Verification:** test_activity_uncertainty_in_register_and_used_by_both_methods; test_stream_one_draws_unchanged_by_new_distributions; effect: EVPI +SAR 31, MC check ±7.502% -> ±7.501%, decisions unchanged.
- **Remaining:** —

### A1-10 — Capital-cost overrun risk not reported (High; Fixed)

- **Before (v1.0):** Budget constraint is enforced on quoted capex only. In the existing scenarios, A+B exceeds the SAR 4.95M budget in 45.2% of cases (95th percentile SAR 5.63M); A+C+D 22.2%; B+C 0%.
- **Proposed fix:** Add P(capex > budget) and 95th-percentile capex to the Monte Carlo table, app and report; optional chance constraint on budget.
- **After (v1.2):** Management decision applied: joint rule D4 = 90% carbon + 90% budget chance constraints (primary recommendation rule). Both probabilities reported for every portfolio. Infeasible at SAR 5M; minimum budget SAR 5,202,423 (A+C+D), budget curve and alternative-threshold grid reported; no recommendation forced.
- **Verification:** tests: test_joint_budget_constraint_infeasible_and_not_forced, test_minimum_budget_makes_rule_feasible; fault injection detects an ignored budget constraint; validated on 200,000 independent scenarios.
- **Remaining:** How to resolve the infeasibility (raise budget, relax compliance level, contingency) is a management decision (A1-27).

### A1-11 — Competitor table has no sources, URLs or access dates (High; Open (deferred to A3))

- **Before (v1.0):** Report Section 3 reproduces the team's table and says it was not re-verified; no URL or date per claim.
- **Proposed fix:** A3: rebuild the benchmark with one cited public source (URL, publication/access date) per cell; mark unverifiable cells as such.
- **After (v1.2):** Report now states the table is the team's unsourced assessment pending A3.
- **Verification:** Text check in the Word report.
- **Remaining:** Evidence-based benchmarking with per-claim sources and dates.

### A1-12 — Deterministic vs Monte Carlo NPV gap not explained (Medium; Fixed)

- **Before (v1.0):** Deterministic case uses the tariff mode 0.18; Monte Carlo mean is 0.2069. Hence deterministic A+B NPV SAR 0.34M vs expected SAR 1.28M.
- **Proposed fix:** State the reason next to both figures; add a deterministic run at mean values.
- **After (v1.2):** Explanation generated from results next to the objectives; deterministic optimum at mean inputs (A+B, NPV SAR 1.27M) reported.
- **Verification:** test_mean_inputs_use_distribution_means; explanation text in workbook, report and results.json.
- **Remaining:** —

### A1-13 — 'Verified' sources used outside their context (Medium; Fixed)

- **Before (v1.0):** pv_life (KAPSARC offshore study), discount_rate (KAPSARC WACC), gas price $3 anchor (DP49) and tariff are labelled 'verified' although the values were transferred to a different context.
- **Proposed fix:** Add a status level 'sourced - transferred context' and relabel.
- **After (v1.2):** New status 'transferred' for 10 parameters; statuses now: verified, derived, transferred, provisional, hypothetical.
- **Verification:** test_every_parameter_documented (transferred/provisional need a source link); compare_versions.py lists all 12 relabelled parameters.
- **Remaining:** —

### A1-14 — Workbook and chart builders untested (Medium; Fixed)

- **Before (v1.0):** Coverage 57% overall; workbook.py 0%, charts.py 0% (engine 95%, timing 91%, app 100%).
- **Proposed fix:** Add tests that build the workbook and charts in a temp folder and check sheet list, formula count and no error values.
- **After (v1.2):** test_workbook_builder (build, formula count, recalc, live value) and test_chart_builder added.
- **Verification:** Statement coverage 57% -> 97% (workbook 0% -> 99%, charts 0% -> 93%).
- **Remaining:** —

### A1-15 — Manifest hashes only CSV/JSON (Medium; Fixed)

- **Before (v1.0):** manifest.json excludes charts, workbook and report.
- **Proposed fix:** Hash charts too; document why the xlsx/docx are excluded (embedded timestamps) and compare them by content instead.
- **After (v1.2):** Charts hashed; note explains what is compared by hash and by content.
- **Verification:** Clean re-run reproduced all 21 data files and 9 charts bit for bit (lock-file environment).
- **Remaining:** —

### A1-16 — EVPPI binning error and LSMC trigger noise not quantified (Medium; Open (deferred to A6))

- **Before (v1.0):** EVPPI uses 20 bins with a noise floor but no confidence interval; LSMC trigger reported from a grid (range 5.0-8.0) without standard error.
- **Proposed fix:** Bootstrap confidence intervals and bin-count sensitivity for EVPPI; report LSMC standard error and grid step.
- **After (v1.2):** No change in A1.
- **Verification:** —
- **Remaining:** Bootstrap confidence intervals, bin-count sensitivity, LSMC standard error.

### A1-17 — App default 5,000 scenarios vs report 20,000 (Medium; Fixed)

- **Before (v1.0):** app.py default; app figures differ slightly from the report (noted only in a figure caption).
- **Proposed fix:** Show a notice in the app or default to 20,000 with caching.
- **After (v1.2):** Notice in the sidebar whenever fewer than 20,000 scenarios are used.
- **Verification:** AppTest runs; screenshot.
- **Remaining:** —

### A1-18 — VOI collection costs typed values; inconsistent solar-capex label (Medium; Fixed)

- **Before (v1.0):** Value of Information sheet C8, C10-C12 are constants (80,000 / 30,000 / 20,000 / 40,000) while the EVSI row links to a cell. 'Solar capex (formal quotation)' is labelled 'not collectable by the firm', although a firm can obtain a quotation.
- **Proposed fix:** Link costs to the assumption table; relabel solar capex as collectable with a quotation cost.
- **After (v1.2):** Costs linked to the input table; solar-capex row 'cost not estimated'.
- **Verification:** Cross-check: linked cost equals SAR 80,000 after recalculation.
- **Remaining:** —

### A1-19 — PV self-consumption not checked against load profile (Low; Open (deferred to A5))

- **Before (v1.0):** Project A (rooftop PV) savings assume all PV output displaces grid purchases.
- **Proposed fix:** Add an hourly or monthly load check, or state the assumption.
- **After (v1.2):** No change.
- **Verification:** —
- **Remaining:** —

### A1-20 — UK proxy emission factors (Low; Open (deferred to A5))

- **Before (v1.0):** Several factors are UK proxies, labelled as such.
- **Proposed fix:** Replace with Saudi or international (IPCC/IEA) factors where available in A5.
- **After (v1.2):** Now labelled 'transferred'.
- **Verification:** —
- **Remaining:** Saudi or international replacements.

### A1-21 — NEW: v1.0 formula count (920) included 24 TRUE/FALSE constants (Medium; Fixed)

- **Before (v1.0):** Found while implementing the A1 corrections.
- **Proposed fix:** —
- **After (v1.2):** Count excludes LibreOffice's =TRUE()/=FALSE(); v1.0 had 896 formulas, v1.1 has 906; report corrected.
- **Verification:** recalc.check on the delivered v1.0 workbook: 896.
- **Remaining:** —

### A1-22 — NEW: fixing one input shifted the random draws of all others (Low; Fixed)

- **Before (v1.0):** Found while implementing the A1 corrections.
- **Proposed fix:** —
- **After (v1.2):** sample(fixed=...) draws and discards the fixed input's stream-1 values so other inputs are unchanged (common random numbers across tariff scenarios).
- **Verification:** test_fixed_input_keeps_other_draws_aligned. Only tests used this in v1.0; no published result changed.
- **Remaining:** —

### A1-23 — NEW: outputs not bit-identical at the minimum NumPy/SciPy versions (Low; Open (documented))

- **Before (v1.0):** Found while implementing the A1 corrections.
- **Proposed fix:** —
- **After (v1.2):** Documented in README and manifest.
- **Verification:** Largest absolute difference across results.json 3.5e-10 SAR; all decisions and printed figures identical.
- **Remaining:** Use requirements-lock.txt for bit-identical reproduction.

### A1-24 — NEW: positive expected NPVs rely on the upward-skewed tariff range (High; Open (documented))

- **Before (v1.0):** Found while implementing the A1 corrections.
- **Proposed fix:** —
- **After (v1.2):** Disclosed in the report (Section 6.6): with the tariff certainly at 0.18, objective 2 picks B+C (never meets the target) and A+C+D has E[NPV] SAR -17,056.
- **Verification:** tariff_scenarios.csv (T0).
- **Remaining:** Revisit the tariff distribution once the 2027 schedule is confirmed (A5/A6).

### A1-25 — NEW: carbon chance constraint decided by sampling noise near the 90% threshold (Critical; Fixed)

- **Before (v1.0):** Found while implementing the A1 corrections.
- **Proposed fix:** —
- **After (v1.2):** Chance constraints imposed at a sampling-tightened level (0.9035 for 20,000 scenarios) and validated on an independent 200,000-scenario sample; in-sample-only result kept as comparison D3a.
- **Verification:** A+B: 90.28% in-sample, 89.89% (95% CI 89.76-90.03%) on validation, below 90% on 4 of 5 other samples. Tests test_tightened_chance_constraint_and_validation; fault injection detects a missing margin.
- **Remaining:** A formal confidence-level choice for the margin (here one-sided 95%) can be reviewed in A6.

### A1-26 — NEW: value-of-information estimator noisy under the new primary rule (High; Open (deferred to A6))

- **Before (v1.0):** Found while implementing the A1 corrections.
- **Proposed fix:** —
- **After (v1.2):** Noise floor (SAR 269,985) and EVPPI net of it reported; v1.1-rule values kept as comparison; noise-floor line added to the chart.
- **Verification:** Dummy-variable EVPPI 269,985 vs 0 under v1.1 rule; motor audit EVPPI 622,481 (352,496 above noise). A pre-posterior MILP variant was tested and found to capture randomisation value, so it was not adopted.
- **Remaining:** Redesign VOI for chance-constrained rules near the threshold (e.g. larger samples per bin, pre-posterior policy with randomisation baseline).

### A1-27 — NEW: primary rule (90% carbon + 90% budget) infeasible at SAR 5M (High; Open (management decision))

- **Before (v1.0):** Found while implementing the A1 corrections.
- **Proposed fix:** —
- **After (v1.2):** Reported as infeasible; minimum budget, budget curve and risk-threshold grid provided.
- **Verification:** In-sample (tightened) and validation sample agree; infeasible in all four tariff and both grid-factor scenarios.
- **Remaining:** Choose: raise budget to about SAR 5.20M, accept about 75% budget compliance (A+C+D 77.8%), or fund a contingency outside the budget.

## Phase A2 (25 Oct 2026) — problem validation (no model changes)

A1-01 (run on real Google Colab) remains open. A2 items:

| ID | Priority | Issue | Status | Next step |
|---|---|---|---|---|
| A2-01 | High | No interviews conducted yet; H1-H6 unvalidated | Open (requires team action) | Run the interview plan; code results against H-items |
| A2-02 | Medium | Evidence on disclosure comes mainly from listed companies; unlisted manufacturers and SMEs under-represented | Open | Recruit unlisted and SME interviewees; seek SEEC/MIM industrial data |
| A2-03 | Medium | Official Vision 2030, SGI and National Industrial Strategy documents and the BDO and KAPSARC full texts could not be accessed from this workspace | Open | Team to supply PDFs; until then these are cited only via accessible official or press sources |
| A2-04 | Medium | Several sources are regional (PwC n=58, S&P) or international (WEF, Solnørdal & Foss) | Documented limitation | Prefer Saudi-specific evidence as it becomes available |
| A2-05 | Low | 2027 tariff and diesel price from secondary press | Open (carried from A1-08) | Official Saudi Energy schedule (A5) |

## Phase A3 (25 Oct 2026) — competitor benchmark (no model changes)

A1-01 (real Google Colab run) and A2-01 (interviews) remain open. A1-11 (unsourced competitor table) is resolved by the A3 benchmark.

| ID | Priority | Issue | Status | Next step |
|---|---|---|---|---|
| A3-01 | High | No competitor capability could be independently verified; the benchmark rests on vendor public materials | Documented limitation | Request demos or trial access; ask interviewees which tools they use (A2 Q8) |
| A3-02 | Medium | URIMPACT main product site and Remedium product pages not accessible from this workspace | Open | Team to review the sites or request product sheets |
| A3-03 | Medium | Verdantix and IDC analyst reports are paywalled; only vendor-reported summaries used | Documented limitation | Use only as 'publicly advertised' |
| A3-04 | High | Cozero ('optimal path') and IBM Envizi ('run optimization models') advertise optimisation without describing method; overlap with CARBON IQ's portfolio optimisation possible | Open | Demo or documentation request; do not claim optimisation alone as unique |
| A3-05 | Medium | CARBON IQ lacks missing-data detection and estimation, data connectors, supplier engagement, Arabic interface and in-Kingdom hosting that several competitors advertise | Partly addressed by A4 (detection, estimation, calibration and change detection implemented and tested on synthetic data); connectors, supplier engagement, Arabic interface and hosting open | Position as complementary to accounting platforms |

## Phase A4 (25 Oct 2026; refined 26 Oct 2026) — missing-data intelligence (decision model unchanged)

All A4 validation is on synthetic data. Open A1-A3 items above remain open unless stated (A1-01 Colab run still pending; A1-26 now concerns the project-parameter VOI only).

| ID | Priority | Issue | Status | Evidence / next step |
|---|---|---|---|---|
| A4-01 | High | All A4 validation uses synthetic data from our own generator; accuracy on real industrial records unknown | Open (requires real data) | A5 pilot: run the engine on real monthly bills and fuel records, mask known months, report the same metrics |
| A4-02 | Medium | Monthly 95% prediction intervals under-covered (93.3% on the held-out base set) | Fixed for the synthetic generator family: 94.9% (95% CI 94.4%-95.4%) after split-conformal calibration; open for production-change data and real data | Re-fit CAL_MONTHLY on real data (A5) |
| A4-03 | Medium | Annual intervals from the linear (fully correlated) sum were overly wide: 96.9-98.6% coverage on held-out sets | Fixed (synthetic evidence): calibrated within-stream correlation 0.12 (directly estimated 0.13) gives 95.1% on the base set and 94.4-95.3% on the other no-change sets, with 29% narrower intervals | Re-fit on real data |
| A4-04 | Medium | Structural breaks (process or production changes) not detected; estimates after a change biased | Partly fixed: change detection with regime-restricted estimation or refusal; after-change error 17.9% -> 8.9% (energy-use changes); 10% shifts detected in only 17% of cases; changes in the last 1-2 months are not detectable | Reviewer flag for known process changes; real-data test |
| A4-05 | High | Carbon-only rule D3 flips between A+C+D and A+B with ~1% data changes or Monte Carlo resampling (knife-edge, linked to A1-25) | Flagged: stability check in report and dashboard warning; the underlying decision remains fragile | A6: decide how to report D3 when it is unstable |
| A4-06 | Medium | Data value-of-information estimator noisy (binning noise floor, same estimator as A1-26) | Fixed for data VOI: pre-posterior conditioning gives exactly zero value for irrelevant measurements; Monte Carlo variation across seeds remains (A4-14) | — |
| A4-07 | Low | Costs of obtaining missing records are hypothetical (staff time at an assumed SAR 150/h) | Documented | Replace with team estimates |
| A4-08 | Low | Scope limits: monthly granularity, single-site decisions, fixed unit list, no meter-interval data, no Arabic interface | Documented | Extend when real data formats are known (A5) |
| A4-09 | Low | Outlier test flags about 1% of clean synthetic cells (false alarms) - reviewer workload on real data unknown | Documented | Measure on real data |
| A4-10 | Medium | Found and fixed during A4 development: production totals were silently dropped from the activity mapping | Fixed | Tested |
| A4-11 | Medium | Change detection raises false alarms: 0.8% of stream-years with gaps in clean synthetic data (0.4% refused), including the demo's forklift diesel | Documented; reviewer override available and labelled | Measure on real data; reviewer guidance |
| A4-12 | Medium | Intervals under-cover when production shifts mid-year: monthly 93.5%, annual 91.4% | Open (documented) | Production-linked regime model; real-data check |
| A4-13 | Medium | Calibration factors fitted on one synthetic generator family; transfer to real data unproven | Open (requires real data) | Re-run tools/calibrate_a4.py on masked real data (A5) |
| A4-14 | Medium | Information value of electricity records varies strongly across Monte Carlo seeds because of the knife-edge | Documented (sd across seeds reported) | More seeds or larger samples in A6 |

## Phase A5 (26 Oct 2026) — carbon and financial data strengthening (model v1.3)

The facility remains synthetic: no input is a measured factory observation and no cost is a supplier quotation.
Sources, dates, URLs and evidence classes for every input: `outputs/a5/CARBON_IQ_A5_Source_Register.xlsx`.

### Status of earlier items after A5

| ID | Priority | Issue | Status after A5 | Evidence |
|---|---|---|---|---|
| A1-01 | Critical | Run on real Google Colab not confirmed | **Still open** — simulation only; a Google Colab run is still required before submission | No Colab access from this workspace |
| A4-01 | High | No real industrial validation (all validation synthetic) | **Still open** | A5 changed public inputs only; no real facility data were available |
| A1-07 | High | Grid emission factor primary source | Fixed: 0.573 derived from two primary Saudi documents (BTR1, GASTAT 2021); remaining limits in A5-13 | test_grid_factor_derived_from_official_statistics |
| A1-08 | High | Official 2027 industrial tariff schedule | Partly resolved: SPA (25 Oct 2026) confirms an adjustment from 1 Jan 2027; rates not retrieved (A5-01) | T0-T3 scenarios: A+B+C in all |
| A1-19 | Low | PV self-consumption vs load profile | Open: annual check only (PV 1,850 MWh vs 12,000 MWh load); hourly profile not available | Financial notes sheet |
| A1-20 | Low | UK proxy emission factors | Open: no Saudi freight factor found; diesel cross-checked against IPCC (+0.6%) (A5-08) | Register |
| A1-24 | High | Positive E[NPV] relies on upward-skewed tariff range | Open: with the tariff fixed at 0.18, E[NPV] of A+B+C is SAR 1.64M instead of 2.56M; still positive | tariff_scenarios.csv |
| A1-27 | High | D4 infeasible at SAR 5M | Resolved under v1.3 inputs (A+B+C, P(capex <= budget) 98.9%) **only because of the PV cost benchmark**; with the v1.2 PV cost D4 remains infeasible (minimum budget SAR 5.44M) | pv_capex_scenarios.csv, a5_attribution.csv |
| A4-05 | High | D3 knife-edge between A+C+D and A+B | No longer the binding issue: D3 = A+B+C with P(target) 99.99%. New knife-edge: inclusion of C (A5-10); D1 switches to A+B if electricity is 1.4% lower (demo estimates) | stability_rules.csv |
| A4-14 | Medium | Electricity-record VOI noisy across seeds | Under v1.3 the value of every missing record is zero (no decision depends on them) | information_value.csv |
| A1-26, A1-16 | High / Medium | VOI estimator noise | Open (A6). Motor-audit EVSI now 0; C sub-metering EVPPI SAR 36k vs cost SAR 40k | value_of_information.csv |

Other open A1-A4 items above are unchanged.

### New A5 items

| ID | Priority | Issue | Status | Evidence / next step |
|---|---|---|---|---|
| A5-01 | High | Official 2027 industrial tariff schedule not retrieved (23 halalas from secondary sources) | Open | Obtain the SPA/Ministry attachment or SEC schedule; tariff T0-T3 scenarios meanwhile |
| A5-02 | Medium | 2026 regulated methane price not officially published; gas availability for a Riyadh plant unverified | Open | G0-G2 scenarios (no decision change) |
| A5-03 | High | No supplier quotations: capex of B, C, D, E and F hypothetical | Open | Request budget quotations; +/-15% capex uncertainty and budget chance constraint meanwhile. Public cost evidence searched (Cost benchmarks sheet): only an undated US VSD example (order-of-magnitude check of B) |
| A5-04 | High | PV capex rests on one consultancy benchmark, and the recommendation change depends on it | Open | Second benchmark or supplier quotation; P1 scenario reported (D1 A+B, D4 infeasible) |
| A5-05 | Medium | Scope 1 refrigerant (fugitive) emissions not inventoried | Open | Refrigerant top-up records |
| A5-06 | Medium | Scope 3 Cat 3 (T&D losses, upstream fuel) not inventoried; T&D/own-use part indicatively 1,308 t | Open | Saudi T&D loss factor |
| A5-07 | Low | Steel factor is crude-steel only; supplier EPDs not obtained | Open | Supplier EPDs |
| A5-08 | Low | Freight (DESNZ UK) and diesel (IPCC default) factors transferred | Open | Saudi fleet data |
| A5-09 | Low | Forklift kWh per litre (3.5) unsourced; relabelled hypothetical | Fixed (label); value open | Fleet trial or OEM data |
| A5-10 | Medium | Project C marginal (NPV SAR 16.5k; savings switch point at the base value 0.20) | Documented | Sub-metering (EVPPI SAR 36k vs cost SAR 40k) |
| A5-11 | Low | PV inverter replacement and hourly self-consumption not modelled (flatters A) | Open | Supplier O&M offer; load profile |
| A5-12 | Medium | 6% discount rate is a transferred energy-sector WACC; at 8-12% the deterministic choice is A+B, and at 12% NPV is negative | Documented | Company hurdle rate |
| A5-13 | Medium | Grid factor from 2021 data (latest official inventory); SEC-specific factor not publicly retrieved; 1.A.1.a.i may include some heat/desalination co-generation | Documented | E0-E2 scenarios; 5% sd |
| A5-14 | Low | PV yield simulated (utility-scale), not measured rooftop output | Documented | Site study |
| A5-15 | Medium | Found and fixed: v1.2 PV NPV assumed no degradation (overstated by SAR 187k at v1.2 inputs); C had no ongoing cost; MAC used undiscounted tonnes for declining output | Fixed | test_degraded_annuity_and_mac, explicit cash-flow checks (17/17) |
| A5-16 | Medium | Found and fixed: text and analysis hard-coded to the v1.2 result — the objectives explanation called A+B's pass a "sampling artefact" even when it passes validation (v1.3: 93.5%); the first-order variance analysis always contrasted A+B with A+C+D; the app said the 0.55 grid factor was retained | Fixed | Explanation now conditional on the validation result (test_explanation_text_follows_the_validation_result); contrast follows the decision (v1.3: A+B+C vs A+B, 81% of variance from C's savings fraction); app text updated (AppTest) |

## Phase A6 (26 Oct 2026) — independent mathematical and integrated validation (model v1.3)

Checks are labelled independent (separately written code or spreadsheet), benchmark (published value or closed form) or
internal (model vs itself). All data are the synthetic case: none of this is real-world validation.
Details: `docs/CARBON_IQ_A6_Mathematical_Validation_Report.docx`, `outputs/a6/`.

| ID | Priority | Issue | Status | Evidence / next step |
|---|---|---|---|---|
| A6-01 | Medium | Project IRR used constant cash flows and ignored PV degradation (A reported 11.5%; correct 11.0%) | Fixed | `engine.project_irr`; independent Brent root and Excel IRR() agree; test + fault injection |
| A6-02 | High | A NaN input made every NPV NaN and the enumeration silently returned an arbitrary portfolio (MILP raised an unrelated error) | Fixed | `optimize._check_finite` raises a named ValueError; test + fault injection |
| A6-03 | Low | Degraded annuity factor returned n instead of n/(1+r) when r = -d (unrealistic negative rate) | Fixed | Edge tests + fault injection |
| A6-04 | Medium | EVPI requires the target in every scenario (SAR 55.7k); keeping the 90% chance constraint under perfect information gives SAR 74.3k | Documented (definition kept) | The model's EVPI is a lower bound under the chance-constrained reading |
| A6-05 | High | A4 report, A4 workbook note, A4 decision chart, app data-gap table and A4 key portfolios still reflected v1.2 (knife-edge, electricity-bill value, "v1.2 unchanged") | Fixed | A4 study rerun and report regenerated with v1.3; consistency scan |
| A6-06 | Low | A4 validation cells store the uncalibrated s.d. (calibration applied at evaluation); MILP named the empty portfolio ""; timing docstring cited $3 | Fixed / documented | Coverage recomputed: 94.92% with the factor = reported |
| A6-07 | Medium | Monte Carlo inputs are independent; correlations (tariff and gas reforms, capex overruns) not modelled | Open (documented limitation) | Add a correlation structure if real data justify it |
| A6-08 | Low | The 20,000-scenario sample under-represents rare overruns for A+B (P(capex <= budget) 0.9997 vs exact 0.9991) | Documented | No decision effect; the 200,000 validation sample agrees with the closed form |
| A6-09 | Medium | Missing-data engine only modestly better than the mean of measured months on the synthetic generator (MAPE 6.6% vs 7.1%) | Documented | Real-data test (A4-01) |
| A6-10 | Info | Reform decision tree is a prototype (no published validation); LSMC and GBM trigger verified as implementations (published put benchmark 4.468 vs 4.472; trigger = numerical optimum); calibration borrowed from Henry Hub | Documented | — |

Still open from earlier phases and required before submission: **A1-01** (run once on real Google Colab) and **A4-01** (no real
industrial validation — state it in the submission). Source-evidence gaps A5-01 to A5-14 remain open.

## Phase B (26 Oct 2026) — competition package (model unchanged)

| ID | Priority | Issue | Status | Next step |
|---|---|---|---|---|
| B-01 | Medium | The guided demo shows saved outputs; after any register or code change, run_all.py and run_a4.py must be rerun and screenshots recaptured | Documented (pre-flight checklist; tests/test_b.py checks the numbers) | Rerun before the event |
| B-02 | Medium | The traditional baseline is a definition: ranking by NPV gives the same portfolio as CARBON IQ; the advantage shown is against abatement-cost ranking and in quantified confidence | Documented in the package and the demo script | — |
| B-03 | Low | Pilot roadmap durations and acceptance thresholds are proposals, not agreed with a facility | Open | Agree with the first pilot partner |
| B-04 | Low | Pitch slides not prepared (Phase C) | Open | Phase C |

Carried and still required before submission: **A1-01** (real Google Colab run), **A4-01** (no real industrial validation),
A5 source-evidence gaps, A2 interviews (problem hypotheses H1-H6 untested).


## v2 (30 October 2026)

| ID | Priority | Issue | Status | Verification | Remaining |
|---|---|---|---|---|---|
| V2-01 | High | MRC Scope 2: reported 96,671 t implies 0.335 tCO2e/MWh vs the 0.573 national average; method not in the data book; both values are derived, neither independently verified (v2.1 labels) | Open | mrc.implied_grid_factor(); test_mrc_scope1_recalculation_and_implied_grid_factor | Ask MRC/Ma'aden for the Scope 2 factor and method (GHG Reporting Methodology). |
| V2-02 | Medium | MRC energy basis (net or gross calorific value) not stated | Open | Scope 1 recalculation with NCV-based IPCC factors matches within 0.22% | Confirm with Ma'aden. |
| V2-03 | High | MRC investment scenario is hypothetical (sizes, costs, end-use shares, budget, target) | Open (labelled) | mrc.scenario_defaults() kinds; test_no_hypothetical_value_is_labelled_reported | Replace with MRC quotations, roof area, sub-metered end uses and MRC's own target. |
| V2-04 | Medium | Missing-data estimation, VoI and real options not applicable to MRC (annual data only) | By design | Learning Center 'Examples' table | Monthly meter data from MRC. |
| V2-05 | Low | Citations checked by web search, links not opened one by one | Open | tests check URL format only | Open each link before quoting. |
| V2-06 | Medium | Real Google Colab run (A1-01) still not confirmed | Open (carried) | — | Run once on Colab with v2. |
| V2-07 | Medium | MRC scenario choice is a knife-edge (A+B+C needs SAR 69.9M of the hypothetical SAR 70M; 1.4 standard errors) | Flagged in app (v2.1) | test_knife_edge_is_flagged_for_the_default_mrc_scenario | Depends on hypothetical costs and budget; resolve with quotations and MRC's budget. |
| V2-08 | Low | Scope 1 gap of +144 t (+0.22%) unexplained in detail | Explained as far as possible (v2.1) | test_scope1_reconciliation_explains_the_gap | Ma'aden's gas factor would confirm the cause. |
| V2-09 | Low | Pre-existing RuntimeWarning (divide by zero) in dataquality/stability.margins when the budget is so small that no plan is feasible | Open (cosmetic; result is inf, not used) | seen in test_synthetic_app_explains_infeasible_budget_without_raising_it | Left unchanged to avoid modifying validated code. |
