"""Accepted Orion cable reel: native-serialized renderer plus the original packed collision."""
import json
from pathlib import Path

MODEL = "models/props/orion/cable_reel_v1/cable_reel.vmdl"
INSTANCE = Path(__file__).resolve().parents[1] / "Sources/Orion/cable-reel-trial-v1/native-instance.json"


def collision(model, deck_height):
    # The reviewed reel remains beside the generator. The old second placement
    # was inside DECK_STAIR; neither its shell nor its collider should return.
    model.collision_box((354, 1294, deck_height), (406, 1346, deck_height + 46), "metal")


def scene_object():
    # Preserve the engine's component schema and stable instance/component IDs.
    node = json.loads(INSTANCE.read_text(encoding="utf-8"))
    assert node["Name"] == "ORION cable reel"
    assert [c for c in node["Components"] if c["__type"] == "Sandbox.ModelRenderer"][0]["Model"]["Path"] == MODEL
    assert not any(c["__type"].endswith("Collider") for c in node["Components"])
    return node
