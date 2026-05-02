from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


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


def _fake_api_module():
    module = types.ModuleType("helpers.api")

    class ApiHandler:
        def __init__(self, app, thread_lock):
            self.app = app
            self.thread_lock = thread_lock

    module.ApiHandler = ApiHandler
    module.Request = object
    module.Response = dict
    return module


def test_self_update_get_reports_disabled_build() -> None:
    fake_runtime = types.ModuleType("helpers.runtime")
    fake_runtime.is_dockerized = lambda: True

    fake_self_update = types.ModuleType("helpers.self_update")
    fake_self_update.is_self_update_enabled = lambda: False
    fake_self_update.get_self_update_disabled_reason = lambda: "disabled for this build"

    fake_helpers = types.ModuleType("helpers")
    fake_helpers.runtime = fake_runtime
    fake_helpers.self_update = fake_self_update

    module = _load_module(
        "test_api_self_update_get",
        PROJECT_ROOT / "api" / "self_update_get.py",
        {
            "helpers": fake_helpers,
            "helpers.api": _fake_api_module(),
            "helpers.runtime": fake_runtime,
            "helpers.self_update": fake_self_update,
        },
    )

    handler = module.SelfUpdateGet(None, None)
    payload = __import__("asyncio").run(handler.process({}, None))

    assert payload["success"] is True
    assert payload["supported"] is False
    assert payload["error"] == "disabled for this build"
    assert payload["pending"] is None


def test_self_update_schedule_rejects_disabled_build() -> None:
    fake_runtime = types.ModuleType("helpers.runtime")
    fake_runtime.is_dockerized = lambda: True

    fake_self_update = types.ModuleType("helpers.self_update")
    fake_self_update.is_self_update_enabled = lambda: False
    fake_self_update.get_self_update_disabled_reason = lambda: "disabled for this build"

    fake_helpers = types.ModuleType("helpers")
    fake_helpers.runtime = fake_runtime
    fake_helpers.self_update = fake_self_update

    module = _load_module(
        "test_api_self_update_schedule",
        PROJECT_ROOT / "api" / "self_update_schedule.py",
        {
            "helpers": fake_helpers,
            "helpers.api": _fake_api_module(),
            "helpers.runtime": fake_runtime,
            "helpers.self_update": fake_self_update,
        },
    )

    handler = module.SelfUpdateSchedule(None, None)
    payload = __import__("asyncio").run(handler.process({}, None))

    assert payload == {
        "success": False,
        "error": "disabled for this build",
    }


def test_backup_settings_hides_self_update_entry() -> None:
    content = (
        PROJECT_ROOT
        / "webui"
        / "components"
        / "settings"
        / "backup"
        / "backup-settings.html"
    ).read_text(encoding="utf-8")

    assert "settings/backup/self-update.html" not in content
    assert "section-self-update" not in content
    assert ">Self Update<" not in content
