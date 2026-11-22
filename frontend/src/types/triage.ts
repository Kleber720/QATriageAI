export type FieldStatus = "confirmed" | "partial" | "missing";

export type ReportCategory =
  | "bug_funcional"
  | "erro_bloqueante"
  | "erro_integracao"
  | "indefinido";

export type InputMode = "vague_report" | "draft_ticket";

export type DataOrigin =
  | "user_report"
  | "platform_log"
  | "unconfirmed"
  | "ai_hypothesis";

export interface LogEvent {
  timestamp: string;
  level: "INFO" | "WARN" | "ERROR" | "FATAL";
  component: string;
  message: string;
  error_code: string;
}

export interface PlatformEnvironment {
  application: string;
  platform: string;
  build: string;
  os: string;
  hardware_summary: string;
}

export interface PlatformSessionSummary {
  session_id: string;
  title: string;
  application: string;
  build: string;
  summary: string;
}

export interface PlatformContextData {
  session_id: string;
  source_type: "mock_telemetry" | "raw_log";
  environment: PlatformEnvironment;
  events: LogEvent[];
  extracted_error_codes: string[];
  raw_excerpt: string;
  pii_redactions: string[];
}

export interface ProvenanceFact {
  fact: string;
  origin: DataOrigin;
  reference: string;
}

export interface LogDivergence {
  relato_usuario: string;
  evidencia_log: string;
  explicacao: string;
}

export interface ChecklistItemStatus {
  field_id: string;
  label: string;
  status: FieldStatus;
  evidence_excerpt: string;
  note: string;
}

export interface SpellingIssue {
  original: string;
  suggestion: string;
  context: string;
}

export interface ClarificationQuestion {
  id: string;
  field_id: string;
  question: string;
  why_needed: string;
  placeholder: string;
  priority: "critical" | "high" | "medium";
}

export interface AnalyzeResponse {
  input_mode: InputMode;
  category: ReportCategory;
  summary: string;
  reproducibility_score: number;
  checklist: ChecklistItemStatus[];
  detected_issues: string[];
  spelling_issues: SpellingIssue[];
  pii_warnings: string[];
  questions: ClarificationQuestion[];
  ready_without_questions: boolean;
}

export interface QuestionAnswer {
  question_id: string;
  field_id: string;
  question: string;
  answer: string;
  skipped: boolean;
}

export interface UnconfirmedItem {
  campo: string;
  motivo: string;
  impacto_para_qa: string;
  hipotese_da_ia: string;
}

export interface SpellingCorrection {
  original: string;
  corrigido: string;
}

export interface QATicket {
  titulo: string;
  categoria: ReportCategory;
  etapas_para_reproduzir: string[];
  resultado_atual: string;
  resultado_esperado: string;
  descricao: string;
  taxa_de_reproducao: string;
  notas: string;
  o_que_nao_foi_confirmado: UnconfirmedItem[];
  correcoes_ortograficas: SpellingCorrection[];
  dados_sensiveis_removidos: string[];
  score_antes: number;
  score_depois: number;
  checklist_final: ChecklistItemStatus[];
  platform_context_used: PlatformContextData | null;
  origem_dos_dados: ProvenanceFact[];
  divergencias_com_logs: LogDivergence[];
}

export interface HealthResponse {
  status: "ok" | "degraded";
  ollama_online: boolean;
  ollama_base_url: string;
  configured_model: string;
  model_available: boolean;
  available_models: string[];
  message: string;
}

export interface ExamplePreset {
  id: string;
  title: string;
  badge: string;
  description: string;
  text: string;
  suggested_session_id: string;
}

export interface TicketHistoryEntry {
  id: string;
  createdAt: string;
  originalReport: string;
  ticket: QATicket;
  checklistBefore?: ChecklistItemStatus[];
}
