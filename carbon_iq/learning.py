"""v2 - learning content for every CARBON IQ method (used by the Learning Mode panels, the Learning Center and the
learning guide). Pure data: nothing here calculates. tests/test_v2.py checks that every code reference points to a
function that exists, so the explanations cannot drift away from the code silently.

status: "Fully implemented" | "Partially implemented" | "Not implemented" - judged from the code, not from intentions.
code:   list of (file, function, what goes in, what comes out). Function names are the real ones.
"""

STATUS_FULL, STATUS_PART, STATUS_NONE = "Fully implemented", "Partially implemented", "Not implemented"

R = {   # references (checked by web search, 28-30 Oct 2026; open the link before quoting)
    "ghgp": ("WRI & WBCSD (2004). The Greenhouse Gas Protocol: A Corporate Accounting and Reporting Standard, revised edition.",
             "https://ghgprotocol.org/corporate-standard"),
    "ipcc_v2": ("IPCC (2006). 2006 IPCC Guidelines for National Greenhouse Gas Inventories, Vol. 2 Energy, Ch. 2 Stationary Combustion.",
                "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf"),
    "ipcc_unc": ("IPCC (2006). 2006 Guidelines, Vol. 1, Ch. 3 Uncertainties (Approach 1: error propagation; Approach 2: Monte Carlo).",
                 "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/1_Volume1/V1_3_Ch3_Uncertainties.pdf"),
    "gum": ("JCGM 100:2008. Evaluation of measurement data - Guide to the Expression of Uncertainty in Measurement (GUM). BIPM.",
            "https://www.bipm.org/en/doi/10.59161/JCGM100-2008E"),
    "rubin": ("Rubin, D. B. (1976). Inference and missing data. Biometrika 63(3), 581-592.", "https://doi.org/10.1093/biomet/63.3.581"),
    "littlerubin": ("Little, R. J. A. & Rubin, D. B. (2019). Statistical Analysis with Missing Data, 3rd ed. Wiley.",
                    "https://doi.org/10.1002/9781119482260"),
    "vovk": ("Vovk, V., Gammerman, A. & Shafer, G. (2005). Algorithmic Learning in a Random World. Springer (conformal prediction).",
             "https://doi.org/10.1007/b106715"),
    "metropolis": ("Metropolis, N. & Ulam, S. (1949). The Monte Carlo method. Journal of the American Statistical Association 44(247), 335-341.",
                   "https://doi.org/10.1080/01621459.1949.10483310"),
    "charnes": ("Charnes, A. & Cooper, W. W. (1959). Chance-constrained programming. Management Science 6(1), 73-79.",
                "https://doi.org/10.1287/mnsc.6.1.73"),
    "pagnoncelli": ("Pagnoncelli, B. K., Ahmed, S. & Shapiro, A. (2009). Sample average approximation method for chance constrained "
                    "programming. J. Optimization Theory and Applications 142, 399-416.", "https://doi.org/10.1007/s10957-009-9523-6"),
    "howard": ("Howard, R. A. (1966). Information value theory. IEEE Transactions on Systems Science and Cybernetics 2(1), 22-26.",
               "https://doi.org/10.1109/TSSC.1966.300074"),
    "raiffa": ("Raiffa, H. & Schlaifer, R. (1961). Applied Statistical Decision Theory. Harvard Business School (book; no free link).", ""),
    "greenbook": ("HM Treasury (2022). The Green Book: appraisal and evaluation in central government.",
                  "https://www.gov.uk/government/publications/the-green-book-appraisal-and-evaluation-in-central-government"),
    "kesicki": ("Kesicki, F. & Ekins, P. (2012). Marginal abatement cost curves: a call for caution. Climate Policy 12(2), 219-236.",
                "https://ideas.repec.org/a/taf/tcpoxx/v12y2012i2p219-236.html"),
    "landdoig": ("Land, A. H. & Doig, A. G. (1960). An automatic method of solving discrete programming problems. Econometrica 28(3), 497-520.",
                 "https://doi.org/10.2307/1910129"),
    "lorie": ("Lorie, J. H. & Savage, L. J. (1955). Three problems in rationing capital. Journal of Business 28(4), 229-239.",
              "https://ideas.repec.org/r/ucp/jnlbus/v28y1955p229.html"),
    "keeney": ("Keeney, R. L. & Raiffa, H. (1976). Decisions with Multiple Objectives: Preferences and Value Tradeoffs. Wiley "
               "(Cambridge University Press edition 1993).", "https://doi.org/10.1017/CBO9781139174084"),
    "saltelli": ("Saltelli, A. et al. (2008). Global Sensitivity Analysis: The Primer. Wiley.", "https://doi.org/10.1002/9780470725184"),
    "sobol": ("Sobol, I. M. (2001). Global sensitivity indices for nonlinear mathematical models and their Monte Carlo estimates. "
              "Mathematics and Computers in Simulation 55, 271-280.", "https://doi.org/10.1016/S0378-4754(00)00270-6"),
    "myers": ("Myers, S. C. (1977). Determinants of corporate borrowing. Journal of Financial Economics 5(2), 147-175.",
              "https://doi.org/10.1016/0304-405X(77)90015-0"),
    "dixit": ("Dixit, A. K. & Pindyck, R. S. (1994). Investment under Uncertainty. Princeton University Press.",
              "https://ideas.repec.org/b/pup/pbooks/5474.html"),
    "lsmc": ("Longstaff, F. A. & Schwartz, E. S. (2001). Valuing American options by simulation: a simple least-squares approach. "
             "Review of Financial Studies 14(1), 113-147.", "https://doi.org/10.1093/rfs/14.1.113"),
    "iso31000": ("ISO 31000:2018. Risk management - Guidelines. International Organization for Standardization.",
                 "https://www.iso.org/standard/65694.html"),
    "maaden": ("Ma'aden (2026). Sustainability Data Book 2025 (file supplied by the user; MRC figures on PDF page 5).", ""),
}

