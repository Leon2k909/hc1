"""Build the private Gunsmith practice scene and its local range assets.

rtk proxy python Tools/gunsmith_range.py

All coordinates in this authoring file are game-world inches. Distances are
measured from the orange firing line, with targets at 10, 25, 50 and 100 metres.
"""
import json
import math
import uuid
from pathlib import Path

import numpy as np
import map_kit as K
import gunsmith_range_bench as B

RESOURCE = "models/gunsmith_range"
OUT = K.ASSETS / RESOURCE
MATERIALS = K.ASSETS / "materials/gunsmith_range"
IDS = K.SceneIds("ba1cd4ef-93b8-4d4a-8d6c-88629614bcee")
METRE = 39.37007874
PAINTS = {
    "range_white": ((.83,.85,.83), .72, 0),
    "range_orange": ((.95,.29,.055), .61, 0),
    "range_black": ((.045,.06,.072), .64, .2),
    "range_blue": ((.13,.19,.24), .59, .15),
}


def p(world):
    x,y,z = world
    return np.array((-y,x,z),dtype=float)


def box(model,lo,hi,paint,surface=None):
    a,b = p(lo),p(hi)
    model.box(np.minimum(a,b),np.maximum(a,b),paint,surface)


def beam(model,a,b,size,paint="rw_steel_dark"):
    model.beam(p(a),p(b),size,paint)


def configure(model):
    for paint in model.polygons:
        model.material_overrides[paint] = f"materials/{'gunsmith_range' if paint in PAINTS else 'railhead'}/{paint}.vmat"
        model.tile_overrides[paint] = 128 if paint in ("rw_concrete","rw_concrete_dark","rw_asphalt") else 64
    B.configure(model)


def metadata(path):
    sidecar=path.with_name(path.name+".meta")
    if not sidecar.exists():
        sidecar.write_text(json.dumps({"guid":str(uuid.uuid5(uuid.NAMESPACE_URL,"hc1/gunsmith_range/"+path.relative_to(K.ASSETS).as_posix()))},indent=2)+"\n")


def materials():
    B.materials()
    MATERIALS.mkdir(parents=True,exist_ok=True)
    for name,(rgb,rough,metal) in PAINTS.items():
        path=MATERIALS/f"{name}.vmat"
        K.write_text(path,f'''// Tools/gunsmith_range.py
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "{metal}"
    TextureColor "materials/default/default_color.tga"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "[{rough} {rough} {rough} 0]"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[{' '.join(str(v) for v in rgb)} 1]"
    g_flModelTintAmount "1"
}}
''')
        metadata(path)


GLYPHS={
    "0":["111","101","101","101","111"],
    "1":["010","110","010","010","111"],
    "2":["111","001","111","100","111"],
    "5":["111","100","111","001","111"],
    "M":["10001","11011","10101","10001","10001"],
}


def sign(model,text,x,y,z,scale=2.1):
    width=sum(len(GLYPHS[c][0])+1 for c in text)*scale
    box(model,(x,y-width/2-8,z-8),(x+2,y+width/2+8,z+5*scale+8),"range_blue")
    yy=y+width/2
    for c in text:
        grid=GLYPHS[c]
        for row,values in enumerate(grid):
            for col,value in enumerate(values):
                if value=="1":
                    a=yy-col*scale
                    zz=z+(4-row)*scale
                    box(model,(x-.15,a-scale*.82,zz),(x-.04,a,zz+scale*.82),"range_white")
        yy-=(len(grid[0])+1)*scale


