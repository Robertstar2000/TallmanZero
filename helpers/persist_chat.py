from collections import OrderedDict
from datetime import datetime
import os
from typing import Any
import uuid
from agent import Agent, AgentConfig, AgentContext, AgentContextType
from helpers import files, history
import json
from initialize import initialize_agent

from helpers.log import Log, LogItem

CHATS_FOLDER = "usr/chats"
USER_CHATS_FOLDER = f"{CHATS_FOLDER}/users"
USER_CHAT_PREFIX = "user_"
ANONYMOUS_CHAT_BUCKET = "anonymous"
LOG_SIZE = 1000
CHAT_FILE_NAME = "chat.json"


def _get_user_chat_bucket(user_id: int | None):
    if user_id is None:
        return ANONYMOUS_CHAT_BUCKET
    return f"{USER_CHAT_PREFIX}{int(user_id)}"


def get_user_chats_folder(user_id: int | None):
    return files.get_abs_path(USER_CHATS_FOLDER, _get_user_chat_bucket(user_id))


def ensure_user_chat_storage(user_id: int | None):
    path = get_user_chats_folder(user_id)
    files.create_dir(path)
    return path


def _get_legacy_chat_folder_path(ctxid: str):
    return files.get_abs_path(CHATS_FOLDER, ctxid)


def _get_legacy_chat_file_path(ctxid: str):
    return files.get_abs_path(CHATS_FOLDER, ctxid, CHAT_FILE_NAME)


def _load_context_owner_from_chat_file(path: str):
    try:
        js = files.read_file(path)
        data = json.loads(js)
    except Exception:
        return None
    return data.get("user_id")


def get_context_owner_user_id(ctxid: str):
    context = AgentContext.get(ctxid)
    if context:
        return context.user_id

    try:
        from helpers import db

        database = db.get_database()
        mapping = database.get("SELECT user_id FROM user_contexts WHERE ctxid = ?", [ctxid])
        if mapping and "user_id" in mapping:
            return mapping["user_id"]
    except Exception:
        pass

    for bucket in files.get_subdirectories(USER_CHATS_FOLDER):
        candidate = files.get_abs_path(USER_CHATS_FOLDER, bucket, ctxid, CHAT_FILE_NAME)
        if files.exists(candidate):
            return _load_context_owner_from_chat_file(candidate)

    legacy_path = _get_legacy_chat_file_path(ctxid)
    if files.exists(legacy_path):
        legacy_owner = _load_context_owner_from_chat_file(legacy_path)
        return 0 if legacy_owner is None else legacy_owner

    return None


def get_chat_folder_path(ctxid: str, user_id: int | None = None):
    """
    Get the folder path for any context (chat or task).

    Args:
        ctxid: The context ID
        user_id: Optional owner override. When omitted, the owner is resolved
            from the live context or persisted mapping.

    Returns:
        The absolute path to the context folder
    """
    owner_user_id = get_context_owner_user_id(ctxid) if user_id is None else user_id
    return files.get_abs_path(
        USER_CHATS_FOLDER,
        _get_user_chat_bucket(owner_user_id),
        ctxid,
    )


def get_chat_msg_files_folder(ctxid: str, user_id: int | None = None):
    return os.path.join(get_chat_folder_path(ctxid, user_id=user_id), "messages")

def save_tmp_chat(context: AgentContext):
    """Save context to the chats folder"""
    # Skip saving BACKGROUND contexts as they should be ephemeral
    if context.type == AgentContextType.BACKGROUND:
        return

    ensure_user_chat_storage(context.user_id)
    path = _get_chat_file_path(context.id, user_id=context.user_id)
    files.make_dirs(path)
    data = _serialize_context(context)
    js = _safe_json_serialize(data, ensure_ascii=False)
    files.write_file(path, js)


def save_tmp_chats():
    """Save all contexts to the chats folder"""
    for context in AgentContext.all():
        # Skip BACKGROUND contexts as they should be ephemeral
        if context.type == AgentContextType.BACKGROUND:
            continue
        save_tmp_chat(context)


def load_tmp_chats():
    """Load all contexts from the chats folder"""
    _convert_v080_chats()
    _migrate_legacy_shared_chats()
    json_files = _list_chat_files()

    ctxids = []
    for file in json_files:
        try:
            js = files.read_file(file)
            data = json.loads(js)
            ctx = _deserialize_context(data)
            ctxids.append(ctx.id)
        except Exception as e:
            print(f"Error loading chat {file}: {e}")
    return ctxids


