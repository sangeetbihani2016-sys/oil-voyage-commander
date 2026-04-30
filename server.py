from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import ssl
import time
from urllib.parse import urlencode
from urllib.request import urlopen

from route_distances import all_route_distances, estimate_distance_nm


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env_file()

FALLBACK_MARKET = {
    "brent": 82.34,
    "wti": 78.12,
    "sofr": 5.31,
    "fx": 7.18,
    "distanceNm": 6355,
    "source": "Fallback marks",
}

FALLBACK_NEWS = {
    "articles": [
        {
            "title": "Port congestion watch: China discharge windows tighten",
            "source": "Operations desk fallback",
            "url": "#",
            "description": "Ningbo anchorage delays remain the highest sensitivity in this voyage model.",
        },
        {
            "title": "Canal transit delays lift prompt freight premiums",
            "source": "Freight risk fallback",
            "url": "#",
            "description": "Chokepoint uncertainty increases the value of fast operational intervention.",
        },
        {
            "title": "OPEC supply signals keep crude flat while SOFR drag persists",
            "source": "Market context fallback",
            "url": "#",
            "description": "Stable flat price can still hide margin erosion from financing and demurrage.",
        },
    ]
}


def get_json(url, timeout=4):
    context = None
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass

    with urlopen(url, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def yfinance_price(symbol):
    import yfinance as yf

    return float(yf.Ticker(symbol).fast_info["last_price"])


def yahoo_price(symbol):
    payload = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}")
    result = payload["chart"]["result"][0]
    return float(result["meta"]["regularMarketPrice"])


def fred_sofr():
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return None
    params = urlencode(
        {
            "series_id": "SOFR",
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
    )
    payload = get_json(f"https://api.stlouisfed.org/fred/series/observations?{params}")
    return float(payload["observations"][0]["value"])


def exchange_rate():
    api_key = os.getenv("EXCHANGERATE_API_KEY")
    if api_key:
        keyed_attempts = []
        if api_key.startswith("fxr_"):
            keyed_attempts.extend(
                [
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
                    (
                        "https://fxratesapi.com/latest?"
                        + urlencode({"apikey": api_key, "base": "USD", "symbols": "CNY"}),
                        lambda payload: float(payload["rates"]["CNY"]),
                    ),
                ]
            )
        else:
            keyed_attempts.append(
                (
                    f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD",
                    lambda payload: float(payload["conversion_rates"]["CNY"]),
                )
            )

        for url, parser in keyed_attempts:
            try:
                return parser(get_json(url))
            except Exception:
                pass

    payload = get_json("https://open.er-api.com/v6/latest/USD")
    return float(payload["rates"]["CNY"])


def live_market():
    data = FALLBACK_MARKET.copy()
    source_bits = []
    try:
        data["brent"] = round(yfinance_price("BZ=F"), 2)
        data["wti"] = round(yfinance_price("CL=F"), 2)
        source_bits.append("yfinance fast_info")
    except Exception:
        try:
            data["brent"] = round(yahoo_price("BZ=F"), 2)
            data["wti"] = round(yahoo_price("CL=F"), 2)
            source_bits.append("Yahoo futures")
        except Exception:
            pass

    try:
        data["distanceNm"] = estimate_distance_nm("Ras Tanura", "Ningbo")
        source_bits.append("offline route model")
    except Exception:
        pass

    try:
        sofr = fred_sofr()
        if sofr is not None:
            data["sofr"] = sofr
            source_bits.append("FRED SOFR")
    except Exception:
        pass

    try:
        data["fx"] = exchange_rate()
        source_bits.append("FX")
    except Exception:
        pass

    data["source"] = " · ".join(source_bits) if source_bits else "Fallback marks"
    return data


def live_news():
    api_key = os.getenv("NEWS_API_KEY")
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
    except Exception:
        return FALLBACK_NEWS

    articles = []
    for item in payload.get("articles", [])[:5]:
        articles.append(
            {
                "title": item.get("title") or "Market context update",
                "source": (item.get("source") or {}).get("name") or "NewsAPI",
                "url": item.get("url") or "#",
                "description": item.get("description") or "",
            }
        )
    return {"articles": articles or FALLBACK_NEWS["articles"]}


class Handler(SimpleHTTPRequestHandler):
    def send_payload(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/market":
            self.send_payload(live_market())
            return
        if self.path == "/api/news":
            self.send_payload(live_news())
            return
        if self.path == "/api/routes":
            self.send_payload({"routes": all_route_distances()})
            return
        if self.path == "/api/health":
            self.send_payload({"ok": True, "time": int(time.time())})
            return
        super().do_GET()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "4173"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Voyage Commander running at http://127.0.0.1:{port}")
    server.serve_forever()
