import type {
  AnalyzeResponse,
  ExamplePreset,
  HealthResponse,
  PlatformContextData,
  PlatformSessionSummary,
  QATicket,
  QuestionAnswer,
} from "../types/triage";

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch {
  }
  return `Erro HTTP ${response.status} ao comunicar com o backend.`;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });
  } catch {
    throw new Error(
      "Não foi possível conectar ao backend FastAPI (http://127.0.0.1:8000). Verifique se o servidor Python está rodando."
    );
  }

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }
  return (await response.json()) as T;
}

export function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/health");
}

export function fetchExamples(): Promise<ExamplePreset[]> {
  return requestJson<ExamplePreset[]>("/api/triage/examples");
}

export function analyzeReport(reportText: string): Promise<AnalyzeResponse> {
  return requestJson<AnalyzeResponse>("/api/triage/analyze", {
    method: "POST",
    body: JSON.stringify({ report_text: reportText }),
  });
}

export function fetchLogSessions(): Promise<PlatformSessionSummary[]> {
  return requestJson<PlatformSessionSummary[]>("/api/logs/sessions");
}

export function fetchLogSession(sessionId: string): Promise<PlatformContextData> {
  return requestJson<PlatformContextData>(
    `/api/logs/sessions/${encodeURIComponent(sessionId)}`
  );
}

export function parseRawLog(rawLogText: string): Promise<PlatformContextData> {
  return requestJson<PlatformContextData>("/api/logs/parse", {
    method: "POST",
    body: JSON.stringify({ raw_log_text: rawLogText }),
  });
}

export function generateTicket(
  originalReport: string,
  analysis: AnalyzeResponse,
  answers: QuestionAnswer[],
  platformSessionId = "",
  rawLogText = ""
): Promise<QATicket> {
  return requestJson<QATicket>("/api/triage/generate", {
    method: "POST",
    body: JSON.stringify({
      original_report: originalReport,
      analysis,
      answers,
      platform_session_id: platformSessionId,
      raw_log_text: rawLogText,
    }),
  });
}
