"""Stage refreshed Collider reflection sources using its verified camera-face converter."""
from pathlib import Path
import ast
import hashlib
import json
import sewage_reflections as shared

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/depot-finish-20261027/reflection-stage'


def main():
    source=(ROOT/'Tools/sewage_reflections.py').read_text()
    tree=ast.parse(source)
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='panorama')
    body=ast.get_source_segment(source,function)
    body=body.replace('output/sewage/reflections','output/depot-finish-20261027/reflections')
    body=body.replace('output/sewage/stage/materials/sewage/reflections',
        'output/depot-finish-20261027/reflection-stage/materials/collider/finish-v1/reflections')
    body=body.replace('materials/sewage/reflections/','materials/collider/finish-v1/reflections/')
    namespace=dict(vars(shared));namespace['ROOT']=ROOT
    exec(compile(body,'collider_finish_reflection_panorama','exec'),namespace)
    for label in ('Hall','Beam','West','East'):namespace['panorama'](label)
    entries=[]
    for path in sorted(OUT.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(OUT).as_posix();target=ROOT/'Assets'/relative
        assert not target.exists(),f'Refusing to replace reflection authoring source: {target}'
        entries.append({'relative':relative,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest={'files':entries,'scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Collider/collider.scene').read_bytes()).hexdigest()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
