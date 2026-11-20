"""Gerador do Brazil on a Budget (@brazil.onabudget), no mesmo visual dos carrosséis de novembro/2026.

Pedido do Luiz em 20/11/2026: mais conteúdo no Brazil on a Budget, toda semana. Este gerador fica no
repositório para o robô semanal ("Brazil on a Budget — semana") montar os posts sem depender do canvas.

Uso:
    python gerador/bob.py pauta.json            (gera em fila/)
    python gerador/bob.py pauta.json --previa   (gera em previa/, para conferir)
pauta.json = {"posts": [{"sufixo": "noronha", "quando": "2026-11-30T18:30:00-03:00", "idioma": "en"|"es",
               "legenda": "...", "alt": ["...", ...], "redes": ["instagram","facebook","tiktok"],
               "cards": [ ... ]}]}
Tipos de card (todos 1080×1350):
    capa   {pilula, selo, titulo, sub, foto (nome em fotos/banco/ sem .jpg), credito}
    lista  {pilula, chamada, titulo, linhas: [[rótulo, valor], ...], nota, rodape}
    preco  {pilula, chamada, grande, texto, dica_titulo, dica, rodape}
    passos {pilula, chamada, titulo, itens: [[título, texto], ...], rodape}
    cta    (último slide, entra sozinho: "comente GUIDE/GUÍA" + siga; não precisa escrever)
O número "n/N" do rodapé é automático. Fontes: npm i @fontsource-variable/bricolage-grotesque @fontsource-variable/instrument-sans
"""
import html
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AZUL, TINTA, AMARELO, CLARO, FUNDO = "#0F6E8C", "#16212F", "#FFC83D", "#F2F7F8", "#F2F7F8"
LOGO = ('<svg width="64" height="64" viewBox="0 0 200 200"><circle cx="100" cy="100" r="96" fill="#16212F"/>'
        '<circle cx="126" cy="70" r="26" fill="#FFC83D"/><path d="M 18 140 C 30 140 34 96 52 92 C 68 89 70 120 80 128 '
        'C 90 108 98 58 120 56 C 138 55 146 110 182 140 Z" fill="#0F6E8C"/><path d="M 14 150 Q 32 140 50 150 T 86 150 '
        'T 122 150 T 158 150 T 194 150" fill="none" stroke="#F2F7F8" stroke-width="9" stroke-linecap="round"/></svg>')
TXT = {
    "en": {"swipe": "Swipe →", "cta_pilula": "FREE GUIDE INFO", "cta_chamada": "PLANNING THIS TRIP?",
           "cta_titulo": "Comment GUIDE and we'll DM you the full plan",
           "cta_itens": [["Comment GUIDE", "We send the day-by-day guide with real prices to your DMs."],
                         ["Follow @brazil.onabudget", "A new Brazil trip, priced, every week."],
                         ["Save and send", "Send this to the friend who's coming with you."]],
           "cta_rodape": "New trip every week"},
    "es": {"swipe": "Desliza →", "cta_pilula": "GUÍA COMPLETA", "cta_chamada": "¿PLANEAS ESTE VIAJE?",
           "cta_titulo": "Comenta GUÍA y te mandamos el plan completo",
           "cta_itens": [["Comenta GUÍA", "Te enviamos por DM la guía día a día con precios reales."],
                         ["Sigue @brazil.onabudget", "Un viaje por Brasil, con precios, cada semana."],
                         ["Guarda y comparte", "Mándaselo a quien viaja contigo."]],
           "cta_rodape": "Un viaje nuevo cada semana"},
}


def e(s):
    return html.escape(str(s or ""))


def fontes_css():
    base = None
    for b in (Path.cwd() / "node_modules", RAIZ / "node_modules", Path.home() / "node_modules"):
        if (b / "@fontsource-variable/bricolage-grotesque").exists():
            base = b
            break
    if not base:
        raise SystemExit("Fontes: rode  npm i @fontsource-variable/bricolage-grotesque @fontsource-variable/instrument-sans")
    css = ""
    for fam, pasta, arq in [("Bricolage Grotesque", "bricolage-grotesque", "bricolage-grotesque-latin-wght-normal.woff2"),
                            ("Instrument Sans", "instrument-sans", "instrument-sans-latin-wght-normal.woff2")]:
        f = base / f"@fontsource-variable/{pasta}/files/{arq}"
        if not f.exists():  # nomes mudam entre versões: pega o primeiro latin-*normal
            f = sorted((base / f"@fontsource-variable/{pasta}/files").glob("*-latin-*normal.woff2"))[0]
        css += f"@font-face{{font-family:'{fam}';src:url('{f.as_uri()}') format('woff2');font-weight:100 900}}"
    return css


def topo(pilula, cor=TINTA, borda=TINTA):
    return (f'<div style="display:flex;align-items:center;justify-content:space-between">'
            f'<div style="display:flex;align-items:center;gap:16px">{LOGO}<span style="font-family:\'Bricolage Grotesque\';font-weight:800;'
            f'font-size:32px;letter-spacing:.06em;color:{cor}">BRAZIL ON A BUDGET</span></div>'
            f'<span style="font-weight:700;font-size:30px;border:2px solid {borda};color:{cor};border-radius:999px;padding:10px 24px;white-space:nowrap">{e(pilula)}</span></div>')


