#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exportador de textos do Graveyard Keeper 2 (português do Brasil e inglês).

O que faz
---------
Lê (SOMENTE LÊ, nunca altera) o arquivo de dados do jogo instalado
(<pasta do jogo>/GraveyardKeeper2_Data/resources.assets), encontra os
idiomas "lng_pt-br" e "lng_en" e grava, ao lado deste script:

    gk2_textos_pt-br.csv     (colunas key,text — abre no Excel)
    gk2_textos_en.csv        (colunas key,text)
    gk2_textos.json          ({ "chave": {"en": "...", "pt": "..."} })
    gk2_exportacao_log.txt   (relatório do que aconteceu)

Uso
---
    Dê dois cliques em exportar_textos.bat   (jeito mais fácil)
ou, no Prompt de Comando:
    py -3 exportar_textos.py
    py -3 exportar_textos.py "D:\\SteamLibrary\\steamapps\\common\\Graveyard Keeper 2"

Opções:
    --sem-unitypy   usa apenas o leitor embutido (não precisa do UnityPy)
    --saida PASTA   grava os arquivos em outra pasta

Como o formato funciona (resumo técnico)
----------------------------------------
Cada idioma é um ScriptableObject do tipo LazyBearTechnology.LL guardado em
Resources/Locales/lng_<idioma> (o jogo chama Resources.Load<LL>("Locales/lng_pt-br")).
No arquivo .assets ele vira um MonoBehaviour serializado pela Unity, sem
compressão e sem criptografia:

    cabeçalho MonoBehaviour (28 bytes: m_GameObject, m_Enabled, m_Script)
    m_Name   string          ("lng_pt-br")
    aliases1 List<string>
    aliases2 List<string>
    id       string          ("pt-br")
    txtIds   List<string>    (chaves)
    txts     List<string>    (textos, na mesma ordem das chaves)
    nestedLocalesMetaInfos   List<{bool hasMetaInfo; List<int> idsToInsert; List<string> localeIDsToInsert}>
    replacementKeysMetaInfoList List<{string id; List<int> keysIndexes; List<string> keys}>

string = int32 tamanho + bytes UTF-8 + preenchimento até múltiplo de 4.
List   = int32 quantidade + itens.
Os metadados reinserem marcadores "#(chave)" e "@(chave)" no texto, em
posições contadas em unidades UTF-16 (como o .NET faz em string.Insert).

