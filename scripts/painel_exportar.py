"""Gera os arquivos do Painel de Operações (dados/painel/export/*.json) a partir dos dados do robô.
Uso: python scripts/painel_exportar.py   (só lê o repositório; não chama nenhuma API)."""
import json, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
P = R / "dados" / "painel"; E = P / "export"; E.mkdir(parents=True, exist_ok=True)
ld = lambda f, d: json.loads(f.read_text(encoding="utf-8")) if f.exists() else d
CAMPOS = ["data", "operacao", "canal", "plataforma", "seguidores", "posts_total", "visualizacoes_total",
          "alcance_dia", "visualizacoes_dia", "interacoes_dia", "cliques_dia"]
canais = [{k: l.get(k) for k in CAMPOS} for l in ld(P / "historico.json", [])]
op = ld(P / "operacao.json", {})
robo = [{"canal": p["canal"], "publicados": p["publicados"], "ultimos_7_dias": p["ultimos_7_dias"],
         "na_fila": p["na_fila"], "falhas": p["falhas"]} for p in op.get("posts", [])]
nomes = {"Brasil 23:59": "Brasil 23:59", "Brazil on a Budget": "Brazil on a Budget"}
contas = ld(R / "config" / "contas.json", {})
dia = {}
for f in (R / "fila").glob("*/post.json"):
    p = ld(f, {})
    if p.get("status") == "publicado" and p.get("publicado_em"):
        o = nomes.get(contas.get(p.get("conta"), {}).get("nome"), "LLShop")
        k = (p["publicado_em"][:10], o)
        dia[k] = dia.get(k, 0) + 1
posts_dia = [{"data": d, "operacao": o, "posts": n} for (d, o), n in sorted(dia.items())]
vids = []
for canal, lista in ld(P / "youtube_videos.json", {}).items():
    for v in lista:
        vids.append({"canal": canal, "titulo": v["titulo"], "publicado": v["publicado"], "status": v["status"],
                     "agendado": v.get("agendado") or "", "views": v["views"], "likes": v["likes"],
                     "comentarios": v["comentarios"], "id": v["id"]})
extra = [{"indicador": "Respostas automáticas enviadas", "valor": op.get("respostas_automaticas", 0)},
         {"indicador": "Vídeos preparados TAF", "valor": op.get("videos_preparados", {}).get("taf", 0)},
         {"indicador": "Vídeos preparados BHC", "valor": op.get("videos_preparados", {}).get("bhc", 0)}]
for nome, dados in {"canais": canais, "robo": robo, "posts_dia": posts_dia, "youtube_videos": vids,
                    "vendas": ld(P / "vendas.json", []), "robo_extra": extra}.items():
    (E / f"{nome}.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(nome, len(dados))
