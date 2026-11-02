// Cenas animadas do FILE #003 (The American File). Gera youtube/taf/003-ordens-cpa-isis/anim/*.html.
// Precisa de: npm i d3-geo@3.1.1 topojson-client@3.1.0 world-atlas@2.0.2  (rode a partir de uma pasta com node_modules)
// Uso: node file003.js <pasta node_modules/..> <pasta de saída anim>
const fs = require("fs"), path = require("path");
const BASE = process.argv[2] || ".", OUT = process.argv[3] || "anim";
const d3 = require(path.resolve(BASE, "node_modules/d3-geo"));
const topo = require(path.resolve(BASE, "node_modules/topojson-client"));
const F = "../../../../gerador/youtube/fontes";
const W = 1920, H = 1080;
const C = { bg: "#0D1117", navy: "#1B3A6B", red: "#C0392B", paper: "#EDE6D6", muted: "#9AA4B2", land: "#1A2230", iraq: "#22314A", line: "#3A4A63" };
const css = `
@font-face{font-family:S;font-weight:400;src:url('${F}/source-serif-4-latin-400-normal.woff2')}
@font-face{font-family:S;font-weight:700;src:url('${F}/source-serif-4-latin-700-normal.woff2')}
@font-face{font-family:S;font-style:italic;font-weight:400;src:url('${F}/source-serif-4-latin-400-italic.woff2')}
@font-face{font-family:M;font-weight:500;src:url('${F}/ibm-plex-mono-latin-500-normal.woff2')}
@font-face{font-family:M;font-weight:700;src:url('${F}/ibm-plex-mono-latin-700-normal.woff2')}
body{margin:0;background:${C.bg}}
#c{width:${W}px;height:${H}px;position:relative;overflow:hidden;background:radial-gradient(1200px 700px at 25% 15%, rgba(27,58,107,.35), transparent 70%), ${C.bg};color:${C.paper};font-family:S}
.top{position:absolute;left:120px;right:120px;top:70px;display:flex;justify-content:space-between;font:500 26px M;letter-spacing:.18em;color:${C.muted};z-index:5}
.tt{position:absolute;left:120px;top:130px;z-index:5;max-width:900px}
.eyebrow{font:500 26px M;letter-spacing:.16em;color:${C.red}}
h1{margin:10px 0 0;font:700 70px S;line-height:1.04}
.src{position:absolute;left:120px;bottom:52px;font:500 22px M;color:${C.muted};letter-spacing:.04em;z-index:5}
svg text{font-family:M}
`;
const ease = `const E=x=>x<=0?0:x>=1?1:(1-Math.cos(Math.PI*x))/2; const seg=(t,a,b)=>E((t-a)/(b-a)); const show=(id,a)=>document.getElementById(id).style.opacity=a;`;
const page = (title, body, script) => `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title><style>${css}</style></head><body><div id="c">${body}</div><script>${ease}${script}</script></body></html>`;
const top = (p) => `<div class="top"><span>THE AMERICAN FILE</span><span>FILE #003 · ${p}</span></div>`;
fs.mkdirSync(OUT, { recursive: true });

