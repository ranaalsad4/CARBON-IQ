"""CARBON IQ assumption register: the single source of truth for every input.

Each parameter carries: value, unit, status, source/rationale and (where uncertain) a distribution used by
the Monte Carlo engine.

status:
  verified      value taken from a cited public source and applicable to this context (checked October 2026)
  derived       computed from verified values with a stated method
  transferred   value taken from a cited public source but transferred from a different context
                (another country, sector or study); applicability to this facility is an assumption
  provisional   value with partial or secondary evidence only; the primary source is not confirmed or a change
                has been announced; results are also reported under alternative scenarios
  hypothetical  illustrative project assumption for the synthetic case facility (NOT real company data)

evidence (A5): the kind of input, separate from its quality status:
  measured      observed at the facility (none in this prototype: the facility is synthetic)
  external      taken from a cited external source (government, utility, standard, study, benchmark)
  derived       computed from external values with a stated method
  hypothetical  illustrative assumption for the synthetic case (NOT real company data or a quotation)
  estimated     filled by the A4 missing-data engine at run time (never stored in this register)

Version history: v1.1 (A1 corrections, 25 Oct 2026) - status labels corrected, activity-data uncertainty moved into
the register, tariff and grid-factor evidence documented with scenarios. v1.3 (A5, 26 Oct 2026) - grid factor derived
from official Saudi statistics, 2025 regulated methane price, Riyadh rooftop-PV cost benchmark, PV degradation,
compressed-air savings and leak-management cost revised, sources and evidence classes added; the v1.2 register is kept as
profile "v1.2" (use_profile) for before/after comparison. See CHANGELOG.md.

The facility is HYPOTHETICAL: a medium-sized metal-fabrication and assembly plant in the Riyadh region.
No value describes a real Saudi company.
"""
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Optional, Tuple

MODEL_VERSION = "1.3"

SAR_PER_USD = 3.75          # Saudi riyal peg (SAMA, fixed since 1986)
GJ_PER_MMBTU = 1.055056


@dataclass(frozen=True)
class Param:
    key: str
    value: float
    unit: str
    status: str
    source: str
    note: str = ""
    dist: Optional[Tuple] = None   # ("uniform", lo, hi) | ("triangular", lo, mode, hi) | ("normal_rel", sd_fraction)
    url: str = ""
    group: str = ""
    stream: int = 1                # 1 = original random stream; 2 = added in v1.1; 3 = added in v1.3 (independent streams)
    evidence: str = ""             # measured | external | derived | hypothetical | estimated (A5)
    published: str = ""            # publication date of the source (A5)
    effective: str = ""            # period / date the value applies to (A5)
    geography: str = ""            # where the value comes from and how it applies to a Riyadh plant (A5)


P = {}


STATUSES = ("verified", "derived", "transferred", "provisional", "hypothetical")
EVIDENCE = ("measured", "external", "derived", "hypothetical", "estimated")
_EVIDENCE_DEFAULT = {"verified": "external", "transferred": "external", "provisional": "external", "derived": "derived",
                     "hypothetical": "hypothetical"}
Z95 = 1.959964   # two-sided 95% normal quantile; a +/-U% (95%) range has 1 s.d. = U / Z95


def add(key, value, unit, status, source, note="", dist=None, url="", group="", stream=1, evidence=None, published="",
        effective="", geography=""):
    assert status in STATUSES, status
    evidence = evidence or _EVIDENCE_DEFAULT[status]
    assert evidence in EVIDENCE, evidence
    P[key] = Param(key, float(value), unit, status, source, note, dist, url, group, stream, evidence, published, effective, geography)


