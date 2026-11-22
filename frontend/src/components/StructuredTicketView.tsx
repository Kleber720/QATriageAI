import { useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  Copy,
  Database,
  Download,
  FileCode2,
  GitCompareArrows,
  Layers,
  RotateCcw,
  ShieldCheck,
  SpellCheck,
} from "lucide-react";
import {
  buildTicketFilename,
  categoryLabel,
  downloadTextFile,
  formatTicketAsJira,
  formatTicketAsJson,
  formatTicketAsMarkdown,
  originLabel,
} from "../lib/ticketFormatter";
import type {
  ChecklistItemStatus,
  DataOrigin,
  FieldStatus,
  QATicket,
} from "../types/triage";

interface StructuredTicketViewProps {
  ticket: QATicket;
  checklistBefore?: ChecklistItemStatus[];
  onBackToQuestions?: () => void;
  onReset: () => void;
}

function originBadgeClass(origin: DataOrigin): string {
  switch (origin) {
    case "user_report":
      return "border-indigo-500/40 bg-indigo-500/15 text-indigo-200";
    case "platform_log":
      return "border-cyan-500/40 bg-cyan-500/15 text-cyan-200";
    case "unconfirmed":
      return "border-amber-500/40 bg-amber-500/15 text-amber-200";
    case "ai_hypothesis":
      return "border-purple-500/40 bg-purple-500/15 text-purple-200";
  }
}

function statusShortLabel(status: FieldStatus): string {
  switch (status) {
    case "confirmed":
      return "Confirmado";
    case "partial":
      return "Parcial";
    case "missing":
      return "Faltando";
  }
}

function statusPillClass(status: FieldStatus): string {
  switch (status) {
    case "confirmed":
      return "text-emerald-300 bg-emerald-500/15 border-emerald-500/30";
    case "partial":
      return "text-amber-300 bg-amber-500/15 border-amber-500/30";
    case "missing":
      return "text-rose-300 bg-rose-500/15 border-rose-500/30";
  }
}

