/**
 * AGENTE DE CONSULTA LOCAL - SOFTCOSMOS / FIREBIRD (NODE.JS)
 * ============================================================================
 * Como usar:
 * 1. Instale as dependencias:
 *    npm install node-firebird express cors
 * 
 * 2. Execute o script:
 *    node agente_consulta_node.js
 * 
 * 3. Consulte via navegador ou leitor:
 *    http://localhost:3333/produto/7891234567890
 * ============================================================================
 */

const http = require('http');
const Firebird = require('node-firebird');

// CONFIGURACOES DO BANCO DE DADOS FIREBIRD
const dbOptions = {
    host: process.env.FIREBIRD_HOST || '127.0.0.1',
    port: parseInt(process.env.FIREBIRD_PORT || '3050', 10),
    database: process.env.FIREBIRD_DATABASE || 'C:\\Softsystem\\Banco\\COSMOS.FDB',
    user: process.env.FIREBIRD_USER || 'SYSDBA',
    password: process.env.FIREBIRD_PASSWORD || 'masterkey',
    lowercase_keys: false,
    role: null,
    pageSize: 4096
};

function queryFirebird(sql, params) {
    return new Promise((resolve, reject) => {
        Firebird.attach(dbOptions, (err, db) => {
            if (err) return reject(err);
            db.query(sql, params, (queryErr, result) => {
                db.detach();
                if (queryErr) return reject(queryErr);
                resolve(result || []);
            });
        });
    });
}

async function buscarProduto(termo) {
    const termoStr = String(termo).trim();
    const termoUpper = `%${termoStr.toUpperCase()}%`;

    // Query 1: Tabela padrao PRODUTO
    const sql1 = `
        SELECT FIRST 20 
            CODIGO, 
            CODBARRAS, 
            DESCRICAO, 
            PRECOVENDA, 
            COALESCE(ESTOQUEATUAL, 0) AS ESTOQUE
        FROM PRODUTO
        WHERE CODBARRAS = ? OR CODIGO = ? OR UPPER(DESCRICAO) LIKE ?
    `;

    try {
        const rows = await queryFirebird(sql1, [termoStr, termoStr, termoUpper]);
        if (rows && rows.length > 0) {
            return rows.map(r => ({
                codigo: String(r.CODIGO || '').trim(),
                codigo_barras: String(r.CODBARRAS || '').trim(),
                descricao: String(r.DESCRICAO || '').trim(),
                preco: Number(r.PRECOVENDA || 0),
                estoque: Number(r.ESTOQUE || 0)
            }));
        }
    } catch (e) {
        // Tenta a segunda estrutura de tabela se a primeira falhar
    }

    // Query 2: Tabela MATERIAL (conforme mapeado no import .ini do SoftCosmos)
    const sql2 = `
        SELECT FIRST 20 
            CODORIGINAL AS CODIGO, 
            CODORIGINAL AS CODBARRAS, 
            DESCRICAO, 
            PRECO AS PRECOVENDA, 
            COALESCE(ESTOQUE, 0) AS ESTOQUE
        FROM MATERIAL
        WHERE CODORIGINAL = ? OR UPPER(DESCRICAO) LIKE ?
    `;

    try {
        const rows2 = await queryFirebird(sql2, [termoStr, termoUpper]);
        return (rows2 || []).map(r => ({
            codigo: String(r.CODIGO || '').trim(),
            codigo_barras: String(r.CODBARRAS || '').trim(),
            descricao: String(r.DESCRICAO || '').trim(),
            preco: Number(r.PRECOVENDA || 0),
            estoque: Number(r.ESTOQUE || 0)
        }));
    } catch (err) {
        return { erro: "Erro ao consultar banco Firebird: " + err.message };
    }
}

// Servidor HTTP simples e rapido sem precisar de frameworks pesados
const server = http.createServer(async (req, res) => {
    // Headers de CORS para permitir acesso de qualquer navegador/celular na rede
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.setHeader('Content-Type', 'application/json; charset=utf-8');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    const url = new URL(req.url, `http://${req.headers.host}`);

    if (url.pathname === '/health') {
        res.writeHead(200);
        res.end(JSON.stringify({ status: "online", motor: "Node.js Firebird Agent" }));
        return;
    }

    if (url.pathname.startsWith('/produto/')) {
        const busca = decodeURIComponent(url.pathname.replace('/produto/', ''));
        try {
            const produtos = await buscarProduto(busca);
            res.writeHead(200);
            res.end(JSON.stringify(produtos));
        } catch (err) {
            res.writeHead(500);
            res.end(JSON.stringify({ erro: err.message }));
        }
        return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ erro: "Rota nao encontrada. Use /produto/<codigo_ou_nome>" }));
});

const PORT = 3333;
server.listen(PORT, '0.0.0.0', () => {
    console.log(`[Agente SoftCosmos] Servidor ouvindo em http://localhost:${PORT}`);
    console.log(`[Exemplo de teste]: http://localhost:${PORT}/produto/7891234567890`);
});
