"""Object-specific aged coatings and manufactured surface detail for the valve."""
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import gaussian_filter

BODY=(39.,54.,61.)
RED=(105.,26.,20.)

def field(rng,shape,sigma):
    a=gaussian_filter(rng.normal(0,1,shape),sigma,mode='wrap')
    return a/max(float(a.std()),1e-9)

def smooth(a,lo,hi):
    t=np.clip((a-lo)/(hi-lo),0,1);return t*t*(3-2*t)

def blend(a,b,mask):return a*(1-mask[...,None])+np.asarray(b)*mask[...,None]

def cast_offset(h,a,lo,hi):
    t=(h-lo)/(hi-lo);fade=math.sin(math.pi*t)**2
    waviness=.025*math.sin(a*5+h*.63)+.011*math.sin(a*13-h*1.41)
    seam=.026*math.exp(-(math.sin(a)/.10)**2)
    return fade*(waviness+seam)

def finish_mesh(model):
    # Flange-face UVs follow the actual vertical face, including bolt positions.
    for i,(points,normal) in enumerate(model.polygons.get('vv_flange',[])):
        model.polygon_uvs[('vv_flange',i)]=[(.5+p[1]/27.,.5+(p[2]-13.)/27.) for p in points]
    for i,(points,normal) in enumerate(model.polygons.get('vv_stem',[])):
        model.polygon_uvs[('vv_stem',i)]=[(math.atan2(p[2]-13.,p[0])/math.tau+.5,(-p[1]-14.1)/11.9) for p in points]
    for i,(points,normal) in enumerate(model.polygons.get('vv_bore',[])):
        model.polygon_uvs[('vv_bore',i)]=[(math.atan2(p[2]-13.,p[1])/math.tau+.5,(p[0]+11.9)/23.8) for p in points]

def coating(rng,shape,base,edge,grease,dust,tile):
    fine=field(rng,shape,.8);grain=field(rng,shape,2.1);orange=field(rng,shape,6.)
    broad=field(rng,shape,45.);patch=field(rng,shape,(5.,13.));pits=smooth(-grain,1.2,2.4)
    chip=smooth(edge*2.4+patch*.52+grain*.13,1.9,2.13)
    fringe=smooth(gaussian_filter(chip,2.1,mode='wrap'),.04,.4)*(1-chip)
    oxidation=smooth(broad*.6+patch*.5,1.,1.7)*np.clip(edge,.0,1.)*.48
    grease=np.clip(grease*(.72+.20*broad+.12*orange),0,.85)
    dusty=np.clip(dust*(.9+.18*broad),0,.34)
    colour=np.asarray(base)[None,None,:]*(1+.10*broad[...,None]+.035*orange[...,None]+.016*grain[...,None])
    colour=blend(colour,(67,42,25),fringe*.55+oxidation*.6)
    exposed=np.stack((109+9*grain,111+8*grain,104+6*grain),axis=-1)
    colour=blend(colour,exposed,chip)
    colour=blend(colour,(90,79,62),dusty)
    colour=blend(colour,(22,24,21),grease)
    height=.0032*grain+.0025*orange+.0006*fine-.010*pits-.0075*chip
    rough=np.clip(.49+.065*broad+.035*grain+.11*pits+.18*dusty-.23*grease-.14*chip,.18,.9)
    metal=np.clip(.025+.80*chip-.25*oxidation,0,.86)
    return colour,height,rough,metal,{'chipFraction':float((chip>.5).mean()),'roughnessRange':[float(rough.min()),float(rough.max())],'physicalTileInches':list(tile)}

