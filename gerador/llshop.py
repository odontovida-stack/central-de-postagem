"""Robô de agenda das páginas LLShop.

Lê uma pauta da semana (pauta/AAAA-MM-DD.json), monta os cards no visual das
páginas e cria um post na fila para cada card, com status "aprovado".
Quem aprova é o merge do pull request.

Uso:
    python gerador/llshop.py pauta/2026-11-02.json          # gera imagens e posts
    python gerador/llshop.py pauta/2026-11-02.json --previa # só as imagens, em previa/

Precisa do Playwright (pip install playwright && playwright install chromium).
"""
import html
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTES = Path(__file__).resolve().parent / "fontes"

PAGINAS = {
    "jogosnatela": {"cor": "#2FD17A"},
    "esportesnatela": {"cor": "#4C9AFF"},
    "tudooqueestreia": {"cor": "#FF5A5F"},
    "lancamentosdegames": {"cor": "#A78BFA"},
    "showsconfirmados": {"cor": "#FFB020"},
}
BG, CARD, FG, MUTED, LINE = "#0F1115", "#181B21", "#F4F4F5", "#B4B8C0", "#2A2E36"


def e(s):
    return html.escape(str(s or ""), quote=False)


def fontes_css():
    regras = []
    for f in sorted(FONTES.glob("*.woff2")):
        familia = "Barlow Condensed" if "condensed" in f.name else "Barlow"
        peso = f.name.split("-")[-2]
        regras.append(f"@font-face{{font-family:'{familia}';font-weight:{peso};src:url('{f.as_uri()}') format('woff2')}}")
    return "\n".join(regras)


def topo(conta, cor, pilula, cheia):
    estilo = (f"background: {cor}; color: {BG}" if cheia else f"border: 2px solid {cor}; color: {cor}")
    return f'''<div style="display: flex; align-items: center; justify-content: space-between; gap: 24px">
<div style="display: flex; align-items: center; gap: 16px"><span style="width: 28px; height: 28px; border-radius: 6px; background: {cor}"></span><span style="font-weight: 600; font-size: 32px">@{conta}</span></div>
<span style="font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 32px; {estilo}; border-radius: 999px; padding: 6px 22px; white-space: nowrap">{e(pilula)}</span>
</div>'''


def rodape(fonte, cta):
    return f'''<div style="display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; border-top: 2px solid {LINE}; padding-top: 22px; font-size: 28px; color: {MUTED}">
<span>{e(fonte)}</span>
<span style="white-space: nowrap; color: {FG}">{e(cta)}</span>
</div>'''


def moldura(miolo):
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>{fontes_css()}
body{{margin:0}}</style></head><body>
<div id="card" style="width: 1080px; height: 1350px; box-sizing: border-box; padding: 72px 80px; background: {BG}; color: {FG}; font-family: 'Barlow', sans-serif; display: flex; flex-direction: column; gap: 36px">
{miolo}
</div></body></html>'''


def agenda(conta, card):
    cor = PAGINAS[conta]["cor"]
    itens = card["itens"]
    n = len(itens)
    titulo_px, det_px, pad, gap, h1_px, data_px = (50, 30, 22, 18, 124, 48) if n <= 4 else (44, 28, 18, 14, 112, 44) if n == 5 else (40, 26, 14, 12, 100, 40)
    linhas = []
    for it in itens:
        linhas.append(f'''<div style="display: flex; align-items: center; gap: 28px; background: {CARD}; border-radius: 18px; padding: {pad}px 24px"><div style="width: 150px; flex-shrink: 0; background: {cor}; color: {BG}; border-radius: 12px; padding: 10px 0; display: flex; flex-direction: column; align-items: center"><span style="font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: {data_px if len(it["data"]) <= 5 else data_px - 10}px; line-height: 1">{e(it["data"])}</span><span style="font-weight: 700; font-size: 26px">{e(it.get("sub"))}</span></div><div style="display: flex; flex-direction: column; gap: 4px; min-width: 0"><span style="font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: {titulo_px}px; line-height: 1">{e(it["titulo"])}</span><span style="font-size: {det_px}px; color: {MUTED}">{e(it.get("detalhe"))}</span></div></div>''')
    miolo = f'''{topo(conta, cor, card["pilula"], False)}
<div style="display: flex; flex-direction: column; gap: 10px">
<span style="font-weight: 700; font-size: 32px; letter-spacing: 0.12em; color: {cor}">{e(card["chamada"])}</span>
<h1 style="margin: 0; font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: {h1_px}px; line-height: 0.9; text-transform: uppercase">{e(card["titulo"])}</h1>
</div>
<div style="display: flex; flex-direction: column; gap: {gap}px; flex-grow: 1; justify-content: center">
{"".join(linhas)}
</div>
{rodape(card["fonte"], card["cta"])}'''
    return moldura(miolo)


def destaque(conta, card):
    cor = PAGINAS[conta]["cor"]
    partes = [f'<span style="font-weight: 700; font-size: 32px; letter-spacing: 0.12em; color: {cor}">{e(card["chamada"])}</span>']
    if card.get("grande"):
        partes.append(f'<span style="font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: 230px; line-height: 0.85; color: {cor}">{e(card["grande"])}</span>')
    tam = card.get("titulo_px") or (136 if len(card["titulo"]) <= 30 else 112)
    partes.append(f'<h1 style="margin: 0; font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: {tam}px; line-height: 0.92; text-transform: uppercase">{e(card["titulo"])}</h1>')
    if card.get("caixas"):
        caixas = "".join(f'<div style="background: {CARD}; border-radius: 18px; padding: 22px 26px; display: flex; flex-direction: column; gap: 6px"><span style="font-size: 28px; color: {MUTED}">{e(a)}</span><span style="font-family: \'Barlow Condensed\', sans-serif; font-weight: 700; font-size: 44px">{e(b)}</span></div>' for a, b in card["caixas"])
        partes.append(f'<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px">{caixas}</div>')
    if card.get("linhas"):
        for d, a, b in card["linhas"]:
            partes.append(f'<div style="display: flex; align-items: center; gap: 28px; background: {CARD}; border-radius: 18px; padding: 22px 26px"><span style="font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: 72px; color: {cor}; width: 190px; flex-shrink: 0">{e(d)}</span><div style="display: flex; flex-direction: column; gap: 4px"><span style="font-family: \'Barlow Condensed\', sans-serif; font-weight: 700; font-size: 50px; line-height: 1">{e(a)}</span><span style="font-size: 30px; color: {MUTED}">{e(b)}</span></div></div>')
    if card.get("nota"):
        partes.append(f'<span style="font-size: 30px; color: {MUTED}">{e(card["nota"])}</span>')
    miolo = f'''{topo(conta, cor, card["pilula"], True)}
