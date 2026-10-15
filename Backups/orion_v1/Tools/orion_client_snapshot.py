"""Read Orion's native network checks from an already running game process."""
import argparse
import json
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def snapshot(cli, pid, output):
    messages = queue.Queue()
    request_id = 0
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as errors:
        process = subprocess.Popen(
            [str(cli), "--connect", str(pid), "--request-timeout", "30"],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=errors, text=True, encoding="utf-8", bufsize=1,
        )

        def read():
            try:
                for line in process.stdout:
                    messages.put(json.loads(line))
            except Exception as error:
                messages.put(error)
            finally:
                messages.put(None)

        reader = threading.Thread(target=read, daemon=True)
        reader.start()

        def send(value):
            process.stdin.write(json.dumps(value) + "\n")
            process.stdin.flush()

        def request(method, params=None):
            nonlocal request_id
            request_id += 1
            send(dict(jsonrpc="2.0", id=request_id, method=method, params=params or {}))
            deadline = time.monotonic() + 40
            while True:
                value = messages.get(timeout=max(.01, deadline - time.monotonic()))
                if value is None:
                    errors.seek(0)
                    raise RuntimeError("Native connection closed: " + errors.read())
                if isinstance(value, Exception):
                    raise value
                if value.get("id") != request_id:
                    continue
                if "error" in value:
                    raise RuntimeError(value["error"])
                return value["result"]

        def call(name, arguments=None):
            value = request("tools/call", dict(name="call_tool", arguments=dict(
                name=name, arguments=arguments or {})))
            content = "\n".join(c["text"] for c in value.get("content", []) if c["type"] == "text")
            if value.get("isError"):
                raise RuntimeError(content)
            return value.get("structuredContent") or json.loads(content)

        try:
            initialized = request("initialize", dict(protocolVersion="2025-11-25", capabilities={},
                clientInfo=dict(name="orion-client-validation", version="1.0")))
            send(dict(jsonrpc="2.0", method="notifications/initialized"))
            entries = request("tools/list")["tools"]
            assert "call_tool" in {item["name"] for item in entries}
            status = call("instance_status")
            assert status["Pid"] == pid and status["Kind"] == "game", status
            exchange = Path(status.get("ExchangeDirectory") or initialized["_meta"]["exchangeDirectory"])
            script = exchange / "orion-network-snapshot.cs"
            shutil.copyfile(ROOT / "Sources/Orion/editor/network-snapshot.cs.txt", script)
            result = call("run_csharp", dict(path=str(script)))
            recorded = Path(result["Snapshot"])
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(recorded, output)
            report = result["Result"]
            print(json.dumps(dict(Output=str(output), Success=report["Success"], Pid=report["Pid"],
                Players=report["Players"], Models=len(report["Models"]), MissingMaterials=report["MissingMaterials"]), indent=2))
            return report["Success"]
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            reader.join(timeout=2)
            process.stdout.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pid", type=int)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cli", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if snapshot(args.cli, args.pid, args.output) else 1)
