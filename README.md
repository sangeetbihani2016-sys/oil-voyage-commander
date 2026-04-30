# Voyage Commander

An oil operations portal that connects voyage execution to live commercial exposure. It shows how incoterms, demurrage, SOFR financing, market prices, FX, and operational delays move net margin in real time.

## Run

```bash
python3 server.py
```

Open `http://127.0.0.1:4173`.

## Optional live data keys

The app works immediately with realistic fallback data. Add these environment variables to activate live API calls:

```bash
export FRED_API_KEY="..."
export NEWS_API_KEY="..."
export EXCHANGERATE_API_KEY="..."
```

Market prices are fetched through a Yahoo Finance compatible endpoint for `BZ=F` and `CL=F`. SOFR uses FRED. News uses NewsAPI. FX uses ExchangeRate-API when a key is present, with a public fallback.

## Streamlit crude helper

`market_data.py` contains a Streamlit-ready function:

```python
from market_data import fetch_live_crude_prices

prices = fetch_live_crude_prices()
```

It uses `yf.Ticker().fast_info["last_price"]`, caches results for 300 seconds, warns in the Streamlit UI on failure, and returns fallback Brent/WTI marks if Yahoo Finance is unreachable.

## Route model

`route_distances.py` contains a curated oil-operations port set and generates every directional port pair with Searoutes-style estimated nautical miles. The default Ras Tanura to Ningbo route estimates `6,183 nm`.