def _list_chat_files():
    json_files: list[str] = []
    seen_ctxids: set[str] = set()

    def _add_chat_file(path: str):
        ctxid = os.path.basename(os.path.dirname(path))
        if ctxid in seen_ctxids:
            return
        seen_ctxids.add(ctxid)
        json_files.append(path)

    for bucket in files.get_subdirectories(USER_CHATS_FOLDER):
        bucket_path = files.get_abs_path(USER_CHATS_FOLDER, bucket)
        if not os.path.isdir(bucket_path):
            continue
        for ctxid in os.listdir(bucket_path):
            path = os.path.join(bucket_path, ctxid, CHAT_FILE_NAME)
            if os.path.isfile(path):
                _add_chat_file(path)

    for folder_name in files.get_subdirectories(CHATS_FOLDER, exclude="users"):
        path = _get_legacy_chat_file_path(folder_name)
        if os.path.isfile(path):
            _add_chat_file(path)

    return json_files


def _get_chat_file_path(ctxid: str, user_id: int | None = None):
    return os.path.join(get_chat_folder_path(ctxid, user_id=user_id), CHAT_FILE_NAME)


def _convert_v080_chats():
    json_files = files.list_files(CHATS_FOLDER, "*.json")
    for file in json_files:
        path = files.get_abs_path(CHATS_FOLDER, file)
        name = file.rstrip(".json")
        new = _get_legacy_chat_file_path(name)
        files.move_file(path, new)


def _migrate_legacy_shared_chats():
    for folder_name in files.get_subdirectories(CHATS_FOLDER, exclude="users"):
        old_path = _get_legacy_chat_folder_path(folder_name)
        old_chat_file = _get_legacy_chat_file_path(folder_name)
        if not os.path.isfile(old_chat_file):
            continue

        owner_user_id = get_context_owner_user_id(folder_name)
        target_path = get_chat_folder_path(folder_name, user_id=owner_user_id)
        if os.path.abspath(old_path) == os.path.abspath(target_path):
            continue
        if files.exists(target_path):
            continue

        files.move_dir(old_path, target_path)


def load_json_chats(jsons: list[str], user_id: int | None = None):
    """Load contexts from JSON strings"""
    ctxids = []
    for js in jsons:
        data = json.loads(js)
        if "id" in data:
            del data["id"]  # remove id to get new
        if user_id is not None:
            data["user_id"] = user_id
        ctx = _deserialize_context(data)
        ctxids.append(ctx.id)
    return ctxids


def export_json_chat(context: AgentContext):
    """Export context as JSON string"""
    data = _serialize_context(context)
    js = _safe_json_serialize(data, ensure_ascii=False)
    return js


def remove_chat(ctxid, user_id: int | None = None):
    """Remove a chat or task context"""
    path = get_chat_folder_path(ctxid, user_id=user_id)
    files.delete_dir(path)


def remove_msg_files(ctxid, user_id: int | None = None):
    """Remove all message files for a chat or task context"""
    path = get_chat_msg_files_folder(ctxid, user_id=user_id)
    files.delete_dir(path)


def _serialize_context(context: AgentContext):
    # serialize agents
    agents = []
    agent = context.agent0
    while agent:
        agents.append(_serialize_agent(agent))
        agent = agent.data.get(Agent.DATA_NAME_SUBORDINATE, None)


    data = {k: v for k, v in context.data.items() if not k.startswith("_")}
    output_data = {k: v for k, v in context.output_data.items() if not k.startswith("_")}

    return {
        "id": context.id,
        "name": context.name,
        "created_at": (
            context.created_at.isoformat()
            if context.created_at
            else datetime.fromtimestamp(0).isoformat()
        ),
        "type": context.type.value,
        "last_message": (
            context.last_message.isoformat()
            if context.last_message
            else datetime.fromtimestamp(0).isoformat()
        ),
        "agents": agents,
        "streaming_agent": (
            context.streaming_agent.number if context.streaming_agent else 0
        ),
        "log": _serialize_log(context.log),
        "data": data,
        "output_data": output_data,
        "user_id": context.user_id,
    }


