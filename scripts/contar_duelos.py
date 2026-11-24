"""Conta os votos (A ou B) dos Duelos publicados nas últimas 48 h (pedido do Luiz em 23/11/2026).

Lê os comentários do Instagram e do Facebook de cada post "duelo" (sufixo -duelo) e grava dados/duelos.json:
{"<pasta>": {"a": 12, "b": 7, "total": 19, "nome_a": "...", "nome_b": "...", "contado_em": "..."}}
O robô "Posts do dia" (00:41) usa esse arquivo para o post de RESULTADO. Roda no workflow "Contar votos dos duelos".
Um voto por pessoa e por rede (vale o primeiro comentário que escolhe A ou B).
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import meta  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def voto(texto, nome_a, nome_b):
    t = norm(texto).strip()
    if "🅰" in texto and "🅱" not in texto:
        return "a"
    if "🅱" in texto and "🅰" not in texto:
        return "b"
    if re.fullmatch(r"[\W_]*(letra\s*)?a[\W_]*(!+)?", t) or re.match(r"^(time|opcao|letra|voto)\s*a\b", t):
        return "a"
    if re.fullmatch(r"[\W_]*(letra\s*)?b[\W_]*(!+)?", t) or re.match(r"^(time|opcao|letra|voto)\s*b\b", t):
        return "b"
    na, nb = norm(nome_a), norm(nome_b)
    ta, tb = bool(na) and na in t, bool(nb) and nb in t
    if ta and not tb:
        return "a"
    if tb and not ta:
        return "b"
    return None


def comentarios(obj, tok, campo):
    out, url = [], f"{obj}/comments"
    params = {"fields": f"{campo},from,username", "limit": 100}
    for _ in range(10):
        r = meta.get(url, tok, **params)
        out += r.get("data", [])
        nxt = (r.get("paging") or {}).get("cursors", {}).get("after")
        if not nxt or not (r.get("paging") or {}).get("next"):
            break
        params["after"] = nxt
    return out


def main():
    contas = json.loads((RAIZ / "config/contas.json").read_text(encoding="utf-8"))
    saida = RAIZ / "dados/duelos.json"
    dados = json.loads(saida.read_text(encoding="utf-8")) if saida.exists() else {}
    agora = datetime.now(timezone.utc)
    for f in sorted((RAIZ / "fila").glob("*-duelo/post.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        if p.get("status") != "publicado" or not p.get("publicado_em"):
            continue
        pub = datetime.fromisoformat(p["publicado_em"].replace("Z", "+00:00"))
        if agora - pub > timedelta(hours=48):
            continue
        cfg = contas.get(p.get("conta")) or {}
        tok = os.environ.get(cfg.get("token_secret", ""), "")
        if not tok:
            continue
        nome_a, nome_b = p.get("duelo_a", ""), p.get("duelo_b", "")
        if not nome_a:  # tira os nomes da legenda ("🅰️ Livro" / "🅱️ Filme")
            m_a = re.search(r"🅰️?\s*([^\n]+)", p.get("legenda", ""))
            m_b = re.search(r"🅱️?\s*([^\n]+)", p.get("legenda", ""))
            nome_a, nome_b = (m_a.group(1).strip() if m_a else ""), (m_b.group(1).strip() if m_b else "")
        votos, vistos = {"a": 0, "b": 0}, set()
        res = p.get("resultado") or {}
        try:
            if str(res.get("instagram", "")).isdigit():
                for c in comentarios(res["instagram"], tok, "text"):
                    quem = ("ig", c.get("username") or (c.get("from") or {}).get("id") or c.get("id"))
                    v = voto(c.get("text", ""), nome_a, nome_b)
                    if v and quem not in vistos:
                        vistos.add(quem); votos[v] += 1
            fb = str(res.get("facebook", ""))
            if re.fullmatch(r"[0-9_]+", fb):
                pt = meta.page_token(cfg["facebook_page_id"], tok)
                for c in comentarios(fb, pt, "message"):
                    quem = ("fb", (c.get("from") or {}).get("id") or c.get("id"))
                    v = voto(c.get("message", ""), nome_a, nome_b)
                    if v and quem not in vistos:
                        vistos.add(quem); votos[v] += 1
        except meta.MetaError as e:
            print(f"{f.parent.name}: {e}")
        dados[f.parent.name] = {**votos, "total": votos["a"] + votos["b"], "nome_a": nome_a, "nome_b": nome_b,
                                "contado_em": agora.isoformat(timespec="seconds")}
        print(f"{f.parent.name}: A {votos['a']} × B {votos['b']}")
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
