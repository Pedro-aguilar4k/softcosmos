"""
=============================================================================
AGENTE DE CONSULTA LOCAL - SOFTCOSMOS / FIREBIRD
=============================================================================
Este script roda em segundo plano no computador onde o SoftCosmos esta aberto.
Ele se conecta ao banco Firebird local e disponibiliza:
1. Uma mini API HTTP local (http://localhost:3333/produto/<termo>)
2. Um modo de consulta rapida no terminal (bipando leitor ou digitando)
=============================================================================
Instalacao dos requisitos:
  pip install fdb flask flask-cors
=============================================================================
Como rodar:
  python agente_consulta_firebird.py
=============================================================================
"""

import os
import sys
import fdb
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# CONFIGURACOES DO BANCO DE DADOS FIREBIRD LOCAL
# O SoftCosmos tipicamente utiliza o Firebird 2.5 ou 3.0 na porta 3050
DB_CONFIG = {
    'host': os.environ.get('FIREBIRD_HOST', 'localhost'),
    'port': int(os.environ.get('FIREBIRD_PORT', 3050)),
    # Altere para o caminho real do arquivo .fdb ou .gdb no seu computador/servidor
    'database': os.environ.get('FIREBIRD_DATABASE', r'C:\Softsystem\Banco\COSMOS.FDB'),
    'user': os.environ.get('FIREBIRD_USER', 'SYSDBA'),
    'password': os.environ.get('FIREBIRD_PASSWORD', 'masterkey'),
    'charset': 'WIN1252'
}

def get_db_connection():
    """Cria uma conexao direta somente leitura com o Firebird."""
    try:
        con = fdb.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset=DB_CONFIG['charset']
        )
        return con
    except Exception as e:
        print(f"[ERRO DE CONEXAO FIREBIRD] {e}")
        return None

def buscar_produto(termo_busca):
    """
    Realiza busca por:
    - Codigo de barras (EAN)
    - Codigo interno (CODORIGINAL / CODIGO)
    - Descricao / Nome do produto
    """
    con = get_db_connection()
    if not con:
        return {"erro": "Nao foi possivel conectar ao banco Firebird do SoftCosmos. Verifique se o caminho do .fdb esta correto."}

    cur = con.cursor()
    termo = str(termo_busca).strip().upper()

    # Query generica adaptavel aos campos padrao do SoftCosmos (PRODUTO / MATERIAL)
    # Testa primeiro na tabela PRODUTO, com fallback para MATERIAL
    sql_queries = [
        # Query 1: Formato padrao tabela PRODUTO
        """
        SELECT FIRST 20 
            P.CODIGO, 
            P.CODBARRAS, 
            P.DESCRICAO, 
            P.PRECOVENDA, 
            COALESCE(P.ESTOQUEATUAL, 0) AS ESTOQUE,
            P.UNIDADE
        FROM PRODUTO P
        WHERE P.CODBARRAS = ? 
           OR P.CODIGO = ? 
           OR UPPER(P.DESCRICAO) LIKE ?
        """,
        # Query 2: Formato identificado no arquivo ImportCadProd_DemoExcel.ini (MATERIAL)
        """
        SELECT FIRST 20 
            M.CODORIGINAL AS CODIGO, 
            COALESCE(M.CODBARRAS, M.CODORIGINAL) AS CODBARRAS, 
            M.DESCRICAO, 
            M.PRECO AS PRECOVENDA, 
            COALESCE(M.ESTOQUE, 0) AS ESTOQUE,
            'UN' AS UNIDADE
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
                produtos.append({
                    "codigo": str(r[0]).strip() if r[0] else "",
                    "codigo_barras": str(r[1]).strip() if r[1] else "",
                    "descricao": str(r[2]).strip() if r[2] else "",
                    "preco": float(r[3]) if r[3] else 0.0,
                    "estoque": float(r[4]) if r[4] else 0.0,
                    "unidade": str(r[5]).strip() if r[5] else "UN"
                })
            if produtos:
                break
        except Exception as query_err:
            # Tenta a proxima estrutura de tabela
            continue

    cur.close()
    con.close()
    return produtos

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "servico": "Agente Local SoftCosmos",
        "banco": DB_CONFIG['database']
    })

@app.route('/produto/<busca>', methods=['GET'])
def api_buscar(busca):
    resultado = buscar_produto(busca)
    return jsonify(resultado)

@app.route('/api/busca', methods=['POST'])
def api_busca_post():
    dados = request.get_json() or {}
    termo = dados.get('termo', '')
    if not termo:
        return jsonify({"erro": "Termo de busca nao informado"}), 400
    resultado = buscar_produto(termo)
    return jsonify(resultado)

def modo_terminal():
    """Permite bipar com leitor de codigo de barras direto no console."""
    print("=" * 60)
    print("MODO DE CONSULTA RAPIDA NO TERMINAL ATIVO")
    print("Bipe o codigo de barras ou digite o nome do produto e aperte ENTER.")
    print("Pressione CTRL+C para sair.")
    print("=" * 60)
    
    while True:
        try:
            termo = input("\n[Bipe ou digite o produto]: ").strip()
            if not termo:
                continue
            resultados = buscar_produto(termo)
            if isinstance(resultados, dict) and 'erro' in resultados:
                print(f"-> {resultados['erro']}")
            elif not resultados:
                print(f"-> Nenhum produto encontrado para: '{termo}'")
            else:
                for p in resultados:
                    print(f"-> COD: {p['codigo']} | EAN: {p['codigo_barras']}")
                    print(f"   {p['descricao']}")
                    print(f"   PRECO: R$ {p['preco']:.2f} | ESTOQUE: {p['estoque']} {p['unidade']}")
                    print("-" * 40)
        except KeyboardInterrupt:
            print("\nEncerrando...")
            break

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        modo_terminal()
    else:
        print("Iniciando Agente Local SoftCosmos na porta 3333...")
        print("Acesse: http://localhost:3333/produto/7891234567890")
        app.run(host='0.0.0.0', port=3333, debug=False)