// ---------- A: Ordem 2, faixa de estimativas (barras que crescem) ----------
{
  const rows = [["Bremer memo to Rumsfeld, June 2003", 230000, "~230,000"], ["Jay Garner", 400000, "300,000–400,000", 300000], ["The Guardian, May 24, 2003", 400000, "~400,000"], ["Charles Ferguson, No End in Sight", 500000, "~500,000"]];
  const x0 = 760, x1 = 1700, max = 500000, y0 = 420, gap = 130;
  const bars = rows.map((r, i) => {
    const y = y0 + i * gap, w = ((x1 - x0) * r[1]) / max, wl = r[3] ? ((x1 - x0) * r[3]) / max : null;
    return `<g id="b${i}" opacity="0"><text x="${x0 - 30}" y="${y + 38}" fill="${C.paper}" font-size="26" text-anchor="end">${r[0]}</text>
      <rect x="${x0}" y="${y}" width="${x1 - x0}" height="56" fill="${C.land}"/>
      ${wl ? `<rect id="r${i}l" x="${x0}" y="${y}" width="0" height="56" fill="${C.navy}" opacity=".55" data-w="${w}"/>` : ""}
      <rect id="r${i}" x="${x0}" y="${y}" width="0" height="56" fill="${i === 0 ? C.navy : C.red}" data-w="${wl || w}"/>
      <text id="t${i}" x="${x0 + 20}" y="${y + 38}" fill="${C.paper}" font-size="28" font-weight="700" data-w="${w}">${r[2]}</text></g>`;
  }).join("");
  const svg = `<svg width="${W}" height="${H}" style="position:absolute;inset:0">${bars}</svg>`;
  const body = `${top("PART 2")}<div class="tt" id="tt" style="opacity:0"><div class="eyebrow">CPA ORDER NUMBER 2 · MAY 23, 2003</div><h1>How many lost their jobs?</h1></div>${svg}
<div class="src">Estimates, not a count · Bremer: officers &amp; NCOs · Ferguson: all dissolved entities</div>`;
  const script = `window.DUR=10;
window.render=function(t){ show('tt',seg(t,0,1));
  for(let i=0;i<4;i++){ const a=1+i*1.8; show('b'+i,seg(t,a,a+0.4)); const r=document.getElementById('r'+i); const w=+r.dataset.w*seg(t,a+0.2,a+1.4); r.setAttribute('width',w);
    const rl=document.getElementById('r'+i+'l'); if(rl){ rl.setAttribute('width', +rl.dataset.w*seg(t,a+0.8,a+1.6)); }
    const tx=document.getElementById('t'+i); const ww=rl? +rl.dataset.w*seg(t,a+0.8,a+1.6) : w; tx.setAttribute('x', ${x0}+Math.max(ww,0)+20); tx.style.opacity=seg(t,a+1.0,a+1.5);} };`;
  fs.writeFileSync(path.join(OUT, "ordem2-estimativas.html"), page("Order 2", body, script));
}

// ---------- mapa do Iraque (base comum) ----------
const T = JSON.parse(fs.readFileSync(path.resolve(BASE, "node_modules/world-atlas/countries-50m.json")));
const paises = topo.feature(T, "countries").features.filter((f) => d3.geoArea(f) < 6);
const mesh = topo.mesh(T, T.objects.countries, (a, b) => a !== b);
function mapa(proj) {
  const p = d3.geoPath(proj);
  const iraq = paises.find((f) => f.properties.name === "Iraq");
  const syr = topo.mesh(T, T.objects.countries, (a, b) => (a.properties.name === "Iraq" && b.properties.name === "Syria") || (b.properties.name === "Iraq" && a.properties.name === "Syria"));
  return { p, base: `<path d="${p({ type: "FeatureCollection", features: paises })}" fill="${C.land}"/><path d="${p(iraq)}" fill="${C.iraq}"/><path d="${p(mesh)}" fill="none" stroke="${C.line}" stroke-width="2"/>`, syr: p(syr) };
}
const rot = (proj, lon, lat) => proj([lon, lat]).map((v) => +v.toFixed(1));
const nome = (proj, lon, lat, txt) => { const [x, y] = rot(proj, lon, lat); return `<text x="${x}" y="${y}" fill="${C.muted}" font-size="26" letter-spacing="6" text-anchor="middle" opacity=".8">${txt}</text>`; };
const ponto = (proj, id, lon, lat, txt, sub, cor, dx = 22, dy = 10, anc = "start") => { const [x, y] = rot(proj, lon, lat);
  return `<g id="${id}" opacity="0"><circle id="${id}r" cx="${x}" cy="${y}" r="12" fill="none" stroke="${cor}" stroke-width="4" opacity="0"/><circle cx="${x}" cy="${y}" r="10" fill="${cor}"/><text x="${x + dx}" y="${y + dy}" fill="${cor}" font-size="30" font-weight="700" text-anchor="${anc}">${txt}</text>${sub ? `<text x="${x + dx}" y="${y + dy + 34}" fill="${C.muted}" font-size="23" text-anchor="${anc}">${sub}</text>` : ""}</g>`; };
