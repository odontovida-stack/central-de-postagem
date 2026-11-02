# Cenas animadas dos vídeos

Cada cena é um HTML com `window.DUR` (segundos) e `window.render(t)`. Fica em `youtube/<canal>/<pasta>/anim/<cena>.html`
e entra no `slides.json` como `{"tipo": "animacao", "html": "anim/<cena>.html"}`, no lugar de um slide. O robô
(`gerador/youtube/animacao.py`) grava a cena em MP4 1920x1080 e o `montar_video.py` toca a animação e segura o último
quadro até acabar o tempo daquele slide na narração.

`bhc004.js` é o gerador das 3 cenas do BHC #004 (mapa Flórida–Cuba, rota do U-2, linha do tempo). Precisa de
`npm i d3-geo@3.1.1 topojson-client@3.1.0 world-atlas@2.0.2` (mapas Natural Earth, domínio público). Só roda na
criação da cena; o robô usa o HTML pronto.

Regras: nada de pessoa identificável, nada de imagem "realista" gerada por IA de fato histórico; rota ou distância
aproximada leva aviso na tela.
