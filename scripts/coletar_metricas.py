"""Coleta os números de cada conta uma vez por dia e grava em dados/metricas.json.

Este arquivo é o que alimenta o Painel de Crescimento das Páginas.
Uso:  python scripts/coletar_metricas.py            (de verdade)
      python scripts/coletar_metricas.py --simular  (sem chamar a Meta)

Formato de cada linha (igual ao do painel):
  {data, semana, pagina, plataforma, seguidores, alcance, curtidas, comentarios,
   compartilhamentos, salvamentos, cliques_link, posts}
Os nomes de métricas da Meta mudam de tempos em tempos; cada métrica é pedida
separadamente, e a que falhar vira 0 com um aviso, sem derrubar a coleta.
"""
import json
import os
import pathlib
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meta  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "metricas.json"
INICIO = date.fromisoformat(os.environ.get("DATA_INICIO", "2026-11-02"))

IG_METRICAS = {  # nome no painel -> nome na API do Instagram (total do dia)
    "alcance": "reach",
    "curtidas": "likes",
    "comentarios": "comments",
    "compartilhamentos": "shares",
    "salvamentos": "saves",
    "cliques_link": "profile_links_taps",
}


def ig_total(ig_id, tok, metrica, desde, ate, avisos):
    try:
        r = meta.get(f"{ig_id}/insights", tok, metric=metrica, period="day",
                     metric_type="total_value", since=int(desde.timestamp()), until=int(ate.timestamp()))
        return int(r["data"][0]["total_value"]["value"])
    except (meta.MetaError, KeyError, IndexError) as e:
        avisos.append(f"{metrica}: {e}")
        return 0


def coletar_instagram(nome, cfg, dia, avisos):
    tok = os.environ.get(cfg.get("token_secret", ""), "")
    ig_id = cfg.get("instagram_user_id")
    if not tok or not ig_id:
        avisos.append(f"{nome}: sem token ou instagram_user_id, pulando")
        return None
    perfil = meta.get(ig_id, tok, fields="followers_count,media_count")
    desde = datetime.combine(dia, datetime.min.time(), tzinfo=timezone(timedelta(hours=-3)))
    ate = desde + timedelta(days=1)
    linha = {"seguidores": int(perfil.get("followers_count", 0))}
    for campo, metrica in IG_METRICAS.items():
        linha[campo] = ig_total(ig_id, tok, metrica, desde, ate, avisos)
    return linha


def main():
    simular = "--simular" in sys.argv
    contas = json.loads((RAIZ / "config" / "contas.json").read_text(encoding="utf-8"))
    ontem = (datetime.now(timezone(timedelta(hours=-3))) - timedelta(days=1)).date()
    semana = (ontem - INICIO).days // 7 + 1
    linhas = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else []
    linhas = [l for l in linhas if l.get("data") != ontem.isoformat()]
    posts_por_conta = {}
    for pasta in (RAIZ / "fila").iterdir():
        f = pasta / "post.json"
        if f.exists():
            p = json.loads(f.read_text(encoding="utf-8"))
            if p.get("status") == "publicado" and p.get("publicado_em", "")[:10] == ontem.isoformat():
                posts_por_conta[p["conta"]] = posts_por_conta.get(p["conta"], 0) + 1
    avisos = []
    novas = 0
    for nome, cfg in contas.items():
        if simular:
            dados = {"seguidores": 0, **{k: 0 for k in IG_METRICAS}}
        else:
            try:
                dados = coletar_instagram(nome, cfg, ontem, avisos)
            except meta.MetaError as e:
                avisos.append(f"{nome}: {e}")
                dados = None
        if dados is None:
            continue
        linhas.append({"data": ontem.isoformat(), "semana": semana, "pagina": cfg.get("nome", nome),
                       "plataforma": "Instagram", **dados, "posts": posts_por_conta.get(nome, 0)})
        novas += 1
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(linhas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{novas} conta(s) coletada(s) para {ontem}.")
    for a in avisos:
        print("aviso:", a)


if __name__ == "__main__":
    main()
