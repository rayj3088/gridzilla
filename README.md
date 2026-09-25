# Gridwarden

*Grid capacity and risk for AI data centers. For responsible expansion.*

An interactive map and simulator for one question: **where can a new AI campus
actually plug in, and how much does efficiency or flexibility change the
answer?**

Everything is in `index.html`. No build step, no server, no dependencies.
Open it by double-clicking, or drop it on GitHub Pages and it is live.

## What works right now

- **Map.** A geographic US map when the optional libraries load, and a tile map
  (one square per state) when they don't. Both show the same marks.
- **Three layers**, matching the plan: Demand (data center markets, your
  sites), Supply (flexible headroom by grid region, live transmission lines and
  substations), Risk (water, zoning and incentive scores per state).
- **Simulator.** Campus size, architecture efficiency, and grid service (firm,
  or flexible at 0.25 / 0.5 / 1 percent curtailment). Results update live:
  power needed per campus, negatokens (power freed), and how many campuses fit
  in each grid region, standard versus your way.
- **Source switches.** One switch per source, 25 of them, in three modes:
  - `built in` — snapshot data shipped inside the file.
  - `live` — fetched by the browser when hosted normally. In a sandboxed
    preview the fetch is blocked and the app says so.
  - `engine` — runs in the Python engine. Switch it on, copy `sources.yaml`,
    run the engine, then import the engine's output here.
- **Sites.** Import a CSV of candidate sites, add them by hand, or load
  samples. They are ranked against the current scenario and can be copied back
  out as CSV.
- **Reports.** Copy a plain-text scenario report, or print to PDF.
- Settings, sites, risk scores and switches are saved in your browser.

## Data in the snapshot

| What | Source | Note |
|---|---|---|
| Flexible headroom per grid region | Duke Nicholas Institute, *Rethinking Load Growth* (Feb 2025) | 98 GW nationally at 0.5% curtailment; PJM 18, MISO 15, ERCOT 10, SPP 10, Southern 8. "Other" is the remainder. |
| Market inventory, construction, vacancy | CBRE, North America Data Center Trends (H2 2025, Q1 2026, H1 2026) | Some markets have no published figure; they show as n/a. |

Caveats the app repeats where they matter: headroom is a system-level,
first-order estimate, not an interconnection study for any one point on the
grid; the 0.25% and 1% levels are scaled from national totals; state shading
uses each state's main grid region and is approximate; the efficiency slider is
a what-if, not a measured result.

## Expanding it

The script is in numbered sections. The ones you'll touch:

1. **Add a source** — add an entry to `SOURCES` (section 3). Set `mode` to
   `engine` and you're done: it appears with a switch and lands in the exported
   `sources.yaml`. Set `mode: 'browser'` and add a loader function in `LOADERS`
   (section 5) to fetch it live.
2. **Change the snapshot** — `REGIONS`, `MARKETS`, `STATES` in section 2.
3. **Engine bridge** — the Import button accepts JSON:

```json
{
  "markets": [{"id":"col","name":"Columbus","st":"OH","region":"PJM",
               "lon":-82.99,"lat":39.96,"inv":800,"uc":1200,"vac":1.2,
               "asOf":"engine 2026-09"}],
  "regions": {"PJM": {"h05": 20}},
  "risk":    {"OH": {"water": 1, "zoning": 2, "incentives": 1}},
  "lines":   {"type":"FeatureCollection","features":[]},
  "sources": ["wri_aqueduct"]
}
```

4. **Map marks** — `renderMap()` in section 6. `place(lon, lat, state, i)`
   returns pixels in either map mode, so a new mark works on both.

## File structure

    gridzilla/
      index.html                 the whole app: map, layers, simulator, reports
      README.md
      ROADMAP.md
      LICENSE                    Apache 2.0
      .gitignore
      .github/
        FUNDING.yml
      config/
        sources.yaml             one switch per source; the app exports this
      docs/
        ARCHITECTURE.md          how the two halves fit together
        DATA_SOURCES.md          what is in the snapshot, what to connect next
        DATA_MODEL.md            the JSON contract between engine and app
        RISK_MODEL.md            how the risk scores work
        PRICING.md               free app, Tracker and Enterprise API plans
      engine/
        gridzilla_engine.py      ingestion engine, standard library only
        requirements.txt
        README.md
      out/                       engine output lands here (git-ignored)

## Running it

    # the app
    open index.html                       # macOS; or just double-click it

    # the engine
    python3 engine/gridzilla_engine.py --plan
    python3 engine/gridzilla_engine.py --fetch
    # then: app -> Sources -> Import engine output

To publish the free map: push this folder to GitHub and turn on Pages. The app
is one file, so Pages serves it as-is.

## Pricing

The app is free under Apache 2.0. Two paid plans: Tracker ($15 a month or
$120 a year) for following the watchlist, and the Enterprise API ($10,000 per
year, founding-customer price) for scenario scoring, batch site ranking and full
watchlist data. It is a planning tool built on public data and a static 2025
study, not engineering or legal advice. No priority data refresh or support tier
is included yet. See `docs/PRICING.md` and `terms.html`.

Support development: https://paypal.me/rayj3088
