"""Transforma um carrossel já publicado num Reel vertical (1080x1920), no mesmo visual do Reel de Foz:
cada slide no centro, sobre uma versão desfocada dele mesmo, com um zoom leve; ~2,9 s por slide; áudio mudo
(o Luiz põe música no app, se quiser). Pedido do Luiz em 12/11/2026: mais Reels no Brazil on a Budget.

Uso: python gerador/reel_carrossel.py <pasta_do_carrossel> <pasta_do_reel> [segundos_por_slide]
Gera <pasta_do_reel>/01.mp4. O post.json do Reel é escrito à parte (status, quando, legenda).
"""
import subprocess
import sys
import tempfile
from pathlib import Path


def segmento(img, saida, seg):
    fps = 30
    n = int(seg * fps)
    filtro = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-0.08[bg];"
        f"[0:v]scale=1000:-2,zoompan=z='min(zoom+0.0006,1.04)':d={n}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1000x1250:fps={fps}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p"
    )
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", str(seg), "-i", str(img),
                    "-filter_complex", filtro, "-r", str(fps), "-t", str(seg), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", str(saida)], check=True)


def main():
    origem, destino = Path(sys.argv[1]), Path(sys.argv[2])
    seg = float(sys.argv[3]) if len(sys.argv) > 3 else 2.9
    imgs = sorted(origem.glob("*.jpg"))
    if not imgs:
        raise SystemExit(f"sem imagens em {origem}")
    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        partes = []
        for i, img in enumerate(imgs):
            p = tmp / f"{i:02d}.mp4"
            segmento(img, p, seg)
            partes.append(p)
        lista = tmp / "lista.txt"
        lista.write_text("".join(f"file '{p}'\n" for p in partes))
        video = tmp / "video.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(video)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                        str(destino / "01.mp4")], check=True)
    print(f"{destino / '01.mp4'}: {len(imgs)} slides × {seg}s")


if __name__ == "__main__":
    main()
