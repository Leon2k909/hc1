#!/usr/bin/env python3
"""Expose the s&box Claude Bridge file IPC as local Codex MCP tools."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
import uuid
from pathlib import Path

SERVER_NAME = "sbox-claude-bridge"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2025-03-26"
SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
IPC_DIR = Path(os.environ.get("SBOX_BRIDGE_IPC_DIR") or Path(tempfile.gettempdir()) / "sbox-bridge-ipc")
SOURCE_RELATIVE = Path("Libraries") / "sboxskinsgg.claudebridge" / "Editor" / "MyEditorMenu.cs"
REGISTER_RE = re.compile(
    r'Register\s*\(\s*"([^"]+)"\s*,\s*\(\)\s*=>\s*new\s+(\w+)',
    re.MULTILINE,
)

# Only these query handlers are exposed without write approval.
READ_ONLY_COMMANDS = {
    "get_project_info", "list_project_files", "read_file", "list_scenes",
    "get_scene_hierarchy", "get_selected_objects", "get_property",
    "get_all_properties", "list_available_components", "is_playing",
    "get_runtime_property", "search_assets", "get_asset_info", "list_sounds",
    "list_prefabs", "get_prefab_info", "get_network_status",
    "get_project_config", "get_package_details", "list_asset_library",
    "list_component_buttons", "raycast", "raycast_terrain", "get_navmesh_path",
    "physics_overlap", "describe_type", "search_types", "get_method_signature",
    "find_in_project", "get_bounds", "list_animations", "get_tags",
}


def active_project_and_source():
    roots = []
    configured_root = os.environ.get("SBOX_BRIDGE_SOURCE_ROOT")
    if configured_root:
        roots.append(Path(configured_root))
    # The adapter is installed in the project it is meant to control. Prefer
    # that source over the shared temp IPC junction, which may target another
    # project when multiple s&box projects use the bridge.
    roots.append(Path(__file__).resolve().parent.parent)
    try:
        real_ipc = IPC_DIR.resolve(strict=False)
        if real_ipc.name.casefold() == "bridge-ipc":
            roots.append(real_ipc.parent.parent)
    except OSError:
        pass
    for root in roots:
        source = root / SOURCE_RELATIVE
        if source.is_file():
            return root, source
    raise RuntimeError(
        "Could not find the active project's Claude Bridge source beside its IPC junction. "
        "Set SBOX_BRIDGE_SOURCE_ROOT if the project stores the bridge elsewhere."
    )


def load_handlers():
    root, source_path = active_project_and_source()
    source = source_path.read_text(encoding="utf-8-sig")
    handlers = {name: cls for name, cls in REGISTER_RE.findall(source)}
    if not handlers:
        raise RuntimeError("No bridge handlers were found in the active project source.")
    return root, source, handlers


def read_status():
    path = IPC_DIR / "status.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def public_status():
    status = read_status()
    result = {
        "ipcAvailable": IPC_DIR.is_dir(),
        "running": bool(status and status.get("running")),
    }
    if status:
        for key in ("version", "startedAt", "heartbeat", "handlerCount"):
            if key in status:
                result[key] = status[key]
    try:
        root, _ = active_project_and_source()
        result["project"] = root.name
    except Exception:
        pass
    return result


def bridge_request(command, params, allowed):
    if command not in allowed:
        raise ValueError(f"Unknown bridge handler '{command}'. Use sbox_bridge_list_handlers.")
    if not isinstance(params, dict):
        raise ValueError("params must be a JSON object.")
    status = read_status()
    if not IPC_DIR.is_dir() or (status is not None and not status.get("running", False)):
        raise RuntimeError("The s&box Claude Bridge is not running.")

    request_id = "codex-" + uuid.uuid4().hex
    request_path = IPC_DIR / f"req_{request_id}.json"
    response_path = IPC_DIR / f"res_{request_id}.json"
    temp_path = IPC_DIR / f".{request_id}.tmp"
    payload = {"id": request_id, "command": command, "params": params}
    try:
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temp_path, request_path)
        deadline = time.monotonic() + 45.0
        while time.monotonic() < deadline:
            if response_path.is_file():
                raw = response_path.read_text(encoding="utf-8-sig")
                response_path.unlink(missing_ok=True)
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    value = {"rawResponse": raw}
                failed = isinstance(value, dict) and (
                    value.get("success") is False or bool(value.get("error"))
                )
                return value, failed
            time.sleep(0.1)
        raise TimeoutError(
            "The editor did not answer within 45 seconds. Check that it is running "
            "and not blocked by a modal dialog."
        )
    finally:
        temp_path.unlink(missing_ok=True)
        request_path.unlink(missing_ok=True)


def result(value, is_error=False):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}


READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True, "destructiveHint": False, "openWorldHint": False,
}
MUTATING_ANNOTATIONS = {
    "readOnlyHint": False, "destructiveHint": True, "openWorldHint": False,
}


def make_tool(name, description, properties=None, required=None, annotations=None):
    schema = {"type": "object", "properties": properties or {}, "additionalProperties": False}
    if required:
        schema["required"] = required
    item = {"name": name, "description": description, "inputSchema": schema}
    if annotations:
        item["annotations"] = annotations
    return item


def build_tools():
    _, _, handlers = load_handlers()
    commands = sorted(handlers)
    read_commands = sorted(READ_ONLY_COMMANDS.intersection(handlers))
    command = {
        "type": "string",
        "enum": commands,
        "description": "Handler registered by the active s&box Claude Bridge.",
    }
    read_command = {**command, "enum": read_commands}
    bridge_params = {
        "type": "object",
        "description": "JSON parameters passed to the selected bridge handler.",
        "additionalProperties": True,
    }
    return [
        make_tool(
            "sbox_bridge_status",
            "Read the active s&box Claude Bridge connection status and heartbeat.",
            annotations=READ_ONLY_ANNOTATIONS,
        ),
        make_tool(
            "sbox_bridge_list_handlers",
            "List handlers registered by the active s&box Claude Bridge.",
            annotations=READ_ONLY_ANNOTATIONS,
        ),
        make_tool(
            "sbox_bridge_describe_handler",
            "Read a handler's C# implementation to inspect its parameters and behavior.",
            {"command": command}, ["command"], READ_ONLY_ANNOTATIONS,
        ),
        make_tool(
            "sbox_bridge_read",
            "Call an allowlisted read-only s&box bridge handler for project, scene, asset, or runtime inspection.",
            {"command": read_command, "params": bridge_params}, ["command"],
            READ_ONLY_ANNOTATIONS,
        ),
        make_tool(
            "sbox_bridge_call",
            "Call any handler registered by the active s&box Claude Bridge. Use the list/describe tools to discover handler parameters. This can change project or editor state.",
            {"command": command, "params": bridge_params}, ["command"],
            MUTATING_ANNOTATIONS,
        ),
    ]


def describe_handler(command):
    root, source, handlers = load_handlers()
    class_name = handlers.get(command)
    if not class_name:
        raise ValueError(f"Unknown bridge handler '{command}'.")
    marker = re.search(r"\bclass\s+" + re.escape(class_name) + r"\b", source)
    if not marker:
        raise RuntimeError(f"Handler class {class_name} was not found.")
    next_class = re.search(
        r"\n(?:public|internal)\s+(?:(?:sealed|abstract|static)\s+)?class\s+",
        source[marker.end():],
    )
    end = marker.end() + next_class.start() if next_class else len(source)
    excerpt = source[marker.start():end].strip()
    if len(excerpt) > 16000:
        excerpt = excerpt[:16000] + "\n\n[truncated]"
    return {"command": command, "handlerClass": class_name, "project": root.name, "source": excerpt}


def call_tool(name, arguments):
    arguments = arguments if isinstance(arguments, dict) else {}
    if name == "sbox_bridge_status":
        return result(public_status())
    if name == "sbox_bridge_list_handlers":
        root, _, handlers = load_handlers()
        return result({
            "project": root.name,
            "count": len(handlers),
            "handlers": [
                {"command": cmd, "handlerClass": cls, "readOnly": cmd in READ_ONLY_COMMANDS}
                for cmd, cls in sorted(handlers.items())
            ],
        })
    if name == "sbox_bridge_describe_handler":
        command = arguments.get("command")
        if not isinstance(command, str):
            raise ValueError("command must be a string.")
        return result(describe_handler(command))
    if name in ("sbox_bridge_read", "sbox_bridge_call"):
        command = arguments.get("command")
        if not isinstance(command, str):
            raise ValueError("command must be a string.")
        params = arguments.get("params", {})
        if name == "sbox_bridge_read":
            allowed = READ_ONLY_COMMANDS
        else:
            _, _, handlers = load_handlers()
            allowed = handlers
        response, failed = bridge_request(command, params, allowed)
        return result(response, failed)
    raise ValueError(f"Unknown MCP tool '{name}'.")


def send(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def rpc_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(message):
    if not isinstance(message, dict):
        return None, False
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None, False
    if method == "exit":
        return None, True
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }, False
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}, False
    if method == "shutdown":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}, False
    if method == "tools/list":
        try:
            return {
                "jsonrpc": "2.0", "id": request_id, "result": {"tools": build_tools()},
            }, False
        except Exception as exc:
            return rpc_error(request_id, -32603, str(exc)), False
    if method == "tools/call":
        try:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": call_tool(params.get("name"), params.get("arguments") or {}),
            }, False
        except Exception as exc:
            return {
                "jsonrpc": "2.0", "id": request_id, "result": result(str(exc), True),
            }, False
    if request_id is None:
        return None, False
    return rpc_error(request_id, -32601, f"Method not found: {method}"), False


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    for raw in sys.stdin.buffer:
        if not raw.strip():
            continue
        try:
            message = json.loads(raw.decode("utf-8"))
            response, should_exit = handle(message)
            if response is not None:
                send(response)
            if should_exit:
                break
        except Exception as exc:
            print(f"[sbox-claude-bridge-mcp] {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
