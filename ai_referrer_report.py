#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-referrer-report: mede sessões e conversões que chegaram de assistentes de
IA (ChatGPT, Perplexity, Gemini, Claude, Copilot e outros) a partir de um CSV
exportado do Google Analytics 4, só pela origem real registrada.

O QUE FAZ
    Lê um CSV do GA4 (relatório de aquisição de tráfego ou exploração) com a
    dimensão "Session source" / "Origem da sessão" ou "Page referrer" /
    "Referenciador da página", opcionalmente "Landing page" / "Página de
    destino", e as métricas de sessões, sessões engajadas, usuários e
    conversões ("Key events" / "Eventos principais"). Classifica cada origem
    pela lista aberta ai_referrers.json e imprime:

    - sessões, sessões engajadas, usuários e conversões por plataforma
      (chatgpt, perplexity, gemini, claude, copilot, outra-ia);
    - a participação de cada plataforma no total de sessões do arquivo;
    - as páginas de destino que mais receberam sessões de IA (top N);
    - com --print-regex, a expressão regular pronta para uma condição
      "corresponde à regex" de um grupo de canais personalizado do GA4.

MÉTODO
    Classificação só pelo valor de origem ou referenciador que o GA4 gravou,
    sem inferência: o host precisa ser igual a um domínio da lista ou
    subdomínio dele (www.perplexity.ai conta como perplexity.ai). Entradas com
    path_prefix (ex.: o assistente do Kagi em kagi.com/assistant) só
    classificam quando o valor traz o caminho, o que acontece com o
    referenciador da página; com a origem da sessão, que só traz o host, a
    linha fica registrada como ambígua. Linhas de comentário do export (#) são
    ignoradas; separador , ou ; e decimal com vírgula ou ponto são detectados.

USO
    python ai_referrer_report.py export-ga4.csv
    python ai_referrer_report.py export-ga4.csv --top 20
    python ai_referrer_report.py export-ga4.csv --csv plataformas.csv --json relatorio.json
    python ai_referrer_report.py --print-regex
    python ai_referrer_report.py export-ga4.csv --referrers minha-lista.json

LIMITAÇÕES
    Parte do tráfego vindo de IA chega sem referenciador (aplicativo, cópia
    do link, navegador que remove o cabeçalho) e aparece no GA4 como direto.
    A ferramenta não estima essa parte: o número dela é um piso, não o total.
    A origem da sessão pode vir de utm_source colocado pela própria
    plataforma, e é contada como o GA4 a registrou. A lista de domínios muda
    com o tempo e precisa de revisão.

Autor: Lucas Ferraz (lucasferraz.com), dependência zero, só biblioteca padrão.
Licença: MIT.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from urllib.parse import urlsplit

PLATAFORMAS = ("chatgpt", "perplexity", "gemini", "claude", "copilot", "outra-ia")


def _chave(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", nome.strip().lstrip("﻿"))
    nome = "".join(c for c in nome if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", nome).strip()


ALIASES = {
    "source": {"session source", "session source medium", "origem da sessao",
               "origem meio da sessao", "source", "source medium", "origem",
               "origem meio"},
    "referrer": {"page referrer", "referenciador da pagina", "referrer",
                 "referenciador"},
    "landing": {"landing page", "landing page query string", "pagina de destino",
                "pagina de destino string de consulta",
                "pagina de destino e string de consulta"},
    "sessions": {"sessions", "sessoes"},
    "engaged": {"engaged sessions", "sessoes engajadas", "engaged users",
                "usuarios engajados"},
    "users": {"active users", "usuarios ativos", "total users", "total de usuarios",
              "users", "usuarios"},
    "conversions": {"key events", "eventos principais", "eventos chave",
                    "conversions", "conversoes"},
}

LINHAS_TOTAL = {"total", "totals", "grand total", "totais", "total geral"}


def mapeia_colunas(cabecalho: list[str]) -> dict[str, int]:
    mapa: dict[str, int] = {}
    for i, nome in enumerate(cabecalho):
        k = _chave(nome)
        for campo, nomes in ALIASES.items():
            if k in nomes and campo not in mapa:
                mapa[campo] = i
    return mapa


def para_numero(valor: str, decimal: str = "auto") -> float:
    s = (valor or "").strip().replace("%", "").replace(" ", "").replace(" ", "")
    if not s or s in {"-", "--", "(not set)"}:
        return 0.0
    if decimal == "comma":
        s = s.replace(".", "").replace(",", ".")
    elif decimal == "dot":
        s = s.replace(",", "")
    elif "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def le_tabela(texto: str) -> tuple[list[str], list[list[str]], dict[str, int]]:
    """Separa o export em blocos (linhas # e em branco dividem) e devolve o
    primeiro bloco cujo cabeçalho tem coluna de origem ou referenciador."""
    blocos: list[list[str]] = [[]]
    for linha in texto.splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            if blocos[-1]:
                blocos.append([])
            continue
        blocos[-1].append(linha)
    for bloco in blocos:
        if len(bloco) < 1:
            continue
        amostra = "\n".join(bloco[:5])
        sep = ";" if amostra.count(";") > amostra.count(",") else ","
        if bloco[0].count("\t") > bloco[0].count(sep):
            sep = "\t"
        linhas = list(csv.reader(io.StringIO("\n".join(bloco)), delimiter=sep))
        mapa = mapeia_colunas(linhas[0])
        if ("source" in mapa or "referrer" in mapa) and "sessions" in mapa:
            return linhas[0], linhas[1:], mapa
    return [], [], {}


def carrega_lista(caminho: str) -> list[tuple[str, str, str]]:
    with open(caminho, encoding="utf-8") as fh:
        dados = json.load(fh)
    regras = []
    for plataforma, entradas in dados.get("platforms", {}).items():
        for e in entradas:
            regras.append((e["domain"].lower().strip("."), e.get("path_prefix", ""), plataforma))
    # domínio mais longo primeiro: gemini.google.com antes de um eventual google.com
    regras.sort(key=lambda r: -len(r[0]))
    return regras


def separa_host(valor: str) -> tuple[str, str]:
    v = valor.strip().lower()
    v = v.split(" / ")[0].strip()  # "chatgpt.com / referral" -> "chatgpt.com"
    if "://" in v:
        partes = urlsplit(v)
        return (partes.hostname or ""), partes.path or ""
    if "/" in v:
        host, _, resto = v.partition("/")
        return host, "/" + resto
    return v, ""


def classifica(valor: str, regras) -> tuple[str, str]:
    """Devolve (plataforma, "") se casou, ("", "ambigua") se só o host casou
    com uma entrada que exige caminho, ou ("", "")."""
    host, caminho = separa_host(valor)
    if not host:
        return "", ""
    ambigua = False
    for dominio, prefixo, plataforma in regras:
        if host == dominio or host.endswith("." + dominio):
            if not prefixo:
                return plataforma, ""
            if caminho.startswith(prefixo):
                return plataforma, ""
            if not caminho:
                ambigua = True
    return "", ("ambigua" if ambigua else "")


def gera_regex(regras) -> tuple[str, dict[str, str], list[str]]:
    por_plat: dict[str, list[str]] = defaultdict(list)
    fora = []
    for dominio, prefixo, plataforma in regras:
        if prefixo:
            fora.append(dominio + prefixo)
            continue
        por_plat[plataforma].append(re.escape(dominio))

    def monta(doms: list[str]) -> str:
        return r"^(.*\.)?(" + "|".join(sorted(doms)) + r")$"

    todas = [d for p in PLATAFORMAS for d in por_plat.get(p, [])]
    return monta(todas), {p: monta(por_plat[p]) for p in PLATAFORMAS if por_plat.get(p)}, fora


def _fmt(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def _pct(parte: float, todo: float) -> str:
    return (f"{100 * parte / todo:.1f}".replace(".", ",") + "%") if todo else "n/d"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Sessões e conversões vindas de assistentes de IA em um export do GA4, só pela origem real.")
    ap.add_argument("arquivo", nargs="?", help="CSV exportado do GA4 (ou '-' para entrada padrão)")
    ap.add_argument("--referrers", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                        "ai_referrers.json"),
                    help="lista de domínios de IA (padrão: ai_referrers.json ao lado do script)")
    ap.add_argument("--top", type=int, default=10, help="quantas páginas de destino mostrar (padrão 10)")
    ap.add_argument("--decimal", choices=["auto", "comma", "dot"], default="auto",
                    help="separador decimal dos números (padrão: detecção automática)")
    ap.add_argument("--csv", metavar="ARQUIVO", help="grava o resumo por plataforma em CSV ('-' para a tela)")
    ap.add_argument("--json", metavar="ARQUIVO", help="grava o relatório completo em JSON ('-' para a tela)")
    ap.add_argument("--print-regex", action="store_true",
                    help="imprime a regex para grupo de canais personalizado do GA4 e sai")
    args = ap.parse_args()
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    try:
        regras = carrega_lista(args.referrers)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Não consegui ler a lista {args.referrers}: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.print_regex:
        geral, por_plat, fora = gera_regex(regras)
        print("# Todas as plataformas de IA (condição: Origem da sessão / Session source, corresponde à regex)")
        print(geral)
        print("\n# Por plataforma")
        for p, rx in por_plat.items():
            print(f"{p}: {rx}")
        if fora:
            print("\n# Fora da regex (dependem do caminho do referenciador, que a origem não traz): "
                  + ", ".join(fora))
        return

    if not args.arquivo:
        ap.error("informe o arquivo CSV ou use --print-regex")
    try:
        if args.arquivo == "-":
            texto = sys.stdin.read()
        else:
            with open(args.arquivo, encoding="utf-8-sig", newline="") as fh:
                texto = fh.read()
    except OSError as exc:
        print(f"Não consegui ler {args.arquivo}: {exc}", file=sys.stderr)
        sys.exit(2)

    cabecalho, linhas, mapa = le_tabela(texto)
    if not cabecalho:
        print("Erro: nenhuma tabela com coluna de origem da sessão (ou referenciador da página) "
              "e coluna de sessões foi encontrada no arquivo.", file=sys.stderr)
        sys.exit(2)
    col_origem = mapa.get("referrer", mapa.get("source"))
    nome_origem = cabecalho[col_origem]

    metricas = [m for m in ("sessions", "engaged", "users", "conversions") if m in mapa]
    tot_geral = defaultdict(float)
    por_plat: dict[str, dict] = {p: defaultdict(float) for p in PLATAFORMAS}
    origens_plat: dict[str, set] = defaultdict(set)
    por_pagina: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    ambiguas: dict[str, float] = defaultdict(float)
    lidas = 0

    for row in linhas:
        if len(row) <= col_origem:
            continue
        origem = row[col_origem].strip()
        if not origem or _chave(origem) in LINHAS_TOTAL:
            continue
        lidas += 1
        valores = {m: para_numero(row[mapa[m]], args.decimal) if mapa[m] < len(row) else 0.0
                   for m in metricas}
        for m, v in valores.items():
            tot_geral[m] += v
        plataforma, flag = classifica(origem, regras)
        if flag == "ambigua":
            ambiguas[origem] += valores.get("sessions", 0.0)
        if not plataforma:
            continue
        origens_plat[plataforma].add(separa_host(origem)[0])
        for m, v in valores.items():
            por_plat[plataforma][m] += v
        if "landing" in mapa and mapa["landing"] < len(row):
            pagina = row[mapa["landing"]].strip() or "(not set)"
            for m, v in valores.items():
                por_pagina[pagina][m] += v
            por_pagina[pagina]["_" + plataforma] += valores.get("sessions", 0.0)

    tot_ia = defaultdict(float)
    for p in PLATAFORMAS:
        for m in metricas:
            tot_ia[m] += por_plat[p][m]

    resumo = []
    for p in PLATAFORMAS:
        d = por_plat[p]
        if not d.get("sessions"):
            continue
        resumo.append({"platform": p, "sources": sorted(origens_plat[p]),
                       **{m: d[m] for m in metricas},
                       "share_of_all_sessions_pct": round(100 * d["sessions"] / tot_geral["sessions"], 2)
                       if tot_geral["sessions"] else None,
                       "share_of_ai_sessions_pct": round(100 * d["sessions"] / tot_ia["sessions"], 2)
                       if tot_ia["sessions"] else None})
    resumo.sort(key=lambda r: -r["sessions"])
    paginas = sorted(({"landing_page": pg, **{m: v for m, v in d.items() if not m.startswith("_")},
                       "by_platform": {k[1:]: v for k, v in d.items() if k.startswith("_") and v}}
                      for pg, d in por_pagina.items()), key=lambda r: -r.get("sessions", 0))

    if args.csv:
        fh = sys.stdout if args.csv == "-" else open(args.csv, "w", encoding="utf-8", newline="")
        w = csv.writer(fh)
        w.writerow(["platform", *metricas, "share_of_all_sessions_pct", "share_of_ai_sessions_pct", "sources"])
        for r in resumo:
            w.writerow([r["platform"], *[int(r[m]) if float(r[m]).is_integer() else r[m] for m in metricas],
                        r["share_of_all_sessions_pct"], r["share_of_ai_sessions_pct"], " ".join(r["sources"])])
        if fh is not sys.stdout:
            fh.close()
    if args.json:
        saida = json.dumps({"file": args.arquivo, "source_column": nome_origem, "rows": lidas,
                            "totals_all": dict(tot_geral), "totals_ai": dict(tot_ia),
                            "platforms": resumo, "landing_pages": paginas,
                            "ambiguous_sources": dict(ambiguas),
                            "referrers_list_version": _versao(args.referrers)},
                           ensure_ascii=False, indent=2)
        if args.json == "-":
            print(saida)
        else:
            with open(args.json, "w", encoding="utf-8") as fh:
                fh.write(saida)
    if "-" in (args.csv, args.json):
        return

    print(f"\n=== ai-referrer-report: {args.arquivo} ===")
    print(f"Coluna de origem: \"{nome_origem}\" | {lidas} linha(s) | lista de domínios versão "
          f"{_versao(args.referrers)}")
    print(f"Sessões no arquivo: {_fmt(tot_geral['sessions'])} | vindas de IA: {_fmt(tot_ia['sessions'])} "
          f"({_pct(tot_ia['sessions'], tot_geral['sessions'])})"
          + (f" | conversões de IA: {_fmt(tot_ia['conversions'])} de {_fmt(tot_geral['conversions'])}"
             if "conversions" in metricas else ""))

    print("\n-- POR PLATAFORMA --")
    if not resumo:
        print("  Nenhuma sessão com origem de assistente de IA no arquivo.")
    cab = f"  {'plataforma':<11}{'sessões':>9}{'% total':>9}{'% IA':>8}"
    if "engaged" in metricas:
        cab += f"{'engaj.':>8}"
    if "users" in metricas:
        cab += f"{'usuários':>10}"
    if "conversions" in metricas:
        cab += f"{'conv.':>7}"
    if resumo:
        print(cab + "  origens")
    for r in resumo:
        linha = (f"  {r['platform']:<11}{_fmt(r['sessions']):>9}"
                 f"{_pct(r['sessions'], tot_geral['sessions']):>9}{_pct(r['sessions'], tot_ia['sessions']):>8}")
        if "engaged" in metricas:
            linha += f"{_fmt(r['engaged']):>8}"
        if "users" in metricas:
            linha += f"{_fmt(r['users']):>10}"
        if "conversions" in metricas:
            linha += f"{_fmt(r['conversions']):>7}"
        print(linha + "  " + ", ".join(r["sources"]))

    if "landing" in mapa and paginas:
        print(f"\n-- PÁGINAS DE DESTINO COM MAIS SESSÕES DE IA (top {args.top}) --")
        for pg in paginas[:args.top]:
            detalhe = ", ".join(f"{k} {_fmt(v)}" for k, v in
                                sorted(pg["by_platform"].items(), key=lambda kv: -kv[1]))
            conv = f", {_fmt(pg['conversions'])} conv." if "conversions" in metricas else ""
            print(f"  {_fmt(pg['sessions']):>6} sessões{conv}  {pg['landing_page']}  ({detalhe})")
    elif "landing" not in mapa:
        print("\n(Sem coluna de página de destino no arquivo: ranking por página não gerado.)")

    if ambiguas:
        print("\n-- ORIGENS AMBÍGUAS (host de IA que exige caminho, não classificadas) --")
        for o, s in sorted(ambiguas.items(), key=lambda kv: -kv[1]):
            print(f"  {o}: {_fmt(s)} sessão(ões)")

    print("\n(Só a origem registrada pelo GA4. Tráfego de IA que chega sem referenciador "
          "aparece como direto e não é estimado aqui: o número é um piso.)")


def _versao(caminho: str) -> str:
    try:
        with open(caminho, encoding="utf-8") as fh:
            return str(json.load(fh).get("version", "n/d"))
    except (OSError, ValueError):
        return "n/d"


if __name__ == "__main__":
    main()
