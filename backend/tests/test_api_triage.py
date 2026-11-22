from typing import TypeVar, cast

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.dependencies import get_triage_service
from app.main import app
from app.models.schemas import (
    HealthResponse,
    LLMAnalyzeWire,
    LLMChecklistWireItem,
    LLMDivergenceWireItem,
    LLMGenerateWire,
    LLMProvenanceWireItem,
    LLMQuestionWireItem,
    LLMSpellingCorrectionWire,
    LLMSpellingWireItem,
    LLMUnconfirmedWireItem,
)
from app.services.llm.base import LLMProvider, LLMUnavailableError
from app.services.triage_service import TriageService

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    def __init__(self, fail_unavailable: bool = False) -> None:
        self.fail_unavailable = fail_unavailable
        self.last_user_prompt: str = ""

    async def check_health(self) -> HealthResponse:
        if self.fail_unavailable:
            return HealthResponse(
                status="degraded",
                ollama_online=False,
                ollama_base_url="http://127.0.0.1:11434",
                configured_model="qwen3:4b-instruct",
                model_available=False,
                available_models=[],
                message="Ollama offline.",
            )
        return HealthResponse(
            status="ok",
            ollama_online=True,
            ollama_base_url="http://127.0.0.1:11434",
            configured_model="qwen3:4b-instruct",
            model_available=True,
            available_models=["qwen3:4b-instruct"],
            message="Ollama pronto.",
        )

    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        self.last_user_prompt = user_prompt
        if self.fail_unavailable:
            raise LLMUnavailableError("Ollama offline no teste.")

        if response_model is LLMAnalyzeWire:
            return cast(
                T,
                LLMAnalyzeWire(
                    category="bug_funcional",
                    summary="Relato sobre remoção do cupom ao selecionar PIX no checkout YouShop.",
                    checklist_updates=[
                        LLMChecklistWireItem(
                            field_id="expected_result",
                            status="missing",
                            evidence_excerpt="",
                            note="Não informado.",
                        )
                    ],
                    detected_issues=["Falta resultado esperado."],
                    spelling_issues=[
                        LLMSpellingWireItem(
                            original="pagina",
                            suggestion="página",
                            context="Acento agudo ausente",
                        )
                    ],
                    questions=[
                        LLMQuestionWireItem(
                            id="q_specs_forbidden",
                            field_id="notes",
                            question="Qual o ID do dispositivo e Processador do seu PC?",
                            why_needed="Teste de bloqueio de fricção",
                            placeholder="",
                            priority="medium",
                        ),
                        LLMQuestionWireItem(
                            id="q_evidence_forbidden",
                            field_id="repro_steps",
                            question="Você pode enviar print ou vídeo de evidência do erro?",
                            why_needed="Teste de bloqueio de evidências",
                            placeholder="",
                            priority="medium",
                        ),
                        LLMQuestionWireItem(
                            id="q_steps_1",
                            field_id="repro_steps",
                            question="Qual forma de pagamento foi selecionada após aplicar o cupom?",
                            why_needed="Identificar o gatilho no checkout.",
                            placeholder="Ex.: PIX",
                            priority="critical",
                        ),
                        LLMQuestionWireItem(
                            id="q_steps_2",
                            field_id="repro_steps",
                            question="Qual produto estava no carrinho quando o erro ocorreu?",
                            why_needed="Reproduzir com o mesmo SKU.",
                            placeholder="Ex.: Tênis Runner Pro",
                            priority="critical",
                        ),
                        LLMQuestionWireItem(
                            id="q_expected",
                            field_id="expected_result",
                            question="O que deveria acontecer ao trocar para PIX?",
                            why_needed="Define o Resultado Esperado.",
                            placeholder="Ex.: O cupom continua aplicado",
                            priority="high",
                        ),
                    ],
                ),
            )

        if response_model is LLMGenerateWire:
            return cast(
                T,
                LLMGenerateWire(
                    titulo="[YouShop] Cupom removido ao selecionar PIX no checkout",
                    categoria="bug_funcional",
                    etapas_para_reproduzir=[
                        "Acesse o site YouShop no Desktop Chrome + versão v2.14.3",
                        "Adicione o produto ao carrinho, aplique o cupom e selecione PIX",
                        "É aqui que o bug é observado",
                    ],
                    resultado_atual="O desconto do cupom desaparece após selecionar PIX.",
                    resultado_esperado="O cupom permanece aplicado após selecionar PIX.",
                    descricao="Na página principal do checkout, ao alternar o pagamento para PIX, o cupom é limpo.",
                    taxa_de_reproducao="3/3",
                    notas="N/A",
                    o_que_nao_foi_confirmado=[],
                    correcoes_ortograficas=[
                        LLMSpellingCorrectionWire(original="pagina", corrigido="página")
                    ],
                    origem_dos_dados=[
                        LLMProvenanceWireItem(
                            fact="O cupom desaparece ao selecionar PIX.",
                            origin="user_report",
                            reference="Relato inicial",
                        )
                    ],
                    divergencias_com_logs=[
                        LLMDivergenceWireItem(
                            relato_usuario="Cartão recusado",
                            evidencia_log="HTTP 504 Gateway Timeout",
                            explicacao="Timeout no gateway, não recusa do emissor.",
                        )
                    ],
                ),
            )

        raise AssertionError(f"Unexpected response_model: {response_model}")