def create_surfaces(md,mat,AM,write_material):
    md=Path(md);rng=np.random.default_rng(291091);stats={}
    def save(name,colour,height,rough,metal,tile):
        h,w=height.shape
        Image.fromarray(np.clip(colour,0,255).astype(np.uint8)).save(md/(name+'_color.png'))
        AM.BX.save_normal(md/(name+'_normal.png'),AM.normals(height,(w/tile[0],h/tile[1])))
        AM.BX.save_grey(md/(name+'_rough.png'),np.clip(rough,0,1))
        AM.BX.save_grey(md/(name+'_metal.png'),np.clip(metal,0,1))
        write_material(name,f'{mat}/{name}_color.png',f'{mat}/{name}_normal.png',f'{mat}/{name}_rough.png',f'{mat}/{name}_metal.png')
    for name,length,circumference in (('vv_cast',26.6,math.tau*10.6),('vv_bonnet',6.2,math.tau*8.1)):
        n=2048 if name=='vv_cast' else 1024;yy,xx=np.mgrid[:n,:n];u=xx/(n-1);v=1-yy/(n-1);a=v*math.tau
        top=np.clip(-np.sin(a),0,1);bottom=np.clip(np.sin(a),0,1)
        edge=np.exp(-(np.minimum(u,1-u)/.055)**2)
        grease=edge*.55+bottom*.12
        if name=='vv_bonnet':grease+=np.exp(-((u-.88)/.15)**2)*.40
        dust=top**3*.23
        values=coating(rng,(n,n),BODY,edge,grease,dust,(length,circumference))
        colour,height,rough,metal,stats[name]=values
        # A few faint gravity streaks, strongest below the connection shoulders.
        streak=field(rng,(n,n),(42.,2.5));stain=smooth(streak,1.25,2.2)*bottom*.12
        colour=blend(colour,(55,40,28),stain)
        save(name,colour,height*.62,rough,metal,(length,circumference))
    n=2048;yy,xx=np.mgrid[:n,:n];y=(xx/(n-1)-.5)*27.;z=(.5-yy/(n-1))*27.;r=np.sqrt(y*y+z*z)
    edges=np.exp(-((r-11.68)/.30)**2)+.65*np.exp(-((r-8.3)/.22)**2)
    grease=np.zeros((n,n));rust=np.zeros((n,n))
    for k in range(8):
        a=k*math.tau/8+math.pi/8;cy=math.cos(a)*10.4;cz=math.sin(a)*10.4
        d=np.sqrt((y-cy)**2+(z-cz)**2)
        edges+=np.exp(-((d-1.02)/.29)**2)*.9
        grease+=np.exp(-(d/1.42)**2)*.65
        rust+=np.exp(-((y-cy)/.32)**2)*np.exp(-(cz-z)/2.2)*((z<cz)&(z>cz-5.))*.12
    values=coating(rng,(n,n),BODY,np.clip(edges,0,1.5),np.clip(grease,0,.85),np.clip(z/13.,0,1)*.13,(27.,27.))
    colour,height,rough,metal,stats['vv_flange']=values
    colour=blend(colour,(76,43,24),np.clip(rust,0,.22));save('vv_flange',colour,height*.60,rough,metal,(27.,27.))
    # Generic packing-collar and spoke coatings share the palette, with small pits.
    for name,base in (('vv_body',BODY),('vv_red',RED)):
        shape=(1024,1024);patch=field(rng,shape,22.)
        values=coating(rng,shape,base,np.clip(patch-.8,0,1)*.6,np.zeros(shape)+.07,np.zeros(shape),(8.,8.))
        colour,height,rough,metal,stats[name]=values
        scale=.32 if name=='vv_red' else .6
        save(name,colour,height*scale,rough,metal,(8.,8.))
    # Unwrapped grip: chipped shoulders, rubbed paint, and irregular primer halos.
    shape=(1024,2048);yy,xx=np.mgrid[:shape[0],:shape[1]];v=1-yy/(shape[0]-1)
    contact=np.exp(-((v-.16)/.075)**2)+.7*np.exp(-(np.minimum(v,1-v)/.045)**2)
    grease=np.exp(-((v-.45)/.12)**2)*.13
    values=coating(rng,shape,RED,contact,grease,np.zeros(shape),(math.tau*11.05,math.tau*1.18))
    colour,height,rough,metal,stats['vv_wheel']=values
    chips=np.clip((metal-.025)/.8,0,1)
    save('vv_wheel',colour,height*.32-.0048*chips,rough,metal,(math.tau*11.05,math.tau*1.18))
    # Machined hardware has directional scratches, tarnish and uneven polish.
    shape=(1024,1024);yy,xx=np.mgrid[:1024,:1024];fine=field(rng,shape,.6);broad=field(rng,shape,23.)
    brushing=np.sin(yy*.83+gaussian_filter(fine,3)*.8)
    for name,base,mean in (('vv_metal',(128.,132.,129.),.31),('vv_bolt',(91.,97.,95.),.43)):
        oxide=smooth(field(rng,shape,2.5),1.75,2.6)*.8
        colour=np.array(base)[None,None,:]*(1+.045*broad[...,None]+.035*brushing[...,None])
        colour=blend(colour,(61,40,26),oxide)
        rough=np.clip(mean+.10*broad+.055*fine+.3*oxide,.2,.87)
        scale=.25 if name=='vv_metal' else .5
        save(name,colour,(.00045*fine+.0003*brushing-.0015*oxide)*scale,rough,np.clip(.88-.75*oxide,.05,.88),(8.,8.))
    # The bored throat is machined smooth, with fine finish variation rather than cast pits.
    shape=(1024,1024);fine=field(rng,shape,1.1);broad=field(rng,shape,(10.,2.))
    colour=np.array((112.,119.,117.))[None,None,:]*(1+.016*fine[...,None]+.012*broad[...,None])
    save('vv_bore',colour,np.zeros(shape),np.clip(.34+.025*fine+.025*broad,.24,.46),np.full(shape,.86),(math.tau*5.,23.8))
    # Axial stem mapping localizes grease near the packing; the thread stays legible.
    shape=(1024,512);yy,xx=np.mgrid[:shape[0],:shape[1]];axial=1-yy/(shape[0]-1)
    fine=field(rng,shape,.7);broad=field(rng,shape,(12.,3.))
    grease=np.clip(np.exp(-(axial/.34)**2)*(.65+.18*broad),0,.9)
    colour=np.array((135.,139.,137.))[None,None,:]*(1+.035*fine[...,None]);colour=blend(colour,(27,28,23),grease)
    rough=np.clip(.28+.055*fine+.08*broad-.12*grease,.16,.72)
    save('vv_stem',colour,np.zeros(shape),rough,np.clip(.9-.65*grease,.15,.9),(math.tau*1.1,11.9))
    # A scuffed metal ID plate; no hand-painted shadows in the label.
    label=Image.new('RGB',(512,256),(153,157,148));draw=ImageDraw.Draw(label)
    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',44);draw.text((256,70),'HV-07',font=font,anchor='mm',fill=(25,30,29))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',27)
    draw.text((256,140),'COOLING INLET',font=font,anchor='mm',fill=(32,37,36));draw.text((256,194),'OPEN  /  CLOSE',font=font,anchor='mm',fill=(32,37,36))
    array=np.asarray(label).astype(float);noise=field(rng,(256,512),1.2);array*=1+.026*noise[...,None]
    Image.fromarray(np.clip(array,0,255).astype(np.uint8)).save(md/'label.png')
    write_material('vv_label',f'{mat}/label.png',rough='[0.47 0.47 0.47 0]',metal=.65)
    return stats
