"""Builds CARBON_IQ_Data_Model.xlsx.

Deterministic calculations are LIVE Excel formulas (baseline, uncertainty propagation, project economics, cash flows,
the 64-portfolio enumeration, the reform decision tree, the GBM trigger). Simulation-based results (Monte Carlo,
value of information, global sensitivity, LSMC) are written as values computed by the Python prototype and labelled.
"""
import itertools

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .assumptions import MODEL_VERSION, P, PROJECTS
from .engine import u95

FONT = "Arial"
NAVY = "1F3A5F"
F_IN = Font(name=FONT, size=10, color="0000FF")
F_CALC = Font(name=FONT, size=10, color="000000")
F_LINK = Font(name=FONT, size=10, color="008000")
F_PY = Font(name=FONT, size=10, color="7030A0")
F_HDR = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_TITLE = Font(name=FONT, size=14, bold=True, color=NAVY)
F_SUB = Font(name=FONT, size=9, italic=True, color="555555")
F_B = Font(name=FONT, size=10, bold=True)
FILL_HDR = PatternFill("solid", fgColor=NAVY)
FILL_KEY = PatternFill("solid", fgColor="FFF2CC")
FILL_STATUS = {"verified": PatternFill("solid", fgColor="D9EAD3"), "derived": PatternFill("solid", fgColor="DDEBF7"),
               "transferred": PatternFill("solid", fgColor="E2EFDA"), "provisional": PatternFill("solid", fgColor="FFF2CC"),
               "hypothetical": PatternFill("solid", fgColor="FCE4D6")}
THIN = Side(style="thin", color="C9D1DB")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
STATUS_DV = '"verified,derived,transferred,provisional,hypothetical"'


class Book:
    def __init__(self):
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ref = {}

    def sheet(self, name, title, subtitle, widths):
        ws = self.wb.create_sheet(name)
        ws["A1"] = title; ws["A1"].font = F_TITLE
        ws["A2"] = subtitle; ws["A2"].font = F_SUB
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.sheet_view.showGridLines = False
        return ws

    def header(self, ws, row, labels):
        for j, h in enumerate(labels, start=1):
            c = ws.cell(row, j, h); c.font = F_HDR; c.fill = FILL_HDR; c.border = BOX
            c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.freeze_panes = ws.cell(row + 1, 1)

    def param_table(self, ws, row, keys, extra_rows=()):
        """Rows: key | description | value | unit | status | source/rationale | 95% range / distribution | URL."""
        self.header(ws, row, ["Key", "Description", "Value", "Unit", "Status", "Source / rationale", "Uncertainty (distribution)", "Link"])
        dv = DataValidation(type="list", formula1=STATUS_DV, allow_blank=False)
        ws.add_data_validation(dv)
        r = row + 1
        for k in keys:
            p = P[k]
            vals = [k, p.note or p.source.split(";")[0], p.value, p.unit, p.status, p.source, _dist_text(p), p.url]
            for j, val in enumerate(vals, start=1):
                c = ws.cell(r, j, val); c.border = BOX; c.font = F_CALC
                c.alignment = Alignment(wrap_text=j in (2, 6, 7), vertical="top")
            ws.cell(r, 2).value = _describe(k)
            ws.cell(r, 3).font = F_IN
            ws.cell(r, 5).fill = FILL_STATUS[p.status]
            if p.url:
                ws.cell(r, 8).hyperlink = p.url; ws.cell(r, 8).value = "source"; ws.cell(r, 8).font = Font(name=FONT, size=10, color="1F5FA8", underline="single")
            dv.add(ws.cell(r, 5))
            nd = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=False,
                                error="Must be a non-negative number", showErrorMessage=True)
            ws.add_data_validation(nd); nd.add(ws.cell(r, 3))
            self.ref[k] = f"'{ws.title}'!$C${r}"
            r += 1
        for label, formula, unit, key, note in extra_rows:
            ws.cell(r, 1, key); ws.cell(r, 2, label); c = ws.cell(r, 3, formula); c.font = F_CALC
            ws.cell(r, 4, unit); ws.cell(r, 5, "derived").fill = FILL_STATUS["derived"]; ws.cell(r, 6, note)
            for j in range(1, 9):
                ws.cell(r, j).border = BOX
                ws.cell(r, j).alignment = Alignment(wrap_text=j in (2, 6), vertical="top")
            self.ref[key] = f"'{ws.title}'!$C${r}"
            r += 1
        return r


DESCR = {
    "tariff": "Industrial electricity tariff", "diesel_price": "Diesel price", "gas_price_usd": "Industrial natural-gas price",
    "discount_rate": "Real discount rate", "budget": "Capital budget for decarbonization", "target_share": "Scope 1+2 reduction target",
    "chance_level": "Required probability of meeting the target", "elec_mwh": "Grid electricity purchased",
    "gas_gj": "Natural gas burned (process heat)", "diesel_forklift_l": "Diesel, forklifts", "diesel_genset_l": "Diesel, backup generators",
    "steel_t": "Purchased steel", "freight_tkm": "Inbound road freight", "production_t": "Finished output",
    "motor_share": "Non-compressor motor systems share of electricity", "compressed_air_share": "Compressed-air share of electricity",
    "ef_grid": "Grid electricity emission factor (location-based)", "ef_gas": "Natural gas emission factor (CO2e, NCV)",
    "ef_diesel": "Diesel emission factor", "ef_freight": "Road freight emission factor",
    "ef_steel_incumbent": "Steel factor, incumbent supplier (proxy)", "ef_steel_alt": "Steel factor, alternative supplier (proxy)",
    "pv_kwp": "Solar PV size", "pv_yield": "Specific PV yield", "pv_capex_kw": "PV installed cost", "pv_om_frac": "PV fixed O&M",
    "pv_life": "PV life", "pv_degradation": "PV output degradation", "c_om": "C leak-management cost", "b_capex": "B capital cost", "b_saving_frac": "B savings on non-compressor motor electricity",
    "b_comp_frac": "B savings on compressor-motor electricity", "b_life": "B life", "c_capex": "C capital cost",
    "c_saving_frac": "C savings on compressed-air electricity", "c_life": "C life", "d_capex": "D capital cost",
    "d_saving_frac": "D share of gas displaced", "d_om": "D maintenance", "d_life": "D life", "e_capex": "E incremental capital cost",
    "e_kwh_per_l": "E electricity per litre of diesel displaced", "e_maint_saving": "E maintenance saving", "e_life": "E life",
    "f_steel_t": "F steel volume switched", "f_premium": "F price premium", "f_onboard": "F onboarding (one-time)",
    "f_life": "F contract horizon", "cost_motor_audit": "Cost: motor-system audit", "audit_error_sd": "Audit measurement error",
    "cost_submeter": "Cost: compressed-air sub-metering", "cost_supplier_data": "Cost: supplier-specific steel data",
    "cost_pv_study": "Cost: PV yield study", "ro_kappa": "Mean-reversion rate (log-OU)", "ro_sigma": "Gas-price log-volatility",
    "ro_mu_gbm": "GBM drift (benchmark)", "ro_horizon": "Deferral window", "ro_paths": "LSMC paths",
    "tree_p_reform": "Probability of gas-price reform within 1 year", "tree_g_reform": "Gas price after reform",
}


def _describe(k):
    return DESCR.get(k, k)


def _dist_text(p):
    d = p.dist
    if d is None:
        return "fixed"
    if d[0] == "normal_rel":
        return f"normal, s.d. {d[1]:.1%} of value"
    if d[0] == "uniform":
        return f"uniform {d[1]:g} to {d[2]:g}"
    if d[0] == "triangular":
        return f"triangular min {d[1]:g}, mode {d[2]:g}, max {d[3]:g}"
    if d[0] == "lognormal":
        return f"lognormal, log-s.d. {d[1]:g} (mean-preserving)"
    return str(d)


