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

## Robô de agenda das páginas LLShop

As 5 páginas (@jogosnatela, @esportesnatela, @tudooqueestreia, @lancamentosdegames e @showsconfirmados) recebem toda semana uma **agenda** e um ou mais **destaques**.

1. **A pauta.** Toda quinta, o Claude apura a semana seguinte em fontes oficiais (CBF, UEFA, Conmebol, UFC, F1, Netflix, Nintendo, Eventim etc.). Ele grava tudo em `pauta/AAAA-MM-DD.json`, com a data da segunda-feira da semana.
2. **Os cards.** `python gerador/llshop.py pauta/AAAA-MM-DD.json` monta os cards no visual das páginas, com as fontes de `gerador/fontes`. Ele cria um post por card em `fila/`. Se um texto não couber no card, o robô para e avisa.
3. **A aprovação.** Tudo vai num pull request. Você confere as imagens e as legendas e faz o merge. Cada post sai no horário marcado no campo `quando`.

Para só ver as imagens, sem criar posts: `python gerador/llshop.py pauta/AAAA-MM-DD.json --previa` (elas ficam em `previa/`, que não vai para o GitHub).

Cada card da pauta tem:
- `tipo`: `agenda` (lista de até 6 itens) ou `destaque` (um evento).
- `quando`, `pilula`, `chamada`, `titulo`, `fonte`, `cta` e `legenda`.
- Na agenda: `itens`, cada um com `data`, `sub`, `titulo` e `detalhe`.
- No destaque: `grande` (uma data grande), `caixas` (2 pares título/valor), `linhas` (data, cidade, local) e `nota`.
- `tipo: pergunta` é o card de engajamento: `pilula`, `chamada`, `titulo` (a pergunta), `contexto` (opcional), `opcoes` (até 4, viram A, B, C e D), `fonte` e `cta`. A pessoa responde nos comentários.
- `tipo: texto` é o slide de comentário dos carrosséis: `pilula`, `chamada`, `titulo`, `texto` (um parágrafo curto), `topicos` (até 4) e `grande` (um número grande, opcional).
- `tipo: carrossel` junta vários cards num post só. Ele leva `quando`, `legenda`, `alt` (opcional) e `cards` (a lista de cards agenda/destaque, na ordem dos slides). É o que o card diário de 7h30 do @jogosnatela usa: resultados de ontem e jogos de hoje.

### Calendário das páginas LLShop (combinado em 29/10/2026)

Os posts diários saem do robô "Posts do dia" (roda à 0h41 e abre um pull request por dia) e só existem quando há novidade. As agendas semanais saem do robô semanal (quinta às 10h58).


| Página | Post | Quando |
|---|---|---|
| @jogosnatela | Resultados de ontem + jogos de hoje (carrossel) | Todo dia, 7h30 |
| @jogosnatela | Jogo do dia (só se houver jogo grande) | 17h |
| @esportesnatela | Hoje tem (UFC, F1, NBA, NFL grandes) | 11h |
| @lancamentosdegames | Sai hoje (lançamento grande) | 10h |
| @lancamentosdegames | Jogos grátis para resgatar (Epic toda quinta, Steam, GOG, PS Plus, Prime, Game Pass) | 14h |
| @tudooqueestreia | Estreia hoje | 12h |
| @showsconfirmados | Pré-venda hoje | 8h |
| @showsconfirmados | Hoje tem show | 16h |
| @lancamentosdegames | Carrossel "O game da semana" | Terça, 19h |
| @tudooqueestreia | Carrossel "As estreias mais esperadas" (streaming + cinema) | Quarta, 20h |
| @lancamentosdegames | Carrossel "O grátis da semana: vale resgatar?" | Quinta, 16h |
| @showsconfirmados | Carrossel "O show da semana" | Quinta, 19h |
| @jogosnatela | Carrossel "O jogo da semana" | Sexta, 19h |
| @esportesnatela | Carrossel "O evento da semana" | Sábado, 10h |
| Todas | Notícia do dia: desfalque, líder, campeão, recorde (inclusive de bilheteria, vendas e público) ou fato curioso, só quando houver | 10h30, 13h ou 15h, até 1 por página por dia |
| Todas | Perguntas para o público: palpite antes de um evento grande, "o que achou?" depois, e 1 enquete fixa por semana (ver o robô "Posts do dia") | 12h ou 20h, até 1 por página por dia |
| @jogosnatela | Agenda da semana | Segunda, 12h |
| @esportesnatela | Agenda da semana | Segunda, 12h30 |
| @lancamentosdegames | Lançamentos da semana | Segunda, 9h |
| @showsconfirmados | Shows da semana ou do mês | Segunda, 19h |
| @tudooqueestreia | Estreias da semana (sexta a quinta) | Sexta, 9h |
| Todas | Destaques | 18h, de terça a sábado |

