"""Pins do Pinterest do Brazil on a Budget (pedido do Luiz em 12/11/2026).

Gera pinterest/pins/<id>.jpg (1000x1500, formato 2:3 que o Pinterest prefere) e pinterest/pins.csv no
formato de "Criar Pins em massa" do Pinterest (Title, Media URL, Pinterest board, Thumbnail, Description,
Link, Publish date, Keywords). As imagens ficam no GitHub Pages, então o CSV já aponta para elas.
Fotos: só as do banco (fotos/banco/), com o crédito da licença na imagem e na descrição.
Uso: python gerador/pinterest.py
"""
import csv
import html
import json
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
FONTES = Path(__file__).resolve().parent / "fontes"
BANCO = RAIZ / "fotos" / "banco"
SAIDA = RAIZ / "pinterest"
BASE = "https://odontovida-stack.github.io/central-de-postagem/pinterest/pins/"
LOJA_EN = "https://payhip.com/QuickBudgetGuides"
e = html.escape

LINKS = json.loads((RAIZ / "config" / "links.json").read_text(encoding="utf-8"))["brazilonabudget"]["hotmart_es"]

# id, idioma, foto, titulo, subtitulo, preco "desde", link, quadro
PINS = [
    ("en-rio", "en", "rio-cristo", "Rio de Janeiro in 5 days", "Day-by-day plan with real prices", "from US$ 370", LOJA_EN, "Rio de Janeiro Travel"),
    ("en-iguazu", "en", "foz-cataratas", "Iguazu Falls in 4 days", "Brazil + Argentina sides, real prices", "from US$ 280", LOJA_EN, "Iguazu Falls Travel"),
    ("en-floripa", "en", "floripa-praia", "Florianópolis in 5 days", "Beaches, budget and where to stay", None, LOJA_EN, "Brazil Beaches"),
    ("en-salvador", "en", "salvador-pelourinho", "Salvador in 4 days", "Pelourinho, beaches and real prices", None, LOJA_EN, "Brazil Travel Guides"),
    ("en-saopaulo", "en", "saopaulo-paulista", "São Paulo in 4 days", "Food, neighborhoods, real prices", None, LOJA_EN, "Brazil Travel Guides"),
    ("en-paraty", "en", "paraty-ruas", "Paraty in 3 days", "Colonial town, islands, waterfalls", None, LOJA_EN, "Brazil Travel Guides"),
    ("en-lencois", "en", "lencois-dunas", "Lençóis Maranhenses", "The dunes and lagoons, step by step", None, LOJA_EN, "Brazil Travel Guides"),
    ("en-camboriu", "en", "camboriu-praia", "Balneário Camboriú", "Beaches, cable car and real prices", None, "https://payhip.com/b/DfFRG", "Brazil Beaches"),
    ("en-carnaval", "en", "rio-carnaval-sapucai-3", "Rio Carnival 2027", "Dates, tickets, blocos and safety", None, "https://payhip.com/b/zSt9f", "Rio de Janeiro Travel"),
    ("en-bundle", "en", "rio-pao-de-acucar", "Brazil: 7 travel guides", "Rio, Iguazu, Floripa, Salvador and more", None, "https://payhip.com/b/VejO0", "Brazil Travel Guides"),
    ("es-rio", "es", "rio-cristo", "Río de Janeiro en 5 días", "Plan día por día con precios reales", "desde US$ 370", LINKS["rio"], "Viajar a Río de Janeiro"),
    ("es-foz", "es", "foz-cataratas", "Cataratas del Iguazú en 4 días", "Lado brasileño y argentino", "desde US$ 280", LINKS["foz"], "Cataratas del Iguazú"),
    ("es-floripa", "es", "floripa-praia", "Florianópolis en 5 días", "Playas, presupuesto y dónde dormir", None, LINKS["floripa"], "Playas de Brasil"),
    ("es-salvador", "es", "salvador-pelourinho", "Salvador de Bahía en 4 días", "Pelourinho, playas y precios reales", None, LINKS["salvador"], "Guías de viaje Brasil"),
    ("es-saopaulo", "es", "saopaulo-paulista", "São Paulo en 4 días", "Comida, barrios y precios reales", None, LINKS["sp"], "Guías de viaje Brasil"),
    ("es-paraty", "es", "paraty-ruas", "Paraty en 3 días", "Pueblo colonial, islas y cascadas", None, LINKS["paraty"], "Guías de viaje Brasil"),
    ("es-lencois", "es", "lencois-dunas", "Lençóis Maranhenses", "Dunas y lagunas, paso a paso", None, LINKS["lencois"], "Guías de viaje Brasil"),
    ("es-camboriu", "es", "camboriu-praia", "Camboriú 2026/27", "Playas, teleférico y precios reales", None, LINKS["camboriu"], "Playas de Brasil"),
    ("es-carnaval", "es", "rio-carnaval-sapucai-3", "Carnaval de Río 2027", "Fechas, entradas, blocos y seguridad", None, LINKS["carnaval"], "Viajar a Río de Janeiro"),
    ("es-pack7", "es", "rio-pao-de-acucar", "Brasil: las 7 guías", "Río, Iguazú, Floripa, Salvador y más", None, LINKS["pack7"], "Guías de viaje Brasil"),
    ("es-packsur", "es", "floripa-praia", "Floripa + Iguazú", "2 guías en 1 pack: playas y cataratas", None, LINKS["packsur"], "Playas de Brasil"),
]