URL = {
    "sec_tariff": "https://rise.esmap.org/data/files/library/saudi-arabia/Renewable%20Energy/Saudi%20Arabia%20Tariff%20Schedule_2022.pdf",
    "agbi_diesel": "https://www.agbi.com/oil-and-gas/2026/01/saudi-companies-face-cost-increase-as-aramco-ups-diesel-price/",
    "kapsarc_ro": "https://doi.org/10.30573/KS--2026-DP49",
    "ipcc2006": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf",
    "desnz2025": "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025",
    "worldsteel": "https://worldsteel.org/wider-sustainability/sustainability-indicators/sustainability-indicators-report-2025/",
    "irena2024": "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2025/Jul/IRENA_TEC_RPGC_in_2024_Summary_2025.pdf",
    "nasa_power": "https://profilesolar.com/locations/Saudi-Arabia/Riyadh/",
    "doe_air": "https://nrel.gov/docs/fy01osti/28008.pdf",
    "iea4e": "https://www.iea-4e.org/document/150/energy-efficiency-policy-opportunities-for-electric-motor-driven-systems",
    "ghg_unc": "https://ghgprotocol.org/sites/default/files/2023-03/ghg-uncertainty.pdf",
    "sec_ef": "https://www.se.com.sa",
    "argaam_2017": "https://www.argaam.com/en/article/articledetail/id/519195",
    "spark_2025": "https://www.spark.sa/page/news_detail/3512",
    "attaqa_2026": "https://attaqa.net/2026/10/25/%D8%B1%D9%81%D8%B9-%D8%A3%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D9%83%D9%87%D8%B1%D8%A8%D8%A7%D8%A1-%D9%81%D9%8A-%D8%A7%D9%84%D8%B3%D8%B9%D9%88%D8%AF%D9%8A%D8%A9-%D9%84%D8%B9%D8%A7%D9%85-2027-%D9%88/",
    "slg_2026": "https://saudilifeguide.com/saudi-electricity-tariff-2027/",
    "national_2026": "https://www.thenationalnews.com/news/gulf/2026/10/25/saudi-arabia-announces-support-measures-as-electricity-and-water-tariffs-rise/",
    "dna_gef_2021": "https://cdmdna.gov.sa/Resources/70/e179cf72596d15213c8772bf7a9dab642.pdf",
    "kfupm_2024": "https://sustainability.kfupm.edu.sa/documents/78/KFUPM_Greenhouse_Gas_Emissions_Inventory_for_2024_v2.pdf",
    "ifi_2019": "https://unfccc.int/sites/default/files/resource/Harmonized_Grid_Emission_factor_data_set.pdf",
    # A5 sources
    "ksa_btr1": "https://unfccc.int/sites/default/files/resource/KSA_BTR1_20250320-2.pdf",
    "gastat_ee_2021": "https://www.stats.gov.sa/sites/default/files/Electric_Energy_Statistics_2021_Ar.pdf",
    "argaam_gastat_2021": "https://www.argaam.com/en/article/articledetail/id/1611319",
    "spa_2027": "https://www.spa.gov.sa/en/N2709801",
    "ajc_2025": "https://www.aljaziracapital.com.sa/media/jn3bxjbu/energy-price-reforms-jan-25-en.pdf",
    "mm_2026": "https://markets.financialcontent.com/stocks/article/marketminute-2026-1-1-saudi-aramco-implements-2026-feedstock-price-hikes-industrial-giants-face-margin-pressure-as-energy-reforms-accelerate",
    "mees_diesel_2026": "https://www.mees.com/2026/1/2/news-in-brief/saudi-increases-diesel-prices/f2cdf290-e7df-11f0-aea8-4d31a1325bf5",
    "knightfrank_2025": "https://www.knightfrank.ae/site-assets/pdf/going-green-rooftop-solar-potential-in-the-gcc-2025.pdf",
    "alzahrani_2021": "https://pubs.sciepub.com/ajer/9/1/5/index.html",
    "jordan_kurtz_2013": "https://doi.org/10.1002/pip.1182",
    "fraunhofer_vsd_2023": "https://www.zvei.org/fileadmin/user_upload/Verband/Fachverbaende/Automation/Elektrische_Antriebe/Cemep_Studie/Cemep_Fraunhofer_study-motor-saving-potential-with-VSD-20231215.pdf",
    "cac_leaks_2026": "https://www.compressedairchallenge.org/data/sites/1/media/library/factsheets2026/fact-sheet-7-compressed-air-system-leaks_updated2026.pdf",
    "doe_preheat": "https://www1.eere.energy.gov/manufacturing/tech_assistance/pdfs/et_preheated.pdf",
    "argaam_intensive_2021": "https://www.argaam.com/en/article/articledetail/id/1500079",
    "ipcc_gwp_2024": "https://ghgprotocol.org/sites/default/files/2024-08/Global-Warming-Potential-Values%20%28August%202024%29.pdf",
}

# ------------------------------------------------------------------ prices and finance
add("tariff", 0.18, "SAR/kWh", "provisional",
    "Industrial tariff 18 halalas/kWh, flat (no consumption bands), in force 1 Jan 2018 - 31 Dec 2026 (ECRA statement "
    "reported by Argaam, 13 Dec 2017; SEC tariff schedule 2022). Reference case = last officially documented rate. "
    "A rise to 23 halalas/kWh from 1 Jan 2027 was reported on 25 Oct 2026; see TARIFF_SCENARIOS",
    "Upward-skewed range reflects possible future tariff reform (assumption, unchanged from v1.0)",
    ("triangular", 0.18, 0.18, 0.26), URL["argaam_2017"], "Energy prices", published="13 Dec 2017 (ECRA via Argaam); 25 Oct 2026 (SPA)",
    effective="1 Jan 2018 - 31 Dec 2026; adjustment officially announced from 1 Jan 2027 (rates not in the SPA release)",
    geography="Saudi Arabia, national regulated tariff, industrial category (non-intensive), applies to a Riyadh plant")
