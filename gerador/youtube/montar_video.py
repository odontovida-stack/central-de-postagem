"""Monta o vídeo do FILE: cada slide fica na tela pelo tempo da narração que vem depois dele.
Uso: python montar_video.py producao.md slides_png_dir audios_dir saida.mp4 [--mapa 1,2,3,4,4,5,...]
- audios_dir: TAF_001_Block01.mp3 ... (um por PART, na ordem)
- --mapa: para cada slide (em ordem), o número do [VISUAL] do roteiro a que ele pertence (slides que dividem um VISUAL dividem o tempo)."""
import re, sys, glob, json, subprocess, os
from pathlib import Path
prod, pngdir, audir, out = sys.argv[1:5]
mapa = None
if '--mapa' in sys.argv: mapa = [int(x) for x in sys.argv[sys.argv.index('--mapa') + 1].split(',')]
# 1. visuais e palavras narradas depois de cada um, por PART
parts, cur = [], None
for l in open(prod, encoding='utf-8').read().split('\n'):
    s = l.strip()
    if s.startswith('## PART'): cur = {'visuais': []}; parts.append(cur); continue
    if cur is None or not s or s.startswith('_') or s.startswith('#'): continue
    if s.startswith('[VISUAL'): cur['visuais'].append(0); continue
    if cur['visuais']: cur['visuais'][-1] += len(re.sub(r'^(🎣 HOOK|🔁 RETENTION|💬 RELATABLE):', '', s).split())
    else: cur.setdefault('antes', 0)
def dur(f): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).decode())
audios = sorted(glob.glob(f'{audir}/*.mp3')) or sorted(glob.glob(f'{audir}/*.wav'))
assert len(audios) == len(parts), f'{len(audios)} áudios para {len(parts)} partes'
tempos = []  # duração de cada VISUAL global
for p, a in zip(parts, audios):
    D = dur(a); w = [max(x, 8) for x in p['visuais']]; T = sum(w)
    tempos += [D * x / T for x in w]
slides = sorted(glob.glob(f'{pngdir}/*.png'))
mapa = mapa or list(range(1, len(slides) + 1))
assert len(mapa) == len(slides) and max(mapa) == len(tempos), (len(mapa), len(slides), max(mapa), len(tempos))
cont = {v: mapa.count(v) for v in set(mapa)}
lista = Path(out).with_suffix('.txt')
duracoes = [tempos[v - 1] / cont[v] for v in mapa]
clipes = [Path(png).with_suffix('.mp4') for png in slides]
if any(c.exists() for c in clipes):
    # há cenas animadas: cada slide vira um trecho; a animação toca e o último quadro segura até o fim do tempo do slide
    tdir = Path(out).with_suffix('.trechos'); tdir.mkdir(exist_ok=True)
    with open(lista, 'w') as f:
        for k, (png, clip, d) in enumerate(zip(slides, clipes, duracoes)):
            seg = tdir / f'{k:03d}.mp4'
            if clip.exists() and Path(png).with_suffix('.broll').exists():
                # b-roll: o trecho de vídeo repete (sem acelerar) até cobrir o tempo do slide
                cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', str(clip), '-t', f'{d:.3f}', '-an',
                       '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', str(seg)]
            elif clip.exists():
                D = dur(str(clip))
                fator = max(d / D, 1 / 3) if d < D else 1.0  # slide curto: acelera a animação (até 3x) para ela terminar
                extra = max(0.0, d - D * fator)
                cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', str(clip), '-vf', f'setpts=PTS*{fator:.4f},tpad=stop_mode=clone:stop_duration={extra:.3f},fps=30,format=yuv420p',
                       '-t', f'{d:.3f}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', str(seg)]
            else:
                cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', png, '-t', f'{d:.3f}', '-vf', 'fps=30,format=yuv420p',
                       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-tune', 'stillimage', str(seg)]
            subprocess.run(cmd, check=True)
            f.write(f"file '{seg.resolve()}'\n")
    concat_video = ['-f', 'concat', '-safe', '0', '-i', str(lista)]
    vf = ['-c:v', 'copy']
else:
    with open(lista, 'w') as f:
        for png, d in zip(slides, duracoes):
            f.write(f"file '{os.path.abspath(png)}'\nduration {d:.3f}\n")
        f.write(f"file '{os.path.abspath(slides[-1])}'\n")
    concat_video = ['-f', 'concat', '-safe', '0', '-i', str(lista)]
    vf = ['-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-tune', 'stillimage']
audio = Path(out).with_suffix('.audio.m4a')
with open(Path(out).with_suffix('.audios.txt'), 'w') as f:
    for a in audios: f.write(f"file '{os.path.abspath(a)}'\n")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(Path(out).with_suffix('.audios.txt')), '-c:a', 'aac', '-b:a', '192k', str(audio)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + concat_video + ['-i', str(audio)] + vf +
               ['-c:a', 'copy', '-shortest', '-movflags', '+faststart', out], check=True)
print(out, f'{dur(out) / 60:.1f} min', len(slides), 'slides')
