# ESPECIFICAÇÃO DE FLUXO PARA O AGENTE DE IMPRESSÃO (SOFTCOSMOS)
> **Instrução para a IA / Desenvolvedor:** Utilize este documento como guia técnico para implementar ou ajustar o agente emulador no Windows que automatiza a impressão de etiquetas no ERP SoftCosmos.

---

## 1. OBJETIVO DO AGENTE
Quando o operador bipar um código de produto (seja via leitor de código de barras, aplicativo web ou requisição HTTP/SSE), o agente Windows deve injetar esse código no formulário de **Gerenciador de Etiquetas** do **SoftCosmos**, acionar a busca do produto, comandar a impressão e em seguida limpar a tela para a próxima bipagem, restaurando o foco original do operador.

---

## 2. JANELA ALVO NO WINDOWS
O agente deve buscar a janela ativa do módulo de etiquetas:

- **Título da Janela:** `"Gerenciador de Etiquetas"` ou contendo `"SoftCosmos"`
- **Classe da Janela (Delphi Form):** `TFEtiquetas`
- **Função Win32 para busca:**
  ```python
  hwnd = user32.FindWindowW("TFEtiquetas", None)
  # Ou enumeração via EnumWindows procurando por "Gerenciador de Etiquetas" no título
  ```

---

## 3. POR QUE O CÓDIGO CAÍA NO LUGAR ERRADO ANTES?
No topo da janela `TFEtiquetas`, existe um campo de texto comum (`TEdit`) chamado:
- **`Identificação da Impressão:`**

Se o agente simplesmente procurar pelo "primeiro Edit ativo da janela", o texto é digitado nesse campo de identificação do cabeçalho, e **não** na lista de produtos.

### O Local Correto:
O campo correto é a coluna **`* Cód. Produto`**, que fica localizada **dentro da tabela de produtos** (`TcxGrid` DevExpress, nome interno do componente: `grdItemsProd` / `grvItemsProdCodProduto`), situada logo abaixo dos botões `Catálogo de Produtos` e `Imprimir Etiquetas`.

---

## 4. MAPEAMENTO DE CONTROLES E BOTÕES DO FORMULÁRIO

| Elemento Visual | Componente Delphi Interno | Como Acessar / Disparar |
| :--- | :--- | :--- |
| **Janela de Etiquetas** | Form `TFEtiquetas` | `FindWindowW("TFEtiquetas", 0)` |
| **Grid de Itens** | `grdItemsProd` (`TcxGrid`) | `FindWindowExW(hwnd, 0, "TcxGrid", ...)` |
| **Botão `+` (Nova Linha)** | Barra de navegação inferior do Grid (`Navigator`) | Clique no botão `+` ou Tecla `VK_INSERT` (`0x2D`) |
| **Coluna `Cód. Produto`** | Célula ativa da linha criada no Grid | `SendInput` com os caracteres do código |
| **Botão `Imprimir Etiquetas`** | `BitBtn5` (`TBitBtn` / Caption: "Imprimir Etiquetas") | `PostMessageW(hwndBitBtn5, BM_CLICK, 0, 0)` |
| **Botão `Novo`** | `btnIncluirEtiqueta` (`TBitBtn` / Caption: "Novo[F3]") | `PostMessageW(hwndBtnNovo, BM_CLICK, 0, 0)` ou Tecla `VK_F3` (`0x72`) |

---

## 5. O FLUXO EXATO PASSO A PASSO (COM ESPERA INTELIGENTE E DETECÇÃO DE ERRO)

> **Por que evoluir além de "sleeps fixos"?** Depender de `time.sleep(450ms)` cravado é frágil: se o Firebird estiver mais lento num dia de pico, o agente clica em "Imprimir" com a tela ainda vazia; se estiver mais rápido, perde tempo esperando à toa. Também não existia nenhuma checagem se o código digitado era válido — um código inexistente simplesmente imprimiria uma etiqueta vazia ou travaria esperando o operador clicar "OK" numa caixa de erro que ninguém via. A versão abaixo resolve os dois problemas.

### Passo 1: Salvar a janela em uso pelo operador
```python
hwnd_anterior = user32.GetForegroundWindow()
```

### Passo 2: Localizar os controles com retentativa
Ao trazer a janela para frente, os componentes DevExpress (grid, botões) podem ainda não estar totalmente prontos para receber mensagens. Em vez de mapear uma única vez e falhar, tente novamente algumas vezes com um pequeno intervalo:
```python
def localizar_controles_com_retentativa(hwnd_janela, tentativas=3, intervalo_ms=150):
    for tentativa in range(1, tentativas + 1):
        controles = mapear_controles_filhos(hwnd_janela)
        if controles:
            return controles
        time.sleep(intervalo_ms / 1000.0)
    return mapear_controles_filhos(hwnd_janela)
```

### Passo 3: Clicar no botão `+` (Inserir nova linha na tabela)
- **Ação:** Clicar no botão `+` da barra inferior do Grid OU focar no Grid e enviar a tecla virtual **`VK_INSERT` (`0x2D`)**.
- **Resultado:** O SoftCosmos abre uma nova linha em branco e posiciona o cursor no campo **`* Cód. Produto`**.
- **Espera recomendada:** `200ms`

### Passo 4: Digitar o código em `Cód. Produto`
- **Ação:** Enviar o código via `SendInput` (ex: `"1379"`, `"123"`).
- **Espera recomendada:** `50ms`