add("diesel_price", 1.79, "SAR/L", "verified", "Aramco diesel price SAR 1.79/L from 1 Jan 2026 (+7.8%; MEES 2 Jan 2026; AGBI Jan 2026); "
    "SAR 1.66/L in 2025 (Al Jazira Capital, Jan 2025)",
    "Range: possible further reform (assumption)", ("triangular", 1.79, 1.79, 2.30), URL["mees_diesel_2026"], "Energy prices",
    published="2 Jan 2026", effective="from 1 Jan 2026", geography="Saudi Arabia, national administered price")
add("gas_price_usd", 2.15, "USD/MMBtu", "provisional",
    "Aramco regulated methane (sales-gas) price USD 2.15/MMBtu from 1 Jan 2025, up from 1.75 (Al Jazira Capital, Jan 2025, "
    "summarising Aramco notices to listed companies). A further 10-20% rise from 1 Jan 2026 was reported by a secondary "
    "source without an official figure; see GAS_SCENARIOS. v1.2 used the KAPSARC DP49 modelling anchor of $3.0",
    "Last price with a quantified credible source (2025); lognormal spread (sd 0.25) retained as an assumption. Whether a "
    "Riyadh fabrication plant can obtain piped sales gas at this price (vs LPG or diesel) is unverified",
    ("lognormal", 0.25), URL["ajc_2025"], "Energy prices", published="Jan 2025", effective="from 1 Jan 2025 (2026 level unconfirmed)",
    geography="Saudi Arabia, Aramco Master Gas System regulated price for industrial users")
add("discount_rate", 0.06, "real, per year", "transferred",
    "6% discount rate used by KAPSARC DP49 (Table D1; WACC from Albalawi & El-Houjeiri 2026)",
    "Applied here as the facility's real discount rate (assumption); 4-12% tested in the sensitivity analysis", None, URL["kapsarc_ro"], "Finance",
    published="2026", geography="Saudi energy-investment context (study WACC), transferred to a private manufacturer")
add("budget", 5_000_000, "SAR", "hypothetical", "Management capital budget for decarbonization (case definition)", group="Finance")
add("target_share", 0.15, "fraction of Scope 1+2", "hypothetical",
    "Management target: cut Scope 1+2 emissions by at least 15% per year (case definition)", group="Finance")
add("chance_level", 0.90, "probability", "hypothetical",
    "Required probability of meeting the target in the stochastic selection (management risk appetite)", group="Finance")
add("budget_chance_level", 0.90, "probability", "hypothetical",
    "Required probability that the actual capital cost stays within the budget (management decision, 25 Oct 2026)", group="Finance")

# ------------------------------------------------------------------ facility activity (synthetic)
add("elec_mwh", 12_000, "MWh/yr", "hypothetical", "Synthetic metered grid electricity (12 monthly bills)",
    "Meter uncertainty +/-2%", ("normal_rel", 0.01), group="Activity")
add("gas_gj", 35_000, "GJ/yr (NCV)", "hypothetical", "Synthetic natural-gas use for furnaces and process heat",
    "Meter uncertainty +/-3%", ("normal_rel", 0.015), group="Activity")
# v1.1: the +/-% (95%) activity uncertainties below were hard-coded in engine.py in v1.0 and not sampled in the Monte
# Carlo; they are now register entries (normal, 1 s.d. = U/Z95) drawn on an independent random stream (stream=2).
add("diesel_forklift_l", 60_000, "L/yr", "hypothetical", "Synthetic diesel use, 12 forklifts (fuel cards)",
    "Fuel-card uncertainty +/-5% (95%) (assumption)", ("normal_rel", 0.05 / Z95), group="Activity", stream=2)
add("diesel_genset_l", 20_000, "L/yr", "hypothetical", "Synthetic diesel use, backup generators (fuel logs)",
    "Manual fuel-log uncertainty +/-10% (95%) (assumption)", ("normal_rel", 0.10 / Z95), group="Activity", stream=2)
add("steel_t", 6_000, "t/yr", "hypothetical", "Synthetic purchased steel (procurement records)",
    "Invoice uncertainty +/-2% (95%) (assumption)", ("normal_rel", 0.02 / Z95), group="Activity", stream=2)
add("freight_tkm", 2_000_000, "t-km/yr", "hypothetical", "Synthetic inbound freight (carrier statements)",
    "Supplier-specific data partly missing: +/-20% (95%) (assumption)", ("normal_rel", 0.20 / Z95), group="Activity", stream=2)
