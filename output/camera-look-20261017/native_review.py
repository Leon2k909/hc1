"""Task-scoped native MCP checks; attaches to the open editor and keeps scene/play state."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import winreg

root = Path.cwd().resolve()
output = root / "output/camera-look-20261017"
engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
process = subprocess.Popen(
    [str(Path(engine) / "bin/managed/sbox-cli.exe"), "--connect", "--request-timeout", "45"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", bufsize=1,
)
diagnostics = []
threading.Thread(target=lambda: diagnostics.extend(process.stderr), daemon=True).start()
request_id = 0

def request(method, params):
    global request_id
    request_id += 1
    process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}) + "\n")
    process.stdin.flush()
    while True:
        line = process.stdout.readline()
        if not line:
            raise RuntimeError("Native connection closed: " + "".join(diagnostics))
        response = json.loads(line)
        if "error" in response and response.get("id") is None:
            raise RuntimeError(response["error"])
        if response.get("id") != request_id:
            continue
        if "error" in response:
            raise RuntimeError(response["error"])
        return response["result"]

def call(name, arguments=None):
    result = request("tools/call", {"name": name, "arguments": arguments or {}})
    if result.get("isError"):
        raise RuntimeError(result)
    return result

def structured(result):
    if "structuredContent" in result:
        return result["structuredContent"]
    return json.loads("\n".join(x["text"] for x in result["content"] if x["type"] == "text"))

def asset_text(result):
    for item in result["content"]:
        if item["type"] == "text":
            try:
                data = json.loads(item["text"])
            except ValueError:
                continue
            if isinstance(data, dict) and ("RootObject" in data or "GameObjects" in data):
                return item["text"]
    raise RuntimeError("Unexpected asset_read format; asset was not changed.")

try:
    initialized = request("initialize", {
        "protocolVersion": "2025-11-25", "capabilities": {},
        "clientInfo": {"name": "camera-review", "version": "1"},
    })
    print(json.dumps({"instructions": initialized.get("instructions"), "meta": initialized.get("_meta")}), flush=True)
    process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
    process.stdin.flush()
    status = structured(call("editor_status"))
    assert Path(status["Paths"]["ProjectRoot"]).resolve() == root, status
    mode = sys.argv[1]
    assert not status["IsCompiling"], status
    if mode != "capture":
        assert not status["IsPlaying"], status
    if mode == "capture":
        result = call("camera_screenshot", {"includeUi": True})
        for item in result["content"]:
            if item["type"] == "image":
                path = output / "lowtide-live-camera.png"
                path.write_bytes(base64.b64decode(item["data"]))
                print(json.dumps({"screenshot": str(path)}), flush=True)
    elif mode == "inspect":
        result = call("editor_camera_screenshot")
        for item in result["content"]:
            if item["type"] == "image":
                path = output / "lowtide-editor-review.png"
                path.write_bytes(base64.b64decode(item["data"]))
                print(json.dumps({"screenshot": str(path)}), flush=True)
        result = call("asset_read", {"path": "prefabs/player/player.prefab"})
        (output / "player-prefab-native-read.json").write_text(json.dumps(result), encoding="utf-8")
        original = asset_text(result)
        (output / "player-prefab-before-cleanup.json").write_text(original, encoding="utf-8")
        print(json.dumps({"prefabBytes": len(original.encode("utf-8")), "obsoletePropertyCount": original.count('"RespawnProtectionSaturation"')}))
    elif mode == "cleanup":
        original = asset_text(call("asset_read", {"path": "prefabs/player/player.prefab"}))
        before = json.loads(original)
        (output / "player-prefab-before-cleanup.json").write_text(original, encoding="utf-8")
        controller = next(c for c in before["RootObject"]["Components"] if c["__type"] == "Facepunch.CameraController")
        assert controller["RespawnProtectionSaturation"] == 0.25
        del controller["RespawnProtectionSaturation"]
        import re
        updated, count = re.subn(r'(?m)^[ \t]*"RespawnProtectionSaturation": 0\.25,\r?\n', "", original)
        assert count == 1 and json.loads(updated) == before
        print(json.dumps({"write": structured(call("asset_write", {"path": "prefabs/player/player.prefab", "json": updated}))}), flush=True)
        actual = json.loads(asset_text(call("asset_read", {"path": "prefabs/player/player.prefab"})))
        assert actual == before, "Unexpected prefab changes after native save"
        print(json.dumps({"verified": "Only the obsolete protection saturation property was removed."}))
    elif mode == "refine":
        import copy
        import re
        for asset_path in ("prefabs/player/cameras/default_player_camera.prefab", "scenes/theater_playback.scene"):
            original = asset_text(call("asset_read", {"path": asset_path}))
            before = json.loads(original)
            expected = copy.deepcopy(before)
            found = []
            def visit(value):
                if isinstance(value, dict):
                    if value.get("__type") in ("Sandbox.Tonemapping", "Sandbox.ColorAdjustments"):
                        found.append(value)
                    for child in value.values():
                        visit(child)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)
            visit(expected)
            assert len(found) == 2, (asset_path, len(found))
            for effect in found:
                if effect["__type"] == "Sandbox.Tonemapping":
                    assert effect["Mode"] == "AgX"
                    effect["Mode"] = "ACES"
                else:
                    assert effect["__enabled"] is True
                    effect["__enabled"] = False
            updated, tones = re.subn(r'("__type": "Sandbox\.Tonemapping",[\s\S]*?"Mode": )"AgX"', r'\1"ACES"', original)
            updated, grades = re.subn(r'("__type": "Sandbox\.ColorAdjustments",\s*"__guid": "[^"]+",\s*"__enabled": )true', r'\1false', updated)
            assert tones == grades == 1 and json.loads(updated) == expected
            backup = output / (Path(asset_path).name + ".before-refine.json")
            backup.write_text(original, encoding="utf-8")
            saved = structured(call("asset_write", {"path": asset_path, "json": updated}))
            actual = json.loads(asset_text(call("asset_read", {"path": asset_path})))
            assert actual == expected, "Unexpected camera profile change after native save"
            print(json.dumps({"asset": asset_path, "write": saved, "verified": "ACES with extra global colour adjustments disabled; other content preserved."}), flush=True)
    else:
        raise RuntimeError("Unknown mode")
    after = structured(call("editor_status"))
    assert after["ActiveScenePath"] == status["ActiveScenePath"]
    assert after["SceneHasUnsavedChanges"] == status["SceneHasUnsavedChanges"]
    assert after["IsPlaying"] == status["IsPlaying"]
    print(json.dumps({"editorAfter": after}), flush=True)
finally:
    process.stdin.close()
    process.wait(timeout=10)
    if diagnostics:
        print("".join(diagnostics), file=sys.stderr, end="")

