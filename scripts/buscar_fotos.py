"""Busca e baixa fotos de licença livre para os cards (roda no GitHub Actions).

Lê fotos/pedidos.json: uma lista de {"nome": "rio-pao-de-acucar", "busca": "Sugarloaf Mountain Rio de Janeiro", "opcao": 1}.
Para cada pedido que ainda não tem fotos/banco/<nome>.jpg:
  1. procura no Openverse (Flickr, Wikimedia e outros) só fotos com uso comercial e modificação permitidos;
  2. escolhe a opção pedida (1 = a melhor) entre as fotos grandes e em boa resolução;
  3. baixa, recorta para 1080 x 1350 (retrato 4:5) e grava fotos/banco/<nome>.jpg;
  4. grava fotos/banco/<nome>.json com autor, licença, link e o crédito pronto para o card.
Com "formato": "paisagem" (fotos de fundo dos slides do YouTube), procura fotos largas e recorta para 1920 x 1080.
Para trocar uma foto, apague o .jpg e mude "opcao" para 2, 3...

Uso: python scripts/buscar_fotos.py
"""
import io
import re
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
PEDIDOS = RAIZ / "fotos" / "pedidos.json"
BANCO = RAIZ / "fotos" / "banco"
UA = {"User-Agent": "central-de-postagem/1.0 (github.com/odontovida-stack/central-de-postagem)"}
LICENCAS = {"cc0": "CC0", "pdm": "Domínio público", "by": "CC BY", "by-sa": "CC BY-SA"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def baixar(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


LOG = []


def log(msg):
    print(msg)
    LOG.append(msg)


FORMATOS = {"retrato": ((1080, 1350), "tall,square,wide", 1600), "paisagem": ((1920, 1080), "wide", 2400)}


def candidatos_commons(busca, formato="retrato"):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                                "gsrsearch": f"{busca} filetype:bitmap", "gsrlimit": 20, "prop": "imageinfo",
                                "iiprop": "url|size|extmetadata", "iiurlwidth": FORMATOS[formato][2]})
    dados = get_json(f"https://commons.wikimedia.org/w/api.php?{q}")
    res = []
    for pg in sorted(dados.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99)):
        ii = (pg.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = (meta.get("LicenseShortName", {}).get("value") or "").lower()
        if not any(k in lic for k in ("cc0", "public domain", "cc by")) or "nc" in lic or "nd" in lic:
            continue
        if min(ii.get("width", 0), ii.get("height", 0)) < 1000:
            continue
        if formato == "paisagem" and ii.get("width", 0) < 1600:
            continue
        autor = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value") or "").strip()
        res.append({"url": ii.get("thumburl") or ii.get("url"), "creator": autor[:60], "license": lic,
                    "license_url": meta.get("LicenseUrl", {}).get("value"), "source": "wikimedia",
                    "foreign_landing_url": ii.get("descriptionurl"), "title": pg.get("title")})
    return res


def candidatos(busca, formato="retrato"):
    q = urllib.parse.urlencode({"q": busca, "license": ",".join(LICENCAS), "category": "photograph",
                                "aspect_ratio": FORMATOS[formato][1], "size": "large", "page_size": 20, "mature": "false"})
    dados = get_json(f"https://api.openverse.org/v1/images/?{q}")
    res = []
    for item in dados.get("results", []):
        w, h = item.get("width") or 0, item.get("height") or 0
        if w and h and min(w, h) < 1000:
            continue
        if formato == "paisagem" and w and w < 1600:
            continue
        res.append(item)
    return res


def recortar(conteudo, formato="retrato"):
    img = Image.open(io.BytesIO(conteudo))
    img = ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.fit(img, FORMATOS[formato][0], method=Image.LANCZOS, centering=(0.5, 0.45))


def main():
    if not PEDIDOS.exists():
        print("Sem fotos/pedidos.json")
        return
    BANCO.mkdir(parents=True, exist_ok=True)
    pedidos = json.loads(PEDIDOS.read_text(encoding="utf-8"))
    for p in pedidos:
        nome, busca, opcao = p["nome"], p["busca"], int(p.get("opcao", 1))
        formato = p.get("formato", "retrato") if p.get("formato") in FORMATOS else "retrato"
        destino = BANCO / f"{nome}.jpg"
        if destino.exists():
            continue
        lista = []
        try:
            lista = candidatos(busca, formato)
        except Exception as e:  # noqa: BLE001
            log(f"Openverse falhou para {nome}: {e}")
        if not lista:
            try:
                lista = candidatos_commons(busca, formato)
            except Exception as e:  # noqa: BLE001
                log(f"Wikimedia falhou para {nome}: {e}")
        ok = False
        for item in lista[opcao - 1:]:
            try:
                img = recortar(baixar(item["url"]), formato)
            except Exception as e:  # noqa: BLE001
                log(f"  pulando {item.get('id')}: {e}")
                continue
            img.save(destino, "JPEG", quality=88)
            lic = LICENCAS.get(item.get("license", ""), (item.get("license") or "").upper().replace("CC-BY", "CC BY"))
            autor = (item.get("creator") or "autor desconhecido").strip()
            info = {"nome": nome, "busca": busca, "opcao": opcao, "formato": formato, "titulo": item.get("title"), "autor": autor,
                    "licenca": lic, "licenca_url": item.get("license_url"), "fonte": item.get("source"),
                    "pagina": item.get("foreign_landing_url"), "credito": f"Foto: {autor} · {lic}"}
            (BANCO / f"{nome}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log(f"OK {nome}: {info['credito']} ({info['pagina']})")
            ok = True
            break
        if not ok:
            log(f"NADA para {nome} ({busca})")
        time.sleep(1)
    (RAIZ / "fotos" / "ultimo-log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
