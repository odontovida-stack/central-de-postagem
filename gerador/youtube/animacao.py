"""Grava cenas animadas (HTML com window.render(t) e window.DUR) em MP4 1920x1080, 30 fps.
Para cada slide de slides.json com "tipo": "animacao" e "html": "anim/<cena>.html" (relativo à pasta do vídeo),
grava <slides_dir>/NNN.mp4 e troca NNN.png pelo quadro final. O montar_video.py usa o MP4 no lugar da imagem.
Uso: python animacao.py <pasta do vídeo> <slides_dir>"""
import json, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

FPS = 30


def gravar(pg, html, mp4, png):
    pg.goto(html.resolve().as_uri())
    pg.evaluate("document.fonts.ready")
    dur = pg.evaluate("window.DUR")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(mp4)],
                          stdin=subprocess.PIPE)
    for i in range(int(dur * FPS)):
        pg.evaluate(f"window.render({i / FPS})")
        ff.stdin.write(pg.screenshot(type="png"))
    ff.stdin.close()
    if ff.wait():
        raise SystemExit(f"ffmpeg falhou em {html}")
    pg.evaluate(f"window.render({dur})")
    pg.screenshot(path=str(png))
    print("animação", html.name, f"{dur}s ->", mp4.name)


def main():
    pasta, sdir = Path(sys.argv[1]), Path(sys.argv[2])
    slides = json.loads((pasta / "slides.json").read_text(encoding="utf-8"))
    cenas = [(i, s) for i, s in enumerate(slides, 1) if s.get("tipo") == "animacao"]
    if not cenas:
        return
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for i, s in cenas:
            gravar(pg, pasta / s["html"], sdir / f"{i:03d}.mp4", sdir / f"{i:03d}.png")
        b.close()


if __name__ == "__main__":
    main()
