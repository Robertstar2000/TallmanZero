from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_errors_module():
    module_name = "test_helpers_errors"
    previous = sys.modules.get(module_name)

    try:
        spec = importlib.util.spec_from_file_location(
            module_name,
            PROJECT_ROOT / "helpers" / "errors.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is not None:
            sys.modules[module_name] = previous
        else:
            sys.modules.pop(module_name, None)


def test_is_model_connection_error_detects_litellm_ollama_failure() -> None:
    errors = _load_errors_module()
    exc = Exception(
        "litellm.APIConnectionError: OllamaException - Cannot connect to host "
        "10.10.20.60:11434 ssl:default [Connect call failed ('10.10.20.60', 11434)]"
    )

    assert errors.is_model_connection_error(exc) is True
    assert errors.extract_connection_target(exc) == "10.10.20.60:11434"


def test_is_model_connection_error_ignores_generic_non_model_connectivity_errors() -> None:
    errors = _load_errors_module()
    exc = RuntimeError("Cannot connect to host db.internal:5432")

    assert errors.is_model_connection_error(exc) is False


def test_describe_model_connection_error_uses_model_config_details() -> None:
    errors = _load_errors_module()
    exc = Exception("Cannot connect to host 10.10.20.60:11434")

    message = errors.describe_model_connection_error(
        exc,
        provider="ollama",
        model_name="gemma2:27b",
        api_base="http://10.10.20.60:11434",
    )

    assert "ollama/gemma2:27b" in message
    assert "http://10.10.20.60:11434" in message
    assert "Restore network access" in message
