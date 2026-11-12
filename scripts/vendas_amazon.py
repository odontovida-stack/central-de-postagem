"""Lê o relatório que o Luiz baixa do Amazon Associates (BR ou EUA) e atualiza a linha da Amazon em
dados/painel/vendas.json, que alimenta a aba Vendas do Painel de Operações. Pedido do Luiz em 12/11/2026.

Como baixar (o Luiz faz, porque o painel da Amazon não deixa leitura automática):
  Associados → Relatórios → escolha o período (ex.: Este mês) → Baixar relatórios → CSV (ou XLSX).
  Vem um .zip com vários arquivos; serve o de "Earnings"/"Ganhos" ou o de "Orders"/"Pedidos".
Uso: python scripts/vendas_amazon.py <arquivo .csv/.xlsx/.zip> [br|us]
O script não guarda nada além dos totais (pedidos, itens, cliques, receita, comissão).
"""
import csv
import io
import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VENDAS = RAIZ / "dados" / "painel" / "vendas.json"
FONTE = {"br": "Amazon Associados BR", "us": "Amazon Associates EUA"}

# nomes de coluna possíveis (inglês e português, como a Amazon exporta)
COL = {
    "comissao": ["ad fees", "earnings", "comissões", "comissao", "taxas de publicidade", "ganhos"],
    "receita": ["revenue", "receita", "total revenue", "valor"],
    "itens": ["items shipped", "items", "itens enviados", "itens", "quantity", "quantidade"],
    "pedidos": ["ordered items", "orders", "pedidos", "itens pedidos"],
    "cliques": ["clicks", "cliques"],
}


def numero(txt):
    if txt is None:
        return 0.0
    s = str(txt).strip().replace("R$", "").replace("$", "").replace("US", "").strip()
    if not s:
        return 0.0
    if re.search(r"\d,\d{1,2}$", s):  # formato brasileiro 1.234,56
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def limpa(c):
    return re.sub(r"\(.*?\)", "", str(c)).strip().lower()


def linhas_csv(texto):
    # a Amazon põe uma linha de título antes do cabeçalho: procura a linha com mais colunas conhecidas
    brutas = list(csv.reader(io.StringIO(texto), delimiter="\t" if texto.count("\t") > texto.count(",") else ","))
    melhor, i_cab = 0, 0
    for i, l in enumerate(brutas[:15]):
        n = sum(1 for c in l if any(limpa(c) == k for ks in COL.values() for k in ks))
        if n > melhor:
            melhor, i_cab = n, i
    cab = [limpa(c) for c in brutas[i_cab]]
    return [dict(zip(cab, l)) for l in brutas[i_cab + 1:] if any(x.strip() for x in l)]


def ler(arquivo):
    p = Path(arquivo)
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            nomes = sorted(z.namelist(), key=lambda n: (0 if re.search(r"earning|ganho|fee", n, re.I) else 1, n))
            for n in nomes:
                if n.lower().endswith((".csv", ".tsv", ".txt")):
                    return linhas_csv(z.read(n).decode("utf-8-sig", errors="replace")), n
        raise SystemExit("o .zip não tem CSV")
    if p.suffix.lower() == ".xlsx":
        import openpyxl
        ws = openpyxl.load_workbook(p, read_only=True, data_only=True).active
        buf = io.StringIO()
        w = csv.writer(buf)
        for row in ws.iter_rows(values_only=True):
            w.writerow(["" if c is None else c for c in row])
        return linhas_csv(buf.getvalue()), p.name
    return linhas_csv(p.read_text(encoding="utf-8-sig", errors="replace")), p.name


def total(linhas, campo):
    nomes = COL[campo]
    soma, achou = 0.0, False
    for l in linhas:
        for k, v in l.items():
            if k in nomes:
                soma += numero(v)
                achou = True
                break
    return soma if achou else None


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    loja = (sys.argv[2] if len(sys.argv) > 2 else "br").lower()
    linhas, nome = ler(sys.argv[1])
    com, rec, itens, ped, cli = (total(linhas, c) for c in ("comissao", "receita", "itens", "pedidos", "cliques"))
    vendas = json.loads(VENDAS.read_text(encoding="utf-8"))
    alvo = next(v for v in vendas if v["fonte"] == FONTE[loja])
    moeda = "R$" if loja == "br" else "US$"
    alvo.update({
        "data": date.today().isoformat(),
        "pedidos": int(ped if ped is not None else (itens or 0)),
        "itens": int(itens) if itens is not None else alvo.get("itens"),
        "visitas": int(cli) if cli is not None else alvo.get("visitas"),
        "receita_usd": round(com, 2) if (com is not None and loja == "us") else alvo.get("receita_usd"),
        "situacao": f"Comissão no período: {moeda} {com or 0:.2f}" + (f" · vendas geradas: {moeda} {rec:.2f}" if rec else ""),
        "como_lido": f"Relatório baixado pelo Luiz ({nome}), lido em {date.today():%d/%m/%Y}",
    })
    if loja == "br" and com is not None:
        alvo["receita_brl"] = round(com, 2)
    VENDAS.write_text(json.dumps(vendas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(alvo, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
