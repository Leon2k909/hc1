"""Check the tactical preset's round flow, equipment defaults and serialized references."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
assets = root / "Assets"
prefabs = assets / "prefabs/game_modes"

def objects(obj):
    yield obj
    for child in obj.get("Children", []):
        yield from objects(child)

def component(obj, kind):
    return next(c for c in obj.get("Components", []) if c["__type"].split(".")[-1] == kind)

mode = json.loads((prefabs / "tactical_defuse.prefab").read_text(encoding="utf-8-sig"))
root_obj = mode["RootObject"]
nodes = list(objects(root_obj))
settings = component(root_obj, "GameMode")
assert settings["Ident"] == "tactical_defuse" and settings["MapObjectMode"] == "Defuse"
assert settings["ArmorEnabled"] and settings["HelmetsEnabled"] and settings["UsesStandardHealth"]
assert component(root_obj, "HudOptions")["ShowArmorVitals"]
assert not settings["HealthRegenerationEnabled"] and not settings["UnlimitedMoney"]
defaults = component(root_obj, "DefaultEquipment")
assert not defaults["LoadoutsEnabled"] and not defaults["ApplySavedAttachments"]
assert defaults["Armor"] == 0 and not defaults["Helmet"] and not defaults["DefuseKit"]
for loadout in defaults["TeamLoadouts"]:
    equipment = [json.loads((assets / path).read_text(encoding="utf-8-sig")) for path in loadout["Equipment"]]
    assert {item["Slot"] for item in equipment} == {"Secondary", "Melee"}
    assert all(item.get("Category") in (None, "Pistol", "Melee") for item in equipment)

by_name = {obj["Name"]: obj for obj in nodes}
assert component(by_name["Freeze Time"], "StateComponent")["DefaultDuration"] == 20
assert component(by_name["Respawn Players"], "RespawnPlayers")["ForceNew"] is False
assert component(by_name["Play Round"], "RoundLimit")["MaxRounds"] == 24
assert component(by_name["Play Round"], "TeamEarlyWinCondition")["TargetScore"] == 13
assert component(by_name["Start Half"], "ResetBalance")["Value"] == 800
assert component(by_name["Start Half"], "ClearEquipment")["ClearProtection"]
buy_states = {obj["Name"] for obj in nodes for c in obj.get("Components", []) if c["__type"].split(".")[-1] == "EnableBuyMenu"}
assert buy_states == {"Waiting", "Freeze Time"}, buy_states

declared = {}
for obj in nodes:
    assert obj["__guid"] not in declared
    declared[obj["__guid"]] = (obj["__guid"], "GameObject")
    for c in obj.get("Components", []):
        assert c["__guid"] not in declared
        declared[c["__guid"]] = (obj["__guid"], c["__type"].split(".")[-1])

def references(value):
    if isinstance(value, dict):
        if value.get("_type") == "component":
            owner, kind = declared[value["component_id"]]
            assert owner == value["go"] and kind == value["component_type"]
        for item in value.values():
            references(item)
    elif isinstance(value, list):
        for item in value:
            references(item)
references(mode)

ordinary = json.loads((prefabs / "bomb_defusal.prefab").read_text(encoding="utf-8-sig"))
original_ids = {entry["__guid"] for obj in objects(ordinary["RootObject"]) for entry in [obj, *obj.get("Components", [])]}
assert not original_ids.intersection(declared), "The new mode must not collide with the original preset's IDs."
for path in prefabs.glob("*.prefab"):
    obj = json.loads(path.read_text(encoding="utf-8-sig"))["RootObject"]
    game_mode = component(obj, "GameMode")
    if game_mode["Ident"] not in {"tactical_defuse", "zombies"}:
        assert not game_mode.get("ArmorEnabled", False) and not game_mode.get("HelmetsEnabled", False)
zombies = component(json.loads((prefabs / "zombies.prefab").read_text(encoding="utf-8-sig"))["RootObject"], "GameMode")
assert zombies["ArmorEnabled"] and not zombies["HelmetsEnabled"]
print(f"PASS: {len(declared)} serialized IDs and all state references; 20-second buying, $800 pistol starts, retained survivors, 13-round victory and halftime resets.")
print("PASS: ordinary presets use health only; Zombies retains body armour without head protection.")
