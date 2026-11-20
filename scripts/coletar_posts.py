"""Números de CADA post (o "nosso Supermetrics", pedido do Luiz em 20/11/2026).

Para cada post publicado pela Central (fila/*/post.json com "resultado"), pede à Meta os números do post
no Instagram e no Facebook e guarda a evolução em dados/posts.json: uma foto 1, 3 e 7 dias depois de
publicar (d1, d3, d7) e a última leitura ("ultimo"). Posts antigos entram de uma vez (a Meta guarda o total
do post), com a foto marcada como d7. Também junta os vídeos do YouTube (dados/painel/youtube_videos.json)
e do TikTok (dados/painel/tiktok_videos.json, quando a conta der a permissão video.list).

O que só nós sabemos de cada post também vai junto, para comparar: conta, formato, dia e hora de Brasília,
idioma e assunto (o nome da pasta). Quem lê é o scripts/relatorio_redes.py e o painel.

Uso:  python scripts/coletar_posts.py              (de verdade, roda no metricas.yml)
      python scripts/coletar_posts.py --sem-meta   (só YouTube/TikTok e os dados dos posts, sem chamar a Meta)
Só leitura nas contas: nada é publicado ou alterado.
"""
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meta  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "posts.json"
BR = timezone(timedelta(hours=-3))
MAX_POR_REDE = int(os.environ.get("MAX_POSTS_POR_RODADA", "150"))  # o resto entra na rodada seguinte
MARCOS = [("d1", 1), ("d3", 3), ("d7", 7)]

# nome na API do Instagram -> nome no nosso arquivo
IG_NOMES = {"reach": "alcance", "views": "visualizacoes", "likes": "curtidas", "comments": "comentarios",
            "shares": "compartilhamentos", "saved": "salvamentos", "total_interactions": "interacoes",
            "ig_reels_avg_watch_time": "tempo_medio_ms", "replies": "respostas"}
IG_POR_TIPO = {
    "imagem": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"],
    "carrossel": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"],
    "reels": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions", "ig_reels_avg_watch_time"],
    "story": ["reach", "views", "replies", "shares", "total_interactions"],
}
ES = re.compile(r"[¿¡]|\b(el|los|las|qué|cuánto|cuesta|comenta|guía|para tu|viaje)\b", re.I)


def agora():
    return datetime.now(timezone.utc)


def idioma(conta, legenda):
    if conta != "brazilonabudget":
        return "pt"
    primeira = next((l for l in (legenda or "").split("\n") if l.strip()), "")
    return "es" if ES.search(primeira) else "en"


def assunto(pasta, conta):
    nome = pasta.name[11:]  # tira AAAA-MM-DD-
    return nome[len(conta) + 1:] if nome.startswith(conta + "-") else nome


def info_post(pasta, p):
    pub = datetime.fromisoformat(p["publicado_em"].replace("Z", "+00:00"))
    local = pub.astimezone(BR)
    return {"conta": p["conta"], "pasta": pasta.name, "tipo": p.get("tipo", "imagem"), "publicado_em": p["publicado_em"],
            "dia_semana": local.strftime("%a"), "hora": local.hour, "idioma": idioma(p["conta"], p.get("legenda")),
            "assunto": assunto(pasta, p["conta"]), "titulo": next((l for l in p.get("legenda", "").split("\n") if l.strip()), "")[:120]}


def marco_devido(reg, idade_dias):
    """Qual foto tirar agora (ou None). Post antigo sem nenhuma foto vira d7 de uma vez."""
    feitos = reg.get("fotos", {})
    if "d7" in feitos:
        return None
    if idade_dias >= 7:
        return "d7"
    devido = None
    for i, (nome, dias) in enumerate(MARCOS):
        mais_tarde_feito = any(m in feitos for m, _ in MARCOS[i + 1:])
        if idade_dias >= dias and nome not in feitos and not mais_tarde_feito:
            devido = nome
    if devido is None and not feitos and idade_dias >= 0.5:
        return "ultimo"  # primeira leitura do dia seguinte, sem marco ainda
    return devido


def ig_numeros(media_id, tok, tipo, avisos):
    metricas = IG_POR_TIPO.get(tipo, IG_POR_TIPO["imagem"])
    out = {}
    try:
        r = meta.get(f"{media_id}/insights", tok, metric=",".join(metricas))
        for item in r.get("data", []):
            v = item.get("values", [{}])[0].get("value", item.get("total_value", {}).get("value"))
            out[IG_NOMES.get(item["name"], item["name"])] = v
        return out
    except meta.MetaError:
        pass
    for m in metricas:  # alguma métrica não vale para esse post: pede uma a uma
        try:
            r = meta.get(f"{media_id}/insights", tok, metric=m)
            item = r["data"][0]
            out[IG_NOMES.get(m, m)] = item.get("values", [{}])[0].get("value", item.get("total_value", {}).get("value"))
        except (meta.MetaError, KeyError, IndexError) as e:
            avisos.setdefault(f"Instagram {m}: {str(e)[:90]}", 0)
            avisos[f"Instagram {m}: {str(e)[:90]}"] += 1
    return out


def fb_numeros(obj_id, tok, avisos):
    for campos in ("reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0),shares",
                   "reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)",
                   "likes.summary(total_count).limit(0),comments.summary(total_count).limit(0)"):
        try:
            r = meta.get(obj_id, tok, fields=campos)
            out = {"curtidas": (r.get("reactions") or r.get("likes") or {}).get("summary", {}).get("total_count", 0),
                   "comentarios": r.get("comments", {}).get("summary", {}).get("total_count", 0)}
            if "shares" in campos:
                out["compartilhamentos"] = r.get("shares", {}).get("count", 0)
            return out
        except meta.MetaError as e:
            erro = str(e)[:90]
    avisos[f"Facebook: {erro}"] = avisos.get(f"Facebook: {erro}", 0) + 1
    return None


