"""Confere a ligação com a Meta sem publicar nada.

Para cada conta com token: lê o perfil do Instagram, prepara (sem publicar) uma imagem
da fila para ver se o Instagram consegue baixá-la, e confere se o token pode postar na Página.
Grava o resultado em dados/teste_conexao.json. O token nunca é gravado nem impresso.
"""
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meta  # noqa: E402
from publicar import url_publica  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def uma_imagem_da_fila(conta):
    for pasta in sorted(d for d in (RAIZ / "fila").iterdir() if d.is_dir()):
        arq = pasta / "post.json"
        if arq.exists():
            p = json.loads(arq.read_text(encoding="utf-8"))
            if p.get("conta") == conta and p.get("tipo") in ("imagem", "carrossel"):
                return url_publica(pasta, p["midias"][0])
    return None


def main():
    contas = json.loads((RAIZ / "config" / "contas.json").read_text(encoding="utf-8"))
    saida = {"quando": datetime.now(timezone.utc).isoformat(timespec="seconds"), "contas": {}}
    for chave, cfg in contas.items():
        tok = os.environ.get(cfg.get("token_secret") or "")
        if not tok:
            continue
        r = {}
        ig, pg = cfg.get("instagram_user_id"), cfg.get("facebook_page_id")
        try:
            r["instagram_perfil"] = meta.get(ig, tok, fields="username,followers_count,media_count")
        except meta.MetaError as e:
            r["instagram_perfil"] = f"ERRO {e}"
        img = uma_imagem_da_fila(chave)
        if img:
            try:
                cid = meta.post(f"{ig}/media", tok, image_url=img, caption="teste (não publicado)")["id"]
                meta._wait_container(cid, tok, timeout=120)
                r["instagram_preparar_imagem"] = "OK (preparada e descartada, nada foi publicado)"
            except meta.MetaError as e:
                r["instagram_preparar_imagem"] = f"ERRO {e}"
        try:
            ptok = meta.page_token(pg, tok)
            r["facebook_token_da_pagina"] = "OK" if ptok != tok else "usando o token do usuário do sistema"
            info = meta.get(pg, ptok, fields="name,followers_count")
            r["facebook_pagina"] = info
        except meta.MetaError as e:
            r["facebook_pagina"] = f"ERRO {e}"
        try:
            perms = meta.get("me/permissions", tok).get("data", [])
            r["permissoes"] = sorted(p["permission"] for p in perms if p.get("status") == "granted")
        except meta.MetaError as e:
            r["permissoes"] = f"(não deu para listar: {e})"
        saida["contas"][chave] = r
        print(chave, json.dumps(r, ensure_ascii=False))
    (RAIZ / "dados" / "teste_conexao.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