add("production_t", 5_000, "t/yr", "hypothetical", "Synthetic finished output (metal products)", group="Activity")
add("motor_share", 0.45, "fraction of electricity", "hypothetical",
    "Non-compressor motor systems; plausible given motors' ~53% share of global electricity (4E/IEA 2025)",
    url=URL["iea4e"], group="Activity")
add("compressed_air_share", 0.15, "fraction of electricity", "hypothetical",
    "Compressed-air system share of plant electricity (assumption, to be sub-metered)", group="Activity")

# ------------------------------------------------------------------ emission factors
add("ef_grid", 0.573, "tCO2e/MWh", "derived",
    "Saudi national grid average 2021 = emissions of electricity generation (IPCC 1.A.1.a.i, 205,579 Gg CO2e, AR5 GWP; KSA First "
    "Biennial Transparency Report, UNFCCC 2025, Table 6) / electricity generated (358,640 GWh; GASTAT via Argaam, 26 Dec 2022; "
    "GASTAT Electric Energy Statistics 2021: 359 TWh) = 0.573 tCO2e/MWh generated. Corroborated by the Saudi DNA 2021 grid "
    "factor 0.568 (as cited by KFUPM). Replaces the v1.2 project factor 0.55, whose source table was never located",
    "Uncertainty +/-10% (95%) retained: 2021 vintage (renewables and gas have grown since), generation-based (T&D losses "
    "belong to Scope 3 Cat 3), category boundary of 1.A.1.a.i vs GASTAT generation not reconciled",
    ("normal_rel", 0.05), URL["ksa_btr1"], "Emission factors", published="Mar 2025 (BTR1); Dec 2022 (GASTAT via Argaam)",
    effective="inventory year 2021", geography="Saudi Arabia, national interconnected grid average (location-based Scope 2)")
add("ef_gas", 0.0561545, "tCO2e/GJ", "derived",
    "IPCC 2006 Vol.2 Table 2.3 natural gas: CO2 56,100 + CH4 1 x 28 + N2O 0.1 x 265 kg/TJ (AR5 GWP)",
    "CO2 range 54,300-58,300 kg/TJ. AR5 GWPs kept for consistency with the Saudi BTR1 inventory (AR5, Tier 1); AR6 "
    "(CH4 fossil 29.8, N2O 273) would give 0.0561571 (+0.005%)", ("normal_rel", 0.018), URL["ipcc2006"], "Emission factors",
    published="2006 (IPCC); GWP AR5 2014", geography="IPCC default, the method used by Saudi Arabia's national inventory (BTR1, Tier 1)")
add("ef_diesel", 0.00266155, "tCO2e/L", "transferred", "DESNZ 2025 diesel (100% mineral), stationary combustion, 2.66155 kg CO2e/L",
    "UK proxy factor; cross-check with IPCC 2006 defaults (74,100 kg CO2/TJ x 43.0 TJ/Gg x assumed density 0.84 kg/L = "
    "2.676 kg CO2/L, +0.6%)", ("normal_rel", 0.02), URL["desnz2025"], "Emission factors", published="Jun 2025",
    geography="UK fuel specification; within 1% of IPCC defaults, so applicable to Saudi diesel within the stated uncertainty")
add("ef_freight", 0.00010163, "tCO2e/t-km", "transferred", "DESNZ 2025 HGV all diesel, average laden, 0.10163 kg CO2e/t-km",
    "UK proxy; supplier-specific data missing; Saudi fleet load factors and empty running unknown", ("normal_rel", 0.15),
    URL["desnz2025"], "Emission factors", published="Jun 2025", geography="UK HGV fleet average; transferred")
add("ef_steel_incumbent", 1.92, "tCO2/t steel", "transferred",
    "worldsteel 2025 report: global average 1.92 tCO2/t crude steel (2024); used as proxy for incumbent supplier",
    "Supplier-specific value unknown: range DRI-EAF 1.47 to BF-BOF 2.34. Crude-steel intensity: excludes rolling/finishing that a "
    "cradle-to-gate product factor (GHG Protocol Scope 3 Cat 1) would include", ("uniform", 1.47, 2.34), URL["worldsteel"],
    "Emission factors", published="2025", effective="2024 data", geography="Global average; Saudi mills are mainly DRI-EAF (lower)")
add("ef_steel_alt", 1.47, "tCO2/t steel", "transferred",
    "worldsteel 2025 report: DRI-EAF route 1.47 tCO2/t (2024); proxy for alternative supplier offer",
    "Offer unverified: range scrap-EAF 0.69 to DRI-EAF 1.47", ("uniform", 0.69, 1.47), URL["worldsteel"], "Emission factors",
    published="2025", effective="2024 data", geography="Global route average; transferred to an unverified supplier offer")

