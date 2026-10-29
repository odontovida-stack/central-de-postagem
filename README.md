# Central de Postagem

Sistema próprio, sem mensalidade, que publica os posts das nossas páginas no Instagram e no Facebook e coleta os números de cada conta todo dia.

Roda de graça no **GitHub Actions**. Você aprova cada post pelo app do GitHub no celular.

## Como funciona

1. **O post chega na fila.** Cada post é uma pasta em `fila/` com as imagens (JPEG) e um `post.json` com conta, legenda, redes e horário. O Claude cria essas pastas e abre um *pull request*.
2. **Você aprova pelo celular.** No app do GitHub, abra o pull request, veja as imagens e a legenda e toque em **Merge**. O post fica com `"status": "aprovado"`.
3. **Ele sai na hora marcada.** A cada 30 minutos o GitHub roda `scripts/publicar.py`. Ele publica os posts aprovados cujo horário já chegou e grava o resultado no próprio `post.json`.
4. **Os números entram no painel.** Todo dia às 6:23, `scripts/coletar_metricas.py` grava os números de ontem em `dados/metricas.json`. O **Painel das Páginas** (`painel/index.html`, publicado em https://odontovida-stack.github.io/central-de-postagem/painel/) mostra seguidores, alcance e interações de cada conta e a fila de posts. Ele se atualiza sozinho.

Se algo der errado, o post fica com `"status": "erro"` e a mensagem do problema, e o GitHub manda um e-mail avisando. Nada é publicado duas vezes.

## O `post.json`

```json
{
  "conta": "brazilonabudget",
  "tipo": "carrossel",
  "redes": ["instagram", "facebook"],
  "quando": "2026-11-02T18:30:00-03:00",
  "status": "rascunho",
  "midias": ["01.jpg", "02.jpg", "03.jpg"],
  "textos_alternativos": ["Capa: What Rio really costs", "…", "…"],
  "legenda": "What does Rio really cost in 2026? …"
}
```

- `tipo`: `imagem`, `carrossel` (2 a 10 imagens) ou `reels` (1 vídeo .mp4).
- `status`: `rascunho` → `aprovado` → `publicado` (ou `erro`).
- `redes`: `instagram`, `facebook` e `tiktok`. O TikTok, por enquanto, só marca o post como "suba à mão", porque a API de postagem do TikTok exige um app auditado por eles. Isso fica para a fase 2.

Antes de aprovar, o GitHub confere sozinho cada post (`scripts/validar.py`): formato JPEG, proporção de 4:5 a 1,91:1, até 8 MB, legenda até 2.200 caracteres e até 30 hashtags.

## Instalação (uma vez só, uns 40 minutos)

### 1. Contas
- Cada página precisa de uma **conta profissional do Instagram** ligada a uma **Página do Facebook**.
- Crie um **Portfólio empresarial** em business.facebook.com e adicione todas as Páginas e contas do Instagram.

### 2. App e token da Meta
1. Em developers.facebook.com, crie um app do tipo **Empresa** e adicione o produto **Instagram** (login pelo Facebook).
2. No Portfólio empresarial, vá em **Usuários do sistema**, crie um usuário do sistema administrador e dê a ele acesso às Páginas e contas do Instagram.
3. Gere um token desse usuário do sistema com as permissões:
   `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `business_management`.
   Um token de usuário do sistema **não expira**, então não precisa renovar.
4. Os ids de cada conta são descobertos sozinhos: depois de criar os Secrets (passo 3.2), rode a ação **Descobrir ids das contas** na aba **Actions**. Ela casa cada Página com o `instagram_username` de `config/contas.json` e grava `instagram_user_id` e `facebook_page_id`.

### 3. GitHub
1. Crie o repositório **central-de-postagem** e suba esta pasta.
   O repositório precisa ser **público** para o Instagram conseguir baixar as imagens. Ali só ficam posts que vão ser públicos de qualquer jeito, e os tokens ficam guardados como *Secrets*, que ninguém vê.
2. Em **Settings → Secrets and variables → Actions → Secrets**, crie:
   `TOKEN_BRAZILONABUDGET`: o token do usuário do sistema **central-postagem** (portfólio Brazil on a Budget). Ele publica em todas as contas: os outros portfólios compartilham a Página e o Instagram com o portfólio Brazil on a Budget (Configurações › Parceiros) e os ativos compartilhados são atribuídos ao usuário do sistema. Não precisa de token novo.
3. Em **Variables** (opcional): `GRAPH_VERSION` (versão da API, padrão `v23.0`) e `DATA_INICIO` (primeiro dia das páginas, padrão `2026-11-02`).
4. Instale o app **GitHub** no celular e ative as notificações de pull request.

### 4. Teste
1. Na aba **Actions**, rode **Publicar posts aprovados** com **Só simular** marcado. Ele mostra o que publicaria, sem publicar.
2. Aprove o post de exemplo de `fila/` mudando o `quando` para daqui a 10 minutos.
3. Na próxima rodada ele sai de verdade. Confira no Instagram.

## Rodar no computador (opcional)

```
python scripts/validar.py
python scripts/publicar.py --simular
python scripts/coletar_metricas.py --simular
```

Não precisa instalar nada: só Python 3.10 ou mais novo.

## Limites da Meta
- Até 100 posts por conta a cada 24 horas no Instagram (nós usamos uns 2).
- Imagens precisam estar num endereço público. Por isso o repositório é público e as imagens são lidas direto do GitHub.
