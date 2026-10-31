"""Use the accepted valve's surface recipe on individually unwrapped pump parts."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import psutil
process=psutil.Process();process.nice(psutil.IDLE_PRIORITY_CLASS);process.cpu_affinity(process.cpu_affinity()[-2:])
from pathlib import Path
import importlib.util,json,math,shutil,sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.interpolate import PchipInterpolator

HERE=Path(__file__).parent;ROOT=HERE.parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
R=module('pump_realism',HERE/'refine_realism.py');B=R.B
V=module('accepted_valve_surfaces',ROOT/'Sources/Collider/valve-trial-v1/valve_surface.py')
K=B.K;O=B.O;face=B.face;UP=B.UP;X=B.X
CAST=(43.,61.,70.);MOTOR=(39.,51.,59.)
STATS={}

def coating(rng,shape,base,edge,grease,dust,tile):
    """Keep the valve's fine foundry relief, with restrained macro colour variation."""
    fine=V.field(rng,shape,.8);grain=V.field(rng,shape,2.1);orange=V.field(rng,shape,6.)
    broad=V.field(rng,shape,45.);patch=V.field(rng,shape,(5.,13.));pits=V.smooth(-grain,1.2,2.4)
    chip=V.smooth(edge*2.4+patch*.52+grain*.13,1.9,2.13)
    fringe=V.smooth(gaussian_filter(chip,2.1,mode='wrap'),.04,.4)*(1-chip)
    oxidation=V.smooth(broad*.6+patch*.5,1.,1.7)*np.clip(edge,0,1)*.48
    grease=np.clip(grease*(.72+.05*broad+.06*orange),0,.85)
    dusty=np.clip(dust*(.9+.08*broad),0,.34)
    colour=np.asarray(base)[None,None,:]*(1+.018*broad[...,None]+.020*orange[...,None]+.016*grain[...,None])
    colour=V.blend(colour,(67,42,25),fringe*.55+oxidation*.6)
    exposed=np.stack((109+9*grain,111+8*grain,104+6*grain),axis=-1)
    colour=V.blend(colour,exposed,chip);colour=V.blend(colour,(90,79,62),dusty)
    colour=V.blend(colour,(22,24,21),grease)
    height=.0032*grain+.0025*orange+.0006*fine-.010*pits-.0075*chip
    rough=np.clip(.49+.025*broad+.035*grain+.11*pits+.18*dusty-.23*grease-.14*chip,.18,.9)
    metal=np.clip(.025+.80*chip-.25*oxidation,0,.86)
    return colour,height,rough,metal,{'chipFraction':float((chip>.5).mean()),
        'roughnessRange':[float(rough.min()),float(rough.max())],'physicalTileInches':list(tile),
        'broadColourVariation':.018,'fineFoundryReliefRetained':True}
CAST_MAIN=PchipInterpolator([-7,-6.5,-4.5,-1.5,2.5,4.05],[.68,.80,.94,1.,1.,.96])
CAST_COVER=PchipInterpolator([4.24,4.8,5.6,6.8,8.],[.96,.985,.975,.89,.80])
OUTLET_PATH=B.S.rounded_path([(22,7,47),(22,7,65),(22,-20,65)],6.)
OUTLET_T=np.array([K.normalise(OUTLET_PATH[min(i+1,len(OUTLET_PATH)-1)]-OUTLET_PATH[max(i-1,0)]) for i in range(len(OUTLET_PATH))])
OUTLET_ARC=np.r_[0,np.cumsum(np.linalg.norm(np.diff(OUTLET_PATH,axis=0),axis=1))]
OUTLET_S=[];OUTLET_O=[];side=np.cross(OUTLET_T[0],UP)
if np.linalg.norm(side)<.01:side=np.cross(OUTLET_T[0],X)
for tangent in OUTLET_T:
    side=K.normalise(side-tangent*(side@tangent));OUTLET_S.append(side.copy());OUTLET_O.append(np.cross(tangent,side))

