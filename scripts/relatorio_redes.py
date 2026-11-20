"""Relatório semanal das redes (pedido do Luiz em 20/11/2026): o que funcionou nos últimos 7 dias.

Lê dados/posts.json (scripts/coletar_posts.py) e dados/painel/historico.json e escreve
dados/relatorios/AAAA-MM-DD.md com:
  1. resumo por conta (posts, alcance, interações, salvamentos, compartilhamentos, seguidores) contra a semana anterior;
  2. os 5 melhores posts da semana;
  3. comparações: formato, horário, dia da semana e idioma (só grupos com 2 posts ou mais);
  4. alertas (alcance quase zero, conta sem números).
Com --avisar, comenta o relatório numa issue fixa ("📊 Relatório semanal das redes") marcando o Luiz,
e o app do GitHub avisa no celular (mesmo jeito do aviso do TikTok).

Uso:  python scripts/relatorio_redes.py [--avisar] [--data AAAA-MM-DD]
"""
import json
import pathlib
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
BR = timezone(timedelta(hours=-3))
TITULO_ISSUE = "📊 Relatório semanal das redes"
DIAS = {"Mon": "seg", "Tue": "ter", "Wed": "qua", "Thu": "qui", "Fri": "sex", "Sat": "sáb", "Sun": "dom"}
REDES = {"instagram": "IG", "facebook": "FB", "tiktok": "TikTok", "youtube": "YouTube"}


def nums(reg):
    """Melhor leitura disponível do post (a foto d7 se já existe, senão a última)."""
    return reg.get("fotos", {}).get("d7") or reg.get("ultimo") or {}


def alcance(reg):
    n = nums(reg)
    return n.get("alcance") if n.get("alcance") is not None else n.get("visualizacoes") or 0


def interacoes(reg):
    n = nums(reg)
    if n.get("interacoes") is not None:
        return n["interacoes"]
    return sum(n.get(k) or 0 for k in ("curtidas", "comentarios", "compartilhamentos", "salvamentos"))


def faixa(h):
    if h is None:
        return None
    return "manhã (6–12h)" if 6 <= h < 12 else "tarde (12–18h)" if 12 <= h < 18 else "noite (18–24h)" if h >= 18 else "madrugada"


def fmt(n):
    return f"{int(round(n)):,}".replace(",", ".")


def variacao(a, b):
    if not b:
        return "novo" if a else "="
    d = (a - b) / b * 100
    return f"{'+' if d >= 0 else ''}{d:.0f}%"


def nome_conta(conta, contas):
    return (contas.get(conta) or {}).get("nome") or conta


def comparar(regs, chave, rotulo):
    grupos = defaultdict(list)
    for r in regs:
        g = chave(r)
        if g:
            grupos[g].append(r)
    grupos = {g: v for g, v in grupos.items() if len(v) >= 2}
    if len(grupos) < 2:
        return []
    linhas = [f"**{rotulo}** (alcance médio por post)", ""]
    ordem = sorted(grupos.items(), key=lambda kv: -sum(alcance(x) for x in kv[1]) / len(kv[1]))
    for g, v in ordem:
        media = sum(alcance(x) for x in v) / len(v)
        inter = sum(interacoes(x) for x in v) / len(v)
        linhas.append(f"- {g}: {fmt(media)} de alcance · {inter:.1f} interações · {len(v)} posts")
    return linhas + [""]


