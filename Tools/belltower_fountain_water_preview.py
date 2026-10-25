"""Stage a native before/after basin preview without opening or changing a scene."""
from pathlib import Path
import json
import re
import hashlib
import numpy as np
import map_kit as K
import belltower_detail as D
import belltower_compact_obj as C
from belltower_stage_fountain_water import ROOT, OUT, sha


def main():
    stage=OUT/'preview-stage'; stage.mkdir(parents=True,exist_ok=True)
    report={'files':{}}
    vmdl=ROOT/'Assets/models/maps/belltower/belltower_centre.vmdl'
    remaps=dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"',vmdl.read_text()))
    for side in ('before','after'):
        source=(OUT/'before/Assets/models/maps/belltower/belltower_centre.obj') if side=='before' else ROOT/'Assets/models/maps/belltower/belltower_centre.obj'
        model=K.Model(); model.tile_overrides.update(D.TILES)
        for paint in ('fountain_water','fountain_jet'): model.tile_overrides[paint]=96
        for paint in ('fountain_limestone','fountain_relief','fountain_bronze'): model.tile_overrides[paint]=48
        data=C.tables(source); counts={k:len(v)-1 for k,v in data.items()}
        paint=None
        for line in source.open('rb'):
            if line.startswith(b'usemtl '): paint=line.split()[1].decode()
            elif line.startswith(b'f ') and (paint.startswith('fountain_') or paint in ('iron_black','planks_dark','roof_tiles')):
                rows=C.face_tokens(line,counts)
                obj=[np.asarray(list(map(float,data[b'v'][r[0]].split()[1:]))) for r in rows]
                points=[np.array((-p[0],p[2],p[1])) for p in obj]
                if not all(abs(p[0])<116 and abs(p[1]-130)<116 and -.1<=p[2]<=70 for p in points): continue
                uv=[tuple(map(float,data[b'vt'][r[1]].split()[1:])) for r in rows]
                normal=[np.asarray(list(map(float,data[b'vn'][r[2]].split()[1:]))) for r in rows]
                normal=[np.array((-p[0],p[2],p[1])) for p in normal]
                model.polygon(paint,points,uv=uv,normals=normal)
        model.material_overrides.update(remaps)
        if side=='before':
            for paint,short in (('fountain_water','water'),('fountain_jet','jet')):
                relative=Path(f'Assets/materials/belltower/fountain-water-v2-preview/legacy-{short}.vmat')
                target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((OUT/f'before/Assets/materials/belltower/{paint}.vmat').read_bytes())
                report['files'][relative.as_posix()]={'source':target.relative_to(ROOT).as_posix(),'sha256':sha(target)}
                model.material_overrides[paint]=relative.relative_to('Assets').as_posix()
        relative=Path(f'Assets/models/maps/belltower/fountain-water-v2-preview/{side}.obj')
        target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(target,model,'belltower_centre')
        K.write_vmdl(target.with_suffix('.vmdl'),'models/maps/belltower/fountain-water-v2-preview',side,model)
        for suffix in ('.obj','.mtl','.vmdl'):
            path=target.with_suffix(suffix)
            report['files'][path.relative_to(stage).as_posix()]={'source':path.relative_to(ROOT).as_posix(),'sha256':sha(path)}
    (stage/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'native_preview_files':len(report['files']),'source_assets_modified':False}))


if __name__=='__main__': main()
