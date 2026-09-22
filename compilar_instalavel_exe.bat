@echo off
title Compilador de Instalavel Windows - Agente SoftCosmos
color 0b
cls

echo ===============================================================================
echo       GERADOR DE EXECUTAVEL STANDALONE (INSTALAVEL .EXE) - AGENTE SOFTCOSMOS
echo ===============================================================================
echo.
echo Este script cria um executavel .EXE unico e independente:
echo - NAO precisa de Python instalado no computador do caixa/conferencia
echo - Roda 100%% em segundo plano sem janela preta de terminal
echo - Consome menos de 15MB de memoria
echo - Conexao Real-Time com a Vercel (ZERO polling)
echo.

pause

echo.
echo [1/3] Verificando instalador do PyInstaller...
python -m pip install --upgrade pip
python -m pip install pyinstaller

echo.
echo [2/3] Compilando AgenteSoftCosmos.exe (Isso pode levar de 30 a 60 segundos)...
python -m PyInstaller --onefile --noconsole --name "AgenteSoftCosmos" --add-data "config_emulador.json;." agente_emulador_softcosmos.py

if exist "dist\AgenteSoftCosmos.exe" (
    echo.
    echo ===============================================================================
    echo [SUCESSO!] EXECUTAVEL GERADO COM SUCESSO!
    echo ===============================================================================
    echo Arquivo gerado em: dist\AgenteSoftCosmos.exe
    echo.
    echo Voce pode copiar o arquivo 'AgenteSoftCosmos.exe' junto com o 'config_emulador.json'
    echo para qualquer computador com Windows e dar 2 cliques para rodar!
    echo.
) else (
    echo.
    echo [ERRO] Ocorreu uma falha durante a compilacao. Verifique as mensagens acima.
)

pause