def _serialize_agent(agent: Agent):
    data = {k: v for k, v in agent.data.items() if not k.startswith("_")}

    history = agent.history.serialize()

    return {
        "number": agent.number,
        "data": data,
        "history": history,
    }


def _serialize_log(log: Log):
    # Guard against concurrent log mutations while serializing.
    with log._lock:
        logs = [item.output() for item in log.logs[-LOG_SIZE:]]  # serialize LogItem objects
        guid = log.guid
        progress = log.progress
        progress_no = log.progress_no
    return {
        "guid": guid,
        "logs": logs,
        "progress": progress,
        "progress_no": progress_no,
    }


def _deserialize_context(data):
    config = initialize_agent()
    log = _deserialize_log(data.get("log", None))

    context = AgentContext(
        config=config,
        id=data.get("id", None),  # get new id
        name=data.get("name", None),
        created_at=(
            datetime.fromisoformat(
                # older chats may not have created_at - backcompat
                data.get("created_at", datetime.fromtimestamp(0).isoformat())
            )
        ),
        type=AgentContextType(data.get("type", AgentContextType.USER.value)),
        last_message=(
            datetime.fromisoformat(
                data.get("last_message", datetime.fromtimestamp(0).isoformat())
            )
        ),
        log=log,
        paused=False,
        data=data.get("data", {}),
        output_data=data.get("output_data", {}),
        user_id=data.get("user_id", 0), # Default to backdoor user for legacy chats
        # agent0=agent0,
        # streaming_agent=straming_agent,
    )

    agents = data.get("agents", [])
    agent0 = _deserialize_agents(agents, config, context)
    streaming_agent = agent0
    while streaming_agent and streaming_agent.number != data.get("streaming_agent", 0):
        streaming_agent = streaming_agent.data.get(Agent.DATA_NAME_SUBORDINATE, None)

    context.agent0 = agent0
    context.streaming_agent = streaming_agent

    return context


def _deserialize_agents(
    agents: list[dict[str, Any]], config: AgentConfig, context: AgentContext
) -> Agent:
    prev: Agent | None = None
    zero: Agent | None = None

    for ag in agents:
        current = Agent(
            number=ag["number"],
            config=config,
            context=context,
        )
        current.data = ag.get("data", {})
        current.history = history.deserialize_history(
            ag.get("history", ""), agent=current
        )
        if not zero:
            zero = current

        if prev:
            prev.set_data(Agent.DATA_NAME_SUBORDINATE, current)
            current.set_data(Agent.DATA_NAME_SUPERIOR, prev)
        prev = current

    return zero or Agent(0, config, context)


# def _deserialize_history(history: list[dict[str, Any]]):
#     result = []
#     for hist in history:
#         content = hist.get("content", "")
#         msg = (
#             HumanMessage(content=content)
#             if hist.get("type") == "human"
#             else AIMessage(content=content)
#         )
#         result.append(msg)
#     return result


def _deserialize_log(data: dict[str, Any]) -> "Log":
    log = Log()
    log.guid = data.get("guid", str(uuid.uuid4()))
    log.set_initial_progress()

    # Deserialize the list of LogItem objects
    i = 0
    for item_data in data.get("logs", []):
        agentno = item_data.get("agentno")
        if agentno is None:
            agentno = item_data.get("agent_number", 0)
        log.logs.append(
            LogItem(
                log=log,  # restore the log reference
                no=i,  # item_data["no"],
                type=item_data["type"],
                heading=item_data.get("heading", ""),
                content=item_data.get("content", ""),
                kvps=OrderedDict(item_data["kvps"]) if item_data["kvps"] else None,
                timestamp=item_data.get("timestamp", 0.0),
                agentno=agentno,
                id=item_data.get("id"),
            )
        )
        log.updates.append(i)
        i += 1

    return log


def _safe_json_serialize(obj, **kwargs):
    def serializer(o):
        if isinstance(o, dict):
            return {k: v for k, v in o.items() if is_json_serializable(v)}
        elif isinstance(o, (list, tuple)):
            return [item for item in o if is_json_serializable(item)]
        elif is_json_serializable(o):
            return o
        else:
            return None  # Skip this property

    def is_json_serializable(item):
        try:
            json.dumps(item)
            return True
        except (TypeError, OverflowError):
            return False

    return json.dumps(obj, default=serializer, **kwargs)
