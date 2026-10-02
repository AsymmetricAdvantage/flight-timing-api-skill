#!/usr/bin/env python3
"""Aviasales flight-data helpers, reached through Travelpayouts.

Zero dependencies (stdlib only), so an agent can drop it in anywhere.

Every endpoint here was exercised against the live API before being exposed.
Endpoints that look useful but return nothing for real routes are deliberately
absent or flagged; see references/endpoints.md for the measured hit rates.

Honest contract, inherited from the API itself:
  * The Aviasales Flight Data API is a CACHE of other people's recent searches, not a
    live price engine. Data is kept about 7 days and each row carries
    `expires_at`. Treat prices as "recently seen", never as "bookable now".
  * Prices are per adult, economy, in the requested currency, for the market
    given by `market` (default `us`).
  * You cannot book. Every answer must hand the user a tracked link.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------- config

API_TOKEN = os.environ.get("TPWL_TOKEN", "8e12db1a1a189d528cdb52f4d26bf38e")
PARTNER_ID = os.environ.get("TPWL_MARKER", "181116")
SUBID = os.environ.get("TPWL_SUBID", "agent-skill")

BASE = "https://api.travelpayouts.com"
REF_DATA = f"{BASE}/data/en"

# White-label engine. A relative /search/... link from the API resolves here.
WL_HOST = os.environ.get("TPWL_WL_HOST", "https://travel.fujidaily.com")
UA = "flight-timing-api-skill/2.2.0 (+https://github.com/AsymmetricAdvantage/flight-timing-api-skill)"

CACHE_DIR = pathlib.Path(os.environ.get("TPWL_CACHE", pathlib.Path(__file__).resolve().parent.parent / ".cache"))
REF_MAX_AGE = 86400  # seconds


class TPError(RuntimeError):
    """Raised when the API returns a failure or unparseable payload."""


# ---------------------------------------------------------------- http

def _http_json(url: str, headers: dict | None = None, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:300].decode("utf-8", "replace")
        raise TPError(f"HTTP {exc.code} for {url}: {detail}") from None
    except Exception as exc:  # noqa: BLE001
        raise TPError(f"{type(exc).__name__} for {url}: {exc}") from None


def api(path: str, **params):
    """Call a Flight Data API endpoint. Returns the `data` value.

    Raises TPError on a real failure, and returns None/[] on an empty-but-ok
    response, so callers can tell "nothing cached" from "request broke".
    """
    params = {k: v for k, v in params.items() if v is not None}
    params.setdefault("currency", "usd")
    query = urllib.parse.urlencode({**params, "token": API_TOKEN})
    payload = _http_json(f"{BASE}{path}?{query}", {"X-Access-Token": API_TOKEN})
    if not payload.get("success"):
        raise TPError(f"{path}: {payload.get('error') or 'unknown error'}")
    return payload.get("data")


def ref(kind: str) -> list:
    """Reference dataset: cities, airports, airlines, countries. No token needed."""
    if kind not in {"cities", "airports", "airlines", "countries"}:
        raise ValueError("kind must be cities|airports|airlines|countries")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{kind}.json"
    fresh = path.exists() and (datetime_now() - path.stat().st_mtime) < REF_MAX_AGE
    if not fresh:
        path.write_text(json.dumps(_http_json(f"{REF_DATA}/{kind}.json"), ensure_ascii=False))
    return json.loads(path.read_text())


def datetime_now() -> float:
    return _dt.datetime.now(_dt.timezone.utc).timestamp()


# ---------------------------------------------------------------- links
# Two link shapes are verified to run a search on the white label. A bare
# ?origin=&destination= pair does NOT: it prefills the form and nothing else.

def deep_link(origin: str, destination: str, depart_date: str,
              return_date: str | None = None, pax: int = 1,
              currency: str = "usd", subid: str | None = SUBID) -> str:
    """White-label deep link that actually fires a search."""
    query = {
        "depart_date": depart_date,
        "return_date": return_date or "",
        "origin_iata": origin.upper(),
        "destination_iata": destination.upper(),
        "currency": currency,
        "language": "EN",
        "with_request": "true",
        "locale": "EN",
    }
    if pax and pax > 1:
        query["adults"] = pax
    marker = PARTNER_ID + (f".{subid}" if subid else "")
    query["marker"] = marker
    return f"{WL_HOST}/?{urllib.parse.urlencode(query)}"


def flight_search_link(origin: str, destination: str, depart_date: str,
                       pax: int = 1, subid: str | None = SUBID) -> str:
    """Compact form TPWL's embed script parses: <ORIGIN><DDMM><DEST><pax>."""
    d = _dt.date.fromisoformat(depart_date)
    code = f"{origin.upper()}{d.day:02d}{d.month:02d}{destination.upper()}{pax}"
    marker = PARTNER_ID + (f".{subid}" if subid else "")
    return f"{WL_HOST}/?flightSearch={code}&marker={marker}"


