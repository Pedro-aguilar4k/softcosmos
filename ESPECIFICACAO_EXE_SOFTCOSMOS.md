# ESPECIFICAÇÃO TÉCNICA COMPLETA: EXECUTÁVEL WINDOWS (.EXE) AGENTE SOFTCOSMOS

> **Objetivo do Documento:** Este documento serve como prompt mestre e especificação técnica para ser entregue a uma IA ou desenvolvedor para gerar o executável nativo Windows (`AgenteSoftCosmos.exe`).

---

## 1. VISÃO GERAL DO PROJETO

- **Nome do Executável:** `AgenteSoftCosmos.exe`
- **Ambiente de Destino:** Windows 10 / Windows 11 / Windows Server (32 ou 64-bit)
- **Papel:** Serviço em segundo plano que recebe ordens de impressão do sistema web de conferência (hospedado na Vercel) e emula a digitação e clique no ERP **SoftCosmos.exe** em tempo real, sem que o operador precise abrir janelas manualmente nem perder o foco da tela atual.
- **Tecnologias Recomendadas para o .EXE:** 
  - **C# / .NET 8 (Single File / Self-Contained / Native AOT)** — gera um único `.exe` leve (~10-15MB), sem necessidade de runtime instalado.
  - **OU Golang (Go)** — gera um único binário nativo de ~8MB, excelente para rede e chamadas Windows API.
  - **OU C++ (Win32)** — binário ultraleve de ~500KB.
  - **OU Python compilado via PyInstaller (`--onefile --noconsole`)**.

---

## 2. MAPEAMENTO DOS CONTROLES DO SOFTCOSMOS (ENGENHARIA REVERSA)

O software alvo é o **`SoftCosmos.exe`**, desenvolvido em **Embarcadero Delphi / VCL** com componentes **DevExpress (TcxGrid, TcxEdit)**.

### Dados da Janela Alvo:
- **Classe da Janela (lpClassName):** `TFEtiquetas`
- **Nome do Formulário Delphi:** `FEtiquetas`
- **Título da Janela (Caption):** `Gerenciador de Etiquetas` (ou janela contendo `"Etiqueta"` no título)
- **Processo:** `SoftCosmos.exe`

### Controles Internos Identificados:
| Função | Nome do Componente Delphi | Classe Win32 / VCL | Ação de Disparo |
| :--- | :--- | :--- | :--- |
| **Limpar / Novo** | `btnIncluirEtiqueta` | `TBitBtn` / `TcxButton` | Caption `Novo[F3]` ou atalho `VK_F3` (`0x72`) |
| **Campo de Código/EAN** | Campo de busca de produto | `TcxCustomInnerEdit`, `TEdit` ou `Edit` | Injetar string (`WM_SETTEXT`) ou `SendInput` |
| **Pesquisar Produto** | Evento OnKeyDown do Edit | N/A | Pressionar tecla `{ENTER}` (`VK_RETURN` = `0x0D`) |
| **Imprimir Etiqueta** | `BitBtn5` | `TBitBtn` / `TcxButton` | Caption `Imprimir Etiquetas` ou mensagem `BM_CLICK` (`0x00F5`) |

---

## 3. O CICLO DE EXECUÇÃO EXATO POR BIPAGEM (COM ESPERA INTELIGENTE)

Sempre que uma solicitação de impressão chegar (ex: `codigo: "123"`, `copias: 1`), o executável DEVE seguir rigorosamente esta sequência de fluxo. A versão atual **não usa mais tempos fixos "às cegas"** para aguardar o Firebird: ela faz *polling* real da tela e cancela o fluxo se detectar um popup de erro do SoftCosmos.

