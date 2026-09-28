**English** · [Português (Brasil)](README.pt-BR.md)

# ai-referrer-report

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)

`ai-referrer-report` is a free, open source command-line tool that reads a
CSV exported from Google Analytics 4 and reports the sessions and
conversions that arrived from AI assistants (ChatGPT, Perplexity, Gemini,
Claude, Copilot and others), by platform and by landing page. It
classifies traffic only by the source or referrer that GA4 recorded, using
an open, versioned list of domains, and it can print a ready-made regex
for a GA4 custom channel group. It runs offline on your machine, and no
data is sent to any server.

The tool prints its report in Brazilian Portuguese.

## Contents

- [Background](#background)
- [What it checks](#what-it-checks)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [FAQ](#faq)
- [Limitations](#limitations)
- [Methodology](#methodology)
- [Contributing](#contributing)
- [Author](#author)
- [License](#license)

## Background

Visits from AI assistants are spread across many referrer domains, and by
default GA4 groups most of them under the generic Referral channel. To
answer simple questions (how many sessions came from ChatGPT last month,
which pages they landed on, whether any of them converted) you need to
match each source against a list of AI domains.

That list is the only rule here. The tool does not guess. Part of the
traffic that comes from AI arrives without a referrer (mobile apps, a
copied link, browsers or settings that strip the header) and GA4 records
it as direct. `ai-referrer-report` does not try to estimate that share, so
its numbers are a floor, not the total.

## What it checks

1. **Classification by the real source.** Each value of "Session source"
   / "Origem da sessão" or "Page referrer" / "Referenciador da página" is
   matched against `ai_referrers.json`. A host matches when it equals a
   listed domain or is a subdomain of it (`www.perplexity.ai` counts as
   `perplexity.ai`). "Session source / medium" values such as
   `chatgpt.com / referral` are also accepted.
2. **Platforms.** `chatgpt`, `perplexity`, `gemini`, `claude`, `copilot`
   and `outra-ia` (other AI: You.com, Phind, Poe, DeepSeek, Meta AI, Grok,
   Mistral Le Chat, Kagi Assistant).
3. **Totals and shares.** Sessions, engaged sessions, users and
   conversions ("Key events" / "Eventos principais") per platform, the
   share of all sessions in the file and the share of AI sessions.
4. **Landing pages.** When the file has "Landing page" / "Página de
   destino", the top N pages by AI sessions, with the split by platform.
5. **Ambiguous sources.** Entries with `path_prefix` (Kagi Assistant lives
   at `kagi.com/assistant`, while `kagi.com` is also a search engine) only
   match when the value carries the path, which happens with Page
   referrer. With Session source, which carries only the host, those rows
   are listed as ambiguous and left out of the totals.
6. **Regex for GA4.** `--print-regex` prints one regex for all AI
   platforms and one per platform, generated from the same list.

GA4 comment lines starting with `#` at the top of the export are skipped.
The separator (`,` or `;`) and the decimal mark are detected
automatically.

## Requirements

Python 3.9 or newer. Standard library only, no external dependencies.

## Installation

```bash
git clone https://github.com/LucasFerrazSEO/ai-referrer-report.git
cd ai-referrer-report
```

## Usage

**1. Export the data from GA4.** In the Traffic acquisition report (or in
an Exploration), use "Session source" as the dimension, optionally add
"Landing page" as a secondary dimension, and download the table as CSV.

**2. Run the tool.**

```bash
python ai_referrer_report.py examples/ga4-traffic-acquisition-example.csv
```

**3. Read the report.** Real output from the example file in `examples/`,
which uses `example.com` and made-up numbers (fictitious data). The tool
prints its report in Brazilian Portuguese.

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

The numbers are displayed in Brazilian format (dot for thousands, comma for
decimals).

**4. Print the regex for a GA4 custom channel group.**

```bash
python ai_referrer_report.py --print-regex
```

Real output (shortened):

```
# Todas as plataformas de IA (condição: Origem da sessão / Session source, corresponde à regex)
^(.*\.)?(bard\.google\.com|chat\.deepseek\.com|chat\.mistral\.ai|chat\.openai\.com|chatgpt\.com|claude\.ai|copilot\.microsoft\.com|edgeservices\.bing\.com|gemini\.google\.com|grok\.com|meta\.ai|perplexity\.ai|phind\.com|poe\.com|x\.ai|you\.com)$

# Por plataforma
chatgpt: ^(.*\.)?(chat\.openai\.com|chatgpt\.com)$
perplexity: ^(.*\.)?(perplexity\.ai)$
...
```

In GA4, create a channel in a custom channel group with the condition
Source "matches regex" and paste the line. The GA4 help page on
[custom channel groups](https://support.google.com/analytics/answer/13051316)
(accessed 2026) explains where the setting lives and includes an AI
assistants example. Place the new channel above Referral in the channel
order, otherwise the Referral rule catches those sessions first.

**5. Save the result.** `--csv` writes the per-platform summary; `--json`
writes the full report, including landing pages and ambiguous sources.
Use `-` to print to the screen.

```bash
python ai_referrer_report.py export.csv --csv platforms.csv --json report.json
```

**6. Use your own domain list** if you want to add or remove platforms.

```bash
python ai_referrer_report.py export.csv --referrers my-list.json
```

## FAQ

**Why does the tool not count direct traffic that probably came from AI?**
Because there is no reliable way to tell it apart in GA4. Any split of
direct traffic would be an estimate, and this tool reports only what was
recorded. Treat the result as a minimum.

**Why is kagi.com listed as ambiguous?**
`kagi.com` hosts both a search engine and an AI assistant. The Session
source dimension only carries the host, so the tool cannot know which one
sent the visit. With the Page referrer dimension, which carries the full
URL, `kagi.com/assistant` is classified as AI.

**How do I add a new AI platform?**
Edit `ai_referrers.json`, add the domain under the right platform (or
under `outra-ia`) and change the `version` field. Pull requests with new
domains are welcome, ideally with a public source showing the referrer.

**Is the tool free and does it need an internet connection?**
It is free and open source under the MIT license. It only reads the local
file you pass to it; no data leaves your machine.

## Limitations

The result is a floor: AI visits without a referrer appear as direct and
are not counted. Session source can come from a `utm_source` added by the
platform itself, and it is counted as GA4 recorded it. The domain list
changes over time and needs review. The tool reads one table per file and
does not merge date ranges or properties. Sessions and conversions follow
GA4's own attribution settings for the report you exported.

## Methodology

The tool comes from the internal attribution rule used at
[lucasferrazseo.com](https://lucasferrazseo.com): a visit is attributed
only by its real, recorded source, and traffic without a referrer is never
reassigned to AI by inference. It is generalized here for public use, with
an open domain list instead of site-specific settings.

## Contributing

Bug reports and suggestions are welcome through [GitHub Issues](https://github.com/LucasFerrazSEO/ai-referrer-report/issues).

## Author

[Lucas Ferraz](https://lucasferraz.com) is an SEO, website development and Generative Engine Optimization specialist and the founder of [Lucas Ferraz SEO](https://lucasferrazseo.com).

## License

MIT. See [LICENSE](LICENSE).
