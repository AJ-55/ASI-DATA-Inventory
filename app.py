"""
ASI Emissions & Industry Explorer  (version 2)
==============================================
Interactive explorer for the plant-level Annual Survey of Industries (ASI) greenhouse-gas inventory,
1999-2000 to 2024-25.  The app reads a compact data bundle (built by asi_bundle.py) so that any
combination of filters is answered from a table of aggregated cells, not from millions of plants.

Pages: Home, Guide, Tables, Charts, Data set.   Theme: dark / light (button in the top-right corner).
Environment variables: ASI_BUNDLE_DIR, ASI_APP_PASSWORD (empty = open access), ASI_DATASET_URL.
"""
import glob
import hashlib
import html as _html
import json
import os
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = os.environ.get("ASI_BUNDLE_DIR", os.path.join(HERE, "bundle"))
STATIC_DIR = os.path.join(HERE, "static")
PASSWORD = os.environ.get("ASI_APP_PASSWORD", "")
DATASET_URL = os.environ.get("ASI_DATASET_URL", "")
APP_VERSION = "2.0"

st.set_page_config(page_title="ASI Emissions Explorer", page_icon="🏭", layout="wide",
                   initial_sidebar_state="expanded")

# ============================================================================ theme
THEMES = {
    "dark": dict(bg="#0e131a", panel="#151c26", panel2="#1d2733", text="#e8edf3", muted="#9aa8b8",
                 border="#2b3745", accent="#4da3ff", accent2="#23507f", input="#0f161f",
                 grid="rgba(160,175,195,0.16)", template="plotly_dark"),
    "light": dict(bg="#f4f6fa", panel="#ffffff", panel2="#eef2f7", text="#16202b", muted="#5b6a7a",
                  border="#d7dfe8", accent="#1a64c8", accent2="#cfe2fb", input="#ffffff",
                  grid="rgba(60,80,100,0.14)", template="plotly_white"),
}
PALETTE = ["#4da3ff", "#ff8a5c", "#2fd6a1", "#f7c948", "#c792ea", "#ff6b9a", "#8bd450", "#5ad1d8",
           "#b8a1ff", "#ffa94d", "#7fb2ff", "#e06c75"]

CSS = """
<style>
:root{--bg:__bg__;--panel:__panel__;--panel2:__panel2__;--text:__text__;--muted:__muted__;
--border:__border__;--accent:__accent__;--accent2:__accent2__;--input:__input__;}
.stApp{background:var(--bg);color:var(--text);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2.2rem;max-width:1500px;}
section[data-testid="stSidebar"]{background:var(--panel);border-right:1px solid var(--border);}
section[data-testid="stSidebar"] *{color:var(--text);}
.stMarkdown, .stMarkdown p, .stMarkdown li, label, [data-testid="stWidgetLabel"] p,
[data-testid="stMetricLabel"] p, [data-testid="stMetricValue"]{color:var(--text);}
[data-testid="stCaptionContainer"], .stCaption{color:var(--muted)!important;}
h1,h2,h3,h4,h5,h6{color:var(--text)!important;letter-spacing:-0.01em;}
[data-testid="stSelectbox"] div[role="group"][data-rac], [data-testid="stMultiSelect"] div[role="group"][data-rac],
[data-testid="stNumberInputContainer"], [data-testid="stTextInput"] div:has(> input),
[data-testid="stTextArea"] div:has(> textarea){background:var(--input)!important;border-color:var(--border)!important;}
[data-testid="stSelectbox"] input, [data-testid="stMultiSelect"] input, [data-testid="stNumberInputField"],
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea{background:transparent!important;color:var(--text)!important;
 -webkit-text-fill-color:var(--text)!important;}
[data-testid="stSelectbox"] input::placeholder, [data-testid="stMultiSelect"] input::placeholder{color:var(--muted)!important;
 -webkit-text-fill-color:var(--muted)!important;}
[data-testid="stSelectbox"] svg, [data-testid="stMultiSelect"] svg, [data-testid="stNumberInputContainer"] svg{fill:var(--muted);color:var(--muted);}
[data-testid$="VirtualDropdown"]{background:var(--panel)!important;color:var(--text)!important;border:1px solid var(--border);}
[data-testid$="VirtualDropdown"] [role="option"]{color:var(--text)!important;}
[data-testid$="VirtualDropdown"] [role="option"]:hover, [data-testid$="VirtualDropdown"] [role="option"][aria-selected="true"]{
 background:var(--panel2)!important;}
span[data-tag]{background:var(--accent2)!important;color:var(--text)!important;}
span[data-tag] span, span[data-tag] button, span[data-tag] svg{color:var(--text)!important;fill:var(--text)!important;}
[data-testid="stRadioOption"] > div > div:first-child:not(:has(+ *:empty)){border-color:var(--muted)!important;}
[data-testid="stRadioOption"]:not(:has(input:checked)) > div > div:first-child{background:var(--input)!important;
 border-color:var(--muted)!important;}
[data-testid="stRadioOption"]:not(:has(input:checked)) > div > div:first-child > div{background:transparent!important;}
[data-testid="stCheckbox"]:not([data-selected="true"]) label > div:nth-of-type(1){background:var(--input)!important;
 border-color:var(--muted)!important;}
[data-testid="stBaseButton-secondary"]{background:var(--panel2)!important;color:var(--text)!important;
 border:1px solid var(--border)!important;border-radius:9px;}
[data-testid="stBaseButton-secondary"] p{color:var(--text)!important;}
[data-testid="stBaseButton-secondary"]:hover{border-color:var(--accent)!important;}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{background:var(--accent)!important;
 border:1px solid var(--accent)!important;}
[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primaryFormSubmit"] p{color:#fff!important;}
[data-testid="stExpander"],[data-testid="stForm"]{background:var(--panel)!important;border:1px solid var(--border)!important;
 border-radius:12px;}
[data-testid="stExpander"] details, [data-testid="stExpander"] summary{background:var(--panel)!important;
 color:var(--text)!important;border-radius:12px;}
[data-testid="stExpander"] summary:hover{background:var(--panel2)!important;}
[data-testid="stExpander"] summary *{color:var(--text)!important;}
[data-testid="stProgressBarTrack"]{background:var(--panel2)!important;}
[data-testid="stTooltipContent"]{background:var(--panel)!important;color:var(--text)!important;border:1px solid var(--border);}

div[data-testid="stTabs"] button{color:var(--muted);}
div[data-testid="stTabs"] button[aria-selected="true"]{color:var(--accent);}
hr{border-color:var(--border);}
a{color:var(--accent)!important;}
.asi-card{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:16px 18px;height:100%;}
.asi-card .k{color:var(--muted);font-size:.80rem;text-transform:uppercase;letter-spacing:.06em;}
.asi-card .v{font-size:1.7rem;font-weight:650;line-height:1.25;margin-top:2px;}
.asi-card .s{color:var(--muted);font-size:.82rem;margin-top:2px;}
.asi-hero{background:linear-gradient(135deg,var(--panel) 0%,var(--panel2) 100%);border:1px solid var(--border);
 border-radius:18px;padding:26px 30px;margin-bottom:16px;}
.asi-hero h1{margin:0 0 6px 0;font-size:2rem;}
.asi-hero p{color:var(--muted);margin:0;font-size:1.02rem;line-height:1.55;}
.asi-wrap{max-height:560px;overflow:auto;border:1px solid var(--border);border-radius:12px;background:var(--panel);}
table.asi-table{border-collapse:separate;border-spacing:0;width:100%;font-size:.86rem;}
table.asi-table th{position:sticky;top:0;background:var(--panel2);color:var(--text);text-align:left;padding:8px 12px;
 border-bottom:1px solid var(--border);white-space:nowrap;z-index:1;}
table.asi-table td{padding:6px 12px;border-bottom:1px solid var(--border);color:var(--text);white-space:nowrap;}
table.asi-table td.n{text-align:right;font-variant-numeric:tabular-nums;}
table.asi-table tr:hover td{background:var(--panel2);}
.asi-dl a{display:inline-block;padding:8px 14px;margin:4px 6px 4px 0;border:1px solid var(--border);
 border-radius:9px;background:var(--panel2);text-decoration:none;color:var(--text)!important;}
.asi-dl a:hover{border-color:var(--accent);}
.asi-pill{display:inline-block;padding:2px 10px;border-radius:99px;background:var(--accent2);font-size:.78rem;margin-right:6px;}
</style>
"""


def inject_css():
    th = THEMES[st.session_state.theme]
    out = CSS
    for k, v in th.items():
        out = out.replace(f"__{k}__", v)
    st.markdown(out, unsafe_allow_html=True)


# ============================================================================ constants
DIMS = {  # column -> label
    "Year": "Survey year", "STATE": "State / UT", "Division": "NIC division (name)",
    "NIC2": "NIC division (2-digit code)", "NIC3": "NIC group (3-digit code)",
    "NIC4": "NIC class (4-digit code)", "NIC5": "NIC sub-class (5-digit code)",
    "Sector": "Sector (harmonised across NIC editions)", "Class": "Manufacturing / non-manufacturing",
}
SCALES = {"As reported": 1.0, "Thousand": 1e3, "Lakh (1e5)": 1e5, "Million": 1e6, "Crore (1e7)": 1e7,
          "Billion": 1e9}
GROUP_LABEL = {"economic": "Output, input and value added", "labour": "Labour and emoluments",
               "capital": "Capital", "energy": "Energy use and fuel cost", "emission": "Emissions"}

DIV_2008 = {"05": "Mining of coal and lignite", "06": "Crude petroleum and natural gas", "07": "Mining of metal ores",
            "08": "Other mining and quarrying", "09": "Mining support services", "10": "Food products",
            "11": "Beverages", "12": "Tobacco products", "13": "Textiles", "14": "Wearing apparel",
            "15": "Leather and related products", "16": "Wood and wood products", "17": "Paper and paper products",
            "18": "Printing and recorded media", "19": "Coke and refined petroleum", "20": "Chemicals and chemical products",
            "21": "Pharmaceuticals", "22": "Rubber and plastics", "23": "Other non-metallic minerals",
            "24": "Basic metals", "25": "Fabricated metal products", "26": "Computer, electronic and optical",
            "27": "Electrical equipment", "28": "Machinery and equipment n.e.c.", "29": "Motor vehicles and trailers",
            "30": "Other transport equipment", "31": "Furniture", "32": "Other manufacturing",
            "33": "Repair and installation of machinery", "35": "Electricity, gas and steam", "36": "Water supply",
            "37": "Sewerage", "38": "Waste collection and recycling", "39": "Remediation services",
            "45": "Motor vehicle trade and repair", "46": "Wholesale trade", "47": "Retail trade",
            "52": "Warehousing", "58": "Publishing", "61": "Telecommunications", "62": "Computer programming",
            "63": "Information services", "95": "Repair of computers and goods", "96": "Other personal services"}
