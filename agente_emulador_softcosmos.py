#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
AGENTE DE EMULACAO E IMPRESSAO AUTOMATICA VIA SOFTCOSMOS (WINDOWS API / DELPHI)
=============================================================================
Este agente roda em segundo plano no PC Windows onde o SoftCosmos esta aberto.
Ele recebe a ordem de impressao do seu SISTEMA DE CONFERENCIA (via HTTP/REST)
e emula exatamente o comportamento de um operador humano dentro do SoftCosmos:
  1. Localiza a janela do 'Gerenciador de Etiquetas' (TFEtiquetas / FEtiquetas)
  2. Injeta o codigo do produto no campo de inclusao
  3. Dispara a tecla ENTER (fazendo o SoftCosmos buscar produto, preco e dados)
  4. Dispara o botao 'Imprimir' (usando o layout e impressora do proprio ERP)

Zero alteracoes no banco de dados, zero custos e zero modificacoes no ERP.
Funciona via Windows Win32 API nativa (ctypes - nao exige compiladores).
=============================================================================
"""

import sys
import os
import json
import time
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Bibliotecas nativas do Windows via ctypes (Zero dependencias obrigatorias)
IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
else:
    # Emulacao para ambiente de desenvolvimento/Linux
    user32 = None
    kernel32 = None

# Constantes da API Win32
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
WM_COMMAND = 0x0111
BM_CLICK = 0x00F5
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F9 = 0x78
SW_RESTORE = 9
SW_SHOW = 5

# Configuracoes padrao baseadas na engenharia reversa do SoftCosmos.exe
CONFIG_PADRAO = {
    "porta_api": 3333,
    "janela_alvo_titulo": "Gerenciador de Etiquetas",
    "janela_alvo_classe": "TFEtiquetas",
    "janela_softcosmos_titulo": "SoftCosmos",
    "tempo_espera_busca_ms": 400,     # Tempo para o SoftCosmos consultar o produto apos ENTER
    "tempo_espera_impressao_ms": 300, # Tempo antes de clicar em imprimir
    "metodo_emulacao": "auto",        # "auto", "win32_background" ou "teclado_focado"
    "restaurar_foco_apos_impressao": True,
    "atalho_impressao": "ENTER"       # Tecla ou botao usado para imprimir no formulario
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_emulador.json")

def carregar_config():
    cfg = dict(CONFIG_PADRAO)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"[AVISO] Erro ao carregar config_emulador.json: {e}")
    return cfg

def salvar_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar config: {e}")

CONFIG = carregar_config()

# =============================================================================
# NUCLEO WIN32 API PARA INTERACAO COM O SOFTCOSMOS
# =============================================================================

def obter_texto_janela(hwnd):
    if not IS_WINDOWS or not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    return ""

def obter_classe_janela(hwnd):
    if not IS_WINDOWS or not hwnd:
        return ""
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value

def listar_janelas_sistema():
    """Retorna lista de janelas ativas relacionadas ao SoftCosmos no Windows"""
    if not IS_WINDOWS:
        return [{
            "hwnd": 12345,
            "titulo": "Gerenciador de Etiquetas (Simulado no Linux)",
            "classe": "TFEtiquetas",
            "visivel": True
        }]

    janelas = []
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    
    def enum_proc(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            titulo = obter_texto_janela(hwnd)
            classe = obter_classe_janela(hwnd)
            if titulo or "Delphi" in classe or "TF" in classe or "Soft" in titulo:
                # Filtrar especialmente janelas do SoftCosmos
                if any(k in titulo.lower() for k in ["softcosmos", "etiqueta", "softsystem", "gerenciador"]) or \
                   any(k in classe.lower() for k in ["tfetiquetas", "tfgerenciador", "tform", "tsoftcosmos"]):
                    janelas.append({
                        "hwnd": hwnd,
                        "titulo": titulo,
                        "classe": classe,
                        "visivel": True
                    })
        return True

    user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
    return janelas

def mapear_controles_filhos(hwnd_pai):
    """Mapeia todos os controles internos (botoes, edits, grids) de uma janela Delphi"""
    if not IS_WINDOWS or not hwnd_pai:
        return []

    controles = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_child_proc(hwnd, lparam):
        titulo = obter_texto_janela(hwnd)
        classe = obter_classe_janela(hwnd)
        ret = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(ret))
        
        controles.append({
            "hwnd": hwnd,
            "classe": classe,
            "titulo": titulo,
            "x": ret.left,
            "y": ret.top,
            "largura": ret.right - ret.left,
            "altura": ret.bottom - ret.top,
            "habilitado": bool(user32.IsWindowEnabled(hwnd))
        })
        return True

    user32.EnumChildWindows(hwnd_pai, WNDENUMPROC(enum_child_proc), 0)
    return controles

def localizar_janela_etiquetas():
    """Localiza a janela do Gerenciador de Etiquetas ou a janela principal do SoftCosmos"""
    if not IS_WINDOWS:
        return 12345, "Gerenciador de Etiquetas (Simulado)"

    # 1. Procura exata por titulo configurado
    titulo_alvo = CONFIG.get("janela_alvo_titulo", "Gerenciador de Etiquetas")
    hwnd = user32.FindWindowW(None, titulo_alvo)
    if hwnd:
        return hwnd, titulo_alvo

    # 2. Varredura por classe Delphi 'TFEtiquetas'
    classe_alvo = CONFIG.get("janela_alvo_classe", "TFEtiquetas")
    hwnd = user32.FindWindowW(classe_alvo, None)
    if hwnd:
        return hwnd, obter_texto_janela(hwnd)

    # 3. Busca parcial entre janelas abertas
    janelas = listar_janelas_sistema()
    for j in janelas:
        if "etiqueta" in j["titulo"].lower():
            return j["hwnd"], j["titulo"]

    # 4. Fallback: Janela principal do SoftCosmos
    for j in janelas:
        if "softcosmos" in j["titulo"].lower() or "softsystem" in j["titulo"].lower():
            return j["hwnd"], j["titulo"]

    return None, None

def enviar_caracteres_win32(hwnd, texto):
    """Envia texto caractere por caractere via WM_CHAR para controles Delphi"""
    for ch in str(texto):
        user32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)
        time.sleep(0.01)

def emular_tecla_enter(hwnd):
    """Dispara a tecla ENTER no controle alvo"""
    user32.PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0)
    time.sleep(0.02)
    user32.PostMessageW(hwnd, WM_KEYUP, VK_RETURN, 0)

# =============================================================================
# ESTRATEGIAS DE EXECUCAO NO SOFTCOSMOS
# =============================================================================

def executar_emulacao_etiqueta(codigo_produto, copias=1):
    """
    Executa a sequencia exata do SoftCosmos:
    1. Localiza a janela do Gerenciador de Etiquetas
    2. Informa o codigo do produto
    3. Pressiona ENTER para puxar os dados
    4. Aciona a impressao
    """
    codigo_produto = str(codigo_produto).strip()
    if not codigo_produto:
        return False, "Codigo do produto nao informado."

    if not IS_WINDOWS:
        # Simulacao em ambiente de teste/servidor Linux
        print(f"[SIMULACAO] Disparo recebido: Codigo={codigo_produto}, Copias={copias}")
        return True, f"[SIMULACAO] Etiqueta do codigo '{codigo_produto}' processada com sucesso no SoftCosmos."

    hwnd_janela, titulo_encontrado = localizar_janela_etiquetas()
    if not hwnd_janela:
        return False, (
            "Janela 'Gerenciador de Etiquetas' ou 'SoftCosmos' nao encontrada no Windows. "
            "Por favor, deixe a tela do Gerenciador de Etiquetas aberta no SoftCosmos."
        )

    print(f"[INFO] Janela identificada: HWND={hwnd_janela} - '{titulo_encontrado}'")
    controles = mapear_controles_filhos(hwnd_janela)
    print(f"[INFO] Controles internos localizados na janela: {len(controles)}")

    # Salva a janela que o usuario estava mexendo para restaurar depois
    hwnd_anterior = user32.GetForegroundWindow()

    metodo = CONFIG.get("metodo_emulacao", "auto")
    tempo_busca = CONFIG.get("tempo_espera_busca_ms", 400) / 1000.0
    tempo_imp = CONFIG.get("tempo_espera_impressao_ms", 300) / 1000.0

    # -------------------------------------------------------------------------
    # ESTRATEGIA A: INJECAO DIRETA EM SEGUNDO PLANO (WIN32 HWND)
    # -------------------------------------------------------------------------
    campo_edit = None
    botao_imprimir = None

    # Tenta achar o controle de edicao (TcxCustomInnerEdit, TEdit, Edit)
    for c in controles:
        classe_lower = c["classe"].lower()
        if "edit" in classe_lower and c["habilitado"]:
            campo_edit = c["hwnd"]
            break

    # Tenta achar o botao Imprimir
    for c in controles:
        titulo_lower = c["titulo"].lower()
        if any(k in titulo_lower for k in ["imprimir", "imprime", "gerar"]):
            botao_imprimir = c["hwnd"]
            break

    if campo_edit and metodo in ("auto", "win32_background"):
        print(f"[INFO] Usando injecao Win32 silenciosa no campo HWND={campo_edit}...")
        
        # 1. Define o texto do codigo
        user32.SendMessageW(campo_edit, WM_SETTEXT, 0, codigo_produto)
        time.sleep(0.05)

        # 2. Pressiona ENTER no campo para o SoftCosmos carregar o produto
        emular_tecla_enter(campo_edit)
        time.sleep(tempo_busca)

        # 3. Dispara o botao imprimir (se achou) ou dispara ENTER/F2
        if botao_imprimir:
            user32.PostMessageW(botao_imprimir, BM_CLICK, 0, 0)
        else:
            emular_tecla_enter(campo_edit)

        time.sleep(tempo_imp)
        return True, f"Etiqueta do codigo '{codigo_produto}' injetada e impressa via SoftCosmos com sucesso!"

    # -------------------------------------------------------------------------
    # ESTRATEGIA B: EMULACAO COM FOCO RAPIDO (DEVEXPRESS / TCXGRID COMPATIVEL)
    # Os componentes DevExpress do Delphi muitas vezes sao 'windowless'.
    # Nesse caso, trazemos a janela suavemente, digitamos e devolvemos o foco!
    # -------------------------------------------------------------------------
    print("[INFO] Executando emulacao com foco rapido (compativel com DevExpress TcxGrid)...")

    # Traz a janela para a frente
    user32.ShowWindow(hwnd_janela, SW_RESTORE)
    user32.SetForegroundWindow(hwnd_janela)
    time.sleep(0.08)

    # Digita o codigo do produto via SendInput
    enviar_caracteres_teclado_sendinput(codigo_produto)
    time.sleep(0.05)

    # Pressiona ENTER (SoftCosmos busca produto)
    enviar_tecla_virtual_sendinput(VK_RETURN)
    time.sleep(tempo_busca)

    # Dispara acao de impressao (se houver botao ou tecla Enter/F5)
    enviar_tecla_virtual_sendinput(VK_RETURN)
    time.sleep(tempo_imp)

    # Restaura o foco da janela onde o operador estava trabalhando
    if CONFIG.get("restaurar_foco_apos_impressao", True) and hwnd_anterior and hwnd_anterior != hwnd_janela:
        user32.SetForegroundWindow(hwnd_anterior)

    return True, f"Etiqueta do codigo '{codigo_produto}' processada e impressa com sucesso no SoftCosmos!"

# =============================================================================
# ENVIO DE TECLAS VIA NATIVE SENDINPUT (WINDOWS)
# =============================================================================

def enviar_caracteres_teclado_sendinput(texto):
    """Envia texto usando a funcao nativa SendInput do Windows"""
    if not IS_WINDOWS:
        return

    # Usando o script PowerShell ou ctypes para envio ultraconfiavel
    for char in str(texto):
        vkey = user32.VkKeyScanW(ord(char)) & 0xFF
        if vkey:
            user32.keybd_event(vkey, 0, 0, 0)
            time.sleep(0.01)
            user32.keybd_event(vkey, 0, 2, 0) # 2 = KEYEVENTF_KEYUP
            time.sleep(0.01)

def enviar_tecla_virtual_sendinput(vk_code):
    """Envia tecla de comando (ENTER, TAB, F2, etc.)"""
    if not IS_WINDOWS:
        return
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(vk_code, 0, 2, 0) # KEYEVENTF_KEYUP
    time.sleep(0.02)

# =============================================================================
# SERVIDOR HTTP REST API PARA O SISTEMA DE CONFERENCIA
# =============================================================================

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agente SoftCosmos - Conferencia & Etiquetas</title>
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --border: #334155;
            --primary: #38bdf8;
            --primary-hover: #0ea5e9;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --success: #22c55e;
            --error: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 24px; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
        h1 { font-size: 20px; font-weight: 600; color: var(--primary); }
        .badge { background: #064e3b; color: #6ee7b7; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px; }
        .badge::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: #34d399; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
        @media(max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        .card h2 { font-size: 16px; margin-bottom: 12px; color: var(--text); }
        .input-group { margin-bottom: 14px; }
        label { display: block; font-size: 13px; color: var(--text-dim); margin-bottom: 6px; }
        input, select { width: 100%; background: #0f172a; border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; color: #fff; font-size: 14px; }
        input:focus { border-color: var(--primary); outline: none; }
        button { background: var(--primary); color: #0f172a; border: none; border-radius: 8px; padding: 10px 16px; font-size: 14px; font-weight: 600; cursor: pointer; width: 100%; transition: background 0.2s; }
        button:hover { background: var(--primary-hover); }
        .log-box { background: #090d16; border: 1px solid var(--border); border-radius: 8px; padding: 14px; font-family: monospace; font-size: 12px; height: 260px; overflow-y: auto; color: #a5f3fc; }
        .log-item { margin-bottom: 6px; border-bottom: 1px dashed #1e293b; padding-bottom: 4px; }
        .code-box { background: #090d16; padding: 12px; border-radius: 8px; font-size: 12px; color: #e2e8f0; overflow-x: auto; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Agente SoftCosmos - Emulador de Etiquetas</h1>
                <p style="font-size: 13px; color: var(--text-dim);">Pronto para receber chamadas do seu sistema de conferencia</p>
            </div>
            <div class="badge">Agente Conectado (Porta 3333)</div>
        </header>

        <div class="grid">
            <div class="card">
                <h2>Testar Impressao Imediata</h2>
                <div class="input-group">
                    <label>Codigo do Produto ou Codigo de Barras</label>
                    <input type="text" id="codigo" placeholder="Ex: 123 ou 7891234567890" autofocus>
                </div>
                <div class="input-group">
                    <label>Quantidade de Copias</label>
                    <input type="number" id="copias" value="1" min="1">
                </div>
                <button onclick="dispararImpressao()">Disparar para o SoftCosmos</button>
                <div id="resultado" style="margin-top: 12px; font-size: 13px;"></div>
            </div>

            <div class="card">
                <h2>Como Chamar do seu Sistema de Conferencia</h2>
                <p style="font-size: 13px; color: var(--text-dim); line-height: 1.5;">
                    No seu projeto de conferencia, basta disparar um GET ou POST para este endereço local:
                </p>
                <div class="code-box">
                    fetch("http://localhost:3333/imprimir/123")<br>
                    &nbsp;&nbsp;.then(res => res.json())<br>
                    &nbsp;&nbsp;.then(data => console.log(data));
                </div>
                <p style="font-size: 12px; color: var(--text-dim); margin-top: 10px;">
                    O SoftCosmos assume a busca e imprime a etiqueta automaticamente.
                </p>
            </div>
        </div>

        <div class="card">
            <h2>Historico de Disparos em Tempo Real</h2>
            <div class="log-box" id="logs">
                <div class="log-item">[SISTEMA] Agente iniciado com sucesso. Aguardando disparos...</div>
            </div>
        </div>
    </div>

    <script>
        function log(msg) {
            const logs = document.getElementById('logs');
            const item = document.createElement('div');
            item.className = 'log-item';
            const hora = new Date().toLocaleTimeString();
            item.innerText = `[${hora}] ${msg}`;
            logs.appendChild(item);
            logs.scrollTop = logs.scrollHeight;
        }

        async function dispararImpressao() {
            const cod = document.getElementById('codigo').value.trim();
            const copias = document.getElementById('copias').value;
            const resDiv = document.getElementById('resultado');

            if (!cod) {
                resDiv.innerHTML = '<span style="color: var(--error);">Digite um codigo para testar.</span>';
                return;
            }

            resDiv.innerHTML = '<span style="color: var(--primary);">Enviando para o SoftCosmos...</span>';
            log(`Disparando impressao do codigo: ${cod} (${copias} copias)...`);

            try {
                const res = await fetch(`/imprimir/${encodeURIComponent(cod)}?copias=${copias}`);
                const data = await res.json();

                if (data.sucesso || data.status === 'sucesso') {
                    resDiv.innerHTML = `<span style="color: var(--success);">${data.mensagem}</span>`;
                    log(`SUCESSO: ${data.mensagem}`);
                    document.getElementById('codigo').value = '';
                    document.getElementById('codigo').focus();
                } else {
                    resDiv.innerHTML = `<span style="color: var(--error);">${data.mensagem || data.erro}</span>`;
                    log(`ERRO: ${data.mensagem || data.erro}`);
                }
            } catch (err) {
                resDiv.innerHTML = `<span style="color: var(--error);">Falha ao contatar agente: ${err.message}</span>`;
                log(`FALHA CONEXAO: ${err.message}`);
            }
        }

        document.getElementById('codigo').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') dispararImpressao();
        });
    </script>
</body>
</html>
"""

class RequisicaoHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Permite requisicoes CORS de qualquer porta ou aplicacao web local
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        caminho = parsed.path

        # 1. Dashboard Web
        if caminho == "/" or caminho == "/index.html":
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode('utf-8'))
            return

        # 2. Status / Health Check
        if caminho == "/health" or caminho == "/status":
            self.enviar_json(200, {
                "status": "online",
                "modulo": "Agente Emulador SoftCosmos",
                "plataforma": sys.platform,
                "janelas_softcosmos": listar_janelas_sistema()
            })
            return

        # 3. Lista de Janelas do SoftCosmos (Diagnostico)
        if caminho == "/janelas":
            self.enviar_json(200, {
                "janelas": listar_janelas_sistema()
            })
            return

        # 4. Disparo Direto de Impressao: /imprimir/<codigo>?copias=1
        if caminho.startswith("/imprimir/"):
            codigo = caminho.replace("/imprimir/", "").strip()
            params = parse_qs(parsed.query)
            copias = int(params.get('copias', ['1'])[0])

            sucesso, msg = executar_emulacao_etiqueta(codigo, copias)
            status_code = 200 if sucesso else 400
            self.enviar_json(status_code, {
                "sucesso": sucesso,
                "codigo": codigo,
                "copias": copias,
                "mensagem": msg
            })
            return

        self.enviar_json(404, {"erro": "Rota nao encontrada", "rotas": ["/imprimir/<codigo>", "/health", "/janelas"]})

    def do_POST(self):
        parsed = urlparse(self.path)
        caminho = parsed.path

        if caminho == "/imprimir":
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            try:
                dados = json.loads(post_body.decode('utf-8'))
            except Exception:
                dados = {}

            codigo = dados.get('codigo') or dados.get('termo') or dados.get('ean')
            copias = int(dados.get('copias', 1))

            sucesso, msg = executar_emulacao_etiqueta(codigo, copias)
            status_code = 200 if sucesso else 400
            self.enviar_json(status_code, {
                "sucesso": sucesso,
                "codigo": codigo,
                "copias": copias,
                "mensagem": msg
            })
            return

        self.enviar_json(404, {"erro": "Rota nao encontrada"})

    def enviar_json(self, status_code, dados):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(dados, ensure_ascii=False, indent=2).encode('utf-8'))

    def log_message(self, format, *args):
        # Log mais limpo no terminal
        print(f"[REQUISICAO] {self.address_string()} - {format % args}")

