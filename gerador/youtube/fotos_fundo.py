"""Fotos de fundo dos slides do YouTube (fotos/banco/<nome>.jpg + .json, baixadas pelo robô de fotos).

Usado por slides.py (fundo + crédito no canto) e por scripts/youtube.py (seção PHOTOS da descrição).
Foto que ainda não foi baixada não é erro: o slide sai sem foto e um aviso é impresso.
"""
import json
from pathlib import Path

BANCO = Path(__file__).resolve().parent.parent.parent / "fotos" / "banco"
SITES = {"wikimedia": "Wikimedia Commons", "flickr": "Flickr"}


def foto(nome):
    """(jpg, info) da foto do banco, ou None se ainda não existe."""
    jpg, meta = BANCO / f"{nome}.jpg", BANCO / f"{nome}.json"
    if not jpg.exists():
        return None
    info = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
    return jpg, info


def credito(info):
    """'Photo: <autor> · <licença> · Wikimedia Commons' (o mesmo crédito do llshop.foto_info, em inglês)."""
    texto = (info.get("credito") or "").strip()
    for prefixo in ("Foto:", "Photo:"):
        if texto.startswith(prefixo):
            texto = texto[len(prefixo):].strip()
    if not texto:
        texto = " · ".join(x for x in (info.get("autor") or "unknown author", info.get("licenca")) if x)
    return f"Photo: {texto} · {SITES.get(info.get('fonte') or 'wikimedia', info.get('fonte') or 'Wikimedia Commons')}"


def creditos_do_video(*arquivos_slides):
    """Créditos únicos (na ordem em que aparecem) das fotos usadas nos slides.json/thumb.json dados."""
    vistos = []
    for arq in arquivos_slides:
        arq = Path(arq)
        if not arq.exists():
            continue
        for s in json.loads(arq.read_text(encoding="utf-8")):
            achada = foto(s["foto"]) if s.get("foto") else None
            if achada:
                c = credito(achada[1])
                if c not in vistos:
                    vistos.append(c)
    return vistos


def descricao_com_creditos(desc, creditos, limite=5000):
    """Acrescenta a seção PHOTOS no fim da descrição sem passar do limite do YouTube."""
    if not creditos:
        return desc
    itens = [c[len("Photo: "):] if c.startswith("Photo: ") else c for c in creditos]
    sites = {c.rsplit(" · ", 1)[-1] for c in itens}
    if len(sites) == 1:  # todas do mesmo site: o nome vai uma vez só no título, para caber mais créditos
        site = sites.pop()
        base = desc.rstrip() + f"\n\nPHOTOS ({site})\n"
        itens = [c.rsplit(" · ", 1)[0] for c in itens]
    else:
        base = desc.rstrip() + "\n\nPHOTOS\n"
    linhas = []
    for i, c in enumerate(itens):
        resto = len(itens) - i - 1
        cauda = f"\n(+{resto} more, credited on screen)" if resto else ""
        if len(base) + len("\n".join(linhas + [c])) + len(cauda) > limite:
            faltam = len(itens) - len(linhas)
            print(f"AVISO descrição: {faltam} crédito(s) de foto não couberam nos {limite} caracteres (ficam só na tela)")
            fim = f"(+{faltam} more, credited on screen)"
            texto = base + "\n".join(linhas + [fim])
            return texto if len(texto) <= limite else desc[:limite]
        linhas.append(c)
    return base + "\n".join(linhas)