TXT = {
    "en": {"selo": "PDF TRAVEL GUIDE", "precos": "Real prices · checked Oct 2026", "cta": "Get the guide →",
           "desc": "{t}: {s}. Short PDF guide by Brazil on a Budget with a day-by-day plan, real prices in US dollars, where to stay, scams to avoid and Google Maps routes.",
           "kw": "brazil travel, {t}, travel guide pdf, budget travel, south america"},
    "es": {"selo": "GUÍA DE VIAJE EN PDF", "precos": "Precios reales · octubre 2026", "cta": "Ver la guía →",
           "desc": "{t}: {s}. Guía corta en PDF de Brazil on a Budget con plan día por día, precios reales en dólares, dónde alojarse, estafas a evitar y rutas en Google Maps.",
           "kw": "viajar a brasil, {t}, guia de viaje pdf, viajar barato, sudamerica"},
}


def fonte(fam, peso, arq):
    return f"@font-face{{font-family:'{fam}';font-weight:{peso};src:url('file://{FONTES}/{arq}')}}"


CSS = (fonte("B", 400, "barlow-latin-400-normal.woff2") + fonte("B", 600, "barlow-latin-600-normal.woff2") +
       fonte("B", 700, "barlow-latin-700-normal.woff2") + fonte("C", 800, "barlow-condensed-latin-800-normal.woff2") +
       fonte("C", 700, "barlow-condensed-latin-700-normal.woff2") + """
body{margin:0}#p{width:1000px;height:1500px;position:relative;overflow:hidden;font-family:B;color:#fff;background:#0b2a3a}
.f{position:absolute;inset:0;background-size:cover;background-position:center}
.v{position:absolute;inset:0;background:linear-gradient(180deg,rgba(6,24,34,.55) 0%,rgba(6,24,34,.05) 30%,rgba(6,24,34,.35) 55%,rgba(6,24,34,.95) 82%)}
.m{position:absolute;left:70px;right:70px;top:70px;display:flex;align-items:center;gap:16px;font:700 30px B;letter-spacing:.06em}
.m i{width:22px;height:22px;border-radius:50%;background:#F5C542;display:inline-block}
.c{position:absolute;left:70px;right:70px;bottom:120px;display:flex;flex-direction:column;gap:22px}
.s{align-self:flex-start;background:#F5C542;color:#0b2a3a;font:700 28px B;letter-spacing:.08em;padding:10px 20px;border-radius:8px}
h1{margin:0;font:800 118px/0.95 C;text-transform:uppercase}
.sub{font:600 44px/1.2 B}
.r{display:flex;gap:18px;flex-wrap:wrap;font:600 32px B;color:#d8e6ec}
.b{margin-top:10px;align-self:flex-start;background:#fff;color:#0b2a3a;font:700 38px B;padding:18px 34px;border-radius:60px}
.cr{position:absolute;right:30px;bottom:24px;font:400 18px B;color:rgba(255,255,255,.75)}
""")


def pagina(pin):
    pid, lang, foto, titulo, sub, preco, _link, _q = pin
    t = TXT[lang]
    cred = json.loads((BANCO / f"{foto}.json").read_text(encoding="utf-8"))["credito"].replace("Foto:", "Photo:" if lang == "en" else "Foto:")
    linhas = [t["precos"]] + ([preco] if preco else [])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div id="p">
<div class="f" style="background-image:url('file://{BANCO}/{foto}.jpg')"></div><div class="v"></div>
<div class="m"><i></i>BRAZIL ON A BUDGET</div>
<div class="c"><span class="s">{e(t["selo"])}</span><h1>{e(titulo)}</h1><div class="sub">{e(sub)}</div>
<div class="r">{"".join(f"<span>· {e(x)}</span>" for x in linhas)}</div><span class="b">{e(t["cta"])}</span></div>
<div class="cr">{e(cred)} · Wikimedia Commons</div></div></body></html>""", cred


def main():
    (SAIDA / "pins").mkdir(parents=True, exist_ok=True)
    inicio = date.today() + timedelta(days=1)
    linhas = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1000, "height": 1500})
        tmp = SAIDA / "_tmp.html"
        for i, pin in enumerate(PINS):
            htm, cred = pagina(pin)
            tmp.write_text(htm, encoding="utf-8")
            pg.goto(tmp.as_uri())
            pg.wait_for_timeout(300)
            arq = SAIDA / "pins" / f"{pin[0]}.jpg"
            pg.locator("#p").screenshot(path=str(arq), type="jpeg", quality=90)
            pid, lang, _f, titulo, sub, _pr, link, quadro = pin
            t = TXT[lang]
            desc = t["desc"].format(t=titulo, s=sub) + f" ({cred}, Wikimedia Commons)"
            # um pin por dia, alternando EN e ES, às 10h de Brasília (13:00 UTC)
            quando = (inicio + timedelta(days=i)).isoformat() + "T13:00:00"
            linhas.append({"Title": titulo[:100], "Media URL": BASE + arq.name, "Pinterest board": quadro, "Thumbnail": "",
                           "Description": desc[:500], "Link": link, "Publish date": quando,
                           "Keywords": t["kw"].format(t=titulo.lower())})
        tmp.unlink(missing_ok=True)
        b.close()
    with open(SAIDA / "pins.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} pins em {SAIDA}")


if __name__ == "__main__":
    main()
