import { Sparkles, Loader2, FileText, Eraser } from "lucide-react";
import type { ExamplePreset } from "../types/triage";

interface ReportInputStepProps {
  reportText: string;
  onChangeText: (value: string) => void;
  onSelectExample: (example: ExamplePreset) => void;
  examples: ExamplePreset[];
  loadingExamples: boolean;
  submitting: boolean;
  onSubmit: () => void;
}

function badgeStyle(badge: string): string {
  const lower = badge.toLowerCase();
  if (lower.includes("diverg")) {
    return "border-purple-500/40 bg-purple-500/15 text-purple-200";
  }
  if (lower.includes("vago")) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-300";
  }
  if (lower.includes("ruim")) {
    return "border-rose-500/30 bg-rose-500/10 text-rose-300";
  }
  if (lower.includes("pii")) {
    return "border-cyan-500/30 bg-cyan-500/10 text-cyan-300";
  }
  return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
}

export function ReportInputStep({
  reportText,
  onChangeText,
  onSelectExample,
  examples,
  loadingExamples,
  submitting,
  onSubmit,
}: ReportInputStepProps) {
  const canSubmit = reportText.trim().length >= 5 && !submitting;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-white">
              1. Relato Vago ou Rascunho de Ticket
            </h2>
            <p className="text-sm text-slate-400">
              Cole um relato curto de usuário/atendente ou um rascunho de ticket incompleto. A IA local identifica o que falta para o QA reproduzir.
            </p>
          </div>
          {reportText && (
            <button
              type="button"
              onClick={() => onChangeText("")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
            >
              <Eraser className="h-3.5 w-3.5" />
              Limpar texto
            </button>
          )}
        </div>

        <textarea
          value={reportText}
          onChange={(e) => onChangeText(e.target.value)}
          rows={10}
          placeholder='Ex.: "Oi, não consegui comprar no site da YouShop, deu erro na hora de pagar" ou cole um rascunho de ticket de QA...'
          className="w-full rounded-xl border border-slate-700 bg-slate-950/90 p-4 text-sm leading-relaxed text-slate-100 placeholder-slate-500 transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
        />

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-slate-400">
            Mínimo de 5 caracteres • Processamento 100% local via Ollama
          </span>

          <button
            type="button"
            disabled={!canSubmit}
            onClick={onSubmit}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analisando lacunas...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Analisar com IA Local
              </>
            )}
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5">
        <div className="mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Cenários Reais para Testar em 1 Clique
          </h3>
        </div>

        {loadingExamples ? (
          <p className="text-xs text-slate-400">Carregando exemplos da base de conhecimento...</p>
        ) : examples.length === 0 ? (
          <p className="text-xs text-slate-500">
            Inicie o backend FastAPI para carregar os exemplos de treino.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {examples.map((ex) => (
              <button
                key={ex.id}
                type="button"
                onClick={() => onSelectExample(ex)}
                className="flex flex-col items-start gap-2 rounded-xl border border-slate-800 bg-slate-950/70 p-3.5 text-left transition hover:border-indigo-500/50 hover:bg-slate-900"
              >
                <div className="flex w-full items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-slate-100">
                    {ex.title}
                  </span>
                  <span
                    className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${badgeStyle(
                      ex.badge
                    )}`}
                  >
                    {ex.badge}
                  </span>
                </div>
                <p className="line-clamp-2 text-xs text-slate-400">
                  {ex.description}
                </p>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
