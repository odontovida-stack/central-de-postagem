"""Avisa o Luiz no celular quando um rascunho chega no TikTok (pedido dele em 20/11/2026).

Como: um comentário com @odontovida-stack numa issue fixa do repositório ("📲 TikTok: rascunhos para
publicar"). O app do GitHub manda a notificação no celular. A issue é criada sozinha na primeira vez.
Precisa de GITHUB_TOKEN/GH_TOKEN e GITHUB_REPOSITORY no ambiente (o workflow "Publicar" já passa).
Nunca derruba a publicação: qualquer erro aqui só vira um print.
"""
import json
import os
import urllib.request

TITULO = "📲 TikTok: rascunhos para publicar"
DONO = "odontovida-stack"
NOMES = {"brasil2359": "@brasil.2359", "brazilonabudget": "@brazilonabudget", "tudooqueestreia": "@tudooqueestreia",
         "jogosnatela": "@jogosnatela", "esportesnatela": "@esportesnatela", "lancamentosdegames": "@lancamentosdegames",
         "showsconfirmados": "@showsconfirmados"}


def _api(metodo, caminho, corpo=None):
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not tok or not repo:
        raise RuntimeError("sem GH_TOKEN/GITHUB_REPOSITORY")
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/{caminho}", method=metodo,
                                 data=json.dumps(corpo).encode() if corpo is not None else None,
                                 headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def _issue():
    for i in _api("GET", "issues?state=open&per_page=100&creator=app%2Fgithub-actions") or []:
        if i.get("title") == TITULO:
            return i["number"]
    for i in _api("GET", "issues?state=open&per_page=100") or []:
        if i.get("title") == TITULO and "pull_request" not in i:
            return i["number"]
    nova = _api("POST", "issues", {"title": TITULO, "body": (
        "Toda vez que o robô manda um post para a caixa de entrada do TikTok, ele comenta aqui e o app do "
        "GitHub te avisa no celular.\n\nPara publicar: abra o app do TikTok na conta indicada → **Caixa de entrada** → "
        "toque no aviso do rascunho → confira → **Publicar**. O TikTok trava com 5 rascunhos esperando, então publique no mesmo dia.\n\n"
        "Não feche esta issue: ela é reaproveitada.")})
    return nova["number"]


def rascunho_tiktok(conta, pasta, post, resultado_tiktok):
    """Chamado pelo publicar.py depois de tentar o TikTok."""
    try:
        nome = NOMES.get(conta, conta)
        primeira = next((l for l in post.get("legenda", "").split("\n") if l.strip()), pasta.name)
        video = any(str(m).lower().endswith(".mp4") for m in post.get("midias", []))
        if resultado_tiktok.startswith("RASCUNHO"):
            passos = (f"Abra o TikTok na conta **{nome}** → **Caixa de entrada** → toque no rascunho → **Publicar**.")
            if video:
                passos += " É vídeo: cole a legenda abaixo antes de publicar."
        else:
            passos = (f"O envio automático não deu certo ({resultado_tiktok[:160]}). Suba à mão pelo app do TikTok "
                      f"na conta **{nome}**, com a legenda abaixo. As imagens estão em `fila/{pasta.name}/`.")
        corpo = (f"@{DONO} 📲 Chegou no TikTok: **{primeira[:120]}**\n\n{passos}\n\n"
                 f"<details><summary>Legenda para copiar</summary>\n\n```\n{post.get('legenda', '').strip()}\n```\n</details>")
        _api("POST", f"issues/{_issue()}/comments", {"body": corpo})
    except Exception as e:  # noqa: BLE001 - aviso nunca derruba a publicação
        print(f"aviso do TikTok não foi enviado: {e}")
