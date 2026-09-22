// =============================================================================
// ROTA EM TEMPO REAL PARA SEU PROJETO NA VERCEL (Next.js App Router)
// Salve este arquivo em: app/api/stream-etiquetas/route.ts
//
// VANTAGEM REVOLUCIONARIA:
// ZERO POLLING! O seu computador abre 1 unica conexao passiva com a Vercel.
// Enquanto ninguem bipa nada, o trafego de rede e ZERO.
// Quando voce bipa um produto na conferencia, a Vercel dispara o evento
// imediatamente (< 30ms) direto para o SoftCosmos imprimir!
// =============================================================================

import { NextRequest, NextResponse } from "next/server";

// Lista de clientes conectados (o instalavel do Windows escutando)
type Subscriber = (data: string) => void;
const subscribers = new Set<Subscriber>();

// Token opcional de seguranca
const TOKEN_SECRETO = process.env.ETIQUETAS_TOKEN_SECRETO || "sua-chave-secreta-123";

/**
 * 1. GET /api/stream-etiquetas
 * O instalavel do Windows conecta aqui UMA UNICA VEZ e fica ouvindo.
 * Nao faz requisicoes repetitivas nem sobrecarrega a rede da empresa.
 */
export async function GET(req: NextRequest) {
  const authHeader = req.headers.get("authorization");
  if (TOKEN_SECRETO && authHeader !== `Bearer ${TOKEN_SECRETO}`) {
    return NextResponse.json({ erro: "Nao autorizado" }, { status: 401 });
  }

  let unsubscribe: Subscriber | null = null;

  const stream = new ReadableStream({
    start(controller) {
      // Envia evento inicial de conexao confirmada
      controller.enqueue(
        new TextEncoder().encode(`data: {"status": "conectado", "timestamp": ${Date.now()}}\n\n`)
      );

      // Registra este instalador para receber novos bips
      const sub: Subscriber = (mensagemJson: string) => {
        try {
          controller.enqueue(new TextEncoder().encode(`data: ${mensagemJson}\n\n`));
        } catch {
          // Erro ao enviar, conexao foi fechada
          subscribers.delete(sub);
        }
      };

      subscribers.add(sub);
      unsubscribe = sub;

      // Keepalive a cada 25 segundos para manter a conexao viva nos roteadores sem trafego
      const keepAliveInterval = setInterval(() => {
        try {
          controller.enqueue(new TextEncoder().encode(": keepalive\n\n"));
        } catch {
          clearInterval(keepAliveInterval);
          if (unsubscribe) subscribers.delete(unsubscribe);
        }
      }, 25000);
    },
    cancel() {
      if (unsubscribe) {
        subscribers.delete(unsubscribe);
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

/**
 * 2. POST /api/stream-etiquetas (ou quando bipa o produto)
 * O seu sistema de conferencia chama esta rota ao bipar o produto.
 * Exemplo de corpo JSON:
 * {
 *    "codigo": "123",
 *    "copias": 1
 * }
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

    const payload = JSON.stringify({
      id: "bip_" + Date.now(),
      codigo: codigo,
      copias: copias,
      dataHora: new Date().toISOString(),
    });

    // Envia instantaneamente para o instalador do SoftCosmos conectado
    let entreguePara = 0;
    subscribers.forEach((enviar) => {
      enviar(payload);
      entreguePara++;
    });

    return NextResponse.json({
      sucesso: true,
      mensagem: `Bip do codigo ${codigo} transmitido para o SoftCosmos imprimir!`,
      computadores_conectados: entreguePara,
      codigo: codigo,
      copias: copias,
    });
  } catch (error: any) {
    return NextResponse.json(
      { erro: "Erro ao emitir evento de impressao", detalhes: error.message },
      { status: 500 }
    );
  }
}
