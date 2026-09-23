# Architecture

    config/sources.yaml     one switch per data source, shared by both halves
            |
            v
    engine/gridzilla_engine.py      Python, standard library only
       fetch -> validate -> normalize -> out/engine-output.json
            |
            v
    index.html              the app: map, layers, simulator, ranking, reports

Two halves, one contract. The app runs alone on snapshot data; the engine is
optional and feeds it richer data through one JSON file.

## The app (index.html)

Single file, no build step, no dependencies. Numbered sections in the script:

1. Config: scenario options (service levels).
2. Snapshot data: regions, states, tile grid, markets, tiers.
3. Source registry: every source and its mode.
4. App state: saved in the browser.
5. Engine: scenario math and browser loaders.
6. Map: geographic when the optional libraries load, tile grid otherwise.
7. Detail cards.
8. Panels.
9. Import and export.
10. Wiring.
11. Start.

Optional libraries (d3, topojson, a US topology) come from CDNs. If they are
blocked the app falls back to the tile map and everything still works.

## Source modes

- `snapshot`: shipped inside index.html.
- `browser`: fetched live by the app when hosted normally.
- `engine`: fetched by the Python engine, then imported into the app.

## The engine

`python3 engine/gridzilla_engine.py --plan` shows what is switched on.
`--fetch` runs the connectors it has and writes `out/engine-output.json`.
Add a connector by adding one function to `CONNECTORS`.