### Passo 5: Pressionar `ENTER`
- **Ação:** Enviar a tecla **`VK_RETURN` (`0x0D`)**.
- **Resultado:** O SoftCosmos valida o código e consulta o Firebird local.

### Passo 5.1: Detectar popup de erro (NOVO)
Verifique, por uma janela curta de tempo (ex: `350ms`), se surgiu uma caixa de diálogo padrão do Windows (classe `#32770`) por cima da janela — é assim que o Delphi normalmente exibe `"Produto não encontrado"` ou `"Código inválido"`:
```python
def detectar_popup_erro(hwnd_janela_alvo, timeout_ms=350, intervalo_ms=50):
    decorrido_ms = 0
    while decorrido_ms <= timeout_ms:
        hwnd_topo = user32.GetForegroundWindow()
        if hwnd_topo and hwnd_topo != hwnd_janela_alvo:
            classe = obter_classe_janela(hwnd_topo)
            if classe == "#32770":
                texto = obter_texto_dialogo(hwnd_topo)
                fechar_janela_popup(hwnd_topo)  # ESC + WM_CLOSE
                return {"hwnd": hwnd_topo, "texto": texto}
        time.sleep(intervalo_ms / 1000.0)
        decorrido_ms += intervalo_ms
    return None
```
**Se um popup for detectado, ABORTE o fluxo aqui** — não clique em "Imprimir". Feche o popup automaticamente e retorne o texto do erro para quem chamou o agente (ex: mostrar no sistema web que o código "123" não existe).

### Passo 5.2: Espera inteligente (NOVO — substitui o `sleep` fixo)
Em vez de um tempo fixo, faça polling da tela até detectar que os dados mudaram (descrição/preço carregados), com um piso mínimo de segurança e um teto máximo:
```python
def aguardar_produto_carregado(hwnd_janela, tempo_minimo_ms=150, tempo_maximo_ms=2000, intervalo_ms=60):
    time.sleep(tempo_minimo_ms / 1000.0)
    tempo_inicial = time.time()
    assinatura_anterior = None
    while (time.time() - tempo_inicial) * 1000 < tempo_maximo_ms:
        controles_atual = mapear_controles_filhos(hwnd_janela)
        assinatura = tuple(c["titulo"] for c in controles_atual if c["titulo"])
        if assinatura_anterior is not None and assinatura != assinatura_anterior:
            time.sleep(0.05)
            return True
        assinatura_anterior = assinatura
        time.sleep(intervalo_ms / 1000.0)
    return False  # Teto atingido — segue mesmo assim como rede de seguranca
```

### Passo 6: Clicar no botão `Imprimir Etiquetas`
- **Ação:** `PostMessageW(hwndBitBtn5, BM_CLICK, 0, 0)`.
- **Espera recomendada:** `400ms` (tempo para o spooler registrar o trabalho).

### Passo 7: Clicar no botão `Novo` (Limpar para a próxima etiqueta)
- **Ação:** `PostMessageW(hwndBtnNovo, BM_CLICK, 0, 0)` ou tecla **`VK_F3` (`0x72`)**.
- **Espera recomendada:** `200ms`

### Passo 8: Restaurar o foco do operador
```python
if hwnd_anterior and hwnd_anterior != hwnd_janela:
    user32.SetForegroundWindow(hwnd_anterior)
```

---

## 6. TABELA DE TECLAS VIRTUAIS DO WINDOWS (CONSTANTES)

```python
VK_RETURN = 0x0D    # ENTER
VK_TAB    = 0x09    # TAB
VK_ESCAPE = 0x1B    # ESC (usado para fechar popups de erro)
VK_INSERT = 0x2D    # INSERT (Atalho do botão '+' do Grid)
VK_F3     = 0x72    # F3 (Atalho do botão 'Novo[F3]')
BM_CLICK  = 0x00F5  # Mensagem Win32 de clique em botão
WM_CLOSE  = 0x0010  # Mensagem Win32 para fechar uma janela/popup
```

---

## 7. RESUMO DAS MELHORIAS DE CONFIABILIDADE

| Risco no fluxo antigo | Mitigação implementada |
|---|---|
| Tempo fixo de espera após o ENTER, sem saber se os dados realmente carregaram | Polling ativo (`aguardar_produto_carregado`) com piso mínimo e teto máximo configuráveis |
| Código de produto inexistente/inválido era ignorado e a etiqueta era impressa mesmo assim | `detectar_popup_erro` identifica e fecha a caixa de diálogo do Windows, cancelando a impressão e retornando a mensagem de erro real |
| Falha ao localizar grid/botões logo após trazer a janela para frente | `localizar_controles_com_retentativa` tenta novamente antes de reportar falha |
| Erro genérico sem explicação quando a janela do SoftCosmos não estava pronta | Mensagens de retorno específicas (ex: "controles internos não localizados", "SoftCosmos recusou o código X: <texto do popup>") |

As constantes, funções e valores de configuração (`tempo_minimo_busca_ms`, `tempo_maximo_busca_ms`, `verificar_popup_erro`, `timeout_popup_erro_ms`, `tentativas_localizar_controles`) já estão implementados em `agente_emulador_softcosmos.py` e podem ser ajustados em `config_emulador.json` sem precisar recompilar o `.exe`.
