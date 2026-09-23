# Data model

The engine writes, and the app imports, one JSON file:

    {
      "generated": "2026-09-22T14:00:00Z",
      "markets": [
        {"id": "col", "name": "Columbus", "st": "OH", "region": "PJM",
         "lon": -82.99, "lat": 39.96,
         "inv": 800, "uc": 1200, "vac": 1.2, "asOf": "engine 2026-09"}
      ],
      "regions": {"PJM": {"h05": 20}},
      "risk":    {"OH": {"water": 1, "zoning": 2, "incentives": 1}},
      "lines":   {"type": "FeatureCollection", "features": []},
      "sources": ["wri_aqueduct"]
    }

- `markets` are added to the snapshot markets. `region` must be one of PJM,
  MISO, ERCOT, SPP, SOCO, OTHER. `inv` and `uc` are MW.
- `regions` overrides headroom at 0.5% curtailment, in GW.
- `risk` scores run 0 (easy) to 5 (hard).
- `lines` is GeoJSON drawn on the geographic map.
- `sources` lists source ids the engine refreshed, for the Sources tab.

Sites import separately as CSV: `name, lat, lon, mw, state`.
Risk scores import as CSV: `state, water, zoning, incentives`.
