[English](README.md) · **Português (Brasil)**

# ai-referrer-report

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)

`ai-referrer-report` é uma ferramenta gratuita, de código aberto e de
linha de comando, que lê um CSV exportado do Google Analytics 4 e mostra
as sessões e conversões que chegaram de assistentes de IA (ChatGPT,
Perplexity, Gemini, Claude, Copilot e outros), por plataforma e por página
de destino. Ela classifica o tráfego só pela origem ou pelo referenciador
que o GA4 registrou, com uma lista aberta e versionada de domínios, e gera
a regex pronta para um grupo de canais personalizado do GA4. Roda offline
na sua máquina, e nenhum dado é enviado para servidor nenhum.

## Sumário

- [Contexto](#contexto)
- [O que a ferramenta verifica](#o-que-a-ferramenta-verifica)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Uso](#uso)
- [Perguntas frequentes](#perguntas-frequentes)
- [Limitações](#limitações)
- [Método e origem](#método-e-origem)
- [Como contribuir](#como-contribuir)
- [Autor](#autor)
- [Licença](#licença)

## Contexto

As visitas vindas de assistentes de IA se espalham por vários domínios de
referência, e o GA4, no padrão, junta a maior parte delas no canal genérico
de referência. Para responder perguntas simples (quantas sessões vieram do
ChatGPT no mês passado, em quais páginas elas entraram, se alguma
converteu) é preciso comparar cada origem com uma lista de domínios de IA.

Essa lista é a única regra aqui. A ferramenta não adivinha. Parte do
tráfego que vem de IA chega sem referenciador (aplicativo de celular, link
copiado, navegador ou configuração que remove o cabeçalho) e o GA4 grava
essa visita como direta. `ai-referrer-report` não tenta estimar essa
parte, então o número dela é um piso, não o total.

## O que a ferramenta verifica

1. **Classificação pela origem real.** Cada valor de "Origem da sessão" /
   "Session source" ou "Referenciador da página" / "Page referrer" é
   comparado com o `ai_referrers.json`. Um host casa quando é igual a um
   domínio da lista ou é subdomínio dele (`www.perplexity.ai` conta como
   `perplexity.ai`). Valores de "Origem / meio da sessão", como
   `chatgpt.com / referral`, também são aceitos.
2. **Plataformas.** `chatgpt`, `perplexity`, `gemini`, `claude`, `copilot`
   e `outra-ia` (You.com, Phind, Poe, DeepSeek, Meta AI, Grok, Le Chat da
   Mistral, Assistente do Kagi).
3. **Totais e participação.** Sessões, sessões engajadas, usuários e
   conversões ("Eventos principais" / "Key events") por plataforma, a
   participação no total de sessões do arquivo e a participação no total
   de sessões de IA.
4. **Páginas de destino.** Quando o arquivo tem "Página de destino" /
   "Landing page", as N páginas com mais sessões de IA, com a divisão por
   plataforma.
5. **Origens ambíguas.** Entradas com `path_prefix` (o Assistente do Kagi
   fica em `kagi.com/assistant`, e `kagi.com` também é um buscador) só
   casam quando o valor traz o caminho, o que acontece com o referenciador
   da página. Com a origem da sessão, que só traz o host, essas linhas
   aparecem como ambíguas e ficam fora dos totais.
6. **Regex para o GA4.** `--print-regex` imprime uma regex para todas as
   plataformas de IA e uma por plataforma, geradas da mesma lista.

As linhas de comentário iniciadas por `#` no topo do export do GA4 são
ignoradas. O separador (`,` ou `;`) e o decimal são detectados sozinhos.

## Requisitos

Python 3.9 ou mais recente. Só biblioteca padrão, sem dependência externa.

## Instalação

```bash
git clone https://github.com/LucasFerrazSEO/ai-referrer-report.git
cd ai-referrer-report
```

## Uso

**1. Exporte os dados do GA4.** No relatório de aquisição de tráfego (ou
em uma exploração), use "Origem da sessão" como dimensão, acrescente
"Página de destino" como dimensão secundária se quiser o ranking por
página, e baixe a tabela em CSV.

**2. Rode a ferramenta.**

```bash
python ai_referrer_report.py examples/ga4-traffic-acquisition-example.csv
```

**3. Leia o relatório.** Saída real do arquivo de exemplo em `examples/`,
que usa `example.com` e números inventados (dados fictícios):

```
=== ai-referrer-report: examples/ga4-traffic-acquisition-example.csv ===
Coluna de origem: "Origem da sessão" | 15 linha(s) | lista de domínios versão 2026-09-28
Sessões no arquivo: 3.991 | vindas de IA: 169 (4,2%) | conversões de IA: 6 de 39

-- POR PLATAFORMA --
  plataforma   sessões  % total    % IA  engaj.  usuários  conv.  origens
  chatgpt          105     2,6%   62,1%      81        95      4  chatgpt.com
  perplexity        28     0,7%   16,6%      23        26      1  perplexity.ai, www.perplexity.ai
  gemini            15     0,4%    8,9%      11        14      1  gemini.google.com
  claude             9     0,2%    5,3%       8         9      0  claude.ai
  copilot            9     0,2%    5,3%       5         9      0  copilot.microsoft.com, edgeservices.bing.com
  outra-ia           3     0,1%    1,8%       2         3      0  chat.deepseek.com

-- PÁGINAS DE DESTINO COM MAIS SESSÕES DE IA (top 10) --
      68 sessões, 3 conv.  /servicos/criacao-de-sites/  (chatgpt 64, copilot 4)
      63 sessões, 2 conv.  /blog/quanto-custa-um-site/  (chatgpt 41, perplexity 22)
      15 sessões, 1 conv.  /servicos/consultoria-de-seo/  (gemini 15)
      12 sessões, 0 conv.  /blog/o-que-e-seo/  (claude 9, outra-ia 3)
      11 sessões, 0 conv.  /  (perplexity 6, copilot 5)

-- ORIGENS AMBÍGUAS (host de IA que exige caminho, não classificadas) --
  kagi.com: 4 sessão(ões)

(Só a origem registrada pelo GA4. Tráfego de IA que chega sem referenciador aparece como direto e não é estimado aqui: o número é um piso.)
```

**4. Gere a regex para um grupo de canais personalizado do GA4.**

```bash
python ai_referrer_report.py --print-regex
```

Saída real (encurtada):

```
# Todas as plataformas de IA (condição: Origem da sessão / Session source, corresponde à regex)
^(.*\.)?(bard\.google\.com|chat\.deepseek\.com|chat\.mistral\.ai|chat\.openai\.com|chatgpt\.com|claude\.ai|copilot\.microsoft\.com|edgeservices\.bing\.com|gemini\.google\.com|grok\.com|meta\.ai|perplexity\.ai|phind\.com|poe\.com|x\.ai|you\.com)$

# Por plataforma
chatgpt: ^(.*\.)?(chat\.openai\.com|chatgpt\.com)$
perplexity: ^(.*\.)?(perplexity\.ai)$
...
```

No GA4, crie um canal em um grupo de canais personalizado com a condição
Origem "corresponde à regex" e cole a linha. A página de ajuda do GA4
sobre [grupos de canais personalizados](https://support.google.com/analytics/answer/13051316)
(acessada em 2026) mostra onde fica a configuração e traz um exemplo para
assistentes de IA. Coloque o canal novo acima do canal de referência na
ordem dos canais; do contrário, a regra de referência pega essas sessões
primeiro.

**5. Salve o resultado.** `--csv` grava o resumo por plataforma; `--json`
grava o relatório completo, com páginas de destino e origens ambíguas. Use
`-` para imprimir na tela.

```bash
python ai_referrer_report.py export.csv --csv plataformas.csv --json relatorio.json
```

**6. Use a sua própria lista de domínios** se quiser acrescentar ou tirar
plataformas.

```bash
python ai_referrer_report.py export.csv --referrers minha-lista.json
```

## Perguntas frequentes

**Por que a ferramenta não conta o tráfego direto que provavelmente veio de IA?**
Porque não existe forma confiável de separá-lo no GA4. Qualquer divisão do
tráfego direto seria estimativa, e esta ferramenta relata só o que foi
registrado. Trate o resultado como um mínimo.

**Por que kagi.com aparece como ambíguo?**
O `kagi.com` hospeda um buscador e um assistente de IA. A dimensão origem
da sessão traz só o host, então a ferramenta não sabe qual dos dois mandou
a visita. Com a dimensão referenciador da página, que traz a URL completa,
`kagi.com/assistant` é classificado como IA.

**Como acrescento uma plataforma de IA nova?**
Edite o `ai_referrers.json`, coloque o domínio na plataforma certa (ou em
`outra-ia`) e mude o campo `version`. Pull requests com domínios novos são
bem-vindos, de preferência com uma fonte pública que mostre o
referenciador.

**A ferramenta é gratuita e precisa de internet?**
É gratuita e de código aberto, sob a licença MIT. Ela só lê o arquivo
local que você passa; nenhum dado sai da sua máquina.

## Limitações

O resultado é um piso: visitas de IA sem referenciador aparecem como
diretas e não entram na conta. A origem da sessão pode vir de um
`utm_source` colocado pela própria plataforma, e é contada como o GA4 a
registrou. A lista de domínios muda com o tempo e precisa de revisão. A
ferramenta lê uma tabela por arquivo e não junta períodos nem
propriedades. Sessões e conversões seguem as configurações de atribuição
do próprio GA4 no relatório exportado.

## Método e origem

A ferramenta nasceu da regra interna de atribuição do
[lucasferrazseo.com](https://lucasferrazseo.com): uma visita é atribuída
só pela origem real registrada, e tráfego sem referenciador nunca é
remanejado para IA por inferência. Aqui ela está generalizada para uso
público, com uma lista aberta de domínios no lugar de configurações de um
site.

## Como contribuir

Relatos de erro e sugestões são bem-vindos pelas [Issues do GitHub](https://github.com/LucasFerrazSEO/ai-referrer-report/issues).

## Autor

[Lucas Ferraz](https://lucasferraz.com) é especialista em SEO, criação de sites e Generative Engine Optimization e fundador da [Lucas Ferraz SEO](https://lucasferrazseo.com).

## Licença

MIT. Veja o arquivo [LICENSE](LICENSE).