def test_health_and_examples_endpoints() -> None:
    app.dependency_overrides[get_triage_service] = lambda: TriageService(MockLLMProvider())
    try:
        client = TestClient(app)

        health_res = client.get("/api/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"

        ex_res = client.get("/api/triage/examples")
        assert ex_res.status_code == 200
        examples = ex_res.json()
        assert len(examples) == 7
        assert any(e["id"] == "youshop_ref_painel_pii" for e in examples)
        checkout_ex = next(e for e in examples if e["id"] == "checkout_divergencia_log")
        assert checkout_ex["suggested_session_id"] == "PED-9042"
    finally:
        app.dependency_overrides.clear()


def test_full_analyze_and_generate_flow_enforces_low_friction_and_grounding() -> None:
    mock_llm = MockLLMProvider()
    app.dependency_overrides[get_triage_service] = lambda: TriageService(mock_llm)
    try:
        client = TestClient(app)

        analyze_res = client.post(
            "/api/triage/analyze",
            json={
                "report_text": (
                    "No site da YouShop no Desktop Chrome versão v2.14.3 fui pagar na pagina do checkout e deu erro.\n"
                    "ID do dispositivo\n00000000-0000-0000-0000-000000000000"
                )
            },
        )
        assert analyze_res.status_code == 200
        analysis = analyze_res.json()

        assert "00000000-0000-0000-0000-000000000000" not in mock_llm.last_user_prompt
        q_texts = [q["question"].lower() for q in analysis["questions"]]
        assert not any("id do dispositivo" in q or "processador" in q for q in q_texts)
        assert not any("print" in q or "evidência" in q or "vídeo" in q for q in q_texts)
        steps_qs = [q for q in analysis["questions"] if q["field_id"] == "repro_steps"]
        assert len(steps_qs) == 2
        assert len(analysis["questions"]) <= 5

        generate_res = client.post(
            "/api/triage/generate",
            json={
                "original_report": "No site da YouShop no Desktop Chrome versão v2.14.3 fui pagar na pagina do checkout e deu erro.",
                "analysis": analysis,
                "answers": [
                    {
                        "question_id": "q_expected",
                        "field_id": "expected_result",
                        "question": "O que deveria acontecer?",
                        "answer": "O cupom permanece aplicado após selecionar PIX.",
                        "skipped": False,
                    },
                    {
                        "question_id": "q_repro_rate",
                        "field_id": "repro_rate",
                        "question": "Quantas vezes aconteceu?",
                        "answer": "",
                        "skipped": True,
                    },
                ],
            },
        )
        assert generate_res.status_code == 200
        ticket = generate_res.json()

        assert ticket["taxa_de_reproducao"] == "Não informado"
        assert ticket["etapas_para_reproduzir"].count("É aqui que o bug é observado") == 1
        assert ticket["etapas_para_reproduzir"][-1] == "É aqui que o bug é observado"
        assert any("Taxa" in item["campo"] for item in ticket["o_que_nao_foi_confirmado"])
    finally:
        app.dependency_overrides.clear()


def test_analyze_returns_503_when_ollama_is_offline() -> None:
    app.dependency_overrides[get_triage_service] = lambda: TriageService(
        MockLLMProvider(fail_unavailable=True)
    )
    try:
        client = TestClient(app)
        res = client.post(
            "/api/triage/analyze",
            json={"report_text": "O painel do WhatsApp travou quando cliquei no pedido."},
        )
        assert res.status_code == 503
        assert "Ollama offline" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_logs_endpoints_and_generate_with_platform_session() -> None:
    mock_llm = MockLLMProvider()
    app.dependency_overrides[get_triage_service] = lambda: TriageService(mock_llm)
    try:
        client = TestClient(app)

        sessions_res = client.get("/api/logs/sessions")
        assert sessions_res.status_code == 200
        sessions = sessions_res.json()
        assert len(sessions) == 4

        sess_res = client.get("/api/logs/sessions/SESS-YS-309")
        assert sess_res.status_code == 200
        assert "ERR_PANEL_ROW_0x4F" in sess_res.json()["extracted_error_codes"]

        missing_res = client.get("/api/logs/sessions/NAO-EXISTE")
        assert missing_res.status_code == 404

        parse_res = client.post(
            "/api/logs/parse",
            json={"raw_log_text": "16:00:00 ERROR [Checkout] ERR_GW_504_TIMEOUT build v2.14.3"},
        )
        assert parse_res.status_code == 200
        assert "ERR_GW_504_TIMEOUT" in parse_res.json()["extracted_error_codes"]

        analyze_res = client.post(
            "/api/triage/analyze",
            json={"report_text": "No painel WhatsApp da YouShop cliquei no pedido e a sessão fechou."},
        )
        assert analyze_res.status_code == 200
        analysis = analyze_res.json()

        generate_res = client.post(
            "/api/triage/generate",
            json={
                "original_report": "No painel WhatsApp da YouShop cliquei no pedido e a sessão fechou.",
                "analysis": analysis,
                "answers": [],
                "platform_session_id": "SESS-YS-309",
            },
        )
        assert generate_res.status_code == 200
        ticket = generate_res.json()
        assert ticket["platform_context_used"]["session_id"] == "SESS-YS-309"
        assert any(p["origin"] == "platform_log" for p in ticket["origem_dos_dados"])
        assert "ERR_PANEL_ROW_0x4F" in mock_llm.last_user_prompt
    finally:
        app.dependency_overrides.clear()
