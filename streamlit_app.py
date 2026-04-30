import json
import os
import ssl
from html import escape
from urllib.parse import urlencode
from urllib.request import urlopen

import streamlit as st

from market_data import fetch_live_crude_prices
from route_distances import PORTS, estimate_distance_nm


st.set_page_config(
    page_title="Voyage Commander",
    page_icon="VC",
    layout="wide",
    initial_sidebar_state="expanded",
)


FALLBACK_NEWS = [
    {
        "title": "Port congestion watch: China discharge windows tighten",
        "source": "Operations desk fallback",
        "description": "Ningbo anchorage delays remain the highest sensitivity in this voyage model.",
    },
    {
        "title": "Canal transit delays lift prompt freight premiums",
        "source": "Freight risk fallback",
        "description": "Chokepoint uncertainty increases the value of fast operational intervention.",
    },
    {
        "title": "OPEC supply signals keep crude flat while SOFR drag persists",
        "source": "Market context fallback",
        "description": "Stable flat price can still hide margin erosion from financing and demurrage.",
    },
]

INCOTERMS = {
    "FOB": {
        "note": "Buyer-side FOB exposure: freight, insurance, discharge demurrage, and financing stay on your desk.",
        "costs": {"freight", "insurance", "discharge", "finance"},
    },
    "CIF": {
        "note": "CIF exposure: seller covers freight and insurance; discharge demurrage and financing remain live.",
        "costs": {"discharge", "finance"},
    },
    "DDP": {
        "note": "DDP exposure: full landed-delivery economics, including local duties converted back to USD.",
        "costs": {"freight", "insurance", "discharge", "finance", "duties", "inland"},
    },
}

ROUTE_PRESETS = {
    "Arab Gulf to China: Ras Tanura → Ningbo": ("Ras Tanura", "Ningbo"),
    "Iraq to China: Basrah Oil Terminal → Qingdao": ("Basrah Oil Terminal", "Qingdao"),
    "Kuwait to Korea: Mina Al Ahmadi → Ulsan": ("Mina Al Ahmadi", "Ulsan"),
    "Iran to India: Kharg Island → Jamnagar": ("Kharg Island", "Jamnagar"),
    "UAE storage to Singapore: Fujairah → Singapore": ("Fujairah", "Singapore"),
    "Saudi Red Sea to Europe: Yanbu → Rotterdam": ("Yanbu", "Rotterdam"),
    "US Gulf to Europe: Corpus Christi → Rotterdam": ("Corpus Christi", "Rotterdam"),
    "US Gulf to Asia: Houston → Ningbo": ("Houston", "Ningbo"),
    "West Africa to Europe: Bonny → Rotterdam": ("Bonny", "Rotterdam"),
    "Angola to China: Luanda → Zhoushan": ("Luanda", "Zhoushan"),
    "Mediterranean to Italy: Ceyhan → Trieste": ("Ceyhan", "Trieste"),
    "Black Sea to Med: Novorossiysk → Augusta": ("Novorossiysk", "Augusta"),
    "North Sea/Baltic to ARA: Primorsk → Rotterdam": ("Primorsk", "Rotterdam"),
    "Brazil to China: Sao Sebastiao → Dalian": ("Sao Sebastiao", "Dalian"),
    "Venezuela to US Gulf: Jose Terminal → LOOP": ("Jose Terminal", "LOOP"),
    "Manual selection": (None, None),
}


def secret_or_env(key):
    try:
        return st.secrets.get(key) or os.getenv(key)
    except Exception:
        return os.getenv(key)


