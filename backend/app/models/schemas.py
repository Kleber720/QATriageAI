from typing import Literal
from pydantic import BaseModel, Field

FieldStatus = Literal["confirmed", "partial", "missing"]
ReportCategory = Literal["bug_funcional", "erro_bloqueante", "erro_integracao", "indefinido"]
InputMode = Literal["vague_report", "draft_ticket"]
DataOrigin = Literal["user_report", "platform_log", "unconfirmed", "ai_hypothesis"]


class LogEvent(BaseModel):
    timestamp: str
    level: Literal["INFO", "WARN", "ERROR", "FATAL"]
    component: str
    message: str
    error_code: str = ""


class PlatformEnvironment(BaseModel):
    application: str = ""
    platform: str = ""
    build: str = ""
    os: str = ""
    hardware_summary: str = ""


class PlatformSessionSummary(BaseModel):
    session_id: str
    title: str
    application: str
    build: str
    summary: str


class PlatformContextData(BaseModel):
    session_id: str = ""
    source_type: Literal["mock_telemetry", "raw_log"]
    environment: PlatformEnvironment = Field(default_factory=PlatformEnvironment)
    events: list[LogEvent] = Field(default_factory=list)
    extracted_error_codes: list[str] = Field(default_factory=list)
    raw_excerpt: str = ""
    pii_redactions: list[str] = Field(default_factory=list)


class RawLogParseRequest(BaseModel):
    raw_log_text: str = Field(..., min_length=5, max_length=12000)


class ProvenanceFact(BaseModel):
    fact: str
    origin: DataOrigin
    reference: str = ""


class LogDivergence(BaseModel):
    relato_usuario: str
    evidencia_log: str
    explicacao: str


class ChecklistItemStatus(BaseModel):
    field_id: str
    label: str
    status: FieldStatus
    evidence_excerpt: str = ""
    note: str = ""


class SpellingIssue(BaseModel):
    original: str
    suggestion: str
    context: str = ""


class ClarificationQuestion(BaseModel):
    id: str
    field_id: str
    question: str
    why_needed: str
    placeholder: str = ""
    priority: Literal["critical", "high", "medium"] = "high"


class AnalyzeRequest(BaseModel):
    report_text: str = Field(..., min_length=5, max_length=12000)


class AnalyzeResponse(BaseModel):
    input_mode: InputMode
    category: ReportCategory
    summary: str
    reproducibility_score: int = Field(..., ge=0, le=100)
    checklist: list[ChecklistItemStatus]
    detected_issues: list[str]
    spelling_issues: list[SpellingIssue]
    pii_warnings: list[str]
    questions: list[ClarificationQuestion]
    ready_without_questions: bool


class QuestionAnswer(BaseModel):
    question_id: str
    field_id: str
    question: str
    answer: str = ""
    skipped: bool = False


class GenerateRequest(BaseModel):
    original_report: str = Field(..., min_length=5, max_length=12000)
    analysis: AnalyzeResponse
    answers: list[QuestionAnswer] = Field(default_factory=list)
    platform_session_id: str = ""
    raw_log_text: str = Field(default="", max_length=12000)


class UnconfirmedItem(BaseModel):
    campo: str
    motivo: str
    impacto_para_qa: str
    hipotese_da_ia: str = ""


class SpellingCorrection(BaseModel):
    original: str
    corrigido: str


class QATicket(BaseModel):
    titulo: str
    categoria: ReportCategory
    etapas_para_reproduzir: list[str]
    resultado_atual: str
    resultado_esperado: str
    descricao: str
    taxa_de_reproducao: str
    notas: str
    o_que_nao_foi_confirmado: list[UnconfirmedItem]
    correcoes_ortograficas: list[SpellingCorrection]
    dados_sensiveis_removidos: list[str]
    score_antes: int = Field(..., ge=0, le=100)
    score_depois: int = Field(..., ge=0, le=100)
    checklist_final: list[ChecklistItemStatus]
    platform_context_used: PlatformContextData | None = None
    origem_dos_dados: list[ProvenanceFact] = Field(default_factory=list)
    divergencias_com_logs: list[LogDivergence] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    ollama_online: bool
    ollama_base_url: str
    configured_model: str
    model_available: bool
    available_models: list[str]
    message: str


class ExamplePreset(BaseModel):
    id: str
    title: str
    badge: str
    description: str
    text: str
    suggested_session_id: str = ""


class LLMChecklistWireItem(BaseModel):
    field_id: str
    status: FieldStatus
    evidence_excerpt: str
    note: str


class LLMSpellingWireItem(BaseModel):
    original: str
    suggestion: str
    context: str


class LLMQuestionWireItem(BaseModel):
    id: str
    field_id: str
    question: str
    why_needed: str
    placeholder: str
    priority: Literal["critical", "high", "medium"]


class LLMAnalyzeWire(BaseModel):
    category: ReportCategory
    summary: str
    checklist_updates: list[LLMChecklistWireItem]
    detected_issues: list[str]
    spelling_issues: list[LLMSpellingWireItem]
    questions: list[LLMQuestionWireItem]


class LLMUnconfirmedWireItem(BaseModel):
    campo: str
    motivo: str
    impacto_para_qa: str
    hipotese_da_ia: str


class LLMSpellingCorrectionWire(BaseModel):
    original: str
    corrigido: str


class LLMProvenanceWireItem(BaseModel):
    fact: str
    origin: DataOrigin
    reference: str


class LLMDivergenceWireItem(BaseModel):
    relato_usuario: str
    evidencia_log: str
    explicacao: str


class LLMGenerateWire(BaseModel):
    titulo: str
    categoria: ReportCategory
    etapas_para_reproduzir: list[str]
    resultado_atual: str
    resultado_esperado: str
    descricao: str
    taxa_de_reproducao: str
    notas: str
    o_que_nao_foi_confirmado: list[LLMUnconfirmedWireItem]
    correcoes_ortograficas: list[LLMSpellingCorrectionWire]
    origem_dos_dados: list[LLMProvenanceWireItem] = Field(default_factory=list)
    divergencias_com_logs: list[LLMDivergenceWireItem] = Field(default_factory=list)
