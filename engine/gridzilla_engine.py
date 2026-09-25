#!/usr/bin/env python3
"""
GridZilla ingestion engine.

Reads config/sources.yaml (the same switches the app exports), fetches the
sources that have a connector, and writes out/engine-output.json in the shape
index.html imports. Standard library only, except the lbnl_queued_up
connector, which needs `openpyxl` (see requirements.txt) to read a real
.xlsx file. Safe by default: --plan just tells you what is switched on;
nothing leaves the machine until you pass --fetch.

    python3 engine/gridzilla_engine.py --plan
    python3 engine/gridzilla_engine.py --fetch
    python3 engine/gridzilla_engine.py --fetch --only hifld_lines

Add a source: switch it on in the app, copy sources.yaml over, then write one
function here and register it in CONNECTORS. A connector takes the source dict
and returns a piece of the output document.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config", "sources.yaml")
OUT_DIR = os.path.join(ROOT, "out")
OUT_FILE = os.path.join(OUT_DIR, "engine-output.json")
TIMEOUT = 60

# State/DC -> GridZilla grid region. Keep this in sync by hand with
# STATES in index.html and STATE_REGION in gridzilla-api/src/sites.js --
# three copies because this engine, the browser app, and the paid worker
# each run in a different place with no shared module between them.
STATE_REGION = {
    "AL": "SOCO", "AK": "OTHER", "AZ": "OTHER", "AR": "MISO", "CA": "OTHER",
    "CO": "OTHER", "CT": "OTHER", "DE": "PJM", "DC": "PJM", "FL": "OTHER",
    "GA": "SOCO", "HI": "OTHER", "ID": "OTHER", "IL": "PJM", "IN": "MISO",
    "IA": "MISO", "KS": "SPP", "KY": "OTHER", "LA": "MISO", "ME": "OTHER",
    "MD": "PJM", "MA": "OTHER", "MI": "MISO", "MN": "MISO", "MS": "MISO",
    "MO": "MISO", "MT": "OTHER", "NE": "SPP", "NV": "OTHER", "NH": "OTHER",
    "NJ": "PJM", "NM": "OTHER", "NY": "OTHER", "NC": "OTHER", "ND": "MISO",
    "OH": "PJM", "OK": "SPP", "OR": "OTHER", "PA": "PJM", "RI": "OTHER",
    "SC": "OTHER", "SD": "SPP", "TN": "OTHER", "TX": "ERCOT", "UT": "OTHER",
    "VT": "OTHER", "VA": "PJM", "WA": "OTHER", "WV": "PJM", "WI": "MISO",
    "WY": "OTHER"
}


# --------------------------------------------------------------- config

def read_sources(path: str = CONFIG) -> list:
    """Minimal reader for the flat list the app exports. No PyYAML needed."""
    items, cur = [], None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            stripped = line.strip()
            if stripped.startswith("- "):
                cur = {}
                items.append(cur)
                stripped = stripped[2:]
            if cur is None or ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            value = value.strip()
            if value.startswith('"') and value.endswith('"') and len(value) > 1:
                value = json.loads(value)
            elif value in ("true", "false"):
                value = value == "true"
            cur[key.strip()] = value
    return items


def api_key(source: dict) -> str:
    """Keys come from the environment, never from the config file."""
    return os.environ.get("GRIDZILLA_" + source["id"].upper() + "_KEY", "")


# ------------------------------------------------------------ connectors

def arcgis(url: str, where: str, **extra) -> dict:
    params = {"where": where, "outFields": "*", "returnGeometry": "true",
              "outSR": "4326", "f": "geojson", "resultRecordCount": "2000"}
    params.update(extra)
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": "gridzilla-engine"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        doc = json.loads(r.read().decode("utf-8"))
    if "error" in doc:
        raise RuntimeError(doc["error"].get("message", "service error"))
    if "features" not in doc:
        raise RuntimeError("no features in the response")
    return doc


def connect_hifld_lines(source: dict) -> dict:
    try:
        doc = arcgis(source["url"], "VOLTAGE>=345", maxAllowableOffset="0.02")
    except (urllib.error.HTTPError, RuntimeError):
        doc = arcgis(source["url"], "1=1", maxAllowableOffset="0.02")
    return {"lines": doc}


def connect_hifld_subs(source: dict) -> dict:
    try:
        doc = arcgis(source["url"], "MAX_VOLT>=345")
    except (urllib.error.HTTPError, RuntimeError):
        doc = arcgis(source["url"], "1=1")
    return {"substations": doc}


# LBNL republishes this yearly at a dated URL; update when a new edition
# ships (check https://emp.lbl.gov/queues for the current link).
LBNL_QUEUED_UP_XLSX_URL = (
    "https://emp.lbl.gov/sites/default/files/2026-05/"
    "LBNL_Ix_Queue_Data_File_thru2025.xlsx"
)


def connect_lbnl_queued_up(source: dict) -> dict:
    """
    Free, no-login download of LBNL's "Queued Up" interconnection-queue
    workbook (CC BY 4.0, Lawrence Berkeley National Laboratory). Sums MW of
    generation + storage capacity currently *active* in queue -- proposed,
    not yet built, not withdrawn -- by GridZilla grid region.

    This is NOT the same measurement as the Duke headroom study (room
    available on the grid today) -- it's how much new supply is waiting in
    line to connect. Treat it as context alongside the Duke numbers, not a
    replacement: more queued capacity can eventually raise real headroom
    once built, or signal a region where queues are backed up.

    Needs `openpyxl` (see requirements.txt) -- the one dependency this
    otherwise-stdlib-only engine has, because the file is a real .xlsx.
    """
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("needs `pip install openpyxl` (see requirements.txt)") from exc

    req = urllib.request.Request(LBNL_QUEUED_UP_XLSX_URL,
                                  headers={"User-Agent": "gridzilla-engine"})
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp_path = os.path.join(OUT_DIR, "_lbnl_queued_up.xlsx")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r, open(tmp_path, "wb") as fh:
        fh.write(r.read())
    try:
        wb = openpyxl.load_workbook(tmp_path, read_only=True, data_only=True)
        ws = wb["03. Complete Queue Data"]
        # Row 1 is a "return to contents" link, row 2 is the header; data from row 3.
        by_region_mw, counted, skipped_status, skipped_state = {}, 0, 0, 0
        for row in ws.iter_rows(min_row=3, values_only=True):
            status, state, mw1 = row[1], row[10], row[25]
            if status != "active":
                skipped_status += 1
                continue
            region = STATE_REGION.get((state or "").upper())
            if not region:
                skipped_state += 1   # Canadian provinces, Mexico, or blank
                continue
            by_region_mw[region] = by_region_mw.get(region, 0) + (mw1 or 0)
            counted += 1
    finally:
        os.remove(tmp_path)

    return {"pipeline_capacity_gw": {
        "regions": {r: round(mw / 1000, 2) for r, mw in by_region_mw.items()},
        "meaning": (
            "Generation + storage capacity (MW), summed to GW, currently "
            "active in interconnection queues -- proposed, not yet built or "
            "withdrawn -- by GridZilla grid region. Not headroom: this is "
            "new supply waiting in line, not room available on the grid "
            "today."
        ),
        "as_of": "LBNL Queued Up, 2026 edition (interconnection requests through end of 2025)",
        "source": "https://emp.lbl.gov/queues (CC BY 4.0, Lawrence Berkeley National Laboratory)",
        "rows_counted": counted,
        "rows_skipped_not_active": skipped_status,
        "rows_skipped_non_us_or_unknown_state": skipped_state
    }}


# Write the next one here, then add it below. A connector returns any of:
#   {"markets": [...]} {"regions": {...}} {"risk": {...}} {"lines": geojson}
#   or any other key -- it is merged into the output document as-is.
CONNECTORS = {
    "hifld_lines": connect_hifld_lines,
    "hifld_subs": connect_hifld_subs,
    "lbnl_queued_up": connect_lbnl_queued_up,
}


# ------------------------------------------------------------------ run

def plan(sources: list) -> None:
    on = [s for s in sources if s.get("enabled")]
    print(f"{len(on)} of {len(sources)} sources switched on\n")
    for mode in ("snapshot", "browser", "engine"):
        rows = [s for s in on if s.get("mode") == mode]
        if not rows:
            continue
        print(f"{mode}:")
        for s in rows:
            if mode == "engine" and s["id"] not in CONNECTORS:
                note = "no connector yet: add one in gridzilla_engine.py"
            elif s["id"] in CONNECTORS:
                note = "ready" + (", key found" if api_key(s) else
                                  ", no key in the environment" if s.get("needs_key") else "")
            else:
                note = "handled by the app"
            print(f"  {s['id']:<22} {s.get('dataset', '')[:46]:<48} {note}")
        print()


def fetch(sources: list, only: str = "") -> dict:
    out = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": [], "status": {}}
    for s in sources:
        if not s.get("enabled") or s["id"] not in CONNECTORS:
            continue
        if only and s["id"] != only:
            continue
        print(f"fetching {s['id']} ... ", end="", flush=True)
        try:
            piece = CONNECTORS[s["id"]](s)
            for key, value in piece.items():
                if key in ("markets",):
                    out.setdefault(key, []).extend(value)
                elif key in ("regions", "risk"):
                    out.setdefault(key, {}).update(value)
                else:
                    out[key] = value
            out["sources"].append(s["id"])
            def _count(v):
                if isinstance(v, dict) and "features" in v:
                    return len(v["features"])
                if isinstance(v, dict) and "rows_counted" in v:
                    return v["rows_counted"]
                return len(v) if isinstance(v, (list, dict)) else 1
            count = sum(_count(v) for v in piece.values())
            out["status"][s["id"]] = f"ok, {count} records"
            print(f"ok, {count} records")
        except Exception as exc:                     # a bad source never stops the run
            out["status"][s["id"]] = f"{type(exc).__name__}: {exc}"
            print(f"failed: {exc}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GridZilla ingestion engine")
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--plan", action="store_true", help="show what is switched on and stop")
    ap.add_argument("--fetch", action="store_true", help="fetch and write out/engine-output.json")
    ap.add_argument("--only", default="", help="fetch a single source id")
    ap.add_argument("--out", default=OUT_FILE)
    a = ap.parse_args(argv)
    if not os.path.exists(a.config):
        print(f"no config at {a.config}. Export one from the app's Sources tab.", file=sys.stderr)
        return 2
    sources = read_sources(a.config)
    if not a.fetch:
        plan(sources)
        if not a.plan:
            print("Nothing fetched. Add --fetch when you want data.")
        return 0
    doc = fetch(sources, a.only)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    size = os.path.getsize(a.out) / 1024
    print(f"\nwrote {a.out} ({size:.0f} kB). Import it in the app: Sources tab, "
          f"Import engine output.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