def guardar(reg, marco, numeros):
    quando = agora().isoformat(timespec="seconds")
    reg["ultimo"] = {**numeros, "em": quando}
    if marco and marco != "ultimo":
        reg.setdefault("fotos", {})[marco] = {**numeros, "em": quando}


def coletar_meta(dados, avisos):
    contas = json.loads((RAIZ / "config" / "contas.json").read_text(encoding="utf-8"))
    pendentes = {"ig": [], "fb": []}
    for f in sorted((RAIZ / "fila").glob("*/post.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if p.get("status") != "publicado" or not p.get("publicado_em") or p.get("conta") not in contas:
            continue
        res = p.get("resultado") or {}
        pub = datetime.fromisoformat(p["publicado_em"].replace("Z", "+00:00"))
        idade = (agora() - pub).total_seconds() / 86400
        base = info_post(f.parent, p)
        for rede, chave in (("ig", "instagram"), ("fb", "facebook")):
            pid = str(res.get(chave) or "")
            if not re.fullmatch(r"[0-9_]+", pid):
                continue
            if rede == "ig" and base["tipo"] == "story" and idade > 1:
                continue  # a Meta só dá números de story enquanto ele está no ar (24 h)
            uid = f"{rede}:{pid}"
            reg = dados.setdefault(uid, {"rede": {"ig": "instagram", "fb": "facebook"}[rede], "id": pid})
            reg.update(base)
            marco = marco_devido(reg, idade)
            if base["tipo"] == "story" and rede == "ig" and "d1" not in reg.get("fotos", {}):
                marco = "d1"
            if marco:
                pendentes[rede].append((pub, uid, marco, contas[p["conta"]]))
    tokens_pagina = {}
    for rede, fila in pendentes.items():
        fila.sort(key=lambda x: x[0], reverse=True)  # os mais novos primeiro
        if len(fila) > MAX_POR_REDE:
            print(f"{rede}: {len(fila)} posts para ler; {MAX_POR_REDE} agora, o resto amanhã")
        for _, uid, marco, cfg in fila[:MAX_POR_REDE]:
            tok = os.environ.get(cfg.get("token_secret", ""), "")
            if not tok:
                avisos[f"sem token {cfg.get('token_secret')}"] = 1
                continue
            reg = dados[uid]
            if rede == "ig":
                nums = ig_numeros(reg["id"], tok, reg["tipo"], avisos)
            else:
                page = cfg.get("facebook_page_id")
                if page not in tokens_pagina:
                    tokens_pagina[page] = meta.page_token(page, tok)
                nums = fb_numeros(reg["id"], tokens_pagina[page], avisos)
            if nums:
                guardar(reg, marco, nums)
        print(f"{rede}: {min(len(fila), MAX_POR_REDE)} post(s) lido(s)")


def juntar_videos(dados):
    """YouTube e TikTok: a coleta do painel já traz o total de cada vídeo; aqui vira histórico com d1/d3/d7."""
    fontes = []
    yt = RAIZ / "dados" / "painel" / "youtube_videos.json"
    if yt.exists():
        for canal, vids in json.loads(yt.read_text(encoding="utf-8")).items():
            for v in vids:
                if v.get("status") == "public" and v.get("publicado"):
                    fontes.append(("youtube", canal, v["id"], v["publicado"] + "T12:00:00+00:00", v.get("titulo", ""),
                                   {"visualizacoes": v.get("views", 0), "curtidas": v.get("likes", 0), "comentarios": v.get("comentarios", 0)}))
    tt = RAIZ / "dados" / "painel" / "tiktok_videos.json"
    if tt.exists():
        for v in json.loads(tt.read_text(encoding="utf-8")):
            fontes.append(("tiktok", v["conta"], v["id"], v["publicado_em"], v.get("titulo", ""),
                           {"visualizacoes": v.get("views", 0), "curtidas": v.get("likes", 0),
                            "comentarios": v.get("comentarios", 0), "compartilhamentos": v.get("compartilhamentos", 0)}))
    for rede, conta, vid, quando, titulo, nums in fontes:
        pub = datetime.fromisoformat(quando.replace("Z", "+00:00"))
        local = pub.astimezone(BR)
        reg = dados.setdefault(f"{rede[:2]}:{vid}", {"rede": rede, "id": vid})
        reg.update({"conta": conta, "tipo": "video", "publicado_em": quando, "dia_semana": local.strftime("%a"),
                    "hora": local.hour if rede == "tiktok" else None, "titulo": titulo[:120],
                    "idioma": "es" if ES.search(titulo) else ("en" if rede == "youtube" else reg.get("idioma", "pt"))})
        idade = (agora() - pub).total_seconds() / 86400
        marco = marco_devido(reg, idade)
        guardar(reg, marco, nums)  # o total do vídeo é sempre o mais novo, então "ultimo" acompanha
    print(f"vídeos: {len(fontes)} do YouTube/TikTok")


def main():
    dados = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    avisos = {}
    if "--sem-meta" not in sys.argv:
        coletar_meta(dados, avisos)
    juntar_videos(dados)
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(dict(sorted(dados.items(), key=lambda kv: kv[1].get("publicado_em", ""), reverse=True)),
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(dados)} post(s) em dados/posts.json")
    for a, n in sorted(avisos.items(), key=lambda x: -x[1])[:15]:
        print(f"aviso ({n}x): {a}")


if __name__ == "__main__":
    main()
