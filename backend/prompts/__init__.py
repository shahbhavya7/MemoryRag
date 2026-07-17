import os
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Read a versioned prompt template by file stem (e.g. 'classifier_v2')."""
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


def classifier_version() -> str:
    # Which classifier prompt version to use, selectable without code changes.
    return os.getenv("CLASSIFIER_PROMPT_VERSION", "v2")


def load_classifier_prompt(version: str | None = None) -> str:
    return load_prompt(f"classifier_{version or classifier_version()}")
