"""Approved standalone Orion standby generator; original packed collision stays authoritative."""
import json
from pathlib import Path

MODEL = "models/props/orion/generator_v1/generator.vmdl"
INSTANCE = Path(__file__).resolve().parents[1] / "Sources/Orion/generator-trial-v1/native-instance.json"


def collision(model, deck_height):
    model.collision_box((200, 1300, deck_height), (330, 1370, deck_height + 70), "metal")


def scene_object():
    node = json.loads(INSTANCE.read_text(encoding="utf-8"))
    assert node["Name"] == "ORION standby generator"
    assert [c for c in node["Components"] if c["__type"] == "Sandbox.ModelRenderer"][0]["Model"]["Path"] == MODEL
    assert not any(c["__type"].endswith("Collider") for c in node["Components"])
    return node
