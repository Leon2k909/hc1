"""Review staged floor-use data with collision checks and matched CPU materials.

The images are isolated floor-plane previews, not s&box screenshots. Existing
colour/normal/contact textures are read unchanged. Native lightmaps, shader
compilation, texture compression and temporal performance remain untested.
"""
import json
from pathlib import Path
import zlib

import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

import lowtide_concrete_wear as C
import lowtide_warehouse_floor_review as R

OUT=C.OUT
VIEWS={
    'receiving':dict(eye=(.6,-2.8,1.5),target=(0,1.2,0),fov=66,origin_plan=(665,-40)),
    'loading':dict(eye=(.5,-3.1,2.2),target=(0,1.3,0),fov=65,origin_plan=(780,800)),
    'grazing':dict(eye=(-.5,-2.2,.50),target=(0,1.7,0),fov=63,origin_plan=(655,240)),
}


def noise(p):
    cell=np.floor(p); f=p-cell; f=f*f*(3-2*f)
    results=[]
    for offset in ((0,0),(1,0),(0,1),(1,1)):
        h=np.sin((cell+offset)@np.array((127.1,311.7)))*43758.5453
        results.append(h-np.floor(h))
    a=results[0]*(1-f[:,0])+results[1]*f[:,0]
    b=results[2]*(1-f[:,0])+results[3]*f[:,0]
    return a*(1-f[:,1])+b*f[:,1]


def linear_mip(chain,uv,dx,dy):
    shape=np.array((chain[0].shape[1],chain[0].shape[0]))
    rho=np.maximum(np.linalg.norm(dx*shape,axis=-1),np.linalg.norm(dy*shape,axis=-1))
    lod=np.clip(np.log2(np.maximum(rho,1)),0,len(chain)-1)
    low=np.floor(lod).astype(int); weight=lod-low
    out=np.zeros((len(uv),chain[0].shape[-1]),np.float32)
    for level in np.unique(low):
        take=low==level
        a=R.bilinear(chain[level],uv[take],False)
        b=R.bilinear(chain[min(level+1,len(chain)-1)],uv[take],False)
        out[take]=a*(1-weight[take,None])+b*weight[take,None]
    return out


def atlas(plane,side=1):
    # plane is engine north, absolute plan east, in inches.
    uv=np.stack(((plane[:,1]-240)/1520,1-(plane[:,0]+400)/1550),-1)
    uv[:,0]=np.clip(uv[:,0],.5/2048,.5-.5/2048)+(0 if side==1 else .5)
    uv[:,1]=np.clip(uv[:,1],.5/2048,1-.5/2048)
    return uv


def eligible(plane,z=0,normal_z=1):
    return (np.abs(z)<.1)&(normal_z>.98)&(plane[:,1]>240)&(plane[:,1]<1000)&(plane[:,0]>-400)&(plane[:,0]<1150)


def material(plane,px,py,maps,candidate,side=1,z=0,normal_z=1):
    crc=zlib.crc32(('lowtide_east' if side==1 else 'lowtide_west').encode())
    offset=np.array(((crc&0xffff)/65535*7,((crc>>16)&0xffff)/65535*7))
    uv=np.stack((plane[:,1]*side/256+offset[0],1-plane[:,0]/256-offset[1]),-1)*3.2512
    dx=np.stack((px[:,1]*side,-px[:,0]),-1)/256*3.2512
    dy=np.stack((py[:,1]*side,-py[:,0]),-1)/256*3.2512
    color=R.sample(maps['color'],uv,dx,dy,True)
    raw=R.unit(R.sample(maps['normal'],uv,dx,dy,True)*2-1)
    normal=R.unit(np.stack((raw[:,1],-raw[:,0]*side,raw[:,2]),-1))
    rough=R.sample(maps['rough'],uv,dx,dy,True)[:,0]
    ground=np.stack((plane[:,0],-plane[:,1]*side),-1)
    patina=noise(ground/170)*.65+noise(ground/47+11.4)*.35
    color*=(.82+.21*patina[:,None])
    rough=np.clip(rough+(patina-.5)*.18,0,1)
    lookup=atlas(plane,side)
    ax=np.stack((px[:,1]/1520,-px[:,0]/1550),-1)
    ay=np.stack((py[:,1]/1520,-py[:,0]/1550),-1)
    contact=linear_mip(maps['contact'],lookup,ax,ay)
    scope=eligible(plane,z,normal_z)
    ao=np.where(scope,(.15+contact[:,0]*.85)*(.55+contact[:,1]*.45),1)
    if candidate:
        use=linear_mip(maps['use'],lookup,ax,ay)*scope[:,None]
        color=color*(1-use[:,0,None]*.30)+np.array((.145,.132,.112))*use[:,0,None]*.30
        color*=1-use[:,1,None]*.50
        rough=np.where(scope,np.clip(rough+use[:,0]*.12+use[:,1]*.06-use[:,2]*.14,np.minimum(rough,.44),np.maximum(rough,.95)),rough)
        normal=R.unit(normal*(1-use[:,2,None]*.22)+np.array((0,0,1))*use[:,2,None]*.22)
    return color,normal,rough,ao


