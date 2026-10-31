# Relatório: exportação dos textos do Graveyard Keeper 2

> Relatório escrito pela sessão no Windows. No repositório: a tabela está em `data/game-texts/gk2_textos.json` (versionada); CSVs, `gk2_textos_todos.json` e `_resumo.json` ficam na mesma pasta, fora do git; o script citado como `exportar_textos.py` é `tools/exportar-textos/exportar_textos_unitypy.py`.

Gerado em 30/10/2026. Toda a leitura foi feita em modo somente leitura, e nada foi gravado na pasta do jogo.
O arquivo mais recente da pasta `_Data` tem data de 30/10/2026 13:53, que é da atualização da Steam (13:54).
O script rodou às 20:17.

## Versão do jogo
| Item | Valor |
|---|---|
| Versão (PlayerSettings.bundleVersion, em `globalgamemanagers`) | **1.011** |
| Steam buildid (`appmanifest_4358690.acf`) | 26297960 (atualizado em 30/10/2026 13:54) |
| Versão do Unity | 6000.3f1 (Unity 6) |
| Pasta do jogo | `E:\SteamLibrary\steamapps\common\Graveyard Keeper 2` (biblioteca `E:\SteamLibrary`, não a padrão) |
| Pasta de dados | `GraveyardKeeper2_Data` (sem espaço, diferente do nome do jogo) |

## Arquivos lidos
- `GraveyardKeeper2_Data\resources.assets`: contém todos os assets `lng_*`.
- `GraveyardKeeper2_Data\globalgamemanagers`: só para ler a versão.
- Também foram varridos `globalgamemanagers.assets` e `sharedassets0.assets`, sem nenhum `lng_*`. Não há AssetBundles em `StreamingAssets`.

## Assets encontrados (todos em `resources.assets`, tipo MonoBehaviour)
| m_Name | path_id | bytes | chaves | pares de alias | chaves com `@()` |
|---|---|---|---|---|---|
| lng_de | 2461 | 1 316 948 | 9 474 | 8 719 | 5 |
| lng_en | 2462 | 1 247 844 | 9 474 | 8 719 | 5 |
| lng_es | 2463 | 1 302 820 | 9 474 | 8 719 | 5 |
| lng_fr | 2464 | 1 367 872 | 9 474 | 8 719 | 5 |
| lng_ja | 2465 | 1 952 788 | 9 474 | 8 719 | 5 |
| lng_ko | 2466 | 1 356 080 | 9 474 | 8 719 | 5 |
| lng_pl | 2467 | 1 283 856 | 9 474 | 8 719 | 5 |
| **lng_pt-br** | 2468 | 1 282 708 | **9 474** | 8 719 | 5 |
| lng_ru | 2469 | 1 561 956 | 9 474 | 8 719 | 5 |
| lng_tr | 2470 | 1 307 208 | 9 474 | 8 719 | 5 |
| lng_zh_cn | 2471 | 1 859 348 | 9 474 | 8 719 | 5 |

Os 11 idiomas esperados estão presentes, e todos decodificaram sem nenhum byte sobrando.

## Validação
- **lng_en e lng_pt-br têm exatamente o mesmo conjunto de 9 474 chaves.** Nenhuma chave existe só em um dos dois.
- **Acentuação:** não há mojibake (`Ã©`, `Ã§`) nem caractere U+FFFD. Contagem no pt-br: ã 2 277, ç 1 265, é 1 330, ê 1 363, á 1 773.
- Uma chave tem texto vazio nos dois idiomas: a chave `" "` (um espaço). Ela vem do próprio jogo.
- 98 chaves têm texto igual em en e pt. São nomes próprios ou termos não traduzidos, como `btn_ok` = "OK", `npc_tavern_owner` = "Linda" e `alchemy_rubedo` = "Rubedo Crystallis".

### Chaves conferidas
| chave | en | pt |
|---|---|---|
| nails_bronze | Bronze Nails | Pregos de Bronze |
| alchemy_flask | Alchemy Flasks | Frascos de alquimia |
| detail_2_iron | Advanced Detail | Detalhe Avançado |
| advanced_rod | Advanced Rod | Vara Avançada |
| bag_alchemy | Alchemist's bag | Bolsa de Alquimista |
| tech_steel_instruments_1 | Steel Instruments I | Instrumentos de Aço I |
| hint_interaction | Interact | Interagir |
| hint_work | Work | Trabalhar |

## Diferenças em relação ao formato descrito
1. **Contagem de chaves:** são 9 474, e não cerca de 9 370. Provavelmente o jogo foi atualizado; a referência tailandesa usava a versão 1.0024, e esta instalação é a 1.011.
2. **Pasta e biblioteca:** a pasta é `GraveyardKeeper2_Data` e fica em `E:\SteamLibrary`.
3. **Estrutura:** a estrutura é a mesma do `locale_codec.py` de referência. A ordem é: cabeçalho de 28 bytes, `m_Name`, dois arrays de alias paralelos (8 719 pares do tipo `garden_empty_1_place` → `garden_empty_1`), `language`, `keys`, `texts`, array "nested" (flag + posições + valores, que gera os tokens `#(...)`) e array de substituições (chave + posições + valores, que gera os tokens `@(...)`). As strings são UTF-8 com prefixo int32, alinhadas a 4 bytes.
4. **Tokens:** os textos guardados no asset vêm sem os tokens, e o jogo os insere em tempo de execução. O script reinsere os tokens para reproduzir o texto-fonte completo.
   - Nesta versão não há nenhum token `#()`.
   - Há `@()` em apenas 5 chaves (`tut_tech_1`, `tut_fishing_bite`, `tut_fishing_bait`, `tut_fishing_game` e `1_intro_prison_sarcophage_1_inventory`). Exemplo: "Aperte @(GameKeyCharacterWindow) para abrir…". O `@(...)` é o nome de uma tecla.
   - Alguns textos também têm tags de TextMeshPro, como `<sprite name="talent_green">`, e foram mantidas como estão.
5. **typetree:** o arquivo não tem typetree embutido, então `read_typetree()` não funciona para esses MonoBehaviours. A leitura é feita pelos bytes brutos (`get_raw_data()`), como faz o codec de referência.
6. **Observação:** a pasta do jogo já tem `BepInEx`, `winhttp.dll`/`doorstop_config.ini` e `README_MODDING.txt`, de antes desta sessão. Nada disso foi usado nem alterado.

## Arquivos gerados
| Arquivo | Conteúdo |
|---|---|
| `gk2_textos.json` | `{ chave: { "en", "pt" } }`, com as 9 474 chaves na ordem do lng_en. UTF-8. |
| `gk2_textos_pt-br.csv`, `gk2_textos_en.csv` | Colunas `key,text`, em UTF-8 com BOM. |
| `gk2_textos_todos.json` | Extra: os 11 idiomas, `{ idioma: { chave: texto } }`. |
| `_resumo.json` | Metadados da execução, incluindo os pares de alias. |
| `exportar_textos.py` | Script final, comentado. |

## Como reexecutar após uma atualização
```
cd %USERPROFILE%\Documents\GK2-textos
.venv\Scripts\python.exe -I exportar_textos.py
```
O script acha o jogo sozinho pelas bibliotecas da Steam. Para usar outra pasta, passe o caminho do jogo como argumento.
Se a `.venv` não existir: `py -m venv .venv` e depois `.venv\Scripts\python.exe -m pip install UnityPy` (versão usada: 1.25.4).
Se o formato mudar, o script falha com uma mensagem clara e salva `_raw_lng_pt-br.bin`.