def get_json(url, timeout=4):
    context = None
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass

    with urlopen(url, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


@st.cache_data(ttl=900)
def fetch_sofr():
    api_key = secret_or_env("FRED_API_KEY")
    if not api_key:
        return 5.31, "fallback"

    params = urlencode(
        {
            "series_id": "SOFR",
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
    )
    try:
        payload = get_json(f"https://api.stlouisfed.org/fred/series/observations?{params}")
        return float(payload["observations"][0]["value"]), "FRED SOFR"
    except Exception:
        return 5.31, "fallback"


@st.cache_data(ttl=900)
def fetch_fx():
    api_key = secret_or_env("EXCHANGERATE_API_KEY")
    attempts = []

    if api_key and api_key.startswith("fxr_"):
        attempts = [
            (
                "https://api.fxapi.com/v1/latest?"
                + urlencode({"apikey": api_key, "base_currency": "USD", "currencies": "CNY"}),
                lambda payload: float(payload["data"]["CNY"]["value"]),
            ),
            (
                "https://api.fxratesapi.com/latest?"
                + urlencode({"apikey": api_key, "base": "USD", "symbols": "CNY"}),
                lambda payload: float(payload["rates"]["CNY"]),
            ),
        ]
    elif api_key:
        attempts = [
            (
                f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD",
                lambda payload: float(payload["conversion_rates"]["CNY"]),
            )
        ]

    attempts.append(("https://open.er-api.com/v6/latest/USD", lambda payload: float(payload["rates"]["CNY"])))

    for url, parser in attempts:
        try:
            return parser(get_json(url)), "FX"
        except Exception:
            pass

    return 7.18, "fallback"


@st.cache_data(ttl=900)
def fetch_news():
    api_key = secret_or_env("NEWS_API_KEY")
    if not api_key:
        return FALLBACK_NEWS

    query = '"port strike" OR "canal delay" OR OPEC OR "freight rates" OR "choke point"'
    params = urlencode(
        {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": api_key,
        }
    )

    try:
        payload = get_json(f"https://newsapi.org/v2/everything?{params}")
        articles = []
        for item in payload.get("articles", [])[:5]:
            articles.append(
                {
                    "title": item.get("title") or "Market context update",
                    "source": (item.get("source") or {}).get("name") or "NewsAPI",
                    "description": item.get("description") or "Operational risk context for the voyage desk.",
                }
            )
        return articles or FALLBACK_NEWS
    except Exception:
        return FALLBACK_NEWS


def money(value):
    return f"${value:,.0f}"


def money2(value):
    return f"${value:,.2f}"


st.markdown(
    """
    <style>
    :root {
        --vc-bg: #eef2f4;
        --vc-panel: #ffffff;
        --vc-ink: #101820;
        --vc-muted: #69737c;
        --vc-line: #d7dee4;
        --vc-sidebar: #111a21;
        --vc-sidebar-2: #18242e;
        --vc-accent: #0d7c66;
        --vc-red: #b3261e;
        --vc-amber: #b86114;
    }
    .stApp { background: var(--vc-bg); color: var(--vc-ink); }
    .main .block-container {
        max-width: 1120px;
        padding: 2.2rem 2.2rem 4rem;
    }
    h1, h2, h3, p, span, div { color: var(--vc-ink); }
    div[data-testid="stMarkdownContainer"] > h3 {
        font-size: 22px;
        margin: 1.15rem 0 0.6rem;
        letter-spacing: 0;
    }
    [data-testid="stSidebar"] {
        background: var(--vc-sidebar);
        border-right: 1px solid #27343f;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #f4f7f8 !important;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #9aa7b2 !important;
    }
    [data-testid="stSidebar"] input {
        background: var(--vc-sidebar-2) !important;
        color: #f4f7f8 !important;
        -webkit-text-fill-color: #f4f7f8 !important;
        border: 1px solid #33424e !important;
    }
    [data-testid="stSidebar"] button {
        color: #f4f7f8 !important;
        background: #22313c !important;
        border-color: #33424e !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: var(--vc-sidebar-2) !important;
        border: 1px solid #33424e !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] span,
    [data-testid="stSidebar"] div[data-baseweb="select"] svg {
        color: #f4f7f8 !important;
        fill: #f4f7f8 !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        background: transparent !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #283540;
    }
    .vc-brand {
        margin-bottom: 1.2rem;
    }
    .vc-brand small {
        display: block;
        color: #d99b39;
        font-size: 11px;
        font-weight: 850;
        letter-spacing: 0.07em;
        text-transform: uppercase;
    }
    .vc-brand strong {
        display: block;
        color: #f4f7f8;
        font-size: 20px;
        margin-top: 2px;
    }
    [data-testid="stAlert"] {
        background: #fff6d6;
        border: 1px solid #ead28a;
        color: #4f3b00;
    }
    [data-testid="stAlert"] * { color: #4f3b00 !important; }
    .vc-header {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 24px;
        align-items: end;
        margin: 0 0 18px;
    }
    .vc-kicker {
        color: #65717b;
        font-size: 12px;
        font-weight: 850;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .vc-title {
        color: var(--vc-ink);
        font-size: 42px;
        line-height: 1.02;
        font-weight: 860;
        letter-spacing: 0;
        margin: 0;
        max-width: 760px;
    }
    .vc-card {
        background: var(--vc-panel);
        border: 1px solid var(--vc-line);
        border-radius: 8px;
        padding: 16px;
        min-height: 116px;
        box-shadow: 0 8px 22px rgba(16, 24, 32, 0.045);
    }
    .vc-card small {
        color: var(--vc-muted);
        font-size: 12px;
        font-weight: 850;
        text-transform: uppercase;
    }
    .vc-card strong {
        display: block;
        color: var(--vc-ink);
        font-size: 29px;
        line-height: 1.05;
        margin: 12px 0 7px;
    }
    .vc-card span { color: #2c3943; font-size: 15px; }
    .profit { border-left: 4px solid var(--vc-accent); }
    .loss { border-left: 4px solid var(--vc-red); }
    .source-pill {
        display: inline-block;
        background: var(--vc-panel);
        border: 1px solid var(--vc-line);
        border-radius: 999px;
        padding: 8px 12px;
        color: #33414c;
        font-size: 12px;
        font-weight: 800;
        max-width: 360px;
    }
    .section-title {
        color: var(--vc-ink);
        font-size: 23px;
        font-weight: 840;
        margin: 18px 0 10px;
    }
    .route-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin: 8px 0 24px;
    }
    .route-cell {
        background: var(--vc-panel);
        border: 1px solid var(--vc-line);
        border-radius: 8px;
        padding: 13px 15px;
    }
    .route-cell small {
        display: block;
        color: var(--vc-muted);
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .route-cell strong {
        color: #101820;
        font-size: 20px;
    }
    .mini-metric {
        background: var(--vc-panel);
        border: 1px solid var(--vc-line);
        border-radius: 8px;
        padding: 15px 16px;
        margin-bottom: 10px;
    }
    .mini-metric small {
        display: block;
        color: #69737c;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .mini-metric strong {
        display: block;
        color: #101820;
        font-size: 26px;
    }
    .mini-metric span { color: #69737c; }
    .bridge-wrap {
        background: var(--vc-panel);
        border: 1px solid var(--vc-line);
        border-radius: 8px;
        padding: 16px;
        margin-top: 8px;
    }
    .bridge-row {
        display: grid;
        grid-template-columns: 118px 1fr 112px;
        gap: 12px;
        align-items: center;
        min-height: 40px;
        border-bottom: 1px solid #edf1f3;
    }
    .bridge-row:last-child { border-bottom: 0; }
    .bridge-row span { color: #33414c; font-weight: 750; }
    .bridge-row strong { color: #101820; text-align: right; }
    .bar-track {
        height: 10px;
        background: #e8edf1;
        border-radius: 999px;
        overflow: hidden;
    }
    .bar-fill {
        height: 100%;
        border-radius: 999px;
        background: #1f8a70;
    }
    .bar-fill.cost { background: #c45a50; }
    .news-item { border-bottom: 1px solid var(--vc-line); padding: 10px 0; }
    .news-item strong { display: block; }
    .news-item span { color: var(--vc-muted); font-size: 13px; }
    @media (max-width: 900px) {
        .vc-header { grid-template-columns: 1fr; }
        .vc-title { font-size: 34px; }
        .route-grid { grid-template-columns: 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        "<div class='vc-brand'><small>Oil operations portal</small><strong>Voyage Commander</strong></div>",
        unsafe_allow_html=True,
    )
    incoterm = st.radio("Contract terms", ["FOB", "CIF", "DDP"], horizontal=True)
    st.caption(INCOTERMS[incoterm]["note"])

    st.divider()
    preset = st.selectbox("Voyage route", list(ROUTE_PRESETS.keys()))
    preset_origin, preset_destination = ROUTE_PRESETS[preset]
    port_names = list(PORTS.keys())

    if preset_origin:
        origin = preset_origin
        destination = preset_destination
        st.caption(f"{origin} → {destination}")
    else:
        origin = st.selectbox("Load port", port_names, index=port_names.index("Ras Tanura"))
        destination_options = [port for port in port_names if port != origin]
        default_destination = "Ningbo" if "Ningbo" in destination_options else destination_options[0]
        destination = st.selectbox(
            "Discharge port",
            destination_options,
            index=destination_options.index(default_destination),
        )

    st.divider()
    barrels = st.number_input("Cargo barrels", min_value=100_000, step=50_000, value=1_000_000)
    purchase = st.number_input("Purchase price / bbl", min_value=1.0, step=0.25, value=73.40)
    freight = st.number_input("Freight cost / bbl", min_value=0.0, step=0.05, value=2.80)
    insurance = st.number_input("Insurance cost / bbl", min_value=0.0, step=0.01, value=0.34)

    st.divider()
    berth_delay = st.slider("Waiting for berth", 0, 20, 5)
    canal_delay = st.slider("Canal / weather delay", 0, 20, 2)
    demurrage = st.number_input("Demurrage rate / day", min_value=0, step=1000, value=45_000)

prices = fetch_live_crude_prices()
sofr, sofr_source = fetch_sofr()
fx, fx_source = fetch_fx()
news = fetch_news()
distance_nm = estimate_distance_nm(origin, destination)
source_label = " · ".join(["yfinance fast_info", "offline route model", sofr_source, fx_source])

speed_knots = 14.5
water_days = distance_nm / (speed_knots * 24)
total_delay = berth_delay + canal_delay
active_costs = INCOTERMS[incoterm]["costs"]

market_value = barrels * prices["brent"]
purchase_value = barrels * purchase
gross_margin = market_value - purchase_value
freight_cost = freight * barrels if "freight" in active_costs else 0
insurance_cost = insurance * barrels if "insurance" in active_costs else 0
demurrage_cost = demurrage * total_delay if "discharge" in active_costs else 0
duties_cost = barrels * 0.42 * (fx / 7.18) if "duties" in active_costs else 0
inland_cost = barrels * 0.28 if "inland" in active_costs else 0
finance_cost = market_value * (sofr / 100 / 365) * (water_days + total_delay) if "finance" in active_costs else 0
net_profit = gross_margin - freight_cost - insurance_cost - demurrage_cost - finance_cost - duties_cost - inland_cost
margin_per_barrel = net_profit / barrels
three_day_loss = demurrage * 3 + market_value * (sofr / 100 / 365) * 3

top_left, top_right = st.columns([2.4, 1])
with top_left:
    route_title = f"{escape(origin)} to {escape(destination)} · VLCC crude voyage"
    st.markdown(
        f"""
        <div class="vc-header">
          <div>
            <div class="vc-kicker">Commercial defense mechanism</div>
            <h1 class="vc-title">{route_title}</h1>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top_right:
    st.write("")
    st.write("")
    st.markdown(f"<span class='source-pill'>Live: {source_label}</span>", unsafe_allow_html=True)

metric_cols = st.columns(4)
cards = [
    ("Live net profit", money(net_profit), f"{money2(margin_per_barrel)} / bbl", "profit" if net_profit >= 0 else "loss"),
    ("Market value", money(market_value), f"Brent {money2(prices['brent'])}", ""),
    ("Delay bleed", money(demurrage_cost + finance_cost), f"{total_delay} exposure days", ""),
    ("SOFR financing", money(finance_cost), f"SOFR {sofr:.2f}%", ""),
]

for col, (label, value, caption, cls) in zip(metric_cols, cards):
    with col:
        st.markdown(
            f"<div class='vc-card {cls}'><small>{label}</small><strong>{value}</strong><span>{caption}</span></div>",
            unsafe_allow_html=True,
        )

left, right = st.columns([1.45, 0.9])
with left:
    st.markdown("<div class='section-title'>Voyage monitor</div>", unsafe_allow_html=True)
    eta_risk = "Red" if total_delay > 10 else "Amber" if total_delay > 3 else "Green"
    route_items = [
        ("Load port", origin),
        ("Discharge port", destination),
        ("Nautical miles", f"{distance_nm:,} nm"),
        ("Days on water", f"{water_days:.1f}"),
        ("ETA risk", eta_risk),
        ("Contract term", incoterm),
        ("Load region", f"{PORTS[origin]['country']} · {PORTS[origin]['role']}"),
        ("Discharge region", f"{PORTS[destination]['country']} · {PORTS[destination]['role']}"),
    ]
    route_html = "".join(
        f"<div class='route-cell'><small>{escape(label)}</small><strong>{escape(value)}</strong></div>"
        for label, value in route_items
    )
    st.markdown(f"<div class='route-grid'>{route_html}</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>Margin bridge</div>", unsafe_allow_html=True)
    bridge = {
        "Gross margin": gross_margin,
        "Freight": -freight_cost,
        "Insurance": -insurance_cost,
        "Demurrage": -demurrage_cost,
        "SOFR carry": -finance_cost,
        "Duties": -duties_cost,
        "Inland": -inland_cost,
    }
    visible_bridge = {label: value for label, value in bridge.items() if abs(value) > 1}
    max_bridge = max([abs(value) for value in visible_bridge.values()] or [1])
    bridge_rows = []
    for label, value in visible_bridge.items():
        width = max(3, abs(value) / max_bridge * 100)
        cost_class = "cost" if value < 0 else ""
        bridge_rows.append(
            "<div class='bridge-row'>"
            f"<span>{escape(label)}</span>"
            f"<div class='bar-track'><div class='bar-fill {cost_class}' style='width:{width:.1f}%'></div></div>"
            f"<strong>{money(value)}</strong>"
            "</div>"
        )
    st.markdown(f"<div class='bridge-wrap'>{''.join(bridge_rows)}</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='section-title'>Market marks</div>", unsafe_allow_html=True)
    st.markdown(
        "".join(
            [
                f"<div class='mini-metric'><small>Brent BZ=F</small><strong>{money2(prices['brent'])}</strong><span>Front-month futures mark</span></div>",
                f"<div class='mini-metric'><small>WTI CL=F</small><strong>{money2(prices['wti'])}</strong><span>Front-month futures mark</span></div>",
                f"<div class='mini-metric'><small>USD/CNY</small><strong>{fx:.4f}</strong><span>FX for landed-cost translation</span></div>",
            ]
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-title'>Three more days stuck?</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='mini-metric'><small>Incremental impact</small><strong>{money(three_day_loss)}</strong><span>Berth delay, demurrage, and capital drag.</span></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-title'>Geopolitical sidebar</div>", unsafe_allow_html=True)
    for item in news:
        st.markdown(
            f"<div class='news-item'><strong>{item['title']}</strong><span>{item['source']} · {item['description']}</span></div>",
            unsafe_allow_html=True,
        )
