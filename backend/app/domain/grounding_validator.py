import re
import unicodedata

from app.domain.pii_sanitizer import scan_and_sanitize
from app.domain.rule_engine import FIELD_LABELS, compute_score
from app.models.schemas import (
    AnalyzeResponse,
    ChecklistItemStatus,
    LogDivergence,
    PlatformContextData,
    ProvenanceFact,
    QATicket,
    QuestionAnswer,
    UnconfirmedItem,
)

_RATIO_PATTERN = re.compile(r"\b\d+\s*/\s*\d+\b")
_NUM_TOKEN = r"(?:\d+|uma|duas|tr[eê]s|quatro|cinco|seis|sete|oito|nove|dez|[uú]nica)"
_FREQ_PHRASE_PATTERN = re.compile(
    rf"\b(?:{_NUM_TOKEN}\s+(?:de|em)\s+{_NUM_TOKEN}|{_NUM_TOKEN}\s+vez(?:es)?|toda\s+vez|sempre\s+acontece|todas\s+as\s+vezes)\b",
    re.IGNORECASE,
)
_MARKER_ANY_PATTERN = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ée]\s+)?aqui\s+(?:que\s+)?o\s+bug\s+[ée]\s+observado\.?\s*$",
    re.IGNORECASE,
)
_FORBIDDEN_UNCONFIRMED_FIELD_RE = re.compile(
    r"\b(?:evid[eê]ncias?|prints?|screenshots?|capturas?(?:\s+de\s+tela)?|v[ií]deos?|grava[cç][oõ]es)\b",
    re.IGNORECASE,
)
_UNCERTAIN_ANSWER_PATTERN = re.compile(
    r"^(?:n[aã]o\s+sei|n[aã]o\s+lembro|n[aã]o\s+reparei|n[aã]o\s+tenho(?:\s+certeza)?|"
    r"sei\s+l[aá]|pular|n/?a|nenhum(?:a)?|desconhecido|\?+|\-+)$",
    re.IGNORECASE,
)


def is_uncertain_or_empty_answer(answer: str) -> bool:
    cleaned = answer.strip().rstrip(".!")
    if not cleaned:
        return True
    return bool(_UNCERTAIN_ANSWER_PATTERN.match(cleaned))