def rodape(esq, dir_, cor="#5B6672", linha="#D5DEE3"):
    return (f'<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:32px;border-top:2px solid {linha};'
            f'padding-top:24px;font-size:30px;color:{cor}"><span>{e(esq)}</span><span style="white-space:nowrap">{e(dir_)}</span></div>')


def quadro(miolo, fundo=FUNDO, cor=TINTA, extra=""):
    return (f'<div id="q" style="width:1080px;height:1350px;box-sizing:border-box;padding:72px 80px;position:relative;'
            f'background:{fundo};color:{cor};font-family:\'Instrument Sans\';display:flex;flex-direction:column;gap:40px">{miolo}{extra}</div>')


def capa(c, pos, idi):
    foto = RAIZ / "fotos/banco" / f"{c['foto']}.jpg"
    if not foto.exists():
        raise SystemExit(f"foto não encontrada: {foto}")
    fundo = (f"linear-gradient(180deg,rgba(10,22,34,.72) 0%,rgba(10,22,34,.30) 30%,rgba(10,22,34,.45) 55%,rgba(10,22,34,.88) 100%),"
             f"url('{foto.as_uri()}') center/cover no-repeat {AZUL}")
    selo = f'<span style="align-self:flex-start;background:{AMARELO};color:{TINTA};font-weight:700;font-size:32px;border-radius:12px;padding:10px 20px">{e(c.get("selo"))}</span>' if c.get("selo") else ""
    tam = 120 if len(c["titulo"]) <= 40 else 100 if len(c["titulo"]) <= 60 else 86
    miolo = (topo(c["pilula"], CLARO, CLARO) +
             f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:flex-end;gap:32px;padding-bottom:8px">{selo}'
             f'<h1 style="margin:0;text-shadow:0 4px 24px rgba(0,0,0,.45);font-family:\'Bricolage Grotesque\';font-weight:800;font-size:{tam}px;line-height:.92;letter-spacing:-.02em">{e(c["titulo"])}</h1>'
             f'<p style="margin:0;text-shadow:0 2px 14px rgba(0,0,0,.6);font-size:44px;line-height:1.3;max-width:880px">{e(c.get("sub"))}</p></div>' +
             rodape(TXT[idi]["swipe"], pos, CLARO, "rgba(242,247,248,.35)"))
    meta = foto.with_suffix(".json")
    if not c.get("credito") and meta.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        c["credito"] = f"Photo: {m.get('autor', '')} · {m.get('licenca', '')} · Wikimedia Commons" if m.get("fonte") == "wikimedia" else m.get("credito", "")
    cred = f'<span style="position:absolute;right:80px;top:150px;font-size:20px;opacity:.85;text-shadow:0 1px 6px rgba(0,0,0,.7)">{e(c.get("credito"))}</span>' if c.get("credito") else ""
    return quadro(miolo, fundo, CLARO, cred)


def cabeca(c):
    return (f'<span style="font-weight:700;font-size:32px;letter-spacing:.08em;color:{AZUL};text-transform:uppercase">{e(c.get("chamada"))}</span>'
            + (f'<h2 style="margin:0;font-family:\'Bricolage Grotesque\';font-weight:800;font-size:76px;line-height:1;letter-spacing:-.02em">{e(c["titulo"])}</h2>' if c.get("titulo") else ""))


def lista(c, pos, idi):
    linhas = "".join(f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:24px;border-bottom:2px solid #D5DEE3;padding:18px 0">'
                     f'<span style="font-size:40px;font-weight:600">{e(a)}</span><span style="font-family:\'Bricolage Grotesque\';font-weight:800;font-size:48px;color:{AZUL};white-space:nowrap">{e(b)}</span></div>'
                     for a, b in c["linhas"])
    nota = f'<p style="margin:8px 0 0;font-size:32px;line-height:1.35;color:#5B6672">{e(c["nota"])}</p>' if c.get("nota") else ""
    miolo = (topo(c["pilula"]) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:14px">{cabeca(c)}'
             f'<div style="margin-top:10px">{linhas}</div>{nota}</div>' + rodape(c.get("rodape", ""), pos))
    return quadro(miolo)


def preco(c, pos, idi):
    dica = (f'<div style="background:{AMARELO};border-radius:20px;padding:26px 30px"><div style="font-weight:700;font-size:34px">{e(c.get("dica_titulo"))}</div>'
            f'<div style="font-size:32px;line-height:1.35;margin-top:6px">{e(c["dica"])}</div></div>') if c.get("dica") else ""
    miolo = (topo(c["pilula"]) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:26px">{cabeca(c)}'
             f'<div style="font-family:\'Bricolage Grotesque\';font-weight:800;font-size:{180 if len(c["grande"]) <= 9 else 130}px;line-height:.9;letter-spacing:-.03em">{e(c["grande"])}</div>'
             f'<p style="margin:0;font-size:42px;line-height:1.35">{e(c.get("texto"))}</p>{dica}</div>' + rodape(c.get("rodape", ""), pos))
    return quadro(miolo)


