"""Reference-oriented forest proportions and cheaper outer-horizon trees.

Called once on freshly generated instances. Existing list indices and rotations
stay intact; roots follow the wooded relief. Middle/distant trees form groves;
near trees and the northern waterfall opening keep their positions.
"""
from pathlib import Path
import re
import math
import numpy as np
import map_kit as K

RESOURCE='models/maps/forestbase/fir'
ASPECTS={'adult':(.86,.86,1.20),'middle':(.88,.88,1.10),'horizon':(.84,.84,1.04)}
HORIZON_START=3600

def tree_count(instances):
    return sum(item[0].startswith(('Fir ','Young fir ','Forest middle ','Far fir ','Forest understory '))
               for item in instances)

def distance_from_play(e,n):
    return float(np.hypot(max(abs(e)-1550,0),max(n-1450,-1730-n,0)))


def regroup(instances):
    """Redistribute existing background trees once, without adding instances.

    Input is the original generated layout, not an already regrouped scene.
    North-side trees are excluded to preserve the waterfall framing.
    """
    def moved(name):
        return (name.startswith('Forest middle ') and int(name.split()[2])>0 or
                name.startswith('Far fir infill ') and int(name.split()[3])>0)
    def tree(name):return name.startswith(('Fir ','Young fir ','Forest middle ','Far fir ','Forest understory '))
    occupied=[np.array(p[:2]) for name,path,p,yaw,scale in instances if tree(name) and not moved(name)]
    result=[]
    for name,path,pos,yaw,scale in instances:
        if not moved(name):result.append((name,path,pos,yaw,scale));continue
        e,n,z=pos
        far=name.startswith('Far fir infill ')
        if far:
            side=int(name.split()[3])
            if side in (1,2):n*=3200/6000
            else:
                e*=3200/6000
                if abs(e)<900:e=-900 if e<0 else 900
        else:
            side,k=map(int,name.split()[2:4])
            if side in (1,2):
                across=2800+(abs(e)-3000)*(1000/1550)
                e=across*(-1 if side==1 else 1)
                n=((k//3)%3-1)*1400+n*(460/3600)
            else:
                across=2800+(-n-350-3000)*(1000/1550)
                n=-across-350
                e=math.copysign(800+(abs(e)-650)*(1400/2950),e)
        for attempt in range(65):
            radius=0 if not attempt else 24*math.sqrt(attempt)
            angle=attempt*2.3999632297
            candidate=np.array((e+radius*math.cos(angle),n+radius*math.sin(angle)))
            if far and distance_from_play(*candidate)<HORIZON_START:continue
            if candidate[1]<-1450 and abs(candidate[0])<650:continue
            if all(np.linalg.norm(candidate-p)>=64 for p in occupied):break
        else:raise AssertionError('Unable to separate forest trunks: '+name)
        occupied.append(candidate)
        result.append((name,path,(float(candidate[0]),float(candidate[1]),z),yaw,scale))
    return result


def fit_roots(instances):
    """Follow the exact triangulated relief while retaining old root burial."""
    import forestbase_floor as floor
    result=[]
    for name,path,pos,yaw,scale in instances:
        if name.startswith(('Fir ','Young fir ','Forest middle ','Far fir ','Forest understory ')):
            e,n,z=pos
            delta=floor.height(e,n)-floor.height(e,n,False)
            if abs(delta)>1e-8:pos=(e,n,z+delta)
        result.append((name,path,pos,yaw,scale))
    return result


def write_horizon_models(output=None):
    """Use reduced dimensional branch geometry in every outer-horizon group."""
    output=K.ASSETS/RESOURCE if output is None else Path(output)
    output.mkdir(parents=True,exist_ok=True)
    for variant in 'abc':
        folder=K.ASSETS/RESOURCE
        assert (output/f'fir_{variant}_horizon.obj').is_file() or (folder/f'fir_{variant}_horizon.obj').is_file()
        text=(folder/f'fir_{variant}.vmdl').read_text()
        regular=text.replace(f'filename = "{RESOURCE}/fir_{variant}_lod2.obj"',
                             f'filename = "{RESOURCE}/fir_{variant}_horizon.obj"')
        regular_path=output/f'fir_{variant}.vmdl'
        if not regular_path.exists() or regular_path.read_text()!=regular:K.write_text(regular_path,regular)
        text,count=re.subn(r'filename = "'+RESOURCE+rf'/fir_{variant}_(?:lod[012]|horizon)\.obj"',
                          f'filename = "{RESOURCE}/fir_{variant}_horizon.obj"',text)
        assert count==3
        path=output/f'fir_{variant}_horizon.vmdl'
        if not path.exists() or path.read_text()!=text:K.write_text(path,text)


def authored(instances):
    adjusted=[]
    for name,path,pos,yaw,scale in instances:
        aspect=None
        if name.startswith('Fir '):aspect=ASPECTS['adult']
        elif name.startswith('Forest middle '):aspect=ASPECTS['middle']
        elif name.startswith('Far fir '):
            aspect=ASPECTS['horizon']
            if distance_from_play(*pos[:2])>=HORIZON_START:
                path=path.replace('_far.vmdl','_horizon.vmdl')
        if aspect:scale=tuple(a*s for a,s in zip(aspect,scale))
        adjusted.append((name,path,pos,yaw,scale))

    # Infill uses reduced dimensional crowns beyond the middle forest.
    # Keep all roots on the existing outer leaf-litter floor.
    rng=np.random.default_rng(31678)
    for side in range(4):
        for k in range(16):
            along=float(rng.uniform(-6000,6000));across=float(rng.uniform(5400,6600))
            if side==0:e,n=along,across
            elif side==1:e,n=-across,along
            elif side==2:e,n=across,along
            else:
                e,n=along,-across
                if abs(e)<800:e=-900 if e<0 else 900
            s=float(rng.uniform(1.25,1.85));aspect=ASPECTS['horizon']
            adjusted.append((f'Far fir infill {side} {k}',f'{RESOURCE}/fir_{"abc"[k%3]}_horizon.vmdl',
                             (e,n,-120),float(rng.uniform(0,360)),tuple(a*s for a in aspect)))

    # Smaller copies of the dimensional branch models form an intermediate
    # canopy. Existing saplings retain their authored proportions below it.
    # This avoids enlarging one-metre saplings and their needles severalfold.
    rng=np.random.default_rng(60432)
    for side in range(4):
        for k in range(6):
            if side==0:
                along=float(rng.uniform(-1480,-800) if k%2==0 else rng.uniform(1300,1550))
            elif side==3:
                along=float(rng.uniform(-1500,-800) if k%2==0 else rng.uniform(800,1500))
            else:along=float(rng.uniform(-1400,1400))
            edge=1450 if side in (0,3) else 1550
            depth=float(rng.uniform(400 if side==3 else 220,480));across=edge+depth
            if side==0:e,n=along,across
            elif side==1:e,n=-across,along
            elif side==2:e,n=across,along
            else:e,n=along,-across
            s=float(rng.uniform(.35,.50));root=-8-min(depth,300)*112/300
            adjusted.append((f'Forest understory {side} {k}',f'{RESOURCE}/fir_{"abc"[k%3]}_far.vmdl',
                             (e,n,root),float(rng.uniform(0,360)),(.9*s,.9*s,1.12*s)))
    old_names={item[0] for item in instances}
    added_names=[item[0] for item in adjusted[len(instances):]]
    assert len(set(added_names))==len(added_names) and not old_names.intersection(added_names)
    return fit_roots(regroup(adjusted))
