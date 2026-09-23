#!/usr/bin/env python3
"""
GridZilla ingestion engine.

Reads config/sources.yaml (the same switches the app exports), fetches the
sources that have a connector, and writes out/engine-output.json in the shape
index.html imports. Standard library only. Safe by default: --plan just tells
you what is switched on; nothing leaves the machine until you pass --fetch.

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


# Write the next one here, then add it below. A connector returns any of:
#   {"markets": [...]} {"regions": {...}} {"risk": {...}} {"lines": geojson}
CONNECTORS = {
    "hifld_lines": connect_hifld_lines,
    "hifld_subs": connect_hifld_subs,
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
            count = sum(len(v.get("features", [])) if isinstance(v, dict) else len(v)
                        for v in piece.values())
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
