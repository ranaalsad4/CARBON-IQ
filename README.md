# CARBON IQ v2 — Carbon Investment Decision Support (research prototype, model v1.3 unchanged; app v2.1)

## Start here (no programming experience needed)

**What you need:** a computer with Python 3.11 or 3.12 installed (free from https://www.python.org/downloads/ ; on Windows
tick "Add Python to PATH" during installation).

1. Unzip `CARBON_IQ_v2.zip`. You get a folder called `CARBON_IQ`.
2. Open a terminal in that folder:
   - **Windows:** open the `CARBON_IQ` folder in File Explorer, click the address bar, type `cmd` and press Enter.
   - **macOS:** right-click the `CARBON_IQ` folder → *New Terminal at Folder*.
3. Install the packages (once, takes a few minutes):
   ```bash
   python -m pip install -r requirements.txt
   ```
   (On macOS use `python3` instead of `python` if `python` is not found.)
4. Start the app:
   ```bash
   python -m streamlit run app.py
   ```
5. Your browser opens at **http://localhost:8501**. If it does not, copy that address into the browser.
6. To stop the app, go back to the terminal and press `Ctrl + C`.

**Using the app** (left sidebar):
- **Mode** — *Learning Mode* adds a "📘 Learn how this works" section under every major feature; *Presentation Mode*
  hides them for judges. Both modes run exactly the same calculations.
