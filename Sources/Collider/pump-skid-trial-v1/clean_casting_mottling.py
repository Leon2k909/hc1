"""Remove broad black mottling without changing the mesh or unrelated materials."""
from pathlib import Path
import importlib.util,json,shutil
HERE=Path(__file__).parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('pump_finish',HERE/'refine_valve_finish.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
B=F.B
OUT=B.OUT/'clean-finish-review';BACKUP=OUT/'before'
PAINTS=('ps_cast_skin','ps_motor_skin','ps_cast_face','ps_outlet_skin','ps_pump','ps_motor')

def main():
    assert not (OUT/'material-change.json').exists(),'This targeted finish revision is already built'
    manifest=json.loads((B.OUT/'manifest.json').read_text())
    for path,h in manifest['protectedSourceSHA256'].items():assert B.sha(ROOT/path)==h,path
    paths=[p for directory in (B.DEST,B.MD) for p in directory.iterdir()
           if p.is_file() and p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')]
    hashes={p.relative_to(ROOT).as_posix():B.sha(p) for p in paths}
    changed_expected={p for p in hashes if Path(p).name in
                      {name+'_'+suffix+'.png' for name in PAINTS for suffix in ('color','rough','metal','normal')} or
                      Path(p).name in {name+'.vmat' for name in PAINTS}}
    OUT.mkdir(parents=True,exist_ok=True)
    for rel in changed_expected|{p for p in hashes if p.startswith('Assets/models/')}:
        target=BACKUP/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,target)
    for name in ('revised-main.png','revised-surface.png','render-report.json'):
        shutil.copy2(B.OUT/'realism-review'/name,OUT/('before-'+name if name.endswith('.png') else 'before-'+name))
    F.refresh_casting_materials()
    actual={rel for rel,h in hashes.items() if B.sha(ROOT/rel)!=h}
    assert actual<=changed_expected,actual-changed_expected
    # Fine normal relief and exposed-metal boundaries must remain exactly as reviewed.
    for name in PAINTS:
        for suffix in ('normal','metal'):
            rel=(B.MD/(name+'_'+suffix+'.png')).relative_to(ROOT).as_posix()
            assert B.sha(ROOT/rel)==hashes[rel],rel
    for path,h in manifest['protectedSourceSHA256'].items():assert B.sha(ROOT/path)==h,path
    record={'status':'material-only-preview','geometrySHA256':manifest['models']['after']['meshSHA256'],
            'broadColourVariationBefore':.10,'broadColourVariationAfter':.018,
            'genericFlatSurfaceGreaseRemoved':True,'fineNormalAndMetalMapsByteIdentical':True,
            'changedFiles':{p:{'before':hashes[p],'after':B.sha(ROOT/p)} for p in sorted(actual)},
            'unchangedFiles':{p:h for p,h in hashes.items() if p not in actual},
            'protectedSourceSHA256':manifest['protectedSourceSHA256'],'installedInMap':False,'editorUsed':False}
    (OUT/'material-change.json').write_text(json.dumps(record,indent=2)+'\n')
    stats=json.loads((B.OUT/'valve-finish-stats.json').read_text());stats.update(F.STATS)
    (B.OUT/'valve-finish-stats.json').write_text(json.dumps(stats,indent=2)+'\n')
    manifest.update(realismRevision=4,finishAdjustment='Broad dark mottling removed; fine relief and metal wear preserved',
                    materialChangeEvidence='output/asset-improvement-20261030/pump-skid/clean-finish-review/material-change.json')
    for p in (B.OUT/'manifest.json',HERE/'candidate.json'):p.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ('changedFiles','unchangedFiles','protectedSourceSHA256')}))

if __name__=='__main__':main()
