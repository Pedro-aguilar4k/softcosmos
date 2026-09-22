@echo off
title Agente SoftCosmos - Conferencia e Impressao de Etiquetas
color 0b
echo =========================================================================
echo       AGENTE EMULADOR SOFTCOSMOS - DISPARO AUTOMATICO DE ETIQUETAS
echo =========================================================================
echo.
echo Verificando instalacao do Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no seu Windows.
    echo Por favor, instale o Python 3 (marque a opcao "Add Python to PATH").
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b
)

echo.
echo Verificando IP local deste computador para comunicacao com seu servidor:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4" /c:"Endereço IPv4"') do (
    echo [IP DA REDE LOCAL] http://%%a:3333/imprimir/CODIGO
)
echo [IP LOCALHOST]     http://localhost:3333/imprimir/CODIGO
echo.
echo =========================================================================
echo Iniciando o agente na porta 3333...
echo =========================================================================
python "%~dp0agente_emulador_softcosmos.py"
pause