METHODS = [
    dict(
        key="ghg", title="Scope 1 and Scope 2 emissions accounting", status=STATUS_FULL,
        status_note="Scope 1 and Scope 2 (location-based) fully; Scope 3 only for purchased steel and inbound freight.",
        what="Turns energy and fuel records into tonnes of CO2-equivalent (tCO2e). Scope 1 is fuel burned on site, Scope 2 is "
             "purchased electricity, Scope 3 is the supply chain.",
        origin="The GHG Protocol Corporate Standard by the World Resources Institute (WRI) and the World Business Council for "
               "Sustainable Development (WBCSD), 2001, revised 2004, defined the three scopes. Default emission factors come from the "
               "IPCC 2006 Guidelines.", refs=["ghgp", "ipcc_v2"],
        why="Everything else - the target, project savings, probabilities - is counted in tonnes. A wrong baseline makes every "
            "later answer wrong.",
        how=["Collect yearly activity data (MWh of electricity, GJ of gas, litres or GJ of diesel).",
             "Multiply each by its emission factor (tCO2e per unit).",
             "Add the results by scope; the target is a share of Scope 1+2."],
        example="Synthetic plant: 12,000 MWh × 0.573 tCO2e/MWh = 6,876 t (Scope 2). MRC: 1,104,220 GJ of gas × 0.05615 tCO2e/GJ "
                "= 62,007 t, most of its reported Scope 1 (63,961 t).",
        code=[("carbon_iq/engine.py", "baseline", "parameter set p (activities and factors from assumptions.P)",
               "one row per source: activity, factor, tCO2e, scope"),
              ("carbon_iq/engine.py", "scope_totals", "rows from baseline()", "Scope 1, 2, 3, 1+2 and total"),
              ("carbon_iq/engine.py", "target_t", "p (target_share)", "target in tCO2e/yr"),
              ("carbon_iq/mrc.py", "scope1_recalc", "MRC reported fuel GJ", "recalculated Scope 1 vs the reported value")],
        judges="We start by measuring. Each energy record is multiplied by an official emission factor - for example 0.573 tonnes "
               "per megawatt-hour for the Saudi grid - and grouped into the GHG Protocol scopes. For Ma'aden Rolling, recalculating "
               "Scope 1 from its reported fuel use with IPCC factors lands within 0.3% of the figure Ma'aden reports.",
        advanced="Scope 2 is location-based (grid average). Market-based Scope 2 (contract-specific factors) is not implemented. "
                 "GWPs are IPCC AR5 (CH4 28, N2O 265), as in Saudi Arabia's national inventory."),
    dict(
        key="factors", title="Emission factors and unit conversions", status=STATUS_FULL,
        status_note="All factors and conversions are in one register with source, date and status.",
        what="An emission factor says how much CO2e one unit of activity produces. Unit conversions make sure the activity and the "
             "factor use the same unit (GJ vs MWh, USD/MMBtu vs SAR/GJ).",
        origin="Factor methodology: IPCC 2006 Guidelines. Saudi grid factor derived from Saudi Arabia's First Biennial Transparency "
               "Report (UNFCCC, 2025) and GASTAT 2021 generation. 1 MWh = 3.6 GJ is a definition.", refs=["ipcc_v2"],
        why="Most errors in carbon tools are unit errors. A factor in tCO2e per MWh applied to GJ gives an answer 3.6 times too big.",
        how=["Store every factor once, with unit, source and uncertainty (assumptions.P).",
             "Convert the activity to the factor's unit before multiplying.",
             "For gas prices, convert USD per MMBtu to SAR per GJ (× 3.75 SAR/USD ÷ 1.055 GJ/MMBtu)."],
        example="MRC electricity 1,040,392 GJ ÷ 3.6 = 288,998 MWh. Gas price USD 2.15/MMBtu × 3.75 ÷ 1.055 = SAR 7.64/GJ.",
        code=[("carbon_iq/mrc.py", "fuel_factor_t_per_gj", "fuel name", "IPCC CO2e factor in tCO2e/GJ"),
              ("carbon_iq/mrc.py", "gj_to_mwh", "GJ", "MWh"),
              ("carbon_iq/assumptions.py", "gas_price_sar_per_gj", "USD/MMBtu", "SAR/GJ"),
              ("carbon_iq/assumptions.py", "add", "key, value, unit, status, source, distribution", "one entry in the register P")],
        judges="Every emission factor sits in one register with its unit, source, year and uncertainty. Before multiplying, CARBON IQ converts the units - Ma'aden reports electricity in gigajoules, so we divide by 3.6 to get megawatt-hours. Getting the unit wrong is the most common carbon-accounting error, and the register makes every conversion visible.",
        advanced="IPCC factors are per GJ of net calorific value. The Ma'aden data book does not say whether its GJ are net or "
                 "gross; the close Scope 1 match suggests net, but that is an inference, not a fact."),
    dict(
        key="uncertainty", title="Uncertainty propagation (error propagation)", status=STATUS_FULL,
        status_note="First-order rule per GHG Protocol / IPCC Approach 1; Monte Carlo (Approach 2) as a cross-check.",
        what="Works out how the uncertainty of each meter and factor adds up to the uncertainty of the total, as ± percent at 95% "
             "confidence.",
        origin="Combination rules from the theory of errors (Gauss, Laplace, early 1800s), standardised in the GUM (JCGM 100:2008) and "
               "adopted as 'Approach 1' in the IPCC 2006 Guidelines.", refs=["gum", "ipcc_unc"],
        why="Without a range, 9,054 t looks exact. Management needs to know how much safety margin a target needs.",
        how=["Give every input a ± percent (95%).", "For activity × factor: U = √(U_activity² + U_factor²).",
             "For a sum of sources, combine the ± tonnes the same way; big uncertain sources dominate."],
        example="Electricity ±2%, grid factor ±9.8% → √(4 + 96) ≈ ±10%. MRC Scope 1 recalculation: ±4.0% (assuming ±2% metering).",
        code=[("carbon_iq/engine.py", "uncertainty_table", "baseline rows", "± % per source and per scope"),
              ("carbon_iq/engine.py", "u_mult", "± percents of a product", "combined ± percent"),
              ("carbon_iq/engine.py", "u_add", "(tonnes, ± percent) pairs", "± percent of the sum")],
        judges='Every number has a margin of error. Our electricity meter might be 2% off, but the national grid factor is uncertain by almost 10%, so the factor - not the meter - drives the uncertainty. We report 9,054 tonnes plus or minus 7.7%, instead of pretending the footprint is exact.',
        advanced="Valid for independent errors below roughly 30%; the code flags sources where it is not (freight ±36%)."),
    dict(
        key="reconcile", title="Reconciling recalculated and reported emissions", status=STATUS_FULL,
        status_note="Implemented for MRC (v2.1): Scope 1 recalculated from reported fuel use with IPCC factors and the difference "
                    "explained; the Scope 2 factor implied by the report compared with the national average.",
        what="Recalculates a company's reported emissions from its own reported activity data and explains any difference.",
        origin="GHG Protocol quality-management guidance (Corporate Standard, ch. 7) and IPCC default factors and uncertainty ranges.",
        refs=["ghgp", "ipcc_v2", "ipcc_unc"],
        why="Before building a decision on a company's baseline, check that it is consistent - and know which parts cannot be checked.",
        how=["Multiply each reported fuel (GJ) by its IPCC factor and add up.", "Compare with the reported Scope 1; express the "
             "difference as a share of the recalculation's uncertainty.", "Back-calculate the Scope 2 factor (Scope 2 ÷ MWh) and "
             "compare it with independent factors - remembering that a back-calculated factor is derived, not verified."],
        example="MRC: 64,105 t recalculated vs 63,961 t reported (+144 t, +0.22%); the 95% uncertainty is ±2,535 t, so the two agree. "
                "A gas factor 0.23% below the IPCC default would close the gap exactly.",
        code=[("carbon_iq/mrc.py", "scope1_reconciliation", "reported fuel GJ and Scope 1", "gap, its share of the uncertainty, tests of possible causes"),
              ("carbon_iq/mrc.py", "scope1_recalc", "reported fuel GJ", "recalculated Scope 1 with ± uncertainty"),
              ("carbon_iq/mrc.py", "grid_factor_comparison", "reported Scope 2 and electricity", "implied vs national vs verified factor")],
        judges="We tested Ma'aden Rolling's reported Scope 1 by recalculating it from its fuel use. We are within 144 tonnes - 0.2% - "
               "well inside the uncertainty. For Scope 2 the report implies a grid factor of 0.335, far below the national 0.573; "
               "that is a derived number, not a verified one, so it is our first question to the company.",
        advanced="AR4 or AR6 greenhouse-gas weights change the recalculation by under 4 t; gross instead of net heating values would "
                 "lower it by about 10%, which would no longer match."),
    dict(
        key="dataquality", title="Data quality checks and missing-data estimation", status=STATUS_FULL,
        status_note="Fully implemented and tested on synthetic data only; not applicable to MRC (no monthly data published).",
        what="Checks monthly records for gaps, duplicates, unit errors and outliers, then estimates missing months with a stated range "
             "- never treating missing data as zero.",
        origin="Missing-data theory from Rubin (1976) and Little & Rubin; prediction intervals calibrated with split-conformal "
               "prediction (Vovk et al., 2005).", refs=["rubin", "littlerubin", "vovk"],
        why="Counting a missing month as zero hides emissions: in the synthetic demo it hides 25% of Scope 1+2 and changes the plan.",
        how=["Check every record (units, duplicates, invalid values, robust z-score outliers, suspicious zeros).",
             "Estimate each gap with the method that back-tests best: seasonal history, production intensity or monthly mean.",
             "Attach a 95% interval, refuse long gaps (> 3 months) or unstable data, and require reviewer approval."],
        example="March missing; March last year 980 MWh; this year runs 3% higher → 980 × 1.03 ≈ 1,009 MWh ± a back-tested range.",
        code=[("carbon_iq/dataquality/quality.py", "assess", "raw monthly records, year, site", "cells with status and issues"),
              ("carbon_iq/dataquality/estimate.py", "propose", "cells (and previous year)", "estimates, intervals, refusals, warnings"),
              ("carbon_iq/dataquality/estimate.py", "Ledger", "raw records", "audit trail, reviewer decisions, annual totals"),
              ("carbon_iq/dataquality/integrate.py", "run_decisions", "annual activity with standard deviations", "the decision rules' choices")],
        judges="Real data always have holes. If you count a missing bill as zero, our test plant's footprint drops by a quarter and "
               "the plan changes. CARBON IQ estimates each gap from the plant's own history, shows how wrong it could be, and needs "
               "a person to approve it.",
        advanced="Calibration factor 1.0898 and within-stream correlation 0.12 were fitted on synthetic facilities and must be re-fitted "
                 "on real records."),
    dict(
        key="montecarlo", title="Monte Carlo simulation", status=STATUS_FULL,
        status_note="Synthetic plant: 20,000 scenarios + 200,000 for validation. MRC: same distributions, reporting basis.",
        what="Runs the plan through thousands of randomly drawn futures (prices, savings, costs) to see the full range of outcomes.",
        origin="Developed at Los Alamos by Ulam, von Neumann and Metropolis (1946-49); first paper Metropolis & Ulam (1949). The IPCC "
               "calls it 'Approach 2' for inventory uncertainty.", refs=["metropolis", "ipcc_unc"],
        why="A single best guess hides risk. Management needs to know how often a plan could miss the target or the budget.",
        how=["Give each uncertain input a distribution (e.g. compressed-air savings uniform 10-30%).",
             "Draw one value of every input and compute cost, tonnes and NPV - one future.",
             "Repeat many times and count: averages, percentiles, probabilities."],
        example="Recommended plan A+B+C: average NPV SAR 2.56M over 20,000 futures; it loses money in 0.11% of them (22 of 20,000).",
        code=[("carbon_iq/uncertainty.py", "sample", "n, seed (distributions from assumptions.P)", "n joint values of every input"),
              ("carbon_iq/uncertainty.py", "Scenarios", "sampled parameters", "NPV, tonnes and cost of all 64 portfolios per scenario"),
              ("carbon_iq/decisions.py", "validation_sample", "n = 200,000, separate seed", "independent check of the probabilities"),
              ("carbon_iq/mrc.py", "monte_carlo", "MRC parameter set", "probabilities for the 16 MRC portfolios")],
        judges="The future is uncertain, so we don't trust a single forecast. CARBON IQ plays out 20,000 possible futures with different tariffs, savings and costs, and records what happens to every plan. The recommended plan lost money in about one future in nine hundred - a measured probability, not a feeling.",
        advanced="Inputs are drawn independently (no correlation between prices). More runs make the answer precise, not correct."),
    dict(
        key="ptarget", title="Probability of meeting emissions targets (chance constraints)", status=STATUS_FULL,
        status_note="Carbon and budget chance constraints, sample-average approximation, tightened for sampling error.",
        what="A rule that accepts only plans meeting the carbon target - and staying within budget - in at least, say, 90% of "
             "simulated futures.",
        origin="Chance-constrained programming by Charnes & Cooper (1959); scenario-based solution (sample average approximation) "
               "studied by Pagnoncelli, Ahmed & Shapiro (2009).", refs=["charnes", "pagnoncelli"],
        why="'Meets the target on average' can mean failing half the time. This turns management's risk appetite into a test.",
        how=["Management sets confidence levels (90% carbon, 90% budget).",
             "For every plan count the share of futures meeting the target and the budget.",
             "Keep plans passing both; choose the highest expected NPV (rule D4)."],
        example="A+B meets the target in the single best guess but only in 93.5% of futures; A+B+C in more than 99.99% and within "
                "budget in 98.8% → chosen.",
        code=[("carbon_iq/uncertainty.py", "Scenarios.decide", "budget, target, alpha, budget reliability", "chosen portfolio and probabilities"),
              ("carbon_iq/uncertainty.py", "alpha_saa", "required level, number of scenarios", "tightened level (0.9035 for 90%, n = 20,000)"),
              ("carbon_iq/decisions.py", "choose", "portfolio probabilities, budget, levels", "index of the qualifying max-E[NPV] portfolio")],
        judges='Management told us: we want at least 90% confidence of hitting the carbon target and 90% confidence of staying on budget. CARBON IQ applies exactly that rule to every plan. The recommended plan met the target in more than 99.99% of simulated futures and stayed on budget in 98.8% - modelled, not guaranteed.',
        advanced="If no plan qualifies, none is forced; the model reports the minimum budget that would make the rule feasible."),
    dict(
        key="budget", title="Budget feasibility and minimum budget", status=STATUS_FULL,
        status_note="When no plan meets the rules, nothing is forced and the budget is never raised automatically; the model reports "
                    "why, and the smallest budget that would make the rule feasible under its assumptions.",
        what="Checks whether any plan can meet the target within the budget - and, if not, how much budget would be needed.",
        origin="Chance-constrained programming (Charnes & Cooper, 1959) evaluated on simulated scenarios (Pagnoncelli et al., 2009).",
        refs=["charnes", "pagnoncelli"],
        why="A tool that quietly raises the budget until a plan works hides the real trade-off. Management must see it and decide.",
        how=["For each plan that meets the carbon rule, find the actual cost it stays under in 90% of futures (its 90th-percentile cost).",
             "The plan's budget need is the larger of that cost and its quoted cost.", "The smallest need over all plans is the "
             "minimum feasible budget; if no plan meets the carbon rule, the target is out of reach at any budget."],
        example="Synthetic plant: at a solar cost of SAR 3,750/kWp no plan passes both 90% rules within SAR 5M; the minimum budget is "
                "SAR 5.44M. MRC scenario: A+B+C needs SAR 69.9M of the SAR 70M budget.",
        code=[("carbon_iq/decisions.py", "_min_budget", "scenarios, probabilities, required levels", "smallest feasible budget"),
              ("carbon_iq/decisions.py", "budget_analysis", "scenarios, target, levels, budget", "budget curve and needs per plan"),
              ("carbon_iq/mrc.py", "budget_feasibility", "MRC parameters and simulation", "deterministic and probabilistic minimum budgets")],
        judges="If no plan fits, CARBON IQ does not quietly raise the budget. It says why, and what the minimum budget would be under its "
               "assumptions - for example 5.44 million riyals if solar costs 50% more. Whether to spend it is management's decision.",
        advanced="The minimum budget uses the same sampling-tightened level as the decision rule (0.9035 for 90% with 20,000 futures)."),
    dict(
        key="evpi", title="Expected Value of Perfect Information (EVPI)", status=STATUS_FULL,
        status_note="Implemented for the synthetic plant; A6 showed it is a lower bound when the confidence rules bind. Not run for MRC.",
        what="The most you should ever pay for information before deciding: the gain if every uncertainty were known in advance.",
        origin="Bayesian decision theory: Raiffa & Schlaifer (1961); named 'information value theory' by Howard (1966).",
        refs=["howard", "raiffa"],
        why="It caps the budget for studies. If EVPI is small, more studies cannot improve the decision much.",
        how=["Value of deciding now = expected NPV of today's best plan.",
             "For each scenario, imagine you knew it and picked the best plan for it.",
             "EVPI = average of those best values − value of deciding now."],
        example="Synthetic plant: EVPI ≈ SAR 55,670, small next to the plan's expected NPV of SAR 2.56M.",
        code=[("carbon_iq/voi.py", "evpi", "scenarios, budget, target, required probability", "EVPI in SAR")],
        judges='Before spending millions, we ask what a perfect crystal ball would be worth - knowing every uncertain number in advance. For our test plant it is about 56,000 riyals, tiny next to a 2.5-million-riyal expected value. So no study, however good, can change much here: the decision is ready to be taken.',
        advanced="Under the chance-constraint rule, the perfect-information benchmark can be defined two ways; A6 found the coded one "
                 "is the lower bound (alternative SAR 74,267)."),
    dict(
        key="voi", title="Value of Information (EVPPI and EVSI)", status=STATUS_FULL,
        status_note="EVPPI for 8 candidate measurements, EVSI for a motor audit, pre-posterior VoI for data gaps (A4). Not run for MRC.",
        what="Prices one specific piece of information - perfect (EVPPI) or from a real, imperfect measurement (EVSI) - by asking "
             "whether it could change the decision.",
        origin="Same Bayesian decision theory as EVPI (Raiffa & Schlaifer 1961; Howard 1966).", refs=["howard", "raiffa"],
        why="Sub-meters, audits and supplier data cost money. Only information that can change the choice is worth buying.",
        how=["Group the scenarios by the value of one input (20 groups).",
             "In each group find the best plan; average those values.",
             "Subtract the value of deciding now; compare with the collection cost."],
        example="Compressed-air sub-metering: EVPPI SAR 35,954 vs assumed cost SAR 40,000 → not quite worth it. Motor audit: EVSI 0.",
        code=[("carbon_iq/voi.py", "evppi", "scenarios, one input's values", "value of resolving that input"),
              ("carbon_iq/voi.py", "evsi_audit", "scenarios, audit error", "value of an imperfect audit"),
              ("carbon_iq/voi.py", "ranking", "scenarios", "all candidate measurements, values and costs"),
              ("carbon_iq/dataquality/integrate.py", "information_value", "activity with gaps", "value of collecting missing records")],
        judges='Not all missing information is worth buying. Of eight possible measurements, only one - sub-metering the compressed-air system - could change our decision, and it is worth about 36,000 riyals. If it costs less than that, measure first; if not, go ahead. Everything else would not change what we do.',
        advanced="Binning estimators carry small noise; an irrelevant dummy variable is evaluated to show the noise floor."),
    dict(
        key="npv", title="Net Present Value (NPV) and simple payback", status=STATUS_FULL,
        status_note="NPV with optional output degradation (solar); payback computed and now shown on the Projects step.",
        what="NPV is a project's total value in today's riyals: discounted future savings minus the investment. Payback is the "
             "number of years to recover the cost.",
        origin="Discounting goes back to Irving Fisher (1907, 1930); NPV became standard capital budgeting in the 1950s and is "
               "prescribed for public appraisal in the UK Treasury Green Book.", refs=["greenbook"],
        why="Savings arrive over 10-25 years; a riyal in year 20 is worth less than one today. NPV compares projects fairly.",
        how=["Estimate the cost and the yearly net saving.", "Divide each year's saving by (1 + r)^t and add them up (r = 6% real).",
             "Subtract the cost. Payback = cost ÷ yearly saving."],
        example="Solar: SAR 2.5M cost, SAR 308,000 a year → payback 8.1 years; NPV over 25 years ≈ +SAR 1.25M.",
        code=[("carbon_iq/engine.py", "npv", "capex, annual cash flow, rate, years", "NPV in SAR"),
              ("carbon_iq/engine.py", "degraded_annuity_factor", "rate, years, degradation", "discount factor for declining output"),
              ("carbon_iq/engine.py", "simple_payback", "capex, annual cash flow", "years"),
              ("carbon_iq/engine.py", "projects", "parameter set p", "capex, cash flow, NPV, tonnes for projects A-F")],
        judges="For each project we ask what it is worth today after discounting future savings - that's NPV - and how quickly the "
               "money comes back - that's payback. Solar pays back in about eight years and is worth 1.25 million riyals today.",
        advanced="Payback ignores everything after the payback year and the time value of money, so CARBON IQ never optimises it."),
    dict(
        key="irr", title="Internal Rate of Return (IRR)", status=STATUS_FULL,
        status_note="Calculated per project (solar with degradation); shown on the Projects step from v2.",
        what="The discount rate at which a project's NPV is exactly zero - its 'interest rate' on the money invested.",
        origin="A standard capital-budgeting measure alongside NPV (UK Treasury Green Book discusses both).", refs=["greenbook"],
        why="Managers often compare projects with a hurdle rate. IRR above the hurdle rate = NPV positive at that rate.",
        how=["Write NPV as a function of the rate r.", "Search for the r where NPV = 0 (bisection).",
             "Compare with the company's hurdle rate."],
        example="Solar: IRR ≈ 11.0% > 6% discount rate → positive NPV. Heat recovery: IRR negative → loses money.",
        code=[("carbon_iq/engine.py", "irr", "capex, annual cash flow, years", "IRR (bisection), or None"),
              ("carbon_iq/engine.py", "project_irr", "project record, degradation", "IRR with declining solar output")],
        judges="IRR is the yearly return a project earns on the money invested - like an interest rate. Solar earns about 11% a year, well above our 6% discount rate, so it creates value. Heat recovery has a negative IRR at today's gas price. We report IRR, but we optimise on NPV, which handles projects of different sizes correctly.",
        advanced="IRR can mislead when comparing projects of different size; CARBON IQ ranks and optimises on NPV."),
    dict(
        key="roi", title="Return on Investment (ROI)", status=STATUS_NONE,
        status_note="Not implemented as a named metric. The same question is answered by NPV, IRR, payback and NPV per riyal "
                    "(profitability index, used as a ranking baseline).",
        what="ROI usually means (total gain − cost) ÷ cost. It ignores when the money arrives.",
        origin="A common business ratio with no single standard definition; discounted alternatives (NPV, IRR) are set out in the "
               "UK Treasury Green Book.", refs=["greenbook"],
        why="CARBON IQ deliberately uses discounted measures instead, because the projects last 10-25 years.",
        how=["Not computed. If needed: ROI = (sum of yearly net savings − cost) ÷ cost, undiscounted.",
             "The nearest implemented measure is NPV ÷ capex (profitability index).", "Report it only with its definition."],
        example="Illustration only: solar 25 × SAR 308,000 − SAR 2.5M = SAR 5.2M gain → ROI 208% (undiscounted, ignores degradation).",
        code=[("carbon_iq/optimize.py", "baselines", "projects, budget, target", "ranking by NPV per riyal (profitability index)")],
        judges='We deliberately do not report simple ROI. It adds up savings without asking when they arrive, so a 25-year solar plant looks the same as one that pays back immediately. NPV, IRR and payback answer the same question properly, and every one of them is shown for each project.',
        advanced="Adding ROI would be a one-line display change; it is not added to avoid a metric without a fixed definition."),
    dict(
        key="mac", title="Marginal Abatement Cost (MAC)", status=STATUS_FULL,
        status_note="SAR per tCO2e for every project; used in the 'cheapest tonne first' ranking baseline.",
        what="The cost of avoiding one tonne of CO2e with a project. Negative means the project saves money while cutting emissions.",
        origin="Used in energy policy since the 1990s and popularised by McKinsey cost curves (2007-09); pitfalls reviewed by Kesicki "
               "& Ekins (2012).", refs=["kesicki"],
        why="It connects money and carbon, and it is the most common way companies rank climate projects today.",
        how=["Take the project's NPV.", "Divide −NPV by its discounted lifetime tonnes.", "Sort: cheapest tonnes first."],
        example="Solar −SAR 97/t (saves money); heat recovery +SAR 107/t (costs money per tonne).",
        code=[("carbon_iq/engine.py", "mac", "project record from projects()", "SAR per tCO2e")],
        judges='Marginal abatement cost tells you what each tonne of CO2 costs to avoid; negative means the project saves money. But funding the cheapest tonnes first, as many companies do, would pick a plan that loses money in our test case - which is why CARBON IQ optimises the whole portfolio instead of sorting projects.',
        advanced="A ratio ignores project size, budget and overlaps between projects."),
    dict(
        key="ranking", title="Single-criterion project ranking (comparison baselines)", status=STATUS_FULL,
        status_note="Three one-criterion rankings (NPV, NPV per riyal, cheapest tonne first) are computed and compared with the "
                    "optimised portfolio. This is sorting on one number at a time, not multi-criteria decision analysis.",
        what="Sorts projects by one number - for example NPV or cost per tonne - and funds them from the top until the money runs out.",
        origin="Capital rationing and the profitability index (Lorie & Savage, 1955); cost-per-tonne ranking from MAC curves "
               "(reviewed by Kesicki & Ekins, 2012).", refs=["lorie", "kesicki"],
        why="It is how many companies choose today, so it is the fair baseline to show what optimisation adds.",
        how=["Compute one score per project (NPV, NPV ÷ capex, or MAC).", "Sort the projects by that score.",
             "Fund down the list while the budget allows; compare with the optimiser's portfolio."],
        example="Cheapest tonne first funds A+B+C+D+F: SAR 4.70M, NPV −SAR 0.56M. Ranking by NPV funds A+B+C - here the same as the optimiser.",
        code=[("carbon_iq/optimize.py", "greedy", "projects, budget, ranking key", "portfolio funded down the list"),
              ("carbon_iq/optimize.py", "baselines", "projects, budget, target", "the three ranking baselines")],
        judges="We compare CARBON IQ with the way companies usually decide: sort projects by one number and fund from the top. Sorting "
               "by cheapest tonne would pick a plan that loses money here. Sorting by NPV happens to match our answer - our added value "
               "is the confidence behind it.",
        advanced="Rankings ignore the target and combinations; they are shown for comparison only."),
    dict(
        key="multicriteria", title="Multi-criteria decision analysis (MCDA, weighted scoring)", status=STATUS_NONE,
        status_note="Not implemented. CARBON IQ assigns no weights and computes no combined score. Its decision rules maximise "
                    "expected NPV subject to carbon and budget confidence constraints - a constrained single-objective method, "
                    "which is not MCDA. The single-criterion rankings above are not MCDA either.",
        what="MCDA scores each option on several criteria (value, carbon, risk, ease), weights the criteria, and ranks options by the "
             "weighted total.",
        origin="Multi-attribute decision analysis: Keeney & Raiffa (1976).", refs=["keeney"],
        why="Not used, because weights are subjective and would need agreement with the company's decision-makers. CARBON IQ instead "
            "turns carbon and risk into explicit limits (constraints).",
        how=["Not computed. A weighted method would: score every project on each criterion (0-1).",
             "Multiply each score by an agreed weight and add them up.", "Rank by the total - and test how the ranking changes with the weights."],
        example="Illustration only (not computed): weights 50% value, 30% carbon, 20% risk; a project scoring 0.8, 0.4, 0.9 gets "
                "0.5×0.8 + 0.3×0.4 + 0.2×0.9 = 0.70.",
        code=[("carbon_iq/decisions.py", "choose", "portfolio probabilities, budget, required levels",
               "related, not MCDA: max expected NPV subject to the carbon and budget constraints")],
        judges="CARBON IQ does not use weighted scoring. Weights are a matter of opinion, so instead we set the carbon target and the "
               "budget confidence as hard limits and maximise value within them. Adding weighted MCDA would be a future step, agreed "
               "with the company.",
        advanced="An epsilon-constraint view: one objective (expected NPV) is optimised while the others (carbon, budget risk) are "
                 "constraints; the efficient frontier shows the trade-off."),
    dict(
        key="portfolio", title="Portfolio optimisation under a budget", status=STATUS_FULL,
        status_note="Binary integer program (HiGHS) cross-checked by enumerating all 64 portfolios; MRC uses the same functions on 16.",
        what="Finds the combination of projects with the highest value that fits the budget and meets the carbon target.",
        origin="Capital rationing (Lorie & Savage, 1955); integer programming solved by branch-and-bound (Land & Doig, 1960).",
        refs=["lorie", "landdoig"],
        why="Six projects give 64 plans. The best plan is rarely 'the top projects until the money runs out'.",
        how=["Give each project a yes/no switch.", "Rules: total cost ≤ budget; total cut ≥ target; shared savings counted once.",
             "Let the solver find the highest-NPV combination; check by trying every combination."],
        example="Synthetic: A+B+C, SAR 4.05M, 1,755 t/yr, NPV SAR 1.56M - best of all plans within SAR 5M meeting 1,358 t.",
        code=[("carbon_iq/optimize.py", "solve_milp", "projects, overlap, budget, target", "optimal portfolio (HiGHS)"),
              ("carbon_iq/optimize.py", "enumerate_best", "projects, overlap, budget, target", "best of all 64 portfolios + every row"),
              ("carbon_iq/engine.py", "portfolio", "selected ids", "capex, NPV, tonnes with the B-C overlap removed"),
              ("carbon_iq/mrc.py", "portfolios", "MRC parameter set", "best of the 16 MRC portfolios")],
        judges='With six projects there are 64 possible plans. Instead of guessing, CARBON IQ checks every one: it keeps the plans that fit the five-million budget and hit the carbon target, then picks the most valuable - solar, efficient motors and compressed-air repair, for 4.05 million riyals and about 1,755 tonnes a year.',
        advanced="The optimiser agreed with exhaustive search in all 3,267 budget/target cases tested in A6."),
    dict(
        key="sensitivity", title="Sensitivity analysis", status=STATUS_FULL,
        status_note="Tornado, first-order variance indices, switch points, discount-rate robustness, price scenarios; Sobol indices "
                    "in the A6 validation script.",
        what="Finds which assumptions move the result most and at what value the recommended plan would change.",
        origin="Tornado charts from decision analysis; variance-based indices by Sobol and Saltelli et al. (2008).",
        refs=["saltelli", "sobol"],
        why="Shows judges and managers which assumptions really matter, and where the answer could flip.",
        how=["Move one input from its 5th to its 95th percentile and record the NPV change (tornado).",
             "Measure each input's share of the total variation from the Monte Carlo runs.",
             "Sweep key inputs to find the switch point where the best plan changes."],
        example="Tariff moves A+B+C's NPV by SAR 2.0M but never changes the plan; compressed-air savings below 20% switch it to A+B.",
        code=[("carbon_iq/sensitivity.py", "tornado", "portfolio ids", "NPV at each input's 5th and 95th percentile"),
              ("carbon_iq/sensitivity.py", "first_order", "scenarios, output", "first-order variance shares"),
              ("carbon_iq/sensitivity.py", "switch_points", "budget, inputs", "values where the best plan changes"),
              ("tools/run_a6.py", "gsa", "sample size", "Sobol first and total indices (validation)"),
              ("carbon_iq/mrc.py", "tornado", "MRC ids and parameters", "one-way NPV sensitivity for MRC")],
        judges="We ask which assumptions really matter. The electricity tariff changes the plan's value the most - by about two million riyals - but never changes the recommendation. The real knife-edge is compressed-air savings: below 20%, the best plan changes. That is the number we would verify first, before committing the money.",
        advanced="One-at-a-time tests miss interactions; the Sobol indices in A6 cover them for the key decision."),
    dict(
        key="timing", title="Investment timing and flexibility (real options)", status=STATUS_PART,
        status_note="Implemented for one project (D, heat recovery) and one uncertain price (gas): decision tree, GBM trigger, "
                    "least-squares Monte Carlo. Not applied to MRC.",
        what="Values the option to wait: should a project start now, or later when an uncertain price becomes clearer?",
        origin="'Real options' coined by Myers (1977); Dixit & Pindyck (1994); simulation method by Longstaff & Schwartz (2001).",
        refs=["myers", "dixit", "lsmc"],
        why="Ordinary NPV assumes 'now or never'. Waiting for a gas-price reform can avoid a loss.",
        how=["Describe how the price may move (a 50% chance of reform within a year).",
             "Compare 'invest now' with 'wait, then invest only if worthwhile'.",
             "Compute a trigger price above which investing pays."],
        example="Heat recovery at USD 2.15/MMBtu: NPV −SAR 0.31M; waiting avoids an expected SAR 0.22M loss; break-even ≈ USD 3.85.",
        code=[("carbon_iq/timing.py", "decision_tree", "reform probability, prices", "invest-now vs wait values"),
              ("carbon_iq/timing.py", "gbm_trigger", "drift, volatility, rate", "price trigger for investing"),
              ("carbon_iq/timing.py", "lsmc", "price model, paths", "option value by least-squares Monte Carlo")],
        judges="Some projects depend on prices that may soon change. Furnace heat recovery saves gas, and Saudi gas prices may be reformed. At today's price it loses money, so instead of saying 'no forever', CARBON IQ says 'wait and watch': invest when the gas price passes a trigger. That flexibility has real value.",
        advanced="The GBM trigger (about USD 17) reflects a high assumed volatility, not a forecast."),
    dict(
        key="stability", title="Decision-stability checks", status=STATUS_FULL,
        status_note="Monte Carlo margins in standard errors, perturbation of estimated data, switch points, knife-edge seeds, "
                    "capital-cost risk and regret (synthetic plant); budget-margin check for MRC (v2.1).",
        what="Asks whether the recommendation would survive small changes in the data, the assumptions or the random sample.",
        origin="Sampling error of scenario-based probabilities (Pagnoncelli, Ahmed & Shapiro, 2009); robustness testing in sensitivity "
               "analysis (Saltelli et al., 2008).", refs=["pagnoncelli", "saltelli"],
        why="A recommendation that flips with a 1% data change, or with a different random sample, should not be presented as settled.",
        how=["Measure how far each probability sits from its 90% threshold, in Monte Carlo standard errors.",
             "Re-run the decision with estimated data at the edges of their intervals and at switch points.",
             "Flag ⚠ any choice that is closer than 2 standard errors or that changes."],
        example="MRC scenario: A+B+C keeps the budget in 90.66% of 20,000 futures vs the 90.35% required - only 1.4 standard errors; "
                "flagged as a knife-edge.",
        code=[("carbon_iq/dataquality/stability.py", "margins", "activity with uncertainty", "distance from each threshold"),
              ("carbon_iq/dataquality/stability.py", "assess", "activity", "STABLE / not stable per rule, switch points"),
              ("carbon_iq/decisions.py", "knife_edge", "scenarios, portfolio", "probability across random seeds"),
              ("carbon_iq/decisions.py", "capex_risk", "scenarios, budget", "cost-overrun probabilities"),
              ("carbon_iq/uncertainty.py", "Scenarios.regret", "budget, target", "average regret per portfolio"),
              ("carbon_iq/mrc.py", "monte_carlo", "MRC parameters", "budget margin in standard errors per plan")],
        judges="We check whether our answer is stable. If a small change in data or in the random sample could flip it, CARBON IQ "
               "shows a warning instead of a confident recommendation - as it does for the MRC scenario, where the best plan passes "
               "the budget rule by a hair.",
        advanced="Two standard errors is the flag threshold; it is a convention, not a guarantee."),
    dict(
        key="risk", title="Risk register", status=STATUS_NONE,
        status_note="Not implemented as a feature. Open risks are tracked in ISSUE_LOG.md (a document) and listed under each "
                    "recommendation's limitations; no likelihood, impact or owner is calculated or stored by the app. The only "
                    "quantified risk is the capital-cost overrun probability (decisions.capex_risk).",
        what="A table of what could go wrong, how likely and how severe it is, who owns it and what is done about it.",
        origin="ISO 31000:2018 risk-management guidelines.", refs=["iso31000"],
        why="Management needs one place to track risks such as an unverified emission factor or a missing supplier quotation.",
        how=["Not computed. A register would list each risk with likelihood and impact (e.g. 1-5).",
             "Multiply likelihood by impact to rank the risks.", "Assign an owner and an action, and review regularly."],
        example="Illustration only: 'MRC Scope 2 factor unverified' - likelihood 4, impact 4 → score 16 → owner: sustainability team; "
                "action: request the factor from Ma'aden.",
        code=[("carbon_iq/decisions.py", "capex_risk", "scenarios, budget", "related: probability of exceeding the budget")],
        judges='CARBON IQ quantifies decision risks - the chance of missing the target or exceeding the budget - but it does not yet keep a formal risk register with likelihoods, impacts and owners. Open risks, like the unverified Scope 2 factor, are listed in our issue log and under every recommendation.',
        advanced="ISSUE_LOG.md is the closest artefact; turning it into a scored register is a documented next step."),
]
BY_KEY = {m["key"]: m for m in METHODS}

