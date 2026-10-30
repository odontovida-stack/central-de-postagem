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
    "jogosnatela": {"cor": "#2FD17A", "promessa": "Os jogos do dia, todo dia de manhã, com horário e onde passa."},
    "esportesnatela": {"cor": "#4C9AFF", "promessa": "A agenda de todos os esportes: futebol, F1, NBA, vôlei, UFC e mais."},
    "tudooqueestreia": {"cor": "#FF5A5F", "promessa": "Tudo o que estreia no cinema e no streaming, toda semana."},
    "lancamentosdegames": {"cor": "#A78BFA", "promessa": "Os lançamentos do dia e os jogos grátis antes de acabar o prazo."},
    "showsconfirmados": {"cor": "#FFB020", "promessa": "Os shows confirmados no Brasil, com data, cidade e pré-venda."},
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


BANCO = RAIZ / "fotos" / "banco"


def foto_info(nome):
    """Dados da foto do banco (fotos/banco/<nome>.jpg + .json). Erro claro se ainda não foi baixada."""
    jpg, meta = BANCO / f"{nome}.jpg", BANCO / f"{nome}.json"
    if not jpg.exists() or not meta.exists():
        raise SystemExit(f"Foto '{nome}' não está no banco. Peça em fotos/pedidos.json e espere o robô de fotos.")
    return jpg, json.loads(meta.read_text(encoding="utf-8"))


def moldura(miolo, card=None):
    fundo, credito = BG, ""
    if card and card.get("foto"):
        jpg, info = foto_info(card["foto"])
        # camada escura forte: o texto fica legível em qualquer foto
        fundo = (f"linear-gradient(180deg, rgba(15,17,21,0.80) 0%, rgba(15,17,21,0.55) 28%, rgba(15,17,21,0.70) 55%, "
                 f"rgba(15,17,21,0.94) 100%), url('{jpg.as_uri()}') center / cover no-repeat {BG}")
        credito = (f'<span style="position: absolute; right: 80px; bottom: 30px; font-size: 20px; color: {MUTED}">'
                   f'{e(info["credito"])} · Wikimedia Commons</span>')
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>{fontes_css()}
body{{margin:0}}</style></head><body>
<div id="card" style="position: relative; width: 1080px; height: 1350px; box-sizing: border-box; padding: 72px 80px; background: {fundo}; color: {FG}; font-family: 'Barlow', sans-serif; display: flex; flex-direction: column; gap: 36px">
{miolo}
{credito}
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
    return moldura(miolo, card)


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
    return moldura(miolo, card)


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
    return moldura(miolo, card)


def texto(conta, card):
    """Slide de comentário: título, um parágrafo curto e até 4 tópicos, ou um número grande."""
    cor = PAGINAS[conta]["cor"]
    tam = card.get("titulo_px") or (96 if len(card["titulo"]) <= 34 else 80)
    partes = [f'<span style="font-weight: 700; font-size: 32px; letter-spacing: 0.12em; color: {cor}">{e(card["chamada"])}</span>',
              f'<h2 style="margin: 0; font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: {tam}px; line-height: 0.95; text-transform: uppercase">{e(card["titulo"])}</h2>']
    if card.get("grande"):
        partes.append(f'<span style="font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: 170px; line-height: 0.9; color: {cor}">{e(card["grande"])}</span>')
    if card.get("texto"):
        partes.append(f'<p style="margin: 0; font-size: 38px; line-height: 1.35; color: {FG}">{e(card["texto"])}</p>')
    if card.get("topicos"):
        itens = "".join(f'<div style="display: flex; gap: 18px; align-items: flex-start"><span style="flex-shrink: 0; width: 14px; height: 14px; margin-top: 16px; border-radius: 4px; background: {cor}"></span><span style="font-size: 36px; line-height: 1.3">{e(t)}</span></div>' for t in card["topicos"][:4])
        partes.append(f'<div style="display: flex; flex-direction: column; gap: 16px; background: {CARD}; border-radius: 18px; padding: 28px 30px">{itens}</div>')
    miolo = f'''{topo(conta, cor, card["pilula"], False)}
<div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center; gap: 30px">
{chr(10).join(partes)}
</div>
{rodape(card.get("fonte", ""), card.get("cta", "Arraste →"))}'''
    return moldura(miolo, card)