Baseado na leitura do locale_codec.py do projeto GK2Thai
(github.com/Jakkrich/graveyardkeeper2-bepinex-thai-plugin) e do código
decompilado LLBase.cs; reimplementado aqui, com alternativas tolerantes caso o
formato tenha mudado.
"""

import argparse
import csv
import gzip
import io
import json
import mmap
import os
import platform
import re
import string
import struct
import sys
import time
import traceback
import zlib
from pathlib import Path

VERSAO = "1.0 (2026-10-30)"
APP_ID = "4358690"
NOME_PASTA_JOGO = "Graveyard Keeper 2"
PASTA_DADOS_PREFERIDA = "GraveyardKeeper2_Data"
CABECALHO_MONOBEHAVIOUR = 28
IDIOMAS_ALVO = ("pt-br", "en")
MAX_LISTA = 400000
JANELA_VARREDURA = 64 * 1024 * 1024  # bytes analisados após o nome no modo varredura
MAX_DUMP = 32 * 1024 * 1024

# ---------------------------------------------------------------------------
# Saída no console e no log
# ---------------------------------------------------------------------------

for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_LOG = []
_ESTADO = {"saida": None}


def log(msg="", tela=True):
    _LOG.append(msg)
    if tela:
        try:
            print(msg, flush=True)
        except Exception:
            print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def detalhe(msg):
    """Só vai para o arquivo de log (informação técnica)."""
    log("    [detalhe] " + msg, tela=False)


def tamanho_legivel(n):
    for unidade in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unidade == "GB":
            return ("%d %s" % (n, unidade)) if unidade == "bytes" else ("%.1f %s" % (n, unidade))
        n /= 1024.0


# ---------------------------------------------------------------------------
# Localizar o jogo
# ---------------------------------------------------------------------------

def _unicos(caminhos):
    vistos, saida = set(), []
    for c in caminhos:
        try:
            chave = os.path.normcase(os.path.abspath(str(c)))
        except Exception:
            continue
        if chave not in vistos:
            vistos.add(chave)
            saida.append(Path(c))
    return saida


def _existe(p):
    try:
        return Path(p).exists()
    except (OSError, ValueError):
        return False


def _unidades_fixas_windows():
    """Letras de unidades de disco fixas (evita leitores de cartão vazios, DVD, rede)."""
    letras = []
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        mascara = k32.GetLogicalDrives()
        for i, letra in enumerate(string.ascii_uppercase):
            if mascara & (1 << i):
                raiz = letra + ":\\"
                if k32.GetDriveTypeW(ctypes.c_wchar_p(raiz)) == 3:  # DRIVE_FIXED
                    letras.append(letra)
    except Exception:
        letras = [l for l in "CDEFGH"]
    return letras


def raizes_steam():
    raizes = []
    if os.name == "nt":
        try:
            import winreg
            chaves = [
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ]
            for hive, sub, valor in chaves:
                try:
                    with winreg.OpenKey(hive, sub) as k:
                        v, _ = winreg.QueryValueEx(k, valor)
                        if v:
                            raizes.append(Path(v))
                except OSError:
                    pass
        except ImportError:
            pass
        for var in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"):
            if os.environ.get(var):
                raizes.append(Path(os.environ[var]) / "Steam")
        raizes += [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    else:
        casa = Path.home()
        raizes += [
            casa / ".steam" / "steam",
            casa / ".local" / "share" / "Steam",
            casa / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
            casa / "Library" / "Application Support" / "Steam",
        ]
    return [r for r in _unicos(raizes) if _existe(r)]


def bibliotecas_steam(raizes):
    libs = list(raizes)
    for raiz in raizes:
        for vdf in (raiz / "steamapps" / "libraryfolders.vdf", raiz / "config" / "libraryfolders.vdf"):
            if not _existe(vdf):
                continue
            try:
                texto = vdf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            detalhe("lido %s" % vdf)
            for m in re.finditer(r'"path"\s+"((?:[^"\\]|\\.)*)"', texto):
                libs.append(Path(m.group(1).replace("\\\\", "\\")))
            # formato antigo: "1"  "D:\\SteamLibrary"
            for m in re.finditer(r'^\s*"\d+"\s+"((?:[^"\\]|\\.)+)"\s*$', texto, re.M):
                libs.append(Path(m.group(1).replace("\\\\", "\\")))
    if os.name == "nt":
        subpastas = ["SteamLibrary", "Steam", r"Program Files (x86)\Steam", r"Program Files\Steam",
                     r"Games\Steam", r"Games\SteamLibrary", r"Jogos\Steam", r"Jogos\SteamLibrary"]
        for letra in _unidades_fixas_windows():
            for sub in subpastas:
                libs.append(Path(letra + ":\\") / sub)
    return [l for l in _unicos(libs) if _existe(l)]


def info_manifesto(lib):
    """Lê appmanifest_4358690.acf (pasta de instalação e número do build)."""
    acf = lib / "steamapps" / ("appmanifest_%s.acf" % APP_ID)
    if not _existe(acf):
        return None
    try:
        texto = acf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    info = {"arquivo": str(acf)}
    for campo in ("installdir", "buildid", "LastUpdated", "name"):
        m = re.search(r'"%s"\s+"([^"]*)"' % campo, texto, re.I)
        if m:
            info[campo] = m.group(1)
    return info


def candidatos_jogo():
    """Pastas onde o jogo provavelmente está, em ordem de preferência."""
    candidatos, manifestos = [], {}
    for lib in bibliotecas_steam(raizes_steam()):
        man = info_manifesto(lib)
        comuns = lib / "steamapps" / "common"
        if man and man.get("installdir"):
            p = comuns / man["installdir"]
            candidatos.append(p)
            manifestos[os.path.normcase(str(p))] = man
        candidatos.append(comuns / NOME_PASTA_JOGO)
    if os.name == "nt":
        for letra in _unidades_fixas_windows():
            raiz = Path(letra + ":\\")
            candidatos += [raiz / "XboxGames" / NOME_PASTA_JOGO / "Content",
                           raiz / "GOG Games" / NOME_PASTA_JOGO,
                           raiz / "Games" / NOME_PASTA_JOGO,
                           raiz / "Jogos" / NOME_PASTA_JOGO]
    return [c for c in _unicos(candidatos) if _existe(c)], manifestos


def resolver_pasta_dados(caminho):
    """Aceita a pasta do jogo, a pasta *_Data ou o próprio resources.assets.
    Devolve a pasta *_Data (que contém resources.assets) ou None."""
    p = Path(str(caminho).strip().strip('"').strip("'"))
    if not _existe(p):
        return None
    if p.is_file():
        return p.parent if p.suffix.lower() in (".assets", ".resource", ".ress") else None
    if _existe(p / "resources.assets"):
        return p
    opcoes = []
    for base in (p, p / "Content"):
        try:
            for filho in base.iterdir():
                if filho.is_dir() and filho.name.lower().endswith("_data") and _existe(filho / "resources.assets"):
                    opcoes.append(filho)
        except OSError:
            pass

    def ordem(d):
        nome = d.name.lower()
        return (0 if nome == PASTA_DADOS_PREFERIDA.lower() else 1, 1 if "demo" in nome else 0, nome)

    opcoes.sort(key=ordem)
    return opcoes[0] if opcoes else None


def perguntar_caminho():
    if not sys.stdin or not sys.stdin.isatty():
        return None
    log("")
    log("Não encontrei o jogo sozinho. Vamos indicar a pasta manualmente:")
    log("  1. Abra a Steam > Biblioteca > clique com o botão direito em Graveyard Keeper 2")
    log("  2. Gerenciar > Procurar arquivos locais (abre a pasta do jogo)")
    log("  3. Clique na barra de endereço do Explorer, copie o caminho (Ctrl+C)")
    log("  4. Cole aqui embaixo (botão direito ou Ctrl+V) e aperte Enter")
    for _ in range(3):
        try:
            resposta = input("\nCaminho da pasta do jogo (Enter vazio para sair): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not resposta:
            return None
        dados = resolver_pasta_dados(resposta)
        if dados:
            return dados
        log("  Essa pasta não tem o arquivo resources.assets do jogo. Confira e tente de novo.")
    return None


def localizar_jogo(argumento):
    if argumento:
        dados = resolver_pasta_dados(argumento)
        if dados:
            return dados, None
        log("ATENÇÃO: o caminho informado não contém os dados do jogo: %s" % argumento)
    if os.environ.get("GK2_GAME_PATH"):
        dados = resolver_pasta_dados(os.environ["GK2_GAME_PATH"])
        if dados:
            return dados, None
    log("Procurando o Graveyard Keeper 2 nas bibliotecas da Steam...")
    candidatos, manifestos = candidatos_jogo()
    for c in candidatos:
        detalhe("candidato: %s" % c)
        dados = resolver_pasta_dados(c)
        if dados:
            return dados, manifestos.get(os.path.normcase(str(c)))
    return perguntar_caminho(), None


# ---------------------------------------------------------------------------
# Decodificador do formato lng_<idioma>
# ---------------------------------------------------------------------------

class FormatoInvalido(Exception):
    pass


class Leitor:
    """Lê dados serializados da Unity (little-endian, strings alinhadas em 4 bytes)."""

    def __init__(self, dados, pos, fim=None, base=None, tolerante=False):
        self.d = dados
        self.pos = pos
        self.fim = len(dados) if fim is None else min(fim, len(dados))
        self.base = pos if base is None else base
        self.tolerante = tolerante

    def i32(self):
        if self.pos + 4 > self.fim:
            raise FormatoInvalido("fim inesperado dos dados na posição %d" % self.pos)
        v = struct.unpack_from("<i", self.d, self.pos)[0]
        self.pos += 4
        return v

    def bloco(self):
        n = self.i32()
        if n < 0 or n > self.fim - self.pos:
            raise FormatoInvalido("tamanho de texto inválido (%d) na posição %d" % (n, self.pos - 4))
        b = bytes(self.d[self.pos:self.pos + n])
        rel = self.pos + n - self.base
        self.pos = self.base + ((rel + 3) & ~3)
        return b

    def texto(self):
        b = self.bloco()
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            if self.tolerante:
                return b.decode("utf-8", errors="replace")
            raise FormatoInvalido("texto não é UTF-8 válido na posição %d" % self.pos)

    def lista(self, ler_item, maximo=MAX_LISTA):
        n = self.i32()
        if n < 0 or n > maximo or n * 4 > self.fim - self.pos:
            raise FormatoInvalido("tamanho de lista inválido (%d) na posição %d" % (n, self.pos - 4))
        return [ler_item() for _ in range(n)]

    def meta_aninhado(self):
        flag = self.i32()  # bool da Unity + 3 bytes de alinhamento
        if (flag & 0xFF) not in (0, 1):
            raise FormatoInvalido("marcador booleano inválido (%d)" % flag)
        return (flag & 0xFF), self.lista(self.i32), self.lista(self.texto)

    def meta_substituicao(self):
        return self.texto(), self.lista(self.i32), self.lista(self.texto)


def inserir_marcadores(texto, posicoes, marcadores):
    """Igual ao string.Insert do .NET: posições em unidades UTF-16."""
    if len(posicoes) != len(marcadores):
        raise FormatoInvalido("metadados com tamanhos diferentes")
    dados = texto.encode("utf-16-le", errors="surrogatepass")
    deslocamento = 0
    for pos, marcador in zip(posicoes, marcadores):
        em = pos * 2 + deslocamento
        if not 0 <= em <= len(dados):
            raise FormatoInvalido("posição de marcador fora do texto")
        cod = marcador.encode("utf-16-le", errors="surrogatepass")
        dados = dados[:em] + cod + dados[em:]
        deslocamento += len(cod)
    return dados.decode("utf-16-le", errors="surrogatepass")


def achar_posicao_nome(dados, fim_busca=256):
    """Procura, no começo do objeto, uma string com prefixo de tamanho que comece com 'lng_'."""
    limite = min(len(dados) - 8, fim_busca)
    posicoes = []
    for p in range(0, max(limite, 0), 4):
        n = struct.unpack_from("<i", dados, p)[0]
        if 5 <= n <= 32 and bytes(dados[p + 4:p + 8]) == b"lng_" and p + 4 + n <= len(dados):
            if re.fullmatch(rb"lng_[A-Za-z0-9_\-]+", bytes(dados[p + 4:p + 4 + n])):
                posicoes.append(p)
    # a posição padrão (28) primeiro
    posicoes.sort(key=lambda x: (x != CABECALHO_MONOBEHAVIOUR, x))
    return posicoes


def decodificar_layout_codec(dados, pos_nome, fim=None):
    """Layout descrito no locale_codec.py do GK2Thai e no LLBase.cs."""
    r = Leitor(dados, pos_nome, fim)
    nome = r.texto()
    aliases1 = r.lista(r.texto)
    aliases2 = r.lista(r.texto)
    idioma = r.texto()
    chaves = r.lista(r.texto)
    textos = r.lista(r.texto)
    avisos = []
    if len(chaves) != len(textos):
        raise FormatoInvalido("quantidade de chaves (%d) diferente da de textos (%d)" % (len(chaves), len(textos)))
    if nome.lower() != ("lng_" + idioma).lower():
        avisos.append("nome do objeto (%s) não bate com o id do idioma (%s)" % (nome, idioma))
    if len(aliases1) != len(aliases2):
        avisos.append("listas de apelidos com tamanhos diferentes")
    aninhados, substituicoes = [], []
    try:
        aninhados = r.lista(r.meta_aninhado)
        substituicoes = r.lista(r.meta_substituicao)
    except FormatoInvalido as e:
        avisos.append("metadados de marcadores #()/@() não lidos (%s); textos exportados sem esses marcadores" % e)
        aninhados, substituicoes = [], []
    if fim is not None and r.pos != r.fim:
        avisos.append("sobraram %d bytes no fim do objeto (o formato pode ter campos novos)" % (r.fim - r.pos))
    if aninhados and len(aninhados) != len(chaves):
        avisos.append("metadados aninhados (%d) não batem com as chaves (%d); ignorados" % (len(aninhados), len(chaves)))
        aninhados = []

    mapa_subst = {}
    for chave, posicoes, valores in substituicoes:
        mapa_subst.setdefault(chave, (posicoes, valores))
    linhas, falhas_marcador = [], 0
    for i, (chave, texto) in enumerate(zip(chaves, textos)):
        try:
            if aninhados:
                flag, posicoes, valores = aninhados[i]
                if flag:
                    texto = inserir_marcadores(texto, posicoes, ["#(" + v + ")" for v in valores])
            if chave in mapa_subst:
                posicoes, valores = mapa_subst[chave]
                texto = inserir_marcadores(texto, posicoes, ["@(" + v + ")" for v in valores])
        except FormatoInvalido:
            falhas_marcador += 1
            texto = textos[i]
        linhas.append((chave, texto))
    if falhas_marcador:
        avisos.append("%d textos ficaram sem os marcadores #()/@() por posição inválida" % falhas_marcador)
    return {"nome": nome, "idioma": idioma, "linhas": linhas, "avisos": avisos,
            "metodo": "layout LL (codec GK2Thai)", "fim": r.pos}


def _parece_chave(s):
    return 0 < len(s) <= 160 and "\n" not in s and re.fullmatch(r"[A-Za-z0-9_\-\.:/ \[\]#@()]+", s) is not None


def decodificar_heuristica(dados, inicio, fim):
    """Plano B: procura duas listas de strings seguidas, com o mesmo tamanho,
    em que a primeira parece uma lista de chaves."""
    fim = min(len(dados), fim)
    melhor = None
    p = inicio
    t0 = time.time()
    while p + 8 <= fim and time.time() - t0 < 60:
        n = struct.unpack_from("<i", dados, p)[0]
        if 50 <= n <= MAX_LISTA:
            primeiro = struct.unpack_from("<i", dados, p + 4)[0]
            if 1 <= primeiro <= 160:
                r = Leitor(dados, p, fim, base=p, tolerante=True)
                try:
                    chaves = r.lista(r.texto)
                    meio = r.pos
                    textos = r.lista(r.texto)
                except FormatoInvalido:
                    p += 4
                    continue
                if len(chaves) == len(textos):
                    amostra = chaves[:500]
                    taxa = sum(1 for k in amostra if _parece_chave(k)) / float(len(amostra) or 1)
                    if taxa >= 0.9 and (melhor is None or len(chaves) > len(melhor[0])):
                        melhor = (chaves, textos)
                    p = r.pos
                    continue
                p = meio
                continue
        p += 4
    if not melhor:
        raise FormatoInvalido("nenhum par de listas chave/texto encontrado")
    return {"nome": None, "idioma": None, "linhas": list(zip(*melhor)),
            "avisos": ["formato diferente do esperado; usei a busca heurística (sem marcadores #()/@())"],
            "metodo": "heurística (listas paralelas)"}


def decodificar_texto_plano(bruto):
    """Caso o idioma esteja num TextAsset (CSV/JSON/TSV, talvez gzip)."""
    if bruto[:2] == b"\x1f\x8b":
        bruto = gzip.decompress(bruto)
    elif bruto[:1] == b"\x78":
        try:
            bruto = zlib.decompress(bruto)
        except zlib.error:
            pass
    if bruto[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texto = bruto.decode("utf-16")
    else:
        texto = bruto.decode("utf-8-sig", errors="replace")
    linhas = []
    try:
        obj = json.loads(texto)
        if isinstance(obj, dict) and isinstance(obj.get("data"), list):
            obj = obj["data"]
        if isinstance(obj, dict):
            linhas = [(str(k), v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)) for k, v in obj.items()]
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    k = item.get("key", item.get("id"))
                    v = item.get("value", item.get("text"))
                    if k is not None and v is not None:
                        linhas.append((str(k), str(v)))
    except ValueError:
        amostra = texto[:20000]
        delim = max([",", ";", "\t"], key=amostra.count)
        leitor = csv.reader(io.StringIO(texto), delimiter=delim)
        for row in leitor:
            if len(row) >= 2:
                linhas.append((row[0], row[1]))
        if linhas and linhas[0][0].strip().lower() in ("key", "id", "chave"):
            linhas = linhas[1:]
        if not linhas:
            for linha in texto.splitlines():
                if "=" in linha:
                    k, v = linha.split("=", 1)
                    linhas.append((k.strip(), v.replace("\\n", "\n")))
    if not linhas:
        raise FormatoInvalido("texto do TextAsset não parece CSV/JSON de chaves")
    return {"nome": None, "idioma": None, "linhas": linhas, "avisos": [], "metodo": "TextAsset (texto puro)"}


def decodificar_objeto(dados, tipo="MonoBehaviour", fim_conhecido=True, heuristica=False):
    """Tenta, em ordem: layout do codec, TextAsset e (se permitido) heurística."""
    erros = []
    fim = len(dados) if fim_conhecido else None
    for pos in achar_posicao_nome(dados) or [CABECALHO_MONOBEHAVIOUR]:
        try:
            return decodificar_layout_codec(dados, pos, fim)
        except FormatoInvalido as e:
            erros.append("layout LL na posição %d: %s" % (pos, e))
        # TextAsset: m_Name seguido do conteúdo (bytes)
        try:
            r = Leitor(dados, pos, fim)
            r.texto()
            return decodificar_texto_plano(r.bloco())
        except (FormatoInvalido, ValueError, OSError, UnicodeDecodeError) as e:
            erros.append("TextAsset na posição %d: %s" % (pos, e))
    if not heuristica:
        raise FormatoInvalido("; ".join(erros))
    inicio = (achar_posicao_nome(dados) or [0])[0]
    try:
        return decodificar_heuristica(dados, inicio, inicio + JANELA_VARREDURA if not fim_conhecido else len(dados))
    except FormatoInvalido as e:
        erros.append("heurística: %s" % e)
    raise FormatoInvalido("; ".join(erros))


def avaliar(resultado):
    """Devolve (ok, motivo): o resultado parece mesmo uma tabela chave/texto?"""
    linhas = resultado["linhas"]
    if len(linhas) < 200:
        return False, "só %d textos (esperava milhares)" % len(linhas)
    chaves = [k for k, _ in linhas]
    if len(set(chaves)) < 0.95 * len(chaves):
        return False, "muitas chaves repetidas"
    amostra = chaves[:2000]
    if sum(1 for k in amostra if _parece_chave(k)) < 0.8 * len(amostra):
        return False, "as chaves não parecem chaves de tradução"
    if sum(1 for _, t in linhas if t.strip()) < 0.5 * len(linhas):
        return False, "a maioria dos textos está vazia"
    return True, ""


# ---------------------------------------------------------------------------
# Varredura dos arquivos do jogo
# ---------------------------------------------------------------------------

def idioma_do_nome(nome):
    n = nome.lower()
    if n.startswith("lng_"):
        n = n[4:]
    n = n.replace("_", "-")
    if n in ("pt-br", "ptbr", "pt"):
        return "pt-br"
    if n in ("en", "en-us", "english"):
        return "en"
    return n


def arquivos_para_varrer(pasta_dados):
    principais = [pasta_dados / "resources.assets"]
    extras = []
    try:
        extras += sorted(pasta_dados.glob("sharedassets*.assets"))
        extras += sorted(pasta_dados.glob("level*"))
        extras += [p for p in (pasta_dados / "globalgamemanagers.assets",) if _existe(p)]
        extras += sorted((pasta_dados / "StreamingAssets").rglob("*.bundle"))
    except OSError:
        pass
    extras = [p for p in extras if p.is_file() and not p.name.lower().endswith((".ress", ".resource"))]
    return [p for p in principais if _existe(p)], extras


class Candidato:
    def __init__(self, nome, tipo, arquivo, metodo_leitura, dados=None, pos_nome=None, fim_conhecido=True):
        self.nome, self.tipo, self.arquivo = nome, tipo, arquivo
        self.metodo_leitura = metodo_leitura
        self.dados, self.pos_nome, self.fim_conhecido = dados, pos_nome, fim_conhecido
        self.idioma = idioma_do_nome(nome)
        self.resultado = None
        self.erro = None


def _nome_do_objeto(obj):
    try:
        nome = obj.peek_name()
        if nome:
            return nome
    except Exception:
        pass
    try:
        bruto = obj.get_raw_data()
        pos = achar_posicao_nome(bruto, 64)
        if pos:
            n = struct.unpack_from("<i", bruto, pos[0])[0]
            return bytes(bruto[pos[0] + 4:pos[0] + 4 + n]).decode("utf-8", "replace")
    except Exception:
        pass
    try:
        return obj.read_typetree(check_read=False).get("m_Name")
    except Exception:
        return None


def varrer_unitypy(arquivo, alvo):
    import UnityPy
    encontrados = []
    env = UnityPy.load(str(arquivo))
    total = 0
    for obj in env.objects:
        total += 1
        tipo = getattr(obj.type, "name", str(obj.type))
        if tipo not in ("MonoBehaviour", "TextAsset"):
            continue
        nome = _nome_do_objeto(obj)
        if not nome or not str(nome).lower().startswith("lng_"):
            continue
        c = Candidato(str(nome), tipo, arquivo, "UnityPy", dados=obj.get_raw_data())
        detalhe("UnityPy: %s (%s, %d bytes, path_id %s)" % (nome, tipo, len(c.dados), getattr(obj, "path_id", "?")))
        encontrados.append(c)
    detalhe("UnityPy: %d objetos em %s" % (total, arquivo.name))
    return encontrados


def varrer_bytes(arquivo, mapas_abertos):
    """Leitor embutido: procura o nome 'lng_...' com prefixo de tamanho direto nos bytes
    do arquivo (funciona em .assets sem compressão, como o resources.assets)."""
    encontrados = []
    tamanho = arquivo.stat().st_size
    if tamanho < 64:
        return encontrados
    f = open(str(arquivo), "rb")  # somente leitura
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    mapas_abertos.append((mm, f))
    pos = 0
    while True:
        i = mm.find(b"lng_", pos)
        if i < 0:
            break
        pos = i + 1
        if i < 4:
            continue
        n = struct.unpack_from("<i", mm, i - 4)[0]
        if not 5 <= n <= 32:
            continue
        nome_b = mm[i:i + n]
        if not re.fullmatch(rb"lng_[A-Za-z0-9_\-]+", nome_b):
            continue
        nome = nome_b.decode("ascii")
        detalhe("varredura: '%s' na posição %d de %s" % (nome, i - 4, arquivo.name))
        encontrados.append(Candidato(nome, "MonoBehaviour?", arquivo, "leitor embutido",
                                     dados=mm, pos_nome=i - 4, fim_conhecido=False))
    return encontrados


def decodificar_candidato(c, heuristica=False):
    """heuristica=False: só o layout conhecido. heuristica=True: só o plano B."""
    c.erro, c.resultado = None, None
    try:
        if c.pos_nome is None:
            if heuristica:
                inicio = (achar_posicao_nome(c.dados) or [0])[0]
                c.resultado = decodificar_heuristica(c.dados, inicio, len(c.dados))
            else:
                c.resultado = decodificar_objeto(c.dados, c.tipo, fim_conhecido=True)
        elif heuristica:
            c.resultado = decodificar_heuristica(c.dados, c.pos_nome, c.pos_nome + JANELA_VARREDURA)
        else:
            c.resultado = decodificar_layout_codec(c.dados, c.pos_nome, None)
        ok, motivo = avaliar(c.resultado)
        if not ok:
            c.erro = "o resultado não parece uma tabela de textos: " + motivo
    except FormatoInvalido as e:
        c.erro = str(e)
    except Exception as e:  # nunca derrubar o programa por um candidato
        c.erro = "erro inesperado: %r" % (e,)
        detalhe(traceback.format_exc())
    return c


def bytes_para_dump(c):
    if c.pos_nome is None:
        return bytes(c.dados)
    ini = max(0, c.pos_nome - CABECALHO_MONOBEHAVIOUR)
    return bytes(c.dados[ini:min(len(c.dados), ini + MAX_DUMP)])


# ---------------------------------------------------------------------------
# Gravação
# ---------------------------------------------------------------------------

def gravar_csv(caminho, linhas):
    with open(str(caminho), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "text"])
        for k, t in linhas:
            w.writerow([k, t])


def gravar_json(caminho, en, pt):
    d_en = dict(en) if en else {}
    d_pt = dict(pt) if pt else {}
    ordem = list(d_en.keys()) + [k for k in d_pt.keys() if k not in d_en]
    saida = {}
    for k in ordem:
        saida[k] = {"en": d_en.get(k), "pt": d_pt.get(k)}
    with open(str(caminho), "w", encoding="utf-8", newline="\n") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
        f.write("\n")


def pasta_saida_padrao():
    aqui = Path(__file__).resolve().parent
    try:
        teste = aqui / ".teste_escrita.tmp"
        teste.write_text("ok")
        teste.unlink()
        return aqui
    except OSError:
        alt = Path.home() / "Desktop" / "GK2_textos"
        if not _existe(alt.parent):
            alt = Path.home() / "GK2_textos"
        alt.mkdir(parents=True, exist_ok=True)
        return alt


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def principal():
    ap = argparse.ArgumentParser(description="Exporta os textos pt-BR e EN do Graveyard Keeper 2 (somente leitura).")
    ap.add_argument("caminho", nargs="?", help="pasta do jogo, pasta *_Data ou resources.assets")
    ap.add_argument("--sem-unitypy", action="store_true", help="não usar o UnityPy; só o leitor embutido")
    ap.add_argument("--saida", help="pasta onde gravar os arquivos (padrão: ao lado deste script)")
    args = ap.parse_args()

    log("=" * 70)
    log(" Exportador de textos do Graveyard Keeper 2  -  versão %s" % VERSAO)
    log(" Este programa SÓ LÊ os arquivos do jogo. Nada no jogo é alterado.")
    log("=" * 70)
    detalhe("Python %s em %s" % (sys.version.split()[0], platform.platform()))
    detalhe("data/hora: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))

    saida = Path(args.saida) if args.saida else pasta_saida_padrao()
    saida.mkdir(parents=True, exist_ok=True)
    _ESTADO["saida"] = saida
    detalhe("pasta de saída: %s" % saida)

    # UnityPy é opcional: sem ele usamos o leitor embutido.
    unitypy_ok = False
    if not args.sem_unitypy:
        try:
            import UnityPy  # noqa: F401
            unitypy_ok = True
            detalhe("UnityPy %s" % getattr(UnityPy, "__version__", "?"))
        except Exception as e:
            log("")
            log("AVISO: a biblioteca UnityPy não está instalada (%s)." % type(e).__name__)
            log("  Para instalar, abra o Prompt de Comando e digite:")
            log("      py -m pip install UnityPy")
            log("  (ou:  pip install UnityPy )")
            log("  Vou continuar com o leitor embutido, que costuma funcionar também.")

    pasta_dados, manifesto = localizar_jogo(args.caminho)
    if not pasta_dados:
        log("")
        log("ERRO: não encontrei a pasta do jogo.")
        log("  Rode de novo informando o caminho, por exemplo:")
        log('      py -3 exportar_textos.py "D:\\SteamLibrary\\steamapps\\common\\Graveyard Keeper 2"')
        log("  Dica: na Steam, botão direito no jogo > Gerenciar > Procurar arquivos locais.")
        return 2, saida
    log("")
    log("Jogo encontrado: %s" % pasta_dados.parent)
    log("Pasta de dados:  %s" % pasta_dados)
    if "demo" in pasta_dados.name.lower():
        log("ATENÇÃO: esta parece ser a versão DEMO. O ideal é a versão completa do jogo.")
    if manifesto:
        detalhe("manifesto Steam: %s" % json.dumps(manifesto, ensure_ascii=False))
        if manifesto.get("buildid"):
            log("Build da Steam:  %s" % manifesto["buildid"])
    try:
        with open(str(pasta_dados / "resources.assets"), "rb") as f:
            cab = f.read(256)
        m = re.search(rb"(20\d\d|6\d{3})\.\d+\.\d+[abfpx]\d+", cab)
        if m:
            log("Versão da Unity: %s" % m.group(0).decode("ascii"))
    except OSError:
        pass

    principais, extras = arquivos_para_varrer(pasta_dados)
    candidatos, mapas = [], []
    escolhidos = {}

    def processar(lista_arquivos):
        for arq in lista_arquivos:
            try:
                tam = arq.stat().st_size
            except OSError:
                continue
            log("")
            log("Lendo %s (%s)... isso pode levar alguns minutos." % (arq.name, tamanho_legivel(tam)))
            achados = []
            if unitypy_ok:
                t0 = time.time()
                try:
                    achados = varrer_unitypy(arq, IDIOMAS_ALVO)
                    detalhe("UnityPy levou %.1f s" % (time.time() - t0))
                except MemoryError:
                    log("  O UnityPy ficou sem memória; usando o leitor embutido.")
                except Exception as e:
                    log("  O UnityPy não conseguiu abrir este arquivo (%s); usando o leitor embutido." % type(e).__name__)
                    detalhe(traceback.format_exc())
            if not achados and not arq.name.lower().endswith(".bundle"):
                try:
                    achados = varrer_bytes(arq, mapas)
                except (OSError, ValueError) as e:
                    log("  Não consegui ler o arquivo: %s" % e)
            nomes = sorted(set(c.nome for c in achados))
            if nomes:
                log("  Idiomas encontrados: %s" % ", ".join(nomes))
            for idioma in IDIOMAS_ALVO:
                if idioma in escolhidos:
                    continue
                deste = [c for c in achados if c.idioma == idioma]
                # 1a passada: layout conhecido em todos; 2a: plano B (heurística)
                for heuristica in (False, True):
                    for c in deste:
                        decodificar_candidato(c, heuristica)
                        if c.erro is None:
                            escolhidos[idioma] = c
                            n = len(c.resultado["linhas"])
                            log("  OK: %s -> %d textos (%s via %s)" % (c.nome, n, c.resultado["metodo"], c.metodo_leitura))
                            for a in c.resultado["avisos"]:
                                log("     aviso: " + a)
                            break
                        detalhe("falhou %s em %s (%s): %s" % (c.nome, arq.name,
                                "heurística" if heuristica else "layout LL", c.erro))
                    if idioma in escolhidos:
                        break
                candidatos.extend(deste)
            if all(i in escolhidos for i in IDIOMAS_ALVO):
                return

    processar(principais)
    if not all(i in escolhidos for i in IDIOMAS_ALVO) and extras:
        log("")
        log("Ainda faltam idiomas; procurando em outros %d arquivos do jogo..." % len(extras))
        if not unitypy_ok and any(p.name.lower().endswith(".bundle") for p in extras):
            log("  (arquivos .bundle exigem o UnityPy: py -m pip install UnityPy)")
        processar(extras)

    # ---- gravação ----
    log("")
    en = escolhidos.get("en")
    pt = escolhidos.get("pt-br")
    gravados = []
    try:
        if pt:
            gravar_csv(saida / "gk2_textos_pt-br.csv", pt.resultado["linhas"])
            gravados.append("gk2_textos_pt-br.csv")
        if en:
            gravar_csv(saida / "gk2_textos_en.csv", en.resultado["linhas"])
            gravados.append("gk2_textos_en.csv")
        if pt or en:
            gravar_json(saida / "gk2_textos.json",
                        en.resultado["linhas"] if en else None,
                        pt.resultado["linhas"] if pt else None)
            gravados.append("gk2_textos.json")
    except PermissionError:
        log("ERRO: não consegui gravar os arquivos em %s." % saida)
        log("  Se algum CSV estiver aberto no Excel, feche-o e rode de novo.")
        return 2, saida

    # despejo bruto do que falhou, para análise remota
    for idioma in IDIOMAS_ALVO:
        if idioma in escolhidos:
            continue
        falhos = [c for c in candidatos if c.idioma == idioma and c.erro]
        for n, c in enumerate(falhos[:3]):
            destino = saida / ("_raw_lng_%s%s.bin" % (idioma, "" if n == 0 else "_%d" % (n + 1)))
            try:
                with open(str(destino), "wb") as f:
                    f.write(bytes_para_dump(c))
                log("Não consegui decodificar '%s' em %s (%s)." % (c.nome, c.arquivo.name, c.erro))
                log("  Salvei os bytes brutos em %s para analisarmos." % destino.name)
                gravados.append(destino.name)
            except OSError as e:
                log("  Também não consegui salvar os bytes brutos: %s" % e)

    # verificação de alinhamento pt x en
    if pt and en:
        k_en = set(k for k, _ in en.resultado["linhas"])
        k_pt = set(k for k, _ in pt.resultado["linhas"])
        comuns = len(k_en & k_pt)
        d_en = dict(en.resultado["linhas"])
        iguais = sum(1 for k, t in pt.resultado["linhas"] if k in d_en and t == d_en[k] and t.strip())
        log("Conferência: %d chaves em inglês, %d em português, %d em comum." % (len(k_en), len(k_pt), comuns))
        if comuns < 0.8 * max(len(k_en), 1):
            log("  AVISO: poucas chaves em comum entre os idiomas. Mande o log junto.")
        if iguais > 0.7 * max(len(k_pt), 1):
            log("  AVISO: a maioria dos textos em português é igual ao inglês. Mande o log junto.")

    for m, f in mapas:
        try:
            m.close()
            f.close()
        except Exception:
            pass

    log("")
    log("=" * 70)
    if pt:
        log(" PRONTO! Arquivos gravados em:")
        log("   %s" % saida)
        for g in gravados:
            log("     - %s" % g)
        log("")
        log(" Envie para nós o arquivo  gk2_textos.json")
        log(" (se quiser, mande também gk2_exportacao_log.txt).")
        codigo = 0
    else:
        log(" NÃO consegui exportar os textos em português.")
        if gravados:
            log(" Arquivos gravados em %s:" % saida)
            for g in gravados:
                log("     - %s" % g)
        log(" Envie para nós o arquivo  gk2_exportacao_log.txt")
        log(" e, se existir, o arquivo  _raw_lng_pt-br.bin")
        codigo = 1 if gravados else 2
    log("=" * 70)
    return codigo, saida


def main():
    codigo, saida = 2, None
    try:
        codigo, saida = principal()
    except KeyboardInterrupt:
        log("\nCancelado pelo usuário.")
    except Exception:
        log("")
        log("ERRO INESPERADO. Por favor, envie o arquivo gk2_exportacao_log.txt para nós.")
        log(traceback.format_exc(), tela=False)
        print(traceback.format_exc().splitlines()[-1])
    finally:
        try:
            destino = (saida or _ESTADO["saida"] or pasta_saida_padrao()) / "gk2_exportacao_log.txt"
            with open(str(destino), "w", encoding="utf-8-sig") as f:
                f.write("\n".join(_LOG) + "\n")
        except Exception:
            pass
    if os.name == "nt" and not os.environ.get("GK2_EXPORT_BAT") and sys.stdin and sys.stdin.isatty():
        try:
            input("\nPressione Enter para fechar...")
        except Exception:
            pass
    sys.exit(codigo)


if __name__ == "__main__":
    main()
