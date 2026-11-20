"""Vídeo curto do relógio do Brasil 23:59 (pedido do Luiz em 20/11/2026).

Toda vez que o relógio se mexe, sai um vídeo vertical de ~8 s (1080×1920, MP4 H.264) mostrando
os ponteiros indo da hora antiga para a nova, item por item (o que adiantou e o que atrasou).

Uso:
    python gerador/relogio_video.py dados.json pasta_de_saida/
dados.json:
    {"data": "2026-11-26", "de": "23:50:20",
     "itens": [{"texto": "IPCA-15 de novembro: piorou", "orgao": "IBGE", "delta": 5},
               {"texto": "Desemprego: melhor da série", "orgao": "IBGE", "delta": -10}],
     "fonte": "IBGE · divulgado em 26/11/2026"}
Gera <pasta>/01.mp4 (e <pasta>/capa.jpg, o último quadro, para conferir).
Fontes: npm i @fontsource-variable/archivo @fontsource/jetbrains-mono (o Google Fonts é bloqueado).
"""
import json
import math
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

FPS = 30
INTRO, POR_ITEM, FINAL = 1.2, 1.4, 2.6
LARANJA, AZUL, CINZA, FG, BG = "#F05A28", "#4C9AFF", "#9B978F", "#F3EFE6", "#0E0E10"
ERA2_INICIO = date(2026, 10, 25)  # dia 1


def seg(h):
    hh, mm, ss = (int(x) for x in h.split(":"))
    return hh * 3600 + mm * 60 + ss


def hora(s):
    s = int(round(s))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def achar_fontes():
    for base in [Path.cwd() / "node_modules", Path(__file__).resolve().parent.parent / "node_modules", Path.home() / "node_modules"]:
        a = base / "@fontsource-variable/archivo/files/archivo-latin-wdth-normal.woff2"
        m = base / "@fontsource/jetbrains-mono/files/jetbrains-mono-latin-700-normal.woff2"
        if a.exists() and m.exists():
            return a, m
    raise SystemExit("Fontes não encontradas: rode  npm i @fontsource-variable/archivo @fontsource/jetbrains-mono")


