"""Stage a bounded gallery cover fix against the currently installed detail mesh."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
import collider_gallery_trench as T

OUT=ROOT/'output/collider-gallery-drain-20261027'
STAGE=OUT/'stage-v1'
BASE='models/maps/collider/collider_detail'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def triangles(model):
    for paint,polys in model.polygons.items():
        for points,normal in polys:
            for i in range(1,len(points)-1):
                yield paint,np.array([points[0],points[i],points[i+1]])


def key(paint,points):
    return paint,tuple(sorted(tuple(round(float(v),3) for v in p) for p in points))


def main():
    assert not STAGE.exists(), 'Keep the original baseline; use a fresh revision for another candidate.'
    before=STAGE/'before'
    assets=STAGE/'assets'
    for ext in ('.obj','.mtl','.vmdl'):
        relative=BASE+ext
        target=before/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/'Assets'/relative).read_bytes())
    old,new=K.Model(),K.Model()
    T.legacy(old)
    T.append(new)
    assert not new.boxes and not new.hulls and not old.boxes
    M.configure(new)
    expected=Counter(key(p,pts) for p,pts in triangles(old))
    remaining=expected.copy()
    vertices=[]
    uv_count=normal_count=0
    retained=[]
    paint=None
    removed=0
    source=(before/(BASE+'.obj')).read_text().splitlines(keepends=True)
    assert not any('gallery-drain-v1' in line for line in source)
    for line in source:
        if line.startswith('v '):
            a,b,c=map(float,line.split()[1:])
            vertices.append(np.array((-a,c,b)))
        elif line.startswith('vt '):uv_count+=1
        elif line.startswith('vn '):normal_count+=1
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            ids=[int(part.split('/')[0]) for part in line.split()[1:]]
            signature=key(paint,[vertices[i-1] for i in ids])
            if remaining[signature]:
                remaining[signature]-=1
                removed+=1
                continue
        retained.append(line)
    assert not +remaining, ('Original gallery strips did not match',sum((+remaining).values()))
    assert removed==288,removed
    generated=STAGE/'generated'
    generated.mkdir(parents=True)
    K.write_obj(generated/'collider_detail.obj',new,'collider_detail')
    extra=['\n# gallery-drain-v1: connected covers and fitted galvanized framing\n','o gallery_drain_v1\n']
    offsets=(len(vertices),uv_count,normal_count)
    added=0
    for line in (generated/'collider_detail.obj').read_text().splitlines(keepends=True):
        if line.startswith(('mtllib ','# ','o ')):continue
        if line.startswith('f '):
            line='f '+' '.join('/'.join(str(int(v)+offsets[k]) for k,v in enumerate(word.split('/')))
                              for word in line.split()[1:])+'\n'
            added+=1
        extra.append(line)
    target=assets/(BASE+'.obj')
    target.parent.mkdir(parents=True)
    target.write_text(''.join(retained+extra),encoding='utf-8',newline='')
    (assets/(BASE+'.mtl')).write_bytes((before/(BASE+'.mtl')).read_bytes()+b'newmtl co_drain_frame\nKd 1 1 1\nd 1\n')
    doc=(before/(BASE+'.vmdl')).read_text()
    pattern=r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])'
    updated,count=re.subn(pattern,lambda m:m[1]+m[2].rstrip().rstrip(',')+',\n'+
        '\t'*7+'{ from = "co_drain_frame.vmat" to = "'+T.MATERIAL+'" }'+m[3],doc,count=1)
    assert count==1
    marker='\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
    assert doc[doc.index(marker):]==updated[updated.index(marker):]
    (assets/(BASE+'.vmdl')).write_text(updated,encoding='utf-8',newline='')
    T.materials(assets/'materials/collider')
    files=[dict(relative=p.relative_to(assets).as_posix(),before=sha(ROOT/'Assets'/p.relative_to(assets)),after=sha(p))
           for p in sorted(assets.rglob('*')) if p.is_file()]
    deps=['materials/railhead/rw_galvanised_'+s+'.png' for s in ('color','normal','rough')]
    protected=[p.relative_to(ROOT/'Assets').as_posix() for p in (ROOT/'Assets/models/maps/collider').glob('collider_detail_hulls*.obj')]
    manifest=dict(revision='gallery-drain-v1',files=files,
        protected={p:sha(ROOT/'Assets'/p) for p in protected+deps},
        geometry=dict(before_triangles=sum(s.startswith('f ') for s in source),removed_triangles=removed,
                      added_triangles=added,after_triangles=sum(s.startswith('f ') for s in retained)+added,
                      retained_faces_and_attributes_preserved=True,collision_unchanged=True,
                      old_junction_gap_inches=8,new_junction_gap_inches=0),
        sources={'Tools/collider_gallery_trench.py':sha(ROOT/'Tools/collider_gallery_trench.py')})
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    source=(ROOT/'Sources/Collider/editor/capture.cs.txt').read_text()
    source=source.replace('output/collider','output/collider-gallery-drain-20261027')
    source=source.replace('new[]{"collider_structure","collider_machine"}','new[]{"collider_structure","collider_detail","collider_machine"}')
    source=source.replace('.Concat(System.IO.Directory.EnumerateFiles',
        '.Concat(new[]{"materials/collider/co_drain_frame.vmat"}.Where(p=>System.IO.File.Exists(System.IO.Path.Combine(root,"Assets",p))))\n    .Concat(System.IO.Directory.EnumerateFiles')
    (ROOT/'Sources/Collider/gallery-drain-v1/capture.cs.txt').write_text(source,encoding='utf-8')
    config=dict(width=1440,height=900,supersample=2,folder='before',views=[
        dict(name='west-junction',eye=[-1240,-700,324],target=[-1314,-833,256],fov=62),
        dict(name='west-joint',eye=[-1240,-610,324],target=[-1318,-700,256],fov=58),
        dict(name='east-junction',eye=[1240,470,324],target=[1314,587,256],fov=62)])
    (OUT/'capture-config.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps({'Stage':str(STAGE),'Files':len(files),'Geometry':manifest['geometry']},indent=2))


if __name__=='__main__':main()
