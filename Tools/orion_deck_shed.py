"""Orion's launch-deck control shed: the standalone model replaces the plain render box; the box's collision stays authoritative.

The old shed was `box( m, -230, -110, 1290, 1380, G, G + 110, ..., METAL )`: 12 render triangles plus one 120 x 90 x 110 in collision box.
Sources/Orion/deck-shed-v1/ has the model's generator (shed.py), its texture painter and native-instance.json, the scene object served below.
The user approved the new shed on 2026-11-06 and had the old box, its archive and its install/revert tooling deleted.
"""
import json
from pathlib import Path

MODEL = "models/props/orion/deck_shed_v1/shed.vmdl"
INSTANCE = Path(__file__).resolve().parents[1] / "Sources/Orion/deck-shed-v1/native-instance.json"


def collision(model, deck_height):
    """ The same box the old render box added to the collision, and nothing drawn. """
    model.collision_box((-230, 1290, deck_height), (-110, 1380, deck_height + 110), "metal")


def scene_object():
    node = json.loads(INSTANCE.read_text(encoding="utf-8"))
    assert node["Name"] == "ORION control shed"
    assert [c for c in node["Components"] if c["__type"] == "Sandbox.ModelRenderer"][0]["Model"]["Path"] == MODEL
    assert not any(c["__type"].endswith("Collider") for c in node["Components"])
    return node
