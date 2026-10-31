# Exportar os textos em português do Graveyard Keeper 2

## O que este programa faz

O Graveyard Keeper 2 vem com a tradução oficial em português do Brasil, mas ela fica guardada dentro dos arquivos do jogo. Este programa copia esses textos para arquivos comuns, como uma planilha, para que o site use os nomes oficiais dos itens no lugar das nossas traduções aproximadas.

- **Ele só LÊ os arquivos do jogo.** Nada é alterado, apagado ou instalado no jogo, e o seu save não é tocado.
- Ele não envia nada pela internet. Quem nos manda o arquivo no final é você.
- Leva de alguns segundos a poucos minutos.

## Antes de começar

Você precisa de:
- Windows com o **Graveyard Keeper 2** instalado (pela Steam).
- A pasta `exportar-textos` com estes arquivos: `exportar_textos.bat`, `exportar_textos.py` e este `LEIA-ME.md`.

## Passo a passo

### 1. Instale o Python 3 (só na primeira vez)

1. Entre em **https://www.python.org/downloads/** e clique no botão amarelo **Download Python 3.x**.
2. Abra o instalador baixado.
3. **Importante:** na primeira tela, marque a caixinha **"Add python.exe to PATH"** (fica embaixo).
4. Clique em **Install Now** e espere terminar.

Se você já tem o Python 3, pule este passo.

### 2. Instale o UnityPy (opcional, recomendado)

O UnityPy é uma biblioteca que ajuda a ler os arquivos de jogos feitos na Unity. O programa funciona sem ele, porque tem um leitor próprio, mas com ele a leitura fica mais confiável.

Você pode deixar o próprio programa instalar no passo 3: quando ele perguntar *"Instalar agora?"*, aperte **S**.

Se preferir instalar à mão, abra o menu Iniciar, digite `cmd`, abra o **Prompt de Comando** e digite:

```
py -m pip install UnityPy
```

(Se `py` não funcionar, use `pip install UnityPy`.)

### 3. Rode o exportador

1. **Feche o jogo**, se estiver aberto. Não é obrigatório, mas evita problemas.
2. Dê **dois cliques** em `exportar_textos.bat`.
3. Uma janela preta vai abrir e mostrar o andamento. O programa procura o jogo sozinho nas bibliotecas da Steam.
4. Quando terminar, aparece **PRONTO!** e a lista dos arquivos criados. Aperte qualquer tecla para fechar.

### 4. Mande o arquivo para nós

Na mesma pasta do programa vão aparecer:

| Arquivo | O que é |
|---|---|
| **`gk2_textos.json`** | **Este é o arquivo que precisamos.** Tem todos os textos em inglês e em português. |
| `gk2_textos_pt-br.csv` | Os textos em português (abre no Excel, se quiser dar uma olhada) |
| `gk2_textos_en.csv` | Os textos em inglês (abre no Excel) |
| `gk2_exportacao_log.txt` | Relatório do que o programa fez (ajuda se algo der errado) |

Mande o **`gk2_textos.json`**. Se puder, mande o `gk2_exportacao_log.txt` junto. Os dois são pequenos, só alguns MB.

## Se algo der errado

### "O Python 3 não foi encontrado"
- Instale o Python como no passo 1 e **marque "Add python.exe to PATH"**.
- Se já instalou sem marcar, rode o instalador de novo, escolha **Modify**, depois **Next**, e marque **"Add Python to environment variables"**.
- Feche a janela preta e dê dois cliques no `.bat` de novo. Se não resolver, reinicie o computador.
- Se abrir a **Microsoft Store** quando você digita `python`, é o atalho do Windows. Instale pelo site python.org mesmo.

### "Não encontrei a pasta do jogo"
O programa vai pedir o caminho. Para descobrir qual é:
1. Abra a **Steam**, vá em **Biblioteca** e clique com o botão direito em **Graveyard Keeper 2**.
2. Clique em **Gerenciar** e depois em **Procurar arquivos locais**. A pasta do jogo vai abrir.
3. Clique na barra de endereço do Explorer (lá em cima), copie com **Ctrl+C**, cole na janela preta com o botão direito e aperte **Enter**.

Outro jeito: **arraste a pasta do jogo para cima do `exportar_textos.bat`**.

Ou, no Prompt de Comando:
```
py -3 exportar_textos.py "D:\SteamLibrary\steamapps\common\Graveyard Keeper 2"
```

### O antivírus bloqueou ou reclamou
- O `.bat` só chama o Python para rodar o `exportar_textos.py`. É um texto que você pode abrir no Bloco de Notas e ler.
- O Windows Defender ou o SmartScreen às vezes avisam sobre `.bat` baixado da internet. Clique em **Mais informações** e depois em **Executar assim mesmo**.
- Se o antivírus apagar o `.bat`, rode direto pelo Prompt de Comando, dentro da pasta do programa:
  ```
  py -3 exportar_textos.py
  ```

### A instalação do UnityPy falhou
Tudo bem. O programa continua com o leitor embutido. Se a exportação também falhar, instale o **Python 3.12** pelo python.org (versões muito novas às vezes ainda não têm o UnityPy pronto) e tente de novo.

### "Não consegui gravar os arquivos"
- Se algum `.csv` estiver aberto no Excel, feche e rode de novo.
- Se a pasta do programa estiver dentro de um `.zip`, extraia antes (botão direito, **Extrair tudo**).

### "NÃO consegui exportar os textos em português"
Mande para nós o `gk2_exportacao_log.txt` e, se ele existir, o `_raw_lng_pt-br.bin`. Com esses arquivos conseguimos ajustar o programa para a sua versão do jogo.

---

*Detalhe técnico, para os curiosos: o texto de cada idioma fica num objeto da Unity chamado `lng_pt-br` (e `lng_en`, `lng_de`...) dentro de `GraveyardKeeper2_Data\resources.assets`. O programa encontra esse objeto e lê as listas de chaves e textos. Os nomes do site são ligados aos do jogo por essas chaves (por exemplo, `nails_bronze`).*

---

## Para quem mantém o projeto (não precisa ler para exportar)

- `exportar_textos.py` + `.bat`: a versão amigável descrita acima (leitor embutido, UnityPy opcional, log).
- `exportar_textos_unitypy.py`: a variante estrita que rodou de fato no jogo 1.011 (exige UnityPy; grava também os 11 idiomas, a versão do jogo e `_resumo.json`). Ver `data/game-texts/RELATORIO-exportacao.md`.
- O arquivo recebido vai para `data/game-texts/gk2_textos.json` (versionado). CSVs, `gk2_textos_todos.json` e `_resumo.json` ficam ao lado, fora do git.
- Depois: `python3 -I tools/exportar-textos/juntar_nomes.py --atualizar` (atualiza `data/names.official.pt-BR.json`). Roteiro completo em `docs/atualizacao.md`.
