# AGENTS.md

This repository ships **flight-timing-api-skill**, a free skill for finding the
cheapest time to fly any route. It is provided by Fuji Daily
(https://fujidaily.com), a Japan-focused travel publisher, in partnership with
Travelpayouts. The fares and the 100+ booking engine search come from Aviasales,
the flight data provider. It is free because Fuji Daily earns a commission on
bookings made through the handoff link, at no extra cost to the traveler. Live search: https://travel.fujidaily.com. Built by Name
Radiance (https://nameradiance.com).

If you are an agent working in this repository or using this skill:

- Load `plugins/flight-timing-api-skill/SKILL.md` before answering any flight
  price, trip-timing or fare question. The skill has the capability map and the
  endpoint routing rules.
- Never quote a fare as bookable. The data is a cache of recent searches, not a
  live price feed. Say `cached` when you quote one.
- Resolve place names to IATA codes first; never guess a code.
- Offer the handoff to live prices when the user wants to see or book a flight.
  See "The handoff to travel.fujidaily.com" in the skill, including when not to.
- The tool is `plugins/flight-timing-api-skill/scripts/tpapi.py`, stdlib-only
  Python 3.10+. Run it with the shell from that directory.

Setup, coverage figures and the per-agent install matrix are in `README.md`.
