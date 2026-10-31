"""
exportar_textos_unitypy.py — Exporta os textos de localização do Graveyard Keeper 2.

Variante enxuta e estrita (exige UnityPy) que gerou de fato data/game-texts/gk2_textos.json
no PC com o jogo (versão 1.011, 30/10/2026; ver data/game-texts/RELATORIO-exportacao.md).
Comparada ao exportar_textos.py (amigável, com .bat, leitor embutido e plano B), esta também
grava os 11 idiomas, a versão do jogo (bundleVersion) e o _resumo.json. Grava ao lado de si
mesma: copie-a para a pasta de trabalho no Windows (ex.: Documents\\GK2-textos) antes de rodar.

Uso (dentro da pasta GK2-textos):
    .venv\\Scripts\\python.exe -I exportar_textos_unitypy.py              # acha o jogo pela Steam
    .venv\\Scripts\\python.exe -I exportar_textos_unitypy.py "E:\\...\\Graveyard Keeper 2"

Requisitos: Python 3.10+ e UnityPy (pip install UnityPy).

SOMENTE LEITURA: os .assets do jogo são lidos para a memória com open(..., "rb")
e nada é gravado na pasta do jogo. Todas as saídas vão para a pasta deste script.

Saídas:
    gk2_textos.json           { chave: { "en": ..., "pt": ... } }  (todas as chaves)
    gk2_textos_en.csv         key,text  (UTF-8 com BOM)
    gk2_textos_pt-br.csv      key,text  (UTF-8 com BOM)
    gk2_textos_todos.json     { idioma: { chave: texto } } com os 11 idiomas
    _resumo.json              metadados usados pelo RELATORIO.md
    _raw_lng_pt-br.bin        bytes brutos (só se a decodificação falhar)

Formato do MonoBehaviour lng_<idioma> (Unity 6000.3, sem typetree no arquivo):
    28 bytes de cabeçalho Unity (m_GameObject PPtr, m_Enabled, m_Script PPtr)
    string  m_Name                    "lng_pt-br"
    string[] alias_a, string[] alias_b   (pares paralelos)
    string  language                  "pt-br"
    string[] keys, string[] texts     (paralelos)
    nested[] : { int flag; int[] positions; string[] values }   -> tokens #(valor)
    repl[]   : { string key; int[] positions; string[] values } -> tokens @(valor)
  Strings: int32 de tamanho + bytes UTF-8, alinhado a 4 bytes.
  Os textos guardados vêm SEM os tokens #(...) e @(...); o jogo os insere
  em tempo de execução nas posições indicadas (em unidades UTF-16). Este
  script reinsere os tokens para reproduzir o texto-fonte completo.
"""
import csv
import glob
import json
import os
import re
import struct
import sys

import UnityPy

APP_ID = "4358690"
IDIOMAS = ["en", "de", "fr", "pt-br", "es", "ru", "pl", "ja", "zh_cn", "ko", "tr"]
SAIDA = os.path.dirname(os.path.abspath(__file__))
HEADER = 28  # cabeçalho padrão de MonoBehaviour neste build


# ---------------------------------------------------------------- localizar jogo
def achar_pasta_jogo():
    """Procura o appmanifest_4358690.acf em todas as bibliotecas Steam."""
    raizes = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            raizes.append(winreg.QueryValueEx(k, "SteamPath")[0])
    except OSError:
        pass
    raizes.append(r"C:\Program Files (x86)\Steam")
    libs = []
    for r in raizes:
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            with open(vdf, encoding="utf-8") as f:
                libs += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
        libs.append(r)
    for lib in dict.fromkeys(libs):
        acf = os.path.join(lib, "steamapps", f"appmanifest_{APP_ID}.acf")
        if os.path.isfile(acf):
            with open(acf, encoding="utf-8") as f:
                txt = f.read()
            installdir = re.search(r'"installdir"\s+"([^"]+)"', txt).group(1)
            return os.path.join(lib, "steamapps", "common", installdir), acf
    sys.exit("Graveyard Keeper 2 não encontrado; passe a pasta do jogo como argumento.")


def versao_jogo(dados):
    """bundleVersion do PlayerSettings (globalgamemanagers), ex.: '1.011'."""
    try:
        with open(os.path.join(dados, "globalgamemanagers"), "rb") as fh:
            env = UnityPy.load(fh.read())
        ps = next(o for o in env.objects if o.type.name == "PlayerSettings")
        return ps.read_typetree(check_read=False).get("bundleVersion")
    except Exception as e:
        return f"? ({e})"


