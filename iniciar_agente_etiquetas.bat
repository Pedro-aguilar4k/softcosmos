@echo off
title Agente SoftCosmos - Conferencia e Impressao de Etiquetas
color 0b
echo =========================================================================
echo       AGENTE EMULADOR SOFTCOSMOS - DISPARO AUTOMATICO DE ETIQUETAS
echo =========================================================================
echo.

:: Se o executavel compilado existir, roda diretamente sem precisar de Python
if exist "%~dp0dist\AgenteSoftCosmos.exe" (
    echo [MODO EXECUTAVEL STANDALONE DETECTADO]
    echo Iniciando AgenteSoftCosmos.exe em segundo plano...
    start "" "%~dp0dist\AgenteSoftCosmos.exe"
    exit /b
)

if exist "%~dp0AgenteSoftCosmos.exe" (
    echo [MODO EXECUTAVEL STANDALONE DETECTADO]
    echo Iniciando AgenteSoftCosmos.exe em segundo plano...
    start "" "%~dp0AgenteSoftCosmos.exe"
    exit /b
)

echo Verificando instalacao do Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Python nao foi encontrado no seu Windows.
    echo Se voce compilou o executavel (.exe), copie o 'AgenteSoftCosmos.exe' para ca.
    echo Caso contrario, instale o Python 3 marcando "Add Python to PATH":
    echo https://www.python.org/downloads/
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
