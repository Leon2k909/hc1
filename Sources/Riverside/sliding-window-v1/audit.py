from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import riverside_map as R
import riverside_parts as P
OUT=ROOT/'output/riverside/sliding-window-v1';OUT.mkdir(parents=True,exist_ok=True)
windows=[];original=P.window
def collect(m,centre,right,w,h,style,seed=0):
    windows.append(dict(centre=[float(x) for x in centre],right=[float(x) for x in right],width=w,height=h,style=style,seed=seed))
    return original(m,centre,right,w,h,style,seed)
try:
    P.window=collect;part,info=R.build_trailer('T2',420,110,'rs_siding_teal',-1,12,'')
finally:P.window=original
options=[x for x in windows if x['centre'][1]<-50 and x['style']!='boarded'];assert options
chosen=min(options,key=lambda x:abs(x['centre'][0]-float(info['door'][0])))
chosen['world_plan']=[chosen['centre'][0]-820,chosen['centre'][1]+1050,chosen['centre'][2]]
chosen['existing_upgrade_audit']='T2 precast entry steps already upgraded and skipped. No trailer/sliding-window upgrade model/source found; architectural masonry windows and door windows are different assemblies.'
(OUT/'target.json').write_text(json.dumps(chosen,indent=2));print(json.dumps(dict(all_windows=windows,selected=chosen),indent=2))