DIV_2004 = {"10": "Coal and lignite", "11": "Crude petroleum and natural gas", "13": "Mining of metal ores",
            "14": "Other mining and quarrying", "15": "Food products and beverages", "16": "Tobacco products",
            "17": "Textiles", "18": "Wearing apparel", "19": "Leather and footwear", "20": "Wood and wood products",
            "21": "Paper and paper products", "22": "Publishing and printing", "23": "Coke, refined petroleum, nuclear fuel",
            "24": "Chemicals and chemical products", "25": "Rubber and plastics", "26": "Other non-metallic minerals",
            "27": "Basic metals", "28": "Fabricated metal products", "29": "Machinery and equipment n.e.c.",
            "30": "Office and computing machinery", "31": "Electrical machinery n.e.c.",
            "32": "Radio, TV and communication equipment", "33": "Medical, precision and optical instruments",
            "34": "Motor vehicles and trailers", "35": "Other transport equipment", "36": "Furniture; manufacturing n.e.c.",
            "37": "Recycling", "40": "Electricity, gas and steam", "41": "Water supply", "45": "Construction",
            "50": "Motor vehicle trade and repair", "51": "Wholesale trade", "52": "Retail trade and repair",
            "60": "Land transport", "64": "Post and telecommunications", "72": "Computer services",
            "74": "Other business services", "90": "Sewage and refuse disposal", "93": "Other service activities"}
# Harmonised sector groups (approximate concordance of NIC-1998/2004 and NIC-2008 divisions)
SEC_2008 = {"10": "Food and beverages", "11": "Food and beverages", "12": "Tobacco", "13": "Textiles",
            "14": "Wearing apparel", "15": "Leather and footwear", "16": "Wood and wood products",
            "17": "Paper and printing", "18": "Paper and printing", "19": "Coke and refined petroleum",
            "20": "Chemicals and pharmaceuticals", "21": "Chemicals and pharmaceuticals", "22": "Rubber and plastics",
            "23": "Non-metallic minerals", "24": "Basic metals", "25": "Fabricated metal products",
            "26": "Electrical, electronic and precision equipment", "27": "Electrical, electronic and precision equipment",
            "28": "Machinery and equipment", "29": "Transport equipment", "30": "Transport equipment",
            "31": "Furniture and other manufacturing", "32": "Furniture and other manufacturing",
            "33": "Repair and installation", "05": "Mining", "06": "Mining", "07": "Mining", "08": "Mining",
            "09": "Mining", "35": "Electricity, gas and water", "36": "Electricity, gas and water",
            "37": "Waste and remediation", "38": "Waste and remediation", "39": "Waste and remediation"}
SEC_2004 = {"15": "Food and beverages", "16": "Tobacco", "17": "Textiles", "18": "Wearing apparel",
            "19": "Leather and footwear", "20": "Wood and wood products", "21": "Paper and printing",
            "22": "Paper and printing", "23": "Coke and refined petroleum", "24": "Chemicals and pharmaceuticals",
            "25": "Rubber and plastics", "26": "Non-metallic minerals", "27": "Basic metals",
            "28": "Fabricated metal products", "29": "Machinery and equipment",
            "30": "Electrical, electronic and precision equipment", "31": "Electrical, electronic and precision equipment",
            "32": "Electrical, electronic and precision equipment", "33": "Electrical, electronic and precision equipment",
            "34": "Transport equipment", "35": "Transport equipment", "36": "Furniture and other manufacturing",
            "37": "Recycling", "10": "Mining", "11": "Mining", "13": "Mining", "14": "Mining",
            "40": "Electricity, gas and water", "41": "Electricity, gas and water", "90": "Waste and remediation"}

STATE_XY = {  # approximate centroids (lat, lon) for the bubble map
    "ANDHRA PRADESH": (15.9, 79.7), "TELANGANA": (17.9, 79.1), "ARUNACHAL PRADESH": (28.2, 94.7),
    "ASSAM": (26.2, 92.9), "BIHAR": (25.1, 85.3), "CHHATTISGARH": (21.3, 81.7), "GOA": (15.3, 74.1),
    "GUJARAT": (22.3, 71.7), "HARYANA": (29.1, 76.1), "HIMACHAL PRADESH": (31.9, 77.2),
    "JHARKHAND": (23.6, 85.3), "KARNATAKA": (15.3, 75.7), "KERALA": (10.5, 76.5),
    "MADHYA PRADESH": (23.5, 78.6), "MAHARASHTRA": (19.7, 75.7), "MANIPUR": (24.7, 93.9),
    "MEGHALAYA": (25.5, 91.4), "MIZORAM": (23.2, 92.9), "NAGALAND": (26.2, 94.6), "ODISHA": (20.5, 84.4),
    "PUNJAB": (31.0, 75.3), "RAJASTHAN": (26.6, 73.8), "SIKKIM": (27.6, 88.5), "TAMIL NADU": (11.1, 78.4),
    "TRIPURA": (23.8, 91.7), "UTTAR PRADESH": (26.9, 80.9), "UTTARAKHAND": (30.1, 79.3),
    "WEST BENGAL": (23.0, 87.9), "DELHI": (28.6, 77.2), "CHANDIGARH": (30.7, 76.8), "PUDUCHERRY": (11.9, 79.8),
    "JAMMU AND KASHMIR": (33.8, 76.6), "LADAKH": (34.2, 77.6), "ANDAMAN AND NICOBAR ISLANDS": (11.7, 92.7),
    "DADRA AND NAGAR HAVELI": (20.2, 73.0), "DAMAN AND DIU": (20.4, 72.8), "LAKSHADWEEP": (10.6, 72.6),
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": (20.3, 73.0),
}

# ============================================================================ data
@st.cache_resource(show_spinner="Loading the ASI data bundle ...")
def load_all(bundle_dir):
    meta = json.load(open(os.path.join(bundle_dir, "meta.json")))
    cube = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(os.path.join(bundle_dir, "cube_*.parquet")))],
                     ignore_index=True)
    sample = pd.read_parquet(os.path.join(bundle_dir, "sample.parquet"))
    nd = int(meta.get("cube_nic_digits", 5))
    names = {}
    p = os.path.join(bundle_dir, "nic_names.csv")        # optional: Edition, Code, Name
    if os.path.exists(p):
        nn = pd.read_csv(p, dtype=str)
        names = {(r.Edition, r.Code): r.Name for r in nn.itertuples()}
    cube = _prep(cube, meta, "NIC", nd)
    sample = _prep(sample, meta, "NIC_5digit", 5)
    return meta, cube, sample, names


def _prep(df, meta, code_col, width):
    years = meta["years"]
    df["Year"] = pd.Categorical(df["Year"], categories=years, ordered=True)
    df["STATE"] = df["STATE"].astype("category")
    code = df[code_col].astype(str)
    is08 = df["Year"].astype(str).map({y: ("2008" in str(e)) for y, e in meta["nic_edition"].items()}).fillna(True).to_numpy(bool)
    for n in (2, 3, 4, 5):
        if n <= width:
            df[f"NIC{n}"] = code.str[:n].astype("category")
    n2 = code.str[:2].to_numpy()
    k = np.where(is08, "8", "4").astype(object) + n2.astype(object)
    div = {("8" + c): f"{c} {n}" for c, n in DIV_2008.items()}
    div.update({("4" + c): f"{c} {n}" for c, n in DIV_2004.items()})
    sec = {("8" + c): n for c, n in SEC_2008.items()}
    sec.update({("4" + c): n for c, n in SEC_2004.items()})
    kk = pd.Series(k, index=df.index)
    mf = df["Mfg"].to_numpy() == 1
    df["Division"] = kk.map(div).fillna(pd.Series("Division " + pd.Series(n2, index=df.index), index=df.index)).astype("category")
    df["Sector"] = kk.map(sec).fillna(pd.Series(np.where(mf, "Other manufacturing", "Other non-manufacturing"),
                                                index=df.index)).astype("category")
    df["Class"] = pd.Series(np.where(mf, "Manufacturing", "Non-manufacturing"), index=df.index).astype("category")
    return df


def data():
    return load_all(BUNDLE_DIR)


def make_mask(df, f):
    m = np.ones(len(df), bool)
    if f.get("years"):
        m &= df["Year"].isin(list(f["years"])).to_numpy()
    if f.get("states"):
        m &= df["STATE"].isin(list(f["states"])).to_numpy()
    if f.get("cls") == "Manufacturing":
        m &= (df["Mfg"].to_numpy() == 1)
    elif f.get("cls") == "Non-manufacturing":
        m &= (df["Mfg"].to_numpy() != 1)
    if f.get("nic_mode") == "code" and f.get("nic_codes"):
        col = f"NIC{f['nic_level']}"
        if col in df:
            m &= df[col].isin(list(f["nic_codes"])).to_numpy()
    elif f.get("nic_mode") == "sector" and f.get("sectors"):
        m &= df["Sector"].isin(list(f["sectors"])).to_numpy()
    return m


