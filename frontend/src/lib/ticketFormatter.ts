import type { DataOrigin, QATicket, ReportCategory } from "../types/triage.ts";

export function categoryLabel(category: ReportCategory): string {
  switch (category) {
    case "bug_funcional":
      return "Bug Funcional";
    case "erro_bloqueante":
      return "Erro Bloqueante / Travamento";
    case "erro_integracao":
      return "Erro de Integração / Pagamento";
    default:
      return "Categoria Indefinida";
  }
}

export function originLabel(origin: DataOrigin): string {
  switch (origin) {
    case "user_report":
      return "Relato do Usuário";
    case "platform_log":
      return "Log da Plataforma";
    case "unconfirmed":
      return "Não Confirmado";
    case "ai_hypothesis":
      return "Hipótese da IA";
  }
}

export function formatTicketAsMarkdown(ticket: QATicket): string {
  const stepsText =
    ticket.etapas_para_reproduzir.length > 0
      ? ticket.etapas_para_reproduzir
          .map((step, index) => `${index + 1}. ${step}`)
          .join("\n")
      : "1. Não informado";

  return [
    `# ${ticket.titulo}`,
    "",
    "## Etapas para Reproduzir :",
    stepsText,
    "",
    "## Resultado Atual:",
    ticket.resultado_atual,
    "",
    "## Resultado Esperado:",
    ticket.resultado_esperado,
    "",
    "## Descrição:",
    ticket.descricao,
    "",
    `## Taxa de Reprodução: ${ticket.taxa_de_reproducao}`,
    "",
    "## NOTAS:",
    ticket.notas,
  ].join("\n");
}

export function formatTicketAsJira(ticket: QATicket): string {
  const stepsLines =
    ticket.etapas_para_reproduzir.length > 0
      ? ticket.etapas_para_reproduzir.map((step) => `# ${step}`)
      : ["# Não informado"];

  return [
    `h1. ${ticket.titulo}`,
    "",
    "h2. Etapas para Reproduzir",
    ...stepsLines,
    "",
    "h2. Resultado Atual",
    ticket.resultado_atual,
    "",
    "h2. Resultado Esperado",
    ticket.resultado_esperado,
    "",
    "h2. Descrição",
    ticket.descricao,
    "",
    `*Taxa de Reprodução:* ${ticket.taxa_de_reproducao}`,
    "",
    "h2. NOTAS",
    ticket.notas,
  ].join("\n");
}

export function formatTicketAsJson(ticket: QATicket): string {
  return JSON.stringify(
    {
      titulo: ticket.titulo,
      etapas_para_reproduzir: ticket.etapas_para_reproduzir,
      resultado_atual: ticket.resultado_atual,
      resultado_esperado: ticket.resultado_esperado,
      descricao: ticket.descricao,
      taxa_de_reproducao: ticket.taxa_de_reproducao,
      notas: ticket.notas,
    },
    null,
    2
  );
}

export function buildTicketFilename(
  ticket: QATicket,
  extension: "md" | "json"
): string {
  const normalized = ticket.titulo
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);

  const slug = normalized || "relato";
  return `ticket-qa-${slug}.${extension}`;
}

export function downloadTextFile(
  filename: string,
  content: string,
  mimeType: string
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