def _normalize_key(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


def _has_unconfirmed_entry(items: list[UnconfirmedItem], field_id: str, label: str) -> bool:
    targets = {_normalize_key(field_id), _normalize_key(label)}
    if field_id == "platform_environment":
        targets.update({"ambiente", "sistema", "dispositivo", "navegador", "versao", "plataforma", "sistema dispositivo e navegador"})
    elif field_id == "repro_steps":
        targets.update({"etapas", "etapas para reproduzir", "passos"})
    elif field_id == "actual_result":
        targets.update({"resultado atual"})
    elif field_id == "expected_result":
        targets.update({"resultado esperado"})
    elif field_id == "repro_rate":
        targets.update({"taxa", "taxa de reproducao"})

    for item in items:
        norm = _normalize_key(item.campo)
        if any(t and (t == norm or t in norm or norm in t) for t in targets):
            return True
    return False


def _add_unconfirmed_if_missing(
    items: list[UnconfirmedItem],
    field_id: str,
    motivo: str,
    impacto: str,
) -> None:
    label = FIELD_LABELS.get(field_id, field_id)
    if not _has_unconfirmed_entry(items, field_id, label):
        items.append(
            UnconfirmedItem(
                campo=label,
                motivo=motivo,
                impacto_para_qa=impacto,
                hipotese_da_ia="",
            )
        )


def _normalize_steps(steps: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in steps:
        line = raw.strip()
        if not line:
            continue
        if _MARKER_ANY_PATTERN.match(line):
            continue
        if not cleaned or cleaned[-1].lower() != line.lower():
            cleaned.append(line)

    if cleaned:
        cleaned.append("É aqui que o bug é observado")
    return cleaned


def _append_unique_provenance(
    items: list[ProvenanceFact],
    candidate: ProvenanceFact,
) -> None:
    cand_key = _normalize_key(candidate.fact)
    for existing in items:
        if existing.origin == candidate.origin:
            ex_key = _normalize_key(existing.fact)
            if cand_key == ex_key or (len(cand_key) > 12 and (cand_key in ex_key or ex_key in cand_key)):
                return
    items.append(candidate)


def validate_and_ground_ticket(
    original_report: str,
    analysis: AnalyzeResponse,
    answers: list[QuestionAnswer],
    raw_ticket: QATicket,
    platform_context: PlatformContextData | None = None,
) -> QATicket:
    answered_parts = [
        ans.answer.strip()
        for ans in answers
        if not ans.skipped and not is_uncertain_or_empty_answer(ans.answer)
    ]
    combined_source_text = "\n".join([original_report, *answered_parts])

    unconfirmed = [
        item
        for item in raw_ticket.o_que_nao_foi_confirmado
        if not _FORBIDDEN_UNCONFIRMED_FIELD_RE.search(item.campo)
    ]
    answers_by_field: dict[str, QuestionAnswer] = {ans.field_id: ans for ans in answers}

    for ans in answers:
        is_unanswered = ans.skipped or is_uncertain_or_empty_answer(ans.answer)
        if is_unanswered:
            _add_unconfirmed_if_missing(
                unconfirmed,
                ans.field_id,
                "Pergunta pulada ou respondida com incerteza ('não sei') pelo usuário.",
                "O QA precisará verificar ou validar este ponto manualmente durante a reprodução.",
            )

    has_rate_in_source = bool(
        _RATIO_PATTERN.search(combined_source_text)
        or _FREQ_PHRASE_PATTERN.search(combined_source_text)
    )
    taxa = raw_ticket.taxa_de_reproducao.strip()
    if not has_rate_in_source:
        taxa = "Não informado"
        _add_unconfirmed_if_missing(
            unconfirmed,
            "repro_rate",
            "Nenhuma contagem de tentativas/ocorrências (X/Y) foi informada.",
            "Não é possível saber se o defeito é constante (ex.: 3/3) ou intermitente.",
        )
    elif not taxa:
        taxa = "Não informado"

    normalized_steps = _normalize_steps(raw_ticket.etapas_para_reproduzir)

    all_redactions: list[str] = list(raw_ticket.dados_sensiveis_removidos)
    if platform_context is not None:
        for red in platform_context.pii_redactions:
            if red not in all_redactions:
                all_redactions.append(red)

    def _sanitize_field(value: str) -> str:
        res = scan_and_sanitize(value)
        for red in res.redactions:
            if red not in all_redactions:
                all_redactions.append(red)
        return res.sanitized_text

    sanitized_notas = _sanitize_field(raw_ticket.notas)
    sanitized_desc = _sanitize_field(raw_ticket.descricao)
    sanitized_actual = _sanitize_field(raw_ticket.resultado_atual)
    sanitized_expected = _sanitize_field(raw_ticket.resultado_esperado)
    sanitized_steps = [_sanitize_field(step) for step in normalized_steps]

    env_confirmed_by_log = bool(
        platform_context is not None
        and platform_context.environment.application
        and platform_context.environment.build
    )

    final_checklist: list[ChecklistItemStatus] = []
    for item in analysis.checklist:
        fid = item.field_id
        ans = answers_by_field.get(fid)
        answered_ok = bool(
            ans and not ans.skipped and not is_uncertain_or_empty_answer(ans.answer)
        )

        new_status = item.status
        new_excerpt = item.evidence_excerpt
        new_note = item.note

        if fid == "repro_rate":
            if taxa != "Não informado" and (_RATIO_PATTERN.search(taxa) or has_rate_in_source):
                new_status = "confirmed"
                new_excerpt = taxa
                new_note = "Taxa confirmada a partir do relato/respostas."
            else:
                new_status = "missing"
                new_excerpt = ""
                new_note = "Não informado (registrado em O que não foi confirmado)."
        elif fid == "notes":
            if sanitized_notas and sanitized_notas.lower() not in {"n/a", "não informado"}:
                new_status = "confirmed"
                new_excerpt = sanitized_notas[:140]
                new_note = "Notas registradas."
        elif fid == "platform_environment" and new_status in {"missing", "partial"} and env_confirmed_by_log and platform_context is not None:
            env = platform_context.environment
            new_status = "confirmed"
            new_excerpt = " | ".join(p for p in [env.application, env.platform, env.build] if p)
            new_note = "Confirmado automaticamente via log da plataforma."
        elif answered_ok and ans is not None:
            new_status = "confirmed"
            new_excerpt = ans.answer.strip()[:140]
            new_note = "Confirmado pelo usuário na etapa de esclarecimento."
        elif item.status == "missing" and fid != "notes":
            _add_unconfirmed_if_missing(
                unconfirmed,
                fid,
                "Campo ausente no relato e sem resposta fornecida.",
                "Informação pendente de verificação pelo QA.",
            )

        final_checklist.append(
            ChecklistItemStatus(
                field_id=fid,
                label=item.label,
                status=new_status,
                evidence_excerpt=new_excerpt,
                note=new_note,
            )
        )

    provenance: list[ProvenanceFact] = []
    for fact_item in raw_ticket.origem_dos_dados:
        if not fact_item.fact.strip():
            continue
        if platform_context is None and fact_item.origin == "platform_log":
            continue
        _append_unique_provenance(
            provenance,
            ProvenanceFact(
                fact=_sanitize_field(fact_item.fact.strip()),
                origin=fact_item.origin,
                reference=fact_item.reference.strip(),
            ),
        )

    divergences: list[LogDivergence] = []
    if platform_context is not None:
        for div in raw_ticket.divergencias_com_logs:
            if div.relato_usuario.strip() and div.evidencia_log.strip():
                divergences.append(
                    LogDivergence(
                        relato_usuario=_sanitize_field(div.relato_usuario.strip()),
                        evidencia_log=_sanitize_field(div.evidencia_log.strip()),
                        explicacao=_sanitize_field(div.explicacao.strip()),
                    )
                )

        env = platform_context.environment
        env_parts = [p for p in [env.application, env.platform, env.build, env.os] if p]
        if env_parts:
            _append_unique_provenance(
                provenance,
                ProvenanceFact(
                    fact=f"Ambiente detectado nos logs: {' • '.join(env_parts)}",
                    origin="platform_log",
                    reference=platform_context.session_id,
                ),
            )

        critical_events = [
            ev for ev in platform_context.events if ev.level in {"ERROR", "FATAL"}
        ]
        if critical_events:
            for ev in critical_events:
                ref = f"{platform_context.session_id} @ {ev.timestamp}"
                if ev.error_code:
                    ref = f"{ref} ({ev.error_code})"
                _append_unique_provenance(
                    provenance,
                    ProvenanceFact(
                        fact=f"[{ev.level}] [{ev.component}] {ev.message}",
                        origin="platform_log",
                        reference=ref,
                    ),
                )
        elif platform_context.events:
            last_ev = platform_context.events[-1]
            _append_unique_provenance(
                provenance,
                ProvenanceFact(
                    fact=f"[{last_ev.level}] [{last_ev.component}] {last_ev.message}",
                    origin="platform_log",
                    reference=f"{platform_context.session_id} @ {last_ev.timestamp}",
                ),
            )

    if not any(p.origin == "user_report" for p in provenance):
        _append_unique_provenance(
            provenance,
            ProvenanceFact(
                fact=f"Relato do problema: {(sanitized_actual or original_report)[:140]}",
                origin="user_report",
                reference="Relato / Respostas do usuário",
            ),
        )

    for u in unconfirmed:
        _append_unique_provenance(
            provenance,
            ProvenanceFact(
                fact=f"{u.campo}: {u.motivo}",
                origin="unconfirmed",
                reference="O que não foi confirmado",
            ),
        )

    score_antes = analysis.reproducibility_score
    score_depois = compute_score(final_checklist)

    return QATicket(
        titulo=raw_ticket.titulo.strip() or "Bug reportado (título pendente)",
        categoria=raw_ticket.categoria,
        etapas_para_reproduzir=sanitized_steps,
        resultado_atual=sanitized_actual or "Não informado",
        resultado_esperado=sanitized_expected or "Não informado",
        descricao=sanitized_desc or "Não informado",
        taxa_de_reproducao=taxa,
        notas=sanitized_notas or "N/A",
        o_que_nao_foi_confirmado=unconfirmed,
        correcoes_ortograficas=raw_ticket.correcoes_ortograficas,
        dados_sensiveis_removidos=all_redactions,
        score_antes=score_antes,
        score_depois=score_depois,
        checklist_final=final_checklist,
        platform_context_used=platform_context,
        origem_dos_dados=provenance,
        divergencias_com_logs=divergences,
    )
