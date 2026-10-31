@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Exportar textos - Graveyard Keeper 2
cd /d "%~dp0"
set "GK2_EXPORT_BAT=1"

rem ------------------------------------------------------------------
rem  Exporta os textos (pt-BR e ingles) do Graveyard Keeper 2.
rem  So LE os arquivos do jogo; nada e alterado.
rem  Dica: voce pode arrastar a pasta do jogo para cima deste arquivo.
rem ------------------------------------------------------------------

rem Procura o Python: primeiro o lancador "py", depois "python"
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo.
    echo  [ERRO] O Python 3 nao foi encontrado neste computador.
    echo  Instale pelo site https://www.python.org/downloads/
    echo  Na primeira tela do instalador, marque "Add python.exe to PATH".
    echo  Depois feche esta janela e de dois cliques neste arquivo de novo.
    goto :fim
)

%PY% -c "import UnityPy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  A biblioteca UnityPy nao esta instalada.
    echo  Ela ajuda a ler os arquivos do jogo, mas o programa tambem funciona sem ela.
    choice /C SN /M " Instalar agora com 'pip install UnityPy' - precisa de internet"
    if not errorlevel 2 (
        %PY% -m pip install --user UnityPy
        if errorlevel 1 echo  [AVISO] A instalacao falhou. Vou continuar com o leitor embutido.
    )
)

echo.
%PY% "%~dp0exportar_textos.py" %*

:fim
echo.
pause
endlocal
