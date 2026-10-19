"""Native daylight authoring and captures in the explicitly selected C: checkout."""
import base64
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import winreg

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Tools"))
from map_daylight import PROFILES, apply_profile

engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
process = subprocess.Popen([str(Path(engine) / "bin/managed/sbox-cli.exe"), "--connect", "--request-timeout", "180"],
    cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", bufsize=1)
diagnostics = []
threading.Thread(target=lambda: diagnostics.extend(process.stderr), daemon=True).start()
request_id = 0

def request(method, params):
    global request_id
    request_id += 1
    process.stdin.write(json.dumps({"jsonrpc":"2.0", "id":request_id, "method":method, "params":params}) + "\n")
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
    result = request("tools/call", {"name":name, "arguments":arguments or {}})
    if result.get("isError"):
        raise RuntimeError(result)
    return result

def structured(result):
    if result.get("structuredContent") is not None:
        return result["structuredContent"]
    return json.loads("\n".join(x["text"] for x in result["content"] if x["type"] == "text"))

def asset_text(result):
    for item in result["content"]:
        if item["type"] != "text":
            continue
        try:
            value = json.loads(item["text"])
        except ValueError:
            continue
        if isinstance(value, dict) and "GameObjects" in value:
            return item["text"]
    raise RuntimeError("Unexpected native scene JSON response")

def patch_values(source, changes, expected):
    # Replace the exact scalar tokens by GUID; retain all unrelated file formatting.
    value_pattern = r'"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null'
    for change in changes:
        guid = re.search(r'"__guid"\s*:\s*"' + re.escape(change["id"]) + r'"', source)
        if not guid:
            raise ValueError(change)
        next_guid = re.search(r'"__guid"\s*:', source[guid.end():])
        end = guid.end() + next_guid.start() if next_guid else len(source)
        prop = re.compile(r'("' + re.escape(change["property"]) + r'"\s*:\s*)(' + value_pattern + r')')
        match = prop.search(source, guid.end(), end)
        if not match:
            raise ValueError("Property token not found: " + str(change))
        if json.loads(match.group(2)) != change["before"]:
            raise ValueError("Unexpected old property: " + str(change))
        source = source[:match.start(2)] + json.dumps(change["after"]) + source[match.end(2):]
    if json.loads(source) != expected:
        raise ValueError("The candidate changed content beyond the reviewed properties")
    return source

def run_script(filename, config=None):
    target = EXCHANGE / filename
    target.write_text((OUT / filename).read_text(encoding="utf-8"), encoding="utf-8")
    if config is not None:
        (EXCHANGE / "capture.json").write_text(json.dumps(config), encoding="utf-8")
    return structured(call("run_csharp", {"path":str(target)}))

def current_status():
    status = structured(call("editor_status"))
    if not os.path.samefile(status["Paths"]["ProjectRoot"], ROOT):
        raise RuntimeError("Editor is on another checkout")
    if status["IsPlaying"] or status["IsCompiling"]:
        raise RuntimeError("Expected an idle editor")
    return status

try:
    init = request("initialize", {"protocolVersion":"2025-11-25", "capabilities":{},
                                "clientInfo":{"name":"map-daylight", "version":"1"}})
    (OUT / "native-handshake.json").write_text(json.dumps(init, indent=2), encoding="utf-8")
    print(json.dumps({"meta":init.get("_meta")}), flush=True)
    process.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"}) + "\n")
    process.stdin.flush()
    EXCHANGE = Path(init["_meta"]["exchangeDirectory"])
    status = current_status()
    mode = sys.argv[1]
    if mode == "prepare":
        plan = []
        (OUT / "candidates").mkdir(exist_ok=True)
        for path in sorted((ROOT / "Assets/scenes/maps").rglob("*.scene")):
            local = json.loads(path.read_text(encoding="utf-8-sig"))
            title = local.get("Title")
            if title not in PROFILES:
                continue
            asset = str(path.relative_to(ROOT / "Assets")).replace("\\", "/")
            source = asset_text(call("asset_read", {"path":asset}))
            before = json.loads(source)
            expected = copy.deepcopy(before)
            changes = apply_profile(expected)
            candidate = patch_values(source, changes, expected)
            assert apply_profile(copy.deepcopy(expected)) == [], "Profile must be idempotent"
            slug = title.lower().replace(" ", "")
            (OUT / "candidates" / (slug + ".before.json")).write_text(source, encoding="utf-8")
            (OUT / "candidates" / (slug + ".json")).write_text(candidate, encoding="utf-8")
            plan.append({"map":title, "slug":slug, "path":asset, "mood":PROFILES[title]["mood"], "changes":changes})
            print(json.dumps({"map":title, "mood":PROFILES[title]["mood"], "properties":len(changes)}), flush=True)
        (OUT / "native-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    elif mode == "apply":
        plan = json.loads((OUT / "native-plan.json").read_text())
        selected = set(sys.argv[2:])
        open_scenes = structured(call("list_scenes"))["Scenes"]
        open_paths = {x["ResourcePath"].lower() for x in open_scenes}
        for entry in plan:
            if selected and entry["slug"] not in selected:
                continue
            status = current_status()
            before = json.loads((OUT / "candidates" / (entry["slug"] + ".before.json")).read_text())
            candidate = (OUT / "candidates" / (entry["slug"] + ".json")).read_text()
            expected = json.loads(candidate)
            current = json.loads(asset_text(call("asset_read", {"path":entry["path"]})))
            if current == expected:
                print(json.dumps({"map":entry["map"], "state":"already applied; verified"}), flush=True)
                continue
            if current != before:
                raise RuntimeError(entry["map"] + ": saved scene changed since preparation")
            if entry["path"].lower() in open_paths:
                if status["ActiveScenePath"].lower() != entry["path"].lower() or status["SceneHasUnsavedChanges"]:
                    raise RuntimeError("Open map must be the active clean scene: " + entry["map"])
                grouped = {}
                for change in entry["changes"]:
                    if change["property"] == "Rotation":
                        angles = ",".join(str(x) for x in PROFILES[entry["map"]]["sun_angles"])
                        call("set_game_object", {"id":change["id"], "angles":angles})
                    else:
                        grouped.setdefault(change["id"], {})[change["property"]] = change["after"]
                for ident, properties in grouped.items():
                    call("set_component", {"id":ident, "properties":properties})
                call("save_scene")
            else:
                call("asset_write", {"path":entry["path"], "json":candidate})
            actual = json.loads(asset_text(call("asset_read", {"path":entry["path"]})))
            (OUT / (entry["slug"] + ".native-saved.json")).write_text(json.dumps(actual, indent=2), encoding="utf-8")
            # Full equivalence for native file edits. Open scene serialization is audited separately.
            exact = actual == expected
            if entry["path"].lower() not in open_paths and not exact:
                raise RuntimeError("Unexpected scene write: " + entry["map"])
            remaining = apply_profile(copy.deepcopy(actual))
            if remaining:
                raise RuntimeError("Native profile values did not persist: " + str(remaining))
            print(json.dumps({"map":entry["map"], "saved":True, "exact_candidate":exact,
                              "properties":len(entry["changes"])}), flush=True)
    elif mode == "refine":
        slug = sys.argv[2]
        plan = json.loads((OUT / "native-plan.json").read_text())
        entry = next(x for x in plan if x["slug"] == slug)
        open_scenes = structured(call("list_scenes"))["Scenes"]
        if any(x["ResourcePath"].lower() == entry["path"].lower() for x in open_scenes):
            raise RuntimeError("Refinement requires a closed scene")
        current_source = asset_text(call("asset_read", {"path":entry["path"]}))
        current = json.loads(current_source)
        previous = json.loads((OUT / "candidates" / (slug + ".json")).read_text())
        if current != previous:
            raise RuntimeError("Saved scene changed since the preceding verification")
        expected = copy.deepcopy(current)
        changes = apply_profile(expected)
        candidate = patch_values(current_source, changes, expected)
        if not changes:
            raise RuntimeError("No refinement pending")
        (OUT / (slug + ".refine-before.json")).write_text(current_source, encoding="utf-8")
        call("asset_write", {"path":entry["path"], "json":candidate})
        actual_source = asset_text(call("asset_read", {"path":entry["path"]}))
        if json.loads(actual_source) != expected:
            raise RuntimeError("Unexpected refinement write")
        (OUT / "candidates" / (slug + ".json")).write_text(candidate, encoding="utf-8")
        (OUT / (slug + ".native-saved.json")).write_text(actual_source, encoding="utf-8")
        original = json.loads((OUT / "candidates" / (slug + ".before.json")).read_text())
        entry["changes"] = apply_profile(original)
        (OUT / "native-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"map":entry["map"], "refinement":changes, "saved":True}), flush=True)
    elif mode == "weather-check":
        result = run_script("check-weather.cs")
        (OUT / "weather-restoration.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result), flush=True)
    elif mode == "capture":
        slug, suffix = sys.argv[2:4]
        plan = json.loads((OUT / "native-plan.json").read_text())
        entry = next(x for x in plan if x["slug"] == slug)
        initial = current_status()
        initial_scenes = structured(call("list_scenes"))["Scenes"]
        already_open = any(x["ResourcePath"].lower() == entry["path"].lower() for x in initial_scenes)
        try:
            call("open_scene", {"path":entry["path"]})
            config = {"map":entry["path"].lower(), "slug":slug, "suffix":suffix,
                      "views":json.loads((OUT / "views.json").read_text())[slug]}
            result = run_script("capture.cs", config)
            (OUT / (slug + "-" + suffix + ".json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result), flush=True)
        finally:
            if not already_open:
                call("close_scene", {"scene":entry["path"]})
            if initial["ActiveScenePath"]:
                call("switch_scene", {"scene":initial["ActiveScenePath"]})
    elif mode == "import-sky":
        print(json.dumps(run_script("import-sky.cs")), flush=True)
        print(json.dumps(structured(call("asset_compile", {"path":"materials/boxyard/sky/boxyard_midday.vmat"}))), flush=True)
    elif mode == "check":
        result = {"status":current_status(), "scenes":structured(call("list_scenes")),
                  "compile":structured(call("compile_status")),
                  "console":call("read_console", {"minimumLevel":"Error", "limit":15})}
        (OUT / "native-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result), flush=True)
    else:
        raise ValueError(mode)
finally:
    process.stdin.close()
    process.wait(timeout=10)
    if diagnostics:
        print("".join(diagnostics), file=sys.stderr, end="")

