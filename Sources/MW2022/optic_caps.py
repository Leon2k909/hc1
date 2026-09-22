"""Remove authored opaque lens plugs without changing the surrounding optic housing.

Source optics can put black lens backs in the housing material. Keep the source
OBJ intact and remove only isolated surface components crossing the optical axis
whose vertices fit inside the lens aperture. Hard edges/UV seams separate these
plugs from the housing in the exported vertex topology.
"""
import numpy as np

def clear_caps(lines, model, materials, center, aperture):
    positions=[]; faces=[]; by_vertex={}; group=material=None
    for li,line in enumerate(lines):
        f=line.split()
        if not f:continue
        if f[0]=='v':positions.append([float(x) for x in f[1:]])
        elif f[0]=='usemtl':material=f[1]
        elif f[0] in ('g','o'):group=f[1]
        elif f[0]=='f' and not materials[model['materials'][material]].get('optic_glass') and not any(t in model['materials'][material] for t in ('stencil','depth_mask')):
            ids=[int(v.split('/')[0])-1 for v in f[1:]]
            idx=len(faces);faces.append((li,group,material,ids))
            for v in ids:by_vertex.setdefault((group,material,v),[]).append(idx)
    positions=np.array(positions);center=np.array(center)
    radius=min(aperture[1][i]-aperture[0][i] for i in (0,1))*.5
    seen=set(); removed=set(); report=[]
    for seed in range(len(faces)):
        if seed in seen:continue
        component=set();todo=[seed]
        while todo:
            i=todo.pop()
            if i in component:continue
            component.add(i);_,g,m,ids=faces[i]
            for v in ids:todo.extend(j for j in by_vertex[(g,m,v)] if j not in component)
        seen.update(component)
        # The 2x magnifier's front plug shares vertices with its bevel. Select
        # the flat disk itself; keep the bevel and outer ring.
        if model['key']=='att_vm_2x_west01' and len(component)>100:
            component={i for i in component if np.max(np.abs(positions[faces[i][3],2]+.51))<.0001}
            component={i for i in component if np.max(np.linalg.norm(positions[faces[i][3],:2]-center,axis=1))<radius*1.22}
        if not component:continue
        coords=positions[list({v for i in component for v in faces[i][3]})]
        # Some optics have offset front objectives; their isolated lens disks
        # can be wider than the rear aiming surface.
        if np.max(np.linalg.norm(coords[:,:2]-center,axis=1))>radius*1.5:continue
        if np.ptp(coords[:,2])>1.5:continue
        hit=False
        for i in component:
            t=positions[faces[i][3]];a=np.vstack((t[:,:2].T,np.ones(3)))
            if abs(np.linalg.det(a))>1e-10 and min(np.linalg.solve(a,[*center,1]))>=-1e-5:hit=True;break
        if not hit:continue
        removed.update(faces[i][0] for i in component)
        report.append(dict(triangles=len(component),material=model['materials'][faces[seed][2]],min=coords.min(0).tolist(),max=coords.max(0).tolist()))
    return [line for i,line in enumerate(lines) if i not in removed],report
