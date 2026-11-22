from app.domain.grounding_validator import validate_and_ground_ticket
from app.domain.rule_engine import analyze_deterministically
from app.models.schemas import (
    AnalyzeResponse,
    LogDivergence,
    ProvenanceFact,
    QATicket,
    QuestionAnswer,
)
from app.services.platform_context.mock_logs_provider import MockLogsProvider
from app.services.platform_context.raw_log_parser import parse_raw_log


def test_mock_logs_provider_lists_and_looks_up_sessions() -> None:
    provider = MockLogsProvider()
    sessions = provider.list_sessions()

    assert len(sessions) == 4
    ids = {s.session_id for s in sessions}
    assert {"PED-9042", "SESS-YS-104", "SESS-YS-218", "SESS-YS-309"}.issubset(ids)

    painel = provider.lookup_session("sess-ys-309")
    assert painel is not None
    assert painel.environment.build == "v3.8.1"
    assert "ERR_PANEL_ROW_0x4F" in painel.extracted_error_codes

    ped = provider.lookup_session("PED-9042")
    assert ped is not None
    assert "ERR_GW_504_TIMEOUT" in ped.extracted_error_codes

    assert provider.lookup_session("NAO-EXISTE") is None


def test_raw_log_parser_extracts_events_codes_and_redacts_pii() -> None:
    raw = (
        "2026-11-21 18:01:02 INFO [Boot] build v2.14.3 Windows 11 x64\n"
        "ID do dispositivo\n"
        "00000000-0000-0000-0000-000000000000\n"
        "2026-11-21 18:01:15 ERROR [PaymentGateway] HTTP 504 ERR_GW_504_TIMEOUT tester@empresa.com\n"
    )
    parsed = parse_raw_log(raw)

    assert parsed.source_type == "raw_log"
    assert "v2.14.3" in parsed.environment.build
    assert "HTTP 504" in parsed.extracted_error_codes
    assert "ERR_GW_504_TIMEOUT" in parsed.extracted_error_codes
    assert "00000000-0000-0000-0000-000000000000" not in parsed.raw_excerpt
    assert "tester@empresa.com" not in parsed.raw_excerpt
    assert len(parsed.pii_redactions) >= 2


def test_grounding_validator_strips_hallucinated_log_provenance_when_no_log_attached() -> None:
    original = "No checkout da YouShop apliquei o cupom e deu erro."
    det = analyze_deterministically(original)
    analysis = AnalyzeResponse(
        input_mode=det.input_mode,
        category="bug_funcional",
        summary="Relato vago.",
        reproducibility_score=det.reproducibility_score,
        checklist=det.checklist,
        detected_issues=det.detected_issues,
        spelling_issues=[],
        pii_warnings=[],
        questions=[],
        ready_without_questions=False,
    )

    raw_ticket = QATicket(
        titulo="Erro no cupom do checkout",
        categoria="bug_funcional",
        etapas_para_reproduzir=["Aplique o cupom", "É aqui que o bug é observado"],
        resultado_atual="Deu erro.",
        resultado_esperado="Não informado",
        descricao="Erro no checkout.",
        taxa_de_reproducao="Não informado",
        notas="N/A",
        o_que_nao_foi_confirmado=[],
        correcoes_ortograficas=[],
        dados_sensiveis_removidos=[],
        score_antes=analysis.reproducibility_score,
        score_depois=analysis.reproducibility_score,
        checklist_final=analysis.checklist,
        origem_dos_dados=[
            ProvenanceFact(
                fact="Erro inventado de servidor",
                origin="platform_log",
                reference="LOG-FALSO",
            )
        ],
        divergencias_com_logs=[
            LogDivergence(
                relato_usuario="X",
                evidencia_log="Y",
                explicacao="Divergência inventada",
            )
        ],
    )

    grounded = validate_and_ground_ticket(original, analysis, [], raw_ticket, platform_context=None)

    assert grounded.platform_context_used is None
    assert grounded.divergencias_com_logs == []
    assert not any(p.origin == "platform_log" for p in grounded.origem_dos_dados)


def test_grounding_validator_auto_upgrades_env_and_adds_log_provenance() -> None:
    provider = MockLogsProvider()
    ctx = provider.lookup_session("SESS-YS-309")
    assert ctx is not None

    original = "Quando clico no pedido dentro do painel WhatsApp a sessão trava e fecha."
    det = analyze_deterministically(original)
    analysis = AnalyzeResponse(
        input_mode=det.input_mode,
        category="erro_bloqueante",
        summary="Erro bloqueante no painel WhatsApp.",
        reproducibility_score=det.reproducibility_score,
        checklist=det.checklist,
        detected_issues=det.detected_issues,
        spelling_issues=[],
        pii_warnings=[],
        questions=[],
        ready_without_questions=False,
    )

    raw_ticket = QATicket(
        titulo="[YouShop Painel WhatsApp] Sessão encerra ao clicar em pedido",
        categoria="erro_bloqueante",
        etapas_para_reproduzir=[
            "Acesse o Painel WhatsApp da YouShop no Desktop Chrome + versão v3.8.1",
            "Clique em uma linha de pedido com o mouse",
            "É aqui que o bug é observado",
        ],
        resultado_atual="O painel exibe modal de erro e encerra a sessão.",
        resultado_esperado="Os detalhes do pedido abrem normalmente.",
        descricao="Erro ocorre ao clicar na linha de pedido com o mouse.",
        taxa_de_reproducao="Não informado",
        notas="Erro ERR_PANEL_ROW_0x4F nos logs.",
        o_que_nao_foi_confirmado=[],
        correcoes_ortograficas=[],
        dados_sensiveis_removidos=[],
        score_antes=analysis.reproducibility_score,
        score_depois=analysis.reproducibility_score,
        checklist_final=analysis.checklist,
    )

    grounded = validate_and_ground_ticket(
        original,
        analysis,
        [QuestionAnswer(question_id="q1", field_id="expected_result", question="?", answer="Abrir os detalhes", skipped=False)],
        raw_ticket,
        platform_context=ctx,
    )

    assert grounded.platform_context_used is not None
    assert grounded.platform_context_used.session_id == "SESS-YS-309"
    assert any(p.origin == "platform_log" and "ERR_PANEL_ROW_0x4F" in p.reference for p in grounded.origem_dos_dados)
    status_by_id = {c.field_id: c.status for c in grounded.checklist_final}
    assert status_by_id["platform_environment"] == "confirmed"
    assert grounded.score_depois > grounded.score_antes
