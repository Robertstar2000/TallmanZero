import re
import traceback
import asyncio
from typing import Literal


_MODEL_ERROR_MARKERS = (
    "litellm",
    "ollama",
    "apiconnectionerror",
    "openai",
)
_CONNECTION_ERROR_MARKERS = (
    "cannot connect to host",
    "connect call failed",
    "connection refused",
    "connection reset by peer",
    "network is unreachable",
    "no route to host",
    "temporary failure in name resolution",
    "name or service not known",
    "timed out",
)
_URL_RE = re.compile(r"https?://[^\s,\]]+")
_HOST_RE = re.compile(r"cannot connect to host\s+([^\s]+)", re.IGNORECASE)
_SOCKET_RE = re.compile(r"connect call failed\s+\('([^']+)',\s*(\d+)\)", re.IGNORECASE)


def handle_error(e: Exception):
    # if asyncio.CancelledError, re-raise
    if isinstance(e, asyncio.CancelledError):
        raise e


def error_text(e: Exception):
    return str(e)


def is_connection_error(e: BaseException) -> bool:
    if isinstance(e, asyncio.CancelledError):
        return False

    type_text = f"{type(e).__module__}.{type(e).__qualname__}".lower()
    if any(marker in type_text for marker in ("apiconnectionerror", "connecterror", "clientconnectorerror")):
        return True

    message = str(e).lower()
    return any(marker in message for marker in _CONNECTION_ERROR_MARKERS)


def is_model_connection_error(e: BaseException) -> bool:
    if not is_connection_error(e):
        return False

    type_text = f"{type(e).__module__}.{type(e).__qualname__}".lower()
    message = str(e).lower()
    return any(marker in type_text or marker in message for marker in _MODEL_ERROR_MARKERS)


def extract_connection_target(e: BaseException) -> str | None:
    message = str(e)

    if match := _URL_RE.search(message):
        return match.group(0).rstrip(".,)")
    if match := _HOST_RE.search(message):
        return match.group(1).rstrip(".,)")
    if match := _SOCKET_RE.search(message):
        return f"{match.group(1)}:{match.group(2)}"

    return None


def describe_model_connection_error(
    e: BaseException,
    *,
    provider: str = "",
    model_name: str = "",
    api_base: str = "",
) -> str:
    endpoint = (api_base or "").strip() or extract_connection_target(e) or "the configured model endpoint"
    model_ref = "/".join(part for part in [provider.strip(), model_name.strip()] if part)

    if model_ref:
        return (
            f"The configured model `{model_ref}` is unreachable from this container at "
            f"`{endpoint}`. Restore network access to that server and try again."
        )

    return (
        f"The configured model endpoint is unreachable from this container: "
        f"`{endpoint}`. Restore network access to that server and try again."
    )


def format_error(
    e: Exception,
    start_entries=20,
    end_entries=15,
    error_message_position: Literal["top", "bottom", "none"] = "top",
):
    # format traceback from the provided exception instead of the most recent one
    traceback_text = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    # Split the traceback into lines
    lines = traceback_text.split("\n")

    if not start_entries and not end_entries:
        trimmed_lines = []
    else:

        # Find all "File" lines
        file_indices = [
            i for i, line in enumerate(lines) if line.strip().startswith("File ")
        ]

        # If we found at least one "File" line, trim the middle if there are more than start_entries+end_entries lines
        if len(file_indices) > start_entries + end_entries:
            start_index = max(0, len(file_indices) - start_entries - end_entries)
            trimmed_lines = (
                lines[: file_indices[start_index]]
                + [
                    f"\n>>>  {len(file_indices) - start_entries - end_entries} stack lines skipped <<<\n"
                ]
                + lines[file_indices[start_index + end_entries] :]
            )
        else:
            # If no "File" lines found, or not enough to trim, just return the original traceback
            trimmed_lines = lines

    # Find the error message at the end
    error_message = ""
    for line in reversed(lines):
        # match both simple errors and module.path.Error patterns
        if re.match(r"[\w\.]+Error:\s*", line):
            error_message = line
            break

    if error_message and error_message_position in ("top", "bottom", "none"):
        for i in range(len(trimmed_lines) - 1, -1, -1):
            if trimmed_lines[i].strip() == error_message.strip():
                trimmed_lines = trimmed_lines[:i] + trimmed_lines[i + 1 :]
                break

    # Combine the trimmed traceback with the error message
    if not trimmed_lines:
        result = "" if error_message_position == "none" else error_message
    else:
        result = "Traceback (most recent call last):\n" + "\n".join(trimmed_lines)

    if error_message and error_message_position == "top":
        result = f"{error_message}\n\n{result}" if result else error_message
    elif error_message and error_message_position == "bottom":
        result = f"{result}\n\n{error_message}" if result else error_message

    # at least something
    if not result:
        result = str(e)

    return result


class RepairableException(Exception):
    """An exception type indicating errors that can be surfaced to the LLM for potential self-repair."""

    pass


class InterventionException(Exception):
    """An exception type raised on user intervention, skipping rest of message loop iteration."""

    pass


class HandledException(Exception):
    pass