def level():
    m=K.Model()
    box(m,(-420,-700,-24),(4220,700,0),"rw_asphalt","concrete")
    box(m,(-440,-720,0),(-420,720,184),"rw_concrete","concrete")
    for y in (-720,700):
        box(m,(-440,y,0),(4220,y+20,224),"rw_concrete","concrete")
        box(m,(-440,y-2,210),(4220,y+22,226),"range_blue")
        for x in range(200,4100,250):
            box(m,(x,y-1,0),(x+12,y+21,212),"rw_concrete_dark")
    box(m,(4120,-720,0),(4230,720,316),"rw_concrete_dark","concrete")
    # Angled steel bullet trap, backed by a thick concrete berm.
    for y in range(-660,661,132):
        beam(m,(4075,y,5),(4110,y,184),(116,7),"rw_steel_dark")
    box(m,(4060,-695,0),(4130,695,8),"rw_steel_dark")
    # A covered firing platform with clear headroom and four sturdy shooting benches.
    box(m,(-360,-680,172),(42,680,181),"range_blue","metal")
    for x in (-342,24):
        for y in (-663,663):
            beam(m,(x,y,0),(x,y,173),(7,7))
    for y in (-650,-330,0,330,650):
        beam(m,(-350,y,170),(32,y,170),(5,9))
    box(m,(0,-680,.01),(2,680,.14),"range_orange")
    for y in (-600,-300,0,300,600):
        box(m,(3,y,.02),(4050,y+1.4,.10),"range_white")
    for bench,(distance,y) in enumerate(((10,-450),(25,-150),(50,150),(100,450))):
        x=distance*METRE
        B.tabletop(m,y,bench)
        for xx in (-29,-9):
            for yy in (y-76,y+76):
                box(m,(xx-2,yy-2,0),(xx+2,yy+2,30),"rw_steel_dark","metal")
        box(m,(-345,y-145,.02),(-12,y-143,.12),"range_white")
        # The target's frame, stand and rail remain visible when the plate drops.
        box(m,(x-16,y-33,0),(x+16,y+33,4),"rw_steel_dark","metal")
        for yy in (y-93,y+93):
            beam(m,(x+5,yy,3),(x+5,yy,102),(2.5,2.5))
        beam(m,(x+5,y-93,101),(x+5,y+93,101),(2.5,2.5))
        sign(m,f"{distance}M",x-3,y,106)
        box(m,(x-90,y-110,1),(x+90,y+110,2.1),"rw_steel_dark")
    # Training barricades in a separate side bay for movement and recoil practice.
    for x,height in ((-260,35),(-245,65)):
        box(m,(x,-670,0),(x+8,-575,height),"rw_wood","wood")
    configure(m)
    return m


def plate(model,outline,zoffset=0,paint="range_white",depth=.8):
    # Convex plate in the Y/Z plane, facing the firing line (-X).
    vertices=[p((x,y,z+zoffset)) for x in (-depth/2,depth/2) for y,z in outline]
    count=len(outline)
    faces=[list(range(count-1,-1,-1)),list(range(count,count*2))]
    faces += [[i,(i+1)%count,(i+1)%count+count,i+count] for i in range(count)]
    centre=np.mean(vertices,axis=0)
    for face in faces:
        points=[vertices[i] for i in face]
        normal=np.cross(points[1]-points[0],points[2]-points[0])
        if np.dot(normal,np.mean(points,axis=0)-centre)<0: points.reverse()
        model.polygon(paint,points)
    model.hull(vertices,"metal")


def target():
    m=K.Model()
    box(m,(-.45,-9,0),(.45,9,31),"range_white","metal")
    plate(m,[(-10,28),(10,28),(16,34),(16,51),(9,57),(-9,57),(-16,51),(-16,34)])
    box(m,(-.45,-4,56),(.45,4,63),"range_white","metal")
    head=[(7*math.cos(t),66+7*math.sin(t)) for t in np.linspace(0,math.tau,20,endpoint=False)]
    plate(m,head)
    # Black aiming marks are geometric paint patches; no external image dependency.
    for radius,z,paint in ((9,44,"range_black"),(3,44,"range_orange"),(2.6,66,"range_black")):
        face_x=-.48 if paint=="range_orange" else -.46
        pts=[p((face_x,radius*math.cos(t),z+radius*math.sin(t))) for t in np.linspace(0,math.tau,28,endpoint=False)]
        m.polygon(paint,pts[::-1],p((-1,0,0)))
    configure(m)
    return m


def obj(name,key,position=(0,0,0),components=(),**kwargs):
    return K.game_object(IDS,name,key,position=position,components=components,**kwargs)


def component(kind,key,**props):
    return K.component(IDS,kind,key,**props)


