import re
from dataclasses import dataclass, field

from app.domain.pii_sanitizer import scan_and_sanitize
from app.models.schemas import (
    ChecklistItemStatus,
    ClarificationQuestion,
    FieldStatus,
    InputMode,
    SpellingIssue,
)

SECTION_WEIGHTS: dict[str, int] = {
    "platform_environment": 15,
    "repro_steps": 25,
    "actual_result": 15,
    "expected_result": 15,
    "description": 15,
    "repro_rate": 15,
    "notes": 0,
}

FIELD_LABELS: dict[str, str] = {
    "platform_environment": "Sistema, Dispositivo e Navegador",
    "repro_steps": "Etapas para Reproduzir",
    "actual_result": "Resultado Atual",
    "expected_result": "Resultado Esperado",
    "description": "Descrição",
    "repro_rate": "Taxa de Reprodução",
    "notes": "NOTAS",
}

_HEADER_PATTERN = re.compile(
    r"^\s*(?P<header>"
    r"Etapas\s+para\s+Reproduzir|"
    r"Resultado\s+Atual|"
    r"Resultado\s+Esperado|"
    r"Descri[cç][aã]o|"
    r"Taxa\s+de\s+Reprodu[cç][aã]o|"
    r"Notas|"
    r"Evid[eê]ncias?"
    r")\s*:\s*(?P<inline>.*)$",
    re.IGNORECASE,
)

_HEADER_CANONICAL_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"etapas", re.IGNORECASE), "repro_steps"),
    (re.compile(r"resultado\s+atual", re.IGNORECASE), "actual_result"),
    (re.compile(r"resultado\s+esperado", re.IGNORECASE), "expected_result"),
    (re.compile(r"descri", re.IGNORECASE), "description"),
    (re.compile(r"taxa", re.IGNORECASE), "repro_rate"),
    (re.compile(r"notas", re.IGNORECASE), "notes"),
    (re.compile(r"evid", re.IGNORECASE), "evidences"),
]

_PLATFORM_KEYWORDS = (
    "web",
    "site",
    "desktop",
    "mobile",
    "chrome",
    "firefox",
    "safari",
    "edge",
    "android",
    "ios",
    "iphone",
    "windows",
    "macos",
    "whatsapp",
    "app",
    "navegador",
    "plataforma",
    "youshop",
    "x64",
    "64x",
)

_FIRST_LINE_STARTERS = ("acesse", "abra", "entre", "inicie")

_BUILD_PATTERN = re.compile(
    r"\b(?:build\s*[a-z0-9_.\-\[\]]*|v\d+\.\d+(?:\.\d+)*|vers[aã]o\s*[a-z0-9_.\-]+)\b",
    re.IGNORECASE,
)

_RATIO_PATTERN = re.compile(r"\b\d+\s*/\s*\d+\b")
_MARKER_LINE_PATTERN = re.compile(
    r"(?:[ée]\s+)?aqui\s+(?:que\s+)?o\s+bug\s+[ée]\s+observado",
    re.IGNORECASE,
)

_COMMON_SPELLING_CORRECTIONS: list[tuple[str, str]] = [
    ("pricipal", "principal"),
    ("pagina", "página"),
    ("codigo", "código"),
    ("usuario", "usuário"),
    ("numero", "número"),
    ("cartao", "cartão"),
    ("credito", "crédito"),
    ("escritorio", "escritório"),
    ("multiplas", "múltiplas"),
    ("muliplas", "múltiplas"),
    ("obersavado", "observado"),
    ("obervado", "observado"),
]


@dataclass
class DeterministicAnalysis:
    input_mode: InputMode
    sections: dict[str, str]
    checklist: list[ChecklistItemStatus]
    reproducibility_score: int
    detected_issues: list[str] = field(default_factory=list)
    spelling_issues: list[SpellingIssue] = field(default_factory=list)
    pii_warnings: list[str] = field(default_factory=list)
    suspected_missing_steps: bool = False
    marker_status: str = "missing"


def _canonical_header(raw_header: str) -> str:
    for pattern, key in _HEADER_CANONICAL_MAP:
        if pattern.search(raw_header):
            return key
    return ""


