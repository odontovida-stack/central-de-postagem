"""Publica os posts aprovados cuja hora já chegou.

Roda no GitHub Actions a cada 30 minutos. Também pode rodar à mão:
    python scripts/publicar.py --simular     (não publica nada, só mostra o que faria)

Regras:
- Só publica post com "status": "aprovado" e "quando" no passado (até 6 horas de atraso).
- Depois de publicar, grava o resultado no próprio post.json (status "publicado" e os ids).
- Se der erro, grava "status": "erro" e a mensagem, e não tenta de novo sozinho.
  Exceção: quando a Meta não consegue baixar a imagem (código 9004, comum logo depois
  do merge, enquanto o endereço público da imagem ainda não está no ar), o post continua
  "aprovado" e é tentado de novo nas próximas rodadas, até 3 vezes.
"""
import json
import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meta  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LIMITE_ATRASO = timedelta(hours=6)
MAX_POR_RODADA = 5
ERROS_TEMPORARIOS = ("código 9004",)  # a Meta não conseguiu baixar a imagem
MAX_TENTATIVAS = 3


def url_publica(pasta, arquivo):
    """Endereço público da imagem. O Instagram baixa a imagem deste endereço."""
    base = os.environ.get("MEDIA_BASE_URL")
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY", "SEU-USUARIO/central-de-postagem")
        ref = os.environ.get("GITHUB_SHA", "main")
        base = f"https://raw.githubusercontent.com/{repo}/{ref}"
    rel = (pasta / arquivo).relative_to(RAIZ).as_posix()
    return f"{base.rstrip('/')}/{rel}"


def token_de(conta_cfg, chave):
    nome = conta_cfg.get(chave)
    return os.environ.get(nome) if nome else None


def main():
    simular = "--simular" in sys.argv or os.environ.get("SIMULAR") == "1"
    contas = json.loads((RAIZ / "config" / "contas.json").read_text(encoding="utf-8"))
    agora = datetime.now(timezone.utc)
    feitos = 0
    resumo = []

    for pasta in sorted(d for d in (RAIZ / "fila").iterdir() if d.is_dir()):
        arq = pasta / "post.json"
        if not arq.exists():
            continue
        p = json.loads(arq.read_text(encoding="utf-8"))
        if p.get("status") != "aprovado":
            continue
        quando = datetime.fromisoformat(p["quando"])
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=timezone(timedelta(hours=-3)))
        if quando > agora:
            continue
        if agora - quando > LIMITE_ATRASO:
            p["status"] = "erro"
            p["erro"] = "passou mais de 6 horas do horário marcado; remarque o 'quando' e aprove de novo"
            arq.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            resumo.append(f"ATRASADO  {pasta.name}")
            continue
        if feitos >= MAX_POR_RODADA:
            break

        cfg = contas[p["conta"]]
        urls = [url_publica(pasta, m) for m in p["midias"]]
        resultado = p.get("resultado", {})
        try:
            for rede in p["redes"]:
                if rede in resultado:
                    continue  # já foi publicado nessa rede numa rodada anterior
                if simular:
                    resultado[rede] = f"SIMULADO {len(urls)} mídia(s)"
                    continue
                if rede == "instagram":
                    tok = token_de(cfg, "token_secret")
                    if not tok or not cfg.get("instagram_user_id"):
                        raise meta.MetaError("falta token ou instagram_user_id da conta")
                    resultado[rede] = meta.ig_publish(cfg["instagram_user_id"], tok, p["tipo"], urls,
                                                      p["legenda"], p.get("textos_alternativos"))
                elif rede == "facebook":
                    tok = token_de(cfg, "token_secret")
                    if not tok or not cfg.get("facebook_page_id"):
                        raise meta.MetaError("falta token ou facebook_page_id da conta")
                    resultado[rede] = meta.fb_publish(cfg["facebook_page_id"], tok, p["tipo"], urls, p["legenda"])
                elif rede == "tiktok":
                    # A API do TikTok exige app auditado. Até lá, o post fica pronto para subir à mão.
                    resultado[rede] = "MANUAL: suba as imagens pelo app do TikTok com a mesma legenda"
            if not simular:
                p["status"] = "publicado"
                p["publicado_em"] = agora.isoformat(timespec="seconds")
            p["resultado"] = resultado
            p.pop("erro", None)
            p.pop("tentativas", None)
            resumo.append(f"{'SIMULADO ' if simular else 'PUBLICADO'} {pasta.name} -> {', '.join(p['redes'])}")
        except meta.MetaError as e:
            p["resultado"] = resultado
            p["erro"] = str(e)
            p["tentativas"] = p.get("tentativas", 0) + 1
            if any(t in str(e) for t in ERROS_TEMPORARIOS) and p["tentativas"] < MAX_TENTATIVAS:
                resumo.append(f"DE NOVO   {pasta.name}: {e} (tentativa {p['tentativas']} de {MAX_TENTATIVAS})")
            else:
                p["status"] = "erro"
                resumo.append(f"ERRO      {pasta.name}: {e}")
        if not simular:
            arq.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        feitos += 1

    print("\n".join(resumo) if resumo else "Nada para publicar agora.")
    if any(r.startswith("ERRO") for r in resumo):
        sys.exit(1)  # deixa a execução vermelha no GitHub e manda e-mail de aviso


if __name__ == "__main__":
    main()
