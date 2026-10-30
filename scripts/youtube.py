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
     A descrição recebe no fim a seção PHOTOS com os créditos das fotos de fundo dos slides (campo "foto").
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
    return descricao_com_creditos(desc, creditos_do_video(pasta / "slides.json", pasta / "thumb.json"))


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


if __name__ == "__main__":
    main()
