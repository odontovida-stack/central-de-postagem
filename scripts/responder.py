"""Responde comentários com palavra-chave: manda a DM (resposta privada) e responde no comentário.

Regras em config/respostas.json. Já respondidos em dados/respondidos.json (só o id do comentário e a data,
apagados depois de 90 dias). Roda junto com o robô de publicação, a cada 5 minutos.
Uso: python scripts/responder.py            (de verdade)
     SIMULAR=1 python scripts/responder.py  (só mostra o que faria)
"""
import json
import os
import pathlib
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meta  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FEITOS = RAIZ / "dados" / "respondidos.json"
SIMULAR = os.environ.get("SIMULAR") == "1"
DIAS_POSTS = 14        # olha os comentários dos posts dos últimos 14 dias
LIMITE_POR_VEZ = 25    # no máximo 25 respostas por rodada (evita parecer spam)


def normal(txt):
    t = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode().upper()
    return set(re.findall(r"[A-Z0-9]+", t))


def regra_do_comentario(regras, texto):
    palavras = normal(texto)
    for r in regras:
        if r.get("ativo", True) and palavras & {normal(p).pop() for p in r["palavras"] if normal(p)}:
            return r
    return None


def resposta_privada(cfg, tok, page_tok, comment_id, texto):
    corpo = {"recipient": json.dumps({"comment_id": comment_id}), "message": json.dumps({"text": texto})}
    try:
        return meta.post(f"{cfg['facebook_page_id']}/messages", page_tok, **corpo)
    except meta.MetaError as e1:
        try:
            return meta.post(f"{cfg['instagram_user_id']}/messages", tok, **corpo)
        except meta.MetaError as e2:
            raise meta.MetaError(f"{e1} | {e2}") from None


def main():
    regras_cfg = json.loads((RAIZ / "config" / "respostas.json").read_text(encoding="utf-8"))
    contas = json.loads((RAIZ / "config" / "contas.json").read_text(encoding="utf-8"))
    feitos = json.loads(FEITOS.read_text(encoding="utf-8")) if FEITOS.exists() else {}
    agora = datetime.now(timezone.utc)
    feitos = {k: v for k, v in feitos.items() if datetime.fromisoformat(v) > agora - timedelta(days=90)}
    total, falhas = 0, 0
    for conta, regras in regras_cfg.items():
        if conta.startswith("_") or not any(r.get("ativo", True) for r in regras):
            continue
        cfg = contas.get(conta, {})
        tok = os.environ.get(cfg.get("token_secret", ""))
        if not tok or not cfg.get("instagram_user_id"):
            print(f"{conta}: sem token ou sem id, pulei")
            continue
        try:
            eu = meta.get(cfg["instagram_user_id"], tok, fields="username").get("username")
            midias = meta.get(f"{cfg['instagram_user_id']}/media", tok, fields="id,timestamp", limit=20).get("data", [])
            page_tok = meta.page_token(cfg["facebook_page_id"], tok) if cfg.get("facebook_page_id") else tok
        except meta.MetaError as e:
            print(f"{conta}: não consegui ler os posts ({e})")
            falhas += 1
            continue
        for m in midias:
            quando = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
            if quando < agora - timedelta(days=DIAS_POSTS):
                continue
            try:
                coms = meta.get(f"{m['id']}/comments", tok, fields="id,text,username,timestamp", limit=50).get("data", [])
            except meta.MetaError as e:
                print(f"{conta}: comentários de {m['id']} indisponíveis ({e})")
                continue
            for c in coms:
                if c["id"] in feitos or c.get("username") == eu:
                    continue
                r = regra_do_comentario(regras, c.get("text", ""))
                if not r:
                    continue
                if total >= LIMITE_POR_VEZ:
                    print("limite da rodada atingido, o resto fica para a próxima")
                    break
                print(f"{conta}: @{c.get('username')} comentou {c.get('text', '')[:40]!r} → DM + resposta")
                if SIMULAR:
                    total += 1
                    continue
                try:
                    resposta_privada(cfg, tok, page_tok, c["id"], r["dm"])
                    meta.post(f"{c['id']}/replies", tok, message=r["resposta"])
                    feitos[c["id"]] = agora.isoformat(timespec="seconds")
                    total += 1
                except meta.MetaError as e:
                    print(f"{conta}: falhou para o comentário {c['id']} ({e})")
                    falhas += 1
    if not SIMULAR:
        FEITOS.parent.mkdir(exist_ok=True)
        FEITOS.write_text(json.dumps(feitos, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"respostas nesta rodada: {total}, falhas: {falhas}")


if __name__ == "__main__":
    main()
