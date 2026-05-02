from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import types
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module(
    module_name: str,
    file_path: Path,
    injected: dict[str, object],
    *,
    restore: bool = True,
):
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
        if restore:
            if previous_module is not None:
                sys.modules[module_name] = previous_module
            else:
                sys.modules.pop(module_name, None)
            for name, value in previous.items():
                if value is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value


def _fake_files_module():
    module = types.ModuleType("helpers.files")
    base_dir = str(PROJECT_ROOT)

    def get_abs_path(*parts):
        if len(parts) == 1 and os.path.isabs(parts[0]):
            return parts[0]
        return os.path.join(base_dir, *parts)

    module.get_abs_path = get_abs_path
    module.create_dir = lambda path: None
    module.make_dirs = lambda path: None
    module.write_file = lambda path, content: None
    module.list_files = lambda path, filter="*": []
    module.get_subdirectories = lambda path, include="*", exclude=None: []
    module.exists = lambda path: False
    module.read_file = lambda path: ""
    module.move_file = lambda old, new: None
    module.move_dir = lambda old, new: None
    module.delete_dir = lambda path: None
    return module


def _load_persist_chat_module():
    fake_agent = types.ModuleType("agent")

    class FakeAgent:
        DATA_NAME_SUBORDINATE = "_subordinate"

    class FakeAgentContext:
        @staticmethod
        def get(ctxid):
            return None

        @staticmethod
        def all():
            return []

    fake_agent.Agent = FakeAgent
    fake_agent.AgentConfig = object
    fake_agent.AgentContext = FakeAgentContext
    fake_agent.AgentContextType = types.SimpleNamespace(BACKGROUND="background", USER="user")

    fake_history = types.ModuleType("helpers.history")
    fake_history.deserialize_history = lambda value, agent=None: []

    fake_log = types.ModuleType("helpers.log")
    fake_log.Log = object
    fake_log.LogItem = object

    fake_initialize = types.ModuleType("initialize")
    fake_initialize.initialize_agent = lambda: None

    fake_helpers = types.ModuleType("helpers")
    fake_helpers.files = _fake_files_module()
    fake_helpers.history = fake_history

    injected = {
        "agent": fake_agent,
        "helpers": fake_helpers,
        "helpers.files": fake_helpers.files,
        "helpers.history": fake_history,
        "helpers.log": fake_log,
        "initialize": fake_initialize,
    }
    return _load_module(
        "test_helpers_persist_chat",
        PROJECT_ROOT / "helpers" / "persist_chat.py",
        injected,
    )


def test_chat_folder_path_uses_per_user_bucket() -> None:
    persist_chat = _load_persist_chat_module()

    path = persist_chat.get_chat_folder_path("ctx-123", user_id=7).replace("\\", "/")

    assert path.endswith("usr/chats/users/user_7/ctx-123")


def test_load_json_chats_reassigns_imported_chat_to_current_user() -> None:
    persist_chat = _load_persist_chat_module()
    captured: dict[str, object] = {}

    def fake_deserialize(data):
        captured.update(data)
        return types.SimpleNamespace(id="ctx-new")

    persist_chat._deserialize_context = fake_deserialize

    ctxids = persist_chat.load_json_chats(
        [json.dumps({"id": "ctx-old", "name": "Imported", "user_id": 99})],
        user_id=7,
    )

    assert ctxids == ["ctx-new"]
    assert captured["user_id"] == 7
    assert "id" not in captured


def test_use_context_refuses_foreign_owned_context_id() -> None:
    fake_agent = types.ModuleType("agent")

    class FakeAgentContext:
        created = False

        @staticmethod
        def first(user_id=None):
            return None

        @staticmethod
        def use(ctxid, user_id=None):
            return None

        def __init__(self, *args, **kwargs):
            FakeAgentContext.created = True
            raise AssertionError("foreign context should not be recreated")

    fake_agent.AgentContext = FakeAgentContext

    fake_persist_chat = types.ModuleType("helpers.persist_chat")
    fake_persist_chat.get_context_owner_user_id = lambda ctxid: 42

    fake_initialize = types.ModuleType("initialize")
    fake_initialize.initialize_agent = lambda: None

    context_utils = _load_module(
        "test_helpers_context_utils",
        PROJECT_ROOT / "helpers" / "context_utils.py",
        {
            "agent": fake_agent,
            "helpers.persist_chat": fake_persist_chat,
            "initialize": fake_initialize,
        },
        restore=False,
    )

    with pytest.raises(Exception, match=r"Context foreign-ctx not found"):
        context_utils.use_context(
            threading.RLock(),
            "foreign-ctx",
            create_if_not_exists=True,
            user_id=7,
        )

    assert FakeAgentContext.created is False