# ------------------------------------------------------------------ projects (all costs hypothetical, anchored where possible)
add("pv_kwp", 1000, "kWp", "hypothetical", "Rooftop PV size limited by usable roof area (~6,000 m2; case definition)", group="A Solar PV")
add("pv_yield", 1850, "kWh/kWp/yr", "derived",
    "Riyadh fixed-tilt PV simulated at 2,008 kWh/kWp/yr with performance ratio 0.818 (Alzahrani & Nahhas 2021, PVsyst + Global "
    "Solar Atlas, 200 MWp utility plant); rooftop value ~8% lower for flat-roof tilt, soiling and heat (assumption) = 1,850",
    "Range 1,650-2,010 (upper = utility-scale simulation)", ("triangular", 1650, 1850, 2010), URL["alzahrani_2021"], "A Solar PV",
    published="2021", geography="Riyadh, simulated (not measured); rooftop adjustment is an assumption")
add("pv_capex_kw", 2500, "SAR/kWp", "transferred",
    "Typical fixed-mount rooftop installation cost SAR 2.5/W from Riyadh-based system providers (Knight Frank, 'Going Green: "
    "Rooftop solar potential in the GCC', 2025). Benchmark, not a quotation. v1.2 used SAR 3,750/kWp (assumed 1.45x IRENA "
    "utility-scale USD 691/kW; no direct source); kept as scenario PV-high",
    "+/-29% (95%; 1 s.d. 15%): system size, structure, grid connection and permitting not covered by the benchmark",
    ("normal_rel", 0.15), URL["knightfrank_2025"], "A Solar PV", published="2025", effective="2025 market",
    geography="Riyadh rooftop market (consultancy survey of local providers)")
add("pv_om_frac", 0.01, "of capex per yr", "hypothetical", "Fixed O&M 1% of capex per year (assumption)", group="A Solar PV")
add("pv_life", 25, "years", "transferred", "Renewables lifetime 25 years (KAPSARC DP49 Table D1; utility-scale context)", url=URL["kapsarc_ro"], group="A Solar PV",
    published="2026", geography="Utility-scale renewables (KAPSARC DP49); transferred to rooftop PV")
add("pv_degradation", 0.005, "per year", "transferred",
    "Median PV degradation 0.5%/yr (Jordan & Kurtz 2013, review of ~2,000 field rates); hot-desert sites tend to be higher",
    "Range 0.3-1.0%/yr (assumption); output in year t = year-1 output x (1-d)^(t-1)", ("triangular", 0.003, 0.005, 0.010),
    URL["jordan_kurtz_2013"], "A Solar PV", stream=3, published="2013", geography="Global field data; transferred")

add("b_capex", 1_200_000, "SAR", "hypothetical", "IE4 motors + variable-speed drives on fans/pumps (budget quote placeholder)",
    "+/-15%", ("normal_rel", 0.15), group="B Motors & VSDs")
add("b_saving_frac", 0.15, "of non-compressor motor electricity", "transferred",
    "Consistent with the Fraunhofer ICT/CEMEP study (Dec 2023) of VSD saving potential: 29% of fan and 15% of pump electricity "
    "(ranges 17-39% and 8-17%); plant-specific savings unverified until an energy audit (key VOI variable)", "Range 8-25%",
    ("uniform", 0.08, 0.25), URL["fraunhofer_vsd_2023"], "B Motors & VSDs", published="15 Dec 2023", geography="EU motor stock; transferred")
add("b_comp_frac", 0.03, "of compressor electricity", "hypothetical", "Premium-efficiency compressor motors (assumption; "
    "Fraunhofer/CEMEP 2023 market potential for compressors 4%, range 2-9%)", url=URL["fraunhofer_vsd_2023"], group="B Motors & VSDs")
add("b_life", 15, "years", "hypothetical", "Equipment life (assumption)", group="B Motors & VSDs")

add("c_capex", 350_000, "SAR", "hypothetical", "Leak survey/repair, controls, pressure reduction (placeholder)",
    "+/-15%", ("normal_rel", 0.15), group="C Compressed air")
add("c_saving_frac", 0.20, "of compressed-air electricity", "derived",
    "Leaks in a poorly maintained system ~20% of capacity (20-30%), well-maintained < 10% (Compressed Air Challenge fact sheet 7, "
    "2026; US DOE tip sheet): repair recovers ~10-15 points; pressure reduction and controls add ~5 points (assumption) = 20%. "
    "v1.2 used 25% (the leak share itself, which overstates savings because leaks cannot be eliminated)", "Range 10-30%",
    ("uniform", 0.10, 0.30), URL["cac_leaks_2026"], "C Compressed air", published="May 2026", geography="Generic (US guidance)")
