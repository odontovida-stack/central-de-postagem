"""Slides 1920x1080 dos canais de YouTube (visual do The American File).
Uso: python gerador/youtube/slides.py slides.json pasta_saida
Tipos: capa, capitulo, numero, citacao, lista, barras, duplo, linha, donut, xs. Campo opcional "stamp" (carimbo)."""
import json, sys, html
from pathlib import Path
from playwright.sync_api import sync_playwright
F = Path(__file__).resolve().parent / "fontes"
import os
TEMAS = {
    "taf": {"cores": ("#0D1117", "#1B3A6B", "#C0392B", "#EDE6D6", "#9AA4B2"), "marca": "THE AMERICAN FILE", "rotulo": "FILE #"},
    "bhc": {"cores": ("#15110C", "#5A4426", "#C9A227", "#F1E6CF", "#A89A84"), "marca": "BEFORE HISTORY CHANGED", "rotulo": "#", "brilho": ("rgba(90,68,38,.45)", "rgba(201,162,39,.10)"), "cartao": "rgba(90,68,38,.38)"},
}
TEMA = TEMAS[os.environ.get("TEMA_SLIDES", "taf")]
BG, NAVY, RED, PAPER, MUTED = TEMA["cores"]
CARTAO = TEMA.get("cartao", "rgba(27,58,107,.35)")
GLOW1, GLOW2 = TEMA.get("brilho", ("rgba(27,58,107,.35)", "rgba(192,57,43,.12)"))
def ff(fam, w, st="normal", fn=None): return f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{st};src:url('file://{F}/{fn}')}}"
CSS = (ff("S", 400, fn="source-serif-4-latin-400-normal.woff2") + ff("S", 400, "italic", "source-serif-4-latin-400-italic.woff2") +
       ff("S", 700, fn="source-serif-4-latin-700-normal.woff2") + ff("S", 700, "italic", "source-serif-4-latin-700-italic.woff2") +
       ff("M", 500, fn="ibm-plex-mono-latin-500-normal.woff2") + ff("M", 700, fn="ibm-plex-mono-latin-700-normal.woff2") +
       f"""body{{margin:0}}#c{{width:1920px;height:1080px;box-sizing:border-box;padding:90px 120px;background:{BG};color:{PAPER};font-family:S;position:relative;overflow:hidden;display:flex;flex-direction:column}}
.grain{{position:absolute;inset:0;background:radial-gradient(ellipse at 30% 20%,{GLOW1},transparent 60%),radial-gradient(ellipse at 90% 100%,{GLOW2},transparent 50%)}}
.top{{display:flex;justify-content:space-between;font:500 26px M;letter-spacing:.18em;color:{MUTED};position:relative}}
.stamp{{position:absolute;border:6px solid {RED};color:{RED};font:700 44px M;letter-spacing:.2em;padding:10px 26px;transform:rotate(-8deg);opacity:.85}}
.src{{position:absolute;left:120px;bottom:60px;font:500 22px M;color:{MUTED};letter-spacing:.04em}}
""")
e = html.escape
def topo(s): return f'<div class="top"><span>{TEMA["marca"]}</span><span>{TEMA["rotulo"]}{e(s.get("file","001"))}{" · " + e(s["parte"]) if s.get("parte") else ""}</span></div>'
def corpo(s):
    t = s["tipo"]
    if t == "capa":
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:34px;position:relative">'
                f'<span style="font:700 34px M;color:{RED};letter-spacing:.2em">{TEMA["rotulo"]}{e(s.get("file","001"))}</span>'
                f'<h1 style="margin:0;font-weight:700;font-size:{s.get("px",128)}px;line-height:1.02;max-width:1500px">{e(s["titulo"])}</h1>'
                f'<p style="margin:0;font-style:italic;font-size:44px;color:{MUTED};max-width:1400px">{e(s.get("sub",""))}</p></div>' +
                (f'<div class="stamp" style="right:140px;top:230px">CLASSIFIED</div>' if not s.get("stamp") and os.environ.get("TEMA_SLIDES", "taf") == "taf" else ''))
    if t == "capitulo":
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:28px;position:relative">'
                f'<span style="font:700 32px M;color:{RED};letter-spacing:.2em">{e(s["numero"])}</span>'
                f'<div style="width:160px;height:6px;background:{RED}"></div>'
                f'<h1 style="margin:0;font-weight:700;font-size:112px;line-height:1.05;max-width:1600px">{e(s["titulo"])}</h1></div>')
    if t == "numero":
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:24px;position:relative">'
                f'<span style="font:500 34px M;color:{MUTED};letter-spacing:.12em">{e(s.get("rotulo",""))}</span>'
                f'<span style="font-weight:700;font-size:{s.get("px",230)}px;line-height:.95;color:{PAPER}">{e(s["valor"])}</span>'
                f'<p style="margin:0;font-size:48px;line-height:1.3;max-width:1500px">{e(s.get("texto",""))}</p></div>'
                + (f'<div class="src">SOURCE: {e(s["fonte"])}</div>' if s.get("fonte") else ""))
    if t == "citacao":
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:40px;position:relative;padding-left:60px;border-left:10px solid {RED};margin:60px 0">'
                f'<p style="margin:0;font-style:italic;font-size:{s.get("px",62)}px;line-height:1.3;max-width:1550px">“{e(s["texto"])}”</p>'
                f'<span style="font:500 32px M;color:{MUTED};letter-spacing:.08em">— {e(s["autor"])}</span></div>')
    if t == "lista":
        itens = "".join(f'<div style="display:flex;gap:30px;align-items:baseline"><span style="font:700 34px M;color:{RED}">{i:02d}</span><span style="font-size:52px;line-height:1.25">{e(x)}</span></div>' for i, x in enumerate(s["itens"], 1))
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:34px;position:relative">'
                f'<h2 style="margin:0 0 10px;font-weight:700;font-size:84px">{e(s["titulo"])}</h2>{itens}</div>'
                + (f'<div class="src">SOURCE: {e(s["fonte"])}</div>' if s.get("fonte") else ""))
    if t == "barras":
        mx = max(v for _, v, _ in s["barras"])
        bs = "".join(f'<div style="display:grid;grid-template-columns:360px 1fr;gap:30px;align-items:center"><span style="font-size:40px;text-align:right">{e(n)}</span>'
                     f'<div style="display:flex;align-items:center;gap:20px"><div style="height:58px;width:{max(6, v / mx * 1000):.0f}px;background:{RED if i == 0 else NAVY}"></div><span style="font:700 36px M">{e(r)}</span></div></div>'
                     for i, (n, v, r) in enumerate(s["barras"]))
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:26px;position:relative">'
                f'<h2 style="margin:0 0 20px;font-weight:700;font-size:76px">{e(s["titulo"])}</h2>{bs}</div>'
                + (f'<div class="src">SOURCE: {e(s["fonte"])}</div>' if s.get("fonte") else ""))
    if t == "duplo":
        cs = "".join(f'<div style="flex:1;background:{CARTAO};border-top:6px solid {RED if i == len(s["itens"])-1 else NAVY};padding:44px 48px;display:flex;flex-direction:column;gap:18px"><span style="font:500 30px M;color:{MUTED};letter-spacing:.1em">{e(a)}</span><span style="font-weight:700;font-size:{s.get("px",96)}px;line-height:1">{e(b)}</span><span style="font-size:36px;line-height:1.3;color:{PAPER}">{e(c)}</span></div>' for i,(a,b,c) in enumerate(s["itens"]))
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:40px;position:relative">'
                + (f'<h2 style="margin:0;font-weight:700;font-size:72px">{e(s["titulo"])}</h2>' if s.get("titulo") else "")
                + f'<div style="display:flex;gap:40px">{cs}</div></div>' + (f'<div class="src">SOURCE: {e(s["fonte"])}</div>' if s.get("fonte") else ""))
    if t == "linha":
        n = len(s["marcos"])
        ms = "".join(f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:22px;text-align:center"><span style="font:700 40px M;color:{RED if i == n-1 else PAPER}">{e(a)}</span><span style="width:26px;height:26px;border-radius:50%;background:{RED if i == n-1 else NAVY};border:4px solid {PAPER}"></span><span style="font-size:32px;line-height:1.25;max-width:270px">{e(b)}</span></div>' for i,(a,b) in enumerate(s["marcos"]))
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:50px;position:relative"><h2 style="margin:0;font-weight:700;font-size:72px">{e(s["titulo"])}</h2>'
                f'<div style="position:relative"><div style="position:absolute;left:5%;right:5%;top:74px;height:4px;background:{MUTED}"></div><div style="display:flex;position:relative">{ms}</div></div></div>'
                + (f'<div class="src">SOURCE: {e(s["fonte"])}</div>' if s.get("fonte") else ""))
    if t == "donut":
        tot = sum(v for _, v in s["fatias"]); cores = [RED, NAVY, "#3E6AA8", "#7A8696", "#4A5160"]; acc = 0; arcs = ""
        import math
        for i, (n_, v) in enumerate(s["fatias"]):
            a0 = acc / tot * 2 * math.pi; acc += v; a1 = acc / tot * 2 * math.pi
            r = 300; x0, y0 = 360 + r * math.sin(a0), 360 - r * math.cos(a0); x1, y1 = 360 + r * math.sin(a1), 360 - r * math.cos(a1)
            arcs += f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 {1 if a1 - a0 > math.pi else 0} 1 {x1:.1f} {y1:.1f}" fill="none" stroke="{cores[i % 5]}" stroke-width="120"/>'
        leg = "".join(f'<div style="display:flex;gap:22px;align-items:center"><span style="width:34px;height:34px;background:{cores[i % 5]}"></span><span style="font-size:40px">{e(n_)}</span><span style="font:700 38px M;margin-left:auto">${v}B</span></div>' for i, (n_, v) in enumerate(s["fatias"]))
        return (topo(s) + f'<div style="flex-grow:1;display:flex;align-items:center;gap:90px;position:relative"><svg width="720" height="720" viewBox="0 0 720 720">{arcs}<text x="360" y="350" text-anchor="middle" fill="{PAPER}" font-family="S" font-weight="700" font-size="96">{e(s.get("total_txt", f"${tot}B"))}</text><text x="360" y="410" text-anchor="middle" fill="{MUTED}" font-family="M" font-size="28">{e(s.get("centro",""))}</text></svg>'
                f'<div style="flex:1;display:flex;flex-direction:column;gap:26px"><h2 style="margin:0 0 10px;font-weight:700;font-size:60px;line-height:1.1">{e(s["titulo"])}</h2>{leg}<p style="margin:10px 0 0;font-size:28px;color:{MUTED}">{e(s.get("nota",""))}</p></div></div>'
                + (f'<div class="src">SOURCE: {e(s["fonte"])}</div>' if s.get("fonte") else ""))
    if t == "xs":
        xs = "".join(f'<div style="display:flex;flex-direction:column;align-items:center;gap:16px"><span style="font:700 120px M;color:{RED};line-height:1">✕</span><span style="font:500 28px M;color:{MUTED}">{e(a)}</span></div>' for a in s["itens"])
        return (topo(s) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:56px;position:relative"><h2 style="margin:0;font-weight:700;font-size:80px">{e(s["titulo"])}</h2>'
                f'<div style="display:flex;justify-content:space-between">{xs}</div><p style="margin:0;font-size:40px;line-height:1.3">{e(s.get("texto",""))}</p></div>'
                + (f'<div class="src">SOURCE: {e(s["fonte"])}</div>' if s.get("fonte") else ""))
    raise SystemExit("tipo desconhecido: " + t)
def main():
    sl = json.load(open(sys.argv[1])); out = Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for i, s in enumerate(sl, 1):
            tmp = out / "_t.html"; stamp = f'<div class="stamp" style="right:140px;top:{s.get("stamp_top",230)}px">{e(s["stamp"])}</div>' if s.get("stamp") else ''
            tmp.write_text(f'<!doctype html><meta charset=utf-8><style>{CSS}</style><div id=c><div class=grain></div>{corpo(s)}{stamp}</div>', encoding="utf-8")
            pg.goto(tmp.as_uri()); pg.evaluate("document.fonts.ready")
            if pg.evaluate("(()=>{const c=document.getElementById('c');return c.scrollHeight>c.clientHeight+1})()"): print("NÃO COUBE:", i)
            pg.locator("#c").screenshot(path=str(out / f"{i:03d}.png")); tmp.unlink()
        b.close()
    print(len(sl), "slides")
if __name__ == "__main__": main()
