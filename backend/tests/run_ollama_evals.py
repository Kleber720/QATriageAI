import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.config import settings
from app.domain.rule_engine import analyze_deterministically
from app.models.schemas import QuestionAnswer, GenerateRequest
from app.services.llm.ollama_provider import OllamaProvider
from app.services.triage_service import TriageService, _FORBIDDEN_FRICTION_PATTERNS

_DATASET_PATH = _BACKEND_ROOT / "dataset" / "qa_evals.jsonl"


def _load_eval_cases() -> list[dict]:
    cases: list[dict] = []
    for line in _DATASET_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            cases.append(json.loads(stripped))
    return cases


def _run_offline_evals(cases: list[dict]) -> int:
    failures = 0
    print(f"=== EVAL DETERMINISTICO OFFLINE ({len(cases)} casos) ===")
    for case in cases:
        t0 = time.perf_counter()
        det = analyze_deterministically(case["input_text"])
        elapsed = time.perf_counter() - t0

        status_by_id = {c.field_id: c.status for c in det.checklist}
        mode_ok = det.input_mode == case["expected_mode"]
        missing_ok = all(
            status_by_id.get(fid) in {"missing", "partial"}
            for fid in case["expected_missing_fields"]
        )
        pii_ok = bool(det.pii_warnings) == bool(case["contains_pii"])
        passed = mode_ok and missing_ok and pii_ok
        if not passed:
            failures += 1

        verdict = "PASS" if passed else "FAIL"
        print(
            f"[{verdict}] {case['id']} | mode={det.input_mode} (ok={mode_ok}) | "
            f"missing_ok={missing_ok} | pii_ok={pii_ok} | score={det.reproducibility_score}% | {elapsed:.3f}s"
        )
    return 0 if failures == 0 else 1


async def _run_live_evals(cases: list[dict]) -> int:
    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    health = await provider.check_health()
    if health.status != "ok":
        print(f"[ERRO] {health.message}")
        return 1

    service = TriageService(llm=provider)
    failures = 0
    print(f"=== EVAL LIVE OLLAMA ({settings.ollama_model} | {len(cases)} casos) ===")

    first_analysis = None
    first_case = None

    for case in cases:
        t0 = time.perf_counter()
        res = await service.analyze(case["input_text"])
        elapsed = time.perf_counter() - t0

        if case["id"] == "youshop_ruim_1":
            first_analysis = res
            first_case = case

        status_by_id = {c.field_id: c.status for c in res.checklist}
        mode_ok = res.input_mode == case["expected_mode"]
        category_ok = res.category == case["expected_category"]
        missing_ok = all(
            status_by_id.get(fid) in {"missing", "partial"}
            for fid in case["expected_missing_fields"]
        )
        pii_ok = bool(res.pii_warnings) == bool(case["contains_pii"])
        low_friction_ok = not any(
            _FORBIDDEN_FRICTION_PATTERNS.search(q.question) for q in res.questions
        )
        placeholder_ok = all(
            q.placeholder.strip().lower() != q.question.strip().lower()
            for q in res.questions
            if q.placeholder.strip()
        )

        passed = (
            mode_ok
            and category_ok
            and missing_ok
            and pii_ok
            and low_friction_ok
            and placeholder_ok
        )
        if not passed:
            failures += 1

        verdict = "PASS" if passed else "FAIL"
        print(
            f"[{verdict}] {case['id']} | cat={res.category} (exp={case['expected_category']}, ok={category_ok}) | "
            f"missing_ok={missing_ok} | pii_ok={pii_ok} | friction_ok={low_friction_ok} | "
            f"placeholder_ok={placeholder_ok} | qs={len(res.questions)} | {elapsed:.1f}s"
        )

    if first_analysis is not None and first_case is not None:
        t0 = time.perf_counter()
        skipped_answers = [
            QuestionAnswer(
                question_id=q.id,
                field_id=q.field_id,
                question=q.question,
                answer="",
                skipped=True,
            )
            for q in first_analysis.questions
        ]
        ticket = await service.generate(
            GenerateRequest(
                original_report=first_case["input_text"],
                analysis=first_analysis,
                answers=skipped_answers,
            )
        )
        elapsed = time.perf_counter() - t0
        campos = [item.campo.lower() for item in ticket.o_que_nao_foi_confirmado]
        marker_count = ticket.etapas_para_reproduzir.count("É aqui que o bug é observado")
        grounding_ok = (
            ticket.taxa_de_reproducao == "Não informado"
            and ticket.divergencias_com_logs == []
            and marker_count == 1
            and any("taxa" in c for c in campos)
            and not any("evid" in c for c in campos)
        )
        if not grounding_ok:
            failures += 1
        g_verdict = "PASS" if grounding_ok else "FAIL"
        print(
            f"[{g_verdict}] anti_hallucination_generate (youshop_ruim_1 skipped) | "
            f"taxa='{ticket.taxa_de_reproducao}' | "
            f"marker_count={marker_count} | unconfirmed={len(ticket.o_que_nao_foi_confirmado)} | {elapsed:.1f}s"
        )

    return 0 if failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    cases = _load_eval_cases()
    if args.offline:
        return _run_offline_evals(cases)
    return asyncio.run(_run_live_evals(cases))


if __name__ == "__main__":
    raise SystemExit(main())
