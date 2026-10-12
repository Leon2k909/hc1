"""Create the Nano Drone's deterministic equipment, aircraft and shared-tablet prefabs.

Run after build_recon_nano.py. Does not modify or regenerate the octocopter.
The rotor frame is a separate parent: ReconRotor turns its child about local Z,
so the tail rotor retains its vertical plane at every speed.
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "Assets"
BASE = "weapons/recon_nano"
MODELS = "models/recon_nano"
DEST = ASSETS / BASE
INFO = json.loads((ASSETS / MODELS / "asset-info.json").read_text(encoding="utf-8"))
METRE = 39.37


def guid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "razed/recon-nano/" + name))


def vec(values):
    return ",".join(f"{float(v):.6f}".rstrip("0").rstrip(".") or "0" for v in values)


def component(name, kind, **props):
    return {"__type": kind, "__guid": guid(name), "__enabled": True, **props}


def obj(name, components=None, children=None, **props):
    return {"__guid": guid(name), "Name": name, "Enabled": True, "NetworkMode": 0,
            "Components": components or [], "Children": children or [], **props}


def ref(name, kind, go):
    return {"_type": "component", "component_id": guid(name), "go": guid(go), "component_type": kind}


def renderer(name, model, shadows=True):
    return component(name, "Sandbox.ModelRenderer", Model=f"{MODELS}/{model}.vmdl", Tint="1,1,1,1",
                     RenderType="On" if shadows else "Off", UseAnimGraph=False,
                     RenderOptions={"GameLayer": True, "OverlayLayer": False})


def box(name, centre, size):
    return component(name, "Sandbox.BoxCollider", Center=vec(centre), Scale=vec(size), IsTrigger=False,
                     Static=False, Surface="surfaces/metal.sheet.surface")


def write_prefab(name, root):
    write_json(DEST / f"{name}.prefab", {"RootObject": root, "ResourceVersion": 2, "__references": [], "__version": 2})


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def rotor(data):
    name = data["name"].title() + " Rotor"
    children = [obj(name + " Hub", [renderer(name + "-hub", f"recon_nano_hub_{data['name']}")]),
                obj(name + " Blades", [renderer(name + "-blades", f"recon_nano_prop_{data['name']}")]),
                obj(name + " Disc", [renderer(name + "-disc", f"recon_nano_disc_{data['name']}", False)])]
    spinning = obj(name, [component(name + "-rotor", "Facepunch.ReconRotor", Spin=data["spin"],
                                    RpmScale=data["rpm_scale"], ShaderScale=data["shader_scale"], Yoke=False,
                                    Hub=ref(name + "-hub", "ModelRenderer", name + " Hub"),
                                    Blades=ref(name + "-blades", "ModelRenderer", name + " Blades"),
                                    Disc=ref(name + "-disc", "ModelRenderer", name + " Disc"))], children)
    # The disc object stays enabled; only its renderer starts hidden until ReconRotor selects it.
    children[-1]["Components"][0]["__enabled"] = False
    return obj(name + " Mount", children=[spinning], Position=vec(data["position"]), Rotation=vec(data["rotation"]))


def cloned_tablet(kind):
    name = f"{kind}_recon_octocopter"
    root = json.loads((ASSETS / f"weapons/recon_octocopter/{name}.prefab").read_text(encoding="utf-8-sig"))["RootObject"]
    ids = set()

    def visit(node):
        if isinstance(node, dict):
            if "__guid" in node:
                ids.add(node["__guid"])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(root)
    text = json.dumps(root).replace("Recon Octocopter", "Nano Drone")
    for old in sorted(ids):
        text = text.replace(old, guid(kind + "-" + old))
    return json.loads(text)


def main():
    flight = component("flight", "Facepunch.ReconOctocopter",
                       DisplayName="Nano Drone", IconPath="ui/weapons/recon_nano.svg",
                       StationResourcePath=f"{BASE}/recon_nano.equip",
                       HandLaunched=True, LinkDelay=.65, SpoolSeconds=.40, RotateCollisionHull=True,
                       Gimbal={"_type": "gameobject", "go": guid("Gimbal")}, LensOffset=vec(INFO["gimbal_lens"]),
                       RotorSound="sounds/drones/nano_rotors.sound", SparksPrefab="prefabs/impact_fx/impact_sparks.prefab",
                       Hull={"Mins": vec(INFO["hull_min"]), "Maxs": vec(INFO["hull_max"])},
                       CruiseSpeed=6 * METRE, SportSpeed=10 * METRE, Acceleration=4 * METRE,
                       ClimbRate=2 * METRE, DescentRate=1.5 * METRE, VerticalAcceleration=3 * METRE,
                       Ceiling=60 * METRE, TakeoffHeight=1.4 * METRE, BatterySeconds=120,
                       DragPerInch=.00055, MaxTilt=28, HoverRpm=4800, MaxIntegrity=10,
                       CrashSpeed=120, ImpactDamageThreshold=60,
                       WideFieldOfView=62, CameraZoomSteps=[1, 2, 4], CameraNearPlane=.15,
                       MaxGimbalPitch=80, MinGimbalPitch=-25, SpotRange=3000)
    # Bullet hitboxes follow the geometry rather than filling its whole rotor/boom envelope.
    colliders = [box("hitbox-pod", [.12, 0, .10], [4.2, 1.4, 1.6]),
                 box("hitbox-tail", [-4.7, 0, .66], [5.8, .28, .8]),
                 box("hitbox-fin", [-6.89, 0, 1.3], [.95, .12, 1.73]),
                 box("hitbox-rotor", INFO["rotors"][0]["position"], [7.5, 7.5, .18])]
    airborne = obj("Nano Drone", [renderer("body", "recon_nano"), flight, *colliders],
                   [obj("Gimbal", [renderer("camera", "recon_nano_gimbal"),
                                    component("hitbox-camera", "Sandbox.SphereCollider", Radius=.355,
                                              IsTrigger=False, Static=False, Surface="surfaces/metal.sheet.surface")],
                        Position=vec(INFO["gimbal_pivot"])),
                    *[rotor(r) for r in INFO["rotors"]]], NetworkMode=2, NetworkInterpolation=True, Tags="recon_nano")
    write_prefab("recon_nano_airborne", airborne)
    write_prefab("vm_recon_nano", cloned_tablet("vm"))
    write_prefab("wm_recon_nano", cloned_tablet("wm"))
    station = obj("Nano Drone Equipment", [
        component("equipment", "Facepunch.Equipment", Resource=f"{BASE}/recon_nano.equip", HoldType="HoldItem",
                  Handedness="Right", UseCrosshair=False, DeploySound="sounds/guns/handling/draw_grenade.sound"),
        component("tags", "Facepunch.TagBinder")],
        [obj("Ground Station Link", [component("link", "Facepunch.ReconTabletLink", InputActions=["Attack1"],
                                              HandLaunch=True, LaunchDistance=32,
                                              Prefab={"_type": "gameobject", "prefab": f"{BASE}/recon_nano_airborne.prefab"})])])
    write_prefab("weapon_recon_nano", station)
    write_json(DEST / "recon_nano.equip", {
        "Name": "Nano Drone", "Description": "Hand-launch a quiet scout and fly it from the recon tablet. Marks visible enemies for your team.",
        "Slot": "Tactical", "Category": "None", "Team": "Unassigned", "CanOtherTeamPickUp": False,
        "DropOnDisconnect": False, "Icon": "ui/weapons/recon_nano.svg", "IsPurchasable": True,
        "Price": 500, "KillReward": 0, "WorldModel": "models/recon_octocopter/recon_tablet.vmdl",
        "MainPrefab": {"_type": "gameobject", "prefab": f"{BASE}/weapon_recon_nano.prefab"},
        "ViewModelPrefab": {"_type": "gameobject", "prefab": f"{BASE}/vm_recon_nano.prefab"},
        "WorldModelPrefab": {"_type": "gameobject", "prefab": f"{BASE}/wm_recon_nano.prefab"},
        "__version": 0, "__references": []})
    (ASSETS / "ui/weapons/recon_nano.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-180 -180 360 360">
<g fill="white" stroke="white" stroke-linecap="round">
<path d="M-10 12 Q-15-21 0-29 Q15-21 10 12 Q0 22-10 12" stroke="none"/>
<path d="M0 12V85" stroke-width="4"/><path d="M-11 76H11M-18 49H18" stroke-width="3"/>
<path d="M-58-10H58" stroke-width="5"/><circle cy="-10" r="5"/>
<path d="M-7 80L7 90" stroke-width="3"/>
</g></svg>
''', encoding="utf-8")
    # Stable IDs for first import, retained if the engine has already assigned one.
    files = [*DEST.glob("*.prefab"), *DEST.glob("*.equip"), ASSETS / "ui/weapons/recon_nano.svg",
             ASSETS / "sounds/drones/nano_rotors.sound"]
    files += [q for q in (ASSETS / MODELS).iterdir() if q.suffix in (".vmdl", ".vmat", ".obj", ".png")]
    for q in files:
        meta = q.with_name(q.name + ".meta")
        if q.exists() and not meta.exists():
            write_json(meta, {"guid": guid("asset-" + q.relative_to(ASSETS).as_posix().lower())})
    print("Built Nano Drone: airborne, equipment, two tablet prefabs, resource and icon.")


if __name__ == "__main__":
    main()