def build(res, path):
    B = Book()
    R = B.ref
    # ------------------------------------------------------------------ README
    ws = B.sheet("README", "CARBON IQ - Data Model", "Research prototype. Synthetic facility data; not a real Saudi company. October 2026.",
                 [26, 70, 18, 18])
    lines = [
        ("Purpose", "Traceable data and calculations behind the CARBON IQ decision-support prototype (hypothetical Riyadh-region metal-fabrication plant)."),
        ("How to use", "Edit BLUE input cells only. Black cells are formulas; green cells link to other sheets; purple cells are results written by the Python prototype (run_all.py) and do NOT update when inputs change - re-run Python."),
        ("Status column", "verified = cited public source, applicable here; derived = calculated from verified values; transferred = cited source from a different context (country, sector or study); provisional = partial or secondary evidence, or a change announced - see Decision Objectives sheet for scenarios; hypothetical = illustrative case assumption."),
        ("Live in Excel", "Baseline emissions, uncertainty propagation, project economics, cash flows, all 64 portfolios and the optimum, decision tree, GBM trigger."),
        ("From Python", "Monte Carlo (20,000 scenarios, seed 20261024), chance-constrained choice, value of information, global sensitivity, LSMC real options."),
        ("Agreement", "tests/test_outputs.py recalculates this file (LibreOffice, carbon_iq/recalc.py) and checks that Excel formulas equal the Python engine."),
        ("Version", f"Model v{MODEL_VERSION} (A5 carbon and financial data strengthening, 26 Oct 2026). Changes and their effects: sheet A5 Changes and CHANGELOG.md."),
        ("Evidence class", "Since v1.3 each input also has an evidence class: external (cited source), derived (computed from external values), hypothetical (case assumption), measured (none: the facility is synthetic) - see sheet Source Register."),
        ("Units", "SAR (real, 2026), tCO2e, MWh, GJ (net calorific value), litres, tonne-km. Percentages stored as fractions."),
        ("Limitations", "Prototype only: not a verified GHG inventory, investment advice or a production decision system."),
    ]
    B.header(ws, 4, ["Item", "Description"])
    for i, (a, b) in enumerate(lines, start=5):
        ws.cell(i, 1, a).font = F_B; c = ws.cell(i, 2, b); c.alignment = Alignment(wrap_text=True, vertical="top"); c.font = F_CALC
        ws.row_dimensions[i].height = 30
    r0 = 5 + len(lines) + 1
    ws.cell(r0, 1, "Sheet guide and data dictionary").font = F_B
    guide = [("Facility Profile", "Case definition: boundary, budget, target, risk appetite"),
             ("Production & Operations", "Monthly production and operating hours (synthetic)"),
             ("Electricity & Fuel", "Monthly energy use, prices and end-use shares"),
             ("Suppliers & Logistics", "Purchased steel, freight and supplier-switch inputs"),
             ("Emission Factors", "Factors with sources, units and status"),
             ("Baseline Emissions", "Activity x factor by source and scope (formulas)"),
             ("Data Quality", "GHG Protocol first-order uncertainty propagation (formulas)"),
             ("Investment Alternatives", "Project inputs and physical effects (formulas)"),
             ("Financials & Cash Flows", "Annuity factors, NPV, MAC, payback, yearly cash flows (formulas)"),
             ("Optimization", "All 64 portfolios evaluated by formula; best feasible portfolio; ranking baselines"),
             ("Monte Carlo", "Simulation results by portfolio, incl. capital-cost overrun risk (Python values)"),
             ("Decision Objectives", "Three decision objectives, reporting basis, budget risk, tariff and grid-factor scenarios"),
             ("Value of Information", "EVPI, EVPPI, EVSI vs collection cost (Python values + formulas)"),
             ("Sensitivity", "Tornado, first-order indices, switch points (Python values)"),
             ("Investment Timing", "Reform decision tree and GBM trigger (formulas); LSMC scan (Python values)"),
             ("Source Register", "Every input with status, evidence class, publication date, effective period, geography and URL (A5)"),
             ("A5 Changes", "Before/after: v1.2 register, each A5 change alone, and v1.3 (Python values)"),
             ("Dashboard", "Management summary linked to the sheets above")]
    B.header(ws, r0 + 1, ["Sheet", "Contents"])
    for i, (a, b) in enumerate(guide, start=r0 + 2):
        ws.cell(i, 1, a).font = F_CALC; ws.cell(i, 2, b).font = F_CALC
    ws.freeze_panes = None
    leg = r0 + len(guide) + 3
    ws.cell(leg, 1, "Colour legend").font = F_B
    for i, (txt, font) in enumerate([("Blue = input", F_IN), ("Black = formula", F_CALC), ("Green = link", F_LINK),
                                     ("Purple = Python result (static)", F_PY)], start=leg + 1):
        ws.cell(i, 1, txt).font = font

    # ------------------------------------------------------------------ Facility Profile
    ws = B.sheet("Facility Profile", "Facility profile (hypothetical case)", "Medium-sized metal fabrication and assembly plant, Riyadh region. Operational control boundary.",
                 [20, 44, 14, 16, 13, 60, 30, 10])
    info = [("Facility", "Hypothetical metal-fabrication & assembly plant"), ("Location", "Riyadh region, Saudi Arabia"),
            ("Boundary", "Operational control; Scope 1, Scope 2 (location-based), Scope 3 Cat 1 (steel) and Cat 4 (inbound freight)"),
            ("Reporting year", "Annual basis, 2026 prices"), ("Data status", "SYNTHETIC - illustrative, not company data")]
    for i, (a, b) in enumerate(info, start=4):
        ws.cell(i, 1, a).font = F_B; ws.cell(i, 2, b).font = F_CALC
    B.param_table(ws, 10, ["production_t", "budget", "target_share", "chance_level"])

    # ------------------------------------------------------------------ Production & Operations (monthly synthetic)
    ws = B.sheet("Production & Operations", "Production and operations (synthetic monthly data)",
                 "Seasonal profile is illustrative; annual totals feed the model.", [12, 18, 18, 18])
    B.header(ws, 4, ["Month", "Output (t)", "Operating hours", "Energy intensity (MWh/t)"])
    w_prod = [0.080, 0.078, 0.084, 0.086, 0.088, 0.083, 0.078, 0.080, 0.085, 0.088, 0.087, 0.083]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for i, (m, wgt) in enumerate(zip(months, w_prod), start=5):
        ws.cell(i, 1, m).font = F_CALC
        ws.cell(i, 2, f"={R['production_t']}*{wgt}").font = F_LINK
        ws.cell(i, 3, 2 * 8 * (22 if m not in ("Mar", "Apr") else 20)).font = F_IN
        ws.cell(i, 4, f"='Electricity & Fuel'!B{i}/B{i}").font = F_CALC
    ws.cell(17, 1, "Total").font = F_B
    ws.cell(17, 2, "=SUM(B5:B16)").font = F_CALC
    ws.cell(17, 3, "=SUM(C5:C16)").font = F_CALC
    ws.cell(17, 4, "='Electricity & Fuel'!B17/B17").font = F_CALC
    ws.cell(18, 1, "Weights sum to 1.000; operating hours: 2 shifts x 8 h x working days (assumption).").font = F_SUB

    # ------------------------------------------------------------------ Electricity & Fuel
    ws = B.sheet("Electricity & Fuel", "Electricity and fuel", "Monthly synthetic metered data (blue) and prices with sources.",
                 [20, 44, 14, 16, 13, 60, 30, 10])
    B.header(ws, 4, ["Month", "Electricity (MWh)", "Natural gas (GJ)", "Diesel forklifts (L)", "Diesel generators (L)"])
    w_el = [0.072, 0.070, 0.078, 0.084, 0.092, 0.095, 0.098, 0.098, 0.090, 0.082, 0.072, 0.069]
    w_el[-1] = round(1 - sum(w_el[:-1]), 6)
    for i, (m, we, wp) in enumerate(zip(months, w_el, w_prod), start=5):
        ws.cell(i, 1, m).font = F_CALC
        ws.cell(i, 2, round(P["elec_mwh"].value * we, 4)).font = F_IN
        ws.cell(i, 3, round(P["gas_gj"].value * wp, 4)).font = F_IN
        ws.cell(i, 4, round(P["diesel_forklift_l"].value / 12, 4)).font = F_IN
        ws.cell(i, 5, round(P["diesel_genset_l"].value * (0.04 if m not in ("Jun", "Jul", "Aug") else 0.2), 4)).font = F_IN
    # make totals exact
    for col, key in ((2, "elec_mwh"), (3, "gas_gj"), (4, "diesel_forklift_l"), (5, "diesel_genset_l")):
        s = sum(ws.cell(i, col).value for i in range(5, 16))
        ws.cell(16, col, round(P[key].value - s, 4))
    ws.cell(17, 1, "Annual total").font = F_B
    for col in range(2, 6):
        ws.cell(17, col, f"=SUM({get_column_letter(col)}5:{get_column_letter(col)}16)").font = F_CALC
    R["elec_mwh"], R["gas_gj"] = "'Electricity & Fuel'!$B$17", "'Electricity & Fuel'!$C$17"
    R["diesel_forklift_l"], R["diesel_genset_l"] = "'Electricity & Fuel'!$D$17", "'Electricity & Fuel'!$E$17"
    B.param_table(ws, 20, ["tariff", "diesel_price", "gas_price_usd", "motor_share", "compressed_air_share"],
                        extra_rows=[("Gas price in SAR per GJ", f"={R.get('gas_price_usd', 'C23')}*3.75/1.055056", "SAR/GJ", "gas_sar_gj",
                                     "USD/MMBtu x 3.75 SAR/USD / 1.055056 GJ/MMBtu"),
                                    ("Compressed-air electricity", None, "MWh/yr", "comp_mwh", "Electricity x compressed-air share"),
                                    ("Non-compressor motor electricity", None, "MWh/yr", "motor_mwh", "Electricity x motor share")])
    ws.cell(int(R["gas_sar_gj"].split("$")[-1]), 3).value = f"={R['gas_price_usd']}*3.75/1.055056"
    ws.cell(int(R["comp_mwh"].split("$")[-1]), 3).value = f"={R['elec_mwh']}*{R['compressed_air_share']}"
    ws.cell(int(R["motor_mwh"].split("$")[-1]), 3).value = f"={R['elec_mwh']}*{R['motor_share']}"

    # ------------------------------------------------------------------ Suppliers & Logistics
    ws = B.sheet("Suppliers & Logistics", "Suppliers and logistics", "Purchased materials, freight and the supplier-switch option (F).",
                 [20, 44, 14, 16, 13, 60, 30, 10])
    B.param_table(ws, 4, ["steel_t", "freight_tkm", "f_steel_t", "f_premium", "f_onboard", "f_life"])

    # ------------------------------------------------------------------ Emission Factors
    ws = B.sheet("Emission Factors", "Emission factors", "Every factor with unit, source and verification status.",
                 [20, 44, 14, 16, 13, 60, 30, 10])
    r = B.param_table(ws, 4, ["ef_grid", "ef_diesel", "ef_freight", "ef_steel_incumbent", "ef_steel_alt"])
    ws.cell(r + 1, 1, "Natural gas factor built from IPCC 2006 Vol.2 Table 2.3 (manufacturing) and AR5 GWPs").font = F_B
    comp = [("CO2", 56100, "kg/TJ"), ("CH4", 1, "kg/TJ"), ("N2O", 0.1, "kg/TJ"), ("GWP CH4 (AR5)", 28, ""), ("GWP N2O (AR5)", 265, "")]
    for i, (a, b, u) in enumerate(comp, start=r + 2):
        ws.cell(i, 1, a); c = ws.cell(i, 3, b); c.font = F_IN; ws.cell(i, 4, u); ws.cell(i, 5, "verified").fill = FILL_STATUS["verified"]
    g = r + 2
    ws.cell(g + 5, 1, "ef_gas"); ws.cell(g + 5, 2, "Natural gas emission factor (CO2e, NCV)")
    ws.cell(g + 5, 3, f"=(C{g}+C{g+1}*C{g+3}+C{g+2}*C{g+4})/1000000").font = F_CALC
    ws.cell(g + 5, 4, "tCO2e/GJ"); ws.cell(g + 5, 5, "derived").fill = FILL_STATUS["derived"]
    ws.cell(g + 5, 6, P["ef_gas"].source)
    R["ef_gas"] = f"'Emission Factors'!$C${g+5}"

    # ------------------------------------------------------------------ Baseline Emissions
    ws = B.sheet("Baseline Emissions", "Baseline emissions (GHG Protocol: activity x emission factor)",
                 "All cells are formulas linked to the input sheets.", [14, 16, 34, 16, 10, 16, 16])
    B.header(ws, 4, ["Source ID", "Scope", "Source", "Activity", "Unit", "EF (t/unit)", "Emissions (tCO2e)"])
    src = [("S1-GAS", "Scope 1", "Natural gas, process heat", "gas_gj", "GJ", "ef_gas"),
           ("S1-DSL-FL", "Scope 1", "Diesel, forklifts", "diesel_forklift_l", "L", "ef_diesel"),
           ("S1-DSL-GEN", "Scope 1", "Diesel, backup generators", "diesel_genset_l", "L", "ef_diesel"),
           ("S2-ELEC", "Scope 2", "Grid electricity (location-based)", "elec_mwh", "MWh", "ef_grid"),
           ("S3-C1-STEEL", "Scope 3", "Purchased steel (Cat 1)", "steel_t", "t", "ef_steel_incumbent"),
           ("S3-C4-FRT", "Scope 3", "Inbound road freight (Cat 4)", "freight_tkm", "t-km", "ef_freight")]
    for i, (sid, scope, name, ak, unit, ek) in enumerate(src, start=5):
        ws.cell(i, 1, sid); ws.cell(i, 2, scope); ws.cell(i, 3, name)
        ws.cell(i, 4, f"={R[ak]}").font = F_LINK; ws.cell(i, 5, unit)
        ws.cell(i, 6, f"={R[ek]}").font = F_LINK
        ws.cell(i, 7, f"=D{i}*F{i}").font = F_CALC
        ws.cell(i, 4).number_format = "#,##0"; ws.cell(i, 6).number_format = "0.000000"; ws.cell(i, 7).number_format = "#,##0.0"
        R["em_" + sid] = f"'Baseline Emissions'!$G${i}"
    tots = [("Scope 1", '=SUMIF(B5:B10,"Scope 1",G5:G10)'), ("Scope 2", '=SUMIF(B5:B10,"Scope 2",G5:G10)'),
            ("Scope 3", '=SUMIF(B5:B10,"Scope 3",G5:G10)'), ("Scope 1+2", "=G12+G13"), ("Total", "=G15+G14"),
            ("Target reduction (t/yr)", f"={R['target_share']}*G15")]
    for i, (a, f) in enumerate(tots, start=12):
        ws.cell(i, 3, a).font = F_B; c = ws.cell(i, 7, f); c.font = F_CALC; c.number_format = "#,##0.0"
    R.update({"S1": "'Baseline Emissions'!$G$12", "S2": "'Baseline Emissions'!$G$13", "S3": "'Baseline Emissions'!$G$14",
              "S12": "'Baseline Emissions'!$G$15", "TOT": "'Baseline Emissions'!$G$16", "TARGET": "'Baseline Emissions'!$G$17"})
    ws["G17"].fill = FILL_KEY

    # ------------------------------------------------------------------ Data Quality
    ws = B.sheet("Data Quality", "Data quality and uncertainty (GHG Protocol first-order propagation)",
                 "U = 95% half-width as % of mean. Source: U = SQRT(Ua^2+Uef^2); total: SQRT(SUMSQ(E x U))/SUM(E). Valid when each U < 60%.",
                 [14, 34, 16, 14, 14, 16, 18, 12, 14])
    B.header(ws, 4, ["Source ID", "Source", "Emissions (t)", "U activity (±%)", "U factor (±%)", "U combined (±%)", "E x U (t·%)", "Quality", "First-order valid"])
    akeys = {"S1-GAS": ("gas_gj", "ef_gas"), "S1-DSL-FL": ("diesel_forklift_l", "ef_diesel"), "S1-DSL-GEN": ("diesel_genset_l", "ef_diesel"),
             "S2-ELEC": ("elec_mwh", "ef_grid"), "S3-C1-STEEL": ("steel_t", "ef_steel_incumbent"), "S3-C4-FRT": ("freight_tkm", "ef_freight")}
    for i, (sid, scope, name, *_rest) in enumerate(src, start=5):
        ka, ke = akeys[sid]
        ws.cell(i, 1, sid); ws.cell(i, 2, name)
        ws.cell(i, 3, f"={R['em_' + sid]}").font = F_LINK
        c = ws.cell(i, 4, round(u95(ka), 4)); c.font = F_IN
        c.comment = Comment("95% half-width of activity data, from the assumption register (same input as the Monte Carlo)", "CARBON IQ")
        c = ws.cell(i, 5, round(u95(ke), 4)); c.font = F_IN
        c.comment = Comment("Derived from the factor's distribution in the assumption register", "CARBON IQ")
        ws.cell(i, 6, f"=SQRT(D{i}^2+E{i}^2)").font = F_CALC
        ws.cell(i, 7, f"=C{i}*F{i}").font = F_CALC
        ws.cell(i, 8, f'=IF(F{i}<=5,"High",IF(F{i}<=15,"Good",IF(F{i}<=30,"Fair","Poor")))').font = F_CALC
        ws.cell(i, 9, f'=AND(D{i}<60,E{i}<60)').font = F_CALC
        for col in (3, 7):
            ws.cell(i, col).number_format = "#,##0.0"
        for col in (4, 5, 6):
            ws.cell(i, col).number_format = "0.0"
    rows_u = [("Scope 1", "5:7"), ("Scope 2", "8:8"), ("Scope 3", "9:10"), ("Scope 1+2", "5:8"), ("Total", "5:10")]
    for i, (a, rg) in enumerate(rows_u, start=12):
        lo, hi = rg.split(":")
        ws.cell(i, 2, a).font = F_B
        ws.cell(i, 3, f"=SUM(C{lo}:C{hi})").font = F_CALC
        ws.cell(i, 6, f"=SQRT(SUMSQ(G{lo}:G{hi}))/C{i}").font = F_CALC
        ws.cell(i, 3).number_format = "#,##0.0"; ws.cell(i, 6).number_format = "0.00"
        R["U_" + a] = f"'Data Quality'!$F${i}"
    ws.cell(18, 1, "Monte Carlo check (Python, 20,000 scenarios): Scope 1+2 95% half-width").font = F_SUB
    c = ws.cell(18, 6, round(res["mc_baseline_scope12"]["u95_pct"], 4)); c.font = F_PY; c.number_format = "0.00"
    ws.cell(19, 1, "Scale (GHG Protocol uncertainty guidance, Table 2): High ±5%, Good ±15%, Fair ±30%, Poor >30%.").font = F_SUB

    # ------------------------------------------------------------------ Investment Alternatives
    ws = B.sheet("Investment Alternatives", "Investment alternatives (inputs and physical effects)",
                 "Six candidate projects. Effects are computed on the shared activity ledger (formulas).", [20, 44, 14, 16, 13, 60, 30, 10])
    keys = ["pv_kwp", "pv_yield", "pv_capex_kw", "pv_om_frac", "pv_life", "pv_degradation", "b_capex", "b_saving_frac", "b_comp_frac",
            "b_life", "c_capex", "c_saving_frac", "c_om", "c_life", "d_capex", "d_saving_frac", "d_om", "d_life", "e_capex", "e_kwh_per_l",
            "e_maint_saving", "e_life"]
    r = B.param_table(ws, 4, keys)
    r += 1
    ws.cell(r, 1, "Physical effects per project (formulas)").font = F_B
    r += 1
    B.header(ws, r, ["Project", "Description", "Capex (SAR)", "Electricity change (MWh/yr)", "Gas change (GJ/yr)",
                     "Diesel change (L/yr)", "Steel-factor change (t/yr)", "Life (yr)"])
    T = R["tariff"]
    eff = {
        "A": (f"={R['pv_kwp']}*{R['pv_capex_kw']}", f"=-{R['pv_kwp']}*{R['pv_yield']}/1000", "=0", "=0", "=0", f"={R['pv_life']}"),
        "B": (f"={R['b_capex']}", f"=-({R['motor_mwh']}*{R['b_saving_frac']}+{R['comp_mwh']}*{R['b_comp_frac']})", "=0", "=0", "=0", f"={R['b_life']}"),
        "C": (f"={R['c_capex']}", f"=-{R['comp_mwh']}*{R['c_saving_frac']}", "=0", "=0", "=0", f"={R['c_life']}"),
        "D": (f"={R['d_capex']}", "=0", f"=-{R['gas_gj']}*{R['d_saving_frac']}", "=0", "=0", f"={R['d_life']}"),
        "E": (f"={R['e_capex']}", f"={R['diesel_forklift_l']}*{R['e_kwh_per_l']}/1000", "=0", f"=-{R['diesel_forklift_l']}", "=0", f"={R['e_life']}"),
        "F": (f"={R['f_onboard']}", "=0", "=0", "=0", f"={R['f_steel_t']}*({R['ef_steel_alt']}-{R['ef_steel_incumbent']})", f"={R['f_life']}"),
    }
    for i, (pid, cells) in enumerate(eff.items(), start=r + 1):
        ws.cell(i, 1, pid).font = F_B; ws.cell(i, 2, PROJECTS[pid])
        for j, fml in enumerate(cells, start=3):
            c = ws.cell(i, j, fml); c.font = F_CALC; c.number_format = "#,##0.0"
        R["row_" + pid] = i
    R["eff_sheet"] = "'Investment Alternatives'"
    ov = r + 8
    ws.cell(ov, 1, "Overlap B-C").font = F_B
    ws.cell(ov, 2, "B's compressor-motor saving applies only to load left after C (counted once)")
    ws.cell(ov, 4, f"={R['comp_mwh']}*{R['b_comp_frac']}*{R['c_saving_frac']}").font = F_CALC
    ws.cell(ov, 4).number_format = "#,##0.00"
    R["ov_mwh"] = f"'Investment Alternatives'!$D${ov}"

    # ------------------------------------------------------------------ Financials & Cash Flows
    ws = B.sheet("Financials & Cash Flows", "Financial evaluation", "NPV = -Capex + annual cash flow x annuity factor (PV energy: degraded "
                 "factor (1-((1-d)/(1+r))^n)/(r+d)); MAC = -NPV / (discount factor x year-1 tCO2e).",
                 [20, 44, 14, 16, 13, 60, 30, 10])
    r = B.param_table(ws, 4, ["discount_rate"])
    r += 1
    B.header(ws, r, ["Project", "Annual net cash flow (SAR/yr)", "Annuity factor", "NPV (SAR)", "Scope 1+2 reduction (t/yr)",
                     "Scope 3 reduction (t/yr)", "MAC (SAR/tCO2e)", "Simple payback (yr)", "Discount factor for energy and tonnes"])
    ea = "'Investment Alternatives'!"
    rate = R["discount_rate"]
    for i, pid in enumerate("ABCDEF", start=r + 1):
        er = R["row_" + pid]
        capex, d_el, d_gas, d_dsl, d_st, life = (f"{ea}$C${er}", f"{ea}$D${er}", f"{ea}$E${er}", f"{ea}$F${er}", f"{ea}$G${er}", f"{ea}$H${er}")
        cf = {"A": f"=-{d_el}*{T}*1000-{R['pv_om_frac']}*{capex}", "B": f"=-{d_el}*{T}*1000", "C": f"=-{d_el}*{T}*1000-{R['c_om']}",
              "D": f"=-{d_gas}*{R['gas_sar_gj']}-{R['d_om']}",
              "E": f"=-{d_dsl}*{R['diesel_price']}-{d_el}*{T}*1000+{R['e_maint_saving']}",
              "F": f"=-{R['f_steel_t']}*{R['f_premium']}"}[pid]
        ws.cell(i, 1, f"{pid} {PROJECTS[pid]}").font = F_B
        ws.cell(i, 2, cf).font = F_CALC
        ws.cell(i, 3, f"=(1-(1+{rate})^(-{life}))/{rate}").font = F_CALC
        if pid == "A":      # degrading output: energy revenue discounted with the degraded factor, O&M with the annuity factor
            dg = R["pv_degradation"]
            ws.cell(i, 9, f"=(1-((1-{dg})/(1+{rate}))^{life})/({rate}+{dg})").font = F_CALC
            ws.cell(i, 4, f"=-{capex}+(B{i}+{R['pv_om_frac']}*{capex})*I{i}-{R['pv_om_frac']}*{capex}*C{i}").font = F_CALC
        else:
            ws.cell(i, 9, f"=C{i}").font = F_CALC
            ws.cell(i, 4, f"=-{capex}+B{i}*C{i}").font = F_CALC
        ws.cell(i, 5, f"=-({d_el}*{R['ef_grid']}+{d_gas}*{R['ef_gas']}+{d_dsl}*{R['ef_diesel']})").font = F_CALC
        ws.cell(i, 6, f"=-{d_st}").font = F_CALC
        ws.cell(i, 7, f"=IFERROR(-D{i}/(I{i}*(E{i}+F{i})),\"n/a\")").font = F_CALC
        ws.cell(i, 8, f'=IF(B{i}>0,{capex}/B{i},"never")').font = F_CALC
        for col, fmt in ((2, "#,##0"), (3, "0.000"), (4, "#,##0;(#,##0)"), (5, "#,##0.0"), (6, "#,##0.0"), (7, "#,##0"), (8, "0.0"), (9, "0.000")):
            ws.cell(i, col).number_format = fmt
        R["fin_" + pid] = i
    R["fin_first"] = r + 1
    ovr = r + 8
    ws.cell(ovr, 1, "Overlap B-C").font = F_B
    lifebc = f"MIN({ea}$H${R['row_B']},{ea}$H${R['row_C']})"
    ws.cell(ovr, 4, f"={R['ov_mwh']}*{T}*1000*(1-(1+{rate})^(-{lifebc}))/{rate}").font = F_CALC
    ws.cell(ovr, 5, f"={R['ov_mwh']}*{R['ef_grid']}").font = F_CALC
    ws.cell(ovr, 4).number_format = "#,##0"; ws.cell(ovr, 5).number_format = "#,##0.00"
    R["ov_npv"], R["ov_t"] = f"'Financials & Cash Flows'!$D${ovr}", f"'Financials & Cash Flows'!$E${ovr}"
    # cash-flow table
    ct = ovr + 3
    ws.cell(ct - 1, 1, "Yearly cash flows (SAR, real) and NPV cross-check with Excel NPV()").font = F_B
    hdr = ["Project"] + [f"Y{t}" for t in range(0, 26)] + ["NPV via NPV()"]
    for j, h in enumerate(hdr, start=1):
        c = ws.cell(ct, j, h); c.font = F_HDR; c.fill = FILL_HDR
    for k, pid in enumerate("ABCDEF", start=ct + 1):
        fr = R["fin_" + pid]; er = R["row_" + pid]
        ws.cell(k, 1, pid).font = F_B
        ws.cell(k, 2, f"=-{ea}$C${er}").font = F_CALC
        for t in range(1, 26):
            if pid == "A":
                om = f"{R['pv_om_frac']}*{ea}$C${er}"
                f_ = f"=IF({t}<={ea}$H${er},($B${fr}+{om})*(1-{R['pv_degradation']})^{t - 1}-{om},0)"
            else:
                f_ = f"=IF({t}<={ea}$H${er},$B${fr},0)"
            c = ws.cell(k, 2 + t, f_); c.font = F_CALC; c.number_format = "#,##0"
        ws.cell(k, 28, f"=B{k}+NPV({rate},C{k}:AA{k})").font = F_CALC
        ws.cell(k, 28).number_format = "#,##0"; ws.cell(k, 2).number_format = "#,##0"
    for j in range(2, 29):
        ws.column_dimensions[get_column_letter(j)].width = max(ws.column_dimensions[get_column_letter(j)].width or 0, 11)

    # ------------------------------------------------------------------ Optimization
    ws = B.sheet("Optimization", "Portfolio optimization (exact enumeration of all 64 portfolios, live formulas)",
                 "Maximise NPV subject to budget and Scope 1+2 target; B-C overlap counted once. Python MILP (HiGHS) gives the same optimum.",
                 [16, 6, 6, 6, 6, 6, 6, 14, 14, 14, 12, 11, 11, 11, 16])
    fin = "'Financials & Cash Flows'!"
    ws["A4"] = "Budget (SAR)"; ws["C4"] = f"={R['budget']}"; ws["C4"].font = F_LINK
    ws["A5"] = "Target (t/yr)"; ws["C5"] = f"={R['TARGET']}"; ws["C5"].font = F_LINK
    hr = 7
    B.header(ws, hr, ["Portfolio", "A", "B", "C", "D", "E", "F", "Capex (SAR)", "NPV (SAR)", "Scope 1+2 (t/yr)", "Scope 3 (t/yr)",
                      "Within budget", "Meets target", "Feasible", "NPV if feasible"])
    combos = [c for k in range(7) for c in itertools.combinations("ABCDEF", k)]
    fr0 = R["fin_first"]
    for i, c in enumerate(combos, start=hr + 1):
        ws.cell(i, 1, "+".join(c) or "(none)")
        for j, pid in enumerate("ABCDEF", start=2):
            ws.cell(i, j, 1 if pid in c else 0).font = F_IN
        x = f"$B{i}:$G{i}"
        capcol = f"'Investment Alternatives'!$C${R['row_A']}:$C${R['row_F']}"
        ws.cell(i, 8, f"=SUMPRODUCT({x},TRANSPOSE({capcol}))").font = F_CALC
        ws.cell(i, 8).value = "=" + "+".join(f"{get_column_letter(j)}{i}*'Investment Alternatives'!$C${R['row_' + pid]}" for j, pid in enumerate("ABCDEF", start=2))
        ws.cell(i, 9, "=" + "+".join(f"{get_column_letter(j)}{i}*{fin}$D${fr0 + k}" for k, (j, pid) in enumerate(zip(range(2, 8), "ABCDEF")))
                + f"-C{i}*D{i}*{R['ov_npv']}").font = F_CALC
        ws.cell(i, 10, "=" + "+".join(f"{get_column_letter(j)}{i}*{fin}$E${fr0 + k}" for k, (j, pid) in enumerate(zip(range(2, 8), "ABCDEF")))
                + f"-C{i}*D{i}*{R['ov_t']}").font = F_CALC
        ws.cell(i, 11, "=" + "+".join(f"{get_column_letter(j)}{i}*{fin}$F${fr0 + k}" for k, (j, pid) in enumerate(zip(range(2, 8), "ABCDEF")))).font = F_CALC
        ws.cell(i, 12, f"=H{i}<=$C$4").font = F_CALC
        ws.cell(i, 13, f"=J{i}>=$C$5").font = F_CALC
        ws.cell(i, 14, f"=AND(L{i},M{i})").font = F_CALC
        ws.cell(i, 15, f"=IF(N{i},I{i},-1E+15)").font = F_CALC
        for col, fmt in ((8, "#,##0"), (9, "#,##0;(#,##0)"), (10, "#,##0.0"), (11, "#,##0.0"), (15, "#,##0;(#,##0)")):
            ws.cell(i, col).number_format = fmt
    last = hr + len(combos)
    ws.cell(4, 5, "Optimal portfolio").font = F_B
    ws.cell(4, 8, f"=INDEX(A{hr+1}:A{last},MATCH(MAX(O{hr+1}:O{last}),O{hr+1}:O{last},0))").font = F_CALC
    ws.cell(5, 5, "Optimal NPV (SAR)").font = F_B
    ws.cell(5, 8, f"=MAX(O{hr+1}:O{last})").font = F_CALC; ws.cell(5, 8).number_format = "#,##0"
    ws.cell(6, 5, "Optimal Scope 1+2 (t/yr)").font = F_B
    ws.cell(6, 8, f"=INDEX(J{hr+1}:J{last},MATCH(MAX(O{hr+1}:O{last}),O{hr+1}:O{last},0))").font = F_CALC
    ws.cell(6, 8).number_format = "#,##0.0"
    for cc in ("H4", "H5", "H6"):
        ws[cc].fill = FILL_KEY
    R["OPT_NAME"], R["OPT_NPV"], R["OPT_T"] = "'Optimization'!$H$4", "'Optimization'!$H$5", "'Optimization'!$H$6"
    br = last + 3
    ws.cell(br - 1, 1, "Simpler ranking methods (Python, same inputs) - fund down the list until the budget is used").font = F_B
    B.header(ws, br, ["Method", "", "", "", "", "", "", "Capex (SAR)", "NPV (SAR)", "Scope 1+2 (t/yr)", "Scope 3 (t/yr)", "Meets target"])
    ws.freeze_panes = None
    for i, b in enumerate(res["baselines"], start=br + 1):
        ws.cell(i, 1, f"{b['method']}: {b['portfolio']}").font = F_PY
        for col, key in ((8, "capex"), (9, "npv"), (10, "scope12_t"), (11, "scope3_t")):
            c = ws.cell(i, col, round(b[key], 2)); c.font = F_PY; c.number_format = "#,##0"
        ws.cell(i, 12, bool(b["meets_target"])).font = F_PY

    # ------------------------------------------------------------------ Monte Carlo
    ws = B.sheet("Monte Carlo", "Monte Carlo results (Python, 20,000 joint scenarios, seed 20261024)",
                 "Static values from run_all.py. Portfolios whose QUOTED capex fits the budget, ranked by expected NPV. P(target) uses the PRIMARY "
                 "basis (fixed reporting baseline); 'validation' columns use an independent 200,000-scenario sample.",
                 [18, 14, 14, 14, 14, 12, 14, 12, 14, 14, 14, 14, 14, 14])
    B.header(ws, 4, ["Portfolio", "Quoted capex (SAR)", "Expected NPV", "5th pct NPV", "CVaR 5% NPV", "P(NPV<0)", "E[Scope 1+2 t]",
                     "P(target) primary", "E[Scope 3 t]", "P(capex <= budget)", "90th pct actual capex", "P(target) validation",
                     "P(capex <= budget) validation", "P(target) sampled factors"])
    for i, rr in enumerate(res["mc_portfolios"], start=5):
        vals = [rr["portfolio"], rr["capex"], rr["e_npv"], rr["p5_npv"], rr["cvar5_npv"], rr["p_loss"], rr["e_t12"], rr["p_target"], rr["e_t3"],
                rr["p_budget"], rr["p90_capex"], rr["p_target_val"], rr["p_budget_val"], rr["p_target_physical"]]
        for j, val in enumerate(vals, start=1):
            c = ws.cell(i, j, round(val, 4) if isinstance(val, float) else val); c.font = F_PY
            c.number_format = "0.0%" if j in (6, 8, 10, 12, 13, 14) else "#,##0;(#,##0)"
    rr0 = 5 + len(res["mc_portfolios"]) + 1
    ws.cell(rr0, 1, "Decision rules").font = F_B
    ws.cell(rr0, 3, "See sheet 'Decision Objectives' for all decision rules, both probabilities and the budget analysis.").font = F_SUB
    ri = rr0 + 2
    ws.cell(ri, 1, "Input distributions as sampled").font = F_B
    B.header(ws, ri + 1, ["Parameter", "Mean", "5th pct", "95th pct"])
    ws.freeze_panes = None
    for i, (k, s) in enumerate(res["mc_inputs"].items(), start=ri + 2):
        ws.cell(i, 1, k); [ws.cell(i, j, round(val, 6)).__setattr__("font", F_PY) for j, val in ((2, s["mean"]), (3, s["p5"]), (4, s["p95"]))]

    # ------------------------------------------------------------------ Value of Information
    ws = B.sheet("Value of Information", "Value of information (Howard 1966) under the primary carbon chance constraint (90%, fixed reporting baseline)",
                 "EVPPI = expected gain from deciding after learning one input exactly. Because A+B sits at the 90% threshold, the binning estimator has a "
                 "high noise floor (row 5); compare EVPPI with it. Net value = EVPPI - collection cost (formula). Column F: v1.1 rule (comparison).",
                 [44, 16, 16, 16, 30, 18])
    ws["A4"] = "EVPI, all uncertainty resolved (SAR)"; ws["B4"] = round(res["evpi"], 0); ws["B4"].font = F_PY; ws["B4"].number_format = "#,##0"
    ws["A5"] = "Noise floor (irrelevant dummy variable)"; ws["B5"] = round(res["voi_noise_floor"], 0); ws["B5"].font = F_PY
    B.header(ws, 7, ["Information", "EVPPI (SAR)", "Collection cost (SAR)", "Net value (SAR)", "Changes the decision?", "EVPPI, v1.1 rule (SAR)"])
    e0 = 8 + len(res["voi"]) + 1
    B.param_table(ws, e0 + 3, ["cost_motor_audit", "audit_error_sd", "cost_submeter", "cost_supplier_data", "cost_pv_study"])
    ws.freeze_panes = None
    from .voi import GROUPS
    for i, rr in enumerate(res["voi"], start=8):
        ws.cell(i, 1, rr["information"])
        c = ws.cell(i, 2, round(rr["evppi_sar"], 0)); c.font = F_PY; c.number_format = "#,##0"
        cost_key = GROUPS[rr["information"]][1]
        if cost_key is not None:
            c = ws.cell(i, 3, f"={R[cost_key]}"); c.font = F_LINK; c.number_format = "#,##0"
            ws.cell(i, 4, f"=B{i}-C{i}").number_format = "#,##0;(#,##0)"
        else:
            ws.cell(i, 3, "not collectable by the firm" if "not collectable" in rr["information"] else "cost not estimated"); ws.cell(i, 4, "n/a")
        ws.cell(i, 5, "yes: " + " / ".join(rr["choices"]) if rr["decision_changes"] else "no")
        cmp_ = {x["parameter"]: x["evppi_sar"] for x in res.get("voi_comparison_v11", {}).get("ranking", [])}
        if rr["parameter"] in cmp_:
            c = ws.cell(i, 6, round(cmp_[rr["parameter"]], 0)); c.font = F_PY; c.number_format = "#,##0"
    ws.cell(e0, 1, "EVSI: motor-system audit (error s.d. 3 percentage points)").font = F_B
    ws.cell(e0, 2, round(res["evsi_audit"]["evsi"], 0)).font = F_PY
    ws.cell(e0, 3, f"={R['cost_motor_audit']}").font = F_LINK
    ws.cell(e0, 4, f"=B{e0}-C{e0}").font = F_CALC
    for col in (2, 3, 4):
        ws.cell(e0, col).number_format = "#,##0"
    R["EVSI_NET"] = f"'Value of Information'!$D${e0}"

    # ------------------------------------------------------------------ Sensitivity
    ws = B.sheet("Sensitivity", "Sensitivity and robustness (Python values)",
                 "Tornado: each input at its 5th/95th percentile. First-order index: share of variance of NPV({0}) - NPV({1}).".format(*res.get("sobol_decision_pair", ["A+B", "A+C+D"])),
                 [26, 14, 14, 16, 16, 14])
    B.header(ws, 4, ["Parameter (tornado, recommended portfolio)", "Low value", "High value", "NPV at low", "NPV at high", "Swing"])
    for i, rr in enumerate(res["tornado_det_opt"][:12], start=5):
        for j, val in enumerate([rr["parameter"], rr["low"], rr["high"], rr["npv_low"], rr["npv_high"], rr["swing"]], start=1):
            c = ws.cell(i, j, round(val, 4) if isinstance(val, float) else val); c.font = F_PY
            if j >= 4:
                c.number_format = "#,##0;(#,##0)"
    s0 = 19
    ws.cell(s0, 1, "First-order variance share (decision {0} vs {1})".format(*res.get("sobol_decision_pair", ["A+B", "A+C+D"]))).font = F_B
    for i, (k, val) in enumerate(list(res["sobol_decision"].items())[:10], start=s0 + 1):
        ws.cell(i, 1, k); c = ws.cell(i, 2, round(val, 4)); c.font = F_PY; c.number_format = "0.0%"
    w0 = s0 + 13
    ws.cell(w0, 1, "Switch points of the deterministic optimum (one input varied)").font = F_B
    i = w0 + 1
    for k, x in res["switch_points"].items():
        txt = "robust over tested range" if x["robust"] else "; ".join(f"at {a:,.4g}: {b} -> {c}" for a, b, c in x["changes"])
        ws.cell(i, 1, k); ws.cell(i, 2, txt).font = F_PY; i += 1
    ws.cell(i + 1, 1, "Discount-rate robustness").font = F_B
    for j, rr in enumerate(res["discount_robustness"], start=i + 2):
        ws.cell(j, 1, f"{rr['rate']:.0%}"); ws.cell(j, 2, rr["with_target"]).font = F_PY; ws.cell(j, 3, rr["without_target"]).font = F_PY
        c = ws.cell(j, 4, round(rr["npv_with_target"] or 0, 0)); c.font = F_PY; c.number_format = "#,##0;(#,##0)"

    # ------------------------------------------------------------------ Investment Timing
    ws = B.sheet("Investment Timing", "Investment timing for D (heat recovery)",
                 "Prototype: one-period reform decision tree (formulas). Extension: KAPSARC DP49 log-OU LSMC and GBM closed form.",
                 [20, 44, 14, 16, 13, 60, 30, 10])
    r = B.param_table(ws, 4, ["tree_p_reform", "tree_g_reform", "ro_kappa", "ro_sigma", "ro_mu_gbm", "ro_horizon"])
    r += 1
    ws.cell(r, 1, "Decision tree (formulas)").font = F_B
    d_row = R["row_D"]
    q = f"(-{ea}$E${d_row})"
    unit = f"{q}*3.75/1.055056"
    life = f"{ea}$H${d_row}"
    capex = f"{ea}$C${d_row}"
    af = f"((1-(1+{rate})^(-{life}))/{rate})"
    tree = [
        ("Gas saved (GJ/yr)", f"={q}"), ("Saving per USD/MMBtu (SAR/yr)", f"={unit}"),
        ("Static NPV at today's price", f"=-{capex}+({unit}*{R['gas_price_usd']}-{R['d_om']})*{af}"),
        ("Static NPV if reform price", f"=-{capex}+({unit}*{R['tree_g_reform']}-{R['d_om']})*{af}"),
        ("Expected price after decision (USD)", f"={R['tree_p_reform']}*{R['tree_g_reform']}+(1-{R['tree_p_reform']})*{R['gas_price_usd']}"),
        ("Invest now: expected NPV", f"=-{capex}+({unit}*{R['gas_price_usd']}-{R['d_om']})/(1+{rate})+({unit}*C{r+5}-{R['d_om']})*({af}-1/(1+{rate}))"),
        ("Wait one year: value", f"=({R['tree_p_reform']}*MAX(C{r+4},0)+(1-{R['tree_p_reform']})*MAX(C{r+3},0))/(1+{rate})"),
        ("Option premium (value of waiting)", f"=MAX(C{r+6},C{r+7})-C{r+6}"),
        ("Decision", f'=IF(C{r+6}>=C{r+7},"invest now","wait for the price decision")'),
        ("Static break-even gas price (USD/MMBtu)", f"=({capex}/{af}+{R['d_om']})/({unit})"),
    ]
    for i, (lab, fml) in enumerate(tree, start=r + 1):
        ws.cell(i, 2, lab).font = F_B; c = ws.cell(i, 3, fml); c.font = F_CALC; c.number_format = "#,##0.00"
    R["TREE_NOW"], R["TREE_WAIT"], R["TREE_DEC"], R["TREE_BE"] = (f"'Investment Timing'!$C${r+6}", f"'Investment Timing'!$C${r+7}",
                                                                  f"'Investment Timing'!$C${r+9}", f"'Investment Timing'!$C${r+10}")
    g = r + 13
    ws.cell(g, 1, "GBM closed-form benchmark (KAPSARC DP49 Eq. C.7, C.13)").font = F_B
    gbm = [("Continuous discount rate", f"=LN(1+{rate})"),
           ("A = (1-e^-(r-mu)T)/(r-mu)", f"=(1-EXP(-(C{g+1}-{R['ro_mu_gbm']})*{life}))/(C{g+1}-{R['ro_mu_gbm']})"),
           ("C = (1-e^-rT)/r", f"=(1-EXP(-C{g+1}*{life}))/C{g+1}"),
           ("lambda", f"=(-({R['ro_mu_gbm']}-{R['ro_sigma']}^2/2)+SQRT(({R['ro_mu_gbm']}-{R['ro_sigma']}^2/2)^2+2*C{g+1}*{R['ro_sigma']}^2))/{R['ro_sigma']}^2"),
           ("Multiplier lambda/(lambda-1)", f"=C{g+4}/(C{g+4}-1)"),
           ("Break-even (USD/MMBtu)", f"=({capex}+{R['d_om']}*C{g+3})/(C{g+2}*{unit})"),
           ("Trigger G* (USD/MMBtu)", f"=C{g+5}*C{g+6}")]
    for i, (lab, fml) in enumerate(gbm, start=g + 1):
        ws.cell(i, 2, lab).font = F_B; c = ws.cell(i, 3, fml); c.font = F_CALC; c.number_format = "0.0000"
    R["GBM_TRIG"] = f"'Investment Timing'!$C${g+7}"
    l0 = g + 10
    ws.cell(l0, 1, "LSMC under log-OU (Python): value of investing now vs optimal waiting, by long-run gas price").font = F_B
    for j, h in enumerate(["Long-run price (USD/MMBtu)", "Invest now (SAR)", "Optimal waiting (SAR)", "Invest now?"], start=2):
        c = ws.cell(l0 + 1, j, h); c.font = F_HDR; c.fill = FILL_HDR
    for i, rr in enumerate(res.get("timing_scan", {}).get("rows", []), start=l0 + 2):
        ws.cell(i, 2, rr["gbar"]).font = F_PY
        c = ws.cell(i, 3, round(rr["value_invest_now"], 0)); c.font = F_PY; c.number_format = "#,##0;(#,##0)"
        c = ws.cell(i, 4, round(rr["value_wait"], 0)); c.font = F_PY; c.number_format = "#,##0;(#,##0)"
        ws.cell(i, 5, bool(rr["invest_now"])).font = F_PY

    # ------------------------------------------------------------------ Decision Objectives (v1.2)
    lv = res["decision_levels"]
    ws = B.sheet("Decision Objectives", f"Decision rules: comparison, primary and sensitivity scenarios (model v{MODEL_VERSION})",
                 f"Primary basis: fixed reporting baseline (management decision 25 Oct 2026). Chance constraints use a sampling-tightened level "
                 f"({lv['alpha_saa']:.4f}) on {lv['n']:,} scenarios and are validated on an independent {lv['n_validation']:,}-scenario sample. "
                 "Black = live formula; purple = Python results. Illustrative case: synthetic data.",
                 [9, 40, 22, 13, 15, 16, 15, 12, 12, 12, 12, 12, 30, 50])
    j = res["mc_joint"]
    mbp = res["budget_analysis"]["min_budget_by_portfolio"]
    banner = (f"PRIMARY RULE (carbon {lv['alpha']:.0%} + budget {lv['beta']:.0%}): "
              + (f"{j['portfolio']}" if j["feasible"] else
                 f"NO FEASIBLE PORTFOLIO within SAR {res['meta']['budget']:,.0f}. Smallest budget that makes it feasible: SAR "
                 f"{mbp[0]['budget_needed']:,.0f} ({mbp[0]['portfolio']}). No recommendation is forced."))
    ws.merge_cells("A3:N3"); ws["A3"] = banner; ws["A3"].font = Font(name=FONT, size=11, bold=True, color="C00000")
    hdr = ["ID", "Decision rule", "Category", "Portfolio", "Quoted capex (live)", "NPV at base inputs (live)", "E[NPV]",
           "P(target) primary", "P(target) validation", "P(capex<=budget)", "P(capex<=budget) validation", "P(both)", "Status", "Formulation"]
    B.header(ws, 5, hdr)
    opt = "'Optimization'!"
    for i, o in enumerate(res["decision_scenarios"], start=6):
        ws.cell(i, 1, o["id"]).font = F_B; ws.cell(i, 2, o["rule"]).font = F_B; ws.cell(i, 3, o["category"])
        ws.cell(i, 4, o["portfolio"]).font = F_PY
        c = ws.cell(i, 5, f'=IFERROR(INDEX({opt}$H$8:$H$71,MATCH(D{i},{opt}$A$8:$A$71,0)),"n/a")'); c.font = F_CALC; c.number_format = "#,##0"
        c = ws.cell(i, 6, f'=IFERROR(INDEX({opt}$I$8:$I$71,MATCH(D{i},{opt}$A$8:$A$71,0)),"n/a")'); c.font = F_CALC; c.number_format = "#,##0;(#,##0)"
        for col, key, fmt in ((7, "e_npv", "#,##0;(#,##0)"), (8, "p_target", "0.0%"), (9, "p_target_val", "0.0%"), (10, "p_budget", "0.0%"),
                              (11, "p_budget_val", "0.0%"), (12, "p_both", "0.0%")):
            val = o.get(key)
            c = ws.cell(i, col, round(val, 4) if val is not None else "n/a"); c.font = F_PY; c.number_format = fmt
        ws.cell(i, 13, o["status"]).font = Font(name=FONT, size=10, bold=o["id"] == "D4", color="C00000" if ("FAIL" in o["status"] or o["status"] == "infeasible") else "000000")
        c = ws.cell(i, 14, o["formulation"]); c.alignment = Alignment(wrap_text=True, vertical="top")
        for col in (2, 3, 13):
            ws.cell(i, col).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 44
    r = 6 + len(res["decision_scenarios"]) + 1
    ws.cell(r, 1, "Why the rules differ").font = F_B
    for k, txt in enumerate(res["objectives_explanation"], start=r + 1):
        ws.merge_cells(start_row=k, start_column=1, end_row=k, end_column=14)
        c = ws.cell(k, 1, txt); c.alignment = Alignment(wrap_text=True, vertical="top"); c.font = F_CALC
        ws.row_dimensions[k].height = 34
    r = r + len(res["objectives_explanation"]) + 2
    ke = res["knife_edge"]
    ws.cell(r, 1, f"Sampling check: P(target) of {ke['portfolio']} on the primary basis").font = F_B
    B.header(ws, r + 1, ["", "Sample", "", "P(target)"]); ws.freeze_panes = None
    lines = [(f"Main sample ({ke['n']:,} scenarios, seed 20261024)", ke["p_in_sample"]),
             (f"Validation sample ({ke['n_validation']:,}, seed 20261025)", ke["p_validation"]),
             ("Validation 95% CI, lower", ke["ci95_validation"][0]), ("Validation 95% CI, upper", ke["ci95_validation"][1])] + \
            [(f"Other {ke['n']:,}-scenario sample, seed {x['seed']}", x["p_target"]) for x in ke["other_seeds"]]
    for k, (lab, val) in enumerate(lines, start=r + 2):
        ws.cell(k, 2, lab); c = ws.cell(k, 4, round(val, 5)); c.font = F_PY; c.number_format = "0.00%"
    r += len(lines) + 3
    ws.cell(r, 1, "Budget needed for the primary rule (90% budget compliance), per target-reliable portfolio").font = F_B
    B.header(ws, r + 1, ["", "Portfolio", "", "Budget needed (SAR)", "E[NPV]", "", "", "P(target) primary", "P(target) validation"]); ws.freeze_panes = None
    for k, x in enumerate(mbp, start=r + 2):
        ws.cell(k, 2, x["portfolio"]).font = F_PY
        c = ws.cell(k, 4, round(x["budget_needed"], 0)); c.font = F_PY; c.number_format = "#,##0"
        c = ws.cell(k, 5, round(x["e_npv"], 0)); c.font = F_PY; c.number_format = "#,##0;(#,##0)"
        for col, key in ((8, "p_target"), (9, "p_target_val")):
            c = ws.cell(k, col, round(x[key], 4)); c.font = F_PY; c.number_format = "0.0%"
    ws.cell(r + 2 + len(mbp), 2, "Budget needed = max(quoted capex, 90th-percentile actual capex in both samples, with the in-sample sampling margin).").font = F_SUB
    r += len(mbp) + 4
    ws.cell(r, 1, f"Choice at SAR {res['meta']['budget']:,.0f} for alternative risk thresholds (validated)").font = F_B
    th = res["budget_analysis"]["thresholds"]
    betas = sorted({x["beta"] for x in th}); alphas = sorted({x["alpha"] for x in th})
    B.header(ws, r + 1, ["", "P(target) >=", ""] + [f"P(capex<=budget) >= {b:.0%}" for b in betas]); ws.freeze_panes = None
    for k, a in enumerate(alphas, start=r + 2):
        ws.cell(k, 2, f"{a:.0%}").font = F_B
        for jj, b in enumerate(betas, start=4):
            x = next(t for t in th if t["alpha"] == a and t["beta"] == b)
            c = ws.cell(k, jj, x["portfolio"]); c.font = F_PY
            if x["portfolio"] == "infeasible":
                c.font = Font(name=FONT, size=10, color="C00000")
    r += len(alphas) + 3
    ws.cell(r, 1, "Budget curve (primary rule): smallest budgets at which the choice changes").font = F_B
    B.header(ws, r + 1, ["", "Budget (SAR)", "", "Portfolio", "E[NPV]", "", "", "P(target)", "P(capex<=budget)", "Validated"]); ws.freeze_panes = None
    prev, k = None, r + 2
    for x in res["budget_analysis"]["curve"]:
        key = (x["portfolio"], x["validated"])
        if key == prev:
            continue
        prev = key
        c = ws.cell(k, 2, x["budget"]); c.font = F_PY; c.number_format = "#,##0"
        ws.cell(k, 4, x["portfolio"]).font = F_PY
        if x["e_npv"] is not None:
            c = ws.cell(k, 5, round(x["e_npv"], 0)); c.font = F_PY; c.number_format = "#,##0"
            for col, key2 in ((8, "p_target"), (9, "p_budget")):
                c = ws.cell(k, col, round(x[key2], 4)); c.font = F_PY; c.number_format = "0.0%"
        ws.cell(k, 10, bool(x["validated"])).font = F_PY
        k += 1
    r = k + 2
    ws.cell(r, 1, "Industrial electricity tariff scenarios (primary basis; full re-optimisation; tariff fixed at the scenario value)").font = F_B
    B.header(ws, r + 1, ["ID", "Scenario", "Tariff (SAR/kWh)", "Deterministic", "Deterministic NPV", "Highest E[NPV]", "E[NPV]",
                         "Carbon CC", "E[NPV] (CC)", "Carbon + budget CC", "", "", "Evidence status", "Effective / source"])
    ws.freeze_panes = None
    ev = {e["id"]: e for e in res["tariff_evidence"]}
    for k, t in enumerate(res["tariff_scenarios"], start=r + 2):
        e = ev[t["id"]]
        vals = {1: t["id"], 2: t["label"], 3: t["tariff"], 4: t["deterministic"], 5: t["det_npv"], 6: t["best_expected"],
                7: t["best_expected_e_npv"], 8: t["chance_constrained"], 9: t["cc_e_npv"], 10: t["joint"], 13: e["status"],
                14: f"{e['effective']}; {e['source']}"}
        for jj, val in vals.items():
            c = ws.cell(k, jj, round(val, 0) if isinstance(val, float) and jj not in (3,) else val)
            c.font = F_PY; c.alignment = Alignment(wrap_text=True, vertical="top")
            if jj in (5, 7, 9):
                c.number_format = "#,##0;(#,##0)"
        if e["url"]:
            ws.cell(k, 14).hyperlink = e["url"]
        ws.row_dimensions[k].height = 60
    r += len(res["tariff_scenarios"]) + 3
    ws.cell(r, 1, "Grid emission factor: evidence and scenarios (reference 0.573 derived from BTR1/GASTAT 2021 since v1.3)").font = F_B
    B.header(ws, r + 1, ["", "Evidence", "Value (tCO2/MWh)", "", "", "", "", "", "", "", "", "", "", "Access / use"])
    ws.freeze_panes = None
    for k, e in enumerate(res["ef_evidence"], start=r + 2):
        ws.cell(k, 2, e["what"]).alignment = Alignment(wrap_text=True); ws.cell(k, 3, e["value"]).font = F_PY
        c = ws.cell(k, 14, f"{e['access']}. {e['use']}"); c.alignment = Alignment(wrap_text=True); ws.cell(k, 14).hyperlink = e["url"]
        ws.row_dimensions[k].height = 44
    r += len(res["ef_evidence"]) + 3
    B.header(ws, r, ["", "Grid-factor scenario", "EF (tCO2/MWh)", "Target (t/yr)", "Deterministic", "Highest E[NPV]", "Carbon CC",
                     "P(target), CC", "Carbon + budget CC", "", "", "", "", ""])
    ws.freeze_panes = None
    for k, t in enumerate(res["ef_scenarios"], start=r + 1):
        vals = {2: t["label"], 3: t["ef_grid"], 4: round(t["target_t"], 1), 5: t["deterministic"], 6: t["best_expected"],
                7: t["chance_constrained"], 8: round(t["cc_p_target"], 4) if t["cc_p_target"] is not None else "n/a", 9: t["joint"]}
        for jj, val in vals.items():
            c = ws.cell(k, jj, val); c.font = F_PY
            if jj == 8:
                c.number_format = "0.0%"
    r += len(res["ef_scenarios"]) + 2
    for title, key, col, unit in (("Industrial methane price scenarios (A5)", "gas_scenarios", "gas_price_usd", "USD/MMBtu"),
                                  ("Rooftop PV capital-cost scenarios (A5; reference = one public benchmark, not a quotation)",
                                   "pv_capex_scenarios", "pv_capex_kw", "SAR/kWp")):
        if not res.get(key):
            continue
        ws.cell(r, 1, title).font = F_B
        B.header(ws, r + 1, ["", "Scenario", unit, "Target (t/yr)", "Deterministic", "NPV (det.)", "Highest E[NPV]", "Carbon CC",
                             "Carbon + budget CC", "Min. budget for D4", "", "", "", ""])
        ws.freeze_panes = None
        for k, t in enumerate(res[key], start=r + 2):
            vals = {2: f"{t['id']} {t['label']}", 3: t[col], 4: round(t["target_t"], 1), 5: t["deterministic"], 6: round(t["det_npv"], 0),
                    7: t["best_expected"], 8: t["chance_constrained"], 9: t["joint"],
                    10: round(t["joint_min_budget"], 0) if t.get("joint_min_budget") is not None else "n/a"}
            for jj, val in vals.items():
                c = ws.cell(k, jj, val); c.font = F_PY
                if jj in (6, 10):
                    c.number_format = "#,##0;(#,##0)"
        r += len(res[key]) + 3

    # ------------------------------------------------------------------ Source Register (A5)
    ws = B.sheet("Source Register", f"Source and assumption register (model v{MODEL_VERSION})",
                 "Every input: value, unit, quality status, evidence class, source, publication date, effective period, geography, URL. "
                 "Hypothetical values are case assumptions, not factory observations or quotations.",
                 [22, 12, 16, 12, 12, 70, 18, 22, 30, 24, 40])
    hdr = ["Key", "Value", "Unit", "Status", "Evidence", "Source / rationale", "Published", "Effective", "Geography / applicability",
           "Uncertainty", "URL"]
    B.header(ws, 4, hdr)
    for i, (k, p_) in enumerate(P.items(), start=5):
        vals = [k, p_.value, p_.unit, p_.status, p_.evidence, p_.source + (f" | {p_.note}" if p_.note else ""), p_.published, p_.effective,
                p_.geography, _dist_text(p_), p_.url]
        for j, val in enumerate(vals, start=1):
            c = ws.cell(i, j, val); c.font = F_CALC; c.border = BOX; c.alignment = Alignment(wrap_text=j in (6, 8, 9), vertical="top")
        ws.cell(i, 4).fill = FILL_STATUS[p_.status]
        if p_.url:
            ws.cell(i, 11).hyperlink = p_.url
    ws.freeze_panes = "B5"
    # ------------------------------------------------------------------ A5 Changes
    ws = B.sheet("A5 Changes", "Before and after: effect of the A5 input revisions (Python, 20,000 scenarios, seed 20261024)",
                 "Row 1 = v1.2 register; middle rows = one A5 change applied alone (others at v1.2); last row = v1.3 register.",
                 [34, 50, 12, 12, 12, 14, 14, 14, 16, 14, 14, 14, 14, 14])
    cols = [("case", "Case"), ("change", "Change"), ("scope12", "Scope 1+2 (t)"), ("target_t", "Target (t)"), ("deterministic", "D1"),
            ("det_npv", "D1 NPV"), ("best_expected", "D2"), ("chance_constrained", "D3"), ("joint", "D4"), ("joint_min_budget", "Min budget D4"),
            ("p_target[A+B]", "P(target) A+B"), ("p_target[A+C+D]", "P(target) A+C+D"), ("p_budget[A+B]", "P(budget) A+B"), ("npv[A+B]", "NPV A+B")]
    B.header(ws, 4, [c[1] for c in cols])
    for i, row in enumerate(res.get("a5_attribution", []), start=5):
        for j, (key, _) in enumerate(cols, start=1):
            val = row.get(key)
            c = ws.cell(i, j, round(val, 4) if isinstance(val, float) else val); c.font = F_PY; c.border = BOX
            if isinstance(val, float):
                c.number_format = "0.0000" if abs(val) < 1.5 else "#,##0"

    # ------------------------------------------------------------------ Dashboard
    ws = B.sheet("Dashboard", "CARBON IQ - management dashboard (synthetic case)",
                 "Green = live links to the model; purple = Python simulation results. Prototype output, not investment advice.",
                 [46, 22, 4, 40, 22])
    items = [
        ("Baseline", None), ("Scope 1 (tCO2e/yr)", f"={R['S1']}"), ("Scope 2 (tCO2e/yr)", f"={R['S2']}"),
        ("Scope 3 Cat 1 + Cat 4 (tCO2e/yr)", f"={R['S3']}"), ("Total (tCO2e/yr)", f"={R['TOT']}"),
        ("Scope 1+2 uncertainty (±%, 95%)", f"={R['U_Scope 1+2']}"), ("Total uncertainty (±%, 95%)", f"={R['U_Total']}"),
        ("Decision inputs", None), ("Budget (SAR)", f"={R['budget']}"), ("Target: Scope 1+2 reduction (t/yr)", f"={R['TARGET']}"),
        ("Deterministic optimisation", None), ("Optimal portfolio", f"={R['OPT_NAME']}"), ("NPV (SAR)", f"={R['OPT_NPV']}"),
        ("Scope 1+2 reduction (t/yr)", f"={R['OPT_T']}"),
        ("Timing (heat recovery D)", None), ("Decision tree", f"={R['TREE_DEC']}"), ("Static break-even gas price (USD/MMBtu)", f"={R['TREE_BE']}"),
        ("GBM trigger (USD/MMBtu)", f"={R['GBM_TRIG']}"),
    ]
    r = 4
    for lab, fml in items:
        if fml is None:
            c = ws.cell(r, 1, lab); c.font = F_HDR; c.fill = FILL_HDR; ws.cell(r, 2).fill = FILL_HDR
        else:
            ws.cell(r, 1, lab).font = F_CALC
            c = ws.cell(r, 2, fml); c.font = F_LINK
            c.number_format = "#,##0.0" if "±" in lab or "USD" in lab else "#,##0"
        r += 1
    cc, be = res["mc_chance_constrained"], res["mc_best_expected"]
    jt, mbp = res["mc_joint"], res["budget_analysis"]["min_budget_by_portfolio"]
    t2 = next(t for t in res["tariff_scenarios"] if t["id"] == "T2")
    py = [("Under uncertainty (Python; primary basis = fixed reporting baseline)", None),
          ("PRIMARY RULE: carbon 90% + budget 90%", (jt["portfolio"] if jt["feasible"] else
              f"INFEASIBLE at SAR {res['meta']['budget']:,.0f}; needs SAR {mbp[0]['budget_needed']:,.0f} ({mbp[0]['portfolio']})")),
          ("Carbon 90% only (validated)", f"{cc['portfolio']}: SAR {cc['e_npv']:,.0f}; target {cc['p_target']:.1%}; within budget {1 - cc['p_over_budget']:.1%}"),
          ("Highest expected NPV (comparison)", f"{be['portfolio']}: SAR {be['e_npv']:,.0f}; target {be['p_target']:.1%}; within budget {1 - be['p_over_budget']:.1%}"),
          ("Sampling check", f"{res['knife_edge']['portfolio']} target probability {res['knife_edge']['p_in_sample']:.2%} in-sample but {res['knife_edge']['p_validation']:.2%} on validation"),
          ("If the announced 2027 tariff (0.23) applies", f"Deterministic {t2['deterministic']}; highest E[NPV] {t2['best_expected']}; carbon CC {t2['chance_constrained']}; carbon + budget {t2['joint']}"),
          ("Information worth buying first", f"Motor-system audit: EVSI SAR {res['evsi_audit']['evsi']:,.0f} (noise floor SAR {res['voi_noise_floor']:,.0f}) vs cost SAR {res['evsi_audit']['audit_cost']:,.0f}"),
          ("Management recommendation", (f"{jt['portfolio']} meets both 90% requirements at SAR 5M (E[NPV] SAR {jt['e_npv']:,.0f}). It depends on the "
                                         "Riyadh rooftop-PV cost benchmark: obtain formal PV quotations and the official 2027 tariff before committing; "
                                         "treat compressed air (C) as marginal." if jt["feasible"] else
                                         "No portfolio meets both 90% requirements at SAR 5M. Options: raise the budget to about SAR "
                                         f"{mbp[0]['budget_needed'] / 1e6:.2f}M for {mbp[0]['portfolio']}, or accept a lower budget-compliance level "
                                         f"({cc['portfolio']} complies in {1 - cc['p_over_budget']:.0%} of scenarios)."))]
    rr = 4
    for lab, txt in py:
        if txt is None:
            c = ws.cell(rr, 4, lab); c.font = F_HDR; c.fill = FILL_HDR; ws.cell(rr, 5).fill = FILL_HDR
        else:
            ws.cell(rr, 4, lab).font = F_B
            c = ws.cell(rr, 5, txt); c.font = F_PY; c.alignment = Alignment(wrap_text=True)
            ws.row_dimensions[rr].height = 30
        rr += 1
    ws.column_dimensions["E"].width = 46
    # charts
    ch = BarChart(); ch.type = "bar"; ch.title = "Baseline emissions by scope (tCO2e/yr)"; ch.style = 10
    data = Reference(B.wb["Baseline Emissions"], min_col=7, min_row=12, max_row=14)
    cats = Reference(B.wb["Baseline Emissions"], min_col=3, min_row=12, max_row=14)
    ch.add_data(data, titles_from_data=False); ch.set_categories(cats); ch.legend = None; ch.height = 6; ch.width = 14
    ws.add_chart(ch, "A24")
    ch2 = BarChart(); ch2.title = "NPV by project (SAR)"; ch2.style = 10
    data = Reference(B.wb["Financials & Cash Flows"], min_col=4, min_row=R["fin_first"], max_row=R["fin_first"] + 5)
    cats = Reference(B.wb["Financials & Cash Flows"], min_col=1, min_row=R["fin_first"], max_row=R["fin_first"] + 5)
    ch2.add_data(data, titles_from_data=False); ch2.set_categories(cats); ch2.legend = None; ch2.height = 6; ch2.width = 14
    ws.add_chart(ch2, "D24")

    # order: README, Dashboard first
    order = ["README", "Dashboard", "Facility Profile", "Production & Operations", "Electricity & Fuel", "Suppliers & Logistics",
             "Emission Factors", "Baseline Emissions", "Data Quality", "Investment Alternatives", "Financials & Cash Flows",
             "Optimization", "Monte Carlo", "Decision Objectives", "Value of Information", "Sensitivity", "Investment Timing",
             "Source Register", "A5 Changes"]
    B.wb._sheets = [B.wb[n] for n in order]
    for wsx in B.wb.worksheets:
        for row in wsx.iter_rows():
            for c in row:
                if c.font is None or c.font.name != FONT:
                    f = c.font
                    c.font = Font(name=FONT, size=f.size or 10, bold=f.bold, italic=f.italic, color=f.color, underline=f.underline)
    from openpyxl.workbook.properties import CalcProperties
    B.wb.calculation = CalcProperties(fullCalcOnLoad=True)   # Excel recalculates every formula when the file is opened
    B.wb.save(path)
    return B.ref
