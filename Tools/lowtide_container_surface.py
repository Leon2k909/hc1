"""Stage painted-metal response using the existing unmodified generated scans."""
from pathlib import Path
import argparse
import hashlib
import json
import uuid

ROOT=Path(__file__).resolve().parents[1]
SHADER='shaders/hc1_lowtide_container.shader'
SOURCE=ROOT/'Sources/Lowtide/containers/hc1_lowtide_container.shader'


def material_text(colour,frame=False):
    stem=f'materials/lowtide/containers/lt_container_{colour}'
    return f'''// Tools/lowtide_container_surface.py: enamel and seam weathering; original source pixels.
"Layer0"
{{
    shader "{SHADER}"
    TextureColor "{stem}_color.png"
    TextureNormal "{stem}_{'frame_normal' if frame else 'normal'}.png"
    TextureRoughness "{stem}_roughness.png"
    TextureMetalness "{stem}_metalness.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vContainerHeight "[0 102]"
    g_flCoatRoughness ".74"
    g_flWeathering ".85"
    g_flIsRail "{1 if frame else 0}"
}}
'''


def stage(out):
    out=out.resolve()
    assert not out.is_relative_to(ROOT/'Assets'),'Stage outside live Assets'
    changes={}
    def put(relative,data):
        path=out/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
        meta=path.with_suffix(path.suffix+'.meta')
        meta.write_text(json.dumps({'guid':str(uuid.uuid5(uuid.NAMESPACE_URL,'hc1/lowtide/container-surface/'+relative))},indent=2)+'\n')
        for p in (path,meta): changes[p.relative_to(out).as_posix()]={'after':hashlib.sha256(p.read_bytes()).hexdigest()}
    put(SHADER,SOURCE.read_bytes())
    for colour in ('blue','red','grey'):
        for frame in (False,True):
            name=f'lt_container_{colour}'+('_frame' if frame else '')
            put(f'materials/lowtide/container_surface/{name}.vmat',material_text(colour,frame).encode())
    protected={}
    for directory in ('Assets/materials/lowtide','Assets/models/maps/lowtide','Assets/scenes/maps/Lowtide'):
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and not p.name.endswith('_c'):
                protected[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    report={'changes':changes,'protected':protected,'status':'staged unused candidate; original six materials remain active',
            'scope':'No texture pixel, mesh, collision, lighting or scene change. Six candidate materials use the existing paint scans.'}
    (out.parent/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'staged_files':len(changes),'protected_files':len(protected)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True)
    stage(parser.parse_args().stage)