def render(spec,maps,candidate):
    width,height=1200,820
    pos,mask,eye=R.ray_floor(spec,width,height)
    east,north=spec['origin_plan']
    plane=np.stack((pos[...,0]/.0254+north,-pos[...,1]/.0254+east),-1)
    py,px=np.gradient(plane,axis=(0,1))
    mask&=eligible(plane.reshape(-1,2)).reshape(height,width)
    result=np.full((height,width,3),.16,np.float32)
    for row in range(0,height,64):
        active=mask[row:row+64]
        if not active.any(): continue
        data=material(plane[row:row+64][active],px[row:row+64][active],py[row:row+64][active],maps,candidate)
        result[row:row+64][active]=R.shade(*data,R.unit(eye-pos[row:row+64][active]))
    image=Image.fromarray(np.rint(np.clip(result,0,1)*255).astype(np.uint8))
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,height-28,width,height),fill=(24,25,26))
    draw.text((12,height-20),'OFFLINE MATERIAL PREVIEW | '+('STAGED USE/WORN CONCRETE' if candidate else 'CURRENT CONCRETE')+
              ' | floor only; matched CPU light; not an engine capture',fill=(220,220,215))
    return image


def diagrams(manifest,mask):
    bounds=manifest['settings']['bounds_plan_inches']
    size=(760,1550)
    for side in (1,-1):
        detail=manifest['details'][str(side)]
        occupied=C.occupancy(detail['collision_shapes'],bounds,size)
        half=mask[:,:1024] if side==1 else mask[:,1024:]
        use=np.asarray(Image.fromarray(np.rint(half*255).astype(np.uint8)).resize(size,Image.Resampling.BILINEAR),float)/255
        # This is a data diagram, with colours explicitly keyed by channel.
        base=np.ones((size[1],size[0],3))*np.array((.89,.88,.84))
        base=base*(1-use[:,:,0,None]*.4)+np.array((.57,.43,.26))*use[:,:,0,None]*.4
        base=base*(1-use[:,:,2,None]*.55)+np.array((.32,.59,.62))*use[:,:,2,None]*.55
        base*=1-use[:,:,1,None]*.80
        base[occupied]=(.16,.18,.18)
        image=Image.fromarray(np.rint(base*255).astype(np.uint8))
        draw=ImageDraw.Draw(image)
        for route in detail['routes']:
            points=C.to_pixel(np.asarray(route['points'])[::12],bounds,size)
            draw.line([tuple(p) for p in points],fill=(230,142,65),width=1)
        draw.rectangle((0,0,760,50),fill=(25,28,29))
        draw.text((12,10),f'NUMERICAL WEAR LAYOUT / {"EAST" if side==1 else "WEST"} / saved collision in charcoal',fill=(224,224,218))
        draw.text((12,29),'brown: dust | teal: traffic polish | dark: rubber | orange: checked path centre',fill=(224,224,218))
        image.save(OUT/'preview'/f'layout-{side:+}.png')


