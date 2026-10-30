"""Use a short-lived native connection; execute QA scripts in its exchange directory."""
import argparse
import base64
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import winreg

parser = argparse.ArgumentParser()
parser.add_argument("--find")
parser.add_argument("--tool", default="editor_status")
parser.add_argument("--args-file", type=Path)
parser.add_argument("--script", type=Path)
parser.add_argument("--output-dir", type=Path)
parser.add_argument("--timeout", type=int, default=30)
parser.add_argument("--pid", type=int, help="Attach to a specific editor process when game clients are also running.")
parser.add_argument("--cleanup-exchange", action="store_true", help="Record this connection and remove its copied script and empty exchange directory afterward.")
parser.add_argument("--direct-call", action="store_true", help="Invoke the discovered tool directly through tools/call instead of the call_tool wrapper.")
args = parser.parse_args()
project = Path(__file__).resolve().parents[3]
output_dir = args.output_dir or project / "output/veridant/ivy-v2/native"
output_dir.mkdir(parents=True, exist_ok=True)
engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
messages = queue.Queue()
request_id = 0
exchange = None

with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as errors:
    process = subprocess.Popen(
        [str(Path(engine) / "bin/managed/sbox-cli.exe"), "--connect"]
        + ([str(args.pid)] if args.pid is not None else [])
        + ["--request-timeout", str(args.timeout)],
        cwd=project, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors,
        text=True, encoding="utf-8", bufsize=1,
    )

    def read_output():
        try:
            for line in process.stdout:
                messages.put(json.loads(line))
        finally:
            messages.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()

    def request(method, params):
        global request_id
        request_id += 1
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}) + "\n")
        process.stdin.flush()
        while True:
            message = messages.get(timeout=args.timeout + 10)
            if message is None:
                errors.seek(0)
                raise RuntimeError(errors.read())
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise RuntimeError(message["error"])
            return message["result"]

    def call(tool, arguments):
        params = {"name": tool, "arguments": arguments} if args.direct_call else {"name": "call_tool", "arguments": {"name": tool, "arguments": arguments}}
        result = request("tools/call", params)
        (output_dir / (tool + ".json")).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        for item in result.get("content", []):
            if item["type"] == "text":
                try:
                    value = json.loads(item["text"])
                    if tool == "compile_status":
                        value = {"IsBuilding": value["IsBuilding"], "Compilers": [{**{key: compiler[key] for key in ("Name", "IsBuilding", "Success", "Errors", "Warnings")}, "Diagnostics": [diagnostic for diagnostic in compiler["Diagnostics"] if diagnostic["Severity"] == "Error"]} for compiler in value["Compilers"]]}
                    print(json.dumps(value, ensure_ascii=False), flush=True)
                except (ValueError, KeyError, TypeError):
                    print(item["text"].replace("\r", ""), flush=True)
            elif item["type"] == "image":
                path = output_dir / (tool + ".png")
                path.write_bytes(base64.b64decode(item["data"]))
                print(str(path), flush=True)
        if result.get("isError"):
            raise RuntimeError("Native tool reported an error")
        return result

    try:
        initialized = request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "veridant-ivy-qa", "version": "1.0"}})
        exchange = initialized.get("_meta", {}).get("exchangeDirectory")
        if args.cleanup_exchange:
            (output_dir / "session.json").write_text(json.dumps(initialized, ensure_ascii=False), encoding="utf-8")
        if args.pid is not None:
            metadata = initialized.get("_meta", {})
            if metadata.get("pid") != args.pid or metadata.get("kind") != "editor":
                raise RuntimeError("The requested editor process did not match the native connection")
            if Path(metadata.get("project", "")).resolve().parent != project:
                raise RuntimeError("The connected editor is using a different project")
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        process.stdin.flush()
        if args.find is not None:
            call("search_tools", {"query": args.find})
        elif args.script:
            if not exchange:
                raise RuntimeError("Native connection did not provide an exchange directory")
            destination = Path(exchange) / args.script.name
            destination.write_text(args.script.read_text(encoding="utf-8"), encoding="utf-8")
            call("run_csharp", {"path": str(destination)})
        else:
            arguments = json.loads(args.args_file.read_text(encoding="utf-8")) if args.args_file else {}
            call(args.tool, arguments)
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=2)
        process.stdout.close()
        if args.cleanup_exchange and exchange:
            target = Path(exchange).resolve()
            temporary_root = (Path(tempfile.gettempdir()) / "sbox-cli").resolve()
            assert target.parent == temporary_root and len(target.name) == 32 and all(c in "0123456789abcdef" for c in target.name), "Unexpected exchange path; retained for inspection."
            if args.script and target.exists():
                copied_script = target / args.script.name
                assert copied_script.resolve().parent == target
                copied_script.unlink(missing_ok=True)
            if target.exists() and not any(target.iterdir()):
                target.rmdir()
            print(json.dumps({"ExchangeDirectory": str(target), "ExchangeRemoved": not target.exists()}), flush=True)
