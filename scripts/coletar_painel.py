"""Coleta a "foto do dia" de todas as operações e grava em dados/painel/.

Alimenta o Painel de Operações. Roda junto com o metricas.yml (todo dia de manhã) e a mão.
Arquivos gerados:
  dados/painel/historico.json  uma linha por dia por canal: {data, operacao, canal, plataforma, seguidores,
                               posts_total, visualizacoes_total, alcance_dia, interacoes_dia, cliques_dia}
  dados/painel/youtube_videos.json  vídeos de cada canal com visualizações, likes e comentários (foto atual)
  dados/painel/operacao.json   números do robô: posts publicados, na fila, falhas, respostas automáticas
  dados/painel/avisos.json     o que não deu para coletar (para corrigir), sem nenhum token
Nada aqui publica ou altera as contas: só leitura.
"""
import json
import os
import pathlib
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meta  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
OUT = RAIZ / "dados" / "painel"
BR = timezone(timedelta(hours=-3))
OPERACAO = {"brasil2359": "Brasil 23:59", "brazilonabudget": "Brazil on a Budget"}  # o resto é LLShop
avisos = []


def ig(nome, cfg, dia):
    tok = os.environ.get(cfg.get("token_secret", ""), "")
    if not tok:
        avisos.append(f"{nome}: sem token no ambiente")
        return []
    linhas = []
    base = {"data": dia.isoformat(), "operacao": OPERACAO.get(nome, "LLShop"), "canal": cfg.get("nome", nome)}
    try:
        p = meta.get(cfg["instagram_user_id"], tok, fields="followers_count,media_count")
        linha = {**base, "plataforma": "Instagram", "seguidores": int(p.get("followers_count", 0)),
                 "posts_total": int(p.get("media_count", 0))}
        desde = datetime.combine(dia, datetime.min.time(), tzinfo=BR)
        for campo, metricas in {"alcance_dia": ["reach"], "visualizacoes_dia": ["views"],
                                "interacoes_dia": ["total_interactions"], "cliques_dia": ["profile_links_taps"]}.items():
            for m in metricas:
                try:
                    r = meta.get(f"{cfg['instagram_user_id']}/insights", tok, metric=m, period="day",
                                 metric_type="total_value", since=int(desde.timestamp()),
                                 until=int((desde + timedelta(days=1)).timestamp()))
                    linha[campo] = int(r["data"][0]["total_value"]["value"])
                    break
                except (meta.MetaError, KeyError, IndexError) as e:
                    avisos.append(f"{nome} instagram {m}: {str(e)[:160]}")
        linhas.append(linha)
    except meta.MetaError as e:
        avisos.append(f"{nome} instagram perfil: {str(e)[:160]}")
    if cfg.get("facebook_page_id"):
        try:
            pt = meta.page_token(cfg["facebook_page_id"], tok)
            f = meta.get(cfg["facebook_page_id"], pt, fields="followers_count,fan_count")
            linhas.append({**base, "plataforma": "Facebook",
                           "seguidores": int(f.get("followers_count") or f.get("fan_count") or 0)})
        except meta.MetaError as e:
            avisos.append(f"{nome} facebook: {str(e)[:160]}")
    return linhas


