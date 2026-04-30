import json
import os
import ssl
from urllib.parse import urlencode
from urllib.request import urlopen

import streamlit as st

from market_data import fetch_live_crude_prices
from route_distances import estimate_distance_nm


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
    .stApp { background: #edf1f3; color: #101820; }
    [data-testid="stSidebar"] { background: #111a21; }
    [data-testid="stSidebar"] * { color: #f5f7f8; }
    .vc-card {
        background: white;
        border: 1px solid #d8dee3;
        border-radius: 8px;
        padding: 18px;
        min-height: 125px;
        box-shadow: 0 10px 28px rgba(16, 24, 32, 0.06);
    }
    .vc-card small { color: #69737c; font-weight: 800; text-transform: uppercase; }
    .vc-card strong { display: block; font-size: 30px; margin: 8px 0 4px; }
    .profit { border-left: 5px solid #0d7c66; }
    .loss { border-left: 5px solid #b3261e; }
    .source-pill {
        display: inline-block;
        background: white;
        border: 1px solid #d8dee3;
        border-radius: 999px;
        padding: 7px 12px;
        color: #33414c;
        font-size: 12px;
        font-weight: 800;
    }
    .news-item { border-bottom: 1px solid #d8dee3; padding: 10px 0; }
    .news-item strong { display: block; }
    .news-item span { color: #69737c; font-size: 13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Voyage Commander")
    st.caption("Oil operations portal")
    incoterm = st.radio("Contract terms", ["FOB", "CIF", "DDP"], horizontal=True)
    st.caption(INCOTERMS[incoterm]["note"])

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
distance_nm = estimate_distance_nm("Ras Tanura", "Ningbo")
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

st.markdown("### Commercial defense mechanism")
top_left, top_right = st.columns([2.4, 1])
with top_left:
    st.title("Ras Tanura to Ningbo · VLCC crude voyage")
with top_right:
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
    st.subheader("Voyage monitor")
    route = {
        "Load port": "Ras Tanura",
        "Discharge port": "Ningbo",
        "Nautical miles": f"{distance_nm:,} nm",
        "Days on water": f"{water_days:.1f}",
        "ETA risk": "Red" if total_delay > 10 else "Amber" if total_delay > 3 else "Green",
    }
    st.table(route)

    st.subheader("Margin bridge")
    bridge = {
        "Gross margin": gross_margin,
        "Freight": -freight_cost,
        "Insurance": -insurance_cost,
        "Demurrage": -demurrage_cost,
        "SOFR carry": -finance_cost,
        "Duties": -duties_cost,
        "Inland": -inland_cost,
    }
    st.bar_chart({k: v for k, v in bridge.items() if abs(v) > 1})

with right:
    st.subheader("Market marks")
    st.metric("Brent BZ=F", money2(prices["brent"]))
    st.metric("WTI CL=F", money2(prices["wti"]))
    st.metric("USD/CNY", f"{fx:.4f}")

    st.subheader("Three more days stuck?")
    st.metric("Incremental impact", money(three_day_loss))
    st.caption("Berth delay, demurrage, and capital drag.")

    st.subheader("Geopolitical sidebar")
    for item in news:
        st.markdown(
            f"<div class='news-item'><strong>{item['title']}</strong><span>{item['source']} · {item['description']}</span></div>",
            unsafe_allow_html=True,
        )