add("c_om", 15_000, "SAR/yr", "hypothetical",
    "Ongoing leak-management programme (quarterly leak surveys recommended by the Compressed Air Challenge) needed for savings "
    "to persist over the measure life (cost is an assumption, not a quotation; v1.2 had none)", url=URL["cac_leaks_2026"],
    group="C Compressed air")
add("c_life", 10, "years", "hypothetical", "Measure life (assumption; requires the leak-management programme)", group="C Compressed air")

add("d_capex", 600_000, "SAR", "hypothetical", "Furnace flue-gas heat recovery (placeholder quote)", "+/-15%",
    ("normal_rel", 0.15), group="D Heat recovery")
add("d_saving_frac", 0.15, "of natural gas", "transferred",
    "Combustion-air preheating saves 13-20% of natural gas at 1,000-2,000 F flue gas with 600 F air preheat (US DOE Process Heating "
    "Tip Sheet #1, 2007, table from IHEA Combustion Technology Manual); furnace temperatures of the case plant are assumed",
    "Range 10-20%", ("uniform", 0.10, 0.20), URL["doe_preheat"], "D Heat recovery", published="Nov 2007", geography="Generic (US guidance)")
add("d_om", 10_000, "SAR/yr", "hypothetical", "Maintenance (assumption)", group="D Heat recovery")
add("d_life", 15, "years", "hypothetical", "Equipment life (assumption)", group="D Heat recovery")

add("e_capex", 900_000, "SAR", "hypothetical", "Incremental cost of 12 electric forklifts + chargers (placeholder)",
    "+/-15%", ("normal_rel", 0.15), group="E Forklift electrification")
add("e_kwh_per_l", 3.5, "kWh per litre displaced", "hypothetical",
    "Diesel ~10 kWh/L x ~25% engine efficiency / ~75% battery-to-wheel efficiency, rounded up (engineering assumption; no "
    "source found; status corrected from 'derived' to 'hypothetical' in v1.3 because the efficiencies are assumed)",
    "Range 3.0-4.0", ("uniform", 3.0, 4.0), group="E Forklift electrification")
add("e_maint_saving", 20_000, "SAR/yr", "hypothetical", "Lower maintenance of electric fleet (assumption)",
    group="E Forklift electrification")
add("e_life", 10, "years", "hypothetical", "Fleet life (assumption)", group="E Forklift electrification")

add("f_steel_t", 3_000, "t/yr", "hypothetical", "Share of steel moved to a lower-carbon supplier (offer)",
    group="F Low-carbon steel")
add("f_premium", 80, "SAR/t steel", "hypothetical", "Price premium of the lower-carbon offer (assumption)", "Range 50-120",
    ("uniform", 50, 120), group="F Low-carbon steel")
add("f_onboard", 50_000, "SAR", "hypothetical", "Supplier qualification and onboarding (one-time)", group="F Low-carbon steel")
add("f_life", 10, "years", "hypothetical", "Contract horizon (assumption)", group="F Low-carbon steel")

# ------------------------------------------------------------------ value-of-information collection costs (hypothetical)
add("cost_motor_audit", 80_000, "SAR", "hypothetical", "Motor-system energy audit with logging (assumption)", group="Information")
add("audit_error_sd", 0.03, "absolute fraction (1 s.d.)", "hypothetical",
    "Audit measures B's savings fraction with normal error s.d. 3 percentage points (assumption)", group="Information")
add("cost_submeter", 40_000, "SAR", "hypothetical", "Compressed-air sub-metering for one quarter (assumption)", group="Information")
add("cost_supplier_data", 20_000, "SAR", "hypothetical", "Supplier-specific steel EPDs / mill certificates (assumption)", group="Information")
add("cost_pv_study", 30_000, "SAR", "hypothetical", "Site-specific PV yield study (assumption)", group="Information")

# ------------------------------------------------------------------ real-options calibration (from KAPSARC DP49 Table D1)
add("ro_kappa", 0.5, "1/yr", "transferred", "Mean-reversion rate of ln G (KAPSARC DP49 maintained value)", url=URL["kapsarc_ro"], group="Timing",
    published="2026", geography="KAPSARC DP49 study parameter (Saudi energy context); transferred")
add("ro_sigma", 0.522, "annualised", "transferred", "Instantaneous log-volatility of gas price, Henry Hub monthly (KAPSARC DP49)",
    url=URL["kapsarc_ro"], group="Timing",
    published="2026", geography="US Henry Hub monthly prices (KAPSARC DP49); Saudi regulated prices do not follow a market process")
add("ro_mu_gbm", 0.0125, "per yr", "transferred", "Long-run drift for GBM benchmark (KAPSARC DP49 Table D1)", url=URL["kapsarc_ro"], group="Timing",
    published="2026", geography="KAPSARC DP49 study parameter (Saudi energy context); transferred")