def ler_manifesto(acf):
    if not acf or not os.path.isfile(acf):
        return {}
    with open(acf, encoding="utf-8") as f:
        txt = f.read()
    return {k: (re.search(rf'"{k}"\s+"([^"]*)"', txt) or [None, None])[1]
            for k in ("buildid", "LastUpdated", "SizeOnDisk")}


# ---------------------------------------------------------------- leitor binário
class Leitor:
    def __init__(self, b, pos=0):
        self.b, self.p = b, pos

    def i32(self):
        if self.p + 4 > len(self.b):
            raise ValueError(f"fim inesperado em {self.p}")
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def count(self):
        n = self.i32()
        if not 0 <= n <= 100_000:
            raise ValueError(f"contagem inválida {n} em {self.p - 4}")
        return n

    def string(self):
        n = self.i32()
        if n < 0 or self.p + n > len(self.b):
            raise ValueError(f"string inválida (len={n}) em {self.p - 4}")
        s = self.b[self.p:self.p + n].decode("utf-8")  # strict: falha se não for UTF-8
        self.p += (n + 3) & ~3  # alinhamento de 4 bytes
        return s

    def strings(self):
        return [self.string() for _ in range(self.count())]

    def ints(self):
        return [self.i32() for _ in range(self.count())]


def inserir_tokens(texto, posicoes, valores, prefixo):
    """Insere prefixo(valor) nas posições (unidades UTF-16 do texto original)."""
    u = texto.encode("utf-16-le")
    desloc = 0
    for pos, val in sorted(zip(posicoes, valores), key=lambda t: t[0]):
        tok = f"{prefixo}({val})".encode("utf-16-le")
        at = pos * 2 + desloc
        u = u[:at] + tok + u[at:]
        desloc += len(tok)
    return u.decode("utf-16-le")


def decodificar(raw, esperado):
    r = Leitor(raw, HEADER)
    nome = r.string()
    if nome != esperado:
        raise ValueError(f"nome {nome!r} != {esperado!r}")
    alias_a, alias_b = r.strings(), r.strings()
    if len(alias_a) != len(alias_b):
        raise ValueError("arrays de alias com tamanhos diferentes")
    lang = r.string()
    keys, texts = r.strings(), r.strings()
    if len(keys) != len(texts):
        raise ValueError("keys e texts com tamanhos diferentes")
    nested = []
    for _ in range(r.count()):
        flag = r.i32()
        nested.append((flag, r.ints(), r.strings()))
    repl = []
    for _ in range(r.count()):
        k = r.string()
        repl.append((k, r.ints(), r.strings()))
    if r.p != len(raw):
        raise ValueError(f"sobraram {len(raw) - r.p} bytes não reconhecidos")
    if len(nested) != len(keys):
        raise ValueError(f"nested ({len(nested)}) != keys ({len(keys)})")

    # monta textos completos com #(...) e @(...)
    idx = {k: i for i, k in enumerate(keys)}
    if len(idx) != len(keys):
        raise ValueError("chaves duplicadas")
    finais = list(texts)
    n_tok_nested = 0
    for i, (flag, pos, vals) in enumerate(nested):
        if pos:
            finais[i] = inserir_tokens(finais[i], pos, vals, "#")
            n_tok_nested += len(pos)
    # @() são inseridos sobre o texto original (posições relativas a ele); como
    # na prática uma mesma chave raramente tem os dois tipos, aplicamos em ordem
    # e registramos quantas chaves têm ambos para conferência.
    ambos = 0
    for k, pos, vals in repl:
        i = idx[k]
        if nested[i][1]:
            ambos += 1
        finais[i] = inserir_tokens(finais[i], pos, vals, "@") if not nested[i][1] else \
            _inserir_misto(texts[i], nested[i][1], nested[i][2], pos, vals)
    return {
        "nome": nome, "lang": lang, "aliases": list(zip(alias_a, alias_b)),
        "textos": dict(zip(keys, finais)), "texto_sem_tokens": dict(zip(keys, texts)),
        "n_nested_tokens": n_tok_nested, "n_repl": len(repl), "n_ambos": ambos,
    }


def _inserir_misto(texto, p1, v1, p2, v2):
    """Chave com #() e @(): insere tudo junto, por posição no texto original."""
    u = texto.encode("utf-16-le")
    itens = [(p, f"#({v})") for p, v in zip(p1, v1)] + [(p, f"@({v})") for p, v in zip(p2, v2)]
    desloc = 0
    for pos, tok in sorted(itens, key=lambda t: t[0]):
        t = tok.encode("utf-16-le")
        at = pos * 2 + desloc
        u = u[:at] + t + u[at:]
        desloc += len(t)
    return u.decode("utf-16-le")


