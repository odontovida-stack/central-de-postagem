"""Robô de vídeo do YouTube (roda no GitHub Actions depois do merge).

Cada vídeo é uma pasta youtube/<canal>/<nome>/ com:
  video.json      título, canal, data/hora, tags, voz, mapa dos slides e o status
  roteiro.md      o roteiro de produção (PARTs + linhas [VISUAL: ...])
  narracao.json   os blocos de narração, um por PART: [{"arquivo": "01.mp3", "texto": "..."}]
  descricao.txt   a descrição do YouTube
  slides.json     os slides (gerador/youtube/slides.py)
  thumb.json      a thumbnail (mesmo gerador, 1920x1080, reduzida para 1280x720)
  short.json      opcional: o Short de chamada {"slides": [números dos slides], "texto": "...", "titulo": "..."}
  audio/          opcional: MP3 já gravados (se existirem, a narração automática é pulada)

O que o robô faz com cada video.json de "status": "aprovado" que ainda não tem "video_id":
  1. narra os blocos que faltam em audio/ pela API do ElevenLabs (secret ELEVENLABS_API_KEY);
  2. gera os slides e a thumbnail;
  3. monta o MP4 (cada slide fica na tela o tempo da narração que vem depois dele);
  4. envia ao YouTube como privado e agendado para "quando" (secrets YT_CLIENT_ID, YT_CLIENT_SECRET,
     YT_REFRESH_TOKEN_<CANAL>), com "não é para crianças" e "conteúdo sintético" marcados, e põe a thumbnail;
  5. se houver short.json, monta e agenda o Short antes do vídeo longo ("short_antes_horas", padrão 24);
     A descrição recebe no fim a seção PHOTOS com os créditos das fotos de fundo dos slides (campo "foto")
     e a seção FOOTAGE com os trechos de vídeo (slides "tipo": "broll", gerador/youtube/broll.py).
  6. grava o resultado no video.json (status "agendado", ids) para não repetir.
Sem os secrets do YouTube, ele para no passo 3 e deixa o MP4 como artefato da execução (para conferir).

Uso local: python scripts/youtube.py [--sem-envio]
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GER = RAIZ / "gerador" / "youtube"
SAIDA = RAIZ / "saida-youtube"
sys.path.insert(0, str(GER))
from fotos_fundo import creditos_do_video, descricao_com_creditos  # noqa: E402


def http(url, dados=None, headers=None, metodo=None):
    req = urllib.request.Request(url, data=dados, headers=headers or {}, method=metodo)
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.status, dict(r.headers), r.read()


def narrar(pasta, cfg):
    blocos = json.loads((pasta / "narracao.json").read_text(encoding="utf-8"))
    if (pasta / "short.json").exists():
        s = json.loads((pasta / "short.json").read_text(encoding="utf-8"))
        if s.get("texto"):
            blocos = blocos + [{"arquivo": s.get("arquivo", "short.mp3"), "texto": s["texto"]}]
    audio = pasta / "audio"
    audio.mkdir(exist_ok=True)
    faltam = [b for b in blocos if not (audio / b["arquivo"]).exists()]
    if not faltam:
        return
    chave = os.environ.get("ELEVENLABS_API_KEY")
    voz = cfg.get("voz")
    if not chave or not voz:
        raise SystemExit(f"{pasta.name}: faltam {len(faltam)} áudios e não há ELEVENLABS_API_KEY ou 'voz' no video.json")
    for b in faltam:
        corpo = json.dumps({"text": b["texto"], "model_id": cfg.get("modelo", "eleven_multilingual_v2"),
                            "voice_settings": cfg.get("ajustes_voz", {"stability": 0.45, "similarity_boost": 0.8, "style": 0.2})}).encode()
        _, _, mp3 = http(f"https://api.elevenlabs.io/v1/text-to-speech/{voz}?output_format=mp3_44100_128", corpo,
                         {"xi-api-key": chave, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        (audio / b["arquivo"]).write_bytes(mp3)
        print("narrado", b["arquivo"], len(mp3) // 1024, "KB")


def rodar(*args):
    print("+", " ".join(map(str, args)))
    subprocess.run([str(a) for a in args], check=True)


def fazer_thumb(pasta, out):
    rodar(sys.executable, GER / "slides.py", pasta / "thumb.json", out / "thumb")
    from PIL import Image
    Image.open(out / "thumb" / "001.png").convert("RGB").resize((1280, 720), Image.LANCZOS).save(out / "thumbnail.jpg", quality=92)


def montar(pasta, cfg):
    out = SAIDA / pasta.parent.name / pasta.name
    out.mkdir(parents=True, exist_ok=True)
    os.environ["TEMA_SLIDES"] = cfg.get("tema", cfg["canal"])
    rodar(sys.executable, GER / "slides.py", pasta / "slides.json", out / "slides")
    rodar(sys.executable, GER / "animacao.py", pasta, out / "slides")  # cenas animadas (mapas, linhas do tempo)
    rodar(sys.executable, GER / "broll.py", pasta, out / "slides")  # trechos de vídeo livres (Commons), sem pessoas
    fazer_thumb(pasta, out)
    blocos = json.loads((pasta / "narracao.json").read_text(encoding="utf-8"))
    aud = out / "audio-longo"
    aud.mkdir(exist_ok=True)
    for i, b in enumerate(blocos, 1):
        destino = aud / f"{i:02d}.mp3"
        if not destino.exists():
            destino.symlink_to((pasta / "audio" / b["arquivo"]).resolve())
    mapa = ",".join(map(str, cfg["mapa"])) if cfg.get("mapa") else None
    args = [sys.executable, GER / "montar_video.py", pasta / "roteiro.md", out / "slides", aud, out / "video.mp4"]
    rodar(*(args + (["--mapa", mapa] if mapa else [])))
    if (pasta / "short.json").exists():
        montar_short(pasta, out)
    return out


def montar_short(pasta, out):
    s = json.loads((pasta / "short.json").read_text(encoding="utf-8"))
    mp3 = pasta / "audio" / s.get("arquivo", "short.mp3")
    if not mp3.exists():
        print("Short sem áudio, pulando")
        return
    from PIL import Image, ImageFilter
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)]).decode())
    quadros = out / "short"
    quadros.mkdir(exist_ok=True)
    lista = []
    for i, n in enumerate(s["slides"], 1):
        im = Image.open(out / "slides" / f"{n:03d}.png").convert("RGB")
        fundo = im.resize((3413, 1920)).crop((1166, 0, 2246, 1920)).filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.5))
        frente = im.resize((1080, 608), Image.LANCZOS)
        fundo.paste(frente, (0, 656))
        f = quadros / f"{i:02d}.png"
        fundo.save(f)
        lista.append(f)
    with open(quadros / "lista.txt", "w") as fh:
        for f in lista:
            fh.write(f"file '{f.resolve()}'\nduration {dur / len(lista):.3f}\n")
        fh.write(f"file '{lista[-1].resolve()}'\n")
    rodar("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", quadros / "lista.txt", "-i", mp3,
          "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-shortest",
          "-movflags", "+faststart", out / "short.mp4")


def descricao(pasta):
    """descricao.txt + seção PHOTOS com os créditos das fotos de fundo usadas (até 5000 caracteres)."""
    desc = (pasta / "descricao.txt").read_text(encoding="utf-8")
    desc = livros_com_link(desc)
    desc = capitulos_reais(pasta, desc)
    desc = descricao_com_creditos(desc, creditos_do_video(pasta / "slides.json", pasta / "thumb.json"))
    arq = pasta / "broll_creditos.json"
    filmes = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []
    if filmes:  # seção FOOTAGE com os créditos dos trechos de vídeo, sem passar dos 5000 caracteres
        bloco = "\n\nFOOTAGE (Wikimedia Commons)\n"
        for c in filmes:
            linha = c.replace("Footage: ", "").rsplit(" · ", 1)[0] + "\n"
            if len(desc) + len(bloco) + len(linha) > 5000:
                break
            bloco += linha
        desc = desc.rstrip() + bloco.rstrip()
    return desc



def livros_com_link(desc):
    """Seção RECOMMENDED READING: cada "- Autor, Título" ganha um link de busca na amazon.com.
    Com a tag de Associado dos EUA em config/afiliados.json (amazon_us.tag), o link leva a tag e entra o aviso
    obrigatório da Amazon; sem a tag, o link vai sem afiliado (decidido pelo Luiz em 04/11/2026)."""
    from urllib.parse import quote_plus
    cfg = json.loads((RAIZ / "config" / "afiliados.json").read_text(encoding="utf-8")).get("amazon_us", {})
    tag = (cfg.get("tag") or "").strip()
    linhas, saida, dentro = desc.split("\n"), [], False
    for l in linhas:
        if l.startswith("RECOMMENDED READING"):
            dentro = True
            saida.append("RECOMMENDED READING" + (" (affiliate links)" if tag else ""))
            continue
        if dentro and l.startswith("- ") and "amazon.com" not in l:
            autor, _, titulo = l[2:].partition(", ")
            busca = quote_plus(f"{titulo or autor} {autor if titulo else ''}".strip())
            url = f"https://www.amazon.com/s?k={busca}" + (f"&tag={tag}" if tag else "")
            saida.append(f"{l}: {url}")
            continue
        if dentro and not l.strip():
            if tag:
                saida.append(cfg.get("aviso_obrigatorio", "As an Amazon Associate I earn from qualifying purchases."))
            dentro = False
        saida.append(l)
    return "\n".join(saida)

def capitulos_reais(pasta, desc):
    """Se há um capítulo por PART e os áudios existem, troca os tempos estimados pelos tempos reais da narração."""
    import re
    linhas = desc.split("\n")
    idx = [i for i, l in enumerate(linhas) if re.match(r"^\d{1,2}:\d{2}(:\d{2})? ", l)]
    blocos = json.loads((pasta / "narracao.json").read_text(encoding="utf-8"))
    mp3s = [pasta / "audio" / b["arquivo"] for b in blocos]
    if len(idx) != len(blocos) or not all(m.exists() for m in mp3s):
        return desc
    ini = 0.0
    for i, m in zip(idx, mp3s):
        s = int(ini)
        tempo = f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"
        linhas[i] = re.sub(r"^\d{1,2}:\d{2}(:\d{2})?", tempo, linhas[i])
        ini += float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(m)]).decode())
    return "\n".join(linhas)


def no_futuro(dt, folga_min=45):
    """O YouTube recusa agendamento no passado: se a hora já passou, agenda para daqui a pouco."""
    minimo = datetime.now(timezone.utc) + timedelta(minutes=folga_min)
    return max(dt, minimo).isoformat()


def token_youtube(canal):
    rt = os.environ.get(f"YT_REFRESH_TOKEN_{canal.upper()}")
    cid, seg = os.environ.get("YT_CLIENT_ID"), os.environ.get("YT_CLIENT_SECRET")
    if not (rt and cid and seg):
        return None
    dados = f"client_id={cid}&client_secret={seg}&refresh_token={rt}&grant_type=refresh_token".encode()
    _, _, r = http("https://oauth2.googleapis.com/token", dados, {"Content-Type": "application/x-www-form-urlencoded"})
    return json.loads(r)["access_token"]


def enviar(token, mp4, titulo, descricao, tags, quando, cfg):
    meta = {"snippet": {"title": titulo[:100], "description": descricao[:5000], "tags": tags,
                        "categoryId": cfg.get("categoria", "27"), "defaultLanguage": cfg.get("idioma", "en"),
                        "defaultAudioLanguage": cfg.get("idioma", "en")},
            "status": {"privacyStatus": "private", "publishAt": quando, "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": True, "embeddable": True}}
    tam = mp4.stat().st_size
    _, h, _ = http("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                   json.dumps(meta).encode(), {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                                                "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(tam)})
    destino = h.get("Location") or h.get("location")
    _, _, r = http(destino, mp4.read_bytes(), {"Content-Type": "video/mp4", "Content-Length": str(tam)}, "PUT")
    vid = json.loads(r)["id"]
    print("enviado", vid, titulo)
    return vid


def por_thumbnail(token, vid, jpg):
    try:
        http(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}", jpg.read_bytes(),
             {"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"})
        return True
    except Exception as e:  # noqa: BLE001  (canal sem verificação por telefone não aceita thumbnail)
        print("thumbnail não aceita:", e)
        return False


def main():
    sem_envio = "--sem-envio" in sys.argv
    for arq in sorted(RAIZ.glob("youtube/*/*/video.json")):
        pasta = arq.parent
        cfg = json.loads(arq.read_text(encoding="utf-8"))
        if cfg.get("video_id") and cfg.get("thumbnail") is False and not sem_envio:
            # já enviado, mas a thumbnail foi recusada (canal sem verificação por telefone): tenta de novo
            token = token_youtube(cfg["canal"])
            if token:
                out = SAIDA / pasta.parent.name / pasta.name
                out.mkdir(parents=True, exist_ok=True)
                os.environ["TEMA_SLIDES"] = cfg.get("tema", cfg["canal"])
                fazer_thumb(pasta, out)
                if por_thumbnail(token, cfg["video_id"], out / "thumbnail.jpg"):
                    cfg["thumbnail"] = True
                    arq.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            continue
        if cfg.get("status") != "aprovado" or cfg.get("video_id"):
            continue
        print(f"== {pasta.relative_to(RAIZ)}")
        narrar(pasta, cfg)
        out = montar(pasta, cfg)
        (out / "descricao.txt").write_text(descricao(pasta), encoding="utf-8")  # a descrição final, para conferir
        token = None if sem_envio else token_youtube(cfg["canal"])
        if not token:
            print("Sem as chaves do YouTube: vídeo montado em", out.relative_to(RAIZ), "(baixe nos artefatos da execução)")
            cfg["status_montagem"] = "montado, aguardando chaves do YouTube"
            arq.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            continue
        quando = datetime.fromisoformat(cfg["quando"])
        desc = descricao(pasta)
        vid = enviar(token, out / "video.mp4", cfg["titulo"], desc, cfg.get("tags", []), no_futuro(quando), cfg)
        cfg["video_id"] = vid
        cfg["thumbnail"] = por_thumbnail(token, vid, out / "thumbnail.jpg")
        if (out / "short.mp4").exists():
            s = json.loads((pasta / "short.json").read_text(encoding="utf-8"))
            q = no_futuro(quando - timedelta(hours=cfg.get("short_antes_horas", 24)), 20)
            cfg["short_id"] = enviar(token, out / "short.mp4", s["titulo"], s.get("descricao", "") + f"\n\nFull video: https://youtu.be/{vid}",
                                     cfg.get("tags", [])[:10], q, cfg)
        cfg["status"] = "agendado"
        arq.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sincronizar_metadados(sem_envio=False):
    """Vídeos já enviados: se o título, a descrição ou as tags no repositório mudaram, atualiza no YouTube.
    Precisa do refresh token com o escopo youtube.force-ssl (o youtube.upload sozinho não edita vídeo)."""
    import hashlib
    if sem_envio:
        return
    tokens = {}
    for arq in sorted(RAIZ.glob("youtube/*/*/video.json")):
        pasta = arq.parent
        cfg = json.loads(arq.read_text(encoding="utf-8"))
        if not cfg.get("video_id"):
            continue
        snip = {"title": cfg["titulo"][:100], "description": descricao(pasta)[:5000], "tags": cfg.get("tags", []),
                "categoryId": cfg.get("categoria", "27"), "defaultLanguage": cfg.get("idioma", "en"),
                "defaultAudioLanguage": cfg.get("idioma", "en")}
        h = hashlib.sha256(json.dumps(snip, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        if cfg.get("meta_hash") == h:
            continue
        canal = cfg["canal"]
        if canal not in tokens:
            try:
                tokens[canal] = token_youtube(canal)
            except Exception as e:  # noqa: BLE001
                print(f"ERRO: a chave YT_REFRESH_TOKEN_{canal.upper()} foi recusada pelo Google ({e}). Gere de novo no OAuth Playground.")
                tokens[canal] = None
        if not tokens[canal]:
            continue
        corpo = json.dumps({"id": cfg["video_id"], "snippet": snip}).encode()
        try:
            http("https://www.googleapis.com/youtube/v3/videos?part=snippet", corpo,
                 {"Authorization": f"Bearer {tokens[canal]}", "Content-Type": "application/json; charset=UTF-8"}, "PUT")
        except Exception as e:  # noqa: BLE001
            print(f"metadados de {pasta.relative_to(RAIZ)} não atualizados ({e}); falta o escopo youtube.force-ssl no token de {canal}?")
            continue
        cfg["meta_hash"] = h
        arq.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("metadados atualizados:", pasta.relative_to(RAIZ), cfg["video_id"])


def conferir_canais():
    """Mostra no log para qual canal cada chave aponta (nome e id), para não enviar vídeo ao canal errado."""
    for canal in ("taf", "bhc"):
        try:
            tk = token_youtube(canal)
            if not tk:
                continue
            _, _, r = http("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true", headers={"Authorization": f"Bearer {tk}"})
            for it in json.loads(r).get("items", []):
                print(f"CANAL DA CHAVE {canal.upper()}: {it['snippet']['title']} ({it['id']})")
        except Exception as e:  # noqa: BLE001
            print(f"CANAL DA CHAVE {canal.upper()}: não consegui conferir ({e})")


def excluir_videos(sem_envio=False):
    """Exclui do YouTube os vídeos listados em youtube/excluir.json ("pendentes": [{"id", "titulo", "motivo"}]).
    Exclusão é definitiva: a lista só entra no main pelo merge do Luiz. Travas: só exclui vídeo dos nossos 2 canais
    e nunca um id que algum video.json ainda usa como vídeo ou Short atual."""
    arq = RAIZ / "youtube" / "excluir.json"
    if sem_envio or not arq.exists():
        return
    lista = json.loads(arq.read_text(encoding="utf-8"))
    pend = lista.get("pendentes", [])
    if not pend:
        return
    em_uso = set()
    for v in RAIZ.glob("youtube/*/*/video.json"):
        c = json.loads(v.read_text(encoding="utf-8"))
        em_uso |= {c.get("video_id"), c.get("short_id")}
    tokens, canais = {}, {}
    for canal in ("taf", "bhc"):
        try:
            tk = token_youtube(canal)
            _, _, r = http("https://www.googleapis.com/youtube/v3/channels?part=id&mine=true", headers={"Authorization": f"Bearer {tk}"})
            for it in json.loads(r).get("items", []):
                canais[it["id"]] = canal
            tokens[canal] = tk
        except Exception as e:  # noqa: BLE001
            print(f"exclusão: não consegui usar a chave {canal.upper()} ({e})")
    restantes, feitos = [], lista.setdefault("feitos", [])
    for item in pend:
        vid = item["id"]
        if vid in em_uso:
            print(f"exclusão RECUSADA: {vid} ainda é o vídeo atual de um video.json")
            restantes.append(item)
            continue
        dono = None
        for canal, tk in tokens.items():
            _, _, r = http(f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={vid}", headers={"Authorization": f"Bearer {tk}"})
            its = json.loads(r).get("items", [])
            if its:
                dono = canais.get(its[0]["snippet"]["channelId"])
                break
        if dono is None:
            print(f"exclusão: {vid} não existe mais ou não é dos nossos canais; tirando da lista")
            feitos.append({**item, "resultado": "não encontrado", "em": datetime.now(timezone.utc).isoformat()[:19]})
            continue
        try:
            http(f"https://www.googleapis.com/youtube/v3/videos?id={vid}", headers={"Authorization": f"Bearer {tokens[dono]}"}, metodo="DELETE")
            print("EXCLUÍDO:", vid, item.get("titulo", ""))
            feitos.append({**item, "resultado": f"excluído do canal {dono.upper()}", "em": datetime.now(timezone.utc).isoformat()[:19]})
        except Exception as e:  # noqa: BLE001
            print(f"exclusão de {vid} falhou ({e})")
            restantes.append(item)
    lista["pendentes"] = restantes
    arq.write_text(json.dumps(lista, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if "--sem-envio" not in sys.argv:
        conferir_canais()
    main()
    sincronizar_metadados("--sem-envio" in sys.argv)
    excluir_videos("--sem-envio" in sys.argv)