const pulso = (id, t0) => `{const r=document.getElementById('${id}r'); if(t>${t0}){const k=((t-${t0})*0.9)%1; r.setAttribute('r',12+k*42); r.style.opacity=1-k;}}`;

// ---------- B: Camp Bucca ----------
{
  const proj = d3.geoMercator().center([45.0, 32.6]).scale(3500).translate([W * 0.6, H * 0.6]).clipExtent([[-50, -50], [W + 50, H + 50]]);
  const m = mapa(proj);
  const svg = `<svg width="${W}" height="${H}" style="position:absolute;inset:0"><g id="map" opacity="0">${m.base}
  ${nome(proj, 43.6, 33.6, "IRAQ")}${nome(proj, 39.2, 34.8, "SYRIA")}${nome(proj, 47.9, 29.25, "KUWAIT")}${nome(proj, 49.6, 33.3, "IRAN")}${nome(proj, 42.5, 29.6, "SAUDI ARABIA")}</g>
  ${ponto(proj, "bag", 44.36, 33.31, "BAGHDAD", "", C.paper)}
  ${ponto(proj, "buc", 47.82, 30.07, "CAMP BUCCA", "near Umm Qasr · 2003–2009", C.red, -22, -40, "end")}
  </svg>`;
  const body = `${top("PART 5")}<div class="tt" id="tt" style="opacity:0"><div class="eyebrow">U.S. DETENTION FACILITY · 2003–2009</div><h1>Camp Bucca.</h1></div>${svg}
<div class="src">Map: Natural Earth (public domain) · Locations approximate</div>`;
  const script = `window.DUR=8;
window.render=function(t){ show('map',seg(t,0,1.2)); show('tt',seg(t,0.6,1.6)); show('bag',seg(t,1.6,2.2)); show('buc',seg(t,3.0,3.6)); ${pulso("buc", 3.6)} };`;
  fs.writeFileSync(path.join(OUT, "camp-bucca.html"), page("Camp Bucca", body, script));
}

// ---------- C: Mosul, junho de 2014 ----------
{
  const proj = d3.geoMercator().center([42.6, 34.2]).scale(3900).translate([W * 0.6, H * 0.58]).clipExtent([[-50, -50], [W + 50, H + 50]]);
  const m = mapa(proj);
  const svg = `<svg width="${W}" height="${H}" style="position:absolute;inset:0"><g id="map" opacity="0">${m.base}
  ${nome(proj, 43.4, 32.6, "IRAQ")}${nome(proj, 38.6, 35.4, "SYRIA")}${nome(proj, 36.9, 31.6, "JORDAN")}${nome(proj, 41.0, 37.65, "TURKEY")}</g>
  <path id="brd" d="${m.syr}" fill="none" stroke="${C.red}" stroke-width="5" stroke-dasharray="12 9"/>
  ${ponto(proj, "bag", 44.36, 33.31, "BAGHDAD", "", C.paper)}
  ${ponto(proj, "mos", 43.13, 36.34, "MOSUL", "June 10, 2014", C.red)}
  <g id="lb" opacity="0"><text x="${rot(proj, 40.0, 33.2)[0]}" y="${rot(proj, 40.0, 33.2)[1]}" fill="${C.red}" font-size="24" font-weight="700" text-anchor="middle">IRAQ–SYRIA BORDER</text></g>
  </svg>`;
  const body = `${top("PART 7")}<div class="tt" id="tt" style="opacity:0"><div class="eyebrow">JUNE 10, 2014</div><h1>Mosul falls.</h1></div>${svg}
<div class="src">Map: Natural Earth (public domain) · Borders as of 2014, approximate</div>`;
  const script = `const b=document.getElementById('brd'); const L=b.getTotalLength(); b.style.strokeDasharray=L; b.style.strokeDashoffset=L;
window.DUR=9;
window.render=function(t){ show('map',seg(t,0,1.2)); show('tt',seg(t,0.6,1.6)); show('bag',seg(t,1.4,2.0));
  b.style.strokeDasharray = t<4.4 ? L : '12 9'; b.style.strokeDashoffset = t<4.4 ? L*(1-seg(t,2.2,4.2)) : 0; show('lb',seg(t,3.6,4.2));
  show('mos',seg(t,5.0,5.6)); ${pulso("mos", 5.6)} };`;
  fs.writeFileSync(path.join(OUT, "mosul-2014.html"), page("Mosul 2014", body, script));
}

