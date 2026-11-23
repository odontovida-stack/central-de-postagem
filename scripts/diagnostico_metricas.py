"""Diagnóstico da coleta por post (23/11/2026): mostra, para alguns posts com números zerados, o que a Meta
devolve. Só imprime números e mensagens de erro, nunca tokens. Roda pelo workflow "Diagnóstico de métricas"."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import meta  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
contas = json.loads((RAIZ / "config/contas.json").read_text(encoding="utf-8"))
dados = json.loads((RAIZ / "dados/posts.json").read_text(encoding="utf-8"))
por_conta = {}
for uid, r in sorted(dados.items(), key=lambda x: x[1].get("publicado_em", ""), reverse=True):
    if r.get("rede") in ("instagram", "facebook") and r.get("ultimo") and not any((r["ultimo"].get(k) or 0) for k in r["ultimo"] if k != "em"):
        por_conta.setdefault((r["conta"], r["rede"]), []).append(r)
print("===== CONTAS =====")
for conta, cfg in contas.items():
    tok = os.environ.get(cfg.get("token_secret", ""), "")
    try:
        r = meta.get(cfg["instagram_user_id"], tok, fields="username,followers_count,follows_count,media_count")
        print(conta, r)
        ins = meta.get(f"{cfg['instagram_user_id']}/insights", tok, metric="reach,views,accounts_engaged", period="day", metric_type="total_value")
        print("  últimas 24h:", {i["name"]: i.get("total_value", {}).get("value") for i in ins.get("data", [])})
    except meta.MetaError as e:
        print(conta, "ERRO", e)
    try:
        pt = meta.page_token(cfg["facebook_page_id"], tok)
        r = meta.get(cfg["facebook_page_id"], pt, fields="name,followers_count,fan_count")
        print("  facebook:", r)
    except meta.MetaError as e:
        print("  facebook ERRO", e)
for (conta, rede), regs in sorted(por_conta.items()):
    cfg = contas.get(conta) or {}
    tok = os.environ.get(cfg.get("token_secret", ""), "")
    print(f"\n===== {conta} · {rede} · {len(regs)} zerados =====")
    if not tok:
        print("sem token"); continue
    if rede == "facebook":
        try:
            tok = meta.page_token(cfg["facebook_page_id"], tok)
        except meta.MetaError as e:
            print("page_token:", e); continue
    for r in regs[:2]:
        print(f"-- {r['pasta']} ({r['tipo']}, publicado {r['publicado_em']})")
        try:
            if rede == "instagram":
                print("  campos:", meta.get(r["id"], tok, fields="like_count,comments_count,media_product_type,media_type,timestamp,owner"))
                for m in ("reach", "views", "likes", "total_interactions"):
                    try:
                        print(f"  insights {m}:", json.dumps(meta.get(f"{r['id']}/insights", tok, metric=m).get("data"))[:300])
                    except meta.MetaError as e:
                        print(f"  insights {m}: ERRO {e}")
            else:
                print("  campos:", json.dumps(meta.get(r["id"], tok, fields="created_time,reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0),shares"))[:300])
                try:
                    print("  insights:", json.dumps(meta.get(f"{r['id']}/insights", tok, metric="post_impressions_unique,post_clicks").get("data"))[:300])
                except meta.MetaError as e:
                    print("  insights: ERRO", e)
        except meta.MetaError as e:
            print("  ERRO", e)