add("ro_horizon", 10, "years", "hypothetical", "Window during which the facility may defer heat recovery (assumption)", group="Timing")
add("ro_paths", 5000, "paths", "verified", "Number of LSMC paths as in KAPSARC DP49", url=URL["kapsarc_ro"], group="Timing",
    published="2026", geography="Numerical setting (not a physical quantity)")

add("tree_p_reform", 0.5, "probability", "hypothetical",
    "Probability that an industrial gas-price reform is announced within one year (scenario assumption)", group="Timing")
add("tree_g_reform", 3.225, "USD/MMBtu", "hypothetical",
    "Industrial gas price after a reform (scenario assumption; +50% on the current $2.15 price; v1.2: +50% on $3 = 4.5)", group="Timing")

# ------------------------------------------------------------------ v1.1 evidence and scenarios (A1 corrections)
# Industrial electricity tariff scenarios. Each is run through the full deterministic and Monte Carlo analysis
# (tariff fixed at the scenario value in the Monte Carlo). None is asserted as "the" rate for 2027 onwards.
TARIFF_SCENARIOS = [
    dict(id="T0", value=0.18, label="Reference: 18 halalas (in force 2018-2026)", status="verified for 2018-2026",
         effective="1 Jan 2018 - 31 Dec 2026",
         source="ECRA statement reported by Argaam, 13 Dec 2017: 'Prices for industrial use will be maintained at SAR 0.18 "
                "per KW/h'; SEC tariff schedule 2022 (ESMAP RISE copy)", url=URL["argaam_2017"]),
    dict(id="T1", value=0.20, label="18 halalas + 2 halala non-qualifying surcharge", status="interpretation uncertain",
         effective="from 28 May 2025",
         source="SPARK utility notice, 27 Apr 2025: industrial facilities not qualifying for the intensive-consumption tariff "
                "'will incur an additional charge of 2 (HH/KWh)'; unit and base not stated; applicability to SEC customers "
                "not confirmed", url=URL["spark_2025"]),
    dict(id="T2", value=0.23, label="Announced 2027 tariff: 23 halalas", status="reported (secondary sources); official schedule not obtained",
         effective="from 1 Jan 2027",
         source="Attaqa and Saudi Life Guide, 25 Oct 2026: industrial 23 halalas/kWh (transmission or distribution "
                "connection) from 1 Jan 2027; tariff rise confirmed without rates by The National (citing SPA), 25 Oct 2026; "
                "industrial fixed monthly fees not reported", url=URL["attaqa_2026"]),
    dict(id="T3", value=0.26, label="Upper reform bound: 26 halalas", status="assumption (v1.0 range maximum)",
         effective="hypothetical", source="Upper end of the v1.0 triangular range; no published source", url=""),
]

# Evidence collected for the grid emission factor (none replaces the 0.55 project factor; see ef_grid).
EF_GRID_EVIDENCE = [
    dict(value=0.568, unit="tCO2/MWh", what="Saudi DNA, 'Development of the Kingdom's Updated Grid Emission Factor 2021'",
         access="Primary PDF not retrievable by the audit tools; value taken from KFUPM GHG inventories (Apr 2024; 2024 v2) "
                "which cite it. Factor type (operating/combined margin vs average) not confirmed",
         url=URL["kfupm_2024"], use="Scenario E1"),
    dict(value=0.475, unit="tCO2/MWh", what="IFI harmonised default grid factors v2.0 (Jul 2019), combined margin, firm energy",
         access="UNFCCC-hosted PDF", url=URL["ifi_2019"], use="Context only: a marginal (crediting) factor, not a location-based inventory factor"),
    dict(value=0.650, unit="tCO2/MWh", what="IFI harmonised default grid factors v2.0 (Jul 2019), combined margin, intermittent energy",
         access="UNFCCC-hosted PDF", url=URL["ifi_2019"], use="Context only: a marginal (crediting) factor, not a location-based inventory factor"),
]
EF_GRID_SCENARIOS = [dict(id="E0", value=0.55, label="v1.2 project factor 0.55 (source not located)"),
                     dict(id="E1", value=0.568, label="Saudi DNA 2021 GEF 0.568 (as cited)"),
                     dict(id="E2", value=0.573, label="BTR1 2021 / GASTAT 2021 derived 0.573 (reference since v1.3)")]
EF_GRID_EVIDENCE.insert(0, dict(value=0.573, unit="tCO2e/MWh generated", what="Derived: KSA BTR1 (UNFCCC, Mar 2025) Table 6, 1.A.1.a.i "
                                "electricity generation 2021 = 205,579 Gg CO2e / GASTAT 2021 generation 358,640 GWh",
                                access="Both primary documents retrieved (BTR1 PDF; GASTAT 2021 Arabic PDF gives 359 TWh)",
                                url=URL["ksa_btr1"], use="Reference factor since v1.3 (scenario E2)"))
