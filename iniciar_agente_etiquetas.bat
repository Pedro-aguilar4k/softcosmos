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

echo Iniciando o agente em http://localhost:3333 ...
echo.
python "%~dp0agente_emulador_softcosmos.py"
pause
