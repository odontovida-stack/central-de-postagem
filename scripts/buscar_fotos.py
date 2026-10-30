"""Busca e baixa fotos de licença livre para os cards (roda no GitHub Actions).

Lê fotos/pedidos.json: uma lista de {"nome": "rio-pao-de-acucar", "busca": "Sugarloaf Mountain Rio de Janeiro", "opcao": 1}.
Para cada pedido que ainda não tem fotos/banco/<nome>.jpg:
  1. procura no Openverse (Flickr, Wikimedia e outros) só fotos com uso comercial e modificação permitidos;
  2. escolhe a opção pedida (1 = a melhor) entre as fotos grandes e em boa resolução;
  3. baixa, recorta para 1080 x 1350 (retrato 4:5) e grava fotos/banco/<nome>.jpg;
  4. grava fotos/banco/<nome>.json com autor, licença, link e o crédito pronto para o card.
Para trocar uma foto, apague o .jpg e mude "opcao" para 2, 3...

Uso: python scripts/buscar_fotos.py
"""
import io
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


def candidatos(busca):
    q = urllib.parse.urlencode({"q": busca, "license": ",".join(LICENCAS), "category": "photograph",
                                "aspect_ratio": "tall,square,wide", "size": "large", "page_size": 20, "mature": "false"})
    dados = get_json(f"https://api.openverse.org/v1/images/?{q}")
    res = []
    for item in dados.get("results", []):
        w, h = item.get("width") or 0, item.get("height") or 0
        if w and h and min(w, h) < 1000:
            continue
        res.append(item)
    return res


def recortar(conteudo):
    img = Image.open(io.BytesIO(conteudo))
    img = ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.fit(img, (1080, 1350), method=Image.LANCZOS, centering=(0.5, 0.45))


def main():
    if not PEDIDOS.exists():
        print("Sem fotos/pedidos.json")
        return
    BANCO.mkdir(parents=True, exist_ok=True)
    pedidos = json.loads(PEDIDOS.read_text(encoding="utf-8"))
    for p in pedidos:
        nome, busca, opcao = p["nome"], p["busca"], int(p.get("opcao", 1))
        destino = BANCO / f"{nome}.jpg"
        if destino.exists():
            continue
        try:
            lista = candidatos(busca)
        except Exception as e:  # noqa: BLE001
            print(f"ERRO na busca de {nome}: {e}")
            continue
        ok = False
        for item in lista[opcao - 1:]:
            try:
                img = recortar(baixar(item["url"]))
            except Exception as e:  # noqa: BLE001
                print(f"  pulando {item.get('id')}: {e}")
                continue
            img.save(destino, "JPEG", quality=88)
            lic = LICENCAS.get(item.get("license", ""), item.get("license", "").upper())
            autor = (item.get("creator") or "autor desconhecido").strip()
            info = {"nome": nome, "busca": busca, "opcao": opcao, "titulo": item.get("title"), "autor": autor,
                    "licenca": lic, "licenca_url": item.get("license_url"), "fonte": item.get("source"),
                    "pagina": item.get("foreign_landing_url"), "credito": f"Foto: {autor} · {lic}"}
            (BANCO / f"{nome}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"OK {nome}: {info['credito']} ({info['pagina']})")
            ok = True
            break
        if not ok:
            print(f"NADA para {nome} ({busca})")
        time.sleep(1)


if __name__ == "__main__":
    main()
