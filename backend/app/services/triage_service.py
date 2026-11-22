import re
from typing import Iterable

from app.domain.grounding_validator import (
    is_uncertain_or_empty_answer,
    validate_and_ground_ticket,
)
from app.domain.pii_sanitizer import scan_and_sanitize
from app.domain.rule_engine import (
    FIELD_LABELS,
    analyze_deterministically,
    build_fallback_questions,
    compute_score,
)
from app.models.schemas import (
    AnalyzeResponse,
    ChecklistItemStatus,
    ClarificationQuestion,
    FieldStatus,
    GenerateRequest,
    HealthResponse,
    LLMAnalyzeWire,
    LLMGenerateWire,
    LogDivergence,
    PlatformContextData,
    ProvenanceFact,
    QATicket,
    SpellingCorrection,
    SpellingIssue,
    UnconfirmedItem,
)
from app.services.knowledge_loader import load_bug_scope, load_few_shot_examples
from app.services.llm.base import LLMProvider
from app.services.platform_context.base import PlatformContextProvider
from app.services.platform_context.mock_logs_provider import MockLogsProvider
from app.services.platform_context.raw_log_parser import (
    merge_platform_contexts,
    parse_raw_log,
)

_FORBIDDEN_FRICTION_PATTERNS = re.compile(
    r"\b(?:id\s+do\s+dispositivo|id\s+do\s+produto|product\s*id|uuid|"
    r"nome\s+do\s+dispositivo|processador|ram\s+instalada|especifica[cç][oõ]es\s+do\s+pc|dxdiag|"
    r"evid[eê]ncias?|captura\s+de\s+tela|screenshot|prints?|v[ií]deos?|grava[cç][aã]o)\b",
    re.IGNORECASE,
)

_STATUS_RANK: dict[FieldStatus, int] = {"missing": 0, "partial": 1, "confirmed": 2}


