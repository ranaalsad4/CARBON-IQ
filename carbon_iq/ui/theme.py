"""v2 visual identity: colours, CSS, header, formatting helpers. No calculations."""
import math

DK, AC, AM, LT, GR = "#0E2A25", "#1F6B5C", "#F2A33A", "#EEF4F1", "#5A6B67"
KIND_COLORS = {"reported": ("#1F6B5C", "#E3F1EC"), "calculated": ("#2F5597", "#E6ECF7"), "benchmark": ("#8A5A12", "#FCF0DC"),
               "hypothetical": ("#A33F22", "#FBE9E3"), "synthetic": ("#5B4A8A", "#EEEAF6")}
KIND_TEXT = {"reported": "Reported (company data)", "calculated": "Calculated by CARBON IQ", "benchmark": "Benchmark (external source)",
             "hypothetical": "Hypothetical (CARBON IQ assumption)", "synthetic": "Synthetic (made-up test data)"}
STATUS_COLORS = {"Fully implemented": "#1F6B5C", "Partially implemented": "#B9761A", "Not implemented": "#A33F22"}
CHART = dict(font=dict(family="Inter, Segoe UI, Helvetica, Arial, sans-serif", size=13, color="#14211E"),
             paper_bgcolor="white", plot_bgcolor="white", margin=dict(t=50, b=40, l=10, r=10))
SEQ = ["#1F6B5C", "#F2A33A", "#2F5597", "#A33F22", "#7FB069", "#5B4A8A"]

CSS = """
<style>
.block-container {padding-top: 1.2rem; max-width: 1300px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.ciq-hero {background: linear-gradient(120deg, #0E2A25 0%, #1F6B5C 100%); color: white; padding: 18px 24px; border-radius: 14px; margin-bottom: 14px;}
.ciq-hero h1 {color: white; font-size: 1.75rem; margin: 0 0 4px 0;}
.ciq-hero p {color: #DDEEE8; margin: 0; font-size: 0.95rem;}
.ciq-chip {display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; margin: 2px 4px 2px 0;}
.ciq-step {color: #B9761A; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.04em; text-transform: uppercase;}
.ciq-lead {font-size: 1.05rem; color: #14211E; margin: 4px 0 10px 0;}
.ciq-box {background: #EEF4F1; border-left: 4px solid #1F6B5C; padding: 10px 14px; border-radius: 6px; margin: 8px 0;}
.ciq-ex {background: #FFF4E2; border-left: 4px solid #F2A33A; padding: 10px 14px; border-radius: 6px; margin: 8px 0;}
.ciq-take {background: #0E2A25; color: white; padding: 10px 14px; border-radius: 8px; margin: 10px 0; font-weight: 600;}
.ciq-quote {font-style: italic; background: #F7FAF8; border-left: 4px solid #1F6B5C; padding: 8px 12px; border-radius: 6px;}
div[data-testid="stMetricValue"] {font-size: 1.55rem;}
div[data-testid="stExpander"] details summary p {font-weight: 600;}
@media (max-width: 640px) {.ciq-hero h1 {font-size: 1.3rem;} div[data-testid="stMetricValue"] {font-size: 1.2rem;}}
</style>
"""


def inject(st):
    st.markdown(CSS, unsafe_allow_html=True)


def hero(st, title, subtitle):
    st.markdown(f'<div class="ciq-hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def chip(kind, text=None):
    fg, bg = KIND_COLORS.get(kind, ("#333", "#eee"))
    return f'<span class="ciq-chip" style="color:{fg};background:{bg}">{text or KIND_TEXT.get(kind, kind)}</span>'


def status_chip(status):
    c = STATUS_COLORS.get(status, "#555")
    return f'<span class="ciq-chip" style="color:white;background:{c}">{status}</span>'


def box(st, html, cls="ciq-box"):
    st.markdown(f'<div class="{cls}">{html}</div>', unsafe_allow_html=True)


def sar(x, digits=None):
    """SAR formatting: millions with 2 decimals above SAR 1M, otherwise thousands separators."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    x = float(x)
    if abs(x) >= 1e6 and digits is None:
        return f"SAR {x / 1e6:,.2f} M"
    return f"SAR {x:,.0f}"


def tonnes(x, unit="tCO₂e/yr"):
    return "—" if x is None else f"{float(x):,.0f} {unit}"


def style_fig(fig, height=360, title=None):
    fig.update_layout(**CHART, height=height)
    if title:
        fig.update_layout(title=dict(text=title, x=0, font=dict(size=15)))
    fig.update_xaxes(showgrid=False, linecolor="#C9D8D2")
    fig.update_yaxes(gridcolor="#E6EEEA", zerolinecolor="#C9D8D2")
    return fig
