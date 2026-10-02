# Aviasales endpoints, via Travelpayouts: what actually returns data

The data, the endpoints, and the search engine behind them are Aviasales'.
Travelpayouts is the affiliate layer and the host that serves them to a partner.

Every line below was run against the live API with partner `181116` on
2026-10-01. "Hit rate" is the fraction of calls that returned any rows, which is
the number that decides whether an agent tool is useful or just noise.

Base: `https://api.travelpayouts.com` (the Aviasales data API as served through
Travelpayouts)
Auth: `X-Access-Token` header **or** `?token=`. Both work.
Rate limit, read from the response headers: **600 per window**
(`X-Rate-Limit: 600`, `X-Rate-Limit-Remaining`, `X-Rate-Limit-Reset`).
Reference datasets need **no token at all**.

## Coverage reality (US → Japan, market=us)

| Shape of question | Endpoint | Result |
| --- | --- | --- |
| Cheapest fare per month | `/v1/prices/monthly` | 10/10 months returned |
| Cheapest day in a month | `/v2/prices/month-matrix` | **24/24** calls non-empty |
| Cheapest day in a month (newer) | `/aviasales/v3/grouped_prices` | 15/24 |
| Cheapest day, ~50-day window | `/v1/prices/calendar` | 51 rows for JFK→TYO |
| Where can I go cheap | `/v1/prices/cheap` (`destination=-`) | 438 destinations for JFK |
| Popular destinations from a city | `/v1/city-directions` | 30 rows |
| Hand-picked deals | `/aviasales/v3/get_special_offers` | 9 rows |
| **A specific date, one-way** | `/aviasales/v3/prices_for_dates` | **3/24** calls, 1 row each |
| **A specific date, round trip** | `/aviasales/v3/prices_for_dates` | **0 rows** |

Read that bottom pair twice. The endpoint that looks like "search a flight" is
the one that is empty almost every time on long-haul. The endpoints that answer
"when and where is it cheap" are the ones with real coverage. A usable skill is
built on the second group and hands off to the white label for the first.

## Working endpoints

| Endpoint | Returns | Notes |
| --- | --- | --- |
| `/aviasales/v3/prices_for_dates` | list | per-date fares; carries `link`. Thin on long-haul |
| `/aviasales/v3/grouped_prices` | dict keyed by date | per-day cheapest for a month, each with `link` |
| `/v2/prices/month-matrix` | list | per-day for a month; best coverage |
| `/v1/prices/calendar` | dict keyed by date | ~50-day window from `depart_date` |
| `/v1/prices/monthly` | dict keyed by `YYYY-MM` | cheapest per month, 10 months out |
| `/v1/prices/cheap` | dict keyed by dest | `destination=-` = anywhere, 438 results |
| `/v1/prices/direct` | dict keyed by dest | non-stop only |
| `/v2/prices/latest` | list | most recent fares found |
| `/v1/city-directions` | dict keyed by dest | inspiration search |
| `/aviasales/v3/get_special_offers` | list | carries `link` |

## Endpoints that are gone or empty

| Endpoint | Status |
| --- | --- |
| `/v1/airlines/directions` | **404**, removed |
| `/v2/ip` | **404**, removed |
| `/v2/prices/week-matrix` | alive but returned 0 rows; needs both date ranges |
| `/v2/prices/nearest-places-matrix` | alive but returned empty |
| `engine.hotellook.com/api/v2/*` | **404**, retired. Hotels is a separate program |
| `api.travelpayouts.com/hotels/*` | **404** |

## Real-time Flights Search API: not usable for a public skill

A separate section of the docs covers a genuinely live search
(`POST /v1/flight_search` with an MD5 signature, then poll the results). It is
excluded here for hard reasons, not preference:

- Requires **application and approval** per website (URL, prototypes,
  justification for why the White Label and data API are insufficient).
- Every search must be **user-initiated**, results shown in full, each row with
  a "buy" button, and links only revealed on click.
- **Automatic collection of links is prohibited** and forfeits access.
- No `localhost` IPs; must be called server-side, not from AJAX.
- Mailed conversion targets: **9%** search-to-buy-link, **5%** buy-to-purchase.
- 200 queries/hour/IP.

An agent skill that fires searches on a model's initiative and harvests links
breaks almost every one of these. Do not build it on that API.

## Reference data (no token)

`https://api.travelpayouts.com/data/en/{cities,airports,airlines,countries}.json`

All four return 200 without a token. This is the plumbing that makes a flight
tool actually usable: it lets the model resolve "Tokyo" to `TYO` instead of
inventing a code. Worth shipping even if nothing else works.

## Two things that surprise people

1. **The API's `link` is relative**, e.g. `/search/JFK1511TYO1?t=PR...`. Prefixed
   with `https://travel.fujidaily.com` it **302s** to
   `/?flightSearch=JFK1511TYO1&t=...` and runs the search, reopening the exact
   fare at the quoted price. Prefixed with `https://www.aviasales.com` it serves
   a 200 directly. Either way the relative link is a real, working deep link.
2. **A bare `?origin=X&destination=Y` white-label link does not search.** It
   prefills the form and stops. Only the `origin_iata`/`destination_iata` +
   `with_request=true` form, or the `?flightSearch=<ORIGIN><DDMM><DEST><pax>`
   code, actually runs a query. A tool that emits the first form looks fine and
   converts nothing.