GLOSSARY = [
    ("tCO2e", "Tonnes of carbon dioxide equivalent: all greenhouse gases converted to the CO2 amount with the same warming effect."),
    ("Scope 1", "Direct emissions from fuel burned on site (gas furnaces, diesel)."),
    ("Scope 2", "Emissions from producing the electricity the site buys."),
    ("Scope 3", "Other value-chain emissions, e.g. making the steel the plant buys."),
    ("Emission factor", "Tonnes of CO2e per unit of activity (per MWh, per GJ, per litre)."),
    ("GJ / MWh", "Energy units. 1 MWh = 3.6 GJ."),
    ("Activity data", "The measured quantity: MWh bought, GJ of gas burned, litres of diesel."),
    ("Baseline", "Emissions before any project, the reference for the target."),
    ("Uncertainty (± %, 95%)", "Range that contains the true value 95 times out of 100."),
    ("Capex", "Capital expenditure: the up-front investment cost."),
    ("Discount rate", "How much less a future riyal is worth than today's (6% real per year here)."),
    ("NPV", "Net present value: discounted savings minus cost, in today's riyals."),
    ("IRR", "Internal rate of return: the discount rate at which NPV = 0."),
    ("Payback", "Years to recover the investment from yearly savings."),
    ("MAC", "Marginal abatement cost: riyals per tonne of CO2e avoided (negative = saves money)."),
    ("Portfolio", "A combination of projects funded together."),
    ("Monte Carlo simulation", "Testing a plan in thousands of randomly drawn futures."),
    ("Expected NPV, E[NPV]", "Average NPV over all simulated futures."),
    ("Percentile (5th)", "The value below which 5% of simulated outcomes fall - a 'bad case'."),
    ("Chance constraint", "A rule such as 'meet the target in at least 90% of futures'."),
    ("EVPI", "Expected value of perfect information: the most any information could be worth."),
    ("EVPPI", "Value of perfect information about one input."),
    ("EVSI", "Value of a real, imperfect measurement."),
    ("Sensitivity analysis", "Testing which assumptions change the result most."),
    ("Switch point", "The value of an input at which the recommended plan changes."),
    ("Real option", "The value of being able to wait and decide later."),
    ("Synthetic data", "Made-up data with realistic values, used to test methods. Not company data."),
    ("Reported data", "Figures published by a company (here Ma'aden's 2025 data book)."),
    ("Benchmark", "A value from a published external source, used when company data are missing."),
    ("Hypothetical", "An illustrative assumption made by CARBON IQ; not a company value."),
]