def verify(manifest,mask):
    assert all(C.sha(C.ROOT/p)==digest for p,digest in manifest['sources'].items())
    assert all(C.sha(C.ROOT/p)==digest for p,digest in manifest['protected'].items())
    assert all(C.sha(OUT/'stage'/p)==digest for p,digest in manifest['staged_files'].items())
    assert mask.shape==(2048,2048,3)
    reports=[]
    for side in (1,-1):
        detail=manifest['details'][str(side)]
        shapes,_=C.collision(side,manifest['settings'])
        assert shapes==detail['collision_shapes']
        occupied=C.occupancy(shapes,manifest['settings']['bounds_plan_inches'],(1024,2048))
        data=mask[:,:1024] if side==1 else mask[:,1024:]
        assert np.max(data[occupied])==0
        assert np.max(data[[0,-1]])==0 and np.max(data[:,[0,-1]])==0
        clearance=ndimage.distance_transform_edt(~occupied,sampling=(1550/2048,760/1024))
        for route in detail['routes']:
            value=C.values(clearance,np.asarray(route['points']),manifest['settings']['bounds_plan_inches'])
            assert value.min()>=route['clearance']-1.5
            reports.append(dict(side=side,name=route['name'],samples=len(value),minimum_clearance=float(value.min())))
    # Texel-centre tests catch atlas orientation, half selection and mirroring errors.
    rng=np.random.default_rng(738)
    pixels=rng.integers(1,1023,(4096,2)); pixels[:,1]=rng.integers(1,2047,len(pixels))
    plan=C.to_plan(pixels,manifest['settings']['bounds_plan_inches'],(1024,2048))
    plane=plan[:,::-1]
    for side in (1,-1):
        uv=atlas(plane,side)
        got=R.bilinear(mask,uv,False)
        wanted=mask[pixels[:,1],pixels[:,0]+(0 if side==1 else 1024)]
        assert np.allclose(got,wanted,atol=1e-6)
    outside=np.array(((0,239.9),(0,1000.1),(-400.1,620),(1150.1,620)))
    assert not eligible(outside).any()
    assert not eligible(plane,z=176).any() and not eligible(plane,normal_z=0).any()
    assert eligible(plane).all()
    # Exercise the actual CPU material gate with unusually smooth inputs, so an
    # accidental global roughness clamp cannot pass merely because use is zero.
    constant=lambda value:[np.broadcast_to(np.asarray(value,np.float32),(4,4,len(value))).copy()]
    maps=dict(color=constant([.18,.17,.15]),normal=constant([.55,.48,.99]),rough=constant([.22]),
              contact=constant([.8,.8,.8]),use=constant([.8,.8,.8]))
    scope_cases=0
    for points,z,nz in ((outside,0,1),(plane[:16],176,1),(plane[:16],0,0)):
        dx=np.tile((.04,0),(len(points),1)); dy=np.tile((0,.04),(len(points),1))
        before=material(points,dx,dy,maps,False,z=z,normal_z=nz)
        after=material(points,dx,dy,maps,True,z=z,normal_z=nz)
        assert all(np.allclose(a,b,atol=1e-7) for a,b in zip(before,after))
        scope_cases+=len(points)
    maps['use']=constant([0,0,0])
    untouched_samples=0
    for baseline in (.22,.98):
        maps['rough']=constant([baseline])
        points=plane[:16]
        dx=np.tile((.04,0),(len(points),1)); dy=np.tile((0,.04),(len(points),1))
        before=material(points,dx,dy,maps,False)
        after=material(points,dx,dy,maps,True)
        assert all(np.allclose(a,b,atol=1e-7) for a,b in zip(before,after))
        untouched_samples+=len(points)
    assert C.staged_shader()==(OUT/'stage'/C.SHADER).read_text()
    # Reverse each scoped slot change and require all other VMDL bytes to match.
    for remap in manifest['remaps']:
        source=C.ROOT/'Assets'/remap['model']; staged=OUT/'stage'/remap['model']
        assert staged.read_bytes().replace(remap['after'].encode(),remap['before'].encode())==source.read_bytes()
    return dict(status='offline_data_geometry_scope_and_atlas_checks_passed',
        manifest_sha256=C.sha(OUT/'manifest.json'),reviewer_sha256=C.sha(Path(__file__)),
        shared_renderer_sha256=C.sha(C.ROOT/'Tools/lowtide_warehouse_floor_review.py'),
        protected_live_files=len(manifest['protected']),collision_routes=reports,
        path_samples=sum(r['samples'] for r in reports),atlas_texel_samples=8192,
        occupied_and_outer_edge_mask_values_zero=True,other_surface_scope_excluded=True,
        complete_material_scope_samples=scope_cases,
        untouched_floor_material_samples=untouched_samples,
        original_shader_preserved_by_reversible_insertions=True,exact_material_slot_remaps=2,
        native_checks='Not run; user requested offline work')


def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    mask=np.asarray(Image.open(OUT/'stage'/C.MASK),float)/255
    report=verify(manifest,mask)
    preview=OUT/'preview'; preview.mkdir(exist_ok=True)
    diagrams(manifest,mask)
    base=C.ROOT/'Assets/materials/lowtide/interior'
    maps={key:R.mips(base/f'concrete_{suffix}.png',key=='color') for key,suffix in (('color','color'),('normal','normal'),('rough','rough'))}
    maps['contact']=R.mips(base/'floor_contact.png')
    maps['use']=R.mips(OUT/'stage'/C.MASK)
    for candidate in (False,True):
        label='candidate' if candidate else 'before'
        for name,spec in VIEWS.items():
            render(spec,maps,candidate).save(preview/f'{name}-{label}.png')
            print(f'Rendered {label} {name}',flush=True)
    C.write(OUT/'offline-verification.json',json.dumps(report,indent=2)+'\n')
    C.write(preview/'provenance.json',json.dumps(dict(kind='CPU material comparison and collision/use-mask diagrams',native_engine_capture=False,
        manifest_sha256=C.sha(OUT/'manifest.json'),renderer_sha256=C.sha(Path(__file__)),
        shared_renderer_sha256=report['shared_renderer_sha256'],views=VIEWS,
        source_colour_pixels_preserved=True,geometry_changes=0,
        limitations=['Isolated floor plane: cargo and architecture are absent from material previews',
                    'Native shader compilation, lightmaps, texture compression and temporal filtering are not tested',
                    'No measured performance or vehicle-route claim'],
        previews={p.name:C.sha(p) for p in sorted(preview.glob('*.png'))}),indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='collision_routes'},indent=2))


if __name__=='__main__': main()
