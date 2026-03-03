"""
generar_web.py - NAFTABOT
Genera docs/index.html con filtros interactivos.
vigentes.json -> tabla de precios actuales (liviano, carga rapido)
stats.json    -> grafico historico (carga lazy al filtrar)
"""
import json
from pathlib import Path
from datetime import datetime

DIR_DATA = Path("data")
DIR_DOCS = Path("docs")

def leer(n):
    p = DIR_DATA / n
    return json.load(open(p, encoding="utf-8")) if p.exists() else None

def fmt_pct(v):
    if v is None: return "—"
    return ("+" if v > 0 else "") + f"{v:.2f}%"

def color_pct(v):
    if v is None: return "#999"
    return "#dc2626" if v > 0 else "#16a34a" if v < 0 else "#999"

def main():
    DIR_DOCS.mkdir(exist_ok=True)
    resumen = leer("resumen.json") or {}
    filtros = leer("filtros.json") or {}

    fecha_str    = datetime.now().strftime("%d/%m/%Y %H:%M")
    fecha_act    = resumen.get("fecha_actualizacion","—")
    dolar        = resumen.get("dolar_bn", 1)
    total_reg    = resumen.get("total_registros", 0)
    total_est    = resumen.get("total_estaciones", 0)
    prov_count   = resumen.get("provincias_count", 0)
    emp_count    = resumen.get("empresas_count", 0)
    precios_prom = resumen.get("precios_promedio", {})
    vars_dia     = resumen.get("variaciones_dia", {})

    filtros_js = json.dumps(filtros, ensure_ascii=False)
    resumen_js = json.dumps(resumen, ensure_ascii=False)

    prod_cards = ""
    for prod, precio in list(precios_prom.items())[:8]:
        v = vars_dia.get(prod)
        nombre_corto = prod.replace("Nafta","Naf.").replace("entre","").replace(" Ron","").replace("  "," ").strip()[:28]
        prod_cards += f"""<div class="pcard">
  <div class="pcard-name">{nombre_corto}</div>
  <div class="pcard-price">${precio:,.0f}</div>
  <div class="pcard-var" style="color:{color_pct(v)}">{fmt_pct(v)}</div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>¿Subió la Nafta? — Dashboard Nacional</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#fafaf8;--white:#ffffff;--border:#e4e4e0;--border2:#ccccc8;
  --text:#181816;--muted:#88887f;--light:#f2f2ee;
  --accent:#16a34a;--red:#dc2626;--blue:#2563eb;--radius:10px;
}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;font-size:14px;line-height:1.5;}}
header{{background:var(--white);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;position:sticky;top:0;z-index:100;}}
.brand{{display:flex;align-items:center;gap:0.6rem;}}
.brand-icon{{font-size:1.4rem;}}
.brand h1{{font-family:'DM Mono',monospace;font-size:0.95rem;font-weight:500;letter-spacing:0.03em;}}
.brand-sub{{font-size:0.72rem;color:var(--muted);font-weight:300;}}
.header-meta{{font-family:'DM Mono',monospace;font-size:0.68rem;color:var(--muted);text-align:right;}}
.container{{max-width:1180px;margin:0 auto;padding:1.5rem 1.5rem 4rem;}}
.national-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-bottom:1.5rem;}}
.ncard{{background:var(--white);padding:1rem 1.25rem;}}
.ncard .label{{font-size:0.62rem;text-transform:uppercase;letter-spacing:0.12em;color:var(--muted);font-weight:500;margin-bottom:0.35rem;}}
.ncard .value{{font-family:'DM Mono',monospace;font-size:1.5rem;font-weight:500;}}
.ncard .sub{{font-size:0.7rem;color:var(--muted);margin-top:0.2rem;font-weight:300;}}
.products-scroll{{display:flex;gap:0.75rem;overflow-x:auto;padding-bottom:0.5rem;margin-bottom:1.5rem;scrollbar-width:thin;}}
.pcard{{background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:0.9rem 1.1rem;min-width:160px;flex-shrink:0;}}
.pcard-name{{font-size:0.68rem;color:var(--muted);font-weight:500;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.4rem;line-height:1.3;}}
.pcard-price{{font-family:'DM Mono',monospace;font-size:1.3rem;font-weight:500;margin-bottom:0.2rem;}}
.pcard-var{{font-family:'DM Mono',monospace;font-size:0.8rem;font-weight:500;}}
.filters-section{{background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem 1.5rem;margin-bottom:1.5rem;}}
.filters-title{{font-size:0.65rem;text-transform:uppercase;letter-spacing:0.14em;color:var(--muted);font-weight:500;margin-bottom:1rem;}}
.filters-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:0.75rem;}}
.filter-group label{{display:block;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);font-weight:500;margin-bottom:0.3rem;}}
.filter-group select{{width:100%;padding:0.5rem 0.75rem;border:1px solid var(--border);border-radius:6px;background:var(--white);color:var(--text);font-family:'DM Sans',sans-serif;font-size:0.83rem;appearance:none;cursor:pointer;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 0.6rem center;}}
.filter-group select:focus{{outline:none;border-color:var(--blue);}}
.btn{{padding:0.5rem 1rem;border-radius:6px;border:none;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:0.83rem;font-weight:500;transition:all 0.15s;}}
.btn-primary{{background:var(--text);color:var(--white);}}
.btn-primary:hover{{background:#333;}}
.btn-ghost{{background:transparent;color:var(--muted);border:1px solid var(--border);}}
.btn-ghost:hover{{border-color:var(--border2);color:var(--text);}}
.results-section{{display:none;}}
.results-section.visible{{display:block;}}
.section-title{{font-size:0.65rem;text-transform:uppercase;letter-spacing:0.14em;color:var(--muted);font-weight:500;margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem;}}
.section-title::after{{content:'';flex:1;height:1px;background:var(--border);}}
.chart-card{{background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1.5rem;}}
.chart-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:0.5rem;}}
.chart-title{{font-size:0.83rem;font-weight:500;}}
.chart-sub{{font-size:0.72rem;color:var(--muted);}}
.chart-wrap{{height:260px;position:relative;}}
.chart-loading{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:0.8rem;gap:0.5rem;}}
.period-tabs{{display:flex;gap:0.2rem;}}
.period-tab{{padding:0.2rem 0.55rem;border-radius:5px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:0.7rem;font-family:'DM Mono',monospace;}}
.period-tab.active{{background:var(--text);color:var(--white);border-color:var(--text);}}
.table-card{{background:var(--white);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-bottom:1.5rem;}}
table{{width:100%;border-collapse:collapse;font-size:0.83rem;}}
th{{padding:0.6rem 1rem;text-align:left;font-size:0.62rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);font-weight:500;background:var(--light);border-bottom:1px solid var(--border);}}
td{{padding:0.6rem 1rem;border-bottom:1px solid var(--border);}}
tr:last-child td{{border-bottom:none;}}
tr:hover td{{background:var(--bg);}}
.tag{{display:inline-block;padding:0.15rem 0.45rem;border-radius:4px;font-size:0.68rem;background:var(--light);color:var(--muted);font-family:'DM Mono',monospace;}}
.up{{color:#dc2626;font-family:'DM Mono',monospace;font-weight:500;}}
.dn{{color:#16a34a;font-family:'DM Mono',monospace;font-weight:500;}}
.neu{{color:var(--muted);font-family:'DM Mono',monospace;}}
.mono{{font-family:'DM Mono',monospace;}}
.spinner{{display:inline-block;width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--text);border-radius:50%;animation:spin 0.6s linear infinite;}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@media(max-width:700px){{.national-grid{{grid-template-columns:repeat(2,1fr);}}header{{padding:0.75rem 1rem;}}.container{{padding:1rem 1rem 3rem;}}.filters-grid{{grid-template-columns:1fr 1fr;}}}}
footer{{text-align:center;padding:2rem;color:var(--muted);font-size:0.68rem;border-top:1px solid var(--border);font-family:'DM Mono',monospace;letter-spacing:0.05em;}}
</style>
</head>
<body>
<header>
  <div class="brand">
    <span class="brand-icon">⛽</span>
    <div>
      <h1>¿SUBIÓ LA NAFTA?</h1>
      <div class="brand-sub">Precios en surtidor — Argentina</div>
    </div>
  </div>
  <div class="header-meta">Actualizado: {fecha_str}<br>Datos: {fecha_act} · Dólar BN: ${dolar:,.0f}</div>
</header>

<div class="container">
  <div class="national-grid">
    <div class="ncard"><div class="label">Estaciones</div><div class="value">{total_est:,}</div><div class="sub">{prov_count} provincias</div></div>
    <div class="ncard"><div class="label">Empresas</div><div class="value">{emp_count}</div><div class="sub">marcas activas</div></div>
    <div class="ncard"><div class="label">Registros hoy</div><div class="value">{total_reg:,}</div><div class="sub">precios vigentes</div></div>
    <div class="ncard"><div class="label">Dólar BN</div><div class="value mono">${dolar:,.0f}</div><div class="sub">ARS — Banco Nación</div></div>
  </div>

  <div class="section-title">Precios promedio nacionales</div>
  <div class="products-scroll">{prod_cards}</div>

  <div class="filters-section">
    <div class="filters-title">🔍 Filtrar por criterio</div>
    <div class="filters-grid">
      <div class="filter-group"><label>Provincia</label><select id="sel-prov" onchange="onProvChange()"><option value="">Todas</option></select></div>
      <div class="filter-group"><label>Localidad</label><select id="sel-loc"><option value="">Todas</option></select></div>
      <div class="filter-group"><label>Combustible</label><select id="sel-prod"><option value="">Todos</option></select></div>
      <div class="filter-group"><label>Empresa / Bandera</label><select id="sel-emp"><option value="">Todas</option></select></div>
    </div>
    <div style="margin-top:0.85rem;display:flex;gap:0.5rem;">
      <button class="btn btn-primary" onclick="aplicarFiltro()">Ver precios</button>
      <button class="btn btn-ghost" onclick="resetFiltros()">Limpiar</button>
    </div>
  </div>

  <div class="results-section" id="results">
    <div class="section-title">Precios actuales</div>
    <div class="table-card">
      <table>
        <thead><tr><th>Empresa</th><th>Producto</th><th>Precio ARS</th><th>Precio USD</th><th>Var. día</th><th>Provincia</th><th>Localidad</th></tr></thead>
        <tbody id="tabla-precios"></tbody>
      </table>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;margin-bottom:1.5rem;">
      <div class="table-card">
        <div style="padding:0.75rem 1rem;font-size:0.7rem;font-weight:500;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);border-bottom:1px solid var(--border);">↑ Más caros</div>
        <table><thead><tr><th>#</th><th>Empresa</th><th>Localidad</th><th>Precio</th></tr></thead><tbody id="rank-caros"></tbody></table>
      </div>
      <div class="table-card">
        <div style="padding:0.75rem 1rem;font-size:0.7rem;font-weight:500;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);border-bottom:1px solid var(--border);">↓ Más baratos</div>
        <table><thead><tr><th>#</th><th>Empresa</th><th>Localidad</th><th>Precio</th></tr></thead><tbody id="rank-baratos"></tbody></table>
      </div>
    </div>

    <div class="section-title">Evolución histórica</div>
    <div class="chart-card">
      <div class="chart-header">
        <div><div class="chart-title" id="chart-title">—</div><div class="chart-sub" id="chart-sub"></div></div>
        <div class="period-tabs" id="ptabs">
          <button class="period-tab active" onclick="cambiarPeriodo(30,this)">30d</button>
          <button class="period-tab" onclick="cambiarPeriodo(90,this)">90d</button>
          <button class="period-tab" onclick="cambiarPeriodo(180,this)">6m</button>
          <button class="period-tab" onclick="cambiarPeriodo(9999,this)">Todo</button>
        </div>
      </div>
      <div class="chart-wrap">
        <div class="chart-loading" id="chart-loading" style="display:none"><span class="spinner"></span> Cargando histórico...</div>
        <canvas id="chartMain"></canvas>
      </div>
    </div>
  </div>
</div>
<footer>datos: datos.energia.gob.ar · naftabot · actualización diaria via github actions</footer>

<script>
const FILTROS = {filtros_js};
const RESUMEN = {resumen_js};
const DOLAR = RESUMEN.dolar_bn || 1;

// ── Poblar selects ────────────────────────────────────────────────────────────
function poblarSelect(id, opciones, placeholder) {{
  const sel = document.getElementById(id);
  sel.innerHTML = `<option value="">${{placeholder}}</option>`;
  opciones.forEach(o => {{ const op = document.createElement('option'); op.value=o; op.textContent=o; sel.appendChild(op); }});
}}
poblarSelect('sel-prov', FILTROS.provincias||[], 'Todas');
poblarSelect('sel-prod', FILTROS.productos ||[], 'Todos');
poblarSelect('sel-emp',  FILTROS.empresas  ||[], 'Todas');
poblarSelect('sel-loc',  FILTROS.localidades||[],'Todas');

function onProvChange() {{
  // podria filtrar localidades — por ahora muestra todas
}}
function resetFiltros() {{
  ['sel-prov','sel-loc','sel-prod','sel-emp'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('results').classList.remove('visible');
}}

// ── Vigentes: carga directa del JSON liviano ─────────────────────────────────
let vigentesData = null;
async function cargarVigentes() {{
  if (vigentesData) return vigentesData;
  const res = await fetch('data/vigentes.json');
  vigentesData = await res.json();
  return vigentesData;
}}

// ── Stats historicos: carga lazy ──────────────────────────────────────────────
let statsData = null;
async function cargarStats() {{
  if (statsData) return statsData;
  const res = await fetch('data/stats.json');
  statsData = await res.json();
  return statsData;
}}

// ── Aplicar filtro ────────────────────────────────────────────────────────────
let filtroActual = {{}};
let periodoActual = 30;
let mainChart = null;

async function aplicarFiltro() {{
  filtroActual = {{
    prov: document.getElementById('sel-prov').value,
    loc:  document.getElementById('sel-loc').value,
    prod: document.getElementById('sel-prod').value,
    emp:  document.getElementById('sel-emp').value,
  }};
  document.getElementById('results').classList.add('visible');
  document.getElementById('tabla-precios').innerHTML =
    '<tr><td colspan="7" style="text-align:center;padding:1.5rem;color:var(--muted)"><span class="spinner"></span> Cargando...</td></tr>';

  // 1. Tabla de precios vigentes (rapida)
  const vigentes = await cargarVigentes();
  renderTabla(vigentes);

  // 2. Grafico historico (lazy, puede tardar)
  renderChartAsync();
}}

// ── Tabla de precios vigentes ─────────────────────────────────────────────────
function filtrarVigentes(vigentes) {{
  const {{prov,loc,prod,emp}} = filtroActual;
  return vigentes.filter(r =>
    (!prov || r.provincia === prov) &&
    (!loc  || r.localidad === loc)  &&
    (!prod || r.producto  === prod) &&
    (!emp  || r.empresabandera === emp)
  );
}}

function renderTabla(vigentes) {{
  const rows = filtrarVigentes(vigentes);
  const tbody = document.getElementById('tabla-precios');
  if (!rows.length) {{
    tbody.innerHTML='<tr><td colspan="7" style="text-align:center;padding:1.5rem;color:var(--muted)">Sin datos para este filtro</td></tr>';
    document.getElementById('rank-caros').innerHTML='';
    document.getElementById('rank-baratos').innerHTML='';
    return;
  }}
  const sorted = [...rows].sort((a,b)=>b.precio-a.precio);
  tbody.innerHTML = sorted.slice(0,100).map(r => {{
    const v = r.var_dia;
    const vcls = v===null?'neu':v>0?'up':'dn';
    const vstr = v===null?'—':(v>0?'+':'')+v.toFixed(2)+'%';
    return `<tr>
      <td><span class="tag">${{r.empresabandera}}</span></td>
      <td style="font-size:0.78rem">${{r.producto}}</td>
      <td class="mono">${{Number(r.precio).toLocaleString('es-AR')}}</td>
      <td class="mono" style="color:var(--muted)">U$S ${{(r.precio/DOLAR).toFixed(2)}}</td>
      <td class="${{vcls}}">${{vstr}}</td>
      <td style="color:var(--muted);font-size:0.78rem">${{r.provincia}}</td>
      <td style="color:var(--muted);font-size:0.78rem">${{r.localidad}}</td>
    </tr>`;
  }}).join('');

  // Rankings
  const caros   = sorted.slice(0,8);
  const baratos = [...rows].sort((a,b)=>a.precio-b.precio).slice(0,8);
  document.getElementById('rank-caros').innerHTML   = caros.map((r,i)=>`<tr><td class="mono" style="color:var(--muted)">${{i+1}}</td><td><span class="tag">${{r.empresabandera}}</span></td><td style="color:var(--muted);font-size:0.78rem">${{r.localidad}}</td><td class="mono up">${{Number(r.precio).toLocaleString('es-AR')}}</td></tr>`).join('');
  document.getElementById('rank-baratos').innerHTML = baratos.map((r,i)=>`<tr><td class="mono" style="color:var(--muted)">${{i+1}}</td><td><span class="tag">${{r.empresabandera}}</span></td><td style="color:var(--muted);font-size:0.78rem">${{r.localidad}}</td><td class="mono dn">${{Number(r.precio).toLocaleString('es-AR')}}</td></tr>`).join('');
}}

// ── Grafico historico ─────────────────────────────────────────────────────────
const COLORS=['#2563eb','#dc2626','#16a34a','#d97706','#7c3aed','#0891b2','#db2777','#65a30d','#ea580c','#0d9488'];
let colorIdx=0; const cmap={{}};
function getColor(e){{ if(!cmap[e]) cmap[e]=COLORS[colorIdx++%COLORS.length]; return cmap[e]; }}

async function renderChartAsync() {{
  const {{prov,loc,prod,emp}} = filtroActual;
  document.getElementById('chart-title').textContent = prod||'Todos los combustibles';
  document.getElementById('chart-sub').textContent   = [emp||'Todas las empresas', loc||prov||'Argentina'].join(' · ');
  document.getElementById('chart-loading').style.display='flex';
  if(mainChart){{ mainChart.destroy(); mainChart=null; }}

  const stats = await cargarStats();
  document.getElementById('chart-loading').style.display='none';

  const series = getSerie(stats);
  renderChart(series);
}}

function getSerie(stats) {{
  const {{prov,prod,emp,loc}} = filtroActual;
  const series = {{}};
  const provKeys = prov ? [prov] : Object.keys(stats);
  for (const p of provKeys) {{
    if (!stats[p]) continue;
    const prodKeys = prod ? [prod] : Object.keys(stats[p]);
    for (const pr of prodKeys) {{
      if (!stats[p][pr]) continue;
      const empKeys = emp ? [emp] : Object.keys(stats[p][pr]);
      for (const e of empKeys) {{
        if (!series[e]) series[e] = {{}};
        for (const entry of (stats[p][pr][e]||[])) {{
          if (loc && entry.localidad!==loc) continue;
          if (!series[e][entry.fecha]) series[e][entry.fecha]=[];
          series[e][entry.fecha].push(entry.precio);
        }}
      }}
    }}
  }}
  return series;
}}

function filtrarPeriodo(series, dias) {{
  if (dias>=9999) return series;
  const cutoff=new Date(); cutoff.setDate(cutoff.getDate()-dias);
  const cut=cutoff.toISOString().slice(0,10);
  const out={{}};
  for(const [e,fechas] of Object.entries(series)){{
    out[e]={{}};
    for(const [f,v] of Object.entries(fechas)) if(f>=cut) out[e][f]=v;
  }}
  return out;
}}

function renderChart(series) {{
  const filtered=filtrarPeriodo(series,periodoActual);
  const allFechas=[...new Set(Object.values(filtered).flatMap(f=>Object.keys(f)))].sort();
  if(!allFechas.length) return;
  const datasets=Object.entries(filtered).slice(0,10).map(([e,fechas])=>{{
    return {{label:e,data:allFechas.map(f=>{{const v=fechas[f];return v?Math.round(v.reduce((a,b)=>a+b,0)/v.length):null;}}),
      borderColor:getColor(e),backgroundColor:'transparent',borderWidth:2,
      pointRadius:allFechas.length>60?0:3,tension:0.3,spanGaps:true}};
  }});
  if(mainChart) mainChart.destroy();
  mainChart=new Chart(document.getElementById('chartMain').getContext('2d'),{{
    type:'line',data:{{labels:allFechas,datasets}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{display:datasets.length<=8,labels:{{color:'#888',font:{{size:11}},boxWidth:10,padding:10}}}},
        tooltip:{{backgroundColor:'#18181a',titleColor:'#fff',bodyColor:'#ccc',padding:10}}}},
      scales:{{
        x:{{ticks:{{color:'#aaa',maxTicksLimit:8,font:{{size:10}}}},grid:{{color:'#f0f0ec'}}}},
        y:{{ticks:{{color:'#aaa',callback:v=>'$'+Number(v).toLocaleString('es-AR'),font:{{size:10}}}},grid:{{color:'#f0f0ec'}}}}
      }}
    }}
  }});
}}

function cambiarPeriodo(dias,btn) {{
  periodoActual=dias;
  document.querySelectorAll('#ptabs .period-tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  if(statsData) renderChart(getSerie(statsData));
  else renderChartAsync();
}}
</script>
</body></html>"""

    with open(DIR_DOCS / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Web NAFTABOT generada: docs/index.html")

if __name__ == "__main__":
    main()