def html(d, fa, fm):
    itens = d["itens"]
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Archivo;src:url('{fa.as_uri()}') format('woff2');font-weight:100 900;font-stretch:62% 125%}}
@font-face{{font-family:Mono;src:url('{fm.as_uri()}') format('woff2');font-weight:700}}
html,body{{margin:0}}
body{{width:1080px;height:1920px;background:{BG};color:{FG};font-family:Archivo;overflow:hidden}}
#q{{position:relative;width:1080px;height:1920px;box-sizing:border-box;padding:110px 80px 100px;display:flex;flex-direction:column}}
.top{{display:flex;justify-content:space-between;align-items:center;font-family:Mono;font-weight:700}}
.logo{{font-size:40px;letter-spacing:.12em}} .pill{{font-size:34px;letter-spacing:.1em;border:2px solid #3a3a40;border-radius:999px;padding:12px 26px}}
.kick{{margin-top:70px;font-family:Mono;font-weight:700;font-size:36px;letter-spacing:.18em;color:{CINZA}}}
#relogio{{margin:40px auto 0;display:block}}
#digital{{text-align:center;font-family:Archivo;font-weight:800;font-stretch:80%;font-size:190px;line-height:1;margin-top:20px;font-variant-numeric:tabular-nums}}
#falta{{text-align:center;font-family:Mono;font-weight:700;font-size:38px;color:{CINZA};margin-top:10px}}
#itens{{margin-top:50px;display:flex;flex-direction:column;gap:18px}}
.it{{display:flex;justify-content:space-between;align-items:center;gap:24px;background:#1a1a1e;border-radius:20px;padding:22px 30px;font-size:40px;line-height:1.15;opacity:0;transform:translateY(30px)}}
.it b{{font-family:Mono;font-size:46px;white-space:nowrap}} .it small{{display:block;font-size:30px;color:{CINZA};margin-top:4px}}
#total{{margin-top:auto;padding-top:30px;text-align:center;font-weight:800;font-stretch:85%;font-size:70px;opacity:0}}
.foot{{margin-top:30px;display:flex;justify-content:space-between;font-family:Mono;font-weight:700;font-size:30px;color:{CINZA}}}
</style></head><body><div id="q">
<div class="top"><div class="logo">BRASIL 23:59</div><div class="pill">ERA 2 · DIA {(date.fromisoformat(d['data']) - ERA2_INICIO).days + 1}</div></div>
<div class="kick">O RELÓGIO ANDOU</div>
<svg id="relogio" width="620" height="620" viewBox="-310 -310 620 620">
 <circle r="290" fill="none" stroke="{FG}" stroke-width="14"/>
 {''.join(f'<line x1="0" y1="-270" x2="0" y2="{-245 if i % 5 else -225}" stroke="{FG}" stroke-width="{4 if i % 5 else 9}" transform="rotate({i * 6})"/>' for i in range(60))}
 <path id="arco" fill="{LARANJA}" opacity=".35"/>
 <line id="hm" x1="0" y1="0" x2="0" y2="-150" stroke="{FG}" stroke-width="18" stroke-linecap="round"/>
 <line id="mm" x1="0" y1="0" x2="0" y2="-235" stroke="{FG}" stroke-width="12" stroke-linecap="round"/>
 <line id="ss" x1="0" y1="40" x2="0" y2="-260" stroke="{LARANJA}" stroke-width="6" stroke-linecap="round"/>
 <circle r="16" fill="{LARANJA}"/>
</svg>
<div id="digital"></div><div id="falta"></div>
<div id="itens">{''.join(f'<div class="it"><span>{x["texto"]}<small>{x.get("orgao", "")}</small></span><b style="color:{LARANJA if x["delta"] > 0 else AZUL if x["delta"] < 0 else CINZA}">{"+" if x["delta"] > 0 else "−" if x["delta"] < 0 else "±"}{abs(x["delta"])} s</b></div>' for x in itens)}</div>
<div id="total"></div>
<div class="foot"><span>{d.get('fonte', '')}</span><span>@brasil.2359</span></div>
</div><script>
const DE={seg(d['de'])}, DELTAS={json.dumps([x['delta'] for x in itens])}, INTRO={INTRO}, POR={POR_ITEM};
const MEIA=24*3600;
function hh(s){{s=Math.round(s);return String(Math.floor(s/3600)).padStart(2,'0')+':'+String(Math.floor(s%3600/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}}
function ease(x){{return x<0?0:x>1?1:1-Math.pow(1-x,3)}}
function quadro(t){{
  let s=DE; const its=document.querySelectorAll('.it');
  DELTAS.forEach((dl,i)=>{{const a=INTRO+i*POR, p=ease((t-a)/(POR*0.8)); s+=dl*p;
    const el=its[i]; const o=ease((t-a)/0.35); el.style.opacity=o; el.style.transform='translateY('+(30*(1-o))+'px)';}});
  document.getElementById('digital').textContent=hh(s);
  document.getElementById('falta').textContent='faltam '+Math.round(MEIA-s)+' s para a meia-noite';
  const ang=v=>v%60*6, mAng=(s%3600)/3600*360, hAng=(s%43200)/43200*360;
  document.getElementById('ss').setAttribute('transform','rotate('+(s%60*6)+')');
  document.getElementById('mm').setAttribute('transform','rotate('+mAng+')');
  document.getElementById('hm').setAttribute('transform','rotate('+hAng+')');
  const a0=(DE%60)*6, a1=(s%60)*6+(Math.floor(s/60)-Math.floor(DE/60))*360;
  const r=275, p0=[r*Math.sin(a0*Math.PI/180),-r*Math.cos(a0*Math.PI/180)], p1=[r*Math.sin(a1*Math.PI/180),-r*Math.cos(a1*Math.PI/180)];
  const big=Math.abs(a1-a0)>180?1:0, sw=a1>=a0?1:0;
  document.getElementById('arco').setAttribute('d', Math.abs(a1-a0)<0.5?'':'M0 0 L'+p0+' A'+r+' '+r+' 0 '+big+' '+sw+' '+p1+' Z');
  document.getElementById('arco').setAttribute('fill', a1>=a0?'{LARANJA}':'{AZUL}');
  const fim=INTRO+DELTAS.length*POR, tot=DELTAS.reduce((a,b)=>a+b,0), ot=document.getElementById('total');
  ot.style.opacity=ease((t-fim)/0.5);
  ot.innerHTML=(tot>0?'Adiantou '+tot+' s':tot<0?'Atrasou '+(-tot)+' s':'Ficou parado: um somou e outro tirou')+'<br><span style="font-size:44px;color:{CINZA};font-weight:600">Siga para ver para que lado ele anda</span>';
}}
</script></body></html>"""


def main(entrada, saida):
    d = json.load(open(entrada, encoding="utf-8"))
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    fa, fm = achar_fontes()
    dur = INTRO + POR_ITEM * len(d["itens"]) + FINAL
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "v.html").write_text(html(d, fa, fm), encoding="utf-8")
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1920})
            pg.goto((tmp / "v.html").as_uri())
            pg.wait_for_timeout(400)
            n = math.ceil(dur * FPS)
            for i in range(n):
                pg.evaluate(f"quadro({i / FPS})")
                pg.screenshot(path=str(tmp / f"f{i:04d}.png"))
            pg.screenshot(path=str(saida / "capa.jpg"), type="jpeg", quality=92)
            b.close()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(saida / "01.mp4")], check=True)
    total = sum(x["delta"] for x in d["itens"])
    print(f"ok: {saida / '01.mp4'} ({dur:.1f} s) · {d['de']} → {hora(seg(d['de']) + total)}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
