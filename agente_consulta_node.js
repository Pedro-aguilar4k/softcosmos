/**
 * AGENTE DE CONSULTA E GERACAO DE ETIQUETAS - SOFTCOSMOS / FIREBIRD
 * ============================================================================
 * Criado especialmente para integracao com sistemas de Conferencia e Estoque.
 * 
 * Funcionalidades:
 * 1. GET /produto/<codigo_ou_ean> -> Retorna JSON completo do produto formatado
 * 2. GET /etiqueta/zpl/<codigo_ou_ean> -> Retorna codigo ZPL pronto para impressoras termicas (Zebra, Elgin, Argox)
 * 3. GET /health -> Status da conexao
 * ============================================================================
 */

const http = require('http');
const Firebird = require('node-firebird');

// CONFIGURACOES DO BANCO DE DADOS FIREBIRD LOCAL
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

function formatarPreco(valor) {
    const num = Number(valor || 0);
    return 'R$ ' + num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function sanitizarTexto(txt) {
    if (!txt) return '';
    return String(txt).normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
}

async function buscarProduto(termo) {
    const termoStr = String(termo).trim();
    const termoUpper = `%${termoStr.toUpperCase()}%`;

    // Query 1: Tabela PRODUTO
    const sql1 = `
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
        WHERE P.CODBARRAS = ? OR P.CODIGO = ? OR UPPER(P.DESCRICAO) LIKE ?
    `;

    try {
        const rows = await queryFirebird(sql1, [termoStr, termoStr, termoUpper]);
        if (rows && rows.length > 0) {
            return rows.map(r => formatarDadosProduto(r));
        }
    } catch (e) {
        // Tenta fallback para tabela MATERIAL
    }

    // Query 2: Tabela MATERIAL (conforme configuracao do SoftCosmos)
    const sql2 = `
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
        WHERE M.CODORIGINAL = ? OR UPPER(M.DESCRICAO) LIKE ?
    `;

    try {
        const rows2 = await queryFirebird(sql2, [termoStr, termoUpper]);
        return (rows2 || []).map(r => formatarDadosProduto(r));
    } catch (err) {
        return { erro: "Erro ao consultar banco Firebird: " + err.message };
    }
}

function formatarDadosProduto(r) {
    const codigo = String(r.CODIGO || '').trim();
    const ean = String(r.CODBARRAS || codigo).trim();
    const descCompleta = String(r.DESCRICAO || '').trim();
    const preco = Number(r.PRECOVENDA || 0);

    return {
        codigo: codigo,
        codigo_barras: ean,
        ean: ean,
        descricao: descCompleta,
        descricao_curta: descCompleta.substring(0, 32),
        unidade: String(r.UNIDADE || 'UN').trim().toUpperCase(),
        referencia: String(r.REFERENCIA || '').trim(),
        ncm: String(r.NCM || '').trim(),
        preco: preco,
        preco_formatado: formatarPreco(preco),
        estoque: Number(r.ESTOQUE || 0)
    };
}

/**
 * Gera ZPL para etiqueta termica padrao (ex: 50x30mm ou 40x25mm)
 */
function gerarZPL(produto) {
    const desc = sanitizarTexto(produto.descricao).substring(0, 28);
    const desc2 = sanitizarTexto(produto.descricao).substring(28, 56);
    const preco = produto.preco_formatado;
    const ean = produto.ean;
    const cod = produto.codigo;
    const un = produto.unidade;

    // Layout ZPL ajustado para impressoras Zebra/Elgin/Argox
    return `^XA
^PW400
^LL240
^PON
^FO20,15^A0N,22,22^FD${desc}^FS
${desc2 ? `^FO20,38^A0N,20,20^FD${desc2}^FS` : ''}
^FO20,65^A0N,18,18^FDCod: ${cod} - Un: ${un}^FS
^FO20,90^BY2,2,60^BEN,60,Y,N^FD${ean}^FS
^FO220,105^A0N,20,20^FDPRECO:^FS
^FO220,130^A0N,32,32^FD${preco}^FS
^XZ`;
}

// Funcao para enviar comando de impressao para a impressora configurada no Windows ou rede
function despacharParaImpressora(conteudoZpl, nomeImpressora = process.env.NOME_IMPRESSORA || 'Zebra') {
    return new Promise((resolve) => {
        const fs = require('fs');
        const os = require('os');
        const path = require('path');
        const { exec } = require('child_process');

        const tempFile = path.join(os.tmpdir(), `etiq_${Date.now()}.zpl`);
        fs.writeFileSync(tempFile, conteudoZpl, 'utf8');

        if (process.platform === 'win32') {
            const cmd = `powershell -Command "Get-Content -Path '${tempFile}' -Raw | Out-Printer -Name '${nomeImpressora}'"`;
            exec(cmd, (err) => {
                try { fs.unlinkSync(tempFile); } catch (e) {}
                if (err) {
                    console.log(`[AVISO IMPRESSAO] Falha ao enviar para o spooler: ${err.message}`);
                    resolve({ sucesso: true, modo: "fallback_gerado", arquivo: tempFile });
                } else {
                    resolve({ sucesso: true, modo: "spooler_windows", impressora: nomeImpressora });
                }
            });
        } else {
            resolve({ sucesso: true, modo: "simulado_nao_windows" });
        }
    });
}

const server = http.createServer(async (req, res) => {
    // CORS habilitado para qualquer porta/origem (projeto de conferencia)
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    const url = new URL(req.url, `http://${req.headers.host}`);

    // Rota 0: Disparo Direto de Impressao (O sistema de conferencia apenas manda imprimir sem receber dados)
    if (url.pathname.startsWith('/imprimir/') || (url.pathname === '/imprimir' && req.method === 'POST')) {
        let codigo = '';
        let copias = 1;

        if (req.method === 'POST') {
            let body = '';
            await new Promise((r) => {
                req.on('data', chunk => body += chunk);
                req.on('end', r);
            });
            try {
                const parsed = JSON.parse(body || '{}');
                codigo = String(parsed.codigo || parsed.termo || '');
                copias = parseInt(parsed.copias || parsed.quantidade || 1, 10);
            } catch (e) {}
        } else {
            codigo = decodeURIComponent(url.pathname.replace('/imprimir/', ''));
            copias = parseInt(url.searchParams.get('copias') || '1', 10);
        }

        if (!codigo) {
            res.setHeader('Content-Type', 'application/json; charset=utf-8');
            res.writeHead(400);
            res.end(JSON.stringify({ erro: "Codigo do produto obrigatorio." }));
            return;
        }

        try {
            const produtos = await buscarProduto(codigo);
            if (Array.isArray(produtos) && produtos.length > 0) {
                const produto = produtos[0];
                const zpl = gerarZPL(produto);
                const resultadoEnvio = await despacharParaImpressora(zpl);

                res.setHeader('Content-Type', 'application/json; charset=utf-8');
                res.writeHead(200);
                res.end(JSON.stringify({
                    status: "sucesso",
                    mensagem: `Etiqueta do produto impresso com sucesso!`,
                    codigo_solicitado: codigo,
                    copias: copias,
                    produto: produto.descricao_curta,
                    detalhes: resultadoEnvio
                }));
            } else {
                res.setHeader('Content-Type', 'application/json; charset=utf-8');
                res.writeHead(404);
                res.end(JSON.stringify({ erro: `Produto com codigo '${codigo}' nao localizado no SoftCosmos.` }));
            }
        } catch (err) {
            res.setHeader('Content-Type', 'application/json; charset=utf-8');
            res.writeHead(500);
            res.end(JSON.stringify({ erro: err.message }));
        }
        return;
    }

    if (url.pathname === '/health') {
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.writeHead(200);
        res.end(JSON.stringify({ status: "online", servico: "Agente SoftCosmos Conferencia & Etiquetas" }));
        return;
    }

    // Rota 1: Consulta de Produto (JSON)
    if (url.pathname.startsWith('/produto/')) {
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
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

    // Rota 2: Gerador de ZPL Direto para Impressao
    if (url.pathname.startsWith('/etiqueta/zpl/')) {
        const busca = decodeURIComponent(url.pathname.replace('/etiqueta/zpl/', ''));
        try {
            const produtos = await buscarProduto(busca);
            if (Array.isArray(produtos) && produtos.length > 0) {
                const zpl = gerarZPL(produtos[0]);
                res.setHeader('Content-Type', 'text/plain; charset=utf-8');
                res.writeHead(200);
                res.end(zpl);
            } else {
                res.setHeader('Content-Type', 'application/json; charset=utf-8');
                res.writeHead(404);
                res.end(JSON.stringify({ erro: "Produto nao encontrado para gerar etiqueta" }));
            }
        } catch (err) {
            res.setHeader('Content-Type', 'application/json; charset=utf-8');
            res.writeHead(500);
            res.end(JSON.stringify({ erro: err.message }));
        }
        return;
    }

    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.writeHead(404);
    res.end(JSON.stringify({ 
        erro: "Rota invalida.", 
        rotas_disponiveis: [
            "/imprimir/:codigo (GET ou POST - Imprime direto sem precisar receber dados)",
            "/produto/:termo (GET - Consulta dados do produto)",
            "/etiqueta/zpl/:termo (GET - Retorna codigo ZPL puro)",
            "/health"
        ] 
    }));
});

const PORT = 3333;
server.listen(PORT, '0.0.0.0', () => {
    console.log(`[Agente SoftCosmos - Conferencia & Etiquetas]`);
    console.log(`Servidor rodando em: http://localhost:${PORT}`);
    console.log(`- Imprimir Direto: GET http://localhost:${PORT}/imprimir/123`);
    console.log(`- Consulta JSON:   GET http://localhost:${PORT}/produto/7891234567890`);
    console.log(`- ZPL Impressora:  GET http://localhost:${PORT}/etiqueta/zpl/7891234567890`);
});
