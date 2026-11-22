import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.schemas import ExamplePreset

_KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"


@lru_cache(maxsize=1)
def load_bug_scope() -> dict[str, Any]:
    path = _KNOWLEDGE_DIR / "bug_scope.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_few_shot_examples() -> list[dict[str, Any]]:
    path = _KNOWLEDGE_DIR / "few_shot_examples.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("examples", [])


def get_example_presets() -> list[ExamplePreset]:
    examples = load_few_shot_examples()
    return [
        ExamplePreset(
            id=ex["id"],
            title=ex["title"],
            badge=ex["badge"],
            description=ex["description"],
            text=ex["text"],
            suggested_session_id=ex.get("suggested_session_id", ""),
        )
        for ex in examples
    ]