## Fotos e engajamento (combinado em 29/10/2026)

### Fotos de fundo
- O robô de fotos (`.github/workflows/fotos.yml`) baixa fotos de licença livre (Wikimedia Commons, CC0/CC BY/CC BY-SA) pedidas em `fotos/pedidos.json` e grava `fotos/banco/<nome>.jpg` + `.json` (autor, licença, crédito). O log da última busca fica em `fotos/ultimo-log.txt`.
- Nos cards LLShop, qualquer card aceita `"foto": "<nome>"`. O gerador põe a foto com camada escura, escreve o crédito no canto do card e acrescenta "📷 Foto: autor · licença, Wikimedia Commons" no fim da legenda.
- Fotos disponíveis para as páginas LLShop: `estadio-maracana`, `futebol-gramado`, `basquete-quadra`, `formula1-pista`, `show-plateia`, `cinema-sala`, `streaming-sofa`, `game-controle` (veja a lista atual em `fotos/banco/`).
- Use foto só em capa de carrossel, destaque e pergunta. Agenda fica sem foto (é muito texto).
- Só cenas genéricas: estádio, quadra, pista, plateia, sala de cinema, controle. NUNCA foto de pessoa famosa (atleta, artista, ator), escudo, logo, pôster, capa de jogo ou print de filme.
- Precisa de foto nova? Acrescente o pedido em `fotos/pedidos.json` (o robô roda sozinho quando o arquivo muda) e, nesse dia, faça o card sem foto.

### Táticas de engajamento
1. Todo carrossel termina sozinho com o slide "Esse post pode não aparecer de novo" (siga · ative as notificações · salve e mande). Para desligar num carrossel: `"sem_seguir": true`.
2. Capa com promessa e número: "5 jogos grátis para resgatar até quinta", "Os 4 shows esgotados de novembro".
3. O slide 2 já entrega a informação principal. Nada de enrolação antes do conteúdo.
4. Legenda em 4 partes: 1ª linha com o gancho, depois a informação, depois "📌 Salve para não esquecer" e "📤 Mande para quem <torce/joga/vai ao show> com você", e por fim a pergunta para os comentários e as hashtags.
5. Responder os comentários na primeira hora ajuda o alcance. Na legenda, faça uma pergunta fácil de responder com uma palavra ou letra (A, B, C).
6. Séries com nome fixo ("O JOGO DA SEMANA", "O GRÁTIS DA SEMANA") criam hábito: mantenha sempre o mesmo nome e dia.

## Robô de vídeo do YouTube (The American File e BHC)

Cada vídeo é uma pasta `youtube/<canal>/<nome>/` (canal `taf` ou `bhc`) com:
`video.json` (título, data e hora, tags, voz, status), `roteiro.md`, `narracao.json` (um bloco por PART),
`descricao.txt`, `slides.json`, `thumb.json` e, se tiver Short, `short.json`.

Fluxo:
1. O Claude cria a pasta num branch e abre um PR com `"status": "aprovado"`.
2. O Luiz confere e faz o merge.
3. O workflow `youtube.yml`:
   - narra os blocos pela API do ElevenLabs (pula os que já estão em `audio/`);
   - gera os slides e a thumbnail;
   - monta o MP4 e o Short;
   - envia os dois ao YouTube como **privados e agendados**: o Short 24 h antes do vídeo longo, ambos com "não é para crianças" e "conteúdo sintético" marcados.
4. O resultado (`video_id`, `status: agendado`) volta gravado no `video.json`.

Sem as chaves do YouTube, o robô para depois de montar. O MP4 fica nos artefatos da execução (Actions → a execução → Artifacts), para conferir e subir à mão.

Secrets necessários (Settings → Secrets and variables → Actions):
- `ELEVENLABS_API_KEY`: ElevenLabs → Profile → API Keys.
- `YT_CLIENT_ID` e `YT_CLIENT_SECRET`: Google Cloud → APIs e serviços → Credenciais → ID do cliente OAuth (tipo "App para computador" ou "Aplicativo da Web").
- `YT_REFRESH_TOKEN_TAF` e `YT_REFRESH_TOKEN_BHC`: um por canal, gerado no OAuth Playground com o escopo `https://www.googleapis.com/auth/youtube.upload`.

Para publicar a tela de consentimento, ponha o app do Google Cloud "Em produção", e não "Em teste". Em teste, o token vence em 7 dias.

Thumbnail personalizada só funciona em canal verificado por telefone (youtube.com/verify).
