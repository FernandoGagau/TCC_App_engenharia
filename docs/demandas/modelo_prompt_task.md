# Prompt: Integração Upstash Vector + Base de Conhecimento para AI Chat

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, frontend, database, auth).
- Siga os guias: agents/architecture-planning.md, agents/backend-development.md, agents/frontend-development.md, agents/database-development.md, agents/security-check.md.

Objetivo
- Integrar o Upstash Vector como base de conhecimento (RAG) para o AI Chat.
- Permitir que o painel Admin gerencie a base (CRUD, reindexação) e, a cada solicitação do usuário, injetar contexto relevante recuperado do Upstash Vector no prompt do chat.

Escopo
- Multi‑tenant: isolar dados por usuário e/ou workspace (sem vazamento entre locatários).
- Ingestão: criar/atualizar/excluir entradas e fragmentos (chunking), gerar embeddings e upsert no Upstash Vector.
- Recuperação: ao iniciar uma requisição de chat, buscar K fragmentos relevantes e injetar no prompt.
- Admin UI: páginas em /admin para gestão da base.
- Observabilidade: logs mínimos (sem dados sensíveis), métricas básicas.

Requisitos de Configuração
- Variáveis de ambiente (adicione em .env.local):
  - UPSTASH_VECTOR_REST_URL
  - UPSTASH_VECTOR_REST_TOKEN
  - OPENAI_API_KEY (ou outro provedor via Vercel AI SDK para embeddings)
- Dependência: `npm i @upstash/vector` (SDK TS).
- Documentação de referência:
  - Upstash Vector (overview): https://upstash.com/docs/vector/overall/getstarted
  - Upstash Vector TS SDK: https://upstash.com/docs/vector/sdks/ts/getting-started

Arquitetura de Alto Nível
- Admin (CRUD): cria registros “KnowledgeBaseEntry” no Prisma e dispara pipeline de indexação (chunk → embed → upsert Upstash Vector).
- Storage: conteúdo em texto no DB; anexos (opcional) reutilizam uploads existentes (docs/uploads.md) e são transcriptados/extraídos conforme necessidade.
- Retrieving no Chat: antes de chamar o provedor (streamText), gerar embedding da entrada do usuário, consultar o Upstash Vector filtrando por tenant e injetar no prompt como contexto.

Modelagem de Dados (Proposta Prisma)
- KnowledgeBaseEntry: { id, userId?, workspaceId?, title, content (Text), tags (String[]), status ('active'|'draft'), updatedAt }
- KnowledgeChunk: { id, entryId, ordinal, content (Text), tokens?, updatedAt }
- Observação: chunking no servidor (ex.: 500–800 tokens). Evite campos com dados sensíveis.

APIs (Propostas)
- POST /api/admin/knowledge: criar entrada (Zod), retorna entryId. Dispara indexação assíncrona (ou síncrona simples para MVP).
- PUT /api/admin/knowledge/:id: atualizar e reindexar.
- DELETE /api/admin/knowledge/:id: remover entrada e deletar vetores no Upstash (por metadata/ids).
- POST /api/admin/knowledge/:id/reindex: reprocessar chunks.
- GET /api/admin/knowledge: listar entradas com paginação, filtros, busca textual.
- Segurança: somente admin (middleware + verificação server‑side). Validar tenancy (user/workspace) em todos os acessos.

Biblioteca de Integração (Server‑only)
- Arquivo sugerido: src/lib/knowledge/upstash.ts
- Responsabilidades:
  - index = new Index({ url: UPSTASH_VECTOR_REST_URL, token: UPSTASH_VECTOR_REST_TOKEN })
  - upsertChunks({ tenantKey, entryId, chunks, vectorProvider }): gera embeddings (ai + @ai-sdk/openai) e faz index.upsert
  - queryRelevant({ tenantKey, text, topK }): gera embedding da consulta e chama index.query com filtro por tenant/entry status
  - deleteByEntry({ tenantKey, entryId }): remove todos os vetores de uma entrada

