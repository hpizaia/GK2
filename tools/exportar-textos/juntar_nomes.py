#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Junta a exportação oficial do jogo (gk2_textos.json ou gk2_textos_pt-br.csv,
gerada por exportar_textos.py no PC do jogador) com as gameKey de
data/names.machine.pt-BR.json e grava data/names.official.pt-BR.json.

Uso (na raiz do projeto):
    python3 -I tools/exportar-textos/juntar_nomes.py [EXPORT] [opções]

    EXPORT       gk2_textos.json ou gk2_textos_pt-br.csv
                 (padrão: data/game-texts/gk2_textos.json; se não existir,
                 tools/exportar-textos/gk2_textos.json, depois os CSVs)
    --nomes      arquivo de nomes com gameKey (padrão: data/names.machine.pt-BR.json)
    --saida      arquivo gerado (padrão: data/names.official.pt-BR.json)
    --completo   inclui também as entradas sem correspondência, sem alteração
                 (por padrão o arquivo traz só as entradas oficiais)
    --atualizar  modo patch do jogo (o que usar no dia a dia): parte do
                 names.official.pt-BR.json ATUAL (--saida), troca o pt/en_game
                 de cada entrada pelo texto novo da mesma gameKey, mantém as
                 entradas ligadas à mão (zonas, perks, matched_by en-text*) e
                 acrescenta as gameKeys novas do --nomes. Sem mudanças,
                 o arquivo fica byte a byte igual.

Atenção: sem --atualizar o arquivo é refeito só pela gameKey do --nomes
(972 entradas) e perde as ~32 entradas ligadas à mão. Use --atualizar.

Formato de saída (mesmo esquema dos outros names.*.pt-BR.json, mais um _meta):
    "Bronze Nails": {"pt": "...", "source": "game-files", "confidence": "official",
                     "kind": [...], "priority": 1, "gameKey": "nails_bronze"}
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

PASTA = Path(__file__).resolve().parent
RAIZ = PASTA.parents[1]
MARCACAO = re.compile(r"<[^>]+>|[#@]\([^)]*\)|%\d+|\{[^{}]+\}")


def carregar_export(caminho):
    """Devolve {chave: {"pt": str|None, "en": str|None}}."""
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".json":
        with caminho.open(encoding="utf-8-sig") as f:
            dados = json.load(f)
        saida = {}
        for k, v in dados.items():
            if k == "_meta":
                continue
            if isinstance(v, dict):
                saida[k] = {"pt": v.get("pt"), "en": v.get("en")}
            elif isinstance(v, str):
                saida[k] = {"pt": v, "en": None}
        return saida
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor)
        nomes = [c.strip().lower() for c in cabecalho]
        i_chave = nomes.index("key") if "key" in nomes else 0
        i_texto = next((nomes.index(c) for c in ("text", "pt", "value", "source") if c in nomes), 1)
        saida = {}
        for linha in leitor:
            if len(linha) > max(i_chave, i_texto):
                saida[linha[i_chave]] = {"pt": linha[i_texto], "en": None}
    return saida


