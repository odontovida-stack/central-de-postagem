"""Descobre sozinho o id da Página do Facebook e o id do Instagram de cada conta.

Usa o token de cada conta (GitHub Secrets), pergunta à Meta quais Páginas ele enxerga
e casa cada Página com a conta pelo nome de usuário do Instagram (campo "instagram_username").
Grava os ids em config/contas.json. Ids não são segredo; o token nunca é impresso.

Rodar à mão:  python scripts/descobrir_ids.py
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meta  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CONTAS = RAIZ / "config" / "contas.json"


def paginas_do_token(token):
    """Lista as Páginas que o token enxerga, com o Instagram ligado a cada uma."""
    achadas, depois = [], None
    while True:
        params = {"fields": "id,name,instagram_business_account{id,username}", "limit": 100}
        if depois:
            params["after"] = depois
        r = meta.get("me/accounts", token, **params)
        achadas += r.get("data", [])
        depois = r.get("paging", {}).get("cursors", {}).get("after")
        if not depois or not r.get("paging", {}).get("next"):
            return achadas


def main():
    contas = json.loads(CONTAS.read_text(encoding="utf-8"))
    cache, mudou, avisos = {}, False, []
    for chave, cfg in contas.items():
        segredo = cfg.get("token_secret")
        tok = os.environ.get(segredo or "")
        if not tok:
            avisos.append(f"{chave}: o segredo {segredo} ainda não foi criado no GitHub, pulando")
            continue
        if segredo not in cache:
            try:
                cache[segredo] = paginas_do_token(tok)
            except meta.MetaError as e:
                avisos.append(f"{chave}: a Meta recusou o token {segredo}: {e}")
                cache[segredo] = []
        alvo = (cfg.get("instagram_username") or "").lower().lstrip("@")
        achou = None
        for pg in cache[segredo]:
            ig = pg.get("instagram_business_account") or {}
            if alvo and (ig.get("username") or "").lower() == alvo:
                achou = (pg, ig)
                break
        if not achou:
            vistas = ", ".join(f"{p.get('name')} (@{(p.get('instagram_business_account') or {}).get('username', 'sem Instagram')})" for p in cache[segredo]) or "nenhuma"
            avisos.append(f"{chave}: não achei a Página ligada a @{alvo}. Páginas que o token enxerga: {vistas}")
            continue
        pg, ig = achou
        if cfg.get("facebook_page_id") != pg["id"] or cfg.get("instagram_user_id") != ig["id"]:
            cfg["facebook_page_id"], cfg["instagram_user_id"] = pg["id"], ig["id"]
            mudou = True
        print(f"OK {chave}: Página '{pg.get('name')}' = {pg['id']} · Instagram @{ig.get('username')} = {ig['id']}")
    if mudou:
        CONTAS.write_text(json.dumps(contas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("config/contas.json atualizado.")
    for a in avisos:
        print("AVISO", a)


if __name__ == "__main__":
    main()
