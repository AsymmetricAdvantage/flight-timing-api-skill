# Flight Timing API Skill

**Find the cheapest time to fly, any route. A free tool by [Fuji Daily](https://fujidaily.com), in partnership with Travelpayouts.**

Ask your AI agent when flights are cheapest and get a real answer with a link to
see live prices. No signup, no API key, no cost.

```
You:    When's the cheapest time to fly from New York to Tokyo?
Agent:  Cached fares for JFK to TYO put the cheapest month at December 2026,
        $617 on Singapore Airlines non-stop, with October next at $631.
        The cheapest single day in November is the 3rd, at $379.
        Those are recent fares, per adult in economy, not bookable prices.
        See what it costs today: https://travel.fujidaily.com/?flightSearch=...
```

It works for any origin and destination. Japan is where the publisher's
expertise sits, not a limit on the tool.

## What it does

It answers the flight questions that actually have data behind them:

- **When** is it cheapest to fly a route, by month?
- **Which day** in a month is cheapest?
- **Would shifting** my dates by a day or two be cheaper?
- **Where** can I go cheap from here, and for how much?
- **What's under $400**, or which routes are non-stop and cheap?

Every answer about a specific route can end with a handoff to live prices on
[travel.fujidaily.com](https://travel.fujidaily.com), where the same search runs
across 100+ booking engines. That is the part that turns a cached fare into a
bookable one.

## What it does not do, said plainly

Fare data comes from the Aviasales flight data API, reached through the
Travelpayouts partnership. It is a **cache of other people's recent searches**,
refreshed about every 7 days. It is not a live price feed and it cannot book.

That single fact shapes the whole design. Measured against the live API on US to
Japan routes:

| Question | Endpoint | Calls that returned data |
| --- | --- | --- |
| Cheapest day in a month | `/v2/prices/month-matrix` | **24 / 24** |
| Cheapest fare per month | `/v1/prices/monthly` | 10 / 10 months |
| Cheapest day, ~50-day window | `/v1/prices/calendar` | 51 rows |
| Where can I go cheap | `/v1/prices/cheap` (`destination=-`) | 438 destinations |
| **A specific date, one-way** | `/aviasales/v3/prices_for_dates` | **3 / 24** calls, 1 row each |
| **A specific date, round trip** | `/aviasales/v3/prices_for_dates` | **0 rows** |

So this is a trip-timing and inspiration tool. It will tell you that New York to
Tokyo is cheapest on 3 November at $379, and that Atlanta is $170 from New York
this week. It will not reliably price an arbitrary future date, and it does not
pretend to. When the cache is empty it says so and offers the live search rather
than inventing a number.

## Install

The skill is a plain folder using the open [Agent Skills](https://agentskills.io)
format, so one copy works across agents. Only the destination path differs.

| Agent | Destination |
| --- | --- |
| **Hermes Agent** | `~/.hermes/skills/travel/flight-timing-api-skill/` |
| **Claude Code** | `~/.claude/skills/flight-timing-api-skill/` |
| **OpenAI Codex** | `$CODEX_HOME/skills/flight-timing-api-skill/` |
| **Grok** | `~/.agents/skills/flight-timing-api-skill/` |
| **OpenClaw** | `~/.agents/skills/flight-timing-api-skill/` |
| **Muse Code** | `~/.claude/skills/flight-timing-api-skill/` or `$CODEX_HOME/skills/` |
| **ChatGPT / dots** | install as a skill or plugin in ChatGPT |

Copy the `plugins/flight-timing-api-skill/` folder and keep the folder name,
since the skill's `name` must match its parent directory.

Three shared roots mean one copy can serve several agents: `~/.agents/skills/` is
read by OpenClaw and Grok, `~/.claude/skills/` by Claude Code, Grok and Muse
Code, and `$CODEX_HOME/skills/` by Codex and Muse Code.

### Claude Code and Grok marketplace

This repository is also a plugin marketplace, which Grok consumes because it is
Claude Code compatible:

```
claude plugin marketplace add asymmetricadvantage/flight-timing-api-skill
claude plugin install flight-timing-api-skill@fuji-daily
```

## Use it

Just ask, in your own words:

- "When's the cheapest time to fly from Boston to Osaka?"
- "What's the cheapest day in November to fly JFK to Tokyo?"
- "Where can I fly cheap from Los Angeles this winter?"
- "Any non-stop flights under $400 from Chicago?"

The agent resolves the city to an airport code, picks the right query, quotes the
cached fare with its caveat, and offers live prices.

You can also run it by hand. It is one stdlib-only Python file:

```bash
cd plugins/flight-timing-api-skill
python3 scripts/tpapi.py resolve Osaka
python3 scripts/tpapi.py months JFK TYO
python3 scripts/tpapi.py days JFK TYO --month 2026-11
python3 scripts/tpapi.py cheap JFK --max 400
python3 scripts/tpapi.py link JFK TYO --depart 2026-11-30
```

## Why it is free

[Fuji Daily](https://fujidaily.com) is a Japan-focused travel publisher. The fares
come from Aviasales, the flight data provider behind the search, and Fuji Daily
reaches it through its Travelpayouts partnership. Between them, this tool
searches **100+ booking engines** at once and compares the results.

Using the skill is free. When someone books through the handoff link to
[travel.fujidaily.com](https://travel.fujidaily.com), Fuji Daily earns a small
referral commission from the booking site. It costs the traveler nothing extra,
it does not change the price shown, and searching or comparing costs nothing at
all. That commission is what pays for the tool and for the publisher's travel
coverage.

Prices shown are cached fares, per adult, in economy class. Always confirm the
final price on the booking site.

## If you fork this and build on it

Two things are required once this runs in front of anyone but yourself. They are
what keep the fare data free.

**Add an affiliate disclaimer wherever the links appear.** Every link to
travel.fujidaily.com is a tracked affiliate link. A customer-facing app, site, or
bot built on this skill has to tell its users that bookings made through those
links earn a commission, and that it costs them nothing extra. In most places
that is a legal requirement as well as an honest one, and a line buried in a
terms page does not count as disclosure.

**Keep the marker on the links.** The links carry `marker=181116`. That marker is
the whole funding mechanism: it credits the booking and pays for the fare data.
Keep it on every link the skill emits. Remove it, swap it for a different one, or
rewrite it in a proxy and the commission stops arriving, and that commission is
the only reason this API stays free for everyone, you included. You do not need
to touch it for your own reporting either. Set `TPWL_SUBID` to your own value and
the marker stays intact while your traffic remains separable in the stats.

Everything else here is MIT. Fork it, translate it, restyle the output, change
the country defaults.

## Under the hood

One stdlib-only Python CLI, `plugins/flight-timing-api-skill/scripts/tpapi.py`,
over the endpoints that measurably return data, plus a keyless airport and city
lookup so the agent never has to guess an IATA code. It deliberately does not use
the API's real-time search, which requires per-site approval and forbids
automated link collection; the reasoning is documented in the skill.

Endpoint-by-endpoint measurements, including the dead ones:
[`plugins/flight-timing-api-skill/references/endpoints.md`](plugins/flight-timing-api-skill/references/endpoints.md).
Per-agent install detail and verification:
[`plugins/flight-timing-api-skill/references/clients.md`](plugins/flight-timing-api-skill/references/clients.md).

## License

MIT. Fork it, ship it, translate it.

---

*Built by [Name Radiance](https://nameradiance.com) for [Fuji Daily](https://fujidaily.com). Fare data by Aviasales, reached via Travelpayouts. Booking links by Travelpayouts.*