def _limpo(texto):
    """Texto do jogo sem tags (<sprite ...>) e com espaços normalizados."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", texto or "")).strip()


def atualizar(textos, export, args):
    """Atualiza o names.official.pt-BR.json existente com uma exportação nova."""
    destino = Path(args.saida)
    with destino.open(encoding="utf-8") as f:
        base = json.load(f)
    with open(args.nomes, encoding="utf-8") as f:
        nomes = json.load(f)
    mudou, sumiu, conferir, novas = [], [], [], []
    for nome_en, e in base.items():
        if nome_en.startswith("_") or not isinstance(e, dict):
            continue
        t = textos.get(e.get("gameKey") or "")
        if not t or not _limpo(t.get("pt")):
            sumiu.append(nome_en)
            continue
        if e.get("matched_by") == "en-text-fuzzy":   # pt e en_game sem a tag, mantidos
            conferir.append("%s: %r (jogo: %r)" % (nome_en, e.get("pt"), t.get("pt")))
            continue
        if t.get("en") is not None:
            e["en_game"] = t["en"]
        pt = _limpo(t["pt"])
        if pt != e.get("pt"):
            mudou.append("%s: %r -> %r" % (nome_en, e.get("pt"), pt))
            e["pt"] = pt
    for nome_en, e in nomes.items():
        if nome_en.startswith("_") or not isinstance(e, dict) or nome_en in base:
            continue
        t = textos.get(e.get("gameKey") or "")
        if t and _limpo(t.get("pt")):
            base[nome_en] = {"pt": _limpo(t["pt"]), "source": "game-files", "confidence": "official",
                             "gameKey": e["gameKey"], "en_game": t.get("en")}
            novas.append(nome_en)
    meta = base.setdefault("_meta", {})
    try:
        meta["source"] = Path(export).resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        meta["source"] = Path(export).name
    resumo = Path(export).with_name("_resumo.json")
    if resumo.exists():
        versao = json.loads(resumo.read_text(encoding="utf-8")).get("versao_jogo")
        if versao:
            meta["game_version"] = versao
    meta["matched"] = sum(1 for k, v in base.items() if not k.startswith("_") and isinstance(v, dict))
    texto = json.dumps(base, ensure_ascii=False, indent=1)
    antigo = destino.read_text(encoding="utf-8")
    if texto != antigo:
        destino.write_text(texto, encoding="utf-8", newline="\n")
    print("Exportação:        %s (%d chaves)" % (export, len(textos)))
    print("Entradas:          %d (novas: %d)" % (meta["matched"], len(novas)))
    print("pt alterado:       %d" % len(mudou))
    for linha in mudou + ["NOVA " + n for n in novas]:
        print("    " + linha)
    print("gameKey sem texto na exportação (mantidas como estavam): %d" % len(sumiu))
    for n in sumiu:
        print("    " + n)
    print("conferir à mão (texto com ícone no meio, pt mantido): %d" % len(conferir))
    for linha in conferir:
        print("    " + linha)
    print("Gravado:           %s" % destino if texto != antigo else "Sem mudanças:      %s" % destino)


def principal():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", nargs="?")
    ap.add_argument("--nomes", default=str(RAIZ / "data" / "names.machine.pt-BR.json"))
    ap.add_argument("--saida", default=str(RAIZ / "data" / "names.official.pt-BR.json"))
    ap.add_argument("--completo", action="store_true")
    ap.add_argument("--atualizar", action="store_true")
    args = ap.parse_args()

    export = args.export
    if not export:
        jogo = RAIZ / "data" / "game-texts"
        for c in (jogo / "gk2_textos.json", PASTA / "gk2_textos.json",
                  jogo / "gk2_textos_pt-br.csv", PASTA / "gk2_textos_pt-br.csv"):
            if c.exists():
                export = str(c)
                break
    if not export or not Path(export).exists():
        sys.exit("ERRO: exportação não encontrada. Informe o caminho do gk2_textos.json ou gk2_textos_pt-br.csv.")

    textos = carregar_export(export)
    if args.atualizar:
        return atualizar(textos, export, args)
    with open(args.nomes, encoding="utf-8") as f:
        nomes = json.load(f)
    meta_original = nomes.get("_meta", {})

    textos_lower = {}
    for k in textos:
        textos_lower.setdefault(k.lower(), k)

    saida = {}
    cont = {"entradas": 0, "comGameKey": 0, "oficiais": 0, "viaMaiusculas": 0, "semTextoPt": 0,
            "chaveAusente": 0, "mudouDoPalpite": 0, "comMarcacao": 0, "enDiferenteDoNome": 0,
            "ptIgualAoIngles": 0, "ptIgualAoNomeEn": 0}
    ausentes, com_marcacao, en_diferente = [], [], []
    for nome_en, entrada in nomes.items():
        if nome_en.startswith("_") or not isinstance(entrada, dict):
            continue
        cont["entradas"] += 1
        chave = entrada.get("gameKey")
        achado = None
        if chave:
            cont["comGameKey"] += 1
            if chave in textos:
                achado = chave
            elif chave.lower() in textos_lower:
                achado = textos_lower[chave.lower()]
                cont["viaMaiusculas"] += 1
            else:
                cont["chaveAusente"] += 1
                ausentes.append(nome_en)
        pt = textos[achado]["pt"] if achado else None
        if achado and (pt is None or not str(pt).strip()):
            cont["semTextoPt"] += 1
            achado = None
        if not achado:
            if args.completo:
                saida[nome_en] = entrada
            continue
        pt = str(pt).strip()
        nova = dict(entrada)
        nova["pt"] = pt
        nova["source"] = "game-files"
        nova["confidence"] = "official"
        nova["gameKey"] = achado
        saida[nome_en] = nova
        cont["oficiais"] += 1
        if pt != entrada.get("pt"):
            cont["mudouDoPalpite"] += 1
        if pt.lower() == nome_en.strip().lower():
            cont["ptIgualAoNomeEn"] += 1
        if MARCACAO.search(pt):
            cont["comMarcacao"] += 1
            com_marcacao.append(nome_en)
        en = textos[achado].get("en")
        if en is not None:
            if MARCACAO.sub("", en).strip().lower() != nome_en.strip().lower():
                cont["enDiferenteDoNome"] += 1
                en_diferente.append("%s -> %s" % (nome_en, en))
            if pt == en:
                cont["ptIgualAoIngles"] += 1

    saida_final = {"_meta": {
        "generated": time.strftime("%Y-%m-%d"),
        "from": Path(export).name,
        "join": Path(args.nomes).name + " gameKey -> official game locale lng_pt-br",
        "sources": {"game-files": "official text exported from the player's copy of the game (lng_pt-br)"},
        "counts": cont,
        "missingGameKeys": ausentes,
        "withMarkup": com_marcacao,
        "legend": meta_original.get("priority"),
    }}
    saida_final.update(saida)

    destino = Path(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(saida_final, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("Exportação:        %s (%d chaves)" % (export, len(textos)))
    print("Nomes:             %s (%d entradas, %d com gameKey)" % (args.nomes, cont["entradas"], cont["comGameKey"]))
    print("OFICIAIS:          %d de %d com gameKey" % (cont["oficiais"], cont["comGameKey"]))
    print("  achadas ignorando maiúsculas: %d" % cont["viaMaiusculas"])
    print("  gameKey ausente na exportação: %d" % cont["chaveAusente"])
    print("  chave presente mas sem texto pt: %d" % cont["semTextoPt"])
    print("  pt diferente do palpite anterior: %d" % cont["mudouDoPalpite"])
    print("  com marcação (<tag>, #(), @(), %%1, {0}): %d" % cont["comMarcacao"])
    print("  pt igual ao nome em inglês: %d" % cont["ptIgualAoNomeEn"])
    if cont["oficiais"] and any(v.get("en") for v in textos.values()):
        print("  texto EN do jogo diferente do nome EN: %d" % cont["enDiferenteDoNome"])
    if cont["oficiais"] and cont["ptIgualAoNomeEn"] > 0.7 * cont["oficiais"]:
        print("  AVISO: a maioria dos textos pt é igual ao inglês; a exportação parece não ser pt-BR.")
    for exemplo in en_diferente[:10]:
        print("    EN difere: " + exemplo)
    print("Gravado:           %s" % destino)


if __name__ == "__main__":
    principal()
