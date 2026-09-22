@echo off
title Instalador do Agente SoftCosmos - Conferencia & Etiquetas
color 0a
cls

echo ===============================================================================
echo        INSTALADOR AUTOMATICO DO AGENTE SOFTCOSMOS (WINDOWS STARTUP)
echo ===============================================================================
echo.
echo Este assistente configura o Agente para:
echo 1. Conectar ao seu sistema de conferencia na Vercel (Modo Real-Time)
echo 2. Iniciar automaticamente sempre que o Windows ligar
echo 3. Rodar em segundo plano sem atrapalhar o operador
echo.

set /p URL_VERCEL="Digite a URL do seu sistema na Vercel (ex: https://meu-projeto.vercel.app): "

if "%URL_VERCEL%"=="" (
    echo [AVISO] Nenhuma URL digitada. Mantendo configuracao padrao do arquivo config_emulador.json.
) else (
    echo.
    echo Atualizando config_emulador.json com a sua URL...
    powershell -Command "(Get-Content config_emulador.json) -replace 'https://SEU-PROJETO.vercel.app/api/stream-etiquetas', '%URL_VERCEL%/api/stream-etiquetas' | Set-Content config_emulador.json"
    powershell -Command "(Get-Content config_emulador.json) -replace 'https://SEU-PROJETO.vercel.app/api/fila-etiquetas', '%URL_VERCEL%/api/fila-etiquetas' | Set-Content config_emulador.json"
    echo [OK] Configuracao gravada com sucesso!
)

echo.
echo [2/3] Criando atalho na Inicializacao do Windows (shell:startup)...
set "PASTA_ATUAL=%~dp0"
set "PASTA_STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%PASTA_STARTUP%\AgenteSoftCosmos.lnk'); $Shortcut.TargetPath = '%PASTA_ATUAL%iniciar_agente_etiquetas.bat'; $Shortcut.WorkingDirectory = '%PASTA_ATUAL%'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"

echo [OK] Atalho criado no Startup do Windows!
echo.
echo [3/3] Iniciando o agente agora em segundo plano...
start "" "%PASTA_ATUAL%iniciar_agente_etiquetas.bat"

echo.
echo ===============================================================================
echo                   INSTALACAO CONCLUIDA COM SUCESSO!
echo ===============================================================================
echo O Agente esta ativo e conectado na sua aplicacao da Vercel.
echo Quando o conferente bipar um produto, a etiqueta saira no SoftCosmos!
echo.
pause
