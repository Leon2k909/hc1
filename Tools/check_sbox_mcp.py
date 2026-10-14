#!/usr/bin/env python3
"""Validate the configured native MCP against the open editor without editing its scene."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import tomllib


def main():
    project = Path(__file__).resolve().parent.parent
    config_root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config = tomllib.loads((config_root / "config.toml").read_text(encoding="utf-8-sig"))
    server = config["mcp_servers"]["sbox"]
    assert server.get("enabled", True), "The native MCP server is disabled."
    assert "--connect" in server["args"], "Validation must attach to an existing editor."
    messages = queue.Queue()
    request_id = 0
    exchange_directory = None

    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as errors:
        process = subprocess.Popen(
            [server["command"], *server["args"]],
            cwd=server.get("cwd") or project,
            env={**os.environ, **server.get("env", {})},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors,
            text=True, encoding="utf-8", bufsize=1,
        )

        def read_stdout():
            try:
                for line in process.stdout:
                    messages.put(json.loads(line))
            except Exception as error:
                messages.put(error)
            finally:
                messages.put(None)

        reader = threading.Thread(target=read_stdout, daemon=True)
        reader.start()

        def send(message):
            process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            process.stdin.flush()

        def request(method, params=None):
            nonlocal request_id
            request_id += 1
            send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
            while True:
                message = messages.get(timeout=45)
                if message is None:
                    errors.seek(0)
                    raise RuntimeError("MCP process exited: " + errors.read())
                if isinstance(message, Exception):
                    raise message
                if message.get("id") != request_id:
                    continue
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message["result"]

        def call(name, arguments=None, expected_error=None, raw=False):
            result = request("tools/call", {
                "name": "call_tool",
                "arguments": {"name": name, "arguments": arguments or {}},
            })
            text = "\n".join(item["text"] for item in result.get("content", []) if item["type"] == "text")
            if expected_error:
                assert result.get("isError"), f"{name} unexpectedly succeeded."
                assert expected_error.casefold() in text.casefold(), text
                return text
            assert not result.get("isError"), f"{name}: {text}"
            if raw:
                return result
            if "structuredContent" in result:
                return result["structuredContent"]
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

        try:
            initialized = request("initialize", {
                "protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "sbox-editor-control-check", "version": "1.0"},
            })
            exchange_directory = initialized.get("_meta", {}).get("exchangeDirectory")
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            print("Checking native MCP tool listing...", flush=True)
            entry_points = request("tools/list")["tools"]
            assert "search_tools" in {tool["name"] for tool in entry_points}
            print("Checking native tools and Bridge helpers...", flush=True)
            before = call("editor_status")
            assert Path(before["Paths"]["ProjectRoot"]).resolve() == project
            assert before["LastCompileSucceeded"] and before["LastCompileErrors"] == 0

            schemas = call("describe_toolset", {"name": "bridge_helpers"})["tools"]
            by_name = {tool["name"]: tool for tool in schemas}
            assert len(by_name) == 6
            for name in ("bridge_list_handlers", "bridge_describe_handler", "bridge_read"):
                assert by_name[name]["annotations"]["readOnlyHint"]
            for name in ("bridge_call", "bridge_simulate_input", "bridge_scatter_props"):
                assert not by_name[name].get("annotations", {}).get("readOnlyHint", False)
            assert by_name["bridge_scatter_props"]["inputSchema"]["properties"]["center"]["type"] == "string"

            listing = call("bridge_list_handlers")
            source = (project / "Libraries/sboxskinsgg.claudebridge/Editor/MyEditorMenu.cs").read_text(encoding="utf-8-sig")
            expected = set(re.findall(r'Register\s*\(\s*"([^"]+)"\s*,\s*\(\)\s*=>\s*new\s+\w+', source))
            assert {item["Command"] for item in listing["Handlers"]} == expected
            assert listing["Count"] == len(expected)
            assert isinstance(call("bridge_read", {"command": "get_project_info"}), dict)
            for command, filename in (("simulate_input", "MyEditorMenu.cs"), ("create_npc_brain", "NpcBrainHandlers.cs"), ("create_health_system", "ScaffoldHandlers.cs")):
                description = call("bridge_describe_handler", {"command": command})
                assert description["SourceFile"].endswith(filename), description
                assert "Execute" in description["Source"]

            call("bridge_read", {"command": "scatter_props"}, expected_error="not an allowlisted read-only")
            call("bridge_call", {"command": "__missing_mcp_validation_handler__"}, expected_error="Unknown command")
            call("bridge_simulate_input", {"action": "jump", "state": "invalid"}, expected_error="state must be")
            call("bridge_scatter_props", {"model": "__missing_mcp_validation_model__.vmdl", "center": "0,0,0", "count": 0}, expected_error="count must be")
            if before["IsPlaying"]:
                call("bridge_call", {"command": "scatter_props"}, expected_error="not allowed while play mode")
                call("bridge_scatter_props", {"model": "__missing_mcp_validation_model__.vmdl", "center": "0,0,0"}, expected_error="not allowed while play mode")

            call("run_csharp", {"code": "return Game.ActiveScene?.Name;"})
            screenshot_tool = "camera_screenshot" if before["IsPlaying"] else "editor_camera_screenshot"
            screenshot = call(screenshot_tool, {"width": 320, "height": 180}, raw=True)
            pixels = next(item for item in screenshot["content"] if item["type"] == "image")
            png = base64.b64decode(pixels["data"], validate=True)
            assert png.startswith(b"\x89PNG\r\n\x1a\n")

            compilation = call("compile_status")
            assert not compilation["IsBuilding"]
            assert all(item["Errors"] == 0 for item in compilation["Compilers"])
            native_diagnostics = [d for compiler in compilation["Compilers"] for d in compiler["Diagnostics"] if "ClaudeBridge.NativeMcp.cs" in d.get("File", "")]
            assert not native_diagnostics, native_diagnostics
            after = call("editor_status")
            for key in ("ActiveScenePath", "SceneHasUnsavedChanges", "IsPlaying", "IsPaused"):
                assert before[key] == after[key], f"Editor state changed: {key}"
            print(f"PASS: native stdio handshake; {after['ToolCount']} native tools; all {listing['Count']} Bridge handlers accessible.")
            print("PASS: helper schemas, source discovery, read-only checks, error propagation and argument validation.")
            print("PASS: C# execution, PNG screenshot and compilation with no new diagnostics.")
            print("PASS: scene, unsaved state and play/pause state preserved.")
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            reader.join(timeout=5)
            process.stdout.close()
            if exchange_directory:
                target = Path(exchange_directory).resolve()
                temporary_root = (Path(tempfile.gettempdir()) / "sbox-cli").resolve()
                if target.parent == temporary_root and target.is_dir():
                    shutil.rmtree(target)
            assert process.poll() is not None, "Validation left the MCP process running."
            print("PASS: validation connection closed; the attached editor remains open.")


if __name__ == "__main__":
    main()