Exemplo de Código (SDK TS + Vercel AI)
```ts
// src/lib/knowledge/upstash.ts (esqueleto)
import { Index } from '@upstash/vector'
import { embedMany } from 'ai'
import { openai } from '@ai-sdk/openai'

const index = new Index({
  url: process.env.UPSTASH_VECTOR_REST_URL!,
  token: process.env.UPSTASH_VECTOR_REST_TOKEN!,
})

type TenantKey = { userId?: string; workspaceId?: string }

export async function upsertChunks({ tenant, entryId, chunks }: {
  tenant: TenantKey
  entryId: string
  chunks: { id: string; content: string; ordinal: number }[]
}) {
  const { embeddings } = await embedMany({
    model: openai.embedding('text-embedding-3-small'),
    values: chunks.map(c => c.content),
  })
  const vectors = chunks.map((c, i) => ({
    id: `${entryId}:${c.ordinal}`,
    vector: embeddings[i],
    metadata: { entryId, ordinal: c.ordinal, ...tenant, status: 'active' },
  }))
  await index.upsert(vectors)
}

export async function queryRelevant({ tenant, text, topK = 5 }: {
  tenant: TenantKey
  text: string
  topK?: number
}) {
  const { embeddings } = await embedMany({
    model: openai.embedding('text-embedding-3-small'),
    values: [text],
  })
  const vector = embeddings[0]
  // Filtragem por tenant e status
  const res = await index.query({ topK, vector, filter: { ...tenant, status: 'active' } })
  return res
}
```

Injeção no AI Chat (RAG)
- Local de integração: src/app/api/ai/chat/route.ts
- Passos:
  1) Obter tenant (userId/workspaceId) via Clerk.
  2) Gerar embedding da última mensagem do usuário.
  3) `queryRelevant({ tenant, text, topK: 5 })` e consolidar contexto (ex.: juntar topK, limitar 1500–2000 tokens).
  4) Injetar contexto no prompt como system/context preamble, ex.:
     "Use o contexto abaixo somente se pertinente. Se irrelevante, ignore.\n<context>...trechos...</context>"
  5) Dar continuidade ao fluxo atual (validação/débito de créditos, streamText, etc.).
- Observação: se não houver resultados, prossiga normalmente sem contexto.

Admin UI (MVP)
- Rota: src/app/(protected)/admin/knowledge
- Páginas:
  - Listagem: tabela com busca/ordenação/status, ações (editar, reindexar, excluir).
  - Formulário: título, tags, conteúdo (textarea/MD); validação Zod; botão “Salvar e Indexar”.
  - Reindexação: ação dedicada; feedback via toasts e estado (loading/success/error).
- Regras: somente admins; paginar; confirmar exclusão com dialog; exibir contagem de chunks.

Segurança & Tenancy
- Sempre filtrar por userId/workspaceId no Upstash (filter) e no Prisma.
- Não retornar conteúdos de outros locatários.
- Sanitizar HTML/MD ao exibir; tratar XSS em conteúdo salvo.
- Logs sem conteúdo: registre apenas IDs/quantidades/tempos.

Custos & Créditos
- A recuperação (query) não consome créditos; a geração no chat mantém custos existentes (`ai_text_chat`).
- Indexação pode ser restrita a admins e fora de billing de usuários finais.

Testes (Manual)
- Crie 2 entradas no Admin com conteúdos distintos (A e B).
- No chat, pergunte algo sobre A: verifique injeção correta; repita para B.
- Alterne usuário/workspace: garanta que não há vazamento entre locatários.
- Derrube o Upstash (simule falha): chat deve continuar sem contexto e registrar aviso.

Entregáveis do PR
- Schema Prisma (novos modelos) + migração.
- Lib `src/lib/knowledge/upstash.ts` com upsert/query/delete.
- API Routes admin (CRUD + reindex) com Zod e auth (Clerk admin).
- UI Admin em /admin/knowledge com formulários/tabelas.
- Alterações no chat route para injeção de contexto.
- Documentação curta em docs/knowledge-base.md e atualização de .env.example.
- Rodar `npm run lint`, `npm run typecheck`, `npm run build` sem erros.

Checklists úteis
- Revisar agents/security-check.md antes do merge.
- Conferir agents/backend-development.md (Zod, auth, Prisma) e agents/frontend-development.md (forms, Query, acessibilidade).
- Validar índices/chaves no Prisma conforme agents/database-development.md.

Notas
- Crie o índice no Upstash Vector via painel e configure UPSTASH_VECTOR_REST_URL/TOKEN.
- Garanta que o modelo de embedding selecionado no `openai.embedding(...)` seja compatível com a dimensão configurada no índice.
- Ajuste `topK`, chunk size e limites de tokens conforme qualidade/latência.

