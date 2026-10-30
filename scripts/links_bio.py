"""Gera a página de links da bio de cada perfil: links/<conta>.html (publicada pelo GitHub Pages).

Junta os "links" dos posts da fila (mais novos primeiro, até 12) e os links fixos de config/links.json:
  {"brazilonabudget": {"titulo": "Brazil on a Budget", "fixos": [{"titulo": "All 7 guides", "url": "https://..."}]}, ...}
Endereço para pôr na bio: https://odontovida-stack.github.io/central-de-postagem/links/<conta>.html
Os links de afiliado levam o aviso exigido ("links de afiliado: podemos ganhar comissão").
Uso: python scripts/links_bio.py
"""
import html
import json
import pathlib
from datetime import datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CORES = {"jogosnatela": "#2FD17A", "esportesnatela": "#4C9AFF", "tudooqueestreia": "#FF5A5F", "lancamentosdegames": "#A78BFA",
         "showsconfirmados": "#FFB020", "brazilonabudget": "#0F6E8C", "brasil2359": "#FF6B2C"}
AVISO = {"brazilonabudget": "Some links are affiliate links: if you book through them we may earn a small commission, at no extra cost to you.",
         "padrao": "Alguns links são de afiliado: se você comprar por eles, podemos ganhar uma pequena comissão, sem custo extra para você."}


def main():
    cfg_arq = RAIZ / "config" / "links.json"
    cfg = json.loads(cfg_arq.read_text(encoding="utf-8")) if cfg_arq.exists() else {}
    por_conta = {}
    for arq in sorted((RAIZ / "fila").glob("*/post.json"), reverse=True):
        p = json.loads(arq.read_text(encoding="utf-8"))
        for l in p.get("links", []):
            if l.get("url", "").startswith("https://"):
                por_conta.setdefault(p["conta"], []).append({**l, "data": p.get("quando", "")[:10]})
    saida = RAIZ / "links"
    saida.mkdir(exist_ok=True)
    for conta in sorted(set(por_conta) | set(cfg)):
        c = cfg.get(conta, {})
        itens = c.get("fixos", []) + por_conta.get(conta, [])[:12]
        cor = CORES.get(conta, "#333")
        lis = "".join(f'<a class="l" href="{html.escape(i["url"])}" target="_blank" rel="noopener sponsored">{html.escape(i["titulo"])}'
                      + (f'<small>{html.escape(i["data"])}</small>' if i.get("data") else "") + "</a>" for i in itens)
        doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>@{conta} · links</title><style>body{{margin:0;font-family:system-ui,sans-serif;background:#0F1115;color:#F4F4F5}}
main{{max-width:520px;margin:0 auto;padding:32px 16px;display:flex;flex-direction:column;gap:12px}}h1{{font-size:22px;margin:0 0 8px}}
.l{{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:16px 18px;border-radius:14px;background:#181B21;color:#F4F4F5;text-decoration:none;border-left:6px solid {cor};font-weight:600}}
.l small{{color:#B4B8C0;font-weight:400}}p{{color:#B4B8C0;font-size:13px;line-height:1.4}}</style></head><body><main>
<h1>{html.escape(c.get("titulo", "@" + conta))}</h1>{lis or "<p>Em breve.</p>"}<p>{html.escape(AVISO.get(conta, AVISO["padrao"]))}</p>
<p>Atualizado em {datetime.now().strftime("%d/%m/%Y")}</p></main></body></html>"""
        (saida / f"{conta}.html").write_text(doc, encoding="utf-8")
        print(conta, len(itens), "links")


if __name__ == "__main__":
    main()
