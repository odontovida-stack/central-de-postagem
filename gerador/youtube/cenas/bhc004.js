// Gera as cenas animadas (HTML + SVG) do BHC #004. Cada cena expõe window.render(t) com t em segundos.
const fs = require("fs");
const d3 = require("d3-geo");
const topo = require("topojson-client");
const F = "/home/claude/central-de-postagem/gerador/youtube/fontes";
const W = 1920, H = 1080;
const C = { bg: "#15110C", deep: "#5A4426", gold: "#C9A227", paper: "#F1E6CF", muted: "#A89A84", red: "#C8402E", sea: "#17120C", land: "#3B2F21" };
const css = `
@font-face{font-family:S;font-weight:400;src:url('file://${F}/source-serif-4-latin-400-normal.woff2')}
@font-face{font-family:S;font-weight:700;src:url('file://${F}/source-serif-4-latin-700-normal.woff2')}
@font-face{font-family:S;font-style:italic;font-weight:400;src:url('file://${F}/source-serif-4-latin-400-italic.woff2')}
@font-face{font-family:M;font-weight:500;src:url('file://${F}/ibm-plex-mono-latin-500-normal.woff2')}
@font-face{font-family:M;font-weight:700;src:url('file://${F}/ibm-plex-mono-latin-700-normal.woff2')}
body{margin:0;background:${C.bg}}
#c{width:${W}px;height:${H}px;position:relative;overflow:hidden;background:radial-gradient(1200px 700px at 30% 20%, rgba(90,68,38,.35), transparent 70%), ${C.bg};color:${C.paper};font-family:S}
.top{position:absolute;left:120px;right:120px;top:70px;display:flex;justify-content:space-between;font:500 26px M;letter-spacing:.18em;color:${C.muted};z-index:5}
.tt{position:absolute;left:120px;top:130px;z-index:5}
.eyebrow{font:500 26px M;letter-spacing:.16em;color:${C.gold}}
h1{margin:10px 0 0;font:700 76px S;line-height:1.02}
.src{position:absolute;left:120px;bottom:52px;font:500 22px M;color:${C.muted};letter-spacing:.04em;z-index:5}
svg text{font-family:M}
`;
const land = (res) => topo.feature(JSON.parse(fs.readFileSync(`node_modules/world-atlas/land-${res}.json`)), "land");
const ease = `const E=x=>x<=0?0:x>=1?1:(1-Math.cos(Math.PI*x))/2; const seg=(t,a,b)=>E((t-a)/(b-a));`;

function page(title, body, script) {
  return `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title><style>${css}</style></head><body><div id="c">${body}</div><script>${ease}${script}</script></body></html>`;
}

