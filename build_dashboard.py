#!/usr/bin/env python3
"""Builds dashboard.html from data/signals.json. Run after scanner.py."""

import json
import os
from collections import Counter
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIGNALS_PATH = os.path.join(BASE_DIR, "data", "signals.json")
OUT_PATH = os.path.join(BASE_DIR, "dashboard.html")

SEVERITY_COLOR = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#65a30d",
}
SEVERITY_ORDER = ["critical", "high", "medium", "low"]


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def build():
    with open(SIGNALS_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
    signals = state["signals"]
    signals.sort(key=lambda s: (SEVERITY_ORDER.index(s["severity"]) if s["severity"] in SEVERITY_ORDER else 9, s.get("pub_date", "")), )

    total = len(signals)
    by_severity = Counter(s["severity"] for s in signals)
    by_category = Counter(s["category"] for s in signals)
    critical_high = by_severity.get("critical", 0) + by_severity.get("high", 0)
    last_run = state["runs"][-1] if state.get("runs") else {}
    last_run_time = last_run.get("timestamp", "n/a")
    total_runs = len(state.get("runs", []))

    categories = list(by_category.keys())
    severities = SEVERITY_ORDER

    rows_html = []
    for s in signals:
        color = SEVERITY_COLOR.get(s["severity"], "#6b7280")
        rows_html.append(f"""
        <tr class="signal-row border-b border-slate-700 hover:bg-slate-800/60"
            data-category="{esc(s['category'])}" data-severity="{esc(s['severity'])}">
          <td class="px-4 py-3">
            <span class="inline-block px-2 py-1 rounded text-xs font-semibold text-white" style="background-color:{color}">
              {s['severity'].upper()}
            </span>
          </td>
          <td class="px-4 py-3 text-slate-300 whitespace-nowrap">{esc(s['category'])}</td>
          <td class="px-4 py-3">
            <a href="{esc(s['link'])}" target="_blank" rel="noopener" class="text-sky-400 hover:text-sky-300 hover:underline">
              {esc(s['title'])}
            </a>
          </td>
          <td class="px-4 py-3 text-slate-400 whitespace-nowrap">{esc(s['source'])}</td>
          <td class="px-4 py-3 text-slate-500 whitespace-nowrap text-sm">{esc(s.get('pub_date',''))}</td>
        </tr>""")

    category_filter_buttons = "".join(
        f'<button class="cat-filter px-3 py-1.5 rounded-full text-sm border border-slate-600 text-slate-300 hover:border-sky-500 hover:text-sky-400 transition" data-value="{esc(c)}">{esc(c)}</button>'
        for c in categories
    )
    severity_filter_buttons = "".join(
        f'<button class="sev-filter px-3 py-1.5 rounded-full text-sm border border-slate-600 hover:border-sky-500 transition" style="color:{SEVERITY_COLOR[s]}" data-value="{s}">{s.upper()}</button>'
        for s in severities if s in by_severity
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FOMO — Supply Chain Risk Radar (Germany)</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body {{ background: #0f172a; }}
  .glow {{ box-shadow: 0 0 40px rgba(56,189,248,0.08); }}
</style>
</head>
<body class="text-slate-100 font-sans">
  <div class="max-w-7xl mx-auto px-6 py-8">

    <header class="flex items-center justify-between mb-8">
      <div class="flex items-center gap-4">
        <img src="icons/jk-logo.png" alt="logo" class="w-12 h-12 rounded-lg object-cover" />
        <div>
          <h1 class="text-3xl font-bold tracking-tight">
            <span class="text-sky-400">FOMO</span> — Fear Of Missing Out
          </h1>
          <p class="text-slate-400 mt-1">Supply chain &amp; logistics risk radar — Germany region · public news only</p>
        </div>
      </div>
      <div class="text-right text-sm text-slate-500">
        <div>Last scan: {esc(str(last_run_time))}</div>
        <div>Total scans run: {total_runs}</div>
      </div>
    </header>

    <section class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5 glow">
        <div class="text-slate-400 text-sm">Total Signals</div>
        <div class="text-3xl font-bold mt-1">{total}</div>
      </div>
      <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5 glow">
        <div class="text-slate-400 text-sm">Critical + High</div>
        <div class="text-3xl font-bold mt-1 text-orange-500">{critical_high}</div>
      </div>
      <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5 glow">
        <div class="text-slate-400 text-sm">Categories Tracked</div>
        <div class="text-3xl font-bold mt-1">{len(categories)}</div>
      </div>
      <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5 glow">
        <div class="text-slate-400 text-sm">Sources Covered</div>
        <div class="text-3xl font-bold mt-1">{len(set(s['source'] for s in signals))}</div>
      </div>
    </section>

    <section class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
      <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
        <h2 class="text-lg font-semibold mb-3">Signals by Severity</h2>
        <canvas id="severityChart" height="200"></canvas>
      </div>
      <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
        <h2 class="text-lg font-semibold mb-3">Signals by Category</h2>
        <canvas id="categoryChart" height="200"></canvas>
      </div>
    </section>

    <section class="mb-4 flex flex-wrap gap-2 items-center">
      <span class="text-slate-400 text-sm mr-2">Severity:</span>
      <button class="sev-filter px-3 py-1.5 rounded-full text-sm border border-sky-500 text-sky-400" data-value="all">ALL</button>
      {severity_filter_buttons}
    </section>
    <section class="mb-6 flex flex-wrap gap-2 items-center">
      <span class="text-slate-400 text-sm mr-2">Category:</span>
      <button class="cat-filter px-3 py-1.5 rounded-full text-sm border border-sky-500 text-sky-400" data-value="all">ALL</button>
      {category_filter_buttons}
    </section>

    <section class="bg-slate-800/60 border border-slate-700 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-900/80 text-slate-400 text-left">
          <tr>
            <th class="px-4 py-3">Severity</th>
            <th class="px-4 py-3">Category</th>
            <th class="px-4 py-3">Headline</th>
            <th class="px-4 py-3">Source</th>
            <th class="px-4 py-3">Published</th>
          </tr>
        </thead>
        <tbody id="signalsBody">
          {''.join(rows_html)}
        </tbody>
      </table>
    </section>

    <footer class="text-center text-slate-600 text-xs mt-8">
      FOMO scans public news only. No Amazon-internal data is used or referenced.
    </footer>
  </div>

<script>
  const severityData = {json.dumps(dict(by_severity))};
  const categoryData = {json.dumps(dict(by_category))};
  const severityColors = {json.dumps(SEVERITY_COLOR)};

  new Chart(document.getElementById('severityChart'), {{
    type: 'doughnut',
    data: {{
      labels: Object.keys(severityData).map(s => s.toUpperCase()),
      datasets: [{{
        data: Object.values(severityData),
        backgroundColor: Object.keys(severityData).map(s => severityColors[s] || '#6b7280'),
        borderWidth: 0,
      }}]
    }},
    options: {{ plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }} }}
  }});

  new Chart(document.getElementById('categoryChart'), {{
    type: 'bar',
    data: {{
      labels: Object.keys(categoryData),
      datasets: [{{
        data: Object.values(categoryData),
        backgroundColor: '#0ea5e9',
        borderRadius: 6,
      }}]
    }},
    options: {{
      indexAxis: 'y',
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} }},
        y: {{ ticks: {{ color: '#cbd5e1' }}, grid: {{ display: false }} }}
      }}
    }}
  }});

  let activeSeverity = 'all';
  let activeCategory = 'all';

  function applyFilters() {{
    document.querySelectorAll('.signal-row').forEach(row => {{
      const sevOk = activeSeverity === 'all' || row.dataset.severity === activeSeverity;
      const catOk = activeCategory === 'all' || row.dataset.category === activeCategory;
      row.style.display = (sevOk && catOk) ? '' : 'none';
    }});
  }}

  document.querySelectorAll('.sev-filter').forEach(btn => {{
    btn.addEventListener('click', () => {{
      activeSeverity = btn.dataset.value;
      document.querySelectorAll('.sev-filter').forEach(b => b.classList.remove('border-sky-500'));
      btn.classList.add('border-sky-500');
      applyFilters();
    }});
  }});
  document.querySelectorAll('.cat-filter').forEach(btn => {{
    btn.addEventListener('click', () => {{
      activeCategory = btn.dataset.value;
      document.querySelectorAll('.cat-filter').forEach(b => b.classList.remove('border-sky-500'));
      btn.classList.add('border-sky-500');
      applyFilters();
    }});
  }});
</script>
</body>
</html>
"""
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard written to {OUT_PATH}")


if __name__ == "__main__":
    build()
