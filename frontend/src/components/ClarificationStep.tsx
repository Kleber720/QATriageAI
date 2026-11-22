import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  HelpCircle,
  Loader2,
  ShieldAlert,
  SkipForward,
  Sparkles,
  SpellCheck,
} from "lucide-react";
import { categoryLabel } from "../lib/ticketFormatter";
import { PlatformLogsPanel } from "./PlatformLogsPanel";
import type {
  AnalyzeResponse,
  PlatformContextData,
  PlatformSessionSummary,
  QuestionAnswer,
} from "../types/triage";

interface ClarificationStepProps {
  analysis: AnalyzeResponse;
  answers: QuestionAnswer[];
  onChangeAnswer: (questionId: string, answer: string) => void;
  onToggleSkip: (questionId: string) => void;
  logSessions: PlatformSessionSummary[];
  selectedSessionId: string;
  suggestedSessionId?: string;
  selectedSessionData: PlatformContextData | null;
  loadingSession: boolean;
  onSelectSession: (sessionId: string) => void;
  rawLogText: string;
  parsedRawLog: PlatformContextData | null;
  parsingRawLog: boolean;
  onChangeRawLog: (text: string) => void;
  onParseRawLog: () => void;
  onBack: () => void;
  onGenerate: () => void;
  submitting: boolean;
}

function statusBadge(status: "confirmed" | "partial" | "missing") {
  if (status === "confirmed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
        <CheckCircle2 className="h-3 w-3" /> Confirmado
      </span>
    );
  }
  if (status === "partial") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-300">
        <AlertCircle className="h-3 w-3" /> Parcial
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2 py-0.5 text-[11px] font-medium text-rose-300">
      <HelpCircle className="h-3 w-3" /> Faltando
    </span>
  );
}

