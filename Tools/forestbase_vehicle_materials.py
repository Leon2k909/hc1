"""Locally authored Forest Base vehicle coatings, canvas and unit stencils."""
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image, ImageDraw, ImageFont
import forestbase_materials as M
import map_kit as K


def main():
    n=1024; rng=np.random.default_rng(66703)
    y,x=np.mgrid[:n,:n]; fine=rng.normal(size=(n,n))
    stains=gaussian_filter(fine,20,mode='wrap'); stains/=stains.std()
    grain=gaussian_filter(fine,.65,mode='wrap')
    specs=[('vehicle_paint',(65,75,54),.58,.03),
           ('vehicle_metal',(46,49,46),.57,.72),
           ('vehicle_rubber',(25,26,24),.87,0),
           ('vehicle_canvas',(61,70,46),.86,0)]
    for name,base,rough,metal in specs:
        color=np.asarray(base)[None,None,:]*(1+.035*stains+.022*fine)[...,None]
        height=.5+grain*.0015; wear=np.zeros((n,n))
        if name in ('vehicle_paint','vehicle_metal'):
            for _ in range(130):
                xx,yy=rng.integers(0,n,2); length=int(rng.integers(3,38))
                wear[yy,xx:min(n,xx+length)]=rng.uniform(.2,.8)
            color-=wear[...,None]*22; height-=wear*.002
        if name=='vehicle_canvas':
            fold=np.sin(x*.035+np.sin(y*.017)*1.5)+.45*np.sin(x*.076+y*.018)
            weave=np.sin(x*np.pi)*np.cos(y*np.pi/2)
            height+=fold*.006+weave*.0007
            color*= (1+fold*.035)[...,None]
        M.save(name,color,height,np.clip(rough+.025*stains+wear*.12,.4,.96),metal)
        path=M.OUT/f'{name}.vmat'
        K.write_text(path,path.read_text().replace('shaders/complex.shader','shaders/forestbase_vehicle.shader'))
    M.save('vehicle_glass',np.ones((n,n,3))*np.array((18,30,32)),0,.095)
    for index,title in enumerate(('FB / 027','FB / 041')):
        image=Image.new('RGBA',(512,128),(0,0,0,0)); draw=ImageDraw.Draw(image)
        draw.text((18,12),title,font=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',81),fill=(193,190,164,255))
        pixels=np.array(image)
        chips=rng.random((128,512))<.025; pixels[:,:,3][chips]=0
        Image.fromarray(pixels[:,:,:3]).save(M.OUT/f'vehicle_stencil_{index}_color.png')
        Image.fromarray(pixels[:,:,3]).save(M.OUT/f'vehicle_stencil_{index}_alpha.png')
        K.write_text(M.OUT/f'vehicle_stencil_{index}.vmat',f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_ALPHA_TEST "1"
 F_RENDER_BACKFACES "1"
 TextureColor "{M.RESOURCE}/vehicle_stencil_{index}_color.png"
 TextureTranslucency "{M.RESOURCE}/vehicle_stencil_{index}_alpha.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[.74 .74 .74 0]"
 g_flAlphaTestReference ".35"
}}
''')
    print('Forest Base vehicle coatings, woven canvas, glazing and stencils written.')


if __name__=='__main__': main()
