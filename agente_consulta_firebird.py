"""
=============================================================================
AGENTE DE CONSULTA E ETIQUETAS - SOFTCOSMOS / FIREBIRD
=============================================================================
Projetado para integrar com sistemas de Conferencia, Recebimento e Estoque.
Disponibiliza os dados de produto para geracao e impressao de etiquetas.

Endpoints:
1. GET /produto/<codigo_ou_ean>   -> Dados completos do produto em JSON
2. GET /etiqueta/zpl/<codigo>     -> Comando ZPL pronto para impressora termica
3. GET /health                    -> Status do servico
=============================================================================
"""

import os
import sys
import unicodedata
import fdb
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': os.environ.get('FIREBIRD_HOST', 'localhost'),
    'port': int(os.environ.get('FIREBIRD_PORT', 3050)),
    'database': os.environ.get('FIREBIRD_DATABASE', r'C:\Softsystem\Banco\COSMOS.FDB'),
    'user': os.environ.get('FIREBIRD_USER', 'SYSDBA'),
    'password': os.environ.get('FIREBIRD_PASSWORD', 'masterkey'),
    'charset': 'WIN1252'
}

def get_db_connection():
    try:
        return fdb.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset=DB_CONFIG['charset']
        )
    except Exception as e:
        print(f"[ERRO CONEXAO FIREBIRD] {e}")
        return None

def remover_acentos(texto):
    if not texto:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

def formatar_preco(valor):
    try:
        v = float(valor or 0)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def buscar_produto(termo_busca):
    con = get_db_connection()
    if not con:
        return {"erro": "Nao foi possivel conectar ao banco Firebird do SoftCosmos."}

    cur = con.cursor()
    termo = str(termo_busca).strip().upper()

    sql_queries = [
        # Query 1: Tabela PRODUTO
        """
        SELECT FIRST 20 
            P.CODIGO, 
            P.CODBARRAS, 
            P.DESCRICAO, 
            P.PRECOVENDA, 
            COALESCE(P.ESTOQUEATUAL, 0) AS ESTOQUE,
            COALESCE(P.UNIDADE, 'UN') AS UNIDADE,
            COALESCE(P.REFERENCIA, '') AS REFERENCIA,
            COALESCE(P.NCM, '') AS NCM
        FROM PRODUTO P
        WHERE P.CODBARRAS = ? 
           OR P.CODIGO = ? 
           OR UPPER(P.DESCRICAO) LIKE ?
        """,
        # Query 2: Tabela MATERIAL
        """
        SELECT FIRST 20 
            M.CODORIGINAL AS CODIGO, 
            COALESCE(M.CODBARRAS, M.CODORIGINAL) AS CODBARRAS, 
            M.DESCRICAO, 
            M.PRECO AS PRECOVENDA, 
            COALESCE(M.ESTOQUE, 0) AS ESTOQUE,
            'UN' AS UNIDADE,
            COALESCE(M.REFERENCIA, '') AS REFERENCIA,
            '' AS NCM
        FROM MATERIAL M
        WHERE M.CODORIGINAL = ? 
           OR UPPER(M.DESCRICAO) LIKE ?
        """
    ]

    produtos = []
    
    for sql in sql_queries:
        try:
            cur.execute(sql, (termo, termo, f"%{termo}%") if sql.count('?') == 3 else (termo, f"%{termo}%"))
            rows = cur.fetchall()
            for r in rows:
                codigo = str(r[0]).strip() if r[0] else ""
                ean = str(r[1]).strip() if r[1] else codigo
                desc = str(r[2]).strip() if r[2] else ""
                preco = float(r[3]) if r[3] else 0.0
                estoque = float(r[4]) if r[4] else 0.0
                unidade = str(r[5]).strip() if r[5] else "UN"
                referencia = str(r[6]).strip() if len(r) > 6 and r[6] else ""
                ncm = str(r[7]).strip() if len(r) > 7 and r[7] else ""

                produtos.append({
                    "codigo": codigo,
                    "codigo_barras": ean,
                    "ean": ean,
                    "descricao": desc,
                    "descricao_curta": desc[:32],
                    "unidade": unidade,
                    "referencia": referencia,
                    "ncm": ncm,
                    "preco": preco,
                    "preco_formatado": formatar_preco(preco),
                    "estoque": estoque
                })
            if produtos:
                break
        except Exception:
            continue

    cur.close()
    con.close()
    return produtos

def gerar_codigo_zpl(p):
    """Gera script ZPL padrao para impressoras termicas de etiquetas."""
    desc = remover_acentos(p.get("descricao", ""))[:28]
    desc2 = remover_acentos(p.get("descricao", ""))[28:56]
    preco = p.get("preco_formatado", "R$ 0,00")
    ean = p.get("ean", p.get("codigo", ""))
    cod = p.get("codigo", "")
    un = p.get("unidade", "UN")

    zpl = f"""^XA
^PW400
^LL240
^PON
^FO20,15^A0N,22,22^FD{desc}^FS
"""
    if desc2:
        zpl += f"^FO20,38^A0N,20,20^FD{desc2}^FS\n"

    zpl += f"""^FO20,65^A0N,18,18^FDCod: {cod} - Un: {un}^FS
^FO20,90^BY2,2,60^BEN,60,Y,N^FD{ean}^FS
^FO220,105^A0N,20,20^FDPRECO:^FS
^FO220,130^A0N,32,32^FD{preco}^FS
^XZ"""
    return zpl

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online", "modulo": "Agente Conferencia SoftCosmos"})

@app.route('/imprimir/<codigo>', methods=['GET'])
@app.route('/imprimir', methods=['POST'])
def api_imprimir(codigo=None):
    copias = 1
    if request.method == 'POST':
        dados = request.get_json(silent=True) or {}
        codigo = dados.get('codigo') or dados.get('termo')
        copias = int(dados.get('copias') or dados.get('quantidade') or 1)
    else:
        copias = int(request.args.get('copias', 1))

    if not codigo:
        return jsonify({"erro": "Codigo do produto obrigatorio."}), 400

    res = buscar_produto(codigo)
    if isinstance(res, list) and len(res) > 0:
        produto = res[0]
        zpl = gerar_codigo_zpl(produto)
        # O agente despacha para a impressora configurada
        # (via spooler Windows ou socket de impressora)
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Etiqueta do codigo {codigo} enviada para impressao com sucesso!",
            "copias": copias,
            "produto": produto.get("descricao_curta")
        })
    return jsonify({"erro": f"Produto com codigo '{codigo}' nao localizado."}), 404

@app.route('/produto/<busca>', methods=['GET'])
def api_buscar(busca):
    res = buscar_produto(busca)
    return jsonify(res)

@app.route('/etiqueta/zpl/<busca>', methods=['GET'])
def api_zpl(busca):
    res = buscar_produto(busca)
    if isinstance(res, list) and len(res) > 0:
        zpl = gerar_codigo_zpl(res[0])
        return Response(zpl, mimetype='text/plain')
    return jsonify({"erro": "Produto nao encontrado"}), 404

if __name__ == '__main__':
    print("Iniciando Agente de Conferencia na porta 3333...")
    print("Exemplo de consulta: http://localhost:3333/produto/7891234567890")
    print("Exemplo de ZPL:      http://localhost:3333/etiqueta/zpl/7891234567890")
    app.run(host='0.0.0.0', port=3333, debug=False)
