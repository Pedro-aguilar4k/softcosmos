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

## 5. O FLUXO EXATO PASSO A PASSO (6 ETAPAS)

### Passo 1: Salvar a janela em uso pelo operador
Para não atrapalhar o operador de caixa ou estoquista:
```python
hwnd_anterior = user32.GetForegroundWindow()
```

### Passo 2: Clicar no botão `+` (Inserir nova linha na tabela)
Na parte inferior do Grid de produtos há uma barra com os botões `|<`, `<`, `>`, `>|`, `+`, `-`.
- **Ação:** Clicar no botão `+` da barra inferior OU focar no Grid e enviar a tecla virtual **`VK_INSERT` (`0x2D`)**.
- **Resultado:** O SoftCosmos abre uma nova linha em branco na tabela e posiciona automaticamente o cursor no campo **`* Cód. Produto`**.
- **Espera recomendada:** `200ms`

### Passo 3: Digitar o código em `Cód. Produto`
Com a célula `Cód. Produto` em edição:
- **Ação:** Enviar o código numérico do produto via `SendInput` (ex: `"1379"`, `"123"`).
- **Espera recomendada:** `50ms`

### Passo 4: Pressionar `ENTER`
- **Ação:** Enviar a tecla **`VK_RETURN` (`0x0D`)**.
- **Resultado:** O SoftCosmos valida o código digitado, consulta o banco Firebird local e preenche automaticamente as demais colunas: `Descrição do Produto`, `Lote`, `Quantidade`, `Preço`, etc.
- **Espera recomendada:** `400ms a 450ms` (tempo necessário para o Firebird retornar os dados do produto).

### Passo 5: Clicar no botão `Imprimir Etiquetas`
- **Ação:** Acionar o clique no botão `Imprimir Etiquetas` (`BitBtn5`) via mensagem `BM_CLICK` (`0x00F5`).
- **Resultado:** O SoftCosmos envia os comandos de impressão da etiqueta selecionada diretamente para a impressora térmica configurada (Zebra, Argox, Elgin, etc.).
- **Espera recomendada:** `400ms` (tempo para o spooler registrar o trabalho).

### Passo 6: Clicar no botão `Novo` (Limpar para a próxima etiqueta)
- **Ação:** Acionar o botão `Novo` (`btnIncluirEtiqueta`) via mensagem `BM_CLICK` OU enviar a tecla **`VK_F3` (`0x72`)**.
- **Resultado:** O SoftCosmos limpa o Grid de itens. Assim, quando o operador bipar o próximo produto, a tela estará 100% limpa, evitando acumular produtos de impressões anteriores.
- **Espera recomendada:** `200ms`

### Passo 7: Restaurar o foco do operador
```python
if hwnd_anterior and hwnd_anterior != hwnd_janela:
    user32.SetForegroundWindow(hwnd_anterior)
```

---

## 6. TABELA DE TECLAS VIRTUAIS DO WINDOWS (CONSTANTES)

```python
VK_RETURN = 0x0D   # ENTER
VK_TAB    = 0x09   # TAB
VK_INSERT = 0x2D   # INSERT (Atalho do botão '+' do Grid)
VK_F3     = 0x72   # F3 (Atalho do botão 'Novo[F3]')
BM_CLICK  = 0x00F5 # Mensagem Win32 de clique em botão
```

---

## 7. EXEMPLO DE IMPLEMENTAÇÃO PRONTA (PYTHON WIN32)

```python
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
BM_CLICK = 0x00F5
VK_RETURN = 0x0D
VK_INSERT = 0x2D
VK_F3 = 0x72

def imprimir_etiqueta_softcosmos(codigo_produto: str):
    # 1. Localiza a janela do Gerenciador de Etiquetas
    hwnd = user32.FindWindowW("TFEtiquetas", None)
    if not hwnd:
        raise Exception("Janela TFEtiquetas (Gerenciador de Etiquetas) não está aberta.")

    # Salva o foco atual do operador
    hwnd_anterior = user32.GetForegroundWindow()

    # Traz a janela para foco temporário
    user32.ShowWindow(hwnd, 9) # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.08)

    # PASSO 1: Clica no '+' (ou envia VK_INSERT para abrir nova linha no grid)
    enviar_tecla(VK_INSERT)
    time.sleep(0.20)

    # PASSO 2: Digita o código no campo 'Cód. Produto'
    digitar_texto(codigo_produto)
    time.sleep(0.05)

    # PASSO 3: Pressiona ENTER para carregar o produto do Firebird
    enviar_tecla(VK_RETURN)
    time.sleep(0.45)

    # PASSO 4: Clica em 'Imprimir Etiquetas'
    # Pode localizar o botão BitBtn5 ou enviar foco + ENTER
    btn_imprimir = localizar_botao(hwnd, "imprimir")
    if btn_imprimir:
        user32.PostMessageW(btn_imprimir, BM_CLICK, 0, 0)
    else:
        enviar_tecla(VK_RETURN)
    time.sleep(0.40)

    # PASSO 5: Clica no botão 'Novo' (F3) para limpar a tela
    btn_novo = localizar_botao(hwnd, "novo")
    if btn_novo:
        user32.PostMessageW(btn_novo, BM_CLICK, 0, 0)
    else:
        enviar_tecla(VK_F3)
    time.sleep(0.20)

    # PASSO 6: Devolve o foco imediatamente para a tela do operador
    if hwnd_anterior and hwnd_anterior != hwnd:
        user32.SetForegroundWindow(hwnd_anterior)
```