def _dedupe_strings(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in items:
        clean = raw.strip()
        if not clean:
            continue
        key = clean.lower()
        if key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def _build_knowledge_digest() -> str:
    scope = load_bug_scope()
    examples = load_few_shot_examples()

    criteria_lines = [
        f"- {c['id']} ({c['label']}, fricção={c['friction']}): {c['guidance']}"
        for c in scope.get("criteria", [])
    ]
    example_lines = [
        f"- {ex['id']} [{ex.get('category', 'indefinido')}]: faltando={ex.get('expected_missing_fields', [])} | lição: {ex.get('key_lesson', '')}"
        for ex in examples
    ]
    return (
        "CRITÉRIOS DO ESCOPO DO BUG:\n"
        + "\n".join(criteria_lines)
        + "\n\nLIÇÕES DOS EXEMPLOS DE TREINAMENTO:\n"
        + "\n".join(example_lines)
    )


def _merge_checklist(
    det_checklist: list[ChecklistItemStatus],
    llm_updates: list,
) -> list[ChecklistItemStatus]:
    llm_by_id = {u.field_id: u for u in llm_updates}
    merged: list[ChecklistItemStatus] = []

    for det_item in det_checklist:
        fid = det_item.field_id
        llm_item = llm_by_id.get(fid)
        if not llm_item:
            merged.append(det_item)
            continue

        final_status = det_item.status
        if _STATUS_RANK[llm_item.status] < _STATUS_RANK[det_item.status]:
            final_status = llm_item.status
        elif det_item.status == "partial" and llm_item.status == "confirmed":
            final_status = "partial"

        final_note = llm_item.note.strip() or det_item.note
        final_excerpt = det_item.evidence_excerpt or llm_item.evidence_excerpt.strip()

        merged.append(
            ChecklistItemStatus(
                field_id=fid,
                label=det_item.label,
                status=final_status,
                evidence_excerpt=final_excerpt,
                note=final_note,
            )
        )
    return merged


def _filter_and_merge_questions(
    llm_questions: list,
    fallback_questions: list[ClarificationQuestion],
    merged_checklist: list[ChecklistItemStatus],
) -> list[ClarificationQuestion]:
    status_by_id = {item.field_id: item.status for item in merged_checklist}
    selected: list[ClarificationQuestion] = []
    field_counts: dict[str, int] = {}
    seen_texts: set[str] = set()
    multi_question_fields = {"repro_steps", "description"}

    for idx, q in enumerate(llm_questions):
        q_text = q.question.strip()
        if not q_text:
            continue
        q_key = q_text.lower()
        if q_key in seen_texts:
            continue
        if q.field_id in {"notes", "evidences"}:
            continue
        if _FORBIDDEN_FRICTION_PATTERNS.search(q_text):
            continue

        fid = q.field_id if q.field_id in FIELD_LABELS else "repro_steps"
        max_for_field = 2 if fid in multi_question_fields else 1
        if field_counts.get(fid, 0) >= max_for_field:
            continue

        if fid not in multi_question_fields and status_by_id.get(fid) == "confirmed":
            continue

        field_counts[fid] = field_counts.get(fid, 0) + 1
        seen_texts.add(q_key)
        selected.append(
            ClarificationQuestion(
                id=q.id.strip() or f"q_{fid}_{idx + 1}",
                field_id=fid,
                question=q_text,
                why_needed=q.why_needed.strip() or "Necessário para tornar o ticket reproduzível pelo QA.",
                placeholder=q.placeholder.strip(),
                priority=q.priority,
            )
        )

    for fb in fallback_questions:
        if field_counts.get(fb.field_id, 0) == 0 and status_by_id.get(fb.field_id) != "confirmed":
            field_counts[fb.field_id] = 1
            seen_texts.add(fb.question.lower())
            selected.append(fb)

    priority_order = {"critical": 0, "high": 1, "medium": 2}
    selected.sort(key=lambda item: priority_order.get(item.priority, 9))
    return selected[:5]


def _format_platform_context_for_prompt(ctx: PlatformContextData) -> str:
    env = ctx.environment
    env_line = (
        f"Sistema/Área={env.application or 'N/A'} | Plataforma/Navegador={env.platform or 'N/A'} | "
        f"Versão={env.build or 'N/A'} | SO={env.os or 'N/A'} | Hardware={env.hardware_summary or 'N/A'}"
    )
    events_lines = [
        f"  - [{ev.timestamp}] {ev.level} [{ev.component}]"
        + (f" ({ev.error_code})" if ev.error_code else "")
        + f": {ev.message}"
        for ev in ctx.events
    ]
    codes = ", ".join(ctx.extracted_error_codes) if ctx.extracted_error_codes else "Nenhum código de erro"
    return (
        f"Sessão: {ctx.session_id} ({ctx.source_type})\n"
        f"Ambiente: {env_line}\n"
        f"Códigos de erro extraídos: {codes}\n"
        "Eventos:\n"
        + ("\n".join(events_lines) if events_lines else ctx.raw_excerpt)
    )


class TriageService:
    def __init__(
        self,
        llm: LLMProvider,
        platform_provider: PlatformContextProvider | None = None,
    ) -> None:
        self.llm = llm
        self.platform_provider = platform_provider or MockLogsProvider()

    async def check_health(self) -> HealthResponse:
        return await self.llm.check_health()

    async def analyze(self, report_text: str) -> AnalyzeResponse:
        det = analyze_deterministically(report_text)
        sanitized_report = scan_and_sanitize(report_text).sanitized_text
        knowledge_digest = _build_knowledge_digest()
        fallback_questions = build_fallback_questions(det)

        det_summary = "\n".join(
            f"- {item.field_id} ({item.label}): {item.status} | {item.note}"
            for item in det.checklist
        )

        system_prompt = (
            "Você é um especialista em Triagem de QA para sistemas web, e-commerce e canais de atendimento (como site YouShop, checkout e atendimento via WhatsApp).\n"
            "Analise o relato de cliente/atendente ou rascunho de ticket em Português (Brasil) e compare com o Escopo Oficial do Bug.\n\n"
            f"{knowledge_digest}\n\n"
            "REGRAS DE RESPOSTA:\n"
            "1. Classifique 'category' rigorosamente:\n"
            "   - 'erro_integracao': falhas em gateway de pagamento, Pix, cartão, webhook do WhatsApp, clipboard/navegador específico ou API externa.\n"
            "   - 'erro_bloqueante': tela branca, travamento, erro fatal/HTTP 500 ou queda de sessão que impede continuar o fluxo.\n"
            "   - 'bug_funcional': defeitos de cupom, cálculo, regra de negócio, botão ou UI incorreta.\n"
            "   - 'indefinido': somente quando o relato for curto demais para inferir a natureza do problema.\n"
            "2. Verifique se há contradições ou omissões entre Descrição e Etapas para Reproduzir "
            "(ex.: etapas param cedo, ou Descrição cita uso de mouse/teclado/código de erro que faltam nas Etapas).\n"
            "3. Liste erros de ortografia reais encontrados no texto.\n"
            "4. Gere NO MÁXIMO 5 perguntas curtas e de BAIXA FRICÇÃO apenas sobre o que falta.\n"
            "5. O campo 'placeholder' de cada pergunta DEVE ser um exemplo curto de resposta (ex.: 'Ex.: 3/3' ou 'Ex.: Chrome Desktop'), NUNCA repita o texto da pergunta.\n"
            "6. NUNCA peça especificações de PC, CPU, RAM, ID do dispositivo ou Product ID ao cliente.\n"
            "7. NUNCA peça ou recomende evidências, prints, capturas de tela ou vídeos.\n"
            "8. Nunca invente informações ausentes."
        )

        user_prompt = (
            f"MODO DETECTADO: {det.input_mode}\n"
            f"PRÉ-DIAGNÓSTICO DETERMINÍSTICO:\n{det_summary}\n"
            f"PROBLEMAS PRÉ-DETECTADOS: {det.detected_issues}\n\n"
            f"TEXTO ENVIADO PELO USUÁRIO:\n\"\"\"\n{sanitized_report}\n\"\"\""
        )

        wire = await self.llm.chat_structured(system_prompt, user_prompt, LLMAnalyzeWire)

        merged_checklist = _merge_checklist(det.checklist, wire.checklist_updates)
        merged_issues = _dedupe_strings([*det.detected_issues, *wire.detected_issues])

        spelling_map: dict[str, SpellingIssue] = {
            s.original.lower(): s for s in det.spelling_issues
        }
        for sp in wire.spelling_issues:
            orig = sp.original.strip()
            sugg = sp.suggestion.strip()
            if orig and sugg and orig.lower() != sugg.lower() and orig.lower() not in spelling_map:
                spelling_map[orig.lower()] = SpellingIssue(
                    original=orig,
                    suggestion=sugg,
                    context=sp.context.strip() or "Ortografia",
                )

        questions = _filter_and_merge_questions(
            wire.questions,
            fallback_questions,
            merged_checklist,
        )
        score = compute_score(merged_checklist)

        return AnalyzeResponse(
            input_mode=det.input_mode,
            category=wire.category,
            summary=wire.summary.strip() or "Análise de triagem concluída.",
            reproducibility_score=score,
            checklist=merged_checklist,
            detected_issues=merged_issues,
            spelling_issues=list(spelling_map.values()),
            pii_warnings=det.pii_warnings,
            questions=questions,
            ready_without_questions=len(questions) == 0,
        )

    def _resolve_platform_context(self, req: GenerateRequest) -> PlatformContextData | None:
        session_ctx: PlatformContextData | None = None
        if req.platform_session_id.strip():
            session_ctx = self.platform_provider.lookup_session(req.platform_session_id)

        raw_ctx: PlatformContextData | None = None
        if req.raw_log_text.strip():
            raw_ctx = parse_raw_log(req.raw_log_text)

        return merge_platform_contexts(session_ctx, raw_ctx)

    async def generate(self, req: GenerateRequest) -> QATicket:
        sanitized_original = scan_and_sanitize(req.original_report).sanitized_text
        platform_context = self._resolve_platform_context(req)

        answers_lines: list[str] = []
        for ans in req.answers:
            if ans.skipped or is_uncertain_or_empty_answer(ans.answer):
                answers_lines.append(
                    f"- [{ans.field_id}] Pergunta: {ans.question} -> RESPOSTA: NÃO RESPONDIDO / PULADO (NÃO INVENTAR; registrar em o_que_nao_foi_confirmado)"
                )
            else:
                answers_lines.append(
                    f"- [{ans.field_id}] Pergunta: {ans.question} -> RESPOSTA DO USUÁRIO: {ans.answer.strip()}"
                )
        answers_block = "\n".join(answers_lines) if answers_lines else "Nenhuma pergunta adicional respondida."

        if platform_context is not None:
            logs_instruction = (
                "10. DADOS DE PLATAFORMA / LOGS DISPONÍVEIS:\n"
                "    - Cruze os eventos, códigos de erro e ambiente dos logs com o relato do usuário.\n"
                "    - Inclua códigos de erro e evidências técnicas relevantes nas NOTAS (e nas Etapas/Descrição se clarificarem o defeito).\n"
                "    - Em 'origem_dos_dados', separe claramente fatos com origin='user_report', 'platform_log', 'unconfirmed' ou 'ai_hypothesis'.\n"
                "    - Se houver divergência entre o que o usuário achou que aconteceu e o que o log mostra, registre em 'divergencias_com_logs'."
            )
            logs_user_block = (
                "\n\nDADOS CRUZADOS DA PLATAFORMA / LOGS:\n"
                + _format_platform_context_for_prompt(platform_context)
            )
        else:
            logs_instruction = (
                "10. Nenhum log da plataforma foi anexado: NÃO crie entradas com origin='platform_log' "
                "e retorne 'divergencias_com_logs' como lista vazia []."
            )
            logs_user_block = ""

        system_prompt = (
            "Você é um especialista sênior em QA para plataformas web, e-commerce e atendimento (como YouShop e WhatsApp).\n"
            "Gere o ticket estruturado final em Português (Brasil) seguindo EXATAMENTE o Escopo Oficial do Bug.\n\n"
            "REGRAS OBRIGATÓRIAS:\n"
            "1. 'etapas_para_reproduzir': lista de strings em ordem cronológica.\n"
            "   - A primeira linha deve seguir: 'Acesse [sistema/área] em [dispositivo + navegador] + versão [se informada]' "
            "(se dispositivo, navegador ou versão não foram confirmados pelo usuário nem por logs, indique claramente sem inventar).\n"
            "   - Inclua 'É aqui que o bug é observado' APENAS UMA ÚNICA VEZ, exatamente na última linha da lista.\n"
            "2. 'resultado_atual': 1 linha objetiva com o comportamento observado.\n"
            "3. 'resultado_esperado': 1 linha objetiva com o comportamento pretendido.\n"
            "4. 'descricao': detalhamento coeso do defeito observado e sua localização exata no sistema.\n"
            "5. 'taxa_de_reproducao': formato 'X/Y' APENAS se informado pelo usuário. Caso contrário, escreva exatamente 'Não informado'.\n"
            "6. 'notas': observações úteis para QA (ex.: comparação entre navegadores/dispositivos, comportamento teclado vs mouse, hardware útil sem dados sensíveis, códigos de erro de log). Use 'N/A' se não houver.\n"
            "7. 'o_que_nao_foi_confirmado': REGRA MAIS IMPORTANTE (Reconhecer os Limites). Liste TODO campo que faltou, foi pulado ou ficou vago, explicando motivo e impacto para QA (NÃO inclua evidências/prints/vídeos aqui). Só preencha 'hipotese_da_ia' se houver uma suposição clara a sinalizar.\n"
            "8. Corrija erros de ortografia e acentuação no ticket final e liste-os em 'correcoes_ortograficas', sem alterar os fatos.\n"
            f"{logs_instruction}"
        )

        user_prompt = (
            f"CATEGORIA IDENTIFICADA: {req.analysis.category}\n"
            f"PROBLEMAS DETECTADOS NA TRIAGEM: {req.analysis.detected_issues}\n\n"
            f"RELATO / RASCUNHO ORIGINAL:\n\"\"\"\n{sanitized_original}\n\"\"\"\n\n"
            f"RESPOSTAS DE ESCLARECIMENTO:\n{answers_block}"
            f"{logs_user_block}"
        )

        wire = await self.llm.chat_structured(system_prompt, user_prompt, LLMGenerateWire)

        raw_ticket = QATicket(
            titulo=wire.titulo,
            categoria=wire.categoria,
            etapas_para_reproduzir=wire.etapas_para_reproduzir,
            resultado_atual=wire.resultado_atual,
            resultado_esperado=wire.resultado_esperado,
            descricao=wire.descricao,
            taxa_de_reproducao=wire.taxa_de_reproducao,
            notas=wire.notas,
            o_que_nao_foi_confirmado=[
                UnconfirmedItem(
                    campo=item.campo,
                    motivo=item.motivo,
                    impacto_para_qa=item.impacto_para_qa,
                    hipotese_da_ia=item.hipotese_da_ia,
                )
                for item in wire.o_que_nao_foi_confirmado
            ],
            correcoes_ortograficas=[
                SpellingCorrection(original=c.original, corrigido=c.corrigido)
                for c in wire.correcoes_ortograficas
                if c.original.strip() and c.corrigido.strip() and c.original.strip() != c.corrigido.strip()
            ],
            dados_sensiveis_removidos=[],
            score_antes=req.analysis.reproducibility_score,
            score_depois=req.analysis.reproducibility_score,
            checklist_final=req.analysis.checklist,
            origem_dos_dados=[
                ProvenanceFact(
                    fact=item.fact,
                    origin=item.origin,
                    reference=item.reference,
                )
                for item in wire.origem_dos_dados
            ],
            divergencias_com_logs=[
                LogDivergence(
                    relato_usuario=d.relato_usuario,
                    evidencia_log=d.evidencia_log,
                    explicacao=d.explicacao,
                )
                for d in wire.divergencias_com_logs
            ],
        )

        return validate_and_ground_ticket(
            original_report=req.original_report,
            analysis=req.analysis,
            answers=req.answers,
            raw_ticket=raw_ticket,
            platform_context=platform_context,
        )
