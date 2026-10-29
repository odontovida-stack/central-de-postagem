"""Cliente mínimo da Graph API da Meta (Instagram + Facebook), só com a biblioteca padrão.

Os tokens vêm de variáveis de ambiente (GitHub Secrets). Nada é impresso com o token.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v23.0")
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


class MetaError(Exception):
    pass


def _call(method, path, token, params=None, retries=3):
    params = dict(params or {})
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"{BASE}/{path.lstrip('/')}"
    if method == "GET":
        url = f"{url}?{data.decode()}"
        data = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                err = json.loads(body).get("error", {})
            except ValueError:
                err = {"message": body[:300]}
            transient = e.code >= 500 or err.get("is_transient")
            if transient and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise MetaError(f"{method} {path}: {err.get('message', 'erro')} (código {err.get('code')})") from None
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise MetaError(f"{method} {path}: sem conexão ({e.reason})") from None


def get(path, token, **params):
    return _call("GET", path, token, params)


def post(path, token, **params):
    return _call("POST", path, token, params)


# ---------- Instagram ----------

def _wait_container(container_id, token, timeout=300):
    """Espera o Instagram terminar de processar a mídia (status FINISHED)."""
    start = time.time()
    while time.time() - start < timeout:
        st = get(container_id, token, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise MetaError(f"Instagram recusou a mídia {container_id}: {st}")
        time.sleep(5)
    raise MetaError(f"Instagram demorou demais para processar {container_id}")


def ig_publish(ig_user_id, token, kind, media_urls, caption, alt_texts=None):
    """Publica no Instagram. kind: 'imagem', 'carrossel' ou 'reels'. Devolve o id do post."""
    alt_texts = alt_texts or []
    if kind == "imagem":
        p = {"image_url": media_urls[0], "caption": caption}
        if alt_texts:
            p["alt_text"] = alt_texts[0]
        container = post(f"{ig_user_id}/media", token, **p)["id"]
    elif kind == "carrossel":
        children = []
        for i, url in enumerate(media_urls):
            p = {"image_url": url, "is_carousel_item": "true"}
            if i < len(alt_texts) and alt_texts[i]:
                p["alt_text"] = alt_texts[i]
            cid = post(f"{ig_user_id}/media", token, **p)["id"]
            _wait_container(cid, token)
            children.append(cid)
        container = post(f"{ig_user_id}/media", token, media_type="CAROUSEL",
                         children=",".join(children), caption=caption)["id"]
    elif kind == "reels":
        container = post(f"{ig_user_id}/media", token, media_type="REELS",
                         video_url=media_urls[0], caption=caption)["id"]
    else:
        raise MetaError(f"tipo desconhecido: {kind}")
    _wait_container(container, token, timeout=600 if kind == "reels" else 300)
    return post(f"{ig_user_id}/media_publish", token, creation_id=container)["id"]


# ---------- Facebook (Página) ----------

def page_token(page_id, token):
    """Troca o token do usuário do sistema pelo token da própria Página (necessário para postar como a Página)."""
    try:
        t = get(page_id, token, fields="access_token").get("access_token")
    except MetaError:
        t = None
    return t or token


def fb_publish(page_id, token, kind, media_urls, caption):
    """Publica na Página do Facebook. Fotos: uma ou várias no mesmo post."""
    token = page_token(page_id, token)
    if kind == "reels":
        return post(f"{page_id}/videos", token, file_url=media_urls[0], description=caption)["id"]
    if len(media_urls) == 1:
        return post(f"{page_id}/photos", token, url=media_urls[0], caption=caption)["id"]
    attached = []
    for url in media_urls:
        pid = post(f"{page_id}/photos", token, url=url, published="false")["id"]
        attached.append(json.dumps({"media_fbid": pid}))
    params = {"message": caption}
    for i, a in enumerate(attached):
        params[f"attached_media[{i}]"] = a
    return post(f"{page_id}/feed", token, **params)["id"]