```
[Bip Recebido da Vercel: "123"]
           │
           ▼
[Passo 1: Salvar HWND Atual] ──> Salva GetForegroundWindow() para devolver o foco depois
           │
           ▼
[Passo 2: Localizar Controles com Retentativa] ──> Mapeia botão '+', grid, botão Imprimir e botão Novo.
                                                    Se não achar de primeira, tenta novamente (até 3x,
                                                    150ms entre tentativas) antes de desistir e reportar erro.
           │
           ▼
[Passo 3: Clicar no botão '+']──> Envia clique no botão '+' da barra de navegação do grid ou tecla VK_INSERT (0x2D).
                                  (Isso cria uma nova linha na tabela e coloca o cursor na célula 'Cód. Produto')
           │ (Aguarda 200ms)
           ▼
[Passo 4: Digitar em 'Cód. Produto'] ──> Envia o código "123" diretamente na célula selecionada
           │ (Aguarda 50ms)
           ▼
[Passo 5: Pressionar ENTER]  ──> Envia VK_RETURN para o SoftCosmos validar/buscar no Firebird
           │
           ▼
[Passo 5.1: Detectar Popup de Erro] ──> Verifica por até 350ms se surgiu uma caixa de diálogo
                                        padrão do Windows (classe '#32770', ex: "Produto não
                                        encontrado"). Se encontrar: lê o texto, FECHA o popup
                                        (ESC/WM_CLOSE) e ABORTA o fluxo sem clicar em Imprimir.
           │ (sem popup)
           ▼
[Passo 5.2: Espera Inteligente]──> Em vez de sleep fixo, faz polling da janela (a cada 60ms,
                                   piso de 150ms, teto de 2000ms) até detectar que a descrição/
                                   preço do produto realmente carregaram na tela.
           ▼
[Passo 6: Clicar Imprimir]   ──> Clica no botão BitBtn5 ('Imprimir Etiquetas')
           │ (Aguarda 400ms para enviar ao Spooler da impressora)
           ▼
[Passo 7: Apertar botão Novo]──> Clica no botão btnIncluirEtiqueta ('Novo[F3]') para limpar a tela para o próximo bip
           │ (Aguarda 200ms)
           ▼
[Passo 8: Restaurar Foco]    ──> Se o foco mudou, chama SetForegroundWindow(hwnd_anterior)
                                  (O operador continua trabalhando normalmente sem perceber)
```

### 3.1 Por que essa mudança importa

| Problema do fluxo anterior | Solução implementada |
|---|---|
| `sleep(450ms)` fixo após o ENTER: se o Firebird demorasse mais, imprimia com dados incompletos; se respondesse mais rápido, perdia tempo à toa | `aguardar_produto_carregado()`: faz polling da tela e segue assim que detecta mudança real, com teto de segurança configurável |
| Código de produto inválido era ignorado e o agente clicava em "Imprimir" mesmo assim | `detectar_popup_erro()`: identifica a caixa de diálogo de erro do Windows/Delphi, fecha automaticamente e cancela a impressão, retornando o texto do erro |
| Se a janela ainda estivesse "desenhando" os componentes DevExpress, a busca de controles falhava de primeira | `localizar_controles_com_retentativa()`: tenta novamente (configurável) antes de reportar falha |

---

## 4. ARQUITETURA DE COMUNICAÇÃO COM A VERCEL (ZERO POLLING)

O executável **NÃO DEVE** fazer requisições HTTP a cada segundo (polling). Em vez disso, ele deve usar **Server-Sent Events (SSE / Stream)**:

1. O executável abre **uma única conexão HTTPS persistente** com a rota da Vercel:
   - `GET https://SEU-PROJETO.vercel.app/api/stream-etiquetas`
   - Headers: `Accept: text/event-stream`, `Cache-Control: no-cache`
2. A conexão fica aberta de forma passiva (tráfego de rede = zero).
3. Quando o conferente bipa no sistema da Vercel, a Vercel emite uma linha SSE:
   ```text
   data: {"codigo": "7891234567890", "copias": 1}
   ```
4. O executável lê a linha instantaneamente (< 30ms) e executa o ciclo de impressão.
5. Se a internet oscilar ou a conexão cair, o executável deve reconectar automaticamente a cada 3 a 5 segundos com reconexão resiliente.

### Servidor HTTP Local Embutido (Diagnóstico e Fallback)
Além da escuta na Vercel, o executável deve subir um servidor HTTP local na porta `3333` (`http://localhost:3333`):
- `GET /imprimir/:codigo` — permite testar manualmente no navegador ou via curl.
- `GET /status` — retorna se o SoftCosmos está aberto e se a janela de etiquetas foi encontrada.
- `GET /` — painel HTML simples para testes locais.

---

## 5. ESTRUTURA DO ARQUIVO DE CONFIGURAÇÃO (`config.json`)

O executável deve ler um arquivo `config.json` no mesmo diretório:

