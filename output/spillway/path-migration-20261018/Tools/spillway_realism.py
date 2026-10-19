"""Stage the reviewed water/landscape material revisions, without live asset writes."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"Sources/Spillway"
STAGE=ROOT/"output/spillway/stage"


def prepare_shaders():
    shaders=SOURCE/"shaders"
    # Keep preprocessor directives on their own lines for the engine shader compiler.
    for name in ("hc1_spillway_falls_v4.shader","hc1_spillway_mountain_v5.shader"):
        path=shaders/name
        text=path.read_text()
        for include in ("common/features.hlsl","common/shared.hlsl","common/vertexinput.hlsl","common/pixelinput.hlsl"):
            text=text.replace('{ #include "'+include+'" }','{\n    #include "'+include+'"\n}')
        path.write_text(text)
    river=(shaders/"hc1_spillway_river_v2.shader").read_text()
    start=river.index('        float2 swp =')
    end=river.index('        CombinerInput lightingInput',start)
    river=river[:start]+'''        // Foam is advected downstream with the current, and stretches around eddies.
        float2 p = position / float2(210,150);
        float2 warp=float2(SWNoise(p*.37),SWNoise(p*.37+19.2));
        float2 curled=p+(warp-.5)*3.4;
        float broad=SWNoise(curled)*.58+SWNoise(curled*2.17+5.3)*.27+SWNoise(curled*4.47+13.1)*.15;
        float ribbons=1-abs(broad*2-1);
        float islands=SWNoise(p*.23+7.8);
        float swFoam=smoothstep(.81,.95,ribbons)*smoothstep(.38,.66,islands);
        float broken=SWNoise(curled*6.3);
        swFoam*=lerp(.38,1,smoothstep(.3,.6,broken));
        water.Albedo=lerp(water.Albedo,float3(.36,.45,.47),swFoam*.72);
        water.Roughness=lerp(water.Roughness,.53,swFoam);
        water.Opacity=lerp(water.Opacity,1,swFoam);

'''+river[end:]
    river=river.replace('        float2 pixelDx = ddx( world.xy );', '''        float2 drift=position/float2(290,240);
        position+=float2(SWNoise(drift*.51),SWNoise(drift*.51+11.7))*55;
        float2 pixelDx = ddx( world.xy );''')
    (shaders/"hc1_spillway_river_v3.shader").write_text(river)
    concrete=(shaders/"hc1_spillway_concrete.shader").read_text()
    concrete=concrete.replace('(1-deposit*.24)','(1-deposit*.34)')
    concrete=concrete.replace('float wet=smoothstep(.50,.67,patch);','float wet=smoothstep(.43,.65,patch);')
    concrete=concrete.replace('m.Albedo*=lerp(.82,.55,wet);','m.Albedo*=lerp(.89,.60,wet);')
    concrete=concrete.replace('m.Roughness=lerp(.69,.32,wet);','m.Roughness=lerp(.68,.12,wet);\n            m.Normal=normalize(lerp(m.Normal,i.vNormalWs,wet*.78));')
    (shaders/"hc1_spillway_concrete_v2.shader").write_text(concrete)


def stage_materials():
    prepare_shaders()
    mats=STAGE/"materials/spillway"
    (mats/"sky/spillway_overcast.vmat").write_text('''"Layer0"
{
 shader "shaders/sky.shader"
 F_TEXTURE_FORMAT2 "6"
 g_flBrightnessExposureBias "0.0"
 g_flRenderOnlyExposureBias "0"
 SkyTexture "materials/spillway/sky/overcast.exr"
}
''')
    for name in ("sw_mountain","sw_hill"):
        old=(mats/(name+"_v3.vmat")).read_text()
        (mats/(name+"_v4.vmat")).write_text(old.replace("hc1_spillway_mountain_v4.shader","hc1_spillway_mountain_v5.shader"))
    for name,foam in (("sw_fall",0),("sw_foam",1),("sw_mist",2)):
        (mats/(name+"_v4.vmat")).write_text('"Layer0"\n{\n shader "shaders/hc1_spillway_falls_v4.shader"\n g_flFoam "'+str(foam)+'"\n}\n')
    (mats/"sw_river_v3.vmat").write_text('''"Layer0"
{
 shader "shaders/hc1_spillway_river_v3.shader"
 g_vWaterColor "[0.012 0.038 0.043]"
 g_vWaterFlow "[-105 0]"
 g_flRippleTile "145"
 g_flRippleStrength "1.20"
 g_flWaterRoughness "0.14"
 g_flAbsorptionDistance "38"
 g_flBankFade "1.1"
}
''')
    for name in ("sw_concrete","sw_dam","sw_yard","sw_trim"):
        old=(mats/(name+".vmat")).read_text()
        (mats/(name+"_v2.vmat")).write_text(old.replace("hc1_spillway_concrete.shader","hc1_spillway_concrete_v2.shader"))
    # Remap staged models so a partial art rebuild uses the same materials as a full rebuild.
    for model in (STAGE/"models/maps/spillway").glob("*.vmdl"):
        text=model.read_text()
        for name in ("sw_mountain","sw_hill","sw_fall","sw_foam","sw_mist"):
            text=text.replace(name+"_v3.vmat",name+"_v4.vmat")
        text=text.replace("sw_river_v2.vmat","sw_river_v3.vmat")
        for name in ("sw_concrete","sw_dam","sw_yard","sw_trim"):
            text=text.replace(name+".vmat",name+"_v2.vmat")
        model.write_text(text)


def backdrop_only():
    import spillway_map as S
    S.P.reset()
    mountains,forest,backdrop=S.backdrop()
    summary=json.loads((S.OUT/"build-summary.json").read_text())
    for name,model in (("mountains",mountains),("forest",forest),("backdrop",backdrop)):
        count=S.K.write_model(S.MODELS,"models/maps/spillway","spillway_"+name,S.configure(model))
        summary["triangles"][name]=count
    summary["total_triangles"]=sum(summary["triangles"].values())
    (S.OUT/"build-summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


def dam_only():
    import spillway_map as S
    S.P.reset()
    dam,falls=S.spillway_dam()
    for name,model in (("dam",dam),("falls",falls)):
        count=S.K.write_model(S.MODELS,"models/maps/spillway","spillway_"+name,S.configure(model))
        print(name,count)


if __name__=="__main__":
    import sys
    if "--backdrop" in sys.argv: backdrop_only()
    if "--dam" in sys.argv: dam_only()
    stage_materials()
