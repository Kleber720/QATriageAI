from app.domain.grounding_validator import (
    _normalize_steps,
    validate_and_ground_ticket,
)
from app.domain.rule_engine import analyze_deterministically
from app.models.schemas import (
    AnalyzeResponse,
    QATicket,
    QuestionAnswer,
    UnconfirmedItem,
)


def test_normalize_steps_never_duplicates_marker() -> None:
    already_has_marker = [
        "Acesse o site YouShop no Desktop Chrome + versão v2.14.3",
        "Clique em Finalizar Compra",
        "É aqui que o bug é observado",
    ]
    normalized = _normalize_steps(already_has_marker)
    assert normalized.count("É aqui que o bug é observado") == 1
    assert normalized[-1] == "É aqui que o bug é observado"
    assert len(normalized) == 3

    duplicated_by_llm = [
        "Acesse YouShop",
        "É aqui que o bug é observado",
        "Aqui o bug é observado.",
        "É aqui que o bug é observado",
    ]
    normalized_dup = _normalize_steps(duplicated_by_llm)
    assert normalized_dup == ["Acesse YouShop", "É aqui que o bug é observado"]


def test_grounding_validator_blocks_hallucinated_rate_and_strips_evidence_unconfirmed() -> None:
    original = "No site da YouShop apliquei o cupom no checkout e deu erro."
    det = analyze_deterministically(original)
    analysis = AnalyzeResponse(
        input_mode=det.input_mode,
        category="bug_funcional",
        summary="Relato vago sobre cupom no checkout da YouShop.",
        reproducibility_score=det.reproducibility_score,
        checklist=det.checklist,
        detected_issues=det.detected_issues,
        spelling_issues=det.spelling_issues,
        pii_warnings=[],
        questions=[],
        ready_without_questions=False,
    )

    answers = [
        QuestionAnswer(
            question_id="q_rate",
            field_id="repro_rate",
            question="Quantas vezes ocorreu?",
            answer="",
            skipped=True,
        ),
        QuestionAnswer(
            question_id="q_exp",
            field_id="expected_result",
            question="O que deveria acontecer?",
            answer="O cupom deveria aplicar o desconto normalmente.",
            skipped=False,
        ),
    ]

    hallucinated_ticket = QATicket(
        titulo="Cupom removido no checkout YouShop",
        categoria="bug_funcional",
        etapas_para_reproduzir=[
            "Acesse YouShop na plataforma [Não informado]",
            "Aplique o cupom",
            "É aqui que o bug é observado",
        ],
        resultado_atual="O desconto desaparece ao avançar.",
        resultado_esperado="O cupom permanece aplicado.",
        descricao="Erro ocorre no checkout.",
        taxa_de_reproducao="1/1",
        notas="ID do dispositivo\n00000000-0000-0000-0000-000000000000\nProcessador\nIntel i7",
        o_que_nao_foi_confirmado=[
            UnconfirmedItem(
                campo="Evidências",
                motivo="Sem print",
                impacto_para_qa="Sem vídeo",
                hipotese_da_ia="",
            )
        ],
        correcoes_ortograficas=[],
        dados_sensiveis_removidos=[],
        score_antes=analysis.reproducibility_score,
        score_depois=100,
        checklist_final=analysis.checklist,
    )

    grounded = validate_and_ground_ticket(original, analysis, answers, hallucinated_ticket)

    assert grounded.taxa_de_reproducao == "Não informado"
    assert grounded.etapas_para_reproduzir.count("É aqui que o bug é observado") == 1
    assert grounded.etapas_para_reproduzir[-1] == "É aqui que o bug é observado"
    campos = [item.campo.lower() for item in grounded.o_que_nao_foi_confirmado]
    assert any("taxa" in c for c in campos)
    assert not any("evid" in c for c in campos)
    assert "00000000-0000-0000-0000-000000000000" not in grounded.notas
    assert "Intel i7" in grounded.notas
    assert len(grounded.dados_sensiveis_removidos) >= 1
    assert grounded.score_depois < 100
    assert grounded.score_depois >= grounded.score_antes


def test_uncertain_text_answer_and_written_frequency_are_handled_correctly() -> None:
    original = "No site da YouShop cliquei em pagar com cartão e deu erro."
    det = analyze_deterministically(original)
    analysis = AnalyzeResponse(
        input_mode=det.input_mode,
        category="bug_funcional",
        summary="Relato vago sobre pagamento na YouShop.",
        reproducibility_score=det.reproducibility_score,
        checklist=det.checklist,
        detected_issues=det.detected_issues,
        spelling_issues=det.spelling_issues,
        pii_warnings=[],
        questions=[],
        ready_without_questions=False,
    )

    answers = [
        QuestionAnswer(
            question_id="q_exp",
            field_id="expected_result",
            question="O que deveria acontecer?",
            answer="não sei",
            skipped=False,
        ),
        QuestionAnswer(
            question_id="q_rate",
            field_id="repro_rate",
            question="Quantas vezes ocorreu?",
            answer="aconteceu só uma vez",
            skipped=False,
        ),
    ]

    raw_ticket = QATicket(
        titulo="Erro ao finalizar pagamento na YouShop",
        categoria="bug_funcional",
        etapas_para_reproduzir=[
            "Acesse YouShop em dispositivo [Não informado]",
            "Clique em Finalizar Compra",
            "É aqui que o bug é observado",
        ],
        resultado_atual="O checkout exibe erro ao pagar.",
        resultado_esperado="Não informado",
        descricao="Erro ocorre ao confirmar o pagamento.",
        taxa_de_reproducao="1/1",
        notas="N/A",
        o_que_nao_foi_confirmado=[],
        correcoes_ortograficas=[],
        dados_sensiveis_removidos=[],
        score_antes=analysis.reproducibility_score,
        score_depois=analysis.reproducibility_score,
        checklist_final=analysis.checklist,
    )

    grounded = validate_and_ground_ticket(original, analysis, answers, raw_ticket)

    assert grounded.taxa_de_reproducao == "1/1"
    status_by_id = {c.field_id: c.status for c in grounded.checklist_final}
    assert status_by_id["repro_rate"] == "confirmed"
    assert status_by_id["expected_result"] != "confirmed"
    campos = [item.campo.lower() for item in grounded.o_que_nao_foi_confirmado]
    assert any("resultado esperado" in c for c in campos)
