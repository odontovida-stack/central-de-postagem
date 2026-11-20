"""Radar de preço do e-commerce (pedido do Luiz em 20/11/2026, ideia tirada dos prints de @felipebernardo__).

Todo dia confere no Mercado Livre o preço dos concorrentes de cada produto de config/radar_precos.json e avisa o
Luiz (issue fixa "💲 Radar de preço", com aviso no celular pelo app do GitHub) quando:
  - um concorrente está mais barato que o nosso anúncio;
  - um concorrente baixou o preço 5% ou mais desde a última leitura.
Guarda o histórico em dados/radar_precos.json (só preços públicos de anúncios).

Usa a API pública do Mercado Livre (api.mercadolibre.com). Se o Mercado Livre pedir login, ponha um token no secret
ML_ACCESS_TOKEN (app em developers.mercadolivre.com.br). A Shopee não tem API pública de busca: fica de fora por enquanto.

Uso: python scripts/radar_precos.py [--avisar]
"""
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CFG = RAIZ / "config" / "radar_precos.json"
SAIDA = RAIZ / "dados" / "radar_precos.json"
API = "https://api.mercadolibre.com"
BR = timezone(timedelta(hours=-3))
TITULO_ISSUE = "💲 Radar de preço"


def get(caminho):
    req = urllib.request.Request(API + caminho, headers={"User-Agent": "central-de-postagem/1.0"})
    tok = os.environ.get("ML_ACCESS_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def id_anuncio(texto):
    """Aceita 'MLB1234567890', 'MLB-1234567890' ou o link do anúncio."""
    import re
    m = re.search(r"MLB-?(\d{6,})", texto or "", re.I)
    return f"MLB{m.group(1)}" if m else None


def brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    hist = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    hoje = datetime.now(BR).date().isoformat()
    alertas, erros = [], []
    for prod in cfg.get("produtos", []):
        if not prod.get("ativo", True):
            continue
        nome = prod["nome"]
        meu_id = id_anuncio(prod.get("meu_anuncio", ""))
        meu_preco = None
        if meu_id:
            try:
                meu_preco = float(get(f"/items/{meu_id}")["price"])
            except Exception as e:  # noqa: BLE001
                erros.append(f"{nome}: não li o nosso anúncio {meu_id} ({str(e)[:80]})")
        vistos = {}
        for busca in prod.get("buscas", []):
            try:
                q = urllib.parse.urlencode({"q": busca, "limit": prod.get("limite", 15)})
                for it in get(f"/sites/MLB/search?{q}").get("results", []):
                    if it["id"] == meu_id or str(it.get("seller", {}).get("id")) in map(str, cfg.get("meus_vendedores", [])):
                        continue
                    vistos[it["id"]] = {"titulo": it["title"][:90], "preco": float(it["price"]), "link": it.get("permalink", ""),
                                        "vendidos": it.get("sold_quantity"), "frete_gratis": it.get("shipping", {}).get("free_shipping")}
            except Exception as e:  # noqa: BLE001
                erros.append(f"{nome}: busca '{busca}' falhou ({str(e)[:80]})")
        h = hist.setdefault(nome, {"leituras": {}})
        anterior = h["leituras"].get(max(h["leituras"]) if h["leituras"] else "", {}).get("concorrentes", {})
        h["leituras"][hoje] = {"meu_preco": meu_preco, "concorrentes": vistos}
        h["leituras"] = dict(sorted(h["leituras"].items())[-90:])  # guarda 90 dias
        for cid, c in sorted(vistos.items(), key=lambda kv: kv[1]["preco"]):
            if meu_preco and c["preco"] < meu_preco:
                alertas.append(f"**{nome}**: concorrente mais barato, {brl(c['preco'])} contra {brl(meu_preco)} do nosso. [{c['titulo']}]({c['link']})")
            antes = anterior.get(cid, {}).get("preco")
            if antes and c["preco"] <= antes * 0.95:
                alertas.append(f"**{nome}**: concorrente baixou de {brl(antes)} para {brl(c['preco'])}. [{c['titulo']}]({c['link']})")
        precos = sorted(c["preco"] for c in vistos.values())
        if precos:
            print(f"{nome}: {len(precos)} concorrentes, menor {brl(precos[0])}, mediana {brl(precos[len(precos)//2])}"
                  + (f", nosso {brl(meu_preco)}" if meu_preco else ""))
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(hist, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for e in erros:
        print("aviso:", e)
    if alertas:
        print("\n".join(alertas))
    if "--avisar" in sys.argv and (alertas or (erros and not any(h["leituras"].get(hoje, {}).get("concorrentes") for h in hist.values()))):
        corpo = (f"💲 Radar de preço {datetime.now(BR).strftime('%d/%m')}\n\n" + "\n".join(f"- {a}" for a in alertas[:15])
                 + ("\n\n⚠️ Problemas na leitura:\n" + "\n".join(f"- {e}" for e in erros) if erros else ""))
        avisar(corpo)


def avisar(texto):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import avisos  # noqa: E402
    try:
        num = next((i["number"] for i in avisos._api("GET", "issues?state=open&per_page=100") or []
                    if i.get("title") == TITULO_ISSUE and "pull_request" not in i), None)
        if num is None:
            num = avisos._api("POST", "issues", {"title": TITULO_ISSUE, "body": (
                "Todo dia o robô confere o preço dos concorrentes no Mercado Livre e comenta aqui quando alguém fica mais "
                "barato que o nosso anúncio ou baixa o preço. Não feche esta issue: ela é reaproveitada.")})["number"]
        avisos._api("POST", f"issues/{num}/comments", {"body": f"@{avisos.DONO} {texto}"})
    except Exception as e:  # noqa: BLE001
        print(f"aviso não enviado: {e}")


if __name__ == "__main__":
    main()
