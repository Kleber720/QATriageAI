from app.domain.rule_engine import analyze_deterministically
from app.services.knowledge_loader import load_few_shot_examples


def _example_by_id(example_id: str) -> dict:
    examples = load_few_shot_examples()
    for ex in examples:
        if ex["id"] == example_id:
            return ex
    raise KeyError(example_id)


def _status_map(text: str) -> tuple[dict[str, str], object]:
    det = analyze_deterministically(text)
    return {item.field_id: item.status for item in det.checklist}, det


def test_youshop_ruim_1_detects_missing_results_rate_and_spelling() -> None:
    ex = _example_by_id("youshop_ruim_1")
    statuses, det = _status_map(ex["text"])

    assert det.input_mode == "draft_ticket"
    assert "evidences" not in statuses
    assert statuses["actual_result"] == "missing"
    assert statuses["expected_result"] == "missing"
    assert statuses["repro_rate"] == "missing"
    assert det.marker_status == "variant"
    assert any(s.original.lower() == "pagina" for s in det.spelling_issues)
    assert any(s.original.lower() == "pricipal" for s in det.spelling_issues)


def test_youshop_ruim_2_detects_missing_intermediate_steps() -> None:
    ex = _example_by_id("youshop_ruim_2")
    statuses, det = _status_map(ex["text"])

    assert det.input_mode == "draft_ticket"
    assert det.suspected_missing_steps is True
    assert statuses["repro_steps"] == "partial"
    assert statuses["repro_rate"] == "missing"
    assert any(s.original.lower() == "codigo" for s in det.spelling_issues)


def test_youshop_ruim_3_detects_missing_rate() -> None:
    ex = _example_by_id("youshop_ruim_3")
    statuses, det = _status_map(ex["text"])

    assert det.input_mode == "draft_ticket"
    assert statuses["actual_result"] == "confirmed"
    assert statuses["expected_result"] == "confirmed"
    assert statuses["repro_rate"] == "missing"


def test_youshop_ref_pix_scores_high() -> None:
    ex = _example_by_id("youshop_ref_pix")
    statuses, det = _status_map(ex["text"])

    assert det.input_mode == "draft_ticket"
    assert statuses["actual_result"] == "confirmed"
    assert statuses["expected_result"] == "confirmed"
    assert statuses["repro_rate"] == "confirmed"
    assert det.reproducibility_score >= 85


def test_youshop_ref_painel_pii_detects_pii_and_complete_core() -> None:
    ex = _example_by_id("youshop_ref_painel_pii")
    statuses, det = _status_map(ex["text"])

    assert det.input_mode == "draft_ticket"
    assert statuses["repro_steps"] == "confirmed"
    assert statuses["repro_rate"] == "confirmed"
    assert len(det.pii_warnings) >= 3
    assert det.reproducibility_score == 100


def test_vague_whatsapp_report_has_low_score_and_correct_mode() -> None:
    ex = _example_by_id("whatsapp_vago_checkout")
    statuses, det = _status_map(ex["text"])

    assert det.input_mode == "vague_report"
    assert statuses["repro_steps"] == "missing"
    assert statuses["expected_result"] == "missing"
    assert statuses["repro_rate"] == "missing"
    assert det.reproducibility_score < 35


def test_spelling_detector_ignores_unaccented_section_headers_and_valid_words() -> None:
    sample = (
        "Etapas para Reproduzir:\n"
        "Acesse o site YouShop no Desktop Chrome versão v2.14.3\n"
        "Finalize o pagamento na sala pricipal do atendimento\n"
        "É aqui que o bug é observado\n"
        "Resultado Atual:\n"
        "O resumo trava.\n"
        "Resultado Esperado:\n"
        "O resumo atualiza normalmente.\n"
        "Descricao:\n"
        "Na etapa final na sala pricipal o resumo não atualiza.\n"
        "Taxa de reproducao:\n"
        "2/2"
    )
    _, det = _status_map(sample)
    flagged = {s.original.lower() for s in det.spelling_issues}
    assert "pricipal" in flagged
    assert "descricao" not in flagged
    assert "reproducao" not in flagged
