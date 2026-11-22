import { useEffect } from "react";
import { Database, History, Trash2, X } from "lucide-react";
import { categoryLabel } from "../lib/ticketFormatter";
import type { TicketHistoryEntry } from "../types/triage";

interface TicketHistoryDrawerProps {
  open: boolean;
  entries: TicketHistoryEntry[];
  onClose: () => void;
  onSelectEntry: (entry: TicketHistoryEntry) => void;
  onDeleteEntry: (id: string) => void;
  onClearAll: () => void;
}

function formatDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function TicketHistoryDrawer({
  open,
  entries,
  onClose,
  onSelectEntry,
  onDeleteEntry,
  onClearAll,
}: TicketHistoryDrawerProps) {
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-950/75 backdrop-blur-xs"
      />

      <aside
        role="dialog"
        aria-label="Histórico local de tickets"
        className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-slate-800 bg-slate-900 shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <History className="h-5 w-5 text-indigo-400" />
            <div>
              <h2 className="text-sm font-bold text-white">
                Histórico Local ({entries.length})
              </h2>
              <p className="text-[11px] text-slate-400">
                Salvo automaticamente neste navegador
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {entries.length > 0 && (
              <button
                type="button"
                onClick={onClearAll}
                className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-300 transition hover:bg-rose-500/20"
              >
                Limpar tudo
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Fechar histórico"
              className="rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-300 transition hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {entries.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 text-center text-xs text-slate-400">
              Nenhum ticket gerado ainda. Ao concluir a triagem, os tickets aparecem aqui para consulta e exportação rápida.
            </div>
          ) : (
            <div className="space-y-3">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className="group relative rounded-xl border border-slate-800 bg-slate-950/80 p-3.5 transition hover:border-indigo-500/50"
                >
                  <button
                    type="button"
                    onClick={() => onSelectEntry(entry)}
                    className="w-full pr-7 text-left"
                  >
                    <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                      <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 font-medium text-slate-300">
                        {categoryLabel(entry.ticket.categoria)}
                      </span>
                      <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-semibold text-emerald-300">
                        {entry.ticket.score_antes}% → {entry.ticket.score_depois}%
                      </span>
                      {entry.ticket.platform_context_used && (
                        <span className="inline-flex items-center gap-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 font-mono text-cyan-300">
                          <Database className="h-2.5 w-2.5" />
                          {entry.ticket.platform_context_used.session_id}
                        </span>
                      )}
                    </div>

                    <p className="mt-2 line-clamp-2 text-xs font-semibold text-white group-hover:text-indigo-300">
                      {entry.ticket.titulo}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500">
                      {formatDateTime(entry.createdAt)}
                    </p>
                  </button>

                  <button
                    type="button"
                    title="Remover do histórico"
                    onClick={() => onDeleteEntry(entry.id)}
                    className="absolute right-2.5 top-3 rounded-lg p-1.5 text-slate-500 transition hover:bg-rose-500/10 hover:text-rose-300"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