def book_link(api_link: str | None, subid: str | None = SUBID) -> str | None:
    """Turn the API's relative /search/... link into a tracked absolute URL.

    That path 302s onto the white label as ?flightSearch=... and keeps the
    price-lock token, so it reopens the exact fare at the price quoted.
    """
    if not api_link:
        return None
    abs_url = api_link if api_link.startswith("http") else WL_HOST.rstrip("/") + api_link
    marker = PARTNER_ID + (f".{subid}" if subid else "")
    sep = "&" if "?" in abs_url else "?"
    if "marker=" not in abs_url:
        abs_url = f"{abs_url}{sep}marker={marker}"
    return abs_url


def white_label_home(subid: str | None = SUBID) -> str:
    """Marker-stamped link to the search engine root, for when no route is known yet."""
    marker = PARTNER_ID + (f".{subid}" if subid else "")
    return f"{WL_HOST.rstrip('/')}/?marker={marker}"


# ---------------------------------------------------------------- flight data

def search_dates(origin, destination, departure_at, return_at=None, one_way=True,
                 direct=False, currency="usd", market="us", limit=30, **kw):
    """Fares for one date (or month). THIN COVERAGE on many long-haul routes."""
    params = {
        "origin": origin.upper(), "destination": destination.upper(),
        "departure_at": departure_at, "return_at": return_at if not one_way else None,
        "one_way": "true" if one_way else "false",
        "direct": "true" if direct else "false",
        "currency": currency, "market": market, "limit": limit,
        "sorting": "price", **kw,
    }
    return api("/aviasales/v3/prices_for_dates", **params) or []


def cheapest_days(origin, destination, month, currency="usd", market="us"):
    """Cheapest fare per day of a month, each with its own booking link."""
    data = api("/aviasales/v3/grouped_prices", origin=origin.upper(),
               destination=destination.upper(), departure_at=month,
               currency=currency, market=market) or {}
    return sorted(({"date": k, **v} for k, v in data.items()),
                  key=lambda r: r.get("price") or 10**9)


def monthly_matrix(origin, destination, month, currency="usd", market="us"):
    """Broader month view than cheapest_days (older endpoint, still alive)."""
    return api("/v2/prices/month-matrix", origin=origin.upper(),
               destination=destination.upper(), departure_at=month,
               currency=currency, market=market, show_to_affiliates="true") or []


def price_calendar(origin, destination, depart_date, currency="usd", market="us"):
    """~50 days of fares from a start date. Good for 'is a day either side cheaper'."""
    data = api("/v1/prices/calendar", origin=origin.upper(),
               destination=destination.upper(), depart_date=depart_date,
               currency=currency, market=market, calendar_type="departure_date") or {}
    return sorted(({"date": k, **v} for k, v in data.items()),
                  key=lambda r: r.get("price") or 10**9)


def cheapest_months(origin, destination, currency="usd", market="us"):
    """Cheapest fare per month for a route. Best-coverage endpoint available."""
    data = api("/v1/prices/monthly", origin=origin.upper(),
               destination=destination.upper(), currency=currency, market=market) or {}
    return sorted(({"month": k, **v} for k, v in data.items()),
                  key=lambda r: r.get("price") or 10**9)


def cheapest_routes(origin, destination=None, currency="usd", market="us", limit=None):
    """Cheapest fares from an origin. destination='-' or None means anywhere."""
    data = api("/v1/prices/cheap", origin=origin.upper(),
               destination=destination.upper() if destination else "-",
               currency=currency, market=market) or {}
    out = []
    for dest_code, options in data.items():
        ranked = sorted(options.items(), key=lambda kv: kv[1].get("price") or 10**9)
        if ranked:
            out.append({"destination": dest_code, **ranked[0][1]})
    out.sort(key=lambda r: r.get("price") or 10**9)
    return out[: (limit or len(out))]


def nonstop(origin, destination, currency="usd", market="us"):
    """Cheapest non-stop only (same shape as cheapest_routes)."""
    data = api("/v1/prices/direct", origin=origin.upper(),
               destination=destination.upper(), currency=currency, market=market) or {}
    out = []
    for dest_code, options in data.items():
        ranked = sorted(options.items(), key=lambda kv: kv[1].get("price") or 10**9)
        if ranked:
            out.append({"destination": dest_code, **ranked[0][1]})
    return out


def latest_fares(origin=None, destination=None, limit=30, currency="usd", market="us"):
    """Most recently found fares, optionally filtered by route."""
    return api("/v2/prices/latest", origin=origin.upper() if origin else None,
               destination=destination.upper() if destination else None,
               limit=limit, currency=currency, market=market,
               show_to_affiliates="true", sorting="price") or []


def city_directions(origin, currency="usd", market="us"):
    """Popular destinations from a city, cheapest first (inspiration search)."""
    data = api("/v1/city-directions", origin=origin.upper(),
               currency=currency, market=market) or {}
    return sorted(({"destination": k, **v} for k, v in data.items()),
                  key=lambda r: r.get("price") or 10**9)