PROVES = [
    "The methods are correctly implemented: automated tests (127 before v2, more since), 28/28 injected errors caught, an independent re-implementation "
    "and spreadsheet agree (A6).",
    "On a synthetic plant, combining them changes the conversation: probabilities for target and budget, the value of extra data, "
    "and warnings when data are missing.",
    "The emissions arithmetic works on real reported data: MRC Scope 1 recalculated within 0.3% of Ma'aden's figure.",
]
NEEDS_VALIDATION = [
    "Accuracy on real monthly plant records (missing-data estimates were calibrated on synthetic data).",
    "Real project costs and savings: all MRC project inputs and five of six synthetic project costs are hypothetical.",
    "MRC's Scope 2 method: the implied factor (0.335 tCO2e/MWh) differs from the national average (0.573) and is not explained "
    "in the data book.",
    "Whether Saudi manufacturers face the decision gap CARBON IQ targets (no interviews held yet).",
    "A real Google Colab run and an external review; CARBON IQ is a research prototype, not production software.",
]

CONNECTIONS_DOT = """
digraph G { rankdir=TB; nodesep=0.35; ranksep=0.32; node [shape=box, style="rounded,filled", fillcolor="#EEF4F1", color="#1F6B5C", fontname="Helvetica", fontsize=12, width=2.2];
 data [label="Factory data\\n(monthly or reported)", fillcolor="#0E2A25", fontcolor="white"];
 dq [label="Data quality &\\nmissing-data estimation"]; f [label="Emission factors &\\nunit conversions"];
 ghg [label="Scope 1 & 2\\naccounting"]; unc [label="Uncertainty\\npropagation"]; econ [label="NPV · IRR · payback · MAC"];
 port [label="Portfolio\\noptimisation", fillcolor="#FFF4E2", color="#F2A33A"]; mc [label="Monte Carlo", fillcolor="#FFF4E2", color="#F2A33A"];
 cc [label="Probability of meeting\\ntarget & budget", fillcolor="#FFF4E2", color="#F2A33A"];
 voi [label="Value of information\\n(EVPI, EVPPI, EVSI)"]; sens [label="Sensitivity &\\nstability"]; time [label="Timing\\n(real options)"];
 rec [label="Recommendation\\n+ confidence + limits", fillcolor="#0E2A25", fontcolor="white"];
 data -> dq -> ghg; f -> ghg; ghg -> unc; ghg -> econ; econ -> port; port -> mc -> cc -> rec; cc -> voi -> rec; sens -> rec; time -> rec;
 voi -> data [style=dashed, color="#B9761A", label="collect if worth it", fontsize=9];
}
"""