def montar(hoje):
    posts = json.loads((RAIZ / "dados" / "posts.json").read_text(encoding="utf-8")) if (RAIZ / "dados" / "posts.json").exists() else {}
    contas = json.loads((RAIZ / "config" / "contas.json").read_text(encoding="utf-8"))
    fim = datetime.combine(hoje, datetime.min.time(), tzinfo=BR)
    ini, ini_ant = fim - timedelta(days=7), fim - timedelta(days=14)

    def quando(r):
        return datetime.fromisoformat(r["publicado_em"].replace("Z", "+00:00"))

    regs = [r for r in posts.values() if r.get("publicado_em") and (r.get("ultimo") or r.get("fotos"))]
    semana = [r for r in regs if ini <= quando(r) < fim]
    anterior = [r for r in regs if ini_ant <= quando(r) < ini]
    md = [f"# 📊 Relatório das redes · {ini.strftime('%d/%m')} a {(fim - timedelta(days=1)).strftime('%d/%m/%Y')}", ""]
    if not semana:
        md += ["Nenhum post com números nesta semana ainda (a coleta por post começou em 20/11/2026).", ""]

    # 1. resumo por conta
    hist = json.loads((RAIZ / "dados" / "painel" / "historico.json").read_text(encoding="utf-8")) if (RAIZ / "dados" / "painel" / "historico.json").exists() else []
    def seguidores(canal, plataforma, dia):
        ok = [h for h in hist if h.get("canal") == canal and h.get("plataforma") == plataforma and h.get("data", "") <= dia]
        return ok[-1].get("seguidores") if ok else None
    md += ["## Por conta", "", "| Conta | Rede | Posts | Alcance/views | vs semana ant. | Interações | Salvos | Compart. | Seguidores |",
           "|---|---|---|---|---|---|---|---|---|"]
    chaves = sorted({(r["conta"], r["rede"]) for r in semana + anterior})
    alertas = []
    for conta, rede in chaves:
        s = [r for r in semana if r["conta"] == conta and r["rede"] == rede]
        a = [r for r in anterior if r["conta"] == conta and r["rede"] == rede]
        alc, alc_a = sum(alcance(r) for r in s), sum(alcance(r) for r in a)
        nome = nome_conta(conta, contas)
        seg = ""
        if rede in ("instagram", "facebook"):
            plat = rede.capitalize()
            agora_s, antes_s = seguidores(nome, plat, hoje.isoformat()), seguidores(nome, plat, (hoje - timedelta(days=7)).isoformat())
            if agora_s is not None:
                seg = f"{agora_s}" + (f" ({'+' if agora_s - antes_s >= 0 else ''}{agora_s - antes_s})" if antes_s is not None else "")
        sem_alc = rede == "facebook"  # a Meta não dá mais alcance por post no Facebook: só reações, comentários e compart.
        md.append(f"| {nome} | {REDES.get(rede, rede)} | {len(s)} | {'—' if sem_alc else fmt(alc)} | {'—' if sem_alc else variacao(alc, alc_a)} | {fmt(sum(interacoes(r) for r in s))} | "
                  f"{fmt(sum(nums(r).get('salvamentos') or 0 for r in s))} | {fmt(sum(nums(r).get('compartilhamentos') or 0 for r in s))} | {seg} |")
        if not sem_alc and len(s) >= 3 and alc < 10 * len(s):
            alertas.append(f"{nome} ({REDES.get(rede, rede)}): {len(s)} posts e só {fmt(alc)} de alcance somado. Os posts quase não estão chegando a ninguém.")
    md.append("")

    # 2. melhores posts
    if semana:
        md += ["## Os 5 melhores da semana", ""]
        for i, r in enumerate(sorted(semana, key=lambda r: (alcance(r), interacoes(r)), reverse=True)[:5], 1):
            n = nums(r)
            extra = " · ".join(f"{v} {k}" for k, v in (("salvos", n.get("salvamentos")), ("compart.", n.get("compartilhamentos"))) if v)
            md.append(f"{i}. **{nome_conta(r['conta'], contas)}** ({REDES.get(r['rede'], r['rede'])}, {r.get('tipo')}) · {fmt(alcance(r))} de {'views' if r['rede'] in ('youtube', 'tiktok') else 'alcance'} · "
                      f"{fmt(interacoes(r))} interações{' · ' + extra if extra else ''}  \n   {r.get('titulo', '')[:90]}")
        md.append("")

    # 3. comparações (só Instagram, onde há alcance por post; o resto entra quando tiver volume)
    ig = [r for r in semana if r["rede"] == "instagram" and r.get("tipo") != "story"]
    comp = []
    comp += comparar(ig, lambda r: r.get("tipo"), "Formato")
    comp += comparar(ig, lambda r: faixa(r.get("hora")), "Horário")
    comp += comparar(ig, lambda r: DIAS.get(r.get("dia_semana")), "Dia da semana")
    comp += comparar([r for r in ig if r["conta"] == "brazilonabudget"], lambda r: {"en": "inglês", "es": "espanhol"}.get(r.get("idioma")), "Idioma (Brazil on a Budget)")
    if comp:
        md += ["## O que funcionou melhor (Instagram)", ""] + comp
    elif semana:
        md += ["## O que funcionou melhor", "", "Ainda não dá para comparar: precisa de pelo menos 2 posts em cada grupo e algum alcance.", ""]

    # 4. alertas
    if alertas:
        md += ["## ⚠️ Atenção", ""] + [f"- {a}" for a in alertas] + [
            "", "Quando o alcance fica perto de zero, confira no app: perfil público, conta Profissional e Configurações → Status da conta.", ""]
    md += ["---", "_Números do Instagram e Facebook (Meta), YouTube e TikTok, coletados todo dia às 6h23 pela Central de Postagem. "
           "Alcance de cada post: a leitura de 7 dias depois, ou a mais recente se o post é novo._"]
    return "\n".join(md) + "\n"


def avisar(texto):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import avisos  # noqa: E402
    num = None
    for i in avisos._api("GET", "issues?state=open&per_page=100") or []:
        if i.get("title") == TITULO_ISSUE and "pull_request" not in i:
            num = i["number"]
    if num is None:
        num = avisos._api("POST", "issues", {"title": TITULO_ISSUE, "body": (
            "Toda segunda de manhã o robô comenta aqui o relatório da semana das redes, e o app do GitHub te avisa no celular. "
            "Os relatórios também ficam em `dados/relatorios/`. Não feche esta issue: ela é reaproveitada.")})["number"]
    avisos._api("POST", f"issues/{num}/comments", {"body": f"@{avisos.DONO} {texto}"})


def main():
    hoje = datetime.now(BR).date()
    if "--data" in sys.argv:
        hoje = date.fromisoformat(sys.argv[sys.argv.index("--data") + 1])
    texto = montar(hoje)
    pasta = RAIZ / "dados" / "relatorios"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{hoje.isoformat()}.md").write_text(texto, encoding="utf-8")
    print(texto)
    if "--avisar" in sys.argv:
        try:
            avisar(texto)
            print("relatório comentado na issue")
        except Exception as e:  # noqa: BLE001
            print(f"aviso não enviado: {e}")


if __name__ == "__main__":
    main()