def yt_get(url, tk):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tk}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def youtube(dia):
    cid, seg = os.environ.get("YT_CLIENT_ID"), os.environ.get("YT_CLIENT_SECRET")
    linhas, videos = [], {}
    for canal, nome in (("taf", "The American File"), ("bhc", "Before History Changed")):
        rt = os.environ.get(f"YT_REFRESH_TOKEN_{canal.upper()}")
        if not (cid and seg and rt):
            avisos.append(f"youtube {canal}: sem chaves no ambiente")
            continue
        try:
            dados = f"client_id={cid}&client_secret={seg}&refresh_token={rt}&grant_type=refresh_token".encode()
            req = urllib.request.Request("https://oauth2.googleapis.com/token", dados,
                                         {"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=60) as r:
                tk = json.loads(r.read().decode())["access_token"]
            api = "https://www.googleapis.com/youtube/v3/"
            ch = yt_get(api + "channels?part=statistics,contentDetails&mine=true", tk)["items"][0]
            st = ch["statistics"]
            linhas.append({"data": dia.isoformat(), "operacao": "YouTube", "canal": nome, "plataforma": "YouTube",
                           "seguidores": int(st.get("subscriberCount", 0)), "posts_total": int(st.get("videoCount", 0)),
                           "visualizacoes_total": int(st.get("viewCount", 0))})
            up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
            ids, token_pag = [], ""
            for _ in range(4):
                r = yt_get(api + f"playlistItems?part=contentDetails&maxResults=50&playlistId={up}{token_pag}", tk)
                ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
                if not r.get("nextPageToken"):
                    break
                token_pag = "&pageToken=" + r["nextPageToken"]
            lista = []
            for i in range(0, len(ids), 50):
                r = yt_get(api + "videos?part=snippet,statistics,status&id=" + ",".join(ids[i:i + 50]), tk)
                for v in r.get("items", []):
                    s = v.get("statistics", {})
                    lista.append({"id": v["id"], "titulo": v["snippet"]["title"],
                                  "publicado": v["snippet"].get("publishedAt", "")[:10],
                                  "status": v["status"].get("privacyStatus"),
                                  "agendado": (v["status"].get("publishAt") or "")[:16],
                                  "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                                  "comentarios": int(s.get("commentCount", 0))})
            videos[nome] = sorted(lista, key=lambda x: x["publicado"], reverse=True)
        except Exception as e:  # noqa: BLE001
            avisos.append(f"youtube {canal}: {str(e)[:160]}")
    return linhas, videos


def operacao(contas):
    por = {n: {"canal": c.get("nome", n), "publicados": 0, "na_fila": 0, "falhas": 0, "ultimos_7_dias": 0}
           for n, c in contas.items()}
    hoje = datetime.now(BR).date()
    for f in (RAIZ / "fila").glob("*/post.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        d = por.setdefault(p.get("conta", "?"), {"canal": p.get("conta", "?"), "publicados": 0, "na_fila": 0,
                                                 "falhas": 0, "ultimos_7_dias": 0})
        st = p.get("status")
        if st == "publicado":
            d["publicados"] += 1
            try:
                if (hoje - datetime.fromisoformat(p.get("publicado_em", "")[:10]).date()).days < 7:
                    d["ultimos_7_dias"] += 1
            except ValueError:
                pass
        elif st in ("aprovado", "pendente", "agendado"):
            d["na_fila"] += 1
        elif st in ("falhou", "erro"):
            d["falhas"] += 1
    resp = RAIZ / "dados" / "respondidos.json"
    try:
        r = json.loads(resp.read_text(encoding="utf-8")) if resp.exists() else {}
        n_resp = len(r) if isinstance(r, (list, dict)) else 0
    except ValueError:
        n_resp = 0
    yt_pastas = {c: len(list((RAIZ / "youtube" / c).glob("*/"))) for c in ("taf", "bhc") if (RAIZ / "youtube" / c).exists()}
    return {"atualizado": datetime.now(BR).isoformat(timespec="minutes"), "posts": list(por.values()),
            "respostas_automaticas": n_resp, "videos_preparados": yt_pastas}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dia = datetime.now(BR).date()
    contas = json.loads((RAIZ / "config" / "contas.json").read_text(encoding="utf-8"))
    linhas = []
    for nome, cfg in contas.items():
        linhas += ig(nome, cfg, dia - timedelta(days=1))
    yl, videos = youtube(dia)
    linhas += yl
    tk = OUT / "tiktok.json"  # gravado antes por scripts/tiktok.py numeros
    nomes = {k: v.get("nome", k) for k, v in contas.items()}
    for t in (json.loads(tk.read_text(encoding="utf-8")) if tk.exists() else []):
        linhas.append({"operacao": OPERACAO.get(t["conta"], "LLShop"), "canal": nomes.get(t["conta"], t["conta"]),
                       "plataforma": "TikTok", "seguidores": int(t.get("seguidores", 0)), "posts_total": int(t.get("videos", 0)),
                       "interacoes_dia": None})
    for l in linhas:
        l["data"] = dia.isoformat()  # a foto é de hoje; alcance/interações/cliques são do dia anterior
    hist_f = OUT / "historico.json"
    hist = json.loads(hist_f.read_text(encoding="utf-8")) if hist_f.exists() else []
    hist = [h for h in hist if h["data"] != dia.isoformat()] + linhas
    hist_f.write_text(json.dumps(hist, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (OUT / "youtube_videos.json").write_text(json.dumps(videos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (OUT / "operacao.json").write_text(json.dumps(operacao(contas), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (OUT / "avisos.json").write_text(json.dumps({"data": dia.isoformat(), "avisos": avisos}, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    print(f"{len(linhas)} linhas para {dia}; {len(avisos)} aviso(s)")


if __name__ == "__main__":
    main()
