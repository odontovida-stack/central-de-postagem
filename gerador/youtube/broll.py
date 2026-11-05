"""B-roll: trechos de vídeo de domínio público ou licença livre (Wikimedia Commons) no meio dos slides.

Para cada slide de slides.json com "tipo": "broll":
  {"tipo": "broll", "commons": "File:Nome do arquivo.webm", "inicio": 12, "duracao": 10,
   "legenda": "Washington, D.C., 1962", "file": "005"}
baixa o arquivo pela API do Commons, confere a licença (só domínio público, CC0, CC BY e CC BY-SA),
corta o trecho, ajusta para 1920x1080 a 30 fps sem som, põe a legenda e o crédito no canto (mesmas fontes
dos slides) e grava <slides_dir>/NNN.mp4, NNN.png (um quadro) e NNN.broll (o crédito, em JSON).
O montar_video.py repete o trecho (em vez de acelerar) até cobrir o tempo da narração do slide.
Os créditos vão para <pasta>/broll_creditos.json, que o scripts/youtube.py põe na seção FOOTAGE da descrição.

Regra do canal: só lugares, mapas, objetos, documentos, máquinas e paisagens. Nada de pessoas identificáveis.
Quem escolhe o arquivo (o roteiro) confere isso; este script só confere a licença.
Uso: python broll.py <pasta do vídeo> <slides_dir>"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

F = Path(__file__).resolve().parent / "fontes"
CACHE = Path(os.environ.get("BROLL_CACHE", Path(__file__).resolve().parent.parent.parent / "saida-youtube" / "broll-cache"))
UA = {"User-Agent": "central-de-postagem/1.0 (YouTube B-roll; https://github.com/odontovida-stack/central-de-postagem)"}
API = "https://commons.wikimedia.org/w/api.php"
LIVRES = re.compile(r"^(public domain|pd\b|pd-|cc0|cc by(-sa)? ?\d|cc-by(-sa)?-\d|no restrictions)", re.I)


def limpar(txt):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", txt or ""))).strip()


def info_commons(titulo):
    q = urllib.parse.urlencode({"action": "query", "titles": titulo, "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size",
                                "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(f"{API}?{q}", headers=UA), timeout=60) as r:
        pagina = next(iter(json.loads(r.read().decode())["query"]["pages"].values()))
    if "imageinfo" not in pagina:
        raise SystemExit(f"B-roll: arquivo não encontrado no Commons: {titulo}")
    ii = pagina["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    licenca = limpar(meta.get("LicenseShortName", {}).get("value"))
    if not LIVRES.search(licenca):
        raise SystemExit(f"B-roll: licença não aceita ({licenca or 'sem licença'}) em {titulo}")
    autor = limpar(meta.get("Artist", {}).get("value")) or "unknown author"
    return {"url": ii["url"], "pagina": ii.get("descriptionurl", ""), "licenca": licenca, "autor": autor[:120], "titulo": titulo}


def baixar(info):
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / re.sub(r"[^\w.-]", "_", info["titulo"].split(":", 1)[-1])
    if not destino.exists():
        with urllib.request.urlopen(urllib.request.Request(info["url"], headers=UA), timeout=300) as r, open(destino, "wb") as f:
            while bloco := r.read(1 << 20):
                f.write(bloco)
    return destino


def sobreposicao(pg, legenda, credito, png, tema):
    rgb = {"taf": "192,57,43", "bhc": "201,162,39"}.get(tema, "192,57,43")
    css = "".join(f"@font-face{{font-family:'{a}';font-weight:{w};src:url('file://{F}/{n}')}}" for a, w, n in [
        ("S", 700, "source-serif-4-latin-700-normal.woff2"), ("M", 500, "ibm-plex-mono-latin-500-normal.woff2")])
    pg.set_content(f"""<html><head><style>{css}html,body{{margin:0;background:transparent}}
#c{{width:1920px;height:1080px;position:relative;background:linear-gradient(180deg,rgba(0,0,0,0) 62%,rgba(0,0,0,.62) 100%)}}
.l{{position:absolute;left:120px;bottom:118px;font:700 56px S;color:#F4EFE6;max-width:1500px;line-height:1.15;text-shadow:0 2px 18px rgba(0,0,0,.6)}}
.b{{position:absolute;left:120px;bottom:96px;width:120px;height:5px;background:rgb({rgb})}}
.k{{position:absolute;right:60px;bottom:40px;font:500 22px M;color:rgba(244,239,230,.75);max-width:1100px;text-align:right}}</style></head>
<body><div id="c">{'<div class="l">' + html.escape(legenda) + '</div><div class="b"></div>' if legenda else ''}
<div class="k">{html.escape(credito)}</div></div></body></html>""")
    pg.evaluate("document.fonts.ready")
    pg.locator("#c").screenshot(path=str(png), omit_background=True)


def rodar(*a):
    subprocess.run([str(x) for x in a], check=True)


def main():
    pasta, sdir = Path(sys.argv[1]), Path(sys.argv[2])
    slides = json.loads((pasta / "slides.json").read_text(encoding="utf-8"))
    trechos = [(i, s) for i, s in enumerate(slides, 1) if s.get("tipo") == "broll"]
    if not trechos:
        return
    from playwright.sync_api import sync_playwright
    tema = os.environ.get("TEMA_SLIDES", "taf")
    creditos = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for i, s in trechos:
            info = info_commons(s["commons"])
            arq = baixar(info)
            credito = f"Footage: {info['autor']} · {info['licenca']} · Wikimedia Commons"
            ov = sdir / f"{i:03d}.overlay.png"
            sobreposicao(pg, s.get("legenda", ""), credito, ov, tema)
            mp4, png = sdir / f"{i:03d}.mp4", sdir / f"{i:03d}.png"
            dur = min(float(s.get("duracao", 10)), 20.0)
            filtro = ("[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,"
                      "eq=saturation=0.85:brightness=-0.03[v];[v][1:v]overlay=0:0,format=yuv420p")
            rodar("ffmpeg", "-y", "-loglevel", "error", "-ss", str(s.get("inicio", 0)), "-t", f"{dur:.2f}", "-i", arq, "-i", ov,
                  "-filter_complex", filtro, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", mp4)
            rodar("ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i", mp4, "-frames:v", "1", png)
            (sdir / f"{i:03d}.broll").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
            ov.unlink()
            if credito not in creditos:
                creditos.append(credito)
            print("b-roll", s["commons"], f"{dur}s ->", mp4.name)
        b.close()
    (pasta / "broll_creditos.json").write_text(json.dumps(creditos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