- **Dataset** — the *synthetic* Saudi metal-fabrication plant (all methods; made-up data) or *Ma'aden Rolling Company
  (MRC)* with its 2025 reported energy and emissions (Ma'aden Sustainability Data Book 2025, PDF page 5). Every MRC
  investment number is a labelled **hypothetical** scenario, not a Ma'aden value.
- **Go to** — *Guided demo* (8 steps with Next/Back buttons), *Analysis workspace* (live calculations in numbered steps;
  advanced settings in the sidebar), *Learning Center* (glossary, one page per method, how methods connect, speaking notes,
  references, what the prototype proves).
- Under every major result, "🔎 Source & calculation" shows where each number comes from, whether it is reported,
  calculated, benchmark or hypothetical, its year and company, unit, the Python function that uses it, its uncertainty
  and how it affects the decision.

The guided demo reads the saved model run in `outputs/`, which is included. To regenerate everything:
`python run_all.py` then `python tools/run_a4.py --fast`. To run the tests: `python -m pytest -q`.

Learning guide: `docs/v2/CARBON_IQ_Learning_Guide.docx` (also `.md`). MRC source-to-variable register:
`docs/v2/CARBON_IQ_MRC_Source_Register.xlsx`. What changed in v2: `CHANGELOG.md`. Test results: `docs/v2/TEST_RESULTS.md`.

---

## Technical documentation (Phases A1–B, unchanged in v2)

### CARBON IQ — Carbon Investment Decision Support (research prototype, model v1.3 + A4 missing-data module, mathematically checked in A6)

CARBON IQ turns incomplete operational, energy, supplier and financial data into traceable emissions estimates and
economically justified decarbonization investment recommendations. It is applied to a **hypothetical** medium-sized
metal-fabrication plant in the Riyadh region.

**Status:** research prototype. The facility data are synthetic, and the project costs are illustrative assumptions
anchored to public sources. Outputs are not a verified GHG inventory, not investment advice and not a
production-ready industrial system.

**Methods, not machine learning.** CARBON IQ uses carbon accounting, financial analysis, integer optimisation,
Monte Carlo simulation, value-of-information and real-options analysis. It does **not** contain a trained or validated
machine-learning model, and it should not be described as one.

## What it answers

| Question | Method | Module |
|---|---|---|
| Are the activity data complete and plausible, and what if they are not? | Rule-based checks (units, duplicates, invalid values, robust z-score outliers, missing vs legitimate zeros); statistical gap estimation with leave-one-out prediction intervals and refusal rules; reviewer approval; lineage ledger (A4) | `dataquality/` |
| What are the emissions and how reliable are they? | GHG Protocol accounting; first-order uncertainty propagation, checked by Monte Carlo | `engine.py` |
| Which investments are attractive? | NPV, payback, IRR, marginal abatement cost (SAR/tCO2e) | `engine.py` |
| Which combination fits the budget? | Binary integer program (scipy HiGHS), checked by exhaustive enumeration; compared with ranking rules | `optimize.py` |
| How do uncertainty and data gaps change the answer? | Monte Carlo over 20,000 joint scenarios; three decision objectives; capital-cost risk | `uncertainty.py`, `decisions.py` |
| What information is worth collecting first? | EVPI, EVPPI and EVSI under the same decision rule | `voi.py` |
| Which assumptions drive the answer? | Tornado chart, first-order variance indices, switch points, discount-rate robustness; tariff and grid-factor scenarios | `sensitivity.py`, `decisions.py` |
| Invest now or wait? | Reform decision tree (prototype); KAPSARC DP49-style log-OU least-squares Monte Carlo and GBM closed-form trigger (extension) | `timing.py` |

All inputs, with their value, unit, status (verified, derived, transferred, provisional or hypothetical), evidence class
(external, derived or hypothetical; none measured), source, publication date, effective period, geography and
distribution, are defined in one place: `carbon_iq/assumptions.py`.

## Decision rules

All rules use the same 20,000 scenarios (seed 20261024). The carbon target is counted against the **fixed reporting
baseline** (management decision, 25 Oct 2026); baseline and emission-factor uncertainty are sensitivity scenarios.
Chance constraints are imposed at a sampling-tightened level (0.9035 for 90% with 20,000 scenarios) and validated on an
independent 200,000-scenario sample (seed 20261025).

| ID | Rule | Role |
|---|---|---|
| D1 | max NPV at base inputs, quoted capex ≤ budget, reduction ≥ target | comparison |
| D2 | max E[NPV], quoted capex ≤ budget | comparison |
| D3 | D2 + P(target met) ≥ 90% | carbon-only rule |
| D4 | D3 + P(actual capex ≤ SAR 5M) ≥ 90% | **primary recommendation rule** |
| S1 / S2 | D3 with sampled emission factors / with an uncertain baseline | sensitivity |

If D4 has no feasible portfolio, none is forced: the model reports the minimum budget that makes it feasible, the
budget curve and the choices at alternative risk thresholds (`outputs/minimum_budget.csv`, `budget_curve.csv`,
`risk_thresholds.csv`). Both probabilities (target and budget compliance) are reported for every portfolio.

## Missing-data intelligence (Phase A4, refined 26 Oct 2026)

`carbon_iq/dataquality/` checks monthly activity records (long format: site, period, stream, value, unit), proposes
estimates for gaps and feeds the reviewed annual totals, with their estimation uncertainty, into the unchanged
emissions, Monte Carlo and portfolio engines. All A4 validation uses **synthetic** data.

- **Never zero by default.** Blank, absent or unusable values are *missing*; zeros are accepted only for intermittent or
  lumpy streams or a documented shutdown. Unresolved gaps block the decision.
- **Estimation** (statistical, no machine learning): production intensity, seasonal history, mean of measured months;
  the method with the lowest leave-one-out back-test error is proposed. Refusals: fewer than 6 measured months, more
  than 3 consecutive missing months, back-test error above 25%, no eligible method, or an operational change (below).
- **Operational change detection:** a permutation test (p < 0.01, shift ≥ 10%) on the quantity each method assumes
  constant. After a change, only same-regime months are used; estimation is refused with fewer than 4 such months or
  when the gap sits at the change point. A reviewer may override (labelled in the lineage).
- **Calibrated uncertainty:** 95% prediction intervals widened by a split-conformal factor (1.090) and annual totals
  combined with a calibrated within-stream correlation (0.12), both fitted on synthetic calibration facilities
  (`tools/calibrate_a4.py`) and checked on six held-out synthetic sets. Not yet validated on real data.
- **Decision integration:** estimated parts enter the Monte Carlo; an estimated baseline also makes the 15% target
  uncertain. Complete data reproduce the register-based pipeline exactly (v1.3; v1.2 under its profile).
- **Decision stability** (`stability.py`): margins to every threshold in Monte Carlo standard errors, agreement over
  plausible true datasets, and switch points; the dashboard warns when a rule is unstable (under v1.3 inputs D1 is data-unstable on the demo estimates because project C is marginal; under v1.2 inputs D3 was).
- **Value of information** (`integrate.information_value`): pre-posterior value of collecting each missing record
  under D2, D3 and D4 with hypothetical staff-time costs and net value.
- **Lineage:** the uploaded table is kept unchanged (SHA-256); every estimate, warning, decision and reviewer is logged.

```bash
python tools/calibrate_a4.py      # optional: refit calibration (outputs/a4/calibration.json; ~5 min)
python tools/run_a4.py            # demo, stability, value of information, validation -> outputs/a4/ + CARBON_IQ_A4_Data_Quality.xlsx (~25 min)
python tools/run_a4.py --fast     # quick check (~4 min)
```

The Streamlit tab **Data gaps (A4)** loads the synthetic demo or a CSV, lists findings and warnings, lets a reviewer
decide, and shows a before/after comparison (register, gaps as zero, estimates, records obtained), stability warnings
and the value of collecting each missing record. Report: `docs/CARBON_IQ_A4_Missing_Data_Report.docx`.

## Competition demonstration (Phase B)

The first app tab, **▶ Guided demo**, walks through eight steps (factory → incomplete data → estimates and warnings →
baseline and options → traditional ranking vs CARBON IQ → probabilities → value of information → recommendation). It only
presents the saved, validated outputs of `run_all.py` and `tools/run_a4.py` (no new calculation), so it is reproducible;
`tests/test_b.py` checks that it shows the model's numbers. Script, screenshots and capture script: `docs/phase_b/`.

```bash
python tools/build_phase_b.py        # impact scorecard -> outputs/phase_b/CARBON_IQ_Phase_B_Impact_Scorecard.xlsx
python tools/phase_b_content.py      # demo script (docs/phase_b/demo_script.json, DEMO_SCRIPT.md)
python tools/build_demo_guide.py     # demo guide PDF (needs Playwright + Chromium)
node report/b/report_b.js . CARBON_IQ_Phase_B_Competition_Package.docx
```

## Independent validation (Phase A6)

`independent/indep.py` recomputes the inventory, cash flows, NPV/IRR/payback/MAC, all 64 portfolios and the Monte Carlo
decisions with separately written code (it does not import `carbon_iq`); `tools/run_a6.py` compares it with the model and
with published benchmarks and closed forms; `tools/build_a6_workbook.py` repeats the deterministic chain in spreadsheet
formulas. Everything agrees within numerical or Monte Carlo precision; four minor defects were fixed (see ISSUE_LOG A6).
This is mathematical and synthetic validation, **not** validation on real industrial data.

```bash
python tools/run_a6.py               # ~10 min -> outputs/a6/ (CSV, a6_results.json, charts)
python tools/build_a6_workbook.py    # independent spreadsheet + LibreOffice recalculation
python tools/build_a6_tables.py      # validation tables workbook and charts
python tools/consistency_a6.py       # Python / Excel / Streamlit / Word consistency scan
```

## Install and run (Python 3.11 or 3.12)

```bash
pip install -r requirements.txt          # minimum versions; exact tested versions: requirements-lock.txt
python run_all.py                        # ~30 s, ~1 GB RAM: outputs/ (CSV, JSON, charts) + CARBON_IQ_Data_Model.xlsx
python tools/run_tests.py                # full regression suite -> outputs/test_summary.json
python tools/fault_injection.py          # shows that the tests catch 28 deliberate errors
python tools/build_a5_register.py        # A5 source register and before/after workbooks -> outputs/a5/
streamlit run app.py                     # interactive prototype at http://localhost:8501
```

- `python run_all.py --fast` skips the slower real-options trigger scans.
- The Excel workbook's formulas are recalculated with LibreOffice (`carbon_iq/recalc.py`) when it is installed; the
  result is recorded in `outputs/excel_recalc.json`. Without LibreOffice the two Excel-agreement tests are reported
  as skipped (never silently), and Excel recalculates the file when it is opened.

### Google Colab

Upload `CARBON_IQ.zip` to the Colab file panel (or open `CARBON_IQ_Colab.ipynb`), then run:

```python
!unzip -q -o /content/CARBON_IQ.zip -d /content
%cd /content/CARBON_IQ
!pip install -q -r requirements.txt
!apt-get -qq update > /dev/null && apt-get -qq install -y libreoffice-calc > /dev/null   # optional: Excel formula checks
!python run_all.py
!python tools/run_tests.py
!python tools/run_a4.py --fast
!python tools/run_a6.py emissions finance optimization   # optional: A6 independent checks (fast sections)
!nohup streamlit run app.py --server.port 8501 --server.headless true > st.log 2>&1 &
from google.colab.output import eval_js; print(eval_js("google.colab.kernel.proxyPort(8501)"))
```

`%cd` must be on its own line: in a line that starts with `!` the whole line goes to the shell, so a `%cd` after
`&&` is not executed (this was the v1.0 bug).

## Reproducing results

- All results are deterministic for a given seed: Monte Carlo seed 20261024, LSMC seed 2026. Distributions added
  in v1.1 use an independent random stream, so the v1.0 draws of every other input are unchanged.
- `outputs/manifest.json` lists SHA-256 hashes of every data output (and of the charts, which depend on the
  matplotlib version); `tests/test_outputs.py` checks reproducibility. Hashes match exactly on repeated runs and in
  the `requirements-lock.txt` environment; at the minimum versions (NumPy 2.0, Python 3.11) the last floating-point
  digit of some values differs (largest absolute difference found: below 1e-9 SAR), with identical decisions and figures.
- `tests/test_outputs.py` recalculates the workbook and checks that its live Excel formulas equal the Python
  engine (baseline, uncertainty, NPVs, NPV() cash flows, the 64-portfolio optimum, decision objectives, decision tree
  and GBM trigger).
- `tools/crosscheck.py` compares Python, Excel and the Word report figure by figure; `tools/compare_versions.py`
  lists every changed assumption and its effect on the results.

## Key results (synthetic case, model v1.3 — illustrative, not advice)

| Item | Value |
|---|---|
| Baseline emissions | Scope 1 2,178 · Scope 2 6,876 · Scope 3 11,723 tCO2e/yr; Scope 1+2 ±7.7% (95%); target 1,358 t/yr |
| D1 Deterministic optimum | A+B+C (solar + motors + compressed air): NPV SAR 1.56M at base inputs, 1,755 t/yr |
| D2 Highest expected NPV | A+B+C: E[NPV] SAR 2.56M |
| D3 Carbon ≥90% (validated) | A+B+C: target met 99.99% (validation 99.996%) |
| **D4 Carbon ≥90% + budget ≥90% (primary)** | **A+B+C, feasible at SAR 5M**: within budget 98.9% (validation 98.8%); quoted capex SAR 4.05M |
| What drives the change from v1.2 | The Riyadh rooftop-PV cost benchmark (SAR 2,500/kWp). With the v1.2 PV cost (3,750) D1 is A+B and D4 is infeasible (needs SAR 5.44M) |
| Fragility | C is marginal (NPV SAR 16.5k); at discount rates of 8–12% the deterministic choice is A+B |
| Industrial tariff | 0.18 SAR/kWh 2018–2026 (reference); adjustment from 1 Jan 2027 officially announced, 0.23 reported (rates not retrieved); A+B+C in all four tariff scenarios |
| Grid emission factor | 0.573 tCO2e/MWh derived from the KSA BTR1 (2021 inventory) and GASTAT 2021 generation |
| Information value | EVPI SAR 56k; motor audit EVSI 0; compressed-air sub-metering EVPPI SAR 36k vs cost SAR 40k |
| Heat-recovery timing | Wait for the gas-price decision (investing now: NPV −SAR 220k) |

v1.2 results remain reproducible with `assumptions.use_profile("v1.2")`; `outputs/a5_attribution.csv` shows the effect
of each A5 change alone. A5 deliverables: `outputs/a5/` (source register, before/after comparison) and
`docs/CARBON_IQ_A5_Carbon_Financial_Methodology.docx`.

**Validated** = calculations, Python/Excel/Word agreement, reproducibility, injected-fault detection and out-of-sample
feasibility of the reported choices. **Illustrative** = everything that depends on the synthetic facility data,
judgement-based ranges, and the unconfirmed tariff and grid factor.

## Folder

```
carbon_iq/        engines (assumptions, engine, optimize, uncertainty, decisions, voi, sensitivity, timing, pipeline,
                  charts, workbook, recalc); dataquality/ (quality, estimate, integrate, stability, synth, validate, workbook_a4)
run_all.py        end-to-end run      app.py   Streamlit interface      tests/   pytest suite
tools/            run_tests.py, fault_injection.py, crosscheck.py, compare_versions.py, calibrate_a4.py, run_a4.py,
                  build_a5_register.py, run_a6.py, build_a6_workbook.py, build_a6_tables.py, consistency_a6.py
independent/      separately written re-implementation used by A6 (does not import carbon_iq)
report/           build.js + lib.js: regenerate the Word report (node, npm package "docx")
outputs/          CSV tables, results.json, manifest.json, test_summary.json, fault_injection.json, charts/*.png
outputs/phase_b/  Phase B impact scorecard and trace check
outputs/a6/       A6 validation results, independent workbook, validation tables, charts
outputs/a5/       A5 source register, before/after comparison, a5_summary.json
outputs/a4/       A4 demo, lineage, decision comparison, data VOI, validation study, charts
docs/             A2-A6 reports and matrices; docs/phase_b/ demo script, screenshots, architecture diagram
docs/v2/          v2 learning guide (.docx/.md), MRC source register (.xlsx/.csv), methods diagram, test results
carbon_iq/mrc.py  v2 MRC case study (reported data, recalculation checks, hypothetical scenario on the unchanged engine)
carbon_iq/learning.py   v2 learning content for every method (status, 7 elements, code references)
carbon_iq/ui/     v2 interface helpers: theme, learning/source panels, MRC screens, Learning Center
.streamlit/       v2 colour theme
CARBON_IQ_Data_Model.xlsx   CARBON_IQ_A4_Data_Quality.xlsx   CARBON_IQ_Complete_Project.docx   CARBON_IQ_Colab.ipynb   CHANGELOG.md   ISSUE_LOG.md
```
