"""Prepare the established scoped installer for the user-selected chair."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
if (Path(__file__).parent/'installed.json').exists() and (Path(__file__).parent/'verify_accepted.py').exists():
    print('Preserving the accepted installer and verifier.')
    raise SystemExit(0)
source=(ROOT/'Sources/Collider/monitor-trial-v1/install_accepted.py').read_text()
replacements={
    'approved monitor':'approved chair',
    'import collider_monitor as CM':'import collider_chair as CM',
    'collider-monitor-accepted-20261029':'collider-chair-accepted-20261029',
    'monitor-trial-v1':'chair-trial-v1',
    'Monitor already installed':'Chair already installed',
    'len(removed)==26':'len(removed)==100',
    'count-26+':'count-100+',
    'Accepted control-room monitor':'Accepted operator chair',
    'collider_approved_monitor':'collider_approved_chair',
    "p.startswith('mm_')":"p.startswith('op_')",
    'len(remaps)==7':'len(remaps)==4',
    "'.monitor-incoming'":"'.chair-incoming'",
    "'placementPlan':[1880.,-190.,381.],'removedOldTriangles':26":"'placementPlan':[1723.,-55.,256.],'removedOldTriangles':100",
    'Tools/collider_monitor.py; collider_map.monitor selected placement':'Tools/collider_chair.py; collider_map.control_desk selected chair',
}
for old,new in replacements.items():
    assert old in source,old
    source=source.replace(old,new)
(Path(__file__).parent/'install_accepted.py').write_text(source)
verify=(ROOT/'Sources/Collider/monitor-trial-v1/verify_accepted.py').read_text()
for old,new in {
    'approved monitor':'approved chair','monitor_install':'chair_install',
    'collider-monitor-accepted-20261029':'collider-chair-accepted-20261029',
    'import collider_monitor as CM':'import collider_chair as CM',
    'M.monitor(m,(1880.,-190.,381.),(-1,0),112,66,0)':'CM.append(m)',
    'o collider_approved_monitor':'o collider_approved_chair',
    'approvedMonitorInstalled':'approvedChairInstalled',
    'oldMonitorTrianglesRemaining':'oldChairTrianglesRemaining',
}.items():
    assert old in verify,old
    verify=verify.replace(old,new)
verify=verify.replace('for p in d[\'retiredOldStandaloneResources\']:', '''
def model_triangles(model):
    return Counter(I.I.key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in model.polygons.items()
        for ps,n in polys for i in range(1,len(ps)-1))
def plain(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    return value
station=K.Model();legacy=K.Model()
M.control_desk(station,1,-55.,256.);M._legacy_control_desk(legacy,1,-55.,256.)
assert model_triangles(station)==model_triangles(legacy)-before+after,'Station generator changed unrelated geometry'
assert plain(station.boxes)==plain(legacy.boxes) and plain(station.hulls)==plain(legacy.hulls),'Station collision changed'
for side,n,z in ((-1,-55.,256.),(1,95.,256.),(1,-220.,560.)):
    a=K.Model();b=K.Model();M.control_desk(a,side,n,z);M._legacy_control_desk(b,side,n,z)
    assert model_triangles(a)==model_triangles(b) and plain(a.boxes)==plain(b.boxes),'Other station changed'
for p in d['retiredOldStandaloneResources']:''')
verify=verify.replace("'priorCaseAndCabinetSourceHashesPreserved':True", "'priorCaseAndCabinetSourceHashesPreserved':True,'stationCollisionUnchanged':True,'otherStationsUnchanged':True")
(Path(__file__).parent/'verify_accepted.py').write_text(verify)
print('Prepared guarded source installer for the accepted chair.')