@st.cache_data(show_spinner=False, max_entries=500)
def aggregate(f, by, bases, weighted, source="cube"):
    """Filtered, grouped sums.  Returns one row per group; columns = by + N_plants + Est_factories + bases."""
    meta, cube, sample, _ = data()
    if source == "sample":
        S = sample
        m = make_mask(S, f)
        sub = S.loc[m]
        cols = [b for b in bases if b in S.columns]
        w = sub["weight"].to_numpy()
        X = sub[cols].astype(float).mul(w if weighted else 1.0, axis=0) if cols else pd.DataFrame(index=sub.index)
        key = sub[list(by)] if by else pd.DataFrame({"All": "All selected"}, index=sub.index)
        out = pd.concat([key.reset_index(drop=True), X.reset_index(drop=True),
                         pd.DataFrame({"N_plants": 1, "Est_factories": w if weighted else 1.0})], axis=1)
        gcols = list(key.columns)
        g = out.groupby(gcols, observed=True, sort=True)
        res = pd.concat([g[cols].sum(min_count=1), g["N_plants"].sum(), g["Est_factories"].sum()], axis=1)
        return res.reset_index()
    C = cube
    m = make_mask(C, f)
    pre = "W__" if (weighted or not meta.get("has_unweighted")) else "U__"
    cols = [b for b in bases if f"{pre}{b}" in C.columns]
    pcols = [f"{pre}{b}" for b in cols]
    use = list(by) + pcols + ["N_plants", "Est_factories"]
    sub = C.loc[m, use].copy()
    if not by:
        sub["All"] = "All selected"
        gcols = ["All"]
    else:
        gcols = list(by)
    g = sub.groupby(gcols, observed=True, sort=True)
    res = pd.concat([g[pcols].sum(min_count=1), g["N_plants"].sum(), g["Est_factories"].sum()], axis=1)
    res.columns = cols + ["N_plants", "Est_factories"]
    return res.reset_index()


# ============================================================================ variable specifications
def spec(label, unit, num, den=None, mult=1.0, kind="level"):
    return dict(label=label, unit=unit, num=list(num), den=list(den) if den else None, mult=mult, kind=kind)


def bases_of(specs):
    s = set()
    for sp in specs:
        s |= {b for b, _ in sp["num"]}
        if sp["den"]:
            s |= {b for b, _ in sp["den"]}
    return tuple(sorted(s - {"Est_factories", "N_plants"}))


def eval_spec(A, sp):
    def comb(terms):
        parts = [A[b] * k for b, k in terms if b in A.columns]
        if not parts:
            return pd.Series(np.nan, index=A.index)
        return pd.concat(parts, axis=1).sum(axis=1, min_count=1)
    num = comb(sp["num"])
    if sp["den"]:
        den = comb(sp["den"])
        return num / den.where(den != 0) * sp["mult"]
    return num


DENOM = {  # label, base terms, multiplier, per-label
    "GVA": ("gross value added", [("Gross_Value_Added", 1.0)], 1e7, "Rs crore of GVA"),
    "Output": ("total output", [("Total_Output", 1.0)], 1e7, "Rs crore of output"),
    "Persons": ("persons engaged", [("Persons_Engaged", 1.0)], 1.0, "person engaged"),
    "Factories": ("estimated factories", [("Est_factories", 1.0)], 1.0, "factory"),
    "Capital": ("net fixed capital", [("Fixed_Capital_Net_Close", 1.0)], 1e7, "Rs crore of fixed capital"),
}
OTHER_IND = {
    "Labour productivity (GVA per person engaged, Rs lakh)": ([("Gross_Value_Added", 1.0)], [("Persons_Engaged", 1.0)], 1e-5),
    "Capital intensity (net fixed capital per person, Rs lakh)": ([("Fixed_Capital_Net_Close", 1.0)], [("Persons_Engaged", 1.0)], 1e-5),
    "Fuel cost share of input (%)": ([("Fuels_Consumed", 1.0)], [("Total_Input", 1.0)], 100.0),
    "GVA share of output (%)": ([("Gross_Value_Added", 1.0)], [("Total_Output", 1.0)], 100.0),
    "Profit share of output (%)": ([("Profit", 1.0)], [("Total_Output", 1.0)], 100.0),
    "Wage share of GVA (%)": ([("Total_Emoluments", 1.0)], [("Gross_Value_Added", 1.0)], 100.0),
    "Average emoluments per person engaged (Rs)": ([("Total_Emoluments", 1.0)], [("Persons_Engaged", 1.0)], 1.0),
}


def emission_specs(scopes, unit, gases, combine_gases, combine_scopes, gwp):
    """Specifications of the selected emission variables.
    scopes: subset of {'Scope 1', 'Scope 2'}; unit: 't CO2e' or 't (mass of gas)'."""
    out = []
    ch4, n2o = gwp.get("CH4", 28.0), gwp.get("N2O", 265.0)
    gas_terms = {"CO2": ("Total_CO2_emission", 1.0), "CH4": ("Total_CH4_emission", ch4),
                 "N2O": ("Total_N2O_emission", n2o)}
    gases = [g for g in ["CO2", "CH4", "N2O"] if g in gases]
    s1_total_terms = None
    if "Scope 1" in scopes and gases:
        if unit == "t CO2e":
            if len(gases) == 3:
                s1_total_terms = [("Total_CO2eq_emission", 1.0)]
            else:
                s1_total_terms = [gas_terms[g] for g in gases]
            if combine_gases or len(gases) == 1:
                lab = "Scope 1 (" + " + ".join(gases) + ")" if len(gases) < 3 else "Scope 1 total"
                out.append(spec(f"{lab}, t CO2e", "t CO2e", s1_total_terms))
            else:
                for g in gases:
                    out.append(spec(f"Scope 1 {g}, t CO2e", "t CO2e", [gas_terms[g]]))
        else:
            for g in gases:
                out.append(spec(f"Scope 1 {g}, t of {g}", f"t {g}", [(gas_terms[g][0], 1.0)]))
    if "Scope 2" in scopes:
        lab = "Scope 2 (purchased electricity), t CO2e" if unit == "t CO2e" else "Scope 2 CO2 (purchased electricity), t"
        out.append(spec(lab, "t CO2e" if unit == "t CO2e" else "t CO2", [("Scope2_CO2eq_emission", 1.0)]))
    if unit == "t CO2e" and combine_scopes and "Scope 1" in scopes and "Scope 2" in scopes and s1_total_terms:
        out.append(spec("Scope 1 + Scope 2, t CO2e", "t CO2e", s1_total_terms + [("Scope2_CO2eq_emission", 1.0)]))
    return out


def build_specs(a, meta):
    """All variable specifications requested by an applied filter state."""
    specs = []
    mt = meta["measures"]
    for v in a.get("vars", []):
        if v == "Est_factories":
            specs.append(spec("Number of factories (estimated), number", "number", [("Est_factories", 1.0)]))
        elif v == "N_plants":
            specs.append(spec("Plants in the survey sample, number", "number", [("N_plants", 1.0)]))
        elif v in mt:
            lab, unit, _ = mt[v]
            specs.append(spec(f"{lab}, {unit}", unit, [(v, 1.0)]))
    em = emission_specs(a.get("scopes", []), a.get("unit", "t CO2e"), a.get("gases", []),
                        a.get("combine_gases", True), a.get("combine_scopes", False), meta["gwp"])
    specs += em
    for d in a.get("ind_den", []):
        nm, den, mult, per = DENOM[d]
        for e in em:
            if e["unit"].startswith("t"):
                specs.append(spec(f"{e['label'].split(',')[0]} per {per}, {e['unit']}",
                                  f"{e['unit']} per {per}", e["num"], den, mult, kind="ratio"))
    for k in a.get("ind_other", []):
        num, den, mult = OTHER_IND[k]
        specs.append(spec(k, "ratio", num, den, mult, kind="ratio"))
    # unique labels
    seen, uniq = {}, []
    for sp in specs:
        if sp["label"] in seen:
            continue
        seen[sp["label"]] = 1
        uniq.append(sp)
    return [sp for sp in uniq if all(b in mt or b in ("Est_factories", "N_plants")
                                      for b, _ in sp["num"] + (sp["den"] or []))]


def compute_frame(a, by, specs, stat="total", scale=1.0, source="cube"):
    """Grouped result table: by-columns, one column per specification, N_plants, Est_factories."""
    meta, *_ = data()
    A = aggregate(a, tuple(by), bases_of(specs), bool(a.get("weighted", True)), source)
    out = A[list(by) + ["N_plants", "Est_factories"]].copy() if by else A[["N_plants", "Est_factories"]].copy()
    if not by:
        out.insert(0, "All", "All selected")
    for sp in specs:
        v = eval_spec(A, sp)
        if sp["kind"] == "level":
            if stat == "per_factory":
                v = v / A["Est_factories"].where(A["Est_factories"] != 0)
            elif stat == "share":
                grp = A["Year"] if "Year" in by and len(by) > 1 else pd.Series(0, index=A.index)
                v = v / v.groupby(grp, observed=True).transform("sum") * 100
            elif scale != 1.0:
                v = v / scale
        out[sp["label"]] = v.values
    minp = int(a.get("minp", 1))
    if minp > 1:
        small = out["N_plants"] < minp
        out.loc[small, [sp["label"] for sp in specs]] = np.nan
    return out