def passos(c, pos, idi):
    itens = "".join(f'<div style="display:flex;gap:26px;align-items:flex-start;background:#E3ECEF;border-radius:20px;padding:24px 28px">'
                    f'<span style="flex-shrink:0;width:72px;height:72px;border-radius:18px;background:{AZUL};color:{CLARO};display:flex;align-items:center;justify-content:center;font-family:\'Bricolage Grotesque\';font-weight:800;font-size:42px">{i}</span>'
                    f'<div><div style="font-family:\'Bricolage Grotesque\';font-weight:800;font-size:40px;line-height:1.05">{e(t)}</div><div style="font-size:30px;line-height:1.3;margin-top:6px;color:#33404D">{e(x)}</div></div></div>'
                    for i, (t, x) in enumerate(c["itens"], 1))
    miolo = (topo(c["pilula"]) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:20px">{cabeca(c)}'
             f'<div style="display:flex;flex-direction:column;gap:16px;margin-top:10px">{itens}</div></div>' + rodape(c.get("rodape", ""), pos))
    return quadro(miolo)


def cta(pos, idi):
    t = TXT[idi]
    itens = "".join(f'<div style="display:flex;align-items:center;gap:26px;background:rgba(22,33,47,.55);border-radius:20px;padding:26px 30px">'
                    f'<span style="flex-shrink:0;width:76px;height:76px;border-radius:18px;background:{AMARELO};color:{TINTA};display:flex;align-items:center;justify-content:center;font-family:\'Bricolage Grotesque\';font-weight:800;font-size:46px">{i}</span>'
                    f'<div><div style="font-family:\'Bricolage Grotesque\';font-weight:800;font-size:44px;line-height:1.05">{e(a)}</div><div style="font-size:30px;line-height:1.3;margin-top:6px">{e(b)}</div></div></div>'
                    for i, (a, b) in enumerate(t["cta_itens"], 1))
    miolo = (topo(t["cta_pilula"], CLARO, CLARO) + f'<div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;gap:30px">'
             f'<span style="font-weight:700;font-size:32px;letter-spacing:.08em;color:{AMARELO}">{e(t["cta_chamada"])}</span>'
             f'<h1 style="margin:0;font-family:\'Bricolage Grotesque\';font-weight:800;font-size:96px;line-height:.95;letter-spacing:-.02em">{e(t["cta_titulo"])}</h1>{itens}</div>'
             + rodape(t["cta_rodape"], "@brazil.onabudget", CLARO, "rgba(242,247,248,.35)"))
    return quadro(miolo, AZUL, CLARO)


TIPOS = {"capa": capa, "lista": lista, "preco": preco, "passos": passos}


def main(pauta, previa):
    from playwright.sync_api import sync_playwright
    dados = json.load(open(pauta, encoding="utf-8"))
    css = fontes_css()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for post in dados["posts"]:
            idi = post.get("idioma", "en")
            data = post["quando"][:10]
            pasta = RAIZ / ("previa" if previa else "fila") / f"{data}-brazilonabudget-{post['sufixo']}"
            pasta.mkdir(parents=True, exist_ok=True)
            n = len(post["cards"]) + 1
            htmls = [TIPOS[c["tipo"]](c, f"{i}/{n}", idi) for i, c in enumerate(post["cards"], 1)] + [cta(f"{n}/{n}", idi)]
            midias = []
            for i, h in enumerate(htmls, 1):
                tmp = pasta / "_render.html"  # arquivo local: file:// de fontes e fotos só carrega a partir de outro file://
                tmp.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}html,body{{margin:0}}</style></head><body>{h}</body></html>", encoding="utf-8")
                pg.goto(tmp.as_uri())
                pg.evaluate("document.fonts.ready")
                pg.wait_for_timeout(300)
                larg = pg.evaluate("(()=>{const q=document.getElementById('q');return [...q.querySelectorAll('*')].some(el=>el.scrollWidth>el.clientWidth+2&&getComputedStyle(el).overflow!='visible')||q.scrollHeight>1352})()")
                if larg:
                    print(f"AVISO: {pasta.name} slide {i}: texto pode ter estourado o quadro, confira")
                nome = f"{i:02d}.jpg"
                pg.locator("#q").screenshot(path=str(pasta / nome), type="jpeg", quality=93)
                midias.append(nome)
            (pasta / "_render.html").unlink(missing_ok=True)
            alts = post.get("alt", [])
            alts = (alts + [alts[-1] if alts else post["legenda"].split("\n")[0]] * n)[:n]
            json.dump({"conta": "brazilonabudget", "tipo": "carrossel", "redes": post.get("redes", ["instagram", "facebook", "tiktok"]),
                       "quando": post["quando"], "status": "aprovado", "midias": midias, "textos_alternativos": alts,
                       "legenda": post["legenda"]}, open(pasta / "post.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"ok: {pasta.relative_to(RAIZ)} ({n} slides)")
        b.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1], "--previa" in sys.argv)