def seguir(conta, card=None):
    """Último slide dos carrosséis: lembrete para seguir, ativar avisos, salvar e mandar para alguém."""
    card = card or {}
    cor = PAGINAS[conta]["cor"]
    passos = [("1", "Siga @" + conta, "O Instagram não mostra todo post para todo mundo. Seguindo, você vê os próximos."),
              ("2", "Ative as notificações", "Toque no sininho do perfil e escolha Posts."),
              ("3", "Salve e mande para alguém", "Salvar e compartilhar faz o post chegar a mais gente.")]
    caixas = "".join(f'<div style="display: flex; align-items: center; gap: 26px; background: {CARD}; border-radius: 18px; padding: 24px 28px"><span style="flex-shrink: 0; width: 72px; height: 72px; border-radius: 16px; background: {cor}; color: {BG}; display: flex; align-items: center; justify-content: center; font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: 50px">{n}</span><div style="display: flex; flex-direction: column; gap: 4px"><span style="font-family: \'Barlow Condensed\', sans-serif; font-weight: 700; font-size: 50px; line-height: 1">{e(t)}</span><span style="font-size: 28px; color: {MUTED}; line-height: 1.3">{e(d)}</span></div></div>' for n, t, d in passos)
    miolo = f'''{topo(conta, cor, card.get("pilula", "NÃO PERCA O PRÓXIMO"), True)}
<div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center; gap: 30px">
<span style="font-weight: 700; font-size: 32px; letter-spacing: 0.12em; color: {cor}">GOSTOU?</span>
<h1 style="margin: 0; font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 120px; line-height: 0.92; text-transform: uppercase">Esse post pode não aparecer de novo</h1>
<span style="font-size: 36px; line-height: 1.3">{e(card.get("promessa") or PAGINAS[conta]["promessa"])}</span>
<div style="display: flex; flex-direction: column; gap: 14px">{caixas}</div>
</div>
{rodape("", "@" + conta)}'''
    return moldura(miolo, card)


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
            subcards = list(card["cards"]) if card["tipo"] == "carrossel" else [card]
            # todo carrossel termina com o lembrete de seguir (desligue com "sem_seguir": true)
            if card["tipo"] == "carrossel" and not card.get("sem_seguir") and subcards[-1]["tipo"] != "seguir":
                subcards.append({"tipo": "seguir", "chamada": "SIGA", "titulo": "Esse post pode não aparecer de novo",
                                 "alt": f"Siga @{conta} e ative as notificações para não perder os próximos posts"})
            nome = f'{card["quando"][:10]}-{conta}-{card["tipo"]}'
            if card.get("sufixo"):
                nome += "-" + card["sufixo"]
            pasta = (RAIZ / "previa" / pauta_arq.stem) if previa else (RAIZ / "fila" / nome)
            midias, alts, creditos = [], [], []
            for i, sub in enumerate(subcards, 1):
                htm = {"agenda": agenda, "destaque": destaque, "pergunta": pergunta, "texto": texto, "seguir": seguir}[sub["tipo"]](conta, sub)
                arq = f"{i:02d}.jpg"
                img = pasta / (f"{nome}-{arq}" if previa else arq)
                trabalhos.append((htm, img))
                midias.append(arq)
                alts.append(sub.get("alt") or f'{sub["chamada"]}: {sub["titulo"]}')
                if sub.get("foto"):
                    c = foto_info(sub["foto"])[1]["credito"] + ", Wikimedia Commons"
                    if c not in creditos:
                        creditos.append(c)
            if card.get("alt") and len(subcards) == 1:
                alts = [card["alt"]]
            if not previa:
                posts.append((pasta, conta, card, midias, alts, creditos))
    renderizar(trabalhos)
    for pasta, conta, card, midias, alts, creditos in posts:
        legenda = card["legenda"]
        if creditos:
            legenda += "\n\n📷 " + " | ".join(creditos)
        post = {
            "conta": conta,
            "tipo": "carrossel" if len(midias) > 1 else "imagem",
            "redes": card.get("redes", ["instagram", "facebook"]),
            "quando": card["quando"],
            "status": "aprovado",
            "midias": midias,
            "textos_alternativos": alts,
            "legenda": legenda,
        }
        # links da bio: [{"titulo": "...", "url": "https://..."}] — aparecem na página de links do perfil
        if card.get("links"):
            post["links"] = card["links"]
        (pasta / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for _, img in trabalhos:
        print(img.relative_to(RAIZ))


if __name__ == "__main__":
    main()
