import { useState } from "react";
import {
  Database,
  FileTerminal,
  Loader2,
  ShieldCheck,
  X,
} from "lucide-react";
import type {
  PlatformContextData,
  PlatformSessionSummary,
} from "../types/triage";

interface PlatformLogsPanelProps {
  sessions: PlatformSessionSummary[];
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
}

function levelBadge(level: "INFO" | "WARN" | "ERROR" | "FATAL"): string {
  switch (level) {
    case "FATAL":
      return "bg-rose-500/20 text-rose-300 border-rose-500/40";
    case "ERROR":
      return "bg-red-500/15 text-red-300 border-red-500/30";
    case "WARN":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    default:
      return "bg-slate-800 text-slate-300 border-slate-700";
  }
}

export function PlatformLogsPanel({
  sessions,
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
}: PlatformLogsPanelProps) {
  const [tab, setTab] = useState<"sessions" | "raw">("sessions");

  const activePreview =
    tab === "sessions" ? selectedSessionData : parsedRawLog;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-cyan-400" />
            <h3 className="text-base font-semibold text-white">
              Etapa 4 (Opcional): Cruzar com Dados da Plataforma / Logs
            </h3>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Vincule uma sessão simulada de telemetria ou cole um log bruto para a IA cruzar horários, códigos de erro e detectar divergências com o relato.
          </p>
        </div>

        <div className="flex rounded-xl border border-slate-800 bg-slate-950 p-1">
          <button
            type="button"
            onClick={() => setTab("sessions")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              tab === "sessions"
                ? "bg-cyan-500/20 text-cyan-200"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Sessões Simuladas
          </button>
          <button
            type="button"
            onClick={() => setTab("raw")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              tab === "raw"
                ? "bg-cyan-500/20 text-cyan-200"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Colar Log Bruto
          </button>
        </div>
      </div>

      {tab === "sessions" ? (
        <div className="space-y-3">
          {suggestedSessionId && !selectedSessionId && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-purple-500/30 bg-purple-500/10 px-3.5 py-2.5 text-xs text-purple-200">
              <span>
                Sugestão para este cenário: vincular a sessão{" "}
                <strong className="font-mono">{suggestedSessionId}</strong> para cruzar com telemetria.
              </span>
              <button
                type="button"
                onClick={() => onSelectSession(suggestedSessionId)}
                className="rounded-lg border border-purple-400/40 bg-purple-500/20 px-3 py-1 font-semibold text-purple-100 transition hover:bg-purple-500/35"
              >
                Vincular agora
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {sessions.map((s) => {
              const isSelected = selectedSessionId === s.session_id;
              return (
                <button
                  key={s.session_id}
                  type="button"
                  onClick={() =>
                    onSelectSession(isSelected ? "" : s.session_id)
                  }
                  className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition ${
                    isSelected
                      ? "border-cyan-500/60 bg-cyan-500/10"
                      : "border-slate-800 bg-slate-950/70 hover:border-slate-600"
                  }`}
                >
                  <div className="flex w-full items-center justify-between gap-2">
                    <span className="font-mono text-xs font-bold text-cyan-300">
                      {s.session_id}
                    </span>
                    <span className="rounded-md border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] text-slate-300">
                      {s.application} • {s.build}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-100">
                    {s.title}
                  </p>
                  <p className="text-[11px] text-slate-400">{s.summary}</p>
                </button>
              );
            })}
          </div>

          {selectedSessionId && (
            <div className="flex items-center justify-between rounded-lg border border-cyan-500/30 bg-cyan-500/5 px-3 py-2 text-xs text-cyan-200">
              <span>
                Sessão vinculada: <strong>{selectedSessionId}</strong>
              </span>
              <button
                type="button"
                onClick={() => onSelectSession("")}
                className="inline-flex items-center gap-1 text-cyan-300 hover:text-white"
              >
                <X className="h-3.5 w-3.5" /> Remover vínculo
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          <textarea
            value={rawLogText}
            onChange={(e) => onChangeRawLog(e.target.value)}
            rows={5}
            placeholder="Cole aqui linhas de log (ex.: 11:02:29 ERROR [PaymentGateway] HTTP 504 ERR_GW_504_TIMEOUT build v2.14.3)..."
            className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 font-mono text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[11px] text-slate-400">
              O log colado é automaticamente sanitizado antes de ir ao LLM.
            </span>
            <button
              type="button"
              disabled={rawLogText.trim().length < 5 || parsingRawLog}
              onClick={onParseRawLog}
              className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/15 px-3 py-1.5 text-xs font-medium text-cyan-200 transition hover:bg-cyan-500/25 disabled:opacity-50"
            >
              {parsingRawLog ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <FileTerminal className="h-3.5 w-3.5" />
              )}
              Pré-analisar Log
            </button>
          </div>
        </div>
      )}

      {loadingSession && (
        <p className="mt-3 text-xs text-slate-400">
          Carregando telemetria da sessão...
        </p>
      )}

      {activePreview && (
        <div className="mt-4 space-y-2.5 rounded-xl border border-slate-800 bg-slate-950/90 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold text-cyan-300">
              Prévia da Telemetria ({activePreview.session_id})
            </span>
            <div className="flex flex-wrap gap-1.5">
              {activePreview.extracted_error_codes.map((code) => (
                <span
                  key={code}
                  className="rounded-md border border-rose-500/40 bg-rose-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-rose-300"
                >
                  {code}
                </span>
              ))}
            </div>
          </div>

          {activePreview.events.length > 0 && (
            <div className="space-y-1 font-mono text-[11px]">
              {activePreview.events.map((ev, idx) => (
                <div
                  key={idx}
                  className="flex flex-wrap items-baseline gap-2 rounded-md bg-slate-900/80 px-2.5 py-1.5"
                >
                  <span className="text-slate-500">{ev.timestamp}</span>
                  <span
                    className={`rounded border px-1.5 py-0.5 text-[10px] font-bold ${levelBadge(
                      ev.level
                    )}`}
                  >
                    {ev.level}
                  </span>
                  <span className="text-indigo-300">[{ev.component}]</span>
                  <span className="text-slate-200">{ev.message}</span>
                </div>
              ))}
            </div>
          )}

          {activePreview.pii_redactions.length > 0 && (
            <div className="flex items-center gap-1.5 text-[11px] text-cyan-300">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>
                PII sanitizado do log:{" "}
                {activePreview.pii_redactions.join(", ")}
              </span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
