#!/usr/bin/env python3
"""Builds index.html (and dashboard.html alias) from data/signals.json.

Generates a single-page app: a dramatic intro animation, a classy animated
home/landing page explaining what FOMO does, and the risk dashboard itself
(KPIs, charts, a date picker for daily snapshots, and a filterable table).
All rendering of the dashboard is data-driven in-browser JS, so the date
filter works without a server.
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIGNALS_PATH = os.path.join(BASE_DIR, "data", "signals.json")
INDEX_PATH = os.path.join(BASE_DIR, "index.html")
DASHBOARD_PATH = os.path.join(BASE_DIR, "dashboard.html")

SEVERITY_COLOR = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#65a30d",
}


def build():
    with open(SIGNALS_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
    signals = state.get("signals", [])
    runs = state.get("runs", [])
    last_run = runs[-1]["timestamp"] if runs else "never"

    payload = json.dumps({
        "signals": signals,
        "severityColor": SEVERITY_COLOR,
        "lastRun": last_run,
        "totalRuns": len(runs),
    }, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FOMO — Supply Chain Risk Radar</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="icons/jk-logo.png">
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  html, body {{ background:#05060a; margin:0; overflow-x:hidden; }}
  * {{ box-sizing:border-box; }}
  .page {{ display:none; }}
  .page.active {{ display:block; }}

  /* ---------------- Intro ---------------- */
  #intro {{
    position:fixed; inset:0; z-index:9999; background:#000;
    display:flex; align-items:center; justify-content:center;
    flex-direction:column; overflow:hidden;
  }}
  #introCanvas {{ position:absolute; inset:0; }}
  #introContent {{ position:relative; z-index:2; text-align:center; }}
  .fomo-title {{
    font-family: 'Courier New', monospace; letter-spacing: 0.4em;
    font-size: clamp(2.5rem, 10vw, 6rem); font-weight:900; color:#38bdf8;
    text-shadow: 0 0 20px rgba(56,189,248,0.9), 0 0 60px rgba(56,189,248,0.5);
    opacity:0; transform: scale(0.85);
    animation: fomoReveal 1.4s ease-out forwards;
  }}
  .fomo-sub {{
    margin-top:1.2rem; font-family:'Courier New',monospace; color:#94a3b8;
    letter-spacing:0.3em; font-size:0.85rem; opacity:0;
    animation: fadeUp 1s ease-out 1.3s forwards;
  }}
  .fomo-typed {{
    margin-top:2rem; color:#38bdf8; font-family:'Courier New',monospace;
    font-size:0.95rem; min-height:1.4em; opacity:0;
    animation: fadeUp 0.6s ease-out 2.1s forwards;
  }}
  @keyframes fomoReveal {{
    0% {{ opacity:0; transform:scale(0.7) skewX(8deg); filter:blur(8px); }}
    40% {{ opacity:1; transform:scale(1.05) skewX(-2deg); filter:blur(1px); }}
    100% {{ opacity:1; transform:scale(1) skewX(0); filter:blur(0); }}
  }}
  @keyframes fadeUp {{
    from {{ opacity:0; transform:translateY(12px); }}
    to {{ opacity:1; transform:translateY(0); }}
  }}
  #introSkip {{
    position:absolute; bottom:2rem; right:2rem; z-index:3;
    color:#475569; font-size:0.75rem; border:1px solid #1e293b;
    padding:0.4rem 0.9rem; border-radius:999px; cursor:pointer;
    font-family:'Courier New',monospace; transition:all .2s;
  }}
  #introSkip:hover {{ color:#38bdf8; border-color:#38bdf8; }}

  /* ---------------- Home ---------------- */
  #home {{ min-height:100vh; color:#e2e8f0; position:relative; }}
  .bg-grid {{
    position:fixed; inset:0; z-index:0;
    background-image: linear-gradient(rgba(56,189,248,0.05) 1px, transparent 1px),
                       linear-gradient(90deg, rgba(56,189,248,0.05) 1px, transparent 1px);
    background-size: 40px 40px;
    animation: gridDrift 30s linear infinite;
  }}
  @keyframes gridDrift {{ from {{ background-position:0 0; }} to {{ background-position:400px 400px; }} }}
  .glow-orb {{
    position:fixed; width:600px; height:600px; border-radius:50%;
    background: radial-gradient(circle, rgba(56,189,248,0.15), transparent 70%);
    filter: blur(40px); z-index:0; pointer-events:none;
    animation: orbFloat 12s ease-in-out infinite;
  }}
  @keyframes orbFloat {{
    0%,100% {{ transform: translate(-10%, -10%); }}
    50% {{ transform: translate(10%, 15%); }}
  }}
  .hero {{ position:relative; z-index:1; max-width:1100px; margin:0 auto; padding:6rem 1.5rem 3rem; text-align:center; }}
  .hero h1 {{
    font-size:clamp(2.2rem, 6vw, 4rem); font-weight:900; letter-spacing:-0.02em;
    background: linear-gradient(120deg, #38bdf8, #818cf8, #38bdf8);
    background-size:200% auto; -webkit-background-clip:text; background-clip:text; color:transparent;
    animation: shine 4s linear infinite;
  }}
  @keyframes shine {{ to {{ background-position:200% center; }} }}
  .hero p.tagline {{ color:#94a3b8; font-size:1.15rem; margin-top:1rem; max-width:640px; margin-inline:auto; }}
  .cta-btn {{
    display:inline-flex; align-items:center; gap:0.6rem; margin-top:2.5rem;
    background:linear-gradient(120deg,#0ea5e9,#6366f1); color:white; font-weight:600;
    padding:0.9rem 2rem; border-radius:999px; border:none; cursor:pointer; font-size:1rem;
    box-shadow:0 0 30px rgba(56,189,248,0.4); transition:transform .2s, box-shadow .2s;
  }}
  .cta-btn:hover {{ transform:translateY(-2px); box-shadow:0 0 45px rgba(56,189,248,0.6); }}
  .feature-grid {{ position:relative; z-index:1; max-width:1100px; margin:2rem auto 5rem; padding:0 1.5rem;
    display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:1.25rem; }}
  .feature-card {{
    background:rgba(15,23,42,0.6); border:1px solid #1e293b; border-radius:1rem; padding:1.5rem;
    backdrop-filter: blur(6px); transition: border-color .2s, transform .2s; opacity:0; transform:translateY(20px);
    animation: fadeUp 0.6s ease-out forwards;
  }}
  .feature-card:hover {{ border-color:#38bdf8; transform:translateY(-4px); }}
  .feature-card .emoji {{ font-size:1.8rem; }}
  .feature-card h3 {{ margin:0.6rem 0 0.4rem; font-size:1.05rem; color:#e2e8f0; }}
  .feature-card p {{ color:#94a3b8; font-size:0.88rem; line-height:1.5; margin:0; }}
  .stat-strip {{ position:relative; z-index:1; max-width:900px; margin:0 auto 4rem; padding:0 1.5rem;
    display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; text-align:center; }}
  .stat-strip .num {{ font-size:2.2rem; font-weight:800; color:#38bdf8; }}
  .stat-strip .lbl {{ color:#64748b; font-size:0.8rem; letter-spacing:0.05em; text-transform:uppercase; }}

  /* ---------------- App / dashboard ---------------- */
  #app {{ color:#e2e8f0; min-height:100vh; }}
  .glowcard {{ box-shadow: 0 0 40px rgba(56,189,248,0.08); }}
  #backHome {{ cursor:pointer; }}
</style>
</head>
<body>

  <!-- ============ INTRO ============ -->
  <div id="intro">
    <canvas id="introCanvas"></canvas>
    <div id="introContent">
      <div class="fomo-title">F.O.M.O</div>
      <div class="fomo-sub">FEAR&nbsp;·&nbsp;OF&nbsp;·&nbsp;MISSING&nbsp;·&nbsp;OUT</div>
      <div class="fomo-typed" id="typedLine"></div>
    </div>
    <div id="introSkip">SKIP ▶</div>
  </div>

  <!-- ============ HOME ============ -->
  <div id="home" class="page">
    <div class="bg-grid"></div>
    <div class="glow-orb" style="top:0;left:0;"></div>
    <div class="glow-orb" style="bottom:0;right:0; background:radial-gradient(circle, rgba(129,140,248,0.15), transparent 70%);"></div>

    <div class="hero">
      <img src="icons/jk-logo.png" width="64" style="border-radius:12px; margin-bottom:1.5rem;" />
      <h1>The risk you don't see<br/>is the one that costs you.</h1>
      <p class="tagline">
        FOMO watches public news for supply chain &amp; logistics risk signals across the
        Germany region — cargo theft, phantom carriers, freight fraud, insolvencies, regulatory
        violations, and disruption — so you're never the last to know.
      </p>
      <button class="cta-btn" id="enterBtn">Enter the Radar →</button>
    </div>

    <div class="stat-strip">
      <div><div class="num" id="statTotal">0</div><div class="lbl">Signals Tracked</div></div>
      <div><div class="num" id="statCritHigh">0</div><div class="lbl">Critical + High</div></div>
      <div><div class="num" id="statSources">0</div><div class="lbl">Sources Covered</div></div>
    </div>

    <div class="feature-grid">
      <div class="feature-card" style="animation-delay:.05s">
        <div class="emoji">🚛</div><h3>Cargo Theft</h3>
        <p>Organised crime, hijackings, and theft-in-transit signals as they hit the press.</p>
      </div>
      <div class="feature-card" style="animation-delay:.1s">
        <div class="emoji">🕵️</div><h3>Phantom Carriers</h3>
        <p>Fake carrier identities and missing-trailer fraud patterns surfacing in freight news.</p>
      </div>
      <div class="feature-card" style="animation-delay:.15s">
        <div class="emoji">📉</div><h3>Corporate Insolvency</h3>
        <p>Carriers and logistics firms heading toward bankruptcy before it hits your lane.</p>
      </div>
      <div class="feature-card" style="animation-delay:.2s">
        <div class="emoji">⚖️</div><h3>Regulatory Risk</h3>
        <p>LkSG / supply chain due-diligence fines and violations as they're reported.</p>
      </div>
      <div class="feature-card" style="animation-delay:.25s">
        <div class="emoji">🔥</div><h3>Operational Disruption</h3>
        <p>Strikes, cyberattacks, and network shocks hitting German logistics.</p>
      </div>
      <div class="feature-card" style="animation-delay:.3s">
        <div class="emoji">🗓️</div><h3>Daily Snapshots</h3>
        <p>Every scan is a dated snapshot — scrub back through history with the calendar picker.</p>
      </div>
    </div>
  </div>

  <!-- ============ APP / DASHBOARD ============ -->
  <div id="app" class="page">
    <div class="max-w-7xl mx-auto px-6 py-8">

      <header class="flex items-center justify-between mb-8 flex-wrap gap-4">
        <div class="flex items-center gap-4">
          <img src="icons/jk-logo.png" alt="logo" class="w-12 h-12 rounded-lg object-cover" />
          <div>
            <h1 class="text-3xl font-bold tracking-tight">
              <span id="backHome" class="text-sky-400 hover:underline" title="Back to home">FOMO</span> — Fear Of Missing Out
            </h1>
            <p class="text-slate-400 mt-1">Supply chain &amp; logistics risk radar — Germany region · public news only</p>
          </div>
        </div>
        <div class="text-right text-sm text-slate-500">
          <div>Last scan: <span id="lastRunLbl">—</span></div>
          <div>Total scans run: <span id="totalRunsLbl">—</span></div>
        </div>
      </header>

      <section class="mb-6 flex flex-wrap items-center gap-3 bg-slate-800/60 border border-slate-700 rounded-xl p-4">
        <label class="text-slate-400 text-sm">📅 View snapshot:</label>
        <select id="dateSelect" class="bg-slate-900 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-slate-200"></select>
        <span class="text-slate-500 text-xs" id="dateHint"></span>
      </section>

      <section class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5 glowcard">
          <div class="text-slate-400 text-sm">Total Signals</div>
          <div class="text-3xl font-bold mt-1" id="kpiTotal">0</div>
        </div>
        <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5 glowcard">
          <div class="text-slate-400 text-sm">Critical + High</div>
          <div class="text-3xl font-bold mt-1 text-orange-500" id="kpiCritHigh">0</div>
        </div>
        <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5 glowcard">
          <div class="text-slate-400 text-sm">Categories Tracked</div>
          <div class="text-3xl font-bold mt-1" id="kpiCategories">0</div>
        </div>
        <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-5 glowcard">
          <div class="text-slate-400 text-sm">Sources Covered</div>
          <div class="text-3xl font-bold mt-1" id="kpiSources">0</div>
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

      <section class="mb-4 flex flex-wrap gap-2 items-center" id="sevFilters">
        <span class="text-slate-400 text-sm mr-2">Severity:</span>
      </section>
      <section class="mb-6 flex flex-wrap gap-2 items-center" id="catFilters">
        <span class="text-slate-400 text-sm mr-2">Category:</span>
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
          <tbody id="signalsBody"></tbody>
        </table>
      </section>

      <footer class="text-center text-slate-600 text-xs mt-8">
        FOMO scans public news only. No Amazon-internal data is used or referenced.
      </footer>
    </div>
  </div>

<script>
const DATA = {payload};

/* ---------------- Intro animation ---------------- */
(function() {{
  const canvas = document.getElementById('introCanvas');
  const ctx = canvas.getContext('2d');
  function resize() {{ canvas.width = innerWidth; canvas.height = innerHeight; }}
  resize(); addEventListener('resize', resize);

  let t = 0;
  function drawRadar() {{
    t += 1;
    ctx.fillStyle = 'rgba(0,0,0,0.15)';
    ctx.fillRect(0,0,canvas.width,canvas.height);
    const cx = canvas.width/2, cy = canvas.height/2;
    const maxR = Math.max(canvas.width, canvas.height) * 0.7;
    for (let i=1;i<=4;i++) {{
      ctx.beginPath();
      ctx.arc(cx, cy, (maxR/4)*i, 0, Math.PI*2);
      ctx.strokeStyle = 'rgba(56,189,248,0.08)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }}
    const angle = (t * 0.03) % (Math.PI*2);
    const grad = ctx.createConicGradient ? ctx.createConicGradient(angle, cx, cy) : null;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angle);
    const sweep = ctx.createLinearGradient(0,0,maxR,0);
    sweep.addColorStop(0, 'rgba(56,189,248,0.35)');
    sweep.addColorStop(1, 'rgba(56,189,248,0)');
    ctx.fillStyle = sweep;
    ctx.beginPath();
    ctx.moveTo(0,0);
    ctx.arc(0,0,maxR, -0.25, 0.05);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
    requestAnimationFrame(drawRadar);
  }}
  drawRadar();

  const lines = [
    'INITIALIZING RISK RADAR...',
    'SCANNING GERMANY LOGISTICS NETWORK...',
    'CROSS-REFERENCING PUBLIC NEWS FEEDS...',
    'THREAT SIGNALS DETECTED.'
  ];
  const typedEl = document.getElementById('typedLine');
  let li = 0, ci = 0;
  function typeNext() {{
    if (li >= lines.length) return;
    const line = lines[li];
    if (ci <= line.length) {{
      typedEl.textContent = line.slice(0, ci);
      ci++;
      setTimeout(typeNext, 22);
    }} else {{
      li++; ci = 0;
      setTimeout(typeNext, 500);
    }}
  }}
  setTimeout(typeNext, 2100);

  function finishIntro() {{
    const intro = document.getElementById('intro');
    intro.style.transition = 'opacity 0.6s ease';
    intro.style.opacity = '0';
    setTimeout(() => {{
      intro.style.display = 'none';
      showPage('home');
      animateStats();
    }}, 600);
  }}
  document.getElementById('introSkip').addEventListener('click', finishIntro);
  setTimeout(finishIntro, 5200);
}})();

/* ---------------- Page routing ---------------- */
function showPage(name) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  if (name === 'app') renderApp();
}}
document.getElementById('enterBtn').addEventListener('click', () => showPage('app'));
document.getElementById('backHome').addEventListener('click', () => showPage('home'));

/* ---------------- Home stat counters ---------------- */
function animateStats() {{
  const total = DATA.signals.length;
  const critHigh = DATA.signals.filter(s => s.severity === 'critical' || s.severity === 'high').length;
  const sources = new Set(DATA.signals.map(s => s.source)).size;
  animateCount('statTotal', total);
  animateCount('statCritHigh', critHigh);
  animateCount('statSources', sources);
}}
function animateCount(id, target) {{
  const el = document.getElementById(id);
  let cur = 0;
  const step = Math.max(1, Math.ceil(target/40));
  const iv = setInterval(() => {{
    cur = Math.min(target, cur + step);
    el.textContent = cur;
    if (cur >= target) clearInterval(iv);
  }}, 25);
}}

/* ---------------- Dashboard rendering (date + filter aware) ---------------- */
let activeSeverity = 'all';
let activeCategory = 'all';
let activeDate = 'all';
let chartSev = null, chartCat = null;
let appInitialized = false;

function dateOf(s) {{ return (s.found_at || '').slice(0,10); }}

function populateDateSelect() {{
  const dates = [...new Set(DATA.signals.map(dateOf))].sort().reverse();
  const sel = document.getElementById('dateSelect');
  sel.innerHTML = '<option value="all">All time (' + DATA.signals.length + ' signals)</option>' +
    dates.map(d => {{
      const count = DATA.signals.filter(s => dateOf(s) === d).length;
      return `<option value="${{d}}">${{d}} (${{count}} new)</option>`;
    }}).join('');
  sel.addEventListener('change', () => {{ activeDate = sel.value; renderTableAndCharts(); }});
}}

function esc(s) {{
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}}

function getFiltered() {{
  return DATA.signals.filter(s =>
    (activeDate === 'all' || dateOf(s) === activeDate) &&
    (activeSeverity === 'all' || s.severity === activeSeverity) &&
    (activeCategory === 'all' || s.category === activeCategory)
  );
}}

function renderApp() {{
  document.getElementById('lastRunLbl').textContent = DATA.lastRun;
  document.getElementById('totalRunsLbl').textContent = DATA.totalRuns;
  if (!appInitialized) {{
    populateDateSelect();
    buildFilterButtons();
    appInitialized = true;
  }}
  renderTableAndCharts();
}}

function buildFilterButtons() {{
  const severities = ['critical','high','medium','low'].filter(s => DATA.signals.some(sig => sig.severity === s));
  const categories = [...new Set(DATA.signals.map(s => s.category))];

  const sevWrap = document.getElementById('sevFilters');
  sevWrap.innerHTML = '<span class="text-slate-400 text-sm mr-2">Severity:</span>' +
    '<button class="sev-filter px-3 py-1.5 rounded-full text-sm border border-sky-500 text-sky-400" data-value="all">ALL</button>' +
    severities.map(s => `<button class="sev-filter px-3 py-1.5 rounded-full text-sm border border-slate-600" style="color:${{DATA.severityColor[s]}}" data-value="${{s}}">${{s.toUpperCase()}}</button>`).join('');

  const catWrap = document.getElementById('catFilters');
  catWrap.innerHTML = '<span class="text-slate-400 text-sm mr-2">Category:</span>' +
    '<button class="cat-filter px-3 py-1.5 rounded-full text-sm border border-sky-500 text-sky-400" data-value="all">ALL</button>' +
    categories.map(c => `<button class="cat-filter px-3 py-1.5 rounded-full text-sm border border-slate-600 text-slate-300" data-value="${{esc(c)}}">${{esc(c)}}</button>`).join('');

  sevWrap.querySelectorAll('.sev-filter').forEach(btn => btn.addEventListener('click', () => {{
    activeSeverity = btn.dataset.value;
    sevWrap.querySelectorAll('.sev-filter').forEach(b => b.classList.remove('border-sky-500'));
    btn.classList.add('border-sky-500');
    renderTableAndCharts();
  }}));
  catWrap.querySelectorAll('.cat-filter').forEach(btn => btn.addEventListener('click', () => {{
    activeCategory = btn.dataset.value;
    catWrap.querySelectorAll('.cat-filter').forEach(b => b.classList.remove('border-sky-500'));
    btn.classList.add('border-sky-500');
    renderTableAndCharts();
  }}));
}}

function renderTableAndCharts() {{
  const filtered = getFiltered();
  const sevOrder = {{critical:0, high:1, medium:2, low:3}};
  filtered.sort((a,b) => (sevOrder[a.severity]??9) - (sevOrder[b.severity]??9));

  document.getElementById('kpiTotal').textContent = filtered.length;
  document.getElementById('kpiCritHigh').textContent = filtered.filter(s => s.severity==='critical'||s.severity==='high').length;
  document.getElementById('kpiCategories').textContent = new Set(filtered.map(s=>s.category)).size;
  document.getElementById('kpiSources').textContent = new Set(filtered.map(s=>s.source)).size;

  document.getElementById('dateHint').textContent = activeDate === 'all'
    ? '' : `Showing signals first found on ${{activeDate}}`;

  const tbody = document.getElementById('signalsBody');
  tbody.innerHTML = filtered.map(s => `
    <tr class="border-b border-slate-700 hover:bg-slate-800/60">
      <td class="px-4 py-3"><span class="inline-block px-2 py-1 rounded text-xs font-semibold text-white" style="background-color:${{DATA.severityColor[s.severity]||'#6b7280'}}">${{s.severity.toUpperCase()}}</span></td>
      <td class="px-4 py-3 text-slate-300 whitespace-nowrap">${{esc(s.category)}}</td>
      <td class="px-4 py-3"><a href="${{esc(s.link)}}" target="_blank" rel="noopener" class="text-sky-400 hover:text-sky-300 hover:underline">${{esc(s.title)}}</a></td>
      <td class="px-4 py-3 text-slate-400 whitespace-nowrap">${{esc(s.source)}}</td>
      <td class="px-4 py-3 text-slate-500 whitespace-nowrap text-sm">${{esc(s.pub_date||'')}}</td>
    </tr>`).join('');

  const sevCounts = {{}};
  filtered.forEach(s => sevCounts[s.severity] = (sevCounts[s.severity]||0)+1);
  const catCounts = {{}};
  filtered.forEach(s => catCounts[s.category] = (catCounts[s.category]||0)+1);

  if (chartSev) chartSev.destroy();
  if (chartCat) chartCat.destroy();

  chartSev = new Chart(document.getElementById('severityChart'), {{
    type: 'doughnut',
    data: {{
      labels: Object.keys(sevCounts).map(s=>s.toUpperCase()),
      datasets: [{{ data: Object.values(sevCounts), backgroundColor: Object.keys(sevCounts).map(s=>DATA.severityColor[s]||'#6b7280'), borderWidth:0 }}]
    }},
    options: {{ plugins: {{ legend: {{ labels: {{ color:'#cbd5e1' }} }} }} }}
  }});

  chartCat = new Chart(document.getElementById('categoryChart'), {{
    type: 'bar',
    data: {{ labels: Object.keys(catCounts), datasets: [{{ data: Object.values(catCounts), backgroundColor:'#0ea5e9', borderRadius:6 }}] }},
    options: {{
      indexAxis: 'y',
      plugins: {{ legend: {{ display:false }} }},
      scales: {{
        x: {{ ticks: {{ color:'#94a3b8' }}, grid: {{ color:'#1e293b' }} }},
        y: {{ ticks: {{ color:'#cbd5e1' }}, grid: {{ display:false }} }}
      }}
    }}
  }});
}}
</script>
</body>
</html>
"""
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written: {INDEX_PATH}")


if __name__ == "__main__":
    build()
