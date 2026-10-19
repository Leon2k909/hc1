"""Build staged PBR resources from the retained generated stone source.

Only output/cerroblanco/stage is written. The editor imports and validates assets.
Stone pixels are material inputs; derived relief/roughness are artistic estimates,
not measurements. Slab randomisation and joints are evaluated by the game shader.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform

# SciPy's optional CPU feature discovery can hang in Windows WMI on this host.
platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64")
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parent.parent
RESOURCE = "materials/cerroblanco/quality-v1"
SOURCE = ROOT / "Sources/CerroBlanco/generated/travertine-source-v1.png"


def save(path, values):
    Image.fromarray(np.clip(np.rint(values), 0, 255).astype(np.uint8)).save(path, optimize=True)


def normal(height, density, strength=1):
    gx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))*density*.5*strength
    gy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))*density*.5*strength
    xyz = np.stack([-gx, gy, np.ones_like(gx)], -1)
    xyz /= np.linalg.norm(xyz, axis=-1, keepdims=True)
    return (xyz*.5+.5)*255


def material(textures, *, shader="complex", extra="", metal=0):
    lines = ["// Tools/cerroblanco_quality_materials.py", '"Layer0"', "{", f'    shader "shaders/{shader}.shader"']
    if shader == "complex":
        lines += ['    F_SPECULAR "1"']
    lines += [f'    g_flMetalness "{metal}"', '    g_flRoughnessScaleFactor "1"', '    g_flModelTintAmount "1"', '    g_vColorTint "[1 1 1 1]"']
    lines += [f'    {key} "{value}"' for key, value in textures.items()]
    lines += [extra, "}"]
    return "\n".join(lines)+"\n"


def build_stone(out):
    size = 2048
    source = np.asarray(Image.open(SOURCE).convert("RGB").resize((size,size), Image.Resampling.LANCZOS), dtype=np.float32)
    # Use a calibrated albedo centre. All high-frequency mineral structure comes
    # from the retained synthetic source, with extreme pore blacks compressed.
    mean = source.mean((0,1),dtype=np.float64)
    source = np.clip((source-mean)*.72+np.array([190,179,159],np.float32),60,238)
    luma = source @ np.array([.2126,.7152,.0722], np.float32)
    local = gaussian_filter(luma, 6, mode="wrap")
    cavity = np.clip((local-luma-3)/36,0,1)
    relief = gaussian_filter(cavity, .65, mode="wrap")
    height_inches = -.055*relief
    rough = np.clip(.64+cavity*.14+(gaussian_filter(luma,28)-luma.mean())*.002,.48,.86)
    save(out/"stone_color.png",source)
    save(out/"stone_normal.png",normal(height_inches,size/78.74))
    save(out/"stone_rough.png",rough*255)
    save(out/"stone_ao.png",(1-.22*relief)*255)
    save(out/"stone_height.png",(1-.52*relief)*255)
    maps = {"TextureColor":f"{RESOURCE}/stone_color.png","TextureNormal":f"{RESOURCE}/stone_normal.png","TextureRoughness":f"{RESOURCE}/stone_rough.png","TextureAmbientOcclusion":f"{RESOURCE}/stone_ao.png","TextureHeight":f"{RESOURCE}/stone_height.png"}
    # The paving is warmer and a shade darker than the walls' stone, with more difference from slab to slab and one slab in
    # twelve from a denser bed: at 1 1 1 and 3% it read as near-white bathroom tile, lighter than the stone beside it.
    presets = {
        "paving": (8,1,.16,.12,.13,.46,.63,"0.93 0.91 0.86",.075,.08),
        "travertine": (4,1,.20,.14,.18,.82,.74,"1.09 1.085 1.07",.033,0),
        "honed": (4,0,.16,.12,.055,.38,.57,"1.045 1.035 1.02",.033,0),
    }
    for name,(tiles,joints,joint,bevel,depth,norm,roughness,tint,variation,odd) in presets.items():
        values = {"g_flTilesPerUv":tiles,"g_flHasJoints":joints,"g_flSlabSize":30,"g_flStoneScale":.381,"g_flJointWidth":joint,"g_flBevelWidth":bevel,"g_flReliefDepth":depth,"g_flNormalStrength":norm,"g_flStoneRoughness":roughness,"g_vStoneTint":f"[{tint}]","g_flSlabVariation":variation,"g_flOddSlabs":odd}
        text = material(maps,shader="cerroblanco_stone",extra="\n".join(f'    {k} "{v}"' for k,v in values.items()))
        (out/f"cb_{name}.vmat").write_text(text,encoding="utf-8")
    return {"source_size":Image.open(SOURCE).size,"runtime_size":[size,size],"mean_albedo_srgb":source.mean((0,1),dtype=np.float64).tolist(),"stone_source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),"slab_inches":30,"slabs":"Independent hash, offset and quarter-turn; no repeating slab atlas"}


def small_surfaces(out):
    n = 1024
    rng = np.random.default_rng(1515)
    fine = rng.standard_normal((n,n)).astype(np.float32)
    broad = gaussian_filter(fine,16,mode="wrap")
    broad /= max(float(broad.std()),.00001)
    yy,xx=np.mgrid[0:n,0:n].astype(np.float32)
    u,v=(xx/n*120)%30,(yy/n*120)%30
    edge=np.minimum.reduce([u,30-u,v,30-v])
    inside=np.clip((edge-.09)/.075,0,1)
    inside=inside*inside*(3-2*inside)
    # The enamelled panels' own maps are the enamel alone: a faint mottle and its orange peel. The open joints, each
    # panel's tilt and pillowing and the rain streaks are cerroblanco_panel.shader's, panel by panel.
    mottle=gaussian_filter(fine,48,mode="wrap")
    mottle/=max(float(mottle.std()),.00001)
    panel_color=np.array([206,203,196],np.float32)+mottle[...,None]*.9+broad[...,None]*.6+fine[...,None]*.25
    panel_height=gaussian_filter(fine,1.1,mode="wrap")*.0035
    surfaces={
        "panel":(panel_color,panel_height,np.clip(.5+fine*.01+mottle*.02,0,1),0),
        "plaster":(np.array([215,212,204])+broad[...,None]*.65+fine[...,None]*.24,gaussian_filter(fine,.7)*.003,np.clip(.85+fine*.012,0,1),0),
        "frame":(np.array([50,53,54])+fine[...,None]*.5,gaussian_filter(fine,.7)*.0006,np.clip(.37+broad*.015+fine*.006,0,1),.6),
        "steel":(np.array([152,156,157])+gaussian_filter(fine,(.35,12),mode="wrap")[...,None]*3,gaussian_filter(fine,(.35,12),mode="wrap")*.0008,np.clip(.3+broad*.018,0,1),.92),
        "red":(np.array([168,29,23])+broad[...,None]*1.2+fine[...,None]*.2,gaussian_filter(fine,.7)*.0015,np.clip(.34+broad*.025,0,1),.05),
        "white":(np.array([212,209,201])+broad[...,None]*.3+fine[...,None]*.15,gaussian_filter(fine,.7)*.0007,np.clip(.38+broad*.01,0,1),.12),
    }
    fibers=gaussian_filter(fine,(28,.7),mode="wrap")
    fibers/=max(float(fibers.std()),.00001)
    growth=np.sin(xx*.15+gaussian_filter(fine,(64,12),mode="wrap")*35)
    teak=np.array([125,87,53])*(1+fibers[...,None]*.065+growth[...,None]*.035+broad[...,None]*.025)
    surfaces["teak"]=(teak,fibers*.003,np.clip(.56+fibers*.025+broad*.02,.4,.8),0)
    for name,(color,height,rough,metal) in surfaces.items():
        save(out/f"{name}_color.png",color)
        save(out/f"{name}_normal.png",normal(height,n/120 if name=="panel" else n/64))
        save(out/f"{name}_rough.png",rough*255)
        maps={"TextureColor":f"{RESOURCE}/{name}_color.png","TextureNormal":f"{RESOURCE}/{name}_normal.png","TextureRoughness":f"{RESOURCE}/{name}_rough.png","TextureAmbientOcclusion":"materials/default/default_ao.tga"}
        if name=="panel":
            values={"g_flTilesPerUv":4,"g_flSlabSize":30,"g_flTextureScale":.25,"g_flJointWidth":.16,"g_flBevelWidth":.12,"g_flTilt":.005,"g_flPillow":.025,"g_flVariation":.012,"g_flStreaks":.035,"g_flPanelRoughness":.48,"g_flNormalStrength":.65,"g_vPanelTint":"[1 1 1]","g_vJointColor":"[.22 .215 .205]"}
            text=material(maps,shader="cerroblanco_panel",extra="\n".join(f'    {k} "{v}"' for k,v in values.items()))
            (out/f"cb_{name}.vmat").write_text(text,encoding="utf-8")
            continue
        (out/f"cb_{name}.vmat").write_text(material(maps,metal=metal),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ROOT/"output/cerroblanco/stage")
    args=parser.parse_args()
    out=args.out/RESOURCE
    out.mkdir(parents=True,exist_ok=True)
    report=build_stone(out)
    small_surfaces(out)
    shader=args.out/"shaders/cerroblanco_stone.shader"
    shader.parent.mkdir(parents=True,exist_ok=True)
    shader.write_bytes((ROOT/"Sources/CerroBlanco/shaders/cerroblanco_stone.shader").read_bytes())
    panel_shader=args.out/"shaders/cerroblanco_panel.shader"
    panel_shader.write_bytes((ROOT/"Sources/CerroBlanco/shaders/cerroblanco_panel.shader").read_bytes())
    report["files"]=[{"path":p.relative_to(args.out).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in sorted([*out.glob("*"),shader,panel_shader]) if p.is_file()]
    report["overrides"]={f"materials/cerroblanco/cb_{name}.vmat":f"{RESOURCE}/cb_{name}.vmat" for name in ["paving","travertine","honed","panel","plaster","frame","steel","red","white","teak"]}
    (ROOT/"output/cerroblanco/material-manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"files":len(report["files"]),"albedo":report["mean_albedo_srgb"],"overrides":len(report["overrides"])}))


if __name__=="__main__":
    main()