export function ClarificationStep({
  analysis,
  answers,
  onChangeAnswer,
  onToggleSkip,
  logSessions,
  selectedSessionId,
  suggestedSessionId,
  selectedSessionData,
  loadingSession,
  onSelectSession,
  rawLogText,
  parsedRawLog,
  parsingRawLog,
  onChangeRawLog,
  onParseRawLog,
  onBack,
  onGenerate,
  submitting,
}: ClarificationStepProps) {
  const answerMap = new Map(answers.map((a) => [a.question_id, a]));

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 text-xs font-medium text-indigo-300">
                {analysis.input_mode === "draft_ticket"
                  ? "Rascunho de Ticket"
                  : "Relato Vago"}
              </span>
              <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-0.5 text-xs font-medium text-slate-300">
                {categoryLabel(analysis.category)}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-white">
              Diagnóstico de Reprodutibilidade
            </h2>
            <p className="text-sm text-slate-300">{analysis.summary}</p>
          </div>

          <div className="min-w-[190px] rounded-xl border border-slate-800 bg-slate-950 p-3.5">
            <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
              <span>Prontidão atual</span>
              <span className="font-bold text-white">
                {analysis.reproducibility_score}%
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full transition-all ${
                  analysis.reproducibility_score >= 75
                    ? "bg-emerald-500"
                    : analysis.reproducibility_score >= 45
                      ? "bg-amber-500"
                      : "bg-rose-500"
                }`}
                style={{ width: `${analysis.reproducibility_score}%` }}
              />
            </div>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
          {analysis.checklist.map((item) => (
            <div
              key={item.field_id}
              className="rounded-xl border border-slate-800/90 bg-slate-950/70 p-3"
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-slate-200">
                  {item.label}
                </span>
                {statusBadge(item.status)}
              </div>
              <p className="text-[11px] leading-snug text-slate-400">
                {item.note}
              </p>
            </div>
          ))}
        </div>

        {(analysis.detected_issues.length > 0 ||
          analysis.spelling_issues.length > 0 ||
          analysis.pii_warnings.length > 0) && (
          <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2">
            {analysis.detected_issues.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300">
                  Lacunas e Problemas Detectados
                </p>
                <ul className="space-y-1 text-xs text-slate-300">
                  {analysis.detected_issues.map((issue, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-amber-400">•</span>
                      <span>{issue}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="space-y-3">
              {analysis.spelling_issues.length > 0 && (
                <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3.5">
                  <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-indigo-300">
                    <SpellCheck className="h-3.5 w-3.5" />
                    Correções Ortográficas Sugeridas
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {analysis.spelling_issues.map((sp, idx) => (
                      <span
                        key={idx}
                        className="rounded-md border border-indigo-500/30 bg-slate-950 px-2 py-0.5 text-xs text-slate-200"
                      >
                        <span className="text-rose-300 line-through">
                          {sp.original}
                        </span>{" "}
                        →{" "}
                        <span className="font-medium text-emerald-300">
                          {sp.suggestion}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {analysis.pii_warnings.length > 0 && (
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-3.5">
                  <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-cyan-200">
                    <ShieldAlert className="h-3.5 w-3.5" />
                    Dados Sensíveis Detectados (Serão Sanitizados)
                  </div>
                  <ul className="space-y-0.5 text-xs text-cyan-100/90">
                    {analysis.pii_warnings.map((w, i) => (
                      <li key={i}>• {w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white">
            2. Perguntas de Esclarecimento (Apenas o que Falta)
          </h3>
          <p className="text-sm text-slate-400">
            Responda apenas ao que souber. Itens marcados como{" "}
            <strong className="text-amber-300">Não sei / Pular</strong> não
            serão inventados e irão automaticamente para{" "}
            <strong className="text-amber-300">O que não foi confirmado</strong>.
          </p>
        </div>

        {analysis.questions.length === 0 ? (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
            Todas as informações principais do Escopo do Bug já estão presentes!
            Você pode gerar o ticket final diretamente para polimento e
            padronização.
          </div>
        ) : (
          <div className="space-y-4">
            {analysis.questions.map((q, index) => {
              const state = answerMap.get(q.id);
              const isSkipped = state?.skipped ?? false;
              const value = state?.answer ?? "";

              return (
                <div
                  key={q.id}
                  className={`rounded-xl border p-4 transition ${
                    isSkipped
                      ? "border-amber-500/30 bg-amber-500/5"
                      : "border-slate-800 bg-slate-950/70"
                  }`}
                >
                  <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                    <div className="space-y-1">
                      <span className="text-xs font-semibold uppercase tracking-wide text-indigo-400">
                        Pergunta {index + 1}
                      </span>
                      <p className="text-sm font-medium text-white">
                        {q.question}
                      </p>
                      <p className="text-xs text-slate-400">{q.why_needed}</p>
                    </div>

                    <button
                      type="button"
                      onClick={() => onToggleSkip(q.id)}
                      className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                        isSkipped
                          ? "border-amber-400/50 bg-amber-500/20 text-amber-200"
                          : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500 hover:text-white"
                      }`}
                    >
                      <SkipForward className="h-3.5 w-3.5" />
                      {isSkipped ? "Pulado (irá para Não Confirmado)" : "Não sei / Pular"}
                    </button>
                  </div>

                  {!isSkipped && (
                    <input
                      type="text"
                      value={value}
                      onChange={(e) => onChangeAnswer(q.id, e.target.value)}
                      placeholder={q.placeholder || "Digite a resposta aqui..."}
                      className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-5">
          <button
            type="button"
            onClick={onBack}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-slate-500 hover:text-white disabled:opacity-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Editar Relato
          </button>

          <button
            type="button"
            disabled={submitting}
            onClick={onGenerate}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-600/20 transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Estruturando ticket QA...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Gerar Ticket para QA
              </>
            )}
          </button>
        </div>
      </section>

      <PlatformLogsPanel
        sessions={logSessions}
        selectedSessionId={selectedSessionId}
        suggestedSessionId={suggestedSessionId}
        selectedSessionData={selectedSessionData}
        loadingSession={loadingSession}
        onSelectSession={onSelectSession}
        rawLogText={rawLogText}
        parsedRawLog={parsedRawLog}
        parsingRawLog={parsingRawLog}
        onChangeRawLog={onChangeRawLog}
        onParseRawLog={onParseRawLog}
      />
    </div>
  );
}
