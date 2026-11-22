import { RefreshCw, Cpu, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { HealthResponse } from "../types/triage";

interface OllamaStatusBadgeProps {
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export function OllamaStatusBadge({
  health,
  loading,
  onRefresh,
}: OllamaStatusBadgeProps) {
  const isOk = health?.status === "ok";

  return (
    <div className="flex flex-col items-end gap-1.5">
      <div className="flex items-center gap-2">
        <div
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${
            isOk
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-amber-500/30 bg-amber-500/10 text-amber-300"
          }`}
        >
          {isOk ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
          )}
          <Cpu className="h-3.5 w-3.5 opacity-80" />
          {health ? (
            <span>
              {isOk
                ? `Ollama Online • ${health.configured_model}`
                : health.ollama_online
                  ? `Modelo ausente • ${health.configured_model}`
                  : "Ollama Offline"}
            </span>
          ) : (
            <span>Verificando IA local...</span>
          )}
        </div>

        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          title="Atualizar status do Ollama"
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-slate-300 transition hover:border-slate-500 hover:text-white disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {health && !isOk && (
        <p className="max-w-md text-right text-xs text-amber-300/90">
          {health.message}
        </p>
      )}
    </div>
  );
}