def parse_ticket_sections(text: str) -> tuple[InputMode, dict[str, str]]:
    sections: dict[str, list[str]] = {}
    current_key: str | None = None
    matched_headers = 0

    for line in text.splitlines():
        match = _HEADER_PATTERN.match(line)
        if match:
            matched_headers += 1
            current_key = _canonical_header(match.group("header"))
            sections.setdefault(current_key, [])
            inline = match.group("inline").strip()
            if inline:
                sections[current_key].append(inline)
        elif current_key is not None:
            sections[current_key].append(line)

    input_mode: InputMode = "draft_ticket" if matched_headers >= 2 else "vague_report"
    joined = {k: "\n".join(v).strip() for k, v in sections.items()}
    return input_mode, joined


def compute_score(checklist: list[ChecklistItemStatus]) -> int:
    total_weight = sum(SECTION_WEIGHTS.values())
    if total_weight == 0:
        return 0
    earned = 0.0
    for item in checklist:
        weight = SECTION_WEIGHTS.get(item.field_id, 0)
        if item.status == "confirmed":
            earned += weight
        elif item.status == "partial":
            earned += weight * 0.5
    return max(0, min(100, round((earned / total_weight) * 100)))


def _strip_section_headers(text: str) -> str:
    content_lines: list[str] = []
    for line in text.splitlines():
        match = _HEADER_PATTERN.match(line)
        if match:
            inline = match.group("inline").strip()
            if inline:
                content_lines.append(inline)
        else:
            content_lines.append(line)
    return "\n".join(content_lines)


def _detect_spelling_issues(text: str) -> list[SpellingIssue]:
    body_text = _strip_section_headers(text)
    issues: list[SpellingIssue] = []
    seen: set[str] = set()
    for wrong, right in _COMMON_SPELLING_CORRECTIONS:
        match = re.search(rf"\b{re.escape(wrong)}\b", body_text, re.IGNORECASE)
        if match and wrong.lower() not in seen:
            matched_word = match.group(0)
            if matched_word != right:
                seen.add(wrong.lower())
                issues.append(
                    SpellingIssue(
                        original=matched_word,
                        suggestion=right,
                        context="Ortografia / acentuação",
                    )
                )
    return issues


def _is_meaningful(text: str) -> bool:
    cleaned = text.strip().lower()
    return cleaned not in {"", "n/a", "na", "-", "nenhum", "nenhuma", "não informado"}


