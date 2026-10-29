"""Confere todos os posts da fila antes de aprovar.

Uso:  python scripts/validar.py            (todos)
      python scripts/validar.py fila/2026-11-02-rio-carrossel
Sai com erro (código 1) se algum post tiver problema.
"""
import json
import pathlib
import struct
import sys
from datetime import datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TIPOS = {"imagem", "carrossel", "reels"}
STATUS = {"rascunho", "aprovado", "publicado", "erro"}
REDES = {"instagram", "facebook", "tiktok"}


def jpeg_size(path):
    """Lê largura e altura de um JPEG sem bibliotecas externas."""
    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            b = f.read(1)
            while b and b != b"\xff":
                b = f.read(1)
            while b == b"\xff":
                b = f.read(1)
            if not b:
                return None
            marker = b[0]
            if marker in (0xC0, 0xC1, 0xC2):
                f.read(3)
                h, w = struct.unpack(">HH", f.read(4))
                return w, h
            length = struct.unpack(">H", f.read(2))[0]
            f.seek(length - 2, 1)


def validar_post(pasta, contas):
    erros = []
    arq = pasta / "post.json"
    if not arq.exists():
        return [f"{pasta.name}: falta o post.json"]
    try:
        p = json.loads(arq.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"{pasta.name}: post.json inválido ({e})"]

    def err(msg):
        erros.append(f"{pasta.name}: {msg}")

    if p.get("conta") not in contas:
        err(f"conta '{p.get('conta')}' não existe em config/contas.json")
    if p.get("tipo") not in TIPOS:
        err(f"tipo deve ser um de {sorted(TIPOS)}")
    if p.get("status") not in STATUS:
        err(f"status deve ser um de {sorted(STATUS)}")
    redes = p.get("redes", [])
    if not redes or not set(redes) <= REDES:
        err(f"redes deve listar {sorted(REDES)}")
    try:
        datetime.fromisoformat(p.get("quando", ""))
    except ValueError:
        err("'quando' deve ser data e hora ISO, ex.: 2026-11-02T18:30:00-03:00")
    leg = p.get("legenda", "")
    if not leg.strip():
        err("legenda vazia")
    if len(leg) > 2200:
        err(f"legenda com {len(leg)} caracteres (máximo do Instagram: 2.200)")
    if leg.count("#") > 30:
        err("mais de 30 hashtags")
    midias = p.get("midias", [])
    if not midias:
        err("nenhuma mídia em 'midias'")
    if p.get("tipo") == "carrossel" and not (2 <= len(midias) <= 10):
        err("carrossel precisa de 2 a 10 imagens")
    if p.get("tipo") in ("imagem", "reels") and len(midias) != 1:
        err(f"{p.get('tipo')} precisa de exatamente 1 mídia")
    for m in midias:
        f = pasta / m
        if not f.exists():
            err(f"arquivo não encontrado: {m}")
            continue
        if p.get("tipo") == "reels":
            if f.suffix.lower() != ".mp4":
                err(f"{m}: Reels precisa ser .mp4")
            continue
        if f.suffix.lower() not in (".jpg", ".jpeg"):
            err(f"{m}: o Instagram só aceita JPEG")
            continue
        if f.stat().st_size > 8 * 1024 * 1024:
            err(f"{m}: maior que 8 MB")
        dim = jpeg_size(f)
        if not dim:
            err(f"{m}: não consegui ler o JPEG")
            continue
        w, h = dim
        ratio = w / h
        if not (0.8 - 0.01 <= ratio <= 1.91 + 0.01):
            err(f"{m}: proporção {w}x{h} fora do aceito (4:5 a 1,91:1)")
        if w < 320:
            err(f"{m}: largura {w}px é pequena demais")
    alts = p.get("textos_alternativos", [])
    if alts and len(alts) != len(midias):
        err("textos_alternativos deve ter um texto por mídia")
    return erros


def main():
    contas = json.loads((RAIZ / "config" / "contas.json").read_text(encoding="utf-8"))
    alvos = [pathlib.Path(a).resolve() for a in sys.argv[1:]] or sorted(
        d for d in (RAIZ / "fila").iterdir() if d.is_dir())
    todos = []
    for pasta in alvos:
        todos += validar_post(pasta, contas)
    if todos:
        print("Problemas encontrados:")
        for e in todos:
            print("  -", e)
        sys.exit(1)
    print(f"Tudo certo: {len(alvos)} post(s) conferido(s).")


if __name__ == "__main__":
    main()
