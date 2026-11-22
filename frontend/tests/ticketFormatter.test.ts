import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  buildTicketFilename,
  formatTicketAsJira,
  formatTicketAsJson,
  formatTicketAsMarkdown,
} from "../src/lib/ticketFormatter.ts";
import type { QATicket } from "../src/types/triage.ts";

function sampleTicket(): QATicket {
  return {
    titulo: "[YouShop] Erro HTTP 504 no checkout com cartão",
    categoria: "erro_integracao",
    etapas_para_reproduzir: [
      "Acesse o checkout da YouShop no Desktop Chrome + versão v2.14.3",
      "Adicione o Tênis Runner Pro ao carrinho e finalize com cartão de crédito",
      "É aqui que o bug é observado",
    ],
    resultado_atual: "O checkout trava carregando e exibe erro após 15 segundos.",
    resultado_esperado: "O pagamento é processado e o pedido é confirmado.",
    descricao: "Na etapa de pagamento do checkout, o gateway retorna HTTP 504.",
    taxa_de_reproducao: "Não informado",
    notas: "Log PED-9042 confirma ERR_GW_504_TIMEOUT.",
    o_que_nao_foi_confirmado: [
      {
        campo: "Taxa de Reprodução",
        motivo: "Nenhuma contagem X/Y informada.",
        impacto_para_qa: "Frequência desconhecida.",
        hipotese_da_ia: "",
      },
    ],
    correcoes_ortograficas: [],
    dados_sensiveis_removidos: [],
    score_antes: 21,
    score_depois: 68,
    checklist_final: [],
    platform_context_used: {
      session_id: "PED-9042",
      source_type: "mock_telemetry",
      environment: {
        application: "YouShop Checkout",
        platform: "Web",
        build: "v2.14.3",
        os: "Windows 11",
        hardware_summary: "Desktop Browser",
      },
      events: [
        {
          timestamp: "2026-11-21 11:02:29",
          level: "ERROR",
          component: "PaymentGateway",
          message: "HTTP 504 Gateway Timeout",
          error_code: "ERR_GW_504_TIMEOUT",
        },
      ],
      extracted_error_codes: ["ERR_GW_504_TIMEOUT"],
      raw_excerpt: "11:02:29 ERROR PaymentGateway",
      pii_redactions: [],
    },
    origem_dos_dados: [
      {
        fact: "Erro ao pagar com cartão.",
        origin: "user_report",
        reference: "Relato inicial",
      },
      {
        fact: "HTTP 504 Gateway Timeout.",
        origin: "platform_log",
        reference: "PED-9042",
      },
    ],
    divergencias_com_logs: [
      {
        relato_usuario: "Cartão recusado",
        evidencia_log: "HTTP 504 Gateway Timeout",
        explicacao: "Timeout no gateway, não recusa do emissor.",
      },
    ],
  };
}

describe("ticketFormatter", () => {
  it("formata Markdown apenas com os campos limpos do ticket QA sem Evidências", () => {
    const md = formatTicketAsMarkdown(sampleTicket());
    assert.match(md, /# \[YouShop\] Erro HTTP 504 no checkout com cartão/);
    assert.match(md, /## Etapas para Reproduzir :/);
    assert.match(md, /3\. É aqui que o bug é observado/);
    assert.match(md, /## Resultado Atual:/);
    assert.match(md, /## Resultado Esperado:/);
    assert.match(md, /## Descrição:/);
    assert.match(md, /## Taxa de Reprodução: Não informado/);
    assert.match(md, /## NOTAS:/);

    assert.doesNotMatch(md, /Evidências/);
    assert.doesNotMatch(md, /O que não foi confirmado/);
    assert.doesNotMatch(md, /Divergências entre Relato e Log/);
    assert.doesNotMatch(md, /Origem dos Dados/);
    assert.doesNotMatch(md, /Score de Reprodutibilidade/);
  });

  it("formata Jira Wiki Markup apenas com o ticket limpo sem Evidências", () => {
    const jira = formatTicketAsJira(sampleTicket());
    assert.match(jira, /^h1\. \[YouShop\] Erro HTTP 504/m);
    assert.match(jira, /^h2\. Etapas para Reproduzir/m);
    assert.match(jira, /^# É aqui que o bug é observado/m);
    assert.match(jira, /^\*Taxa de Reprodução:\* Não informado/m);

    assert.doesNotMatch(jira, /Evidências/);
    assert.doesNotMatch(jira, /O que não foi confirmado/);
    assert.doesNotMatch(jira, /Divergências/);
    assert.doesNotMatch(jira, /Origem dos Dados/);
    assert.doesNotMatch(jira, /\{code/);
  });

  it("exporta JSON apenas com os 7 campos do ticket", () => {
    const parsed = JSON.parse(formatTicketAsJson(sampleTicket()));
    assert.deepEqual(Object.keys(parsed), [
      "titulo",
      "etapas_para_reproduzir",
      "resultado_atual",
      "resultado_esperado",
      "descricao",
      "taxa_de_reproducao",
      "notas",
    ]);
    assert.equal(parsed.evidencias, undefined);
    assert.equal(parsed.o_que_nao_foi_confirmado, undefined);
    assert.equal(parsed.platform_context_used, undefined);
  });

  it("gera nome de arquivo limpo em ASCII", () => {
    const filename = buildTicketFilename(sampleTicket(), "md");
    assert.equal(
      filename,
      "ticket-qa-youshop-erro-http-504-no-checkout-com-cartao.md"
    );
  });
});
