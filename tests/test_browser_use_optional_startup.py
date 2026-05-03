from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, file_path: Path, injected: dict[str, object]):
    previous = {name: sys.modules.get(name) for name in injected}
    previous_module = sys.modules.get(module_name)

    try:
        for name, value in injected.items():
            sys.modules[name] = value

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_module is not None:
            sys.modules[module_name] = previous_module
        else:
            sys.modules.pop(module_name, None)
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def test_browser_use_monkeypatch_noops_when_browser_use_is_missing() -> None:
    fake_dirty_json = types.ModuleType("helpers.dirty_json")
    fake_dirty_json.parse = lambda text: {"raw": text}
    fake_dirty_json.stringify = lambda value: str(value)

    fake_helpers = types.ModuleType("helpers")
    fake_helpers.dirty_json = fake_dirty_json

    module = _load_module(
        "test_helpers_browser_use_monkeypatch",
        PROJECT_ROOT / "helpers" / "browser_use_monkeypatch.py",
        {
            "helpers": fake_helpers,
            "helpers.dirty_json": fake_dirty_json,
        },
    )

    assert module.is_available() is False
    assert module.gemini_clean_and_conform("{}") is None
    module.apply()


def test_models_import_without_browser_use_and_raise_only_on_browser_wrapper_use() -> None:
    fake_litellm = types.ModuleType("litellm")
    fake_litellm.completion = lambda *args, **kwargs: None

    async def _fake_acompletion(*args, **kwargs):
        return None

    fake_litellm.acompletion = _fake_acompletion
    fake_litellm.embedding = lambda *args, **kwargs: types.SimpleNamespace(data=[])
    fake_litellm.modify_params = False
    fake_litellm.drop_params = False
    fake_litellm.suppress_debug_info = True

    fake_litellm_types = types.ModuleType("litellm.types")
    fake_litellm_types_utils = types.ModuleType("litellm.types.utils")
    fake_litellm_types_utils.ModelResponse = object

    fake_openai = types.ModuleType("openai")

    fake_dotenv = types.ModuleType("helpers.dotenv")
    fake_dotenv.load_dotenv = lambda: None

    fake_settings = types.ModuleType("helpers.settings")
    fake_settings.get_settings = lambda: {}

    fake_dirty_json = types.ModuleType("helpers.dirty_json")
    fake_dirty_json.parse = lambda text: {"raw": text}
    fake_dirty_json.stringify = lambda value: str(value)

    fake_providers = types.ModuleType("helpers.providers")
    fake_providers.get_provider_config = lambda *args, **kwargs: {}

    fake_rate_limiter = types.ModuleType("helpers.rate_limiter")

    class FakeRateLimiter:
        def __init__(self, seconds=60):
            self.seconds = seconds
            self.limits = {}

        def add(self, **kwargs):
            return None

    fake_rate_limiter.RateLimiter = FakeRateLimiter

    fake_tokens = types.ModuleType("helpers.tokens")
    fake_tokens.approximate_tokens = lambda text: 0

    fake_browser_use_monkeypatch = types.ModuleType("helpers.browser_use_monkeypatch")
    fake_browser_use_monkeypatch.apply = lambda: None
    fake_browser_use_monkeypatch.gemini_clean_and_conform = lambda text: None

    fake_helpers = types.ModuleType("helpers")
    fake_helpers.dotenv = fake_dotenv
    fake_helpers.settings = fake_settings
    fake_helpers.dirty_json = fake_dirty_json
    fake_helpers.browser_use_monkeypatch = fake_browser_use_monkeypatch

    fake_langchain_chat_models = types.ModuleType("langchain_core.language_models.chat_models")

    class SimpleChatModel:
        pass

    fake_langchain_chat_models.SimpleChatModel = SimpleChatModel

    fake_langchain_outputs = types.ModuleType("langchain_core.outputs.chat_generation")

    class ChatGenerationChunk:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    fake_langchain_outputs.ChatGenerationChunk = ChatGenerationChunk

    fake_langchain_callbacks = types.ModuleType("langchain_core.callbacks.manager")
    fake_langchain_callbacks.CallbackManagerForLLMRun = object
    fake_langchain_callbacks.AsyncCallbackManagerForLLMRun = object

    fake_langchain_messages = types.ModuleType("langchain_core.messages")

    class _Message:
        def __init__(self, content=None, **kwargs):
            self.content = content

    fake_langchain_messages.BaseMessage = _Message
    fake_langchain_messages.AIMessageChunk = _Message
    fake_langchain_messages.HumanMessage = _Message
    fake_langchain_messages.SystemMessage = _Message

    fake_langchain_embeddings = types.ModuleType("langchain.embeddings.base")

    class Embeddings:
        pass

    fake_langchain_embeddings.Embeddings = Embeddings

    fake_sentence_transformers = types.ModuleType("sentence_transformers")

    class SentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

    fake_sentence_transformers.SentenceTransformer = SentenceTransformer

    fake_pydantic = types.ModuleType("pydantic")
    fake_pydantic.ConfigDict = dict

    module = _load_module(
        "test_models_optional_browser_use",
        PROJECT_ROOT / "models.py",
        {
            "litellm": fake_litellm,
            "litellm.types": fake_litellm_types,
            "litellm.types.utils": fake_litellm_types_utils,
            "openai": fake_openai,
            "helpers": fake_helpers,
            "helpers.dotenv": fake_dotenv,
            "helpers.settings": fake_settings,
            "helpers.dirty_json": fake_dirty_json,
            "helpers.providers": fake_providers,
            "helpers.rate_limiter": fake_rate_limiter,
            "helpers.tokens": fake_tokens,
            "helpers.browser_use_monkeypatch": fake_browser_use_monkeypatch,
            "langchain_core.language_models.chat_models": fake_langchain_chat_models,
            "langchain_core.outputs.chat_generation": fake_langchain_outputs,
            "langchain_core.callbacks.manager": fake_langchain_callbacks,
            "langchain_core.messages": fake_langchain_messages,
            "langchain.embeddings.base": fake_langchain_embeddings,
            "sentence_transformers": fake_sentence_transformers,
            "pydantic": fake_pydantic,
        },
    )

    assert module.BROWSER_USE_AVAILABLE is False
    with pytest.raises(ModuleNotFoundError, match="browser_use is not installed"):
        module.get_browser_model("ollama", "gemma2:27b")