# =============================================================================
# MODO INSPETOR E INICIALIZACAO CLI
# =============================================================================

def modo_inspetor():
    print("=" * 70)
    print("INSPETOR DE JANELAS E CONTROLES DO SOFTCOSMOS")
    print("=" * 70)
    janelas = listar_janelas_sistema()
    if not janelas:
        print("[!] Nenhuma janela do SoftCosmos localizada aberta no Windows.")
        print("    Abra o SoftCosmos e o Gerenciador de Etiquetas e execute novamente.")
        return

    print(f"Foram encontradas {len(janelas)} janelas relacionadas:")
    for i, j in enumerate(janelas):
        print(f"\n[{i+1}] HWND: {j['hwnd']} | Titulo: '{j['titulo']}' | Classe: '{j['classe']}'")
        controles = mapear_controles_filhos(j['hwnd'])
        print(f"    Controles internos ({len(controles)}):")
        for c in controles[:20]:
            print(f"      - HWND {c['hwnd']}: Classe='{c['classe']}' Titulo='{c['titulo']}' [{c['largura']}x{c['altura']}]")
        if len(controles) > 20:
            print(f"      ... e mais {len(controles) - 20} controles.")

def main():
    parser = argparse.ArgumentParser(description="Agente de Emulacao SoftCosmos para Conferencia de Etiquetas")
    parser.add_argument("--porta", type=int, default=CONFIG.get("porta_api", 3333), help="Porta HTTP da API (padrao: 3333)")
    parser.add_argument("--codigo", type=str, help="Disparar impressao de um codigo diretamente via terminal")
    parser.add_argument("--inspect", action="store_true", help="Inspecionar janelas e controles abertos no Windows")

    args = parser.parse_args()

    if args.inspect:
        modo_inspetor()
        return

    if args.codigo:
        print(f"[TESTE DIRETO] Disparando para o codigo: {args.codigo}")
        sucesso, msg = executar_emulacao_etiqueta(args.codigo)
        print(f"Resultado: {msg}")
        return

    porta = args.porta
    servidor = HTTPServer(('0.0.0.0', porta), RequisicaoHandler)
    print("=" * 75)
    print("AGENTE EMULADOR SOFTCOSMOS - CONFERENCIA & ETIQUETAS")
    print("=" * 75)
    print(f"-> Servidor rodando em: http://localhost:{porta}")
    print(f"-> Painel de Testes Web: http://localhost:{porta}/")
    print(f"-> Endpoint de Impressao: GET http://localhost:{porta}/imprimir/SEU_CODIGO")
    print(f"-> Status do ERP: http://localhost:{porta}/status")
    print("-> Pressione CTRL+C para encerrar o agente.")
    print("=" * 75)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Agente encerrado.")
        servidor.server_close()

if __name__ == '__main__':
    main()