// ---------- Cena 1: Florida – Cuba ----------
{
  const T = JSON.parse(fs.readFileSync("node_modules/world-atlas/countries-10m.json"));
  const L = { type: "FeatureCollection", features: topo.feature(T, "countries").features.filter((f) => d3.geoArea(f) < 6) };
  const proj = d3.geoMercator().center([-80.6, 23.6]).scale(6200).translate([W * 0.56, H * 0.56]).clipExtent([[-50, -50], [W + 50, H + 50]]);
  const path = d3.geoPath(proj);
  const P = (lon, lat) => proj([lon, lat]).map((v) => v.toFixed(1));
  const kw = P(-81.78, 24.555), hav = P(-82.366, 23.136), banes = P(-75.72, 20.96), mia = P(-80.19, 25.76);
  const svg = `<svg width="${W}" height="${H}" style="position:absolute;inset:0">
  <defs><clipPath id="cl"><rect width="${W}" height="${H}"/></clipPath></defs>
  <g id="map" clip-path="url(#cl)" opacity="0"><path d="${path(L)}" fill="${C.land}" stroke="${C.deep}" stroke-width="2"/></g>
  <g id="kw" opacity="0"><circle cx="${kw[0]}" cy="${kw[1]}" r="11" fill="${C.paper}"/><text x="${+kw[0] - 22}" y="${+kw[1] - 26}" fill="${C.paper}" font-size="30" text-anchor="end" font-weight="700">KEY WEST</text></g>
  <g id="mia" opacity="0"><circle cx="${mia[0]}" cy="${mia[1]}" r="8" fill="${C.muted}"/><text x="${+mia[0] + 20}" y="${+mia[1] + 10}" fill="${C.muted}" font-size="24">Miami</text></g>
  <g id="hav" opacity="0"><circle cx="${hav[0]}" cy="${hav[1]}" r="11" fill="${C.gold}"/><text x="${+hav[0] + 24}" y="${+hav[1] + 44}" fill="${C.gold}" font-size="30" font-weight="700">HAVANA</text></g>
  <line id="ln" x1="${kw[0]}" y1="${kw[1]}" x2="${hav[0]}" y2="${hav[1]}" stroke="${C.gold}" stroke-width="5" stroke-dasharray="14 10"/>
  <g id="mi" opacity="0"><rect x="${+kw[0] - 300}" y="${(+kw[1] + +hav[1]) / 2 - 34}" width="250" height="64" rx="8" fill="${C.bg}" stroke="${C.gold}" stroke-width="3"/><text x="${+kw[0] - 175}" y="${(+kw[1] + +hav[1]) / 2 + 12}" fill="${C.paper}" font-size="34" font-weight="700" text-anchor="middle">~90 MILES</text></g>
  <g id="ba" opacity="0"><circle id="bar" cx="${banes[0]}" cy="${banes[1]}" r="12" fill="none" stroke="${C.red}" stroke-width="4"/><circle cx="${banes[0]}" cy="${banes[1]}" r="9" fill="${C.red}"/><text x="${banes[0]}" y="${+banes[1] + 60}" fill="${C.red}" font-size="26" font-weight="700" text-anchor="middle">BANES · U-2 SHOT DOWN</text><text x="${banes[0]}" y="${+banes[1] + 92}" fill="${C.muted}" font-size="22" text-anchor="middle">Oct. 27, ~10:20 a.m.</text></g>
</svg>`;
  const body = `<div class="top"><span>BEFORE HISTORY CHANGED</span><span>#004 · PART 1</span></div>
<div class="tt" id="tt" style="opacity:0"><div class="eyebrow">THE STRAITS OF FLORIDA · OCTOBER 1962</div><h1>Cuba.</h1></div>${svg}
<div class="src">Map: Natural Earth (public domain) · Distance approximate</div>`;
  const script = `
const ln=document.getElementById('ln'); const len=Math.hypot(ln.x2.baseVal.value-ln.x1.baseVal.value, ln.y2.baseVal.value-ln.y1.baseVal.value);
window.DUR=9;
window.render=function(t){
  const z=1+0.05*seg(t,0,9); document.getElementById('map').setAttribute('transform','translate(${W / 2} ${H / 2}) scale('+z+') translate(-${W / 2} -${H / 2})');
  document.getElementById('map').style.opacity=seg(t,0,1.2);
  document.getElementById('tt').style.opacity=seg(t,0.6,1.6);
  document.getElementById('mia').style.opacity=0.8*seg(t,1.2,1.8);
  document.getElementById('kw').style.opacity=seg(t,1.4,2.0);
  document.getElementById('hav').style.opacity=seg(t,1.8,2.4);
  const p=seg(t,2.4,4.2); ln.style.strokeDasharray=(len*p)+' '+len; ln.style.opacity=p>0?1:0;
  document.getElementById('mi').style.opacity=seg(t,4.0,4.6);
  document.getElementById('ba').style.opacity=seg(t,5.6,6.2);
  const r=12+((t*1.2)%1)*40*(t>6.2?1:0); const br=document.getElementById('bar'); br.setAttribute('r',r); br.style.opacity=t>6.2?1-((t*1.2)%1):0;
};`;
  fs.writeFileSync("cena1.html", page("Florida Cuba", body, script));
}

// ---------- Cena 2: a rota do U-2 de Maultsby (polar) ----------
{
  const L = land("50m");
  const proj = d3.geoOrthographic().rotate([150, -78, 0]).scale(1250).translate([W * 0.6, H * 0.6]).clipAngle(90);
  const path = d3.geoPath(proj);
  const grat = d3.geoGraticule().step([30, 10])();
  const pts = { eielson: [-147.1, 64.67], pole: [0, 89.9], chuk: [178, 66.5], kotz: [-162.6, 66.9] };
  const P = (k) => proj(pts[k]).map((v) => +v.toFixed(1));
  // rota ilustrativa: Eielson -> polo -> desvio a oeste -> Chukotka -> Kotzebue
  const route = { type: "LineString", coordinates: [pts.eielson, [-150, 75], [-140, 85], pts.pole, [150, 84], [168, 74], pts.chuk, [-172, 66.8], pts.kotz] };
  const lbl = (k, txt, dx, dy, col, anchor = "start") => { const [x, y] = P(k); return `<g id="p_${k}" opacity="0"><circle cx="${x}" cy="${y}" r="10" fill="${col}"/><text x="${x + dx}" y="${y + dy}" fill="${col}" font-size="27" font-weight="700" text-anchor="${anchor}">${txt}</text></g>`; };
  const svg = `<svg width="${W}" height="${H}" style="position:absolute;inset:0">
  <g id="map" opacity="0"><path d="${path({ type: "Sphere" })}" fill="${C.sea}" stroke="${C.deep}" stroke-width="2"/><path d="${path(grat)}" fill="none" stroke="${C.deep}" stroke-width="1" opacity=".5"/><path d="${path(L)}" fill="${C.land}" stroke="${C.deep}" stroke-width="1.5"/></g>
  <path id="rt" d="${path(route)}" fill="none" stroke="${C.gold}" stroke-width="5" stroke-linecap="round"/>
  ${lbl("eielson", "EIELSON AFB, ALASKA", 22, 8, C.paper)}
  ${lbl("pole", "NORTH POLE", 20, -18, C.paper)}
  ${lbl("chuk", "CHUKOTKA · SOVIET AIRSPACE", -20, 46, C.red, "end")}
  ${lbl("kotz", "KOTZEBUE · GLIDES IN", 24, -18, C.gold)}
</svg>`;
  const body = `<div class="top"><span>BEFORE HISTORY CHANGED</span><span>#004 · PART 4</span></div>
<div class="tt" id="tt" style="opacity:0"><div class="eyebrow">CAPT. CHARLES MAULTSBY · OCT. 27, 1962</div><h1>The wrong turn.</h1></div>${svg}
<div class="src">Map: Natural Earth (public domain) · Route illustrative, not to exact scale</div>`;
  const script = `
const rt=document.getElementById('rt'); const L=rt.getTotalLength(); rt.style.strokeDasharray=L; rt.style.strokeDashoffset=L;
window.DUR=11;
const show=(id,a)=>document.getElementById(id).style.opacity=a;
window.render=function(t){
  show('map',seg(t,0,1.2)); show('tt',seg(t,0.6,1.6)); show('p_eielson',seg(t,1.2,1.8));
  const p=seg(t,1.8,9.0); rt.style.strokeDashoffset=L*(1-p);
  show('p_pole',seg(t,3.6,4.2)); show('p_chuk',seg(t,6.0,6.6)); show('p_kotz',seg(t,8.6,9.2));
};`;
  fs.writeFileSync("cena2.html", page("U-2 route", body, script));
}