# ============================================================================ UI helpers
def fmt_value(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    if isinstance(v, (int, np.integer)):
        return f"{v:,}"
    a = abs(v)
    if a >= 1000:
        return f"{v:,.0f}"
    if a >= 1:
        return f"{v:,.2f}"
    if a == 0:
        return "0"
    return f"{v:.4g}"


def html_table(df, max_rows=None):
    d = df if max_rows is None else df.head(max_rows)
    heads = "".join(f"<th>{_html.escape(str(c))}</th>" for c in d.columns)
    numeric = [pd.api.types.is_numeric_dtype(d[c]) for c in d.columns]
    rows = []
    for r in d.itertuples(index=False, name=None):
        tds = []
        for v, isn in zip(r, numeric):
            if isn:
                tds.append(f'<td class="n">{fmt_value(v)}</td>')
            else:
                tds.append(f"<td>{_html.escape(str(v))}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="asi-wrap"><table class="asi-table"><thead><tr>{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def card(k, v, s=""):
    return f'<div class="asi-card"><div class="k">{_html.escape(k)}</div><div class="v">{_html.escape(str(v))}</div><div class="s">{_html.escape(s)}</div></div>'


def fig_style(fig, height=520, title=None):
    th = THEMES[st.session_state.theme]
    fig.update_layout(template=th["template"], height=height, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=th["text"], size=13),
                      margin=dict(l=10, r=10, t=60 if title else 30, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                      colorway=PALETTE, hoverlabel=dict(namelength=-1))
    if title:
        fig.update_layout(title=dict(text=title, x=0.01, font=dict(size=16)))
    fig.update_xaxes(gridcolor=th["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=th["grid"], zeroline=False)
    return fig


def top_bar(title, subtitle=""):
    c1, c2 = st.columns([12, 1])
    with c1:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)
    with c2:
        dark = st.session_state.theme == "dark"
        st.button("🌙" if dark else "☀️", key=f"theme_btn_{title}", on_click=toggle_theme,
                  help="Dark mode is on - click for light mode" if dark else "Light mode is on - click for dark mode",
                  width="stretch")


def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
    st.query_params["theme"] = st.session_state.theme


# ============================================================================ filter panel
EMIS_SCOPES = ["Scope 1", "Scope 2"]


def default_state(meta):
    return dict(years=tuple(meta["years"]), states=(), cls="All", nic_mode="All", nic_level=2, nic_codes=(),
                sectors=(), vars=("Gross_Value_Added",), scopes=("Scope 1",), unit="t CO2e",
                gases=("CO2", "CH4", "N2O"), combine_gases=True, combine_scopes=False, ind_den=(),
                ind_other=(), weighted=True, minp=1)


def _set_defaults(key, meta, force=False):
    ss = st.session_state
    d = default_state(meta)
    pairs = {"years": list(d["years"]), "states": [], "cls": "All", "nicmode": "All (no NIC filter)", "niclevel": 2,
             "niccodes": [], "nicpaste": "", "sectors": [], "vars": list(d["vars"]), "scopes": list(d["scopes"]),
             "unit": "t CO2e", "gases": list(d["gases"]), "cg": True, "cs": False, "inden": [], "inoth": [],
             "weighted": "Population estimate (x Multiplier)", "minp": 1, "nq": 0, "nqdir": "latest"}
    for k, v in pairs.items():
        if force or f"{key}_{k}" not in ss:
            ss[f"{key}_{k}"] = v
    if force or f"{key}_applied" not in ss:
        ss[f"{key}_applied"] = d


def _reset(key, meta):
    _set_defaults(key, meta, force=True)


def _quick_years(key, meta):
    ss = st.session_state
    n = int(ss[f"{key}_nq"])
    if n > 0:
        ys = meta["years"]
        ss[f"{key}_years"] = ys[-n:] if ss[f"{key}_nqdir"] == "latest" else ys[:n]


def _collect(key, meta):
    ss = st.session_state
    g = lambda k: ss[f"{key}_{k}"]
    mode = {"All (no NIC filter)": "All", "NIC code": "code", "Sector name": "sector"}[g("nicmode")]
    codes = list(g("niccodes"))
    paste = [c.strip() for c in re.split(r"[,\s;]+", str(g("nicpaste"))) if c.strip()]
    if mode == "code":
        codes += [c.zfill(int(g("niclevel"))) for c in paste]
    return dict(years=tuple(g("years")) or tuple(meta["years"]), states=tuple(g("states")), cls=g("cls"),
                nic_mode=mode, nic_level=int(g("niclevel")), nic_codes=tuple(dict.fromkeys(codes)),
                sectors=tuple(g("sectors")), vars=tuple(g("vars")), scopes=tuple(g("scopes")), unit=g("unit"),
                gases=tuple(g("gases")), combine_gases=bool(g("cg")), combine_scopes=bool(g("cs")),
                ind_den=tuple(g("inden")), ind_other=tuple(g("inoth")),
                weighted=g("weighted").startswith("Population"), minp=int(g("minp")))


def filter_panel(key, expanded=True):
    """Detailed selection panel. Returns the applied filter dict."""
    meta, cube, sample, names = data()
    ss = st.session_state
    _set_defaults(key, meta)
    n_years = len(meta["years"])
    nd = int(meta.get("cube_nic_digits", 5))
    with st.expander("Selection of data  ·  years, states, industries, variables, emissions", expanded=expanded):
        # --- controls that change the option lists immediately (kept outside the form)
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            st.slider(f"Number of years (0 - {n_years})", 0, n_years, key=f"{key}_nq",
                      on_change=_quick_years, args=(key, meta),
                      help="Quick selection: the latest (or earliest) N survey years. 0 leaves the year list as it is.")
        with c2:
            st.radio("Take the", ["latest", "earliest"], key=f"{key}_nqdir", horizontal=True,
                     on_change=_quick_years, args=(key, meta))
        with c3:
            sel_n = len(ss[f"{key}_years"])
            st.progress(sel_n / n_years, text=f"{sel_n} of {n_years} survey years selected")
        c1, c2 = st.columns([2, 2])
        with c1:
            st.radio("Industry filter by", ["All (no NIC filter)", "NIC code", "Sector name"], key=f"{key}_nicmode",
                     horizontal=True)
        with c2:
            if ss[f"{key}_nicmode"] == "NIC code":
                lv = [n for n in (2, 3, 4, 5) if n <= nd]
                st.selectbox("NIC level", lv, key=f"{key}_niclevel",
                             format_func=lambda n: f"{n}-digit ({['division', 'group', 'class', 'sub-class'][n - 2]})")
        with st.form(f"{key}_form", border=False):
            st.multiselect("Survey years (1999-2000 to 2024-25)", meta["years"], key=f"{key}_years")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.multiselect("States / Union Territories (empty = all)", meta["states"], key=f"{key}_states")
            with c2:
                st.radio("Classification", ["All", "Manufacturing", "Non-manufacturing"], key=f"{key}_cls",
                         horizontal=True)
            mode = ss[f"{key}_nicmode"]
            if mode == "NIC code":
                lvl = int(ss.get(f"{key}_niclevel", 2))
                col = f"NIC{lvl}"
                codes = sorted(cube[col].cat.categories.tolist())
                def lab(c, lvl=lvl):
                    if lvl == 2:
                        a, b = DIV_2004.get(c), DIV_2008.get(c)
                        if a and b and a != b:
                            return f"{c} · {a} (NIC-1998/2004) | {b} (NIC-2008)"
                        return f"{c} · {a or b or ''}".strip(" ·")
                    n8, n4 = names.get(("NIC-2008", c)), names.get(("NIC-2004", c))
                    if n8 and n4 and n8.lower() != n4.lower():
                        return f"{c} · {n8[:60]} (NIC-2008) | {n4[:60]} (NIC-2004)"
                    nm = n8 or n4
                    return f"{c} · {nm}" if nm else c
                st.multiselect(f"NIC codes, {lvl}-digit (type to search; empty = all)", codes, key=f"{key}_niccodes",
                               format_func=lab)
                st.text_input("Or paste NIC codes (comma or space separated)", key=f"{key}_nicpaste")
                st.caption("NIC codes changed between the 1998/2004 and 2008 editions: a code selects the same digits in "
                           "every year, not the same industry. Use 'Sector name' for a comparison across editions.")
            elif mode == "Sector name":
                secs = sorted(cube["Sector"].cat.categories.tolist())
                st.multiselect("Sector (harmonised across NIC editions; empty = all)", secs, key=f"{key}_sectors")
                st.caption("Sectors group NIC divisions of the 1998/2004 and 2008 editions by product; the concordance "
                           "is approximate at division level.")
            mt = meta["measures"]
            var_opts = ["Est_factories", "N_plants"] + [k for k, v in mt.items() if v[2] != "emission"]
            def vlab(k):
                if k == "Est_factories":
                    return "Number of factories (estimated)"
                if k == "N_plants":
                    return "Plants in the survey sample"
                lab_, unit_, grp = mt[k]
                return f"{lab_} ({unit_}) · {GROUP_LABEL.get(grp, grp)}"
            st.multiselect("Variables (economic, labour, capital, energy; emissions are chosen below)", var_opts,
                           key=f"{key}_vars", format_func=vlab)
            st.markdown("**Greenhouse-gas emissions**")
            e1, e2, e3 = st.columns([2, 2, 2])
            with e1:
                st.multiselect("Emission scope", EMIS_SCOPES, key=f"{key}_scopes",
                               help="Scope 1: fuel combustion in the plant. Scope 2: purchased electricity x CEA grid factor.")
            with e2:
                st.radio("Unit", ["t CO2e", "t (mass of gas)"], key=f"{key}_unit", horizontal=True,
                         help="t CO2e: carbon-dioxide equivalent with the GWP of the inventory. "
                              "t (mass of gas): tonnes of CO2, CH4 and N2O separately.")
            with e3:
                st.multiselect("GHG (Scope 1)", ["CO2", "CH4", "N2O"], key=f"{key}_gases")
            e1, e2 = st.columns(2)
            with e1:
                st.checkbox("Combine the selected gases into one Scope 1 total (t CO2e only)", key=f"{key}_cg")
            with e2:
                st.checkbox("Add the Scope 1 + Scope 2 total (t CO2e only)", key=f"{key}_cs")
            i1, i2 = st.columns(2)
            with i1:
                st.multiselect("Emission intensity: per unit of ...", list(DENOM), key=f"{key}_inden",
                               format_func=lambda k: DENOM[k][0].capitalize())
            with i2:
                st.multiselect("Other ratio indicators", list(OTHER_IND), key=f"{key}_inoth")
            w1, w2 = st.columns([3, 1])
            with w1:
                opts = ["Population estimate (x Multiplier)"] + (["Sample only (unweighted)"] if meta.get("has_unweighted") else [])
                st.radio("Values represent", opts, key=f"{key}_weighted", horizontal=True)
            with w2:
                st.number_input("Hide cells with fewer plants than", 1, 50, key=f"{key}_minp")
            b1, b2, _ = st.columns([1, 1, 4])
            with b1:
                applied = st.form_submit_button("Apply", type="primary", width="stretch", key=f"{key}_apply")
            if applied:
                ss[f"{key}_applied"] = _collect(key, meta)
        st.button("Reset all selections", key=f"{key}_reset", on_click=_reset, args=(key, meta))
    a = ss[f"{key}_applied"]
    return a


def summary_chips(a, meta):
    ys = a["years"]
    parts = [f"{len(ys)} years ({ys[0]} … {ys[-1]})" if len(ys) > 1 else f"year {ys[0]}",
             f"{len(a['states']) or 'all'} states", a["cls"].lower() if a["cls"] != "All" else "all units"]
    if a["nic_mode"] == "code":
        parts.append(f"{len(a['nic_codes']) or 'all'} NIC {a['nic_level']}-digit codes")
    elif a["nic_mode"] == "sector":
        parts.append(f"{len(a['sectors']) or 'all'} sectors")
    parts.append("population estimate" if a["weighted"] else "sample only")
    st.markdown(" ".join(f'<span class="asi-pill">{_html.escape(p)}</span>' for p in parts), unsafe_allow_html=True)


def image_downloads(fig, name, key):
    """PNG / JPG export of a Plotly figure (server-side, kaleido)."""
    sig = hashlib.md5(fig.to_json().encode()).hexdigest()[:10]
    c1, c2, c3 = st.columns([1, 1, 3])
    for col, fmt, mime in ((c1, "png", "image/png"), (c2, "jpg", "image/jpeg")):
        with col:
            sk = f"img_{key}_{fmt}"
            if st.button(f"Prepare {fmt.upper()}", key=f"prep_{key}_{fmt}"):
                try:
                    kw = dict(format="png" if fmt == "png" else "jpeg", scale=2, width=1500, height=int(fig.layout.height or 600))
                    st.session_state[sk] = (sig, fig.to_image(**kw))
                except Exception as e:
                    st.session_state[sk] = (sig, None)
                    st.session_state[sk + "_err"] = f"{type(e).__name__}"
            got = st.session_state.get(sk)
            if got and got[0] == sig and got[1]:
                st.download_button(f"Download {fmt.upper()}", got[1], file_name=f"{name}.{fmt}", mime=mime,
                                   key=f"dl_{key}_{fmt}")
            elif got and got[0] == sig and got[1] is None:
                st.caption("Image export is not available on this server; use the camera icon in the chart toolbar.")


# ============================================================================ pages
def page_home():
    meta, cube, sample, names = data()
    ys = meta["years"]
    _, tcol = st.columns([12, 1])
    with tcol:
        dark = st.session_state.theme == "dark"
        st.button("🌙" if dark else "☀️", key="theme_btn_home", on_click=toggle_theme, width="stretch",
                  help="Dark mode is on - click for light mode" if dark else "Light mode is on - click for dark mode")
    st.markdown(f"""<div class="asi-hero"><h1>ASI Emissions &amp; Industry Explorer</h1>
<p>Plant-level greenhouse-gas emissions (Scope 1 and Scope 2) and economic variables of Indian registered factories,
estimated bottom-up from the unit-level data of the Annual Survey of Industries, {ys[0]} to {ys[-1]}.
Totals are survey-weighted (Horvitz-Thompson) estimates; use the menu on the left to tabulate or plot them.</p></div>""",
                unsafe_allow_html=True)
    last = ys[-1]
    L = cube[cube["Year"] == last]
    pre = "W__"
    def tot(c):
        return float(L[pre + c].sum()) if pre + c in L else float("nan")
    cols = st.columns(4)
    items = [("Survey years", f"{len(ys)}", f"{ys[0]} to {ys[-1]}"),
             ("Plant records", f"{meta['n_plant_records']:,}", "unit-level observations, all years"),
             ("States / UTs", f"{len(meta['states'])}", "as named in the survey files"),
             ("NIC sub-classes", f"{cube['NIC'].nunique():,}", f"codes at {meta.get('cube_nic_digits', 5)}-digit level")]
    for c, it in zip(cols, items):
        c.markdown(card(*it), unsafe_allow_html=True)
    st.write("")
    cols = st.columns(4)
    items = [(f"Estimated factories, {last}", f"{L['Est_factories'].sum():,.0f}", "sum of survey multipliers"),
             (f"Scope 1, {last}", f"{tot('Total_CO2eq_emission') / 1e6:,.1f} Mt CO2e", "fuel combustion, all units"),
             (f"Scope 2, {last}", f"{tot('Scope2_CO2eq_emission') / 1e6:,.1f} Mt CO2e", "purchased electricity"),
             (f"Gross value added, {last}", f"Rs {tot('Gross_Value_Added') / 1e7:,.0f} crore", "current prices")]
    for c, it in zip(cols, items):
        c.markdown(card(*it), unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### About the data")
        st.markdown(f"""
- **Source:** ASI unit-level microdata (MoSPI), blocks A to J, one record per factory (Despatch Serial Number).
- **Emissions:** CO2, CH4 and N2O from fuels purchased and consumed (Blocks H and I), converted with IPCC 2006
  factors (Tier 1) and India-specific coal and lignite factors (Tier 2); Scope 2 = purchased electricity x CEA grid factor of the year.
  CO2-equivalents use the {meta['gwp'].get('basis', 'AR5')} GWP (CH4 {meta['gwp'].get('CH4')}, N2O {meta['gwp'].get('N2O')}).
- **Economic variables** follow the official ASI definitions (output, input, GVA, NVA, net income, profit, capital, employment).
- **Industries:** NIC-1998, NIC-2004 (1999-2007) and NIC-2008 (from 2008-09); use *Sector name* to compare across editions.
- **Data bundle:** built {meta.get('built', '')}; builder version {meta.get('builder_version', '')}.""")
    with c2:
        st.markdown("#### How to start")
        st.markdown("""
1. Open **Tables** to tabulate any combination of years, states, industries and variables, and download the result as CSV.
2. Open **Charts** for 20 chart types (bar, line, pie, treemap, heat map, bubble, map, histogram, box plot and more) with PNG / JPG export.
3. Open **Data set** to download the complete folder of processed results.
4. Open **Guide** for the definitions, the filters and the statistical conventions.""")
    with st.expander("Year-by-year summary"):
        rows = []
        for y in ys:
            Y = cube[cube["Year"] == y]
            rows.append({"Survey year": y, "Plant records": int(Y["N_plants"].sum()),
                         "Estimated factories": float(Y["Est_factories"].sum()),
                         "Scope 1 (Mt CO2e)": float(Y["W__Total_CO2eq_emission"].sum()) / 1e6 if "W__Total_CO2eq_emission" in Y else np.nan,
                         "Scope 2 (Mt CO2e)": float(Y["W__Scope2_CO2eq_emission"].sum()) / 1e6 if "W__Scope2_CO2eq_emission" in Y else np.nan,
                         "GVA (Rs crore)": float(Y["W__Gross_Value_Added"].sum()) / 1e7 if "W__Gross_Value_Added" in Y else np.nan})
        st.markdown(html_table(pd.DataFrame(rows)), unsafe_allow_html=True)


def page_guide():
    meta, *_ = data()
    top_bar("Guide", "How to use the interface")
    st.markdown("""
### Navigation and appearance
- The menu on the left has five pages. The arrow at its top edge **retracts** it to give the page more room.
- The button in the top-right corner switches between **dark mode (🌙)** and **light mode (☀️)**; it shows the mode that is on now.

### The selection panel (Tables and Charts)
| Control | Purpose |
|---|---|
| Number of years (0 – 26) | Quick selection of the latest or earliest N survey years; the meter shows how many years are selected. |
| Survey years | Any combination of years, 1999-2000 to 2024-25. |
| States / Union Territories | Empty means all states. |
| Classification | All units, manufacturing only, or non-manufacturing only. |
| Industry filter | *NIC code* (2 to 5 digits, with division names at 2-digit level, or paste a list of codes) or *Sector name* (harmonised across NIC editions). |
| Variables | Output, input, value added, capital, labour, energy use; emissions are selected separately. |
| Emission scope and unit | Scope 1 and / or Scope 2, in tonnes of CO2-equivalent or in tonnes of each gas; GHG (CO2, CH4, N2O) can be combined or shown separately. |
| Intensity and ratio indicators | Emissions per Rs crore of GVA or output, per person, per factory; productivity and cost shares. |
| Apply / Reset | Nothing is recomputed until you press **Apply**, so choosing many options is instantaneous. **Reset** restores all defaults. |

### Tables
Choose the row variables (up to three), an optional pivot column, the statistic (total, share, per factory, change over time) and the display unit.
The table can be sorted and paged, and the **complete** result is downloaded as CSV.

### Charts
Pick a chart type, the category axis, an optional split and the variable(s). After the chart is drawn, *Prepare PNG* / *Prepare JPG* creates an image, and
*Download chart data (CSV)* gives the numbers behind it. The camera icon in the chart toolbar saves the current view directly from the browser.

### Statistical conventions
- **Population estimate:** every plant value is multiplied by its survey multiplier before summing. Totals are estimates for the whole registered-factory sector.
- **Ratios** (intensities, shares of input or output, productivity) are ratios of weighted totals of the selected group, not averages of plant ratios.
- **Per factory** divides a total by the estimated number of factories (sum of multipliers) in the group.
- **Missing values** are never treated as zero: a group without any reporting plant is shown as –.
- **Distribution charts** (histogram, box, violin, Lorenz) use a weighted random sample of plants, so that they stay fast.
- **NIC editions:** division codes mean different industries before and after 2008-09. Use *Sector name* for comparisons across the break.
- **Emissions in tonnes CO2e** use the GWP of the inventory ("""
                + f"{meta['gwp'].get('basis', 'AR5')}: CH4 {meta['gwp'].get('CH4')}, N2O {meta['gwp'].get('N2O')}"
                + """). Scope 2 contains CO2 from electricity only.
""")
    st.markdown("### Variable dictionary")
    rows = [{"Column": k, "Label": v[0], "Unit": v[1], "Group": GROUP_LABEL.get(v[2], v[2])} for k, v in meta["measures"].items()]
    st.markdown(html_table(pd.DataFrame(rows)), unsafe_allow_html=True)


def page_tables():
    meta, cube, sample, names = data()
    top_bar("Tables", "Cross-tabulate the estimates and download them")
    a = filter_panel("tb")
    summary_chips(a, meta)
    specs = build_specs(a, meta)
    if not specs:
        st.info("Select at least one variable, emission scope or indicator and press Apply.")
        return
    dimopts = [d for d in DIMS if d != "NIC5" or "NIC5" in cube.columns]
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        rows = st.multiselect("Rows (up to three)", dimopts, default=["Year"] if len(a["years"]) > 1 else ["STATE"],
                              format_func=DIMS.get, max_selections=3, key="tb_rows")
    with c2:
        colsel = st.selectbox("Pivot column (optional)", ["(none)"] + [d for d in dimopts if d not in rows],
                              format_func=lambda d: "(none)" if d == "(none)" else DIMS[d], key="tb_col")
    with c3:
        stat = st.selectbox("Statistic", ["total", "share", "per_factory"] + (["change", "index"] if "Year" in rows else []),
                            format_func={"total": "Total / ratio", "share": "Share of selection (%)",
                                         "per_factory": "Per estimated factory", "change": "Change over previous year (%)",
                                         "index": "Index (first year = 100)"}.get, key="tb_stat")
    with c4:
        scale_name = st.selectbox("Display unit", list(SCALES), key="tb_scale")
    by = rows + ([colsel] if colsel != "(none)" else [])
    base_stat = stat if stat in ("total", "share", "per_factory") else "total"
    T = compute_frame(a, by, specs, base_stat, SCALES[scale_name])
    vcols = [sp["label"] for sp in specs]
    if stat in ("change", "index"):
        other = [d for d in by if d != "Year"]
        for c in vcols:
            if stat == "change":
                T[c] = (T.groupby(other, observed=True)[c].pct_change(fill_method=None) if other else T[c].pct_change(fill_method=None)) * 100
            else:
                first = T.groupby(other, observed=True)[c].transform(lambda s: s.dropna().iloc[0] if s.notna().any() else np.nan) if other else T[c].dropna().iloc[0]
                T[c] = T[c] / first * 100
    if colsel != "(none)":
        vsel = st.selectbox("Value shown in the pivot", vcols, key="tb_vsel")
        P = T.pivot_table(index=rows, columns=colsel, values=vsel, aggfunc="first", observed=True)
        P.columns = [str(c) for c in P.columns]
        out = P.reset_index()
    else:
        out = T.drop(columns=["N_plants", "Est_factories"], errors="ignore") if False else T
        out = out.rename(columns={"N_plants": "Plants in sample", "Est_factories": "Estimated factories"})
    out = out.rename(columns={d: DIMS[d] for d in DIMS if d in out.columns})
    for c in out.columns:
        if str(out[c].dtype) == "category":
            out[c] = out[c].astype(str)
    sc1, sc2, sc3, sc4 = st.columns([3, 1, 1, 1])
    with sc1:
        sort_col = st.selectbox("Sort by", list(out.columns), key="tb_sort")
    with sc2:
        desc = st.checkbox("Descending", False, key="tb_desc")
    with sc3:
        psize = st.selectbox("Rows per page", [25, 50, 100, 250], index=1, key="tb_psize")
    n = len(out)
    pages = max(1, -(-n // psize))
    with sc4:
        page = st.number_input("Page", 1, pages, 1, key="tb_page")
    if sort_col in out:
        try:
            out = out.sort_values(sort_col, ascending=not desc, kind="stable", na_position="last")
        except TypeError:
            pass
    st.caption(f"{n:,} rows × {len(out.columns)} columns" + (f" · page {int(page)} of {pages}" if pages > 1 else ""))
    view = out.iloc[(int(page) - 1) * psize: int(page) * psize]
    st.markdown(html_table(view), unsafe_allow_html=True)
    st.write("")
    st.download_button("Download the full table (CSV)", out.to_csv(index=False).encode("utf-8-sig"),
                       file_name="ASI_table.csv", mime="text/csv", key="tb_dl", type="primary")
    with st.expander("Notes on this table"):
        st.markdown("\n".join(f"- **{sp['label']}**" for sp in specs) +
                    "\n\nUnits: " + ("rupees at current prices (display unit applied), tonnes, persons, kWh or TJ as stated in the column name. "
                                     "Shares and indicators are not rescaled."))


CHART_TYPES = [
    "Bar - grouped", "Bar - horizontal ranking", "Bar - stacked", "Bar - 100% stacked", "Pareto (bars + cumulative share)",
    "Line - trend over years", "Area - stacked trend", "Pie", "Donut", "Treemap", "Sunburst", "Heat map",
    "Bubble (three variables)", "Scatter (two variables)", "Bubble map of states", "Histogram (plants)",
    "Box plot (plants)", "Violin plot (plants)", "Concentration (Lorenz) curve", "Correlation matrix",
    "Waterfall (change between two years)", "Radar profile",
]


def fold_top(df, cat, y, n, additive, keys):
    """Keep the n largest groups of `cat`; fold the remainder into 'Other' (additive measures) or drop them."""
    df = df.copy()
    df[cat] = df[cat].astype(str)
    tot = df.groupby(cat, observed=True)[y].sum().sort_values(ascending=False)
    keep = tot.index[:n].tolist()
    if len(tot) <= n:
        return df, keep
    if additive:
        df[cat] = df[cat].where(df[cat].isin(keep), "Other")
        df = df.groupby(keys, observed=True, as_index=False)[y].sum(min_count=1)
        return df, keep + ["Other"]
    return df[df[cat].isin(keep)], keep


def page_charts():
    meta, cube, sample, names = data()
    top_bar("Charts", "Visualise the estimates; every chart can be saved as PNG or JPG")
    a = filter_panel("ch")
    summary_chips(a, meta)
    specs = build_specs(a, meta)
    if not specs:
        st.info("Select at least one variable, emission scope or indicator and press Apply.")
        return
    labels = [sp["label"] for sp in specs]
    bylab = {sp["label"]: sp for sp in specs}
    dimopts = [d for d in DIMS if d != "NIC5" or "NIC5" in cube.columns]
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        ctype = st.selectbox("Chart type", CHART_TYPES, key="ch_type")
    with c2:
        stat = st.selectbox("Statistic", ["total", "share", "per_factory"],
                            format_func={"total": "Total / ratio", "share": "Share of selection (%)",
                                         "per_factory": "Per estimated factory"}.get, key="ch_stat")
    with c3:
        scale_name = st.selectbox("Display unit", list(SCALES), key="ch_scale")
    with c4:
        topn = st.slider("Largest groups shown", 3, 40, 12, key="ch_topn")
    scale = SCALES[scale_name]
    is_trend = ctype.startswith(("Line", "Area"))
    needs_sample = ctype.startswith(("Histogram", "Box", "Violin", "Concentration"))
    d1, d2, d3 = st.columns([2, 2, 3])
    with d1:
        cat = st.selectbox("Category / group by", dimopts, index=dimopts.index("Year") if is_trend else dimopts.index("STATE"),
                           format_func=DIMS.get, key="ch_cat")
    with d2:
        split = st.selectbox("Colour / split by", ["(none)"] + [d for d in dimopts if d != cat],
                             format_func=lambda d: "(none)" if d == "(none)" else DIMS[d], key="ch_split")
        split = None if split == "(none)" else split
    with d3:
        y = st.selectbox("Variable (vertical axis / values)", labels, key="ch_y")
    sp_y = bylab[y]
    extra = {}
    if ctype.startswith(("Bubble (", "Scatter")):
        e1, e2, e3 = st.columns(3)
        with e1:
            extra["x"] = st.selectbox("Horizontal axis variable", labels, index=min(1, len(labels) - 1), key="ch_x")
        with e2:
            if ctype.startswith("Bubble ("):
                extra["size"] = st.selectbox("Bubble size variable", labels, index=min(2, len(labels) - 1), key="ch_size")
        with e3:
            extra["anim"] = st.checkbox("Animate over survey years", False, key="ch_anim") and cat != "Year"
            extra["log"] = st.checkbox("Logarithmic axes", True, key="ch_log")
    if ctype.startswith("Bar") or ctype.startswith("Pareto"):
        extra["log"] = st.checkbox("Logarithmic value axis", False, key="ch_logv")
        extra["labels"] = st.checkbox("Show value labels", False, key="ch_vl")
    if is_trend:
        extra["mode"] = st.radio("Show as", ["Level", "Index (first year = 100)", "Growth over previous year (%)"],
                                 horizontal=True, key="ch_mode")
    if needs_sample:
        extra["log"] = st.checkbox("Logarithmic scale (positive values only)", True, key="ch_logs")
    if ctype.startswith("Waterfall"):
        ys = list(a["years"])
        if len(ys) < 2:
            st.info("Select at least two survey years for a waterfall chart.")
            return
        w1, w2 = st.columns(2)
        with w1:
            extra["y0"] = st.selectbox("From year", ys, index=0, key="ch_y0")
        with w2:
            extra["y1"] = st.selectbox("To year", ys, index=len(ys) - 1, key="ch_y1")
    if ctype.startswith("Radar") or ctype.startswith("Correlation"):
        extra["multi"] = st.multiselect("Variables compared", labels, default=labels[: min(6, len(labels))], key="ch_multi")

    additive = sp_y["kind"] == "level" and stat in ("total", "share")
    fig, data_out, note = None, None, ""
    try:
        fig, data_out, note = build_chart(ctype, a, specs, sp_y, y, cat, split, stat, scale, topn, additive, extra, meta)
    except Exception as e:      # never leave the page blank
        st.error(f"This combination cannot be drawn ({type(e).__name__}: {e}). Adjust the selection and try again.")
        return
    if fig is None:
        st.info(note or "Nothing to draw for this selection.")
        return
    cfg = {"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "ASI_chart"}}
    st.plotly_chart(fig, width="stretch", config=cfg, theme=None)
    if note:
        st.caption(note)
    image_downloads(fig, "ASI_chart", f"{ctype}")
    if data_out is not None:
        st.download_button("Download chart data (CSV)", data_out.to_csv(index=False).encode("utf-8-sig"),
                           file_name="ASI_chart_data.csv", mime="text/csv", key="ch_csv")
        with st.expander("Data behind the chart"):
            st.markdown(html_table(data_out, max_rows=300), unsafe_allow_html=True)


def build_chart(ctype, a, specs, sp_y, y, cat, split, stat, scale, topn, additive, ex, meta):
    """Returns (figure, data frame, note)."""
    sec = [d for d in [cat, split] if d]
    ylab = y if stat == "total" else (y + " - share (%)" if stat == "share" else y + " - per factory")
    # ---------------- distribution charts (sample) ------------------------------
    if ctype.startswith(("Histogram", "Box", "Violin", "Concentration")):
        need = bases_of([sp_y])
        samp = meta["sample_vars"]
        if any(b not in samp for b in need):
            return None, None, "This variable is not available for plant-level distributions; choose an emission, output, GVA, capital or employment variable."
        _, _, S, _ = data()
        m = make_mask(S, a)
        sub = S.loc[m].copy()
        if sp_y["den"]:
            vals = eval_spec(sub.astype({b: float for b in need}), sp_y)
        else:
            vals = eval_spec(sub.astype({b: float for b in need}), sp_y)
        sub["value"] = vals.values
        sub = sub.dropna(subset=["value"])
        if ex.get("log"):
            sub = sub[sub["value"] > 0]
        if sub.empty:
            return None, None, "No plant has a positive value for this selection."
        g = split or (cat if cat in ("Year", "Class", "Sector", "Division", "STATE") else None)
        if g:
            top = sub.groupby(g, observed=True)["weight"].sum().sort_values(ascending=False).index[:8].tolist()
            sub = sub[sub[g].isin(top)]
            sub[g] = sub[g].astype(str)
        if ctype.startswith("Histogram"):
            sub["plot"] = np.log10(sub["value"]) if ex.get("log") else sub["value"]
            fig = px.histogram(sub, x="plot", y="weight", color=g, nbins=60, histfunc="sum", barmode="overlay",
                               opacity=.7, color_discrete_sequence=PALETTE,
                               labels={"plot": ("log10 of " if ex.get("log") else "") + y, "weight": "Estimated factories"})
            fig.update_yaxes(title="Estimated factories")
            return fig_style(fig, 540, "Distribution of plants"), sub[[c for c in ["Year", "STATE", g, "value", "weight"] if c]].head(5000), \
                f"{len(sub):,} sampled plants (weighted by survey multiplier / sampling fraction)."
        if ctype.startswith("Box"):
            fig = px.box(sub, x="value", y=g, color=g, points=False, log_x=bool(ex.get("log")),
                         color_discrete_sequence=PALETTE, labels={"value": y})
        elif ctype.startswith("Violin"):
            fig = px.violin(sub, x="value", y=g, color=g, box=True, points=False, log_x=bool(ex.get("log")),
                            color_discrete_sequence=PALETTE, labels={"value": y})
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", name="Equal distribution",
                                     line=dict(dash="dot", color="#9aa8b8")))
            rows = []
            groups = [(None, sub)] if not g else [(k, d) for k, d in sub.groupby(g, observed=True)]
            for i, (k, d) in enumerate(groups):
                d = d[d["value"] >= 0].sort_values("value")
                w = d["weight"].to_numpy(); v = d["value"].to_numpy()
                if len(v) < 2 or (v * w).sum() == 0:
                    continue
                cw = np.concatenate([[0], np.cumsum(w) / w.sum()]); cv = np.concatenate([[0], np.cumsum(v * w) / (v * w).sum()])
                gini = 1 - np.sum((cv[1:] + cv[:-1]) * np.diff(cw))
                step = max(1, len(cw) // 1500)
                fig.add_trace(go.Scatter(x=cw[::step] * 100, y=cv[::step] * 100, mode="lines", name=f"{k or 'All'} (Gini {gini:.2f})",
                                         line=dict(color=PALETTE[i % len(PALETTE)], width=2)))
                rows.append({"Group": k or "All", "Plants (sample)": len(d), "Gini": round(float(gini), 3)})
            fig.update_layout(xaxis_title="Cumulative share of plants, smallest to largest (%)",
                              yaxis_title=f"Cumulative share of {y} (%)")
            return fig_style(fig, 560, "Concentration"), pd.DataFrame(rows), "Weighted sample of plants; Gini coefficient in the legend."
        return fig_style(fig, 520), sub[["value", "weight"]].head(5000), f"{len(sub):,} sampled plants."
    # ---------------- map ---------------------------------------------------------
    if ctype.startswith("Bubble map"):
        T = compute_frame(a, ["STATE"], [sp_y], stat, scale)
        T = T[T[y].notna() & (T[y] > 0)]
        T["lat"] = T["STATE"].astype(str).map(lambda s: STATE_XY.get(s, (np.nan, np.nan))[0])
        T["lon"] = T["STATE"].astype(str).map(lambda s: STATE_XY.get(s, (np.nan, np.nan))[1])
        T = T.dropna(subset=["lat"])
        if T.empty:
            return None, None, "No state could be placed on the map."
        fig = px.scatter_geo(T, lat="lat", lon="lon", size=y, color=y, hover_name="STATE", color_continuous_scale="Turbo",
                             size_max=46)
        fig.update_geos(scope="asia", center=dict(lat=22, lon=80), projection_scale=4.2, showcountries=True,
                        showland=True, landcolor="rgba(120,130,140,0.18)", countrycolor="rgba(150,160,170,0.5)",
                        bgcolor="rgba(0,0,0,0)")
        return fig_style(fig, 620, ylab + " by state"), T[["STATE", y]].sort_values(y, ascending=False), \
            "Bubble positions are approximate state centroids."
    # ---------------- correlation / radar ---------------------------------------
    if ctype.startswith(("Correlation", "Radar")):
        multi = ex.get("multi") or []
        sp = [s for s in specs if s["label"] in multi]
        if len(sp) < 2:
            return None, None, "Select at least two variables to compare."
        T = compute_frame(a, [cat], sp, "total", 1.0)
        if ctype.startswith("Correlation"):
            C = T[[s["label"] for s in sp]].corr()
            fig = go.Figure(go.Heatmap(z=C.values, x=C.columns, y=C.index, zmin=-1, zmax=1, colorscale="RdBu",
                                       text=np.round(C.values, 2), texttemplate="%{text}"))
            fig.update_yaxes(autorange="reversed")
            return fig_style(fig, 560, f"Correlation across {DIMS[cat].lower()} groups"), C.reset_index(), \
                f"Pearson correlation of group totals over {len(T):,} groups."
        top = T.sort_values(sp[0]["label"], ascending=False).head(min(topn, 8))
        fig = go.Figure()
        cats = [s["label"] for s in sp]
        for i, r in enumerate(top.itertuples(index=False)):
            row = top.iloc[i]
            vals = [float(row[c]) / float(T[c].max()) * 100 if T[c].max() else 0 for c in cats]
            fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=cats + cats[:1], fill="toself", name=str(row[cat]), opacity=.55))
        return fig_style(fig, 600, "Profile (index: group maximum = 100)"), top, "Each variable is scaled so that the largest group equals 100."
    # ---------------- waterfall ---------------------------------------------------
    if ctype.startswith("Waterfall"):
        a2 = dict(a); a2["years"] = tuple(sorted({ex["y0"], ex["y1"]}, key=meta["years"].index))
        T = compute_frame(a2, [cat, "Year"] if cat != "Year" else ["Year"], [sp_y], "total", scale)
        if cat == "Year":
            return None, None, "Choose a category other than the survey year for a waterfall chart."
        P = T.pivot_table(index=cat, columns="Year", values=y, aggfunc="sum", observed=True)
        if ex["y0"] not in P or ex["y1"] not in P:
            return None, None, "No data in one of the two years."
        P["delta"] = P[ex["y1"]].fillna(0) - P[ex["y0"]].fillna(0)
        P = P.reindex(P["delta"].abs().sort_values(ascending=False).index)
        head, tail = P.head(topn), P.iloc[topn:]
        xs = [f"{ex['y0']} total"] + head.index.astype(str).tolist() + (["Other groups"] if len(tail) else []) + [f"{ex['y1']} total"]
        ys_ = [P[ex["y0"]].sum()] + head["delta"].tolist() + ([tail["delta"].sum()] if len(tail) else []) + [P[ex["y1"]].sum()]
        meas = ["absolute"] + ["relative"] * (len(xs) - 2) + ["total"]
        fig = go.Figure(go.Waterfall(x=xs, y=ys_, measure=meas, increasing=dict(marker=dict(color="#2fd6a1")),
                                     decreasing=dict(marker=dict(color="#ff6b6b")), totals=dict(marker=dict(color="#4da3ff"))))
        return fig_style(fig, 560, f"{y}: change {ex['y0']} to {ex['y1']}"), P.reset_index(), ""
    # ---------------- bubble / scatter ----------------------------------------------
    if ctype.startswith(("Bubble (", "Scatter")):
        sx = next(s for s in specs if s["label"] == ex["x"])
        pick = [sp_y, sx] + ([next(s for s in specs if s["label"] == ex["size"])] if "size" in ex else [])
        pick = list({s["label"]: s for s in pick}.values())
        by = [cat] + ([split] if split else []) + (["Year"] if ex.get("anim") else [])
        T = compute_frame(a, by, pick, "total", 1.0)
        T = T.dropna(subset=[y, ex["x"]])
        if ex.get("log"):
            T = T[(T[y] > 0) & (T[ex["x"]] > 0)]
        if "size" in ex:
            T = T[T[ex["size"]] > 0]
        if T.empty:
            return None, None, "No group has positive values for all selected variables."
        for c in T.columns:
            if str(T[c].dtype) == "category":
                T[c] = T[c].astype(str)
        kw = dict(x=ex["x"], y=y, hover_name=cat, color=split or (cat if T[cat].nunique() <= 12 else None),
                  log_x=bool(ex.get("log")), log_y=bool(ex.get("log")), color_discrete_sequence=PALETTE)
        if "size" in ex:
            kw.update(size=ex["size"], size_max=55)
        if ex.get("anim"):
            kw.update(animation_frame="Year", animation_group=cat)
            T = T.sort_values("Year")
        fig = px.scatter(T, **kw)
        return fig_style(fig, 600), T, f"{len(T):,} groups of {DIMS[cat].lower()}."
    # ---------------- aggregated charts -------------------------------------------
    if ctype == "Heat map" and not split:
        split = "Year" if cat != "Year" else "STATE"
        sec = [cat, split]
    is_trend_chart = ctype.startswith(("Line", "Area"))
    if is_trend_chart:
        grp = split or (cat if cat != "Year" else None)
        by = ["Year"] + ([grp] if grp else [])
    else:
        grp = None
        by = sec if sec else [cat]
    T = compute_frame(a, by, [sp_y], stat, scale)
    for c in T.columns:
        if str(T[c].dtype) == "category" and c != "Year":
            T[c] = T[c].astype(str)
    T = T.dropna(subset=[y])
    if T.empty:
        return None, None, "No data for this selection."
    if is_trend_chart:
        mode = ex.get("mode", "Level")
        T["Year"] = T["Year"].astype(str)
        if grp:
            T, _ = fold_top(T, grp, y, topn, additive, ["Year", grp])
        order = meta["years"]
        T = T.sort_values("Year", key=lambda s_: s_.map({v: i for i, v in enumerate(order)})).reset_index(drop=True)
        if mode.startswith("Index"):
            f0 = T.groupby(grp)[y].transform(lambda s_: s_.dropna().iloc[0] if s_.notna().any() else np.nan) if grp \
                else (T[y].dropna().iloc[0] if T[y].notna().any() else np.nan)
            T["plot"] = T[y] / f0 * 100
            yl = y + ", index (first year = 100)"
        elif mode.startswith("Growth"):
            T["plot"] = (T.groupby(grp)[y].pct_change(fill_method=None) if grp else T[y].pct_change(fill_method=None)) * 100
            yl = y + ", growth over previous year (%)"
        else:
            T["plot"] = T[y]
            yl = ylab
        if ctype.startswith("Line"):
            fig = px.line(T, x="Year", y="plot", color=grp, markers=True, color_discrete_sequence=PALETTE, labels={"plot": yl})
        else:
            fig = px.area(T, x="Year", y="plot", color=grp, color_discrete_sequence=PALETTE, labels={"plot": yl})
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=[o for o in order if o in set(T["Year"])])
        return fig_style(fig, 540), T.drop(columns=["plot"]), ""
    # category-based charts
    tot_col = T.groupby(cat, observed=True)[y].sum().sort_values(ascending=False)
    keep = tot_col.index[:topn].tolist()
    if len(tot_col) > topn:
        if additive:
            T[cat] = T[cat].astype(str).where(T[cat].isin(keep), "Other")
            T = T.groupby([c for c in by], observed=True, as_index=False)[y].sum(min_count=1)
            keep = keep + ["Other"]
        else:
            T = T[T[cat].isin(keep)]
    T[cat] = T[cat].astype(str)
    if cat == "Year":
        keep = [k for k in meta["years"] if k in set(T[cat])]
    T = T.sort_values(y, ascending=False) if cat != "Year" else T
    cmap = {"Other": "#9aa8b8"}
    if ctype.startswith("Bar - grouped") or ctype.startswith("Bar - stacked") or ctype.startswith("Bar - 100"):
        kw = dict(x=cat, y=y, color=split, color_discrete_sequence=PALETTE, category_orders={cat: keep},
                  log_y=bool(ex.get("log")), text_auto=".3s" if ex.get("labels") else False)
        fig = px.bar(T, barmode="group" if "grouped" in ctype else "relative", **kw)
        if "100" in ctype:
            fig.update_layout(barnorm="percent")
            fig.update_yaxes(title="Share (%)")
        fig.update_xaxes(title=DIMS.get(cat, cat))
        return fig_style(fig, 540), T, ""
    if ctype.startswith("Bar - horizontal"):
        T2 = T.groupby(cat, observed=True, as_index=False)[y].sum(min_count=1).sort_values(y)
        fig = px.bar(T2, x=y, y=cat, orientation="h", color_discrete_sequence=PALETTE, log_x=bool(ex.get("log")),
                     text_auto=".3s" if ex.get("labels") else False)
        fig.update_yaxes(type="category")
        return fig_style(fig, max(420, 26 * len(T2) + 120)), T2.sort_values(y, ascending=False), ""
    if ctype.startswith("Pareto"):
        T2 = T.groupby(cat, observed=True, as_index=False)[y].sum(min_count=1).sort_values(y, ascending=False)
        T2["cum"] = T2[y].cumsum() / T2[y].sum() * 100
        fig = go.Figure()
        fig.add_trace(go.Bar(x=T2[cat], y=T2[y], name=y, marker_color=PALETTE[0]))
        fig.add_trace(go.Scatter(x=T2[cat], y=T2["cum"], name="Cumulative share (%)", yaxis="y2", mode="lines+markers",
                                 line=dict(color=PALETTE[1])))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105], title="Cumulative share (%)", showgrid=False),
                          yaxis_title=ylab)
        return fig_style(fig, 540), T2, ""
    if ctype in ("Pie", "Donut"):
        T2 = T.groupby(cat, observed=True, as_index=False)[y].sum(min_count=1)
        T2 = T2[T2[y] > 0]
        fig = px.pie(T2, names=cat, values=y, hole=.5 if ctype == "Donut" else 0, color_discrete_sequence=PALETTE)
        fig.update_traces(textposition="inside", texttemplate="%{label}<br>%{percent}")
        return fig_style(fig, 560, ylab), T2, "Negative and zero values are left out of pie charts."
    if ctype in ("Treemap", "Sunburst"):
        T2 = T[T[y] > 0]
        path = ([split] if split else []) + [cat]
        if T2.empty:
            return None, None, "No positive values."
        fn = px.treemap if ctype == "Treemap" else px.sunburst
        fig = fn(T2, path=path, values=y, color_discrete_sequence=PALETTE)
        fig.update_traces(texttemplate="%{label}<br>%{percentRoot:.1%}" if ctype == "Treemap" else None)
        return fig_style(fig, 600), T2, "Only positive values are drawn."
    if ctype == "Heat map":
        if not split:
            return None, None, "Choose a 'Colour / split by' variable: it forms the columns of the heat map."
        P = T.pivot_table(index=cat, columns=split, values=y, aggfunc="sum", observed=True)
        if split == "Year":
            P = P[[c for c in meta["years"] if c in P.columns]]
        fig = go.Figure(go.Heatmap(z=P.values, x=[str(c) for c in P.columns], y=[str(i) for i in P.index],
                                   colorscale="Viridis", colorbar=dict(title=""),
                                   hovertemplate=f"{DIMS[cat]}: %{{y}}<br>{DIMS[split]}: %{{x}}<br>{y}: %{{z:,.2f}}<extra></extra>"))
        fig.update_yaxes(autorange="reversed", type="category"); fig.update_xaxes(type="category")
        return fig_style(fig, max(440, 24 * len(P) + 160), ylab), P.reset_index(), ""
    return None, None, "Chart type not available."


