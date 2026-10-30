"""Prepare the exact-mesh installer and regeneration hook for the approved base."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent

helper=(ROOT/'Tools/collider_cooling_unit.py').read_text()
for old,new in (
    ('cooling-unit mesh','column-base mesh'),('cooling-unit-trial-v1','column-base-trial-v1'),
    ('(-1470.,1702.,20.)','(-960.,-500.,0.)')):
    assert old in helper,old
    helper=helper.replace(old,new)
(ROOT/'Tools/collider_column_base.py').write_text(helper,encoding='utf-8')

s=(ROOT/'Sources/Collider/cooling-unit-trial-v1/install_accepted.py').read_text()
for old,new in (
    ('cooling unit','column base'),('cooling-unit','column-base'),
    ('collider_cooling_unit','collider_column_base'),('Cooling unit','Column base'),
    ('58810b5ef523d2f5c3f4f238e3ce28562c9550b06ba8f47b0400d07d3ce7f76f','54e8a606a501804793153bc0f8a508f22cd1fd3e6cbd144d78bea49d21c69826'),
    ('collider_machine','collider_structure'),('len(removed)==170','len(removed)==12'),
    ('count-170+','count-12+'),('collider_approved_cooling_unit','collider_approved_column_base'),
    ("p.startswith('cu_')","p.startswith('cb_')"),('len(remaps)==14','len(remaps)==8'),
    ("'placementPlan':[-1470.,1702.,20.]","'placementPlan':[-960.,-500.,0.]"),
    ("'removedOldTriangles':170","'removedOldTriangles':12"),
    ('machineTrianglesBefore','structureTrianglesBefore'),('machineTrianglesAfter','structureTrianglesAfter'),
    ('collider_map.cooling_unit selected placement','collider_map.column_base selected placement')):
    assert old in s,old
    s=s.replace(old,new)

# Guard and include the procedural generator in the same rollback transaction.
marker="    completed=[]\n    try:\n"
replacement='''    generator=ROOT/'Tools/collider_map.py'
    old_generator=generator.read_bytes();generator_before=sha(generator)
    updated=old_generator.decode('utf-8')
    changes=[
        ('import collider_cooling_unit as CU\\n','import collider_cooling_unit as CU\\nimport collider_column_base as CB\\n'),
        ("        if paint.startswith('cu_'):","        if paint.startswith('cb_'):\\n            m.material_overrides[paint] = f'{CB.MATERIAL_DIR}/{paint}.vmat'\\n            m.tile_overrides[paint] = 12.\\n        elif paint.startswith('cu_'):"),
        ('def wall(m,axis,run,across,z,openings=()):',"def column_base(m,e,n):\\n    if (e,n)==tuple(CB.ORIGIN[:2]):\\n        box(m,e-44,e+44,n-44,n+44,0,8,None)\\n        CB.append(m)\\n    else:\\n        box(m,e-44,e+44,n-44,n+44,0,8,'co_trim')\\n\\ndef wall(m,axis,run,across,z,openings=()):"),
        ('            box(m,e-44,e+44,n-44,n+44,0,8,"co_trim")','            column_base(m,e,n)'),
    ]
    for old,new in changes:
        assert updated.count(old)==1,old
        updated=updated.replace(old,new)
    compile(updated,str(generator),'exec')
    generator_backup=OUT/'before/Tools/collider_map.py'
    generator_backup.parent.mkdir(parents=True,exist_ok=True);generator_backup.write_bytes(old_generator)
    completed=[]
    try:
        assert sha(generator)==generator_before
        generator.write_text(updated,encoding='utf-8',newline='')
'''
assert s.count(marker)==1
s=s.replace(marker,replacement)
s=s.replace('    except Exception:\n','    except Exception:\n        generator.write_bytes(old_generator)\n',1)
s=s.replace("'sceneAndPhysicsUnchanged':True,'retiredOldStandaloneResources':retired,",
    "'sceneAndPhysicsUnchanged':True,'retiredOldStandaloneResources':retired,\n        'generatorFile':{'path':'Tools/collider_map.py','before':generator_before,'after':sha(generator)},")
(HERE/'install_accepted.py').write_text(s,encoding='utf-8')
compile(s,str(HERE/'install_accepted.py'),'exec')
print('Prepared guarded column-base installer and regeneration helper; map is not modified yet.')