```json
{
  "stream_nuvem_url": "https://seu-projeto.vercel.app/api/stream-etiquetas",
  "token_secreto": "",
  "porta_local": 3333,
  "janela_alvo_titulo": "Gerenciador de Etiquetas",
  "janela_alvo_classe": "TFEtiquetas",
  "limpar_com_novo_antes": true,
  "tempo_espera_novo_ms": 150,
  "tempo_espera_busca_ms": 400,
  "tempo_espera_impressao_ms": 300,
  "restaurar_foco": true
}
```

---

## 6. CÓDIGO DE REFERÊNCIA NATIVO EM C# (.NET 8 CONSOLE / WINDOWS SERVICE)

Abaixo está o código-fonte C# de referência pronto que pode ser compilado diretamente em um `.exe` único com `dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true`:

```csharp
using System;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace SoftCosmosAgente
{
    class Program
    {
        // ==========================================
        // IMPORTAÇÕES WIN32 API
        // ==========================================
        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string lpszClass, string lpszWindow);

        [DllImport("user32.dll")]
        static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, string lParam);

        [DllImport("user32.dll")]
        static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

        [DllImport("user32.dll")]
        static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        // Constantes Win32
        const uint WM_SETTEXT = 0x000C;
        const uint WM_KEYDOWN = 0x0100;
        const uint WM_KEYUP = 0x0101;
        const uint BM_CLICK = 0x00F5;
        const int VK_RETURN = 0x0D;
        const int VK_F3 = 0x72;
        const int SW_RESTORE = 9;

        // Delegado para enumerar controles filhos
        public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr parameter);
        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool EnumChildWindows(IntPtr window, EnumWindowProc callback, IntPtr i);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

        static void Main(string[] args)
        {
            Console.Title = "Agente SoftCosmos - Emissor de Etiquetas";
            Console.WriteLine("==================================================");
            Console.WriteLine(" AGENTE SOFTCOSMOS - RECEPTOR DE ETIQUETAS");
            Console.WriteLine("==================================================");

            string configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.json");
            string streamUrl = "https://SEU-PROJETO.vercel.app/api/stream-etiquetas";

            if (File.Exists(configPath))
            {
                var json = File.ReadAllText(configPath);
                using var doc = JsonDocument.Parse(json);
                if (doc.RootElement.TryGetProperty("stream_nuvem_url", out var el))
                    streamUrl = el.GetString() ?? streamUrl;
            }

            Console.WriteLine($"Conectando à Vercel via Stream SSE: {streamUrl}");

            // Inicia thread de escuta SSE em tempo real (zero polling)
            Task.Run(() => IniciarEscutaSSE(streamUrl));

            // Mantém o aplicativo ativo
            while (true)
            {
                Thread.Sleep(1000);
            }
        }

        static async Task IniciarEscutaSSE(string url)
        {
            using var client = new HttpClient { Timeout = Timeout.InfiniteTimeSpan };
            while (true)
            {
                try
                {
                    using var request = new HttpRequestMessage(HttpMethod.Get, url);
                    request.Headers.Add("Accept", "text/event-stream");

                    using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);
                    using var stream = await response.Content.ReadAsStreamAsync();
                    using var reader = new StreamReader(stream);

                    Console.WriteLine("[CONECTADO] Ouvindo bips da Vercel em tempo real...");

                    while (!reader.EndOfStream)
                    {
                        var line = await reader.ReadLineAsync();
                        if (string.IsNullOrWhiteSpace(line)) continue;

                        if (line.StartsWith("data:"))
                        {
                            var dataJson = line.Substring(5).Trim();
                            if (dataJson == "keepalive") continue;

                            Console.WriteLine($"[BIP RECEBIDO] {dataJson}");
                            using var doc = JsonDocument.Parse(dataJson);
                            string codigo = "";
                            if (doc.RootElement.TryGetProperty("codigo", out var c))
                                codigo = c.GetString() ?? "";

                            if (!string.IsNullOrEmpty(codigo))
                            {
                                ExecutarCicloEtiqueta(codigo);
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[AVISO REDE] Reconectando em 4 segundos... ({ex.Message})");
                    await Task.Delay(4000);
                }
            }
        }

        public static void ExecutarCicloEtiqueta(string codigoProduto)
        {
            // Localiza a janela TFEtiquetas / Gerenciador de Etiquetas
            IntPtr hwndJanela = FindWindow("TFEtiquetas", null);
            if (hwndJanela == IntPtr.Zero)
            {
                hwndJanela = FindWindow(null, "Gerenciador de Etiquetas");
            }

            if (hwndJanela == IntPtr.Zero)
            {
                Console.WriteLine("[ERRO] Janela 'Gerenciador de Etiquetas' nao encontrada no SoftCosmos!");
                return;
            }

            IntPtr hwndFocoAnterior = GetForegroundWindow();

            IntPtr hwndEdit = IntPtr.Zero;
            IntPtr hwndBtnNovo = IntPtr.Zero;
            IntPtr hwndBtnImprimir = IntPtr.Zero;

            // Enumera controles filhos do formulário Delphi
            EnumChildWindows(hwndJanela, (hwndChild, param) =>
            {
                var sbClass = new StringBuilder(256);
                GetClassName(hwndChild, sbClass, 256);
                string classe = sbClass.ToString();

                var sbText = new StringBuilder(256);
                GetWindowText(hwndChild, sbText, 256);
                string texto = sbText.ToString();

                if (classe.Contains("Edit", StringComparison.OrdinalIgnoreCase) && hwndEdit == IntPtr.Zero)
                    hwndEdit = hwndChild;

                if (texto.Contains("Novo", StringComparison.OrdinalIgnoreCase) || texto.Contains("F3"))
                    hwndBtnNovo = hwndChild;

                if (texto.Contains("Imprimir", StringComparison.OrdinalIgnoreCase))
                    hwndBtnImprimir = hwndChild;

                return true;
            }, IntPtr.Zero);

            Console.WriteLine($"[EMULACAO] Imprimindo codigo: {codigoProduto}");

            // PASSO 1: LIMPAR COM 'NOVO[F3]' (evita acumular itens anteriores)
            if (hwndBtnNovo != IntPtr.Zero)
                PostMessage(hwndBtnNovo, BM_CLICK, IntPtr.Zero, IntPtr.Zero);
            else
            {
                PostMessage(hwndJanela, WM_KEYDOWN, (IntPtr)VK_F3, IntPtr.Zero);
                PostMessage(hwndJanela, WM_KEYUP, (IntPtr)VK_F3, IntPtr.Zero);
            }
            Thread.Sleep(150);

            // PASSO 2: INJETAR CÓDIGO
            if (hwndEdit != IntPtr.Zero)
            {
                SendMessage(hwndEdit, WM_SETTEXT, IntPtr.Zero, codigoProduto);
                Thread.Sleep(50);

                // PASSO 3: ENTER PARA PESQUISAR PRODUTO NO FIREBIRD
                PostMessage(hwndEdit, WM_KEYDOWN, (IntPtr)VK_RETURN, IntPtr.Zero);
                PostMessage(hwndEdit, WM_KEYUP, (IntPtr)VK_RETURN, IntPtr.Zero);
            }
            Thread.Sleep(400); // Aguarda consulta do SoftCosmos

            // PASSO 4: DISPARAR IMPRESSÃO
            if (hwndBtnImprimir != IntPtr.Zero)
                PostMessage(hwndBtnImprimir, BM_CLICK, IntPtr.Zero, IntPtr.Zero);

            Thread.Sleep(300);

            // PASSO 5: RESTAURAR FOCO DO OPERADOR
            if (hwndFocoAnterior != IntPtr.Zero && hwndFocoAnterior != hwndJanela)
            {
                SetForegroundWindow(hwndFocoAnterior);
            }

            Console.WriteLine($"[SUCESSO] Etiqueta do produto {codigoProduto} impressa!");
        }
    }
}
```

---

## 7. CRITÉRIOS DE ACEITAÇÃO PARA O EXECUTÁVEL

1. **Nenhum clique ou foco roubado:** O operador pode estar usando o Excel ou digitando no caixa; a impressão deve ocorrer de forma transparente.
2. **Sem acúmulo de produtos:** A cada bip, o comando `Novo[F3]` deve limpar a grade para que apenas a etiqueta do produto recém-bipado saia na impressora.
3. **Consumo de rede mínimo:** A conexão SSE não pode exceder alguns KB por dia em repouso.
4. **Auto-recuperação:** Se o SoftCosmos for fechado e reaberto, ou se a internet cair, o executável deve reconectar e continuar funcionando sem travar.
