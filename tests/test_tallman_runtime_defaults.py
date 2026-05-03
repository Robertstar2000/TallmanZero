from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_tallman_dockerfile_preloads_real_sentence_transformer() -> None:
    content = (PROJECT_ROOT / "Dockerfile.tallman").read_text(encoding="utf-8")

    assert "SENTENCE_TRANSFORMERS_HOME=/opt/sentence_transformers" in content
    assert "SentenceTransformer('all-MiniLM-L6-v2'" in content


def test_tallman_model_defaults_target_internal_ollama() -> None:
    content = (PROJECT_ROOT / "plugins" / "_model_config" / "default_config.yaml").read_text(
        encoding="utf-8"
    )

    assert 'api_base: "http://10.10.20.60:11434"' in content
    assert 'name: "sentence-transformers/all-MiniLM-L6-v2"' in content