def scene():
    objects=[
        obj("Scene Information","info",components=[component("Sandbox.SceneInformation","info/component",Title="Firing Range",Description="Private Gunsmith practice range: 10, 25, 50 and 100 metre steel targets.",SceneTags="firing_range")]),
        obj("Practice Session","session",components=[component("Facepunch.Gunsmith.FiringRangeSystem","session/system"),component("Facepunch.GameNetworkManager","session/network",IsMultiplayer=False,ClientPrefab={"_type":"gameobject","prefab":"prefabs/player/client.prefab"})]),
        obj("Range","geometry",components=[component("Sandbox.ModelRenderer","geometry/renderer",Model=f"{RESOURCE}/gunsmith_range.vmdl",BodyGroups=18446744073709551615,Tint="1,1,1,1"),component("Sandbox.ModelCollider","geometry/collider",Model=f"{RESOURCE}/gunsmith_range.vmdl",Static=True)]),
        obj("Firing Line Spawn","spawn",(-100,-450,2),components=[component("Facepunch.TeamSpawnPoint","spawn/point",Team="CounterTerrorist")],tags="spawnpoint"),
        obj("Sun","sun",rotation="0.258819,0.369644,0.099046,0.886415",components=[component("Sandbox.DirectionalLight","sun/light",LightColor="1.3,1.21,1.08,1",SkyColor=".55,.64,.76,1",Shadows=True,ContactShadows=True,ShadowCascadeCount=4)]),
        obj("Sky","sky",components=[component("Sandbox.SkyBox2D","sky/material",SkyMaterial="materials/lowtide/sky/lowtide_sky.vmat",SkyIndirectLighting=True,Tint="1,1,1,1")]),
        obj("Range HUD","hud",components=[component("Sandbox.ScreenPanel","hud/screen",ZIndex=100,ScaleStrategy="ConsistentHeight",AutoScreenScale=True),component("Facepunch.UI.FiringRangeHud","hud/panel")]),
        obj("Overview Camera","camera",(-238,-480,80),components=[component("Sandbox.CameraComponent","camera/view",IsMainCamera=True,Priority=-100,FieldOfView=85,ZNear=1,ZFar=14000,EnablePostProcessing=True),component("Sandbox.Tonemapping","camera/tone",Mode="ACES",AutoExposureEnabled=False,ExposureCompensation=0)]),
        obj("Firing Platform Light","light",(-145,0,142),components=[component("Sandbox.PointLight","light/point",LightColor="1.15,1.25,1.4,1",Radius=900,Shadows=False)]),
    ]
    for distance,y in ((10,-450),(25,-150),(50,150),(100,450)):
        key=f"target/{distance}"
        objects.append(obj(f"{distance} m Target",key,(distance*METRE,y,4),components=[
            component("Sandbox.ModelRenderer",key+"/renderer",Model=f"{RESOURCE}/range_target.vmdl",Tint="1,1,1,1"),
            component("Sandbox.ModelCollider",key+"/collider",Model=f"{RESOURCE}/range_target.vmdl",Static=False),
            component("Facepunch.Gunsmith.FiringRangeTarget",key+"/target",DistanceMetres=distance,MaxHealth=100,Travel=70),
        ],tags="range_target"))
    return {"__guid":IDS("scene"),"GameObjects":objects,"SceneProperties":{
        "FixedUpdateFrequency":60,"MaxFixedUpdates":5,"NetworkFrequency":60,
        "NetworkInterpolation":True,"ThreadedAnimation":True,"TimeScale":1,"UseFixedUpdate":True,
        "PhysicsMode":"Physics3D","WantsSystemScene":True,"Metadata":{"Title":"Firing Range"},
        "NavMesh":{"Enabled":False,"EditorAutoUpdate":False},
    }}


def main():
    materials()
    for name,model in (("gunsmith_range",level()),("range_target",target())):
        count=K.write_model(OUT,RESOURCE,name,model)
        for suffix in (".vmdl",".obj"):
            metadata(OUT/f"{name}{suffix}")
        print(f"{name}: {count} triangles, {len(model.boxes)} boxes, {len(model.hulls)} hulls")
    path=K.ASSETS/"scenes/gunsmith_range.scene"
    K.write_text(path,json.dumps(scene(),indent=2)+"\n")
    metadata(path)
    print("Gunsmith firing range: four distance lanes, independent damage targets, solo session")


if __name__=="__main__":
    main()