// ---------- D: a corrente 2003 → 2014 ----------
{
  const ev = [["2003", "Orders 1 & 2", "Party members purged, army dissolved"], ["2003–06", "Zarqawi's strategy", "Sectarian war by design"], ["2004–09", "Camp Bucca", "Networks formed behind the wire"],
    ["2007–08", "The Awakening", "Promises half kept"], ["2011", "U.S. exit", "Last troops leave Dec. 18"], ["2012–13", "Maliki's crackdown", "Sunni protests met with force"],
    ["2011–14", "Syria's war", "Money, weapons, territory"], ["JUNE 2014", "“Caliphate”", "Declared June 29"]];
  const x0 = 140, x1 = 1780, y = 600, xs = ev.map((_, i) => x0 + (i * (x1 - x0)) / (ev.length - 1));
  const items = ev.map((e, i) => { const up = i % 2 === 0, last = i === ev.length - 1;
    return `<div id="e${i}" style="position:absolute;left:${xs[i] - 130}px;width:260px;${up ? `bottom:${H - y + 46}px` : `top:${y + 46}px`};opacity:0;text-align:center">
      <div style="font:700 28px M;color:${last ? C.red : C.muted};letter-spacing:.06em">${e[0]}</div>
      <div style="font:700 30px S;line-height:1.12;margin-top:6px">${e[1]}</div>
      <div style="font:400 22px S;font-style:italic;color:${C.muted};margin-top:6px;line-height:1.25">${e[2]}</div></div>
      <div id="d${i}" style="position:absolute;left:${xs[i] - 22}px;top:${y - 22}px;width:44px;height:44px;border-radius:50%;box-sizing:border-box;border:6px solid ${last ? C.red : C.paper};background:${C.bg};transform:scale(0)"></div>`; }).join("");
  const body = `${top("PART 8")}<div class="tt" id="tt" style="opacity:0"><div class="eyebrow">MAY 2003 → JUNE 2014</div><h1>The chain.</h1></div>
<div id="bar" style="position:absolute;left:${x0}px;top:${y - 4}px;height:8px;width:0;background:repeating-linear-gradient(90deg, ${C.navy} 0 34px, transparent 34px 44px)"></div>${items}
<div class="src">No single link made ISIS. Each one made the next easier. (Our reading.)</div>`;
  const script = `window.DUR=14;
window.render=function(t){ show('tt',seg(t,0,1)); document.getElementById('bar').style.width=(${x1 - x0}*seg(t,0.6,12))+'px';
  for(let i=0;i<${ev.length};i++){ const a=0.6+(i/${ev.length - 1})*11.4; document.getElementById('d'+i).style.transform='scale('+seg(t,a-0.2,a+0.3)+')';
    const e=document.getElementById('e'+i); e.style.opacity=seg(t,a,a+0.6); e.style.transform='translateY('+(1-seg(t,a,a+0.6))*20+'px)'; } };`;
  fs.writeFileSync(path.join(OUT, "a-corrente.html"), page("The chain", body, script));
}
console.log("ok");
