// =============================================================================
// EXEMPLO DE ROTA PARA SEU PROJETO NA VERCEL (Next.js App Router)
// Salve este arquivo no seu projeto da Vercel em:
// app/api/fila-etiquetas/route.ts
// =============================================================================

import { NextRequest, NextResponse } from "next/server";

export interface ItemEtiqueta {
  id: string;
  codigo: string;
  copias: number;
  criadoEm: number;
  status: "pendente" | "imprimindo" | "concluido";
}

// Fila em memoria compartilhada (para alto volume ou persistencia duravel, 
// voce pode salvar em uma tabela simples no Supabase, Neon ou KV)
const filaEtiquetas: ItemEtiqueta[] = [];

// Chave secreta de autenticacao (opcional, configurada no config_emulador.json)
const TOKEN_SECRETO = process.env.ETIQUETAS_TOKEN_SECRETO || "sua-chave-secreta-123";

/**
 * 1. GET /api/fila-etiquetas
 * O agente .bat rodando no seu computador consulta essa rota a cada 1.5s
 * buscando novas etiquetas para imprimir no SoftCosmos.
 */
export async function GET(req: NextRequest) {
  // Verificacao de seguranca opcional
  const authHeader = req.headers.get("authorization");
  if (TOKEN_SECRETO && authHeader !== `Bearer ${TOKEN_SECRETO}`) {
    return NextResponse.json({ erro: "Nao autorizado" }, { status: 401 });
  }

  // Pega apenas as etiquetas que estao pendentes
  const pendentes = filaEtiquetas.filter((item) => item.status === "pendente");

  // Marca como 'imprimindo' para evitar impressao duplicada
  pendentes.forEach((item) => {
    item.status = "imprimindo";
  });

  return NextResponse.json(pendentes);
}

/**
 * 2. POST /api/fila-etiquetas
 * O seu sistema de conferencia chama essa rota quando bipa ou seleciona um produto.
 * Exemplo de corpo JSON: { "codigo": "123", "copias": 1 }
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const codigo = String(body.codigo || body.ean || body.termo || "").trim();
    const copias = Math.max(1, parseInt(body.copias || 1, 10));

    if (!codigo) {
      return NextResponse.json(
        { erro: "O campo 'codigo' e obrigatorio." },
        { status: 400 }
      );
    }

    const novoItem: ItemEtiqueta = {
      id: "etiq_" + Date.now() + "_" + Math.random().toString(36).substring(2, 7),
      codigo: codigo,
      copias: copias,
      criadoEm: Date.now(),
      status: "pendente",
    };

    // Adiciona na fila para o SoftCosmos imprimir
    filaEtiquetas.push(novoItem);

    // Mantem apenas os ultimos 100 registros na memoria para economizar recursos
    if (filaEtiquetas.length > 100) {
      filaEtiquetas.splice(0, filaEtiquetas.length - 100);
    }

    return NextResponse.json({
      sucesso: true,
      mensagem: `Etiqueta do codigo ${codigo} enfileirada com sucesso! O SoftCosmos ira imprimir nos proximos segundos.`,
      item: novoItem,
    });
  } catch (error: any) {
    return NextResponse.json(
      { erro: "Erro ao processar solicitacao", detalhes: error.message },
      { status: 500 }
    );
  }
}

/**
 * 3. PATCH /api/fila-etiquetas
 * Ou rota /api/fila-etiquetas/concluir:
 * Chamada pelo agente quando a impressao e concluida com sucesso.
 */
export async function PATCH(req: NextRequest) {
  try {
    const body = await req.json();
    const id = body.id;
    const item = filaEtiquetas.find((i) => i.id === id);
    if (item) {
      item.status = "concluido";
    }
    return NextResponse.json({ sucesso: true });
  } catch {
    return NextResponse.json({ sucesso: false }, { status: 400 });
  }
}

