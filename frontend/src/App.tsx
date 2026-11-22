import { useEffect, useState } from "react";
import { Bug, AlertOctagon, History } from "lucide-react";
import { ClarificationStep } from "./components/ClarificationStep";
import { OllamaStatusBadge } from "./components/OllamaStatusBadge";
import { ReportInputStep } from "./components/ReportInputStep";
import { StepIndicator, type WizardStep } from "./components/StepIndicator";
import { StructuredTicketView } from "./components/StructuredTicketView";
import { TicketHistoryDrawer } from "./components/TicketHistoryDrawer";
import {
  clearTicketHistory,
  deleteTicketFromHistory,
  loadTicketHistory,
  saveTicketToHistory,
} from "./lib/ticketHistory";
import {
  analyzeReport,
  fetchExamples,
  fetchHealth,
  fetchLogSession,
  fetchLogSessions,
  generateTicket,
  parseRawLog,
} from "./services/api";
import type {
  AnalyzeResponse,
  ChecklistItemStatus,
  ExamplePreset,
  HealthResponse,
  PlatformContextData,
  PlatformSessionSummary,
  QATicket,
  QuestionAnswer,
  TicketHistoryEntry,
} from "./types/triage";

export function App() {
  const [step, setStep] = useState<WizardStep>(1);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [examples, setExamples] = useState<ExamplePreset[]>([]);
  const [loadingExamples, setLoadingExamples] = useState(true);

  const [reportText, setReportText] = useState("");
  const [suggestedSessionId, setSuggestedSessionId] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [answers, setAnswers] = useState<QuestionAnswer[]>([]);
  const [ticket, setTicket] = useState<QATicket | null>(null);

  const [history, setHistory] = useState<TicketHistoryEntry[]>(() =>
    loadTicketHistory()
  );
  const [historyOpen, setHistoryOpen] = useState(false);
  const [viewingHistoryEntry, setViewingHistoryEntry] =
    useState<TicketHistoryEntry | null>(null);

  const [logSessions, setLogSessions] = useState<PlatformSessionSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [selectedSessionData, setSelectedSessionData] =
    useState<PlatformContextData | null>(null);
  const [loadingSession, setLoadingSession] = useState(false);
  const [rawLogText, setRawLogText] = useState("");
  const [parsedRawLog, setParsedRawLog] =
    useState<PlatformContextData | null>(null);
  const [parsingRawLog, setParsingRawLog] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function refreshHealth() {
    setLoadingHealth(true);
    try {
      const h = await fetchHealth();
      setHealth(h);
    } catch (err) {
      setHealth({
        status: "degraded",
        ollama_online: false,
        ollama_base_url: "http://127.0.0.1:11434",
        configured_model: "qwen3:4b-instruct",
        model_available: false,
        available_models: [],
        message:
          err instanceof Error
            ? err.message
            : "Backend FastAPI não acessível.",
      });
    } finally {
      setLoadingHealth(false);
    }
  }

  useEffect(() => {
    refreshHealth();
    fetchExamples()
      .then(setExamples)
      .catch(() => setExamples([]))
      .finally(() => setLoadingExamples(false));
    fetchLogSessions()
      .then(setLogSessions)
      .catch(() => setLogSessions([]));
  }, []);

  async function handleAnalyze() {
    setErrorMessage(null);
    setSubmitting(true);
    try {
      const result = await analyzeReport(reportText);
      setAnalysis(result);
      setAnswers(
        result.questions.map((q) => ({
          question_id: q.id,
          field_id: q.field_id,
          question: q.question,
          answer: "",
          skipped: false,
        }))
      );
      setStep(2);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Falha ao analisar relato."
      );
    } finally {
      setSubmitting(false);
    }
  }

  function handleAnswerChange(questionId: string, value: string) {
    setAnswers((prev) =>
      prev.map((a) =>
        a.question_id === questionId ? { ...a, answer: value } : a
      )
    );
  }

  function handleToggleSkip(questionId: string) {
    setAnswers((prev) =>
      prev.map((a) =>
        a.question_id === questionId ? { ...a, skipped: !a.skipped } : a
      )
    );
  }

  async function handleSelectSession(sessionId: string) {
    setSelectedSessionId(sessionId);
    if (!sessionId) {
      setSelectedSessionData(null);
      return;
    }
    setLoadingSession(true);
    try {
      const data = await fetchLogSession(sessionId);
      setSelectedSessionData(data);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Erro ao consultar log da sessão."
      );
      setSelectedSessionData(null);
    } finally {
      setLoadingSession(false);
    }
  }

  async function handleParseRawLog() {
    setErrorMessage(null);
    setParsingRawLog(true);
    try {
      const parsed = await parseRawLog(rawLogText);
      setParsedRawLog(parsed);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Erro ao processar log bruto."
      );
    } finally {
      setParsingRawLog(false);
    }
  }

  async function handleGenerate() {
    if (!analysis) return;
    setErrorMessage(null);
    setSubmitting(true);
    try {
      const result = await generateTicket(
        reportText,
        analysis,
        answers,
        selectedSessionId,
        rawLogText
      );
      setViewingHistoryEntry(null);
      setTicket(result);
      setHistory(
        saveTicketToHistory({
          originalReport: reportText,
          ticket: result,
          checklistBefore: analysis.checklist,
        })
      );
      setStep(3);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Falha ao gerar ticket."
      );
    } finally {
      setSubmitting(false);
    }
  }

  function handleSelectExample(example: ExamplePreset) {
    setReportText(example.text);
    setSuggestedSessionId(example.suggested_session_id ?? "");
    setSelectedSessionId("");
    setSelectedSessionData(null);
  }

  function handleSelectHistoryEntry(entry: TicketHistoryEntry) {
    setViewingHistoryEntry(entry);
    setTicket(entry.ticket);
    setErrorMessage(null);
    setHistoryOpen(false);
    setStep(3);
  }

  function handleReset() {
    setStep(1);
    setReportText("");
    setSuggestedSessionId("");
    setAnalysis(null);
    setAnswers([]);
    setTicket(null);
    setViewingHistoryEntry(null);
    setSelectedSessionId("");
    setSelectedSessionData(null);
    setRawLogText("");
    setParsedRawLog(null);
    setErrorMessage(null);
  }

  const activeTicket = viewingHistoryEntry?.ticket ?? ticket;
  const activeChecklistBefore: ChecklistItemStatus[] | undefined =
    viewingHistoryEntry
      ? viewingHistoryEntry.checklistBefore
      : analysis?.checklist;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-wrap items-start justify-between gap-4 border-b border-slate-800/80 pb-6">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-indigo-500/30 bg-indigo-500/15 text-indigo-400">
              <Bug className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                QA Triage AI
              </h1>
              <p className="text-xs text-slate-400 sm:text-sm">
                YouShop • Triagem de bugs web, checkout e atendimento WhatsApp — 100% local com Ollama
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-start gap-3">
            <button
              type="button"
              onClick={() => setHistoryOpen(true)}
              className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-slate-200 transition hover:border-indigo-500/60 hover:text-white"
            >
              <History className="h-3.5 w-3.5 text-indigo-400" />
              Histórico ({history.length})
            </button>

            <OllamaStatusBadge
              health={health}
              loading={loadingHealth}
              onRefresh={refreshHealth}
            />
          </div>
        </header>

        <StepIndicator currentStep={step} />

        {errorMessage && (
          <div
            role="alert"
            className="mb-6 flex items-start gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200"
          >
            <AlertOctagon className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
            <div>
              <p className="font-semibold">Não foi possível concluir a etapa</p>
              <p className="mt-0.5 text-xs text-rose-200/90">{errorMessage}</p>
            </div>
          </div>
        )}

        {step === 1 && (
          <ReportInputStep
            reportText={reportText}
            onChangeText={(txt) => {
              setReportText(txt);
              if (!txt.trim()) {
                setSuggestedSessionId("");
              }
            }}
            onSelectExample={handleSelectExample}
            examples={examples}
            loadingExamples={loadingExamples}
            submitting={submitting}
            onSubmit={handleAnalyze}
          />
        )}

        {step === 2 && analysis && (
          <ClarificationStep
            analysis={analysis}
            answers={answers}
            onChangeAnswer={handleAnswerChange}
            onToggleSkip={handleToggleSkip}
            logSessions={logSessions}
            selectedSessionId={selectedSessionId}
            suggestedSessionId={suggestedSessionId}
            selectedSessionData={selectedSessionData}
            loadingSession={loadingSession}
            onSelectSession={handleSelectSession}
            rawLogText={rawLogText}
            parsedRawLog={parsedRawLog}
            parsingRawLog={parsingRawLog}
            onChangeRawLog={(txt) => {
              setRawLogText(txt);
              if (!txt.trim()) setParsedRawLog(null);
            }}
            onParseRawLog={handleParseRawLog}
            onBack={() => {
              setErrorMessage(null);
              setStep(1);
            }}
            onGenerate={handleGenerate}
            submitting={submitting}
          />
        )}

        {step === 3 && activeTicket && (
          <StructuredTicketView
            ticket={activeTicket}
            checklistBefore={activeChecklistBefore}
            onBackToQuestions={
              viewingHistoryEntry
                ? undefined
                : () => {
                    setErrorMessage(null);
                    setStep(2);
                  }
            }
            onReset={handleReset}
          />
        )}
      </div>

      <TicketHistoryDrawer
        open={historyOpen}
        entries={history}
        onClose={() => setHistoryOpen(false)}
        onSelectEntry={handleSelectHistoryEntry}
        onDeleteEntry={(id) => {
          setHistory(deleteTicketFromHistory(id));
          if (viewingHistoryEntry?.id === id) {
            handleReset();
          }
        }}
        onClearAll={() => {
          setHistory(clearTicketHistory());
          if (viewingHistoryEntry) {
            handleReset();
          }
        }}
      />
    </div>
  );
}

export default App;