def page_dataset():
    meta, *_ = data()
    top_bar("Data set", "Download the processed results")
    idx = os.path.join(STATIC_DIR, "files.json")
    items = json.load(open(idx)) if os.path.exists(idx) else []
    st.markdown("""The data set is the folder **ASI emission estimated results**: one sub-folder per survey year
(`ASI_ESTIMTED_DATA_<yyyy_yy>_CSV`) with the plant-level file (`Desirable_variables_<yyyy_yy>.csv`), the NIC-level, State, State × NIC-2 and
All-India roll-ups and an `Analysis_<yyyy_yy>` folder with fuel-line detail and reconciliation tables, plus the all-years summary files.""")
    if items:
        allz = [i for i in items if i["kind"] == "all"]
        if allz:
            st.markdown("#### Entire folder")
            st.markdown('<div class="asi-dl">' + "".join(
                f'<a href="app/static/{i["file"]}" download>⬇ {i["label"]} (ZIP, {i["size_mb"]:,.0f} MB)</a>' for i in allz) + "</div>",
                unsafe_allow_html=True)
        yrs = [i for i in items if i["kind"] == "year"]
        if yrs:
            st.markdown("#### One survey year at a time")
            st.markdown('<div class="asi-dl">' + "".join(
                f'<a href="app/static/{i["file"]}" download>⬇ {i["label"].replace("ASI_ESTIMTED_DATA_", "").replace("_CSV", "").replace("_", "-")} ({i["size_mb"]:,.0f} MB)</a>'
                for i in yrs) + "</div>", unsafe_allow_html=True)
        summ = [i for i in items if i["kind"] == "summary"]
        if summ:
            st.markdown("#### Summary files (all years)")
            st.markdown('<div class="asi-dl">' + "".join(
                f'<a href="app/static/{i["file"]}" download>⬇ {i["label"]}</a>' for i in summ) + "</div>", unsafe_allow_html=True)
    elif DATASET_URL:
        st.markdown(f'<div class="asi-dl"><a href="{_html.escape(DATASET_URL)}" target="_blank">⬇ Download the entire folder</a></div>',
                    unsafe_allow_html=True)
    else:
        st.info("The download files have not been prepared on this server. Ask the owner of the app for the data set.")
    cp = os.path.join(BUNDLE_DIR, "catalogue.csv")
    if os.path.exists(cp):
        with st.expander("List of files in the results folder"):
            cat_ = pd.read_csv(cp)
            q = st.text_input("Filter the list (text in the file path)", "", key="ds_q")
            if q:
                cat_ = cat_[cat_["path"].str.contains(q, case=False, regex=False)]
            st.caption(f"{len(cat_):,} files")
            st.markdown(html_table(cat_.head(400)), unsafe_allow_html=True)
    st.markdown("#### Citation and terms")
    st.markdown("Emission estimates are model results built from the ASI unit-level data and the stated emission factors; "
                "they are not official statistics. Please cite the data set together with the survey years used.")


