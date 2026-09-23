# Data sources

## In the snapshot

| What | Source | Vintage |
|---|---|---|
| Flexible headroom by grid region | Duke Nicholas Institute, *Rethinking Load Growth* | Feb 2025 |
| Market inventory, construction, vacancy | CBRE, North America Data Center Trends | H2 2025, Q1 2026, H1 2026 |

Headroom at 0.5% curtailment: PJM 18 GW, MISO 15, ERCOT 10, SPP 10, Southern
Co. 8; 98 GW nationally across the 22 largest balancing authorities. The
0.25% and 1% levels are scaled from the national totals (76 GW and 126 GW).

Caveats carried into the app: this is a system-level, first-order estimate,
not an interconnection study for any single point on the grid; state shading
uses each state's main grid region and is approximate.

## Switchable sources

`config/sources.yaml` holds all 25. Live in the browser: HIFLD transmission
lines and substations. Engine connectors to write next, in the order that
buys the most: LBNL Queued Up (who is ahead of you in line), EIA Open Data
(regional load), GridStatus.io (real-time ISO), WRI Aqueduct (water), FEMA
National Risk Index (hazards), and a data center pipeline feed such as
Aterio or Cleanview (commercial licence).