def outlet_uv(pts):
    indices=[];angles=[]
    for p in pts:
        d=p-np.array(OUTLET_PATH);distance=np.linalg.norm(d,axis=1)
        axial=np.abs(np.sum(d*OUTLET_T,axis=1));score=np.abs(distance-3.6)+axial
        i=int(np.argmin(score))
        if abs(distance[i]-3.6)>.035 or axial[i]>.035:return None
        indices.append(i);angles.append(math.atan2(d[i]@OUTLET_O[i],d[i]@OUTLET_S[i])/math.tau)
    if max(angles)-min(angles)>.5:angles=[a+1 if a<0 else a for a in angles]
    return [(OUTLET_ARC[i]/OUTLET_ARC[-1],a+.5) for i,a in zip(indices,angles)]

def uv_angle(points,centre,axis):
    # U is axial, V follows the unwrapped circumference. Unwrap each polygon at
    # its seam rather than stretching a triangle across an entire texture.
    if axis==0:angles=[math.atan2(p[2]-centre[2],p[1]-centre[1])/math.tau for p in points]
    else:angles=[math.atan2(p[2]-centre[2],p[0]-centre[0])/math.tau for p in points]
    if max(angles)-min(angles)>.5:angles=[a+1 if a<0 else a for a in angles]
    return angles

def finish_mesh(original):
    result=K.Model()
    for paint,polys in original.polygons.items():
        for i,(points,normal) in enumerate(polys):
            pts=np.array(points);target=paint;uv=original.polygon_uvs.get((paint,i))
            r=np.linalg.norm(pts[:,1:]-np.array((7.,39.)),axis=1)
            rm=np.linalg.norm(pts[:,1:]-np.array((7.,40.)),axis=1)
            theta=np.arctan2(pts[:,2]-39,pts[:,1]-7);axial=pts[:,0]-22
            scale=np.where(axial<=4.05,CAST_MAIN(np.clip(axial,-7,4.05)),CAST_COVER(np.clip(axial,4.24,8.)))
            expected=(17.5+1.1*np.cos(theta-.55)+.65*np.sin(2*theta-.6))*scale+.022*np.sin(theta*13+axial*.7)*np.sin(theta*5-axial*.4)
            casting_surface=np.all(abs(r-expected)<.07)
            if paint=='ps_pump' and np.all((pts[:,0]>=14.99)&(pts[:,0]<=30.01)) and casting_surface:
                if abs(normal[0])>.97:
                    target='ps_cast_face';uv=[(.5+(p[1]-7)/40,.5+(p[2]-39)/40) for p in pts]
                else:
                    target='ps_cast_skin';angles=uv_angle(pts,(22,7,39),0)
                    uv=[((p[0]-15)/15.,a+.5) for p,a in zip(pts,angles)]
            elif paint=='ps_motor' and pts[:,0].min()>=-46.6 and pts[:,0].max()<=.1 and np.all((rm>10.5)&(rm<17.3)) and np.ptp(rm)<.75 and abs(normal[0])<.9:
                target='ps_motor_skin';angles=uv_angle(pts,(-20,7,40),0)
                uv=[((p[0]+46.5)/47.,a+.5) for p,a in zip(pts,angles)]
            elif paint=='ps_pump' and pts[:,2].min()>46.9 and pts[:,0].min()>18.3 and pts[:,0].max()<25.7 and outlet_uv(pts) is not None:
                target='ps_outlet_skin';uv=outlet_uv(pts)
            elif paint in ('ps_pump','ps_metal') and pts[:,0].min()>30.39 and pts[:,0].max()<49.1 and np.all(abs(r-6.1)<.025):
                target='ps_bore';angles=uv_angle(pts,(39,7,39),0)
                uv=[((p[0]-30.4)/19.,a+.5) for p,a in zip(pts,angles)]
            elif paint=='ps_metal' and np.all((pts[:,0]>=47.54)&(pts[:,0]<=48.77)) and abs(normal[0])>.97 and np.all((r>=6.09)&(r<=7.81)):
                target='ps_lip';uv=[(.5+(p[1]-7)/17,.5+(p[2]-39)/17) for p in pts]
            elif paint in ('ps_pump','ps_motor'):
                uv=None
            result.polygon(target,points,normal,uv=uv,normals=original.polygon_normals.get((paint,i)))
    result.boxes=list(original.boxes);result.hulls=list(original.hulls)
    for paint in result.polygons:
        result.material_overrides[paint]=f'{B.MAT}/{paint}.vmat';result.tile_overrides[paint]=8. if paint in ('ps_pump','ps_motor') else 12.
    return result

