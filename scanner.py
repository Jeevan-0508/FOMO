#!/usr/bin/env python3
"""
FOMO - Fear Of Missing Out
Supply chain & logistics risk radar for the Germany region.

Scans public Google News RSS for logistics/supply-chain risk signals
(cargo theft, missing trailers, carrier/freight fraud, insolvency,
regulatory/compliance risk, disruption) and builds a static HTML dashboard.

No Amazon-internal data is used anywhere in this tool. All signals come
from public news sources.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNALS_PATH = os.path.join(DATA_DIR, "signals.json")
DASHBOARD_PATH = os.path.join(BASE_DIR, "dashboard.html")

# category -> list of (query, language) pairs to scan, plus severity config.
# Each category now scans both English and German-language coverage, since
# German regional press (local papers, DVZ, Verkehrsrundschau, police
# releases) reports plenty of incidents that never show up in English feeds.
CATEGORIES = {
    "Cargo Theft": {
        "queries": [
            {"q": "cargo theft Germany logistics OR trucking OR freight", "lang": "en"},
            {"q": "Ladungsdiebstahl OR \"LKW Diebstahl\" Fracht", "lang": "de"},
        ],
        "severity": "high",
        "escalate_if": [
            "organised", "organized crime", "armed", "violence", "hijack",
            "organisierte kriminalität", "bewaffnet", "gewalt",
        ],
    },
    "Missing Trailer / Phantom Carrier": {
        "queries": [
            {"q": "phantom carrier fraud OR missing trailer freight Germany", "lang": "en"},
            {"q": "Frachtbetrug OR Frachtführerbetrug OR \"gestohlene Ladung\"", "lang": "de"},
        ],
        "severity": "high",
        "escalate_if": [
            "fake identity", "identity theft", "disappeared", "never arrived",
            "gefälschte identität", "verschwunden", "spurlos",
        ],
    },
    "Carrier / Freight Fraud": {
        "queries": [
            {"q": "freight fraud OR carrier fraud Germany logistics", "lang": "en"},
            {"q": "Frachtbetrug Spedition OR \"Frachtführer Betrug\"", "lang": "de"},
        ],
        "severity": "medium",
        "escalate_if": [
            "million", "€", "criminal", "arrested", "indicted",
            "verhaftet", "angeklagt", "betrug",
        ],
    },
    "Corporate Insolvency": {
        "queries": [
            {"q": "logistics OR trucking OR transport company insolvency Germany", "lang": "en"},
            {"q": "Spedition Insolvenz OR \"Logistikunternehmen Insolvenz\"", "lang": "de"},
        ],
        "severity": "medium",
        "escalate_if": [
            "insolvenz", "bankruptcy", "collapse", "shut down", "liquidation",
            "insolvenzverfahren", "bankrott", "pleite",
        ],
    },
    "Regulatory / Compliance Risk": {
        "queries": [
            {"q": "Lieferkettengesetz OR supply chain due diligence Germany fine OR violation", "lang": "en"},
            {"q": "Lieferkettensorgfaltspflichtengesetz OR \"Lieferkettengesetz Bußgeld\"", "lang": "de"},
        ],
        "severity": "low",
        "escalate_if": [
            "fine", "penalty", "violation", "lawsuit",
            "bußgeld", "verstoss", "verstoß", "klage",
        ],
    },
    "Operational Disruption": {
        "queries": [
            {"q": "Germany logistics OR supply chain strike OR disruption OR cyberattack", "lang": "en"},
            {"q": "Streik Logistik Deutschland OR \"Cyberangriff Spedition\"", "lang": "de"},
        ],
        "severity": "medium",
        "escalate_if": [
            "cyberattack", "ransomware", "strike", "halt", "shutdown",
            "cyberangriff", "streik", "stillstand",
        ],
    },
}

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
USER_AGENT = "Mozilla/5.0 (compatible; FOMO-RiskRadar/1.0)"


def _fetch_once(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
    items = []
    root = ET.fromstring(raw)
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else "Unknown"
        if title and link:
            items.append({"title": title, "link": link, "pub_date": pub_date, "source": source})
    return items


def fetch_rss(query: str, region: str = "DE", lang: str = "en", retries: int = 2) -> list[dict]:
    """Pull a Google News RSS feed for a query, scoped loosely to the Germany region.

    Google News RSS silently returns an empty feed (HTTP 200, no <item>s) when it
    throttles a client instead of raising an error, so an empty result is retried
    with backoff before being trusted as a real "no news" result.
    """
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl={lang}-{region}&gl={region}&ceid={region}:{lang}"

    for attempt in range(retries + 1):
        try:
            items = _fetch_once(url)
        except Exception as e:
            print(f"  [warn] fetch failed for query '{query}' (attempt {attempt + 1}): {e}", file=sys.stderr)
            items = []
        if items:
            return items
        if attempt < retries:
            time.sleep(4 * (attempt + 1))
    print(f"  [info] no results for query '{query}' after {retries + 1} attempt(s)", file=sys.stderr)
    return []


def score_severity(title: str, base_severity: str, escalate_keywords: list[str]) -> str:
    lowered = title.lower()
    hits = sum(1 for kw in escalate_keywords if kw.lower() in lowered)
    if hits >= 2:
        return "critical"
    if hits == 1:
        idx = SEVERITY_RANK[base_severity]
        for sev, rank in SEVERITY_RANK.items():
            if rank == idx + 1:
                return sev
        return base_severity
    return base_severity


def load_existing() -> dict:
    if os.path.exists(SIGNALS_PATH):
        with open(SIGNALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"signals": [], "runs": []}


def run_scan() -> dict:
    state = load_existing()
    known_links = {s["link"] for s in state["signals"]}
    new_count = 0
    now = datetime.now(timezone.utc).isoformat()

    category_items = list(CATEGORIES.items())
    for idx, (category, cfg) in enumerate(category_items):
        if idx > 0:
            time.sleep(2)
        queries = cfg.get("queries") or [{"q": cfg.get("query", ""), "lang": "en"}]
        for q_idx, q_cfg in enumerate(queries):
            print(f"Scanning: {category} ({q_cfg['lang']}) ...")
            if q_idx > 0:
                time.sleep(2)
            for item in fetch_rss(q_cfg["q"], lang=q_cfg["lang"]):
                if item["link"] in known_links:
                    continue
                severity = score_severity(item["title"], cfg["severity"], cfg["escalate_if"])
                signal = {
                    "category": category,
                    "title": item["title"],
                    "link": item["link"],
                    "source": item["source"],
                    "pub_date": item["pub_date"],
                    "severity": severity,
                    "found_at": now,
                }
                state["signals"].append(signal)
                known_links.add(item["link"])
                new_count += 1

    state["runs"].append({
        "timestamp": now,
        "new_signals": new_count,
        "total_signals": len(state["signals"]),
    })

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SIGNALS_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {new_count} new signal(s) this run, {len(state['signals'])} total.")
    return state


if __name__ == "__main__":
    run_scan()