def special_offers(origin=None, destination=None, currency="usd", market="us"):
    """Hand-picked deals. Each row carries its own booking link."""
    params = {"currency": currency, "market": market, "locale": "en"}
    if origin:
        params["origin"] = origin.upper()
    if destination:
        params["destination"] = destination.upper()
    return api("/aviasales/v3/get_special_offers", **params) or []


# ---------------------------------------------------------------- resolve

def resolve_city(query: str, limit: int = 5) -> list[dict]:
    """Turn 'Tokyo' or 'tokyo' into IATA codes, so a model never has to guess."""
    q = (query or "").strip().lower()
    if not q:
        return []
    hits = []
    for c in ref("cities"):
        code = (c.get("code") or "").upper()
        name = (c.get("name") or "")
        english = (c.get("name_translations") or {}).get("en") or ""
        if q == code.lower() or q == english.lower() or q == name.lower():
            hits.append({"code": code, "name": english or name,
                         "country": c.get("country_code"), "match": "exact"})
    if not hits:
        for c in ref("cities"):
            english = ((c.get("name_translations") or {}).get("en") or c.get("name") or "")
            if q in english.lower():
                hits.append({"code": (c.get("code") or "").upper(), "name": english,
                             "country": c.get("country_code"), "match": "partial"})
    return hits[:limit]


# ---------------------------------------------------------------- CLI

def _print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def main() -> int:
    p = argparse.ArgumentParser(description="Flight timing: cheapest time to fly (cached fares).")
    p.add_argument("--market", default="us",
                   help="which country's price cache to read, e.g. us, gb, de (default us)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def route(sp):
        """Origin required, destination optional (omit for 'anywhere')."""
        sp.add_argument("origin")
        sp.add_argument("destination", nargs="?", default=None)

    def route2(sp):
        """Both origin and destination required."""
        sp.add_argument("origin")
        sp.add_argument("destination")

    s = sub.add_parser("dates"); route(s)
    s.add_argument("--depart", required=True); s.add_argument("--return", dest="ret")
    s.add_argument("--round", action="store_true")

    s = sub.add_parser("days"); route2(s); s.add_argument("--month", required=True)
    s = sub.add_parser("months"); route2(s)
    s = sub.add_parser("calendar"); route2(s); s.add_argument("--depart", required=True)
    s = sub.add_parser("cheap"); route(s)
    s.add_argument("--limit", type=int, default=15)
    s.add_argument("--max", type=float, dest="max_price", default=None,
                   help="keep only fares at or below this price")
    s = sub.add_parser("direct"); route2(s); s.add_argument("--limit", type=int, default=15)
    s = sub.add_parser("latest"); route(s); s.add_argument("--limit", type=int, default=15)
    s = sub.add_parser("inspire"); s.add_argument("origin")
    s = sub.add_parser("offers")
    s.add_argument("origin", nargs="?", default=None)
    s.add_argument("destination", nargs="?", default=None)
    s = sub.add_parser("resolve"); s.add_argument("query")
    s = sub.add_parser("link"); route2(s); s.add_argument("--depart", required=True)
    s.add_argument("--pax", type=int, default=1)

    a = p.parse_args()
    market = a.market

    if a.cmd == "dates":
        rows = search_dates(a.origin, a.destination, a.depart, a.ret,
                            one_way=not a.round, market=market)
    elif a.cmd == "days":
        rows = cheapest_days(a.origin, a.destination, a.month, market=market)
    elif a.cmd == "months":
        rows = cheapest_months(a.origin, a.destination, market=market)
    elif a.cmd == "calendar":
        rows = price_calendar(a.origin, a.destination, a.depart, market=market)
    elif a.cmd == "cheap":
        rows = cheapest_routes(a.origin, a.destination, market=market)
        if a.max_price is not None:
            rows = [r for r in rows if (r.get("price") or 10**9) <= a.max_price]
        rows = rows[: a.limit]
    elif a.cmd == "direct":
        rows = nonstop(a.origin, a.destination, market=market)[: a.limit]
    elif a.cmd == "latest":
        rows = latest_fares(a.origin, a.destination, limit=a.limit, market=market)
    elif a.cmd == "inspire":
        rows = city_directions(a.origin, market=market)[:15]
    elif a.cmd == "offers":
        rows = special_offers(a.origin, a.destination, market=market)
    elif a.cmd == "resolve":
        _print(resolve_city(a.query)); return 0
    elif a.cmd == "link":
        _print({"deep_link": deep_link(a.origin, a.destination, a.depart, pax=a.pax),
                "flight_search": flight_search_link(a.origin, a.destination, a.depart, pax=a.pax)})
        return 0
    else:
        return 2

    if not rows:
        origin = (getattr(a, "origin", None) or "").upper()
        destination = (getattr(a, "destination", None) or "").upper()
        note = {"note": "Nothing cached for this query. Hand the user the link instead."}
        if origin and destination:
            note["fallback_link"] = deep_link(
                origin, destination,
                getattr(a, "depart", None) or _dt.date.today().isoformat())
        else:
            note["fallback_link"] = white_label_home()
        _print(note)
        return 0
    _print(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