EF_GRID_EVIDENCE.append(dict(value=0.682, unit="tCO2e/MWh consumed", what="Same emissions / GASTAT 2021 consumption 301,600 GWh",
                             access="Derived; the 16% gap includes T&D losses and own use", url=URL["argaam_gastat_2021"],
                             use="Context: a consumption-based factor would add T&D losses, which GHG Protocol places in Scope 3 Cat 3"))

# Industrial natural-gas (methane) price scenarios (A5)
GAS_SCENARIOS = [
    dict(id="G0", value=2.15, label="2025 regulated methane price (reference)", status="secondary (Al Jazira Capital summary of Aramco notices)",
         effective="from 1 Jan 2025", url=URL["ajc_2025"]),
    dict(id="G1", value=2.47, label="2026 reported +10-20% (midpoint +15%)", status="reported by a secondary source; no official figure",
         effective="from 1 Jan 2026", url=URL["mm_2026"]),
    dict(id="G2", value=3.00, label="v1.2 anchor (KAPSARC DP49 modelling value)", status="study anchor, not a price", effective="n/a",
         url=URL["kapsarc_ro"]),
]
# Rooftop PV capital-cost scenarios (A5)
PV_CAPEX_SCENARIOS = [
    dict(id="P0", value=2500, label="Riyadh rooftop benchmark SAR 2.5/W (reference)", url=URL["knightfrank_2025"]),
    dict(id="P1", value=3750, label="v1.2 assumption SAR 3.75/W (no direct source)", url=URL["irena2024"]),
]

PROJECTS = {
    "A": "Rooftop solar PV (1,000 kWp)",
    "B": "High-efficiency motors + variable-speed drives",
    "C": "Compressed-air leak repair & controls",
    "D": "Furnace waste-heat recovery",
    "E": "Forklift electrification (12 units)",
    "F": "Lower-carbon steel supplier (3,000 t/yr)",
}
SCOPE12_PROJECTS = ("A", "B", "C", "D", "E")   # F reduces Scope 3 only (not counted toward the Scope 1+2 target)


def v(key):
    return P[key].value


def base_values():
    return {k: p.value for k, p in P.items()}


def gas_price_sar_per_gj(usd_mmbtu):
    return usd_mmbtu * SAR_PER_USD / GJ_PER_MMBTU


# ------------------------------------------------------------------ register profiles (A5): reproduce v1.2 for comparison
V12_CHANGES = {
    "ef_grid": dict(value=0.55, status="provisional", dist=("normal_rel", 0.05)),
    "gas_price_usd": dict(value=3.0, status="transferred", dist=("lognormal", 0.25)),
    "pv_capex_kw": dict(value=3750, status="hypothetical", dist=("normal_rel", 0.10)),
    "pv_yield": dict(value=1850, dist=("triangular", 1650, 1850, 1950)),
    "pv_degradation": dict(value=0.0, dist=None),
    "c_saving_frac": dict(value=0.25, dist=("uniform", 0.15, 0.30)),
    "c_om": dict(value=0.0),
    "tree_g_reform": dict(value=4.5),
    "e_kwh_per_l": dict(status="derived", evidence="derived"),     # label correction only; value unchanged
}
A5_CHANGE_LABELS = {
    "ef_grid": "Grid factor 0.55 -> 0.573 (BTR1/GASTAT 2021)",
    "gas_price_usd": "Gas price $3.00 -> $2.15/MMBtu (2025 regulated methane)",
    "tree_g_reform": "Reform gas price 4.5 -> 3.225 (+50% on the new price)",
    "pv_capex_kw": "PV cost SAR 3,750 -> 2,500/kWp (Riyadh benchmark), sd 10% -> 15%",
    "pv_yield": "PV yield range upper 1,950 -> 2,010",
    "pv_degradation": "PV degradation 0 -> 0.5%/yr",
    "c_saving_frac": "Compressed-air savings 25% -> 20% (range 10-30%)",
    "c_om": "Leak-management cost 0 -> SAR 15,000/yr",
    "e_kwh_per_l": "Status derived -> hypothetical (assumed efficiencies, no source); value unchanged",
}
_CURRENT = dict(P)


@contextmanager
def use_profile(name="v1.2", keys=None):
    """Temporarily replace register entries: name 'v1.2' restores the v1.2 values for `keys` (default: all A5 changes)."""
    assert name == "v1.2", name
    keys = list(V12_CHANGES) if keys is None else list(keys)
    saved = {k: P[k] for k in keys}
    try:
        for k in keys:
            P[k] = replace(P[k], **V12_CHANGES[k])
        yield
    finally:
        P.update(saved)