def save(name,colour,height,rough,metal,tile):
    import ares_materials as AM
    rows,columns=height.shape
    Image.fromarray(np.clip(colour,0,255).astype('uint8')).save(B.MD/(name+'_color.png'))
    AM.BX.save_normal(B.MD/(name+'_normal.png'),AM.normals(height,(columns/tile[0],rows/tile[1])))
    AM.BX.save_grey(B.MD/(name+'_rough.png'),np.clip(rough,0,1))
    AM.BX.save_grey(B.MD/(name+'_metal.png'),np.clip(metal,0,1))
    prefix=f'{B.MAT}/{name}'
    text=O.vmat(name,prefix+'_color.png',prefix+'_normal.png',prefix+'_rough.png')
    text=text.replace('    g_flMetalness "0.0"',f'    F_METALNESS_TEXTURE "1"\n    TextureMetalness "{prefix}_metal.png"')
    (B.MD/(name+'.vmat')).write_text(text)

def skin(name,base,xlo,xhi,radius,seed):
    rng=np.random.default_rng(seed);shape=(4096,2048)
    yy,xx=np.mgrid[:shape[0],:shape[1]];u=xx/(shape[1]-1);v=1-yy/(shape[0]-1)
    angle=(v-.5)*math.tau
    top=np.clip(np.sin(angle),0,1);bottom=np.clip(-np.sin(angle),0,1)
    edge=np.exp(-(np.minimum(u,1-u)/.050)**2)
    # A cast split / bearing shoulder has more contact wear than the free skin.
    shoulder=.738 if name=='ps_cast_skin' else .90
    edge+=.60*np.exp(-((u-shoulder)/.021)**2)
    grease=np.clip(edge*.28+bottom**2*.12,0,.65);dust=top**3*.23
    tile=(xhi-xlo,math.tau*radius)
    colour,height,rough,metal,stats=coating(rng,shape,base,edge,grease,dust,tile)
    # A restrained foundry texture, using the same physical scale as the accepted valve.
    save(name,colour,height*.65,rough,metal,tile)
    STATS[name]={**stats,'texturePixels':[shape[1],shape[0]],'mapping':'axial / circumference'}

def outlet_material():
    rng=np.random.default_rng(310734);shape=(2048,2048)
    yy,xx=np.mgrid[:shape[0],:shape[1]];u=xx/(shape[1]-1);v=1-yy/(shape[0]-1)
    edge=np.exp(-(np.minimum(u,1-u)/.045)**2)
    tile=(float(OUTLET_ARC[-1]),math.tau*3.6)
    colour,height,rough,metal,stats=coating(rng,shape,CAST,edge,np.zeros(shape)+.045,np.zeros(shape)+.035,tile)
    save('ps_outlet_skin',colour,height*.40,rough,metal,tile)
    STATS['ps_outlet_skin']={**stats,'texturePixels':[2048,2048],'mapping':'continuous centreline / transported circumference'}

def casting_faces_and_fins():
    rng=np.random.default_rng(310733)
    # The cap has its own full-resolution radial map, including actual bolt seats.
    n=2048;yy,xx=np.mgrid[:n,:n];y=(xx/(n-1)-.5)*40;z=(.5-yy/(n-1))*40;r=np.hypot(y,z)
    edges=np.exp(-((r-14.7)/.38)**2)+.6*np.exp(-((r-7.6)/.28)**2)
    grime=np.zeros((n,n));rust=np.zeros((n,n))
    for a in np.linspace(0,math.tau,8,endpoint=False):
        cy=13.2*math.cos(a);cz=13.2*math.sin(a);d=np.hypot(y-cy,z-cz)
        edges+=.9*np.exp(-((d-.77)/.22)**2)
        grime+=.54*np.exp(-(d/1.20)**2)
        rust+=.14*np.exp(-((y-cy)/.31)**2)*np.exp(-(cz-z)/2.7)*((z<cz)&(z>cz-6))
    colour,height,rough,metal,stats=coating(rng,(n,n),CAST,np.clip(edges,0,1.5),np.clip(grime,0,.8),np.clip(z/20,0,1)*.13,(40,40))
    colour=V.blend(colour,(76,43,25),np.clip(rust,0,.20))
    save('ps_cast_face',colour,height*.60,rough,metal,(40,40));STATS['ps_cast_face']={**stats,'texturePixels':[n,n],'mapping':'radial face and eight bolt centres'}
    # The remaining foundry pieces and fins use the accepted valve's fine coating recipe.
    for name,base in (('ps_pump',CAST),('ps_motor',MOTOR)):
        shape=(1024,1024);patch=V.field(rng,shape,22.)
        edge=np.clip(patch-.8,0,1)*.60
        colour,height,rough,metal,stats=coating(rng,shape,base,edge,np.zeros(shape),np.zeros(shape),(8,8))
        save(name,colour,height*.55,rough,metal,(8,8));STATS[name]=stats
    return rng

