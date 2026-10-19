"""Sequential native viewport checks; one bitmap per call, no temporary worlds."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
VIEWS={
    'west-street':((125,1800,64),(-2.7,-88.57,0),80),
    'east-street':((125,-1800,64),(-2.7,88.57,0),80),
    'cart':((120,1720,55),(1.533,-15.524,0),70),
    'bench':((-930,1710,42),(15.703,-116.565,0),80),
    'lantern':((-950,1530,125),(-6.19,-40.601,0),80),
    'sacks':((1210,2050,68),(9.24,42.51,0),80),
    'door-terrace':((-1040,1660,54),(3.14,-13.53,0),70),
    'door-green':((680,1290,55),(4.4,68.64,0),80),
}
for name,eye,target,fov in (
    ('terrace',(-1760,-950,64),(0,-950,110),80),
    ('valley',(-700,-950,64),(1500,-9000,-900),80),
    ('west-ridge',(-250,125,64),(-8000,125,520),80),
    ('west-ridge-detail',(-250,125,64),(-8000,125,520),35),
    ('ground-edge',(-1313.323,379.7965,64),(-1393.323,379.7965,26),90),
    ('ground-edge-close',(-1313.323,379.7965,38),(-1393.323,379.7965,1),65),
    ('ground-edge-sunlit',(-1936.32457,627.60665,64),(-1856.32457,627.60665,26),90),
    ('ground-edge-sunlit-close',(-1936.32457,627.60665,38),(-1856.32457,627.60665,1),65),
    ('facade-north',(-1700,125,64),(-1625,350,238),70),
    ('facade-south',(-1700,125,64),(-1625,-100,238),70),
    ('coping',(-1710,-950,52),(-1560,-994,28),70),
    ('garden-shed',(-1630,-1200,25),(-1780,-1390,10),70),
    ('small-shed',(-1120,-1060,18),(-1410,-1060,3),70),
    ('garden-store',(-1550,-1260,16),(-1700,-1105,-20),75),
    ('firewood',(-1760,-1320,7),(-1790,-1155,-28),65),
    ('wheelbarrow',(-1445,-1263,0),(-1530,-1185,-25),65),
    ('council-hall',(-240,1030,240),(180,650,235),85),
    ('hall-office',(-260,930,64),(-245,680,70),85),
    ('clerk-desk',(-270,745,62),(-290,840,26),70),
    ('council-table',(0,620,230),(0,825,198),75),
    ('hall-archive',(-230,760,230),(-422,650,217),75),
    ('cafe',(-330,-370,64),(-550,-210,82),75),
    ('map-art',(-470,-390,160),(-50,600,350),100),
):
    e=(eye[1],-eye[0],eye[2]); t=(target[1],-target[0],target[2])
    dx,dy,dz=(b-a for a,b in zip(e,t))
    angles=(-math.degrees(math.atan2(dz,math.hypot(dx,dy))),math.degrees(math.atan2(dy,dx)),0)
    VIEWS[name]=(e,angles,fov)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory',required=True)
parser.add_argument('--views',nargs='+',choices=VIEWS,required=True)
parser.add_argument('--trial',action='store_true')
parser.add_argument('--weathered-plaster-trial',action='store_true',help='Preview separate weathered plaster v2 materials.')
parser.add_argument('--forest-trial',action='store_true')
parser.add_argument('--forest-brightness',type=float)
parser.add_argument('--canopy-trial',action='store_true',help='Temporarily compare the separate full-resolution canopy materials.')
parser.add_argument('--farfield-trial',action='store_true',help='Temporarily compare the separate far-field terrain colour maps and matching forest materials.')
parser.add_argument('--forest-detail-trial',action='store_true',help='Temporarily compare the checked forest-detail material on all 88 current woodland sectors.')
parser.add_argument('--forest-coverage-trial',action='store_true',help='Temporarily compare the checked forest alpha-mip compensation material.')
parser.add_argument('--forest-coverage-strength',type=float,help='Private alpha-mip compensation strength: one is the accepted response, zero cancels the mip boost.')
parser.add_argument('--forest-detail-blend',type=float,help='Private material-copy blend from zero (accepted response) to one (detail trial).')
parser.add_argument('--forest-detail-fade',type=float,nargs=2,metavar=('START','END'),help='Diagnostic fade range on the private forest material copy.')
parser.add_argument('--ground-edge-trial',action='store_true',help='Temporarily insert the checked two-model ground-edge trial without collision or shadows.')
parser.add_argument('--street-trial',action='store_true',help='Temporarily override existing cobbles with the dedicated dry-patina trial material.')
parser.add_argument('--look-trial',choices=('aces-lower','agx-lower','agx-saved','aces-fixed-low','aces-fixed-high'),help='Temporary tone mapping comparison, restored after capture.')
parser.add_argument('--sync-main-postprocess',action='store_true',help='Exposure diagnostic: also update the scene main camera before editor-camera rendering.')
parser.add_argument('--prepare-only',action='store_true',help='Write one view config for the connected native MCP session.')
parser.add_argument('--pid',type=int,help='Attach to the already-verified editor process.')
args=parser.parse_args()
if sum((args.canopy_trial,args.farfield_trial,args.forest_detail_trial,args.forest_coverage_trial))>1:
    parser.error('Only one landscape trial may be selected')
if (args.forest_detail_trial or args.forest_coverage_trial) and args.forest_trial:
    parser.error('Compare forest material and geometry separately')
if args.ground_edge_trial and any((args.trial,args.weathered_plaster_trial,args.forest_trial,args.canopy_trial,args.farfield_trial,args.forest_detail_trial,args.forest_coverage_trial,args.street_trial)):
    parser.error('Compare ground-edge geometry separately from other asset trials')
if args.forest_detail_blend is not None and (not args.forest_detail_trial or not math.isfinite(args.forest_detail_blend) or not 0<=args.forest_detail_blend<=1):
    parser.error('--forest-detail-blend requires --forest-detail-trial and a finite value from zero to one')
if args.forest_detail_fade is not None and (not args.forest_detail_trial or not all(math.isfinite(v) for v in args.forest_detail_fade) or not 1000<=args.forest_detail_fade[0]<args.forest_detail_fade[1]<=65000):
    parser.error('--forest-detail-fade requires --forest-detail-trial and a finite increasing range from 1000 to 65000 units')
if args.forest_coverage_strength is not None and (not args.forest_coverage_trial or not math.isfinite(args.forest_coverage_strength) or not 0<=args.forest_coverage_strength<=1):
    parser.error('--forest-coverage-strength requires --forest-coverage-trial and a finite value from zero to one')
if args.prepare_only and len(args.views)!=1:
    parser.error('--prepare-only requires exactly one view')
for name in args.views:
    position,angles,fov=VIEWS[name]
    config={'directory':args.directory,'name':name,'position':','.join(map(str,position)),
            'angles':','.join(map(str,angles)),'fov':fov,'width':1920,'height':1080,'plaster_trial':args.trial,'forest_trial':args.forest_trial,'forest_brightness':args.forest_brightness}
    config['sync_main_postprocess']=args.sync_main_postprocess
    config['canopy_trial']=args.canopy_trial
    config['farfield_trial']=args.farfield_trial
    config['forest_detail_trial']=args.forest_detail_trial
    config['forest_coverage_trial']=args.forest_coverage_trial
    if args.forest_coverage_strength is not None:
        config['forest_coverage_strength']=args.forest_coverage_strength
    config['ground_edge_trial']=args.ground_edge_trial
    if args.forest_detail_blend is not None:
        config['forest_detail_blend']=args.forest_detail_blend
    if args.forest_detail_fade is not None:
        config['forest_detail_fade_start'],config['forest_detail_fade_end']=args.forest_detail_fade
    config['weathered_plaster_trial']=args.weathered_plaster_trial
    config['street_trial']=args.street_trial
    if args.look_trial:
        low=args.look_trial.endswith('-lower')
        config['look_trial']={'minimum_exposure':.7 if low else 1.05,'maximum_exposure':1.5 if low else 2.2,
                              'compensation':0,'mode':'ACES' if args.look_trial.startswith('aces-') else 'AgX'}
        if args.look_trial in ('aces-fixed-low','aces-fixed-high'):
            exposure=.35 if args.look_trial.endswith('-low') else 2.0
            config['look_trial'].update(minimum_exposure=exposure,maximum_exposure=exposure)
    (ROOT/'output/belltower/quality/viewport-capture.json').write_text(json.dumps(config,indent=2)+'\n')
    if args.prepare_only:
        print(f'Prepared {name}',flush=True)
        continue
    subprocess.run([sys.executable,'-X','utf8','output/knife-throw/editor_check.py',
                    '--script','Sources/Belltower/editor/capture-viewport.cs.txt',
                    '--output-dir',f'output/belltower/quality/{args.directory}',
                    '--cleanup-exchange',
                    '--direct-call',
                    '--timeout','90']+(['--pid',str(args.pid)] if args.pid is not None else []),cwd=ROOT,check=True)
    destination=ROOT/'output/belltower/quality'/args.directory
    captured=json.loads((destination/(name+'-camera.json')).read_text(encoding='utf-8'))
    if not captured['GamePreserved'] or not captured['SelectedDocumentPreserved'] or captured['SceneHasUnsavedChanges']:
        raise RuntimeError('Shared game/document state changed during the capture; inspect before continuing')
    if args.forest_coverage_trial:
        restored=json.loads((destination/(name+'-restore.json')).read_text(encoding='utf-8'))
        if captured['TrialForestCoverageSlots']!=88 or restored!={'MaterialsRestored':True,'Slots':88}:
            raise RuntimeError('Forest coverage override did not match and restore all 88 slots')
    if args.look_trial and not json.loads((destination/(name+'-look-restore.json')).read_text(encoding='utf-8'))['ToneRestored']:
        raise RuntimeError('The temporary exposure profile did not restore')
    print(f'Captured {name}',flush=True)
