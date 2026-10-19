"""Validate the staged scene's wiring and resource dependencies without starting a match."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"output/collider/stage"

def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values(): yield from walk(child)
    elif isinstance(value,list):
        for child in value: yield from walk(child)

def validate(scene_file=None, report_file=None):
    scene_file=Path(scene_file) if scene_file else STAGE/"collider.scene.json"
    data=json.loads(scene_file.read_text(encoding="utf-8"))
    nodes=list(walk(data))
    ids=[node["__guid"] for node in nodes if "__guid" in node]
    assert len(ids)==len(set(ids)),"Duplicate object/component ID"
    known=set(ids)
    for node in nodes:
        if node.get("_type")=="component":
            assert node["component_id"] in known,node
            assert node["go"] in known,node
    paths=set()
    for node in nodes:
        for key in ("Model","Image","CurrentMinimapPath","Resource","IrradianceTexture","DistanceTexture","RelocationTexture","Texture","BakedTexture"):
            if isinstance(node.get(key),str) and "/" in node[key]: paths.add(node[key])
            elif isinstance(node.get(key),dict) and "Path" in node[key]: paths.add(node[key]["Path"])
        if "__Prefab" in node: paths.add(node["__Prefab"]["Path"])
    def resource(path):
        assert not Path(path).is_absolute() and ".." not in Path(path).parts,"Unexpected resource path: "+path
        for base in (STAGE,ROOT/"Assets"):
            if (base/path).is_file(): return base/path
            if path.endswith(".vtex") and (base/(path+"_c")).is_file(): return base/(path+"_c")
        raise AssertionError("Missing resource: "+path)
    for path in paths: resource(path)
    # Follow the generated models into their material/mesh files and texture maps.
    # This catches a staged model silently depending on a material never packaged.
    model_dependencies=set()
    for path in sorted(paths):
        if not path.endswith(".vmdl"): continue
        model_dependencies.update(re.findall(r'\b(?:to|filename)\s*=\s*"([^\"]+)"',resource(path).read_text()))
    material_dependencies=set(); engine_textures=set()
    for path in sorted(model_dependencies):
        file=resource(path)
        if not path.endswith(".vmat"): continue
        for texture in re.findall(r'\bTexture\w+\s+"([^\"]+)"',file.read_text()):
            if texture.startswith("["): continue
            if texture.startswith("materials/default/"):
                engine_textures.add(texture); continue
            resource(texture); material_dependencies.add(texture)
    groups={go.get("Name"):go for go in data["GameObjects"]}
    counts=Counter(node["__type"] for node in nodes if "__type" in node)
    assert len(groups["Team Spawns"]["Children"])==12
    assert len(groups["Deathmatch Spawns"]["Children"])==20
    assert len(groups["Bomb Sites"]["Children"])==2
    team_filter=groups["Team Spawns"]["Components"][0]
    assert team_filter["Inverse"] and set(team_filter["GameModes"])=={"Deathmatch","Gun Game","Retakes"}
    retakes=groups["Retakes Spawns"]
    assert retakes["Components"][0]["GameModes"]==["Retakes"]
    for site in ("bombsite_a","bombsite_b"):
        roles=Counter()
        for go in retakes["Children"]:
            tags=go["Tags"].split(",")
            if site not in tags: continue
            role=next(role for role in ("planter","defender","attacker") if role in tags)
            expected="CounterTerrorist" if role=="attacker" else "Terrorist"
            assert go["Components"][0]["Team"]==expected
            roles[role]+=1
        assert roles=={"planter":2,"defender":3,"attacker":6},roles
    assert counts["Facepunch.ObjectiveSpot"]==6
    assert counts["Facepunch.CashPoint"]==3 and counts["Facepunch.ExtractionPoint"]==3
    nav=data["SceneProperties"]["NavMesh"]
    assert nav["Enabled"] and nav["AgentHeight"]==64 and nav["AgentRadius"]==16
    menu=(ROOT/"Code/GameLoop/GameUtils.cs").read_text(encoding="utf-8-sig")
    assert menu.count('"scenes/maps/collider/collider.scene"')==2
    assert '"Collider"' in menu
    report={"success":True,"objects_and_components":len(ids),"referenced_resources":sorted(paths),
            "model_dependencies":sorted(model_dependencies),"texture_dependencies":sorted(material_dependencies),
            "engine_default_textures":sorted(engine_textures),
            "component_counts":dict(counts),"checks":["Unique stable IDs","Internal component references",
            "Resource files present","Model material/mesh and texture dependencies","Per-mode spawn isolation","Retakes role/team tags",
            "Objective and Cash Grab wiring","Navmesh agent settings","Map catalog entries"],
            "scope":"Offline scene schema, resource dependencies and gameplay wiring; native reports are separate",
            "scene_sha256":hashlib.sha256(scene_file.read_bytes()).hexdigest()}
    out=Path(report_file) if report_file else ROOT/"output/collider/scene-validation.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene",type=Path,help="Validate a saved scene without replacing the staged scene")
    parser.add_argument("--report",type=Path,help="Write the validation report at a separate path")
    args=parser.parse_args()
    report=validate(args.scene,args.report)
    print(json.dumps({k:report[k] for k in ("success","objects_and_components","checks")},indent=2))

if __name__=="__main__": main()