def refresh_casting_materials():
    skin('ps_cast_skin',CAST,15.,30.,17.5,310731)
    skin('ps_motor_skin',MOTOR,-46.5,.5,14.8,310732)
    outlet_material()
    return casting_faces_and_fins()

def materials():
    R.materials()
    rng=refresh_casting_materials()
    # Smoothly machined bores and flange lips must not inherit rough casting pits.
    shape=(2048,1024);fine=V.field(rng,shape,1.1);broad=V.field(rng,shape,(12.,2.))
    colour=np.array((112.,119.,117.))[None,None,:]*(1+.016*fine[...,None]+.012*broad[...,None])
    save('ps_bore',colour,np.zeros(shape),np.clip(.34+.025*fine+.025*broad,.24,.46),np.full(shape,.86),(19.,math.tau*6.1))
    shape=(2048,2048);yy,xx=np.mgrid[:2048,:2048];y=(xx/2047-.5)*17;z=(.5-yy/2047)*17;r=np.hypot(y,z)
    fine=V.field(rng,shape,.8);broad=V.field(rng,shape,25.);tooling=np.sin(r*math.tau/.09)
    oxide=V.smooth(broad,1.25,2.0)*np.exp(-((r-7.55)/.25)**2)*.38
    colour=np.array((126.,132.,128.))[None,None,:]*(1+.026*broad[...,None]+.012*tooling[...,None])
    colour=V.blend(colour,(66,43,26),oxide)
    save('ps_lip',colour,.00020*tooling+.00008*fine,np.clip(.29+.035*fine+.028*tooling+.24*oxide,.20,.65),np.clip(.90-.7*oxide,.2,.9),(17,17))
    STATS['ps_lip']={'texturePixels':[2048,2048],'mapping':'radial machined annulus'}
    (B.OUT/'valve-finish-stats.json').write_text(json.dumps(STATS,indent=2)+'\n')

ORIGINAL=R.candidate
def candidate():return finish_mesh(ORIGINAL())

def main():
    R.archive();B.candidate=candidate;B.materials=materials
    repair='--repair-outlet' in sys.argv
    sys.argv=[sys.argv[0],'--refine']+(['--geometry-only'] if '--geometry-only' in sys.argv or repair else [])
    B.main()
    if repair:
        outlet_material();R.atlas('ps_guard',(169,124,37),.58)
        stats=json.loads((B.OUT/'valve-finish-stats.json').read_text());stats.update(STATS)
        (B.OUT/'valve-finish-stats.json').write_text(json.dumps(stats,indent=2)+'\n')
    data=json.loads((B.OUT/'manifest.json').read_text())
    data.update(realismRevision=4,materialBenchmark='accepted valve surface recipe with reduced broad mottling',
                previousProposalArchive='output/asset-improvement-20261030/pump-skid/revision-01',
                finishStats='output/asset-improvement-20261030/pump-skid/valve-finish-stats.json',
                newDetails=['separate unwrapped 4K casting and motor coatings',
                            'radial casing-cap UVs with actual bolt-centred grime and wear',
                            'machined bore and concentric-tooling lip with separate PBR finish',
                            'accepted valve recipe for pits, orange peel, paint loss, dust and grease',
                            'formed perforated guard, rounded connected motor mounts and fabricated controller'])
    for p in (B.OUT/'manifest.json',HERE/'candidate.json'):p.write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':main()