<div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center; gap: 28px">
{chr(10).join(partes)}
</div>
{rodape(card["fonte"], card["cta"])}'''
    return moldura(miolo)


def pergunta(conta, card):
    """Card de engajamento: uma pergunta grande e até 4 opções para responder nos comentários."""
    cor = PAGINAS[conta]["cor"]
    tam = card.get("titulo_px") or (112 if len(card["titulo"]) <= 40 else 92)
    partes = [f'<span style="font-weight: 700; font-size: 32px; letter-spacing: 0.12em; color: {cor}">{e(card["chamada"])}</span>',
              f'<h1 style="margin: 0; font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: {tam}px; line-height: 0.95; text-transform: uppercase">{e(card["titulo"])}</h1>']
    if card.get("contexto"):
        partes.append(f'<span style="font-size: 32px; color: {MUTED}; line-height: 1.3">{e(card["contexto"])}</span>')
    opcoes = card.get("opcoes") or []
    if opcoes:
        letras = "ABCD"
        caixas = "".join(f'<div style="display: flex; align-items: center; gap: 22px; background: {CARD}; border-radius: 18px; padding: 22px 26px"><span style="flex-shrink: 0; width: 64px; height: 64px; border-radius: 14px; background: {cor}; color: {BG}; display: flex; align-items: center; justify-content: center; font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: 44px">{letras[i]}</span><span style="font-family: \'Barlow Condensed\', sans-serif; font-weight: 700; font-size: 46px; line-height: 1.05">{e(o)}</span></div>' for i, o in enumerate(opcoes[:4]))
        partes.append(f'<div style="display: flex; flex-direction: column; gap: 14px">{caixas}</div>')
    miolo = f'''{topo(conta, cor, card["pilula"], True)}
<div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center; gap: 30px">
{chr(10).join(partes)}
</div>
{rodape(card.get("fonte", ""), card.get("cta", "Responda nos comentários"))}'''
    return moldura(miolo)


def renderizar(trabalhos):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page(viewport={"width": 1080, "height": 1350})
        for htm, destino in trabalhos:
            destino.parent.mkdir(parents=True, exist_ok=True)
            tmp = destino.with_suffix(".html")
            tmp.write_text(htm, encoding="utf-8")
            pag.goto(tmp.as_uri())
            pag.evaluate("document.fonts.ready")
            sobra = pag.evaluate("(() => { const c = document.getElementById('card'); return c.scrollHeight > c.clientHeight + 1; })()")
            if sobra:
                raise SystemExit(f"O texto não coube no card: {destino}")
            pag.locator("#card").screenshot(path=str(destino), type="jpeg", quality=92)
            tmp.unlink()
        nav.close()


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pauta_arq = Path(sys.argv[1])
    previa = "--previa" in sys.argv
    pauta = json.loads(pauta_arq.read_text(encoding="utf-8"))
    trabalhos, posts = [], []
    for conta, cards in pauta["contas"].items():
        if conta not in PAGINAS:
            raise SystemExit(f"Conta desconhecida: {conta}")
        for card in cards:
            subcards = card["cards"] if card["tipo"] == "carrossel" else [card]
            nome = f'{card["quando"][:10]}-{conta}-{card["tipo"]}'
            if card.get("sufixo"):
                nome += "-" + card["sufixo"]
            pasta = (RAIZ / "previa" / pauta_arq.stem) if previa else (RAIZ / "fila" / nome)
            midias, alts = [], []
            for i, sub in enumerate(subcards, 1):
                htm = {"agenda": agenda, "destaque": destaque, "pergunta": pergunta}[sub["tipo"]](conta, sub)
                arq = f"{i:02d}.jpg"
                img = pasta / (f"{nome}-{arq}" if previa else arq)
                trabalhos.append((htm, img))
                midias.append(arq)
                alts.append(sub.get("alt") or f'{sub["chamada"]}: {sub["titulo"]}')
            if card.get("alt") and len(subcards) == 1:
                alts = [card["alt"]]
            if not previa:
                posts.append((pasta, conta, card, midias, alts))
    renderizar(trabalhos)
    for pasta, conta, card, midias, alts in posts:
        post = {
            "conta": conta,
            "tipo": "carrossel" if len(midias) > 1 else "imagem",
            "redes": card.get("redes", ["instagram", "facebook"]),
            "quando": card["quando"],
            "status": "aprovado",
            "midias": midias,
            "textos_alternativos": alts,
            "legenda": card["legenda"],
        }
        (pasta / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for _, img in trabalhos:
        print(img.relative_to(RAIZ))


if __name__ == "__main__":
    main()