# ---------------------------------------------------------------- principal
def main():
    if len(sys.argv) > 1:
        jogo, acf = sys.argv[1], None
        lib = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(jogo))))
        cand = os.path.join(lib, "steamapps", f"appmanifest_{APP_ID}.acf")
        acf = cand if os.path.isfile(cand) else None
    else:
        jogo, acf = achar_pasta_jogo()
    dados = next(iter(glob.glob(os.path.join(jogo, "*_Data"))), None)
    if not dados:
        sys.exit(f"pasta *_Data não encontrada em {jogo}")
    print("Pasta do jogo:", jogo)

    # varre todos os .assets procurando MonoBehaviours lng_*
    achados = {}  # nome -> (arquivo, path_id, raw)
    for arq in sorted(glob.glob(os.path.join(dados, "*.assets"))):
        with open(arq, "rb") as fh:          # somente leitura
            env = UnityPy.load(fh.read())    # carregado da memória, não do disco
        versao_unity = getattr(env.file, "version", "?")
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                nome = obj.peek_name()
            except Exception:
                continue
            if nome and nome.startswith("lng_"):
                if nome in achados:
                    print(f"  aviso: {nome} duplicado em {arq} (mantendo o primeiro)")
                    continue
                achados[nome] = (arq, obj.path_id, obj.get_raw_data())
                print(f"  {nome:10s} {os.path.basename(arq)} path_id={obj.path_id} {len(achados[nome][2])} bytes")

    resultado, resumo = {}, {"jogo": jogo, "dados": dados, "unity": str(versao_unity),
                             "versao_jogo": versao_jogo(dados),
                             "manifesto": ler_manifesto(acf), "assets": {}, "erros": {}}
    for nome, (arq, pid, raw) in achados.items():
        try:
            d = decodificar(raw, nome)
            resultado[d["lang"]] = d
            resumo["assets"][nome] = {"arquivo": arq, "path_id": pid, "bytes": len(raw),
                                      "lang": d["lang"], "chaves": len(d["textos"]),
                                      "aliases": len(d["aliases"]),
                                      "tokens_hash": d["n_nested_tokens"],
                                      "chaves_com_arroba": d["n_repl"],
                                      "chaves_com_ambos": d["n_ambos"]}
        except Exception as e:
            resumo["erros"][nome] = str(e)
            print(f"  ERRO ao decodificar {nome}: {e}")
            if nome == "lng_pt-br":
                with open(os.path.join(SAIDA, "_raw_lng_pt-br.bin"), "wb") as f:
                    f.write(raw)

    for lang in IDIOMAS:
        if lang not in resultado:
            print(f"  aviso: idioma {lang} não encontrado")

    en = resultado.get("en", {}).get("textos", {})
    pt = resultado.get("pt-br", {}).get("textos", {})
    so_en, so_pt = sorted(set(en) - set(pt)), sorted(set(pt) - set(en))
    resumo["so_en"], resumo["so_pt"] = so_en, so_pt
    resumo["aliases_en"] = resultado.get("en", {}).get("aliases", [])

    # gk2_textos.json — ordem das chaves do lng_en, depois as que só existem em pt
    ordem = list(en) + [k for k in pt if k not in en]
    combinado = {k: {"en": en.get(k), "pt": pt.get(k)} for k in ordem}
    with open(os.path.join(SAIDA, "gk2_textos.json"), "w", encoding="utf-8") as f:
        json.dump(combinado, f, ensure_ascii=False, indent=1)

    for lang, arqcsv in (("en", "gk2_textos_en.csv"), ("pt-br", "gk2_textos_pt-br.csv")):
        textos = resultado.get(lang, {}).get("textos", {})
        with open(os.path.join(SAIDA, arqcsv), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["key", "text"])
            w.writerows(textos.items())

    with open(os.path.join(SAIDA, "gk2_textos_todos.json"), "w", encoding="utf-8") as f:
        json.dump({l: d["textos"] for l, d in resultado.items()}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(SAIDA, "_resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1)

    print(f"Versão do jogo: {resumo['versao_jogo']} (Steam build {resumo['manifesto'].get('buildid')})")
    print(f"OK: {len(combinado)} chaves (en={len(en)}, pt-br={len(pt)}); "
          f"só en={len(so_en)}, só pt={len(so_pt)}")


if __name__ == "__main__":
    main()
