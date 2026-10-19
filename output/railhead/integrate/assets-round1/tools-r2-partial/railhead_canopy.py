"""Individual two-sided, networked breakable panes for Railhead's cab canopies."""
import json
from pathlib import Path
import map_kit as K
import railhead_station as S

MODEL = "models/maps/railhead/railhead_canopy_pane.vmdl"
WIDTH = 1432.0 - (S.SHED_E + 10.0)
LENGTH = 60.0


def pane_model():
    m = K.Model()
    # Local normal +X, pane spans local Y/Z. Pitch -90 turns it into a roof.
    m.polygon("rw_canopy_glass", [(-WIDTH/2,0,-30), (WIDTH/2,0,-30),
                                (WIDTH/2,0,30), (-WIDTH/2,0,30)], normal=(0,1,0))
    m.material_overrides["rw_canopy_glass"] = "materials/railhead/rw_canopy_glass.vmat"
    m.tile_overrides["rw_canopy_glass"] = 64.0
    return m


def scene_group():
    ids = K.SceneIds("a580a704-e5f3-4920-9b64-a74222249e19")
    children = []
    for side in (-1, 1):
        for index in range(int((S.SHED_N1-S.SHED_N0)/LENGTH)):
            key = f"canopy/{side}/{index}"
            n = S.SHED_N0 + LENGTH*(index+0.5)
            components = [
                K.component(ids,"Sandbox.ModelRenderer",key+"/renderer",Model=MODEL,
                            RenderType="Off",Tint="1,1,1,1"),
                K.component(ids,"Sandbox.BoxCollider",key+"/collider",
                            Center="0,0,0",Scale=K.vec((1.0,WIDTH,LENGTH)),
                            IsTrigger=False,Static=True,Surface="surfaces/glass.surface"),
                K.component(ids,"Facepunch.BreakableGlass",key+"/glass",
                            IntactModel=MODEL,BrokenModels=[],PaneSize=K.vec((WIDTH,LENGTH)),
                            ShardDensity=4.0,BreakSound="sounds/buildings/glass_break.sound",
                            ShardEffect={"_type":"gameobject","prefab":"prefabs/buildings/glass_shatter.prefab"})
            ]
            children.append(K.game_object(ids,f"Canopy {'East' if side>0 else 'West'} Pane {index+1}",
                key,K.to_world((side*(S.SHED_E+10+WIDTH/2),n,218.5)),
                rotation="0,-0.70710678,0,0.70710678",components=components,tags="glass,navskip"))
    return K.game_object(ids,"Breakable Canopy Glass","canopy",children=children)


def write():
    import railhead_map as M
    out = K.ASSETS / "models/maps/railhead"
    K.write_model(out,"models/maps/railhead","railhead_canopy_pane",pane_model())
    glass = S.build()["railhead_glass"]
    M.configure(glass)
    K.write_model(out,"models/maps/railhead","railhead_glass",glass)
    scene = json.loads(M.SCENE_FILE.read_text(encoding="utf-8"))
    station = next(o for o in scene["GameObjects"] if o["Name"]=="Station")
    station["Children"] = [o for o in station["Children"] if o["Name"]!="Breakable Canopy Glass"]
    group = scene_group()
    station["Children"].append(group)
    M.SCENE_FILE.write_text(json.dumps(scene,indent=2)+"\n",encoding="utf-8")
    assert len(group["Children"]) == 88
    print("88 breakable panes installed; aggregate canopy render and collision removed.")


if __name__ == "__main__":
    write()