// ---------- Cena 3: linha do tempo de sábado, 27/10/1962 (hora de Washington) ----------
{
  const ev = [
    ["~10:00 A.M.", "Moscow Radio: a second letter", "Khrushchev adds the missiles in Turkey"],
    ["~10:20 A.M.", "U-2 shot down over Cuba", "Maj. Rudolf Anderson Jr. is killed"],
    ["1:41 P.M.", "McNamara told: a U-2 is over the USSR", "Capt. Maultsby, lost near the North Pole"],
    ["4:00 P.M.", "ExComm meets", "How to answer two letters"],
    ["7:45 P.M.", "RFK meets Dobrynin", "Justice Department, by RFK's own account"],
    ["9:52 P.M.", "Soviet submarine B-59 surfaces", "After practice depth charges"],
  ];
  const x0 = 170, x1 = 1750, y = 610;
  const xs = ev.map((_, i) => x0 + (i * (x1 - x0)) / (ev.length - 1));
  const items = ev.map((e, i) => {
    const up = i % 2 === 0;
    return `<div class="ev" id="e${i}" style="position:absolute;left:${xs[i] - 150}px;width:300px;${up ? `bottom:${H - y + 40}px` : `top:${y + 40}px`};opacity:0;text-align:center">
      <div style="font:700 34px M;color:${C.gold}">${e[0]}</div>
      <div style="font:700 31px S;line-height:1.15;margin-top:8px">${e[1]}</div>
      <div style="font:400 23px S;font-style:italic;color:${C.muted};margin-top:6px;line-height:1.25">${e[2]}</div></div>
      <div id="d${i}" style="position:absolute;left:${xs[i] - 13}px;top:${y - 13}px;width:26px;height:26px;border-radius:50%;background:${i === 1 ? C.red : C.gold};transform:scale(0)"></div>`;
  }).join("");
  const body = `<div class="top"><span>BEFORE HISTORY CHANGED</span><span>#004</span></div>
<div class="tt" id="tt" style="opacity:0"><div class="eyebrow">SATURDAY, OCTOBER 27, 1962 · WASHINGTON TIME</div><h1>Black Saturday.</h1></div>
<div id="bar" style="position:absolute;left:${x0}px;top:${y - 3}px;height:6px;width:0;background:${C.deep}"></div>${items}
<div class="src">Times: Miller Center tapes, National Security Archive, Michael Dobbs (2008). Some vary by a few minutes.</div>`;
  const script = `
window.DUR=13;
window.render=function(t){
  document.getElementById('tt').style.opacity=seg(t,0,1);
  document.getElementById('bar').style.width=(${x1 - x0}*seg(t,0.6,11))+'px';
  for(let i=0;i<${ev.length};i++){ const a=0.6+ (i/${ev.length - 1})*10.4; const s=seg(t,a-0.2,a+0.3);
    document.getElementById('d'+i).style.transform='scale('+s+')'; const e=document.getElementById('e'+i);
    e.style.opacity=seg(t,a,a+0.6); e.style.transform='translateY('+(1-seg(t,a,a+0.6))*20+'px)'; }
};`;
  fs.writeFileSync("cena3.html", page("Timeline", body, script));
}
console.log("ok");