def analyze_deterministically(report_text: str) -> DeterministicAnalysis:
    input_mode, sections = parse_ticket_sections(report_text)
    detected_issues: list[str] = []
    suspected_missing_steps = False
    marker_status = "missing"

    pii_result = scan_and_sanitize(report_text)
    spelling_issues = _detect_spelling_issues(report_text)
    if spelling_issues:
        words = ", ".join(f"'{s.original}' → '{s.suggestion}'" for s in spelling_issues[:4])
        detected_issues.append(f"Possíveis erros de ortografia/acentuação detectados: {words}.")

    checklist: list[ChecklistItemStatus] = []

    if input_mode == "draft_ticket":
        steps_raw = sections.get("repro_steps", "")
        step_lines = [line.strip() for line in steps_raw.splitlines() if line.strip()]
        first_line = step_lines[0] if step_lines else ""

        first_lower = first_line.lower()
        has_starter = first_lower.startswith(_FIRST_LINE_STARTERS)
        has_platform = any(p in first_lower for p in _PLATFORM_KEYWORDS)
        has_build = bool(_BUILD_PATTERN.search(first_line))
        if has_starter and has_platform and (has_build or any(b in first_lower for b in ("chrome", "safari", "firefox", "edge", "android", "ios", "whatsapp"))):
            env_status: FieldStatus = "confirmed"
            env_note = "Cabeçalho inicial com sistema, dispositivo e navegador/versão identificado."
        elif first_line and (has_starter or has_platform or has_build):
            env_status = "partial"
            env_note = "Formato recomendado: 'Acesse [sistema/área] em [dispositivo + navegador] + versão'."
            detected_issues.append("Linha inicial de sistema/dispositivo/navegador incompleta ou fora do padrão.")
        else:
            env_status = "missing"
            env_note = "Não foram informados sistema, dispositivo e navegador na primeira etapa."
            detected_issues.append("Falta identificar sistema, dispositivo e navegador na 1ª linha das etapas.")

        checklist.append(
            ChecklistItemStatus(
                field_id="platform_environment",
                label=FIELD_LABELS["platform_environment"],
                status=env_status,
                evidence_excerpt=first_line[:160],
                note=env_note,
            )
        )

        steps_lower = steps_raw.lower()
        if "é aqui que o bug é observado" in steps_lower or "e aqui que o bug e observado" in steps_lower:
            marker_status = "exact"
        elif "aqui o bug é observado" in steps_lower or "aqui o bug e observado" in steps_lower:
            marker_status = "variant"
            detected_issues.append(
                "Marcador final fora do padrão ('Aqui o bug é observado' → padronizar para 'É aqui que o bug é observado')."
            )
        else:
            marker_status = "missing"
            detected_issues.append("Falta o marcador padrão 'É aqui que o bug é observado' ao final das etapas.")

        candidate_steps = step_lines[1:] if first_lower.startswith(_FIRST_LINE_STARTERS) else step_lines
        action_lines = [
            line
            for line in candidate_steps
            if not _MARKER_LINE_PATTERN.search(line)
        ]
        desc_text = sections.get("description", "")
        actual_text = sections.get("actual_result", "")

        if len(action_lines) == 0:
            steps_status: FieldStatus = "missing"
            steps_note = "Nenhuma ação intermediária até o bug foi descrita."
            detected_issues.append("Faltam as etapas cronológicas para reproduzir o bug.")
        elif len(action_lines) <= 1 and (len(desc_text) > 70 or _is_meaningful(actual_text)):
            steps_status = "partial"
            suspected_missing_steps = True
            steps_note = "Etapas param muito cedo em relação aos detalhes citados na Descrição/Resultado."
            detected_issues.append(
                "Etapas faltando: a Descrição menciona interações/locais que não aparecem nas Etapas para Reproduzir."
            )
        elif marker_status == "missing":
            steps_status = "partial"
            steps_note = "Passos presentes, mas falta o marcador 'É aqui que o bug é observado'."
        else:
            steps_status = "confirmed"
            steps_note = f"{len(action_lines)} passos intermediários identificados."

        checklist.append(
            ChecklistItemStatus(
                field_id="repro_steps",
                label=FIELD_LABELS["repro_steps"],
                status=steps_status,
                evidence_excerpt=" | ".join(action_lines[:3])[:180],
                note=steps_note,
            )
        )

        if _is_meaningful(actual_text):
            ar_status: FieldStatus = "confirmed"
            ar_note = "Resultado observado preenchido."
        else:
            ar_status = "missing"
            ar_note = "Campo 'Resultado Atual' está vazio."
            detected_issues.append("Falta o campo 'Resultado Atual' (1 linha com o comportamento observado).")
        checklist.append(
            ChecklistItemStatus(
                field_id="actual_result",
                label=FIELD_LABELS["actual_result"],
                status=ar_status,
                evidence_excerpt=actual_text[:160],
                note=ar_note,
            )
        )

        expected_text = sections.get("expected_result", "")
        if _is_meaningful(expected_text):
            er_status: FieldStatus = "confirmed"
            er_note = "Resultado esperado preenchido."
        else:
            er_status = "missing"
            er_note = "Campo 'Resultado Esperado' está vazio."
            detected_issues.append("Falta o campo 'Resultado Esperado' (1 linha com o comportamento pretendido).")
        checklist.append(
            ChecklistItemStatus(
                field_id="expected_result",
                label=FIELD_LABELS["expected_result"],
                status=er_status,
                evidence_excerpt=expected_text[:160],
                note=er_note,
            )
        )

        if not _is_meaningful(desc_text):
            desc_status: FieldStatus = "missing"
            desc_note = "Campo 'Descrição' está vazio."
            detected_issues.append("Falta a 'Descrição' detalhando comportamento e localização exata.")
        elif len(desc_text.strip()) < 25:
            desc_status = "partial"
            desc_note = "Descrição muito curta; precisa detalhar localização e comportamento exato."
            detected_issues.append("Descrição muito breve para orientar o QA.")
        else:
            desc_status = "confirmed"
            desc_note = "Descrição detalhada presente."
        checklist.append(
            ChecklistItemStatus(
                field_id="description",
                label=FIELD_LABELS["description"],
                status=desc_status,
                evidence_excerpt=desc_text[:180],
                note=desc_note,
            )
        )

        rate_text = sections.get("repro_rate", "")
        if _RATIO_PATTERN.search(rate_text):
            rr_status: FieldStatus = "confirmed"
            rr_note = "Taxa no formato X/Y informada."
        elif _is_meaningful(rate_text):
            rr_status = "partial"
            rr_note = "Taxa informada fora do padrão X/Y."
            detected_issues.append("Taxa de Reprodução deve usar o formato X/Y (vezes que ocorreu / testadas).")
        else:
            rr_status = "missing"
            rr_note = "Taxa de Reprodução não informada."
            detected_issues.append("Falta a 'Taxa de Reprodução' (ex.: 3/3 ou 1/5).")
        checklist.append(
            ChecklistItemStatus(
                field_id="repro_rate",
                label=FIELD_LABELS["repro_rate"],
                status=rr_status,
                evidence_excerpt=rate_text[:80],
                note=rr_note,
            )
        )

        notes_text = sections.get("notes", "")
        if _is_meaningful(notes_text):
            notes_status: FieldStatus = "confirmed"
            notes_note = "Notas adicionais informadas."
        else:
            notes_status = "missing"
            notes_note = "Opcional: sem notas adicionais."
        checklist.append(
            ChecklistItemStatus(
                field_id="notes",
                label=FIELD_LABELS["notes"],
                status=notes_status,
                evidence_excerpt=notes_text[:160],
                note=notes_note,
            )
        )
    else:
        lower = report_text.lower()
        has_platform = any(p in lower for p in _PLATFORM_KEYWORDS)
        has_build = bool(_BUILD_PATTERN.search(report_text))
        has_ratio = bool(_RATIO_PATTERN.search(report_text))

        if has_platform and has_build:
            env_status = "confirmed"
            env_note = "Dispositivo/navegador e versão citados no relato."
        elif has_platform or has_build or len(report_text.strip()) >= 25:
            env_status = "partial"
            env_note = "Sistema possivelmente citado, mas faltam dispositivo, navegador e/ou versão."
            detected_issues.append("Falta confirmar sistema/área, dispositivo e navegador.")
        else:
            env_status = "missing"
            env_note = "Não informa sistema, dispositivo ou navegador."
            detected_issues.append("Não informa sistema, dispositivo nem navegador.")

        checklist.extend(
            [
                ChecklistItemStatus(
                    field_id="platform_environment",
                    label=FIELD_LABELS["platform_environment"],
                    status=env_status,
                    evidence_excerpt=report_text[:120] if env_status != "missing" else "",
                    note=env_note,
                ),
                ChecklistItemStatus(
                    field_id="repro_steps",
                    label=FIELD_LABELS["repro_steps"],
                    status="missing",
                    evidence_excerpt="",
                    note="Relato livre sem sequência de passos numerados até o bug.",
                ),
                ChecklistItemStatus(
                    field_id="actual_result",
                    label=FIELD_LABELS["actual_result"],
                    status="partial" if len(report_text.strip()) > 15 else "missing",
                    evidence_excerpt=report_text.strip()[:140],
                    note="Sintoma relatado informalmente; precisa de 1 linha objetiva.",
                ),
                ChecklistItemStatus(
                    field_id="expected_result",
                    label=FIELD_LABELS["expected_result"],
                    status="missing",
                    evidence_excerpt="",
                    note="Relato não explica o comportamento esperado.",
                ),
                ChecklistItemStatus(
                    field_id="description",
                    label=FIELD_LABELS["description"],
                    status="partial" if len(report_text.strip()) > 40 else "missing",
                    evidence_excerpt=report_text.strip()[:160] if len(report_text.strip()) > 40 else "",
                    note="Necessita detalhamento exato do local e comportamento.",
                ),
                ChecklistItemStatus(
                    field_id="repro_rate",
                    label=FIELD_LABELS["repro_rate"],
                    status="confirmed" if has_ratio else "missing",
                    evidence_excerpt="",
                    note="Taxa informada." if has_ratio else "Não informa quantas vezes ocorreu.",
                ),
                ChecklistItemStatus(
                    field_id="notes",
                    label=FIELD_LABELS["notes"],
                    status="missing",
                    evidence_excerpt="",
                    note="Campo opcional.",
                ),
            ]
        )
        detected_issues.append("Relato vago: faltam etapas exatas, resultado esperado e frequência.")

    score = compute_score(checklist)
    return DeterministicAnalysis(
        input_mode=input_mode,
        sections=sections,
        checklist=checklist,
        reproducibility_score=score,
        detected_issues=detected_issues,
        spelling_issues=spelling_issues,
        pii_warnings=pii_result.warnings,
        suspected_missing_steps=suspected_missing_steps,
        marker_status=marker_status,
    )


