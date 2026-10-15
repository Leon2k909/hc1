"""Verify two native Orion clients and movement replicated between them."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def position(value):
    return tuple(float(x) for x in value.split(","))


def verify(before_host, before_client, after_host, after_client):
    snapshots = [json.loads(p.read_text()) for p in
                 (before_host, before_client, after_host, after_client)]
    bh, bc, ah, ac = snapshots
    errors = []
    for label, item in zip(("host before", "client before", "host after", "client after"), snapshots):
        if not item["Success"]:
            errors.append(f"{label}: native checks failed")
        if item["Scene"].lower() != "scenes/maps/orion/orion.scene":
            errors.append(f"{label}: wrong map")
    if not bh["IsHost"] or not ah["IsHost"] or not bc["IsClient"] or not ac["IsClient"]:
        errors.append("Unexpected host/client roles")
    if bh["Pid"] == bc["Pid"] or bh["LocalConnection"] == bc["LocalConnection"]:
        errors.append("Snapshots do not represent two distinct processes and connections")
    if bh["LocalConnection"] != ah["LocalConnection"] or bc["LocalConnection"] != ac["LocalConnection"]:
        errors.append("Connections changed during the check")
    tables = [{p["Connection"]: p for p in item["Players"] if p["IsConnected"]} for item in snapshots]
    expected = {bh["LocalConnection"], bc["LocalConnection"]}
    for label, table in zip(("host before", "client before", "host after", "client after"), tables):
        if not expected.issubset(table):
            errors.append(f"{label}: a connected player is missing")
    movement = []
    if not errors:
        for connection in sorted(expected):
            players = [table[connection] for table in tables]
            if len({p["Id"] for p in players}) != 1 or len({p["Pawn"] for p in players}) != 1:
                errors.append(f"{connection}: client or pawn identity differs between snapshots")
            if any(p["PawnOwner"] != connection or not p["OwnerMatches"] for p in players):
                errors.append(f"{connection}: ownership mismatch")
            host_delta = math.dist(position(players[0]["Position"]), position(players[2]["Position"]))
            client_delta = math.dist(position(players[1]["Position"]), position(players[3]["Position"]))
            final_error = math.dist(position(players[2]["Position"]), position(players[3]["Position"]))
            movement.append({"Connection": connection, "HostDistance": host_delta,
                             "ClientDistance": client_delta, "FinalPositionDifference": final_error,
                             "ReplicatedMovement": min(host_delta, client_delta) >= 8 and final_error <= 16})
        if not any(item["ReplicatedMovement"] for item in movement):
            errors.append("No movement was observed consistently in both processes")
    scene = ROOT / "Assets/scenes/maps/Orion/orion.scene"
    return {"Success": not errors, "CheckedAt": datetime.now(timezone.utc).isoformat(),
            "SceneSha256": hashlib.sha256(scene.read_bytes()).hexdigest(),
            "Errors": errors, "Movement": movement,
            "Snapshots": [{"Path": str(path.resolve()), "Sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                          for path in (before_host, before_client, after_host, after_client)],
            "Host": ah, "Client": ac}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for label in ("before-host", "before-client", "after-host", "after-client"):
        parser.add_argument("--" + label, type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/orion/network-validation.json")
    args = parser.parse_args()
    report = verify(args.before_host, args.before_client, args.after_host, args.after_client)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("Success", "Errors", "Movement")}, indent=2))
    raise SystemExit(0 if report["Success"] else 1)