# ============================================================================ shell
def gate():
    if not PASSWORD or st.session_state.get("_auth"):
        return True
    st.markdown("## ASI Emissions & Industry Explorer")
    pw = st.text_input("Password", type="password")
    if pw and pw.strip() == PASSWORD.strip():
        st.session_state["_auth"] = True
        st.rerun()
    elif pw:
        st.error("Incorrect password (case-sensitive).")
    return False


def main():
    ss = st.session_state
    qp = st.query_params
    if "theme" not in ss:
        ss.theme = qp.get("theme", "dark") if qp.get("theme", "dark") in THEMES else "dark"
    inject_css()
    if not gate():
        return
    if not os.path.exists(os.path.join(BUNDLE_DIR, "meta.json")):
        st.error(f"Data bundle not found in {BUNDLE_DIR}. Build it with asi_bundle.build_bundle().")
        return
    meta, *_ = data()
    pages = {"🏠  Home": page_home, "📖  Guide": page_guide, "📋  Tables": page_tables,
             "📊  Charts": page_charts, "💾  Data set": page_dataset}
    if "page" not in ss:
        want = qp.get("page", "")
        ss.page = next((k for k in pages if want and want.lower() in k.lower()), "🏠  Home")
    with st.sidebar:
        st.markdown("### 🏭 ASI Explorer")
        st.caption(f"Emissions inventory {meta['years'][0]} to {meta['years'][-1]}")
        st.radio("Menu", list(pages), key="page", label_visibility="collapsed",
                 on_change=lambda: st.query_params.update({"page": st.session_state.page.split()[-1].lower()}))
        st.markdown("---")
        st.caption(f"Version {APP_VERSION} · data built {meta.get('built', '')}")
    pages[ss.page]()


main()