def build_fallback_questions(det: DeterministicAnalysis) -> list[ClarificationQuestion]:
    status_by_id = {item.field_id: item.status for item in det.checklist}
    questions: list[ClarificationQuestion] = []

    if status_by_id.get("platform_environment") in {"missing", "partial"}:
        questions.append(
            ClarificationQuestion(
                id="q_platform_environment",
                field_id="platform_environment",
                question="Em qual área/sistema (ex.: Checkout, Painel WhatsApp), dispositivo (Desktop/Celular) e navegador o problema aconteceu?",
                why_needed="A 1ª linha do ticket exige sistema, dispositivo e navegador para o QA reproduzir no ambiente correto.",
                placeholder="Ex.: Site YouShop no celular Android, Chrome (ou Desktop Windows, Edge)",
                priority="high",
            )
        )

    if status_by_id.get("repro_steps") in {"missing", "partial"}:
        if det.suspected_missing_steps:
            q_text = "Quais são os passos exatos entre abrir o sistema e o momento em que o bug acontece (tela, produto/pedido, botões clicados e forma de pagamento)?"
        else:
            q_text = "O que você estava fazendo passo a passo imediatamente antes do erro acontecer (qual tela, qual ação e qual botão clicou)?"
        questions.append(
            ClarificationQuestion(
                id="q_repro_steps",
                field_id="repro_steps",
                question=q_text,
                why_needed="Sem a sequência exata em ordem cronológica, o QA não consegue reproduzir o defeito.",
                placeholder="Ex.: Adicionei produto ao carrinho, apliquei cupom BEMVINDO10 e selecionei PIX no pagamento",
                priority="critical",
            )
        )

    if status_by_id.get("actual_result") == "missing":
        questions.append(
            ClarificationQuestion(
                id="q_actual_result",
                field_id="actual_result",
                question="Em uma frase curta, o que exatamente apareceu na tela quando o erro ocorreu (mensagem ou comportamento)?",
                why_needed="O campo 'Resultado Atual' é obrigatório para definir o sintoma principal do bug.",
                placeholder="Ex.: O botão Finalizar Compra trava carregando e exibe erro HTTP 504",
                priority="critical",
            )
        )

    if status_by_id.get("expected_result") in {"missing", "partial"}:
        questions.append(
            ClarificationQuestion(
                id="q_expected_result",
                field_id="expected_result",
                question="Em uma frase, o que você esperava que tivesse acontecido no lugar do erro?",
                why_needed="O campo 'Resultado Esperado' deixa claro qual é a intenção correta da funcionalidade.",
                placeholder="Ex.: O pedido deveria ser confirmado com o desconto aplicado normalmente",
                priority="high",
            )
        )

    if status_by_id.get("repro_rate") in {"missing", "partial"}:
        questions.append(
            ClarificationQuestion(
                id="q_repro_rate",
                field_id="repro_rate",
                question="Quantas vezes o problema aconteceu em quantas tentativas (ex.: 1/1, 3/3, 2/5)?",
                why_needed="A Taxa de Reprodução ajuda o QA a priorizar e saber se o bug é intermitente.",
                placeholder="Ex.: 3/3 (aconteceu todas as 3 vezes que tentei)",
                priority="medium",
            )
        )

    return questions[:5]
