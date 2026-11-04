"""TikTok: conecta contas e manda posts de foto como rascunho (Content Posting API, modo MEDIA_UPLOAD).

As autorizações (refresh_token e open_id de cada conta) ficam em dados/tiktok.enc, trancadas com
openssl (AES-256, chave no secret TIKTOK_CHAVE). Nada de token é impresso.
Uso:  python scripts/tiktok.py conectar <conta> <codigo>   (pela ação "Conectar TikTok")
      python scripts/tiktok.py status                      (mostra quais contas estão conectadas)
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
COFRE = RAIZ / "dados" / "tiktok.enc"
CFG = json.loads((RAIZ / "config" / "tiktok.json").read_text(encoding="utf-8"))
API = "https://open.tiktokapis.com/v2"


class TikTokError(Exception):
    pass


def _chave():
    k = os.environ.get("TIKTOK_CHAVE")
    if not k:
        raise TikTokError("falta o secret TIKTOK_CHAVE")
    return k


def ler_cofre():
    if not COFRE.exists():
        return {}
    env = dict(os.environ, TIKTOK_CHAVE=_chave())
    r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-a", "-pass", "env:TIKTOK_CHAVE", "-in", str(COFRE)],
                       capture_output=True, env=env)
    if r.returncode != 0:
        raise TikTokError("não consegui abrir dados/tiktok.enc (a TIKTOK_CHAVE mudou?)")
    return json.loads(r.stdout.decode())


def gravar_cofre(dados):
    env = dict(os.environ, TIKTOK_CHAVE=_chave())
    COFRE.parent.mkdir(exist_ok=True)
    r = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-a", "-salt", "-pass", "env:TIKTOK_CHAVE", "-out", str(COFRE)],
                       input=json.dumps(dados).encode(), capture_output=True, env=env)
    if r.returncode != 0:
        raise TikTokError("não consegui gravar dados/tiktok.enc")


def _post(url, dados=None, token=None, form=False):
    if form:
        corpo, tipo = urllib.parse.urlencode(dados).encode(), "application/x-www-form-urlencoded"
    else:
        corpo, tipo = json.dumps(dados or {}).encode(), "application/json; charset=UTF-8"
    req = urllib.request.Request(url, data=corpo, method="POST", headers={"Content-Type": tipo})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            res = json.loads(e.read().decode())
        except ValueError:
            raise TikTokError(f"HTTP {e.code} em {url}") from None
    err = res.get("error")
    if isinstance(err, dict) and err.get("code") not in (None, "ok"):
        raise TikTokError(f"{err.get('code')}: {err.get('message', '')}")
    if isinstance(err, str):
        raise TikTokError(f"{err}: {res.get('error_description', '')}")
    return res


def _segredos():
    ck = os.environ.get("TIKTOK_CLIENT_KEY") or CFG.get("client_key")
    cs = os.environ.get("TIKTOK_CLIENT_SECRET")
    if not ck or not cs:
        raise TikTokError("faltam os secrets TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET")
    return ck, cs


def conectar(conta, codigo):
    ck, cs = _segredos()
    res = _post(f"{API}/oauth/token/", {"client_key": ck, "client_secret": cs, "code": codigo.strip(),
                                         "grant_type": "authorization_code", "redirect_uri": CFG["redirect_uri"]}, form=True)
    cofre = ler_cofre()
    cofre[conta] = {"open_id": res["open_id"], "refresh_token": res["refresh_token"], "scope": res.get("scope", ""),
                    "conectado_em": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    gravar_cofre(cofre)
    print(f"{conta}: conectada (permissões: {res.get('scope', '?')})")


def _token(conta, cofre):
    if conta not in cofre:
        return None
    ck, cs = _segredos()
    res = _post(f"{API}/oauth/token/", {"client_key": ck, "client_secret": cs, "grant_type": "refresh_token",
                                         "refresh_token": cofre[conta]["refresh_token"]}, form=True)
    cofre[conta]["refresh_token"] = res.get("refresh_token", cofre[conta]["refresh_token"])
    return res["access_token"]


def url_midia(pasta, arquivo):
    rel = (pasta / arquivo).relative_to(RAIZ).as_posix()
    return CFG["midia_base"].rstrip("/") + "/" + urllib.parse.quote(rel)


def enviar_rascunho(conta, pasta, midias, legenda):
    """Manda as fotos para a caixa de entrada (rascunho) da conta. Devolve o publish_id, ou None se a conta não está conectada."""
    cofre = ler_cofre()
    antes = json.dumps(cofre, sort_keys=True)
    tok = _token(conta, cofre)
    if not tok:
        return None
    if json.dumps(cofre, sort_keys=True) != antes:
        gravar_cofre(cofre)  # o TikTok pode trocar o refresh_token na renovação
    linhas = [l for l in legenda.strip().split("\n") if l.strip()]
    titulo = (linhas[0] if linhas else "")[:89]
    corpo = {"post_info": {"title": titulo, "description": legenda.strip()[:3990]},
             "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0,
                             "photo_images": [url_midia(pasta, m) for m in midias[:35]]},
             "post_mode": "MEDIA_UPLOAD", "media_type": "PHOTO"}
    res = _post(f"{API}/post/publish/content/init/", corpo, token=tok)
    return res.get("data", {}).get("publish_id")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "conectar":
        conectar(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 2 and sys.argv[1] == "status":
        c = ler_cofre()
        for k in CFG["contas"]:
            print(f"{k}: {'conectada em ' + c[k]['conectado_em'] if k in c else 'não conectada'}")
    else:
        print(__doc__)