export function StructuredTicketView({
  ticket,
  checklistBefore,
  onBackToQuestions,
  onReset,
}: StructuredTicketViewProps) {
  const [copiedType, setCopiedType] = useState<"markdown" | "jira" | "json" | null>(null);

  async function handleCopy(kind: "markdown" | "jira" | "json") {
    const content =
      kind === "markdown"
        ? formatTicketAsMarkdown(ticket)
        : kind === "jira"
          ? formatTicketAsJira(ticket)
          : formatTicketAsJson(ticket);
    await navigator.clipboard.writeText(content);
    setCopiedType(kind);
    setTimeout(() => setCopiedType(null), 2200);
  }

  function handleDownloadMarkdown() {
    downloadTextFile(
      buildTicketFilename(ticket, "md"),
      formatTicketAsMarkdown(ticket),
      "text/markdown;charset=utf-8"
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                Ticket Estruturado QA
              </span>
              <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-0.5 text-xs font-medium text-slate-300">
                {categoryLabel(ticket.categoria)}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white">{ticket.titulo}</h2>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3">
            <p className="text-[11px] uppercase tracking-wide text-slate-400">
              Score de Reprodutibilidade
            </p>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-sm text-slate-400">
                {ticket.score_antes}%
              </span>
              <span className="text-slate-600">→</span>
              <span className="text-xl font-bold text-emerald-400">
                {ticket.score_depois}%
              </span>
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2.5 border-t border-slate-800 pt-4">
          <button
            type="button"
            onClick={() => handleCopy("markdown")}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500"
          >
            {copiedType === "markdown" ? (
              <>
                <Check className="h-3.5 w-3.5" />
                Markdown Copiado!
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                Copiar Markdown
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => handleCopy("jira")}
            className="inline-flex items-center gap-2 rounded-xl border border-indigo-500/40 bg-indigo-500/15 px-4 py-2 text-xs font-semibold text-indigo-200 transition hover:bg-indigo-500/25"
          >
            {copiedType === "jira" ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                Jira Copiado!
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                Copiar Jira
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => handleCopy("json")}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
          >
            {copiedType === "json" ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                JSON Copiado!
              </>
            ) : (
              <>
                <FileCode2 className="h-3.5 w-3.5" />
                Copiar JSON
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleDownloadMarkdown}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
          >
            <Download className="h-3.5 w-3.5" />
            Baixar .md
          </button>

          <span className="text-[11px] text-slate-400">
            Exporta apenas os campos limpos do ticket QA
          </span>

          <div className="ml-auto flex flex-wrap gap-2">
            {onBackToQuestions && (
              <button
                type="button"
                onClick={onBackToQuestions}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Ajustar Respostas
              </button>
            )}
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Novo Relato
            </button>
          </div>
        </div>
      </section>

      <section className="space-y-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div>
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-indigo-400">
            Etapas para Reproduzir :
          </h3>
          <ol className="space-y-1.5 rounded-xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-200">
            {ticket.etapas_para_reproduzir.map((step, idx) => {
              const isMarker = step
                .toLowerCase()
                .includes("aqui que o bug é observado");
              return (
                <li
                  key={idx}
                  className={`flex gap-2.5 ${
                    isMarker ? "font-semibold text-amber-300" : ""
                  }`}
                >
                  <span className="select-none text-slate-500">{idx + 1}.</span>
                  <span>{step}</span>
                </li>
              );
            })}
          </ol>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
            <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-rose-400">
              Resultado Atual:
            </h3>
            <p className="text-sm text-slate-200">{ticket.resultado_atual}</p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
            <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-emerald-400">
              Resultado Esperado:
            </h3>
            <p className="text-sm text-slate-200">{ticket.resultado_esperado}</p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
          <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-slate-400">
            Descrição:
          </h3>
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-200">
            {ticket.descricao}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
            <h3 className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-400">
              Taxa de Reprodução:
            </h3>
            <p
              className={`text-base font-bold ${
                ticket.taxa_de_reproducao === "Não informado"
                  ? "text-amber-300"
                  : "text-white"
              }`}
            >
              {ticket.taxa_de_reproducao}
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 md:col-span-2">
            <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-slate-400">
              NOTAS:
            </h3>
            <p className="whitespace-pre-line text-sm text-slate-300">
              {ticket.notas}
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-6">
        <div className="mb-3 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-400" />
          <div>
            <h3 className="text-base font-bold text-amber-200">
              O que não foi confirmado (Reconhecer os Limites da IA)
            </h3>
            <p className="text-xs text-amber-200/80">
              Separação explícita entre fatos confirmados pelo usuário e lacunas ou suposições não validadas.
            </p>
          </div>
        </div>

        {ticket.o_que_nao_foi_confirmado.length === 0 ? (
          <p className="text-sm text-emerald-300">
            Todos os critérios obrigatórios do Escopo do Bug foram confirmados pelo usuário.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {ticket.o_que_nao_foi_confirmado.map((item, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-amber-500/30 bg-slate-950/80 p-4"
              >
                <p className="text-sm font-semibold text-amber-300">
                  {item.campo}
                </p>
                <p className="mt-1 text-xs text-slate-200">{item.motivo}</p>
                <p className="mt-1.5 text-xs text-slate-400">
                  <strong className="text-slate-300">Impacto para QA:</strong>{" "}
                  {item.impacto_para_qa}
                </p>
                {item.hipotese_da_ia && (
                  <p className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-2.5 py-1.5 text-xs text-amber-200">
                    <strong>Suposição da IA (não confirmado):</strong>{" "}
                    {item.hipotese_da_ia}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {(ticket.correcoes_ortograficas.length > 0 ||
        ticket.dados_sensiveis_removidos.length > 0) && (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {ticket.correcoes_ortograficas.length > 0 && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-indigo-300">
                <SpellCheck className="h-4 w-4" />
                Correções Ortográficas Aplicadas
              </div>
              <div className="flex flex-wrap gap-2">
                {ticket.correcoes_ortograficas.map((c, i) => (
                  <span
                    key={i}
                    className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-200"
                  >
                    <span className="text-rose-300 line-through">
                      {c.original}
                    </span>{" "}
                    →{" "}
                    <span className="font-medium text-emerald-300">
                      {c.corrigido}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {ticket.dados_sensiveis_removidos.length > 0 && (
            <div className="rounded-2xl border border-cyan-500/30 bg-cyan-500/5 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-cyan-300">
                <ShieldCheck className="h-4 w-4" />
                Dados Sensíveis Sanitizados Automaticamente
              </div>
              <ul className="space-y-1 text-xs text-cyan-100/90">
                {ticket.dados_sensiveis_removidos.map((item, i) => (
                  <li key={i}>• {item}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {ticket.divergencias_com_logs.length > 0 && (
        <section className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-6">
          <div className="mb-3 flex items-center gap-2">
            <GitCompareArrows className="h-5 w-5 text-rose-400" />
            <div>
              <h3 className="text-base font-bold text-rose-200">
                Divergências Detectadas (Relato do Usuário vs. Log da Plataforma)
              </h3>
              <p className="text-xs text-rose-200/80">
                Diferenças identificadas automaticamente ao cruzar a descrição do usuário com a telemetria.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {ticket.divergencias_com_logs.map((div, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-rose-500/30 bg-slate-950/80 p-4 text-xs"
              >
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div>
                    <p className="font-semibold text-indigo-300">
                      Usuário relatou:
                    </p>
                    <p className="mt-0.5 text-slate-200">{div.relato_usuario}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-cyan-300">
                      Evidência no log:
                    </p>
                    <p className="mt-0.5 text-slate-200">{div.evidencia_log}</p>
                  </div>
                </div>
                {div.explicacao && (
                  <p className="mt-2 border-t border-slate-800 pt-2 text-slate-300">
                    <strong className="text-rose-300">Análise:</strong>{" "}
                    {div.explicacao}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {ticket.origem_dos_dados.length > 0 && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="mb-3 flex items-center gap-2">
            <Layers className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Origem dos Dados (Rastreabilidade)
            </h3>
          </div>
          <div className="space-y-2">
            {ticket.origem_dos_dados.map((item, idx) => (
              <div
                key={idx}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-950/70 px-3.5 py-2.5 text-xs"
              >
                <div className="flex flex-wrap items-center gap-2.5">
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${originBadgeClass(
                      item.origin
                    )}`}
                  >
                    {originLabel(item.origin)}
                  </span>
                  <span className="text-slate-200">{item.fact}</span>
                </div>
                {item.reference && (
                  <span className="font-mono text-[11px] text-slate-400">
                    {item.reference}
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {ticket.platform_context_used && (
        <section className="rounded-2xl border border-cyan-500/30 bg-slate-900/60 p-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-cyan-400" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-cyan-200">
                Contexto de Log Cruzado ({ticket.platform_context_used.session_id})
              </h3>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {ticket.platform_context_used.extracted_error_codes.map((code) => (
                <span
                  key={code}
                  className="rounded border border-rose-500/40 bg-rose-500/10 px-2 py-0.5 font-mono text-[11px] text-rose-300"
                >
                  {code}
                </span>
              ))}
            </div>
          </div>

          {ticket.platform_context_used.events.length > 0 && (
            <div className="space-y-1 font-mono text-[11px]">
              {ticket.platform_context_used.events.map((ev, idx) => (
                <div
                  key={idx}
                  className="rounded-md bg-slate-950 px-3 py-1.5 text-slate-300"
                >
                  <span className="text-slate-500">{ev.timestamp}</span>{" "}
                  <span className="font-bold text-cyan-300">{ev.level}</span>{" "}
                  <span className="text-indigo-300">[{ev.component}]</span>{" "}
                  <span>{ev.message}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {ticket.checklist_final.length > 0 && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
          <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-300">
            Checklist de Prontidão (Antes → Depois)
          </h3>
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
            {ticket.checklist_final.map((afterItem) => {
              const beforeItem = checklistBefore?.find(
                (b) => b.field_id === afterItem.field_id
              );
              const changed =
                beforeItem && beforeItem.status !== afterItem.status;

              return (
                <div
                  key={afterItem.field_id}
                  className="rounded-xl border border-slate-800 bg-slate-950/70 p-3"
                >
                  <p className="text-xs font-semibold text-slate-200">
                    {afterItem.label}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px]">
                    {changed && beforeItem && (
                      <>
                        <span
                          className={`rounded-full border px-2 py-0.5 opacity-75 ${statusPillClass(
                            beforeItem.status
                          )}`}
                        >
                          {statusShortLabel(beforeItem.status)}
                        </span>
                        <ArrowRight className="h-3 w-3 text-slate-500" />
                      </>
                    )}
                    <span
                      className={`rounded-full border px-2 py-0.5 font-semibold ${statusPillClass(
                        afterItem.status
                      )}`}
                    >
                      {statusShortLabel(afterItem.status)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
