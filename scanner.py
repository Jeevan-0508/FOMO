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
        "must_match": [
            "theft", "thieves", "stolen", "stole", "steal", "robbery", "robbed", "robbers",
            "hijack", "burglary", "burgled", "looted", "loot", "raid", "raided", "heist",
            "gang", "crimin", "smuggl",
            "diebstahl", "dieb", "gestohlen", "stehlen", "stiehlt", "raub", "beraubt", "geraubt",
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
        "must_match": [
            "phantom carrier", "missing trailer", "fake identity", "identity theft",
            "disappeared", "never arrived", "vanished", "ghost carrier", "impersonat",
            "double brokering", "cybercrim", "hacker",
            "frachtführerbetrug", "gestohlene ladung", "gefälschte identität",
            "verschwunden", "spurlos", "phantom",
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
        "must_match": [
            "fraud", "fraudster", "scam", "scammed", "swindle", "con artist",
            "double brokering", "double-brokering", "cargo crime", "seizure", "probe",
            "frachtbetrug", "betrug", "betrüger", "schwindel", "abzocke", "entlarvt",
            "scheinspedition", "freight crime",
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
        "must_match": [
            "insolven", "bankrupt", "liquidat", "administration", "receivership",
            "winding up", "wound up", "collapse", "folds", "folded", "ceases operation",
            "ceases trading", "files for", "going under", "restructuring", "restructure",
            "up for sale", "hard times", "struggling", "crisis", "turmoil",
            "job cuts", "cut jobs", "cutting jobs", "layoffs", "lay off", "jobs at risk",
            "insolvenz", "pleite", "bankrott", "abwicklung", "konkurs", "entlassen",
            "abgewickelt", "vor dem aus", "ermittelt", "ermittlung", "bangen um",
            "schließung", "macht dicht", "court supervision", "court protection",
            "schutzschirmverfahren", "rettet", "retten", "gerettet", "seeks investor",
            "gerichtskontrolle", "sanier", "aufgelöst", "auflösung", "zusammenbruch",
            "kämpft ums überleben",
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
        "must_match": [
            "fine", "fined", "penalt", "violat", "lawsuit", "sued", "sanction",
            "due diligence", "regulator", "regulation", "watchdog", "investigat",
            "probe", "seizure", "cabotage", "illegal cabotage", "tax probe",
            "lieferkettengesetz", "bußgeld", "verstoss", "verstoß", "klage",
            "sanktion", "compliance", "aufsicht",
            "forced labour", "forced labor", "human rights", "modern slavery",
            "child labour", "child labor", "complaint filed", "complaint",
            "ngo", "lksg", "lieferkettensorgfaltspflichtengesetz",
            "esg", "csddd", "csrd", "exploitation", "labour rights", "labor rights",
            "supply chain law", "supply chain act", "ausbeutung", "xinjiang",
            "sustainability law", "sustainability directive", "sustainability requirement",
            "duty of care", "supply chain abuse", "lieferkettensorgfalt",
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
        "must_match": [
            "strike", "walkout", "work stoppage", "cyberattack", "cyber attack",
            "ransomware", "hacked", "hacker", "breach", "outage", "halt", "pause output", "shutdown",
            "disrupt", "congestion", "block check", "border check", "traffic ban",
            "blockade", "blocking", "blockad", "protest", "shipping crisis",
            "shipping lane", "canal", "strait of", "chokepoint", "export ban",
            "chip shortage", "supply shock", "delay",
            "streik", "arbeitsniederlegung", "legten die arbeit nieder",
            "legten arbeit nieder", "lahmgelegt", "lahm", "urabstimmung",
            "blockieren", "blockade", "cyberangriff", "stillstand", "störung",
            "verzögerung", "blockabfertigung",
            "tarifverhandlung", "tarifstreit", "tarifkonflikt", "tarifeinigung",
        ],
    },
}


# Some risk phrasings vary too much in word order/number for a literal
# substring match (e.g. "DB Cargo to cut 6,200 jobs" vs. "job cuts"), so a
# few high-value patterns are matched with regex instead.
CATEGORY_REGEX = {
    "Corporate Insolvency": [
        r"cut[s]?\s+[\d.,]+\s*(jobs|stellen|arbeitsplätze)",
        r"(jobs|stellen|arbeitsplätze)\s+(werden\s+)?(abgebaut|gestrichen)",
    ],
}


def best_category_for(title: str, own_category: str) -> str | None:
    """Decide which category (if any) a headline actually belongs in.

    A category's search query is a broad net for Google News, which matches
    loosely on individual words rather than the query's intent - it will
    return a story about carrier tariffs for a "carrier fraud" query with no
    fraud in it anywhere. This checks the title against each category's own
    identifying keywords rather than trusting the query that fetched it.

    Returns the best-fit category, which may differ from own_category if the
    content clearly belongs elsewhere, or None if no category's keywords are
    present at all (the story is noise from an overly broad query).
    """
    lowered = title.lower().replace("\xad", "")
    own_cfg = CATEGORIES.get(own_category)
    if own_cfg and any(kw.lower() in lowered for kw in own_cfg.get("must_match", [])):
        return own_category
    own_patterns = CATEGORY_REGEX.get(own_category, [])
    if any(re.search(p, lowered) for p in own_patterns):
        return own_category

    best_cat, best_hits = None, 0
    for cat, cfg in CATEGORIES.items():
        hits = sum(1 for kw in cfg.get("must_match", []) if kw.lower() in lowered)
        hits += sum(2 for p in CATEGORY_REGEX.get(cat, []) if re.search(p, lowered))
        if hits > best_hits:
            best_cat, best_hits = cat, hits
    return best_cat

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
                # The query is a broad net for Google News, not a content filter -
                # confirm the headline actually matches a category before keeping it.
                actual_category = best_category_for(item["title"], category)
                if actual_category is None:
                    known_links.add(item["link"])  # seen, but not a real risk signal
                    continue
                final_cfg = CATEGORIES[actual_category]
                severity = score_severity(item["title"], final_cfg["severity"], final_cfg["escalate_if"])
                signal = {
                    "category": actual_category,
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
