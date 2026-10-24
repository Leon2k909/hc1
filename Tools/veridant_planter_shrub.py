"""The garden table's single planter: grounded photographic shrub and real soil.

The source mesh was read from the installed beech shrub's default material group
through the editor. Preserve its authored UVs, normals and branch geometry.
"""
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Sources/Veridant/planter-shrub-v1/beech-source.json'
PREFIX='materials/veridant/planter-shrub-v1'
SOIL='vr_garden_planter_soil'
LEAVES='vr_garden_planter_beech'


def build_into(model,base=(-470.,740.,148.)):
    record=json.loads(SOURCE.read_text())
    model.material_overrides.update({LEAVES:record['Material'],SOIL:f'{PREFIX}/soil.vmat'})
    model.tile_overrides.update({LEAVES:16.,SOIL:16.})
    angle=math.radians(24);c,s=math.cos(angle),math.sin(angle)
    rotation=np.array(((c,-s,0),(s,c,0),(0,0,1)))
    vertices=np.array([v['Position'] for v in record['Vertices']])@rotation.T*.43
    normals=np.array([v['Normal'] for v in record['Vertices']])@rotation.T
    # Native world to the generator's east/north plan axes.
    vertices=np.column_stack((-vertices[:,1],vertices[:,0],vertices[:,2]))
    vertices+=np.array(base)+np.array((0.,0.,-1.0))
    normals=np.column_stack((-normals[:,1],normals[:,0],normals[:,2]))
    uv=np.array([(v['UV'][0],1-v['UV'][1]) for v in record['Vertices']])
    for ids in np.array(record['Indices']).reshape(-1,3):
        model.polygon(LEAVES,vertices[ids],normals=normals[ids],uv=uv[ids])
    e,n,z=base

    def height(x,y):return z+.20+.48*math.exp(-(x*x+y*y)/140)+.075*math.sin(x*.55)*math.cos(y*.46)

    grid=np.linspace(-23.98,23.98,11)
    for x0,x1 in zip(grid,grid[1:]):
        for y0,y1 in zip(grid,grid[1:]):
            points=[np.array((e+x,n+y,height(x,y))) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
            model.polygon(SOIL,points,uv=[((p[0]-e)/16+.31,(p[1]-n)/16+.19) for p in points])
    # Small irregular pieces of mulch give the base contact and scale.
    rng=np.random.default_rng(17032)
    for _ in range(44):
        x,y=rng.uniform(-22.8,22.8,2);a=rng.uniform(0,math.tau)
        length=rng.uniform(.30,.82);width=rng.uniform(.12,.32)
        along=np.array((math.cos(a),math.sin(a),0.))*length
        across=np.array((-math.sin(a),math.cos(a),0.))*width
        centre=np.array((e+x,n+y,height(x,y)+.055))
        points=[centre-along*.5-across*.35,centre+along*.4-across*.5,
                centre+along*.5+across*.3,centre-along*.3+across*.5]
        model.polygon(SOIL,points,uv=[(0,0),(.1,0),(.1,.04),(0,.04)])
    assert np.isfinite(vertices).all()
    return model


def write_materials(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(59032);size=512

    def noise(sigma):
        values=gaussian_filter(rng.normal(size=(size,size)),sigma,mode='wrap')
        return values/max(values.std(),1e-8)

    broad=noise(18);clods=noise(2.2);grain=noise(.55)
    lum=1+.11*broad+.09*clods+.045*grain
    colour=np.array((73.,55.,37.))*lum[...,None]
    Image.fromarray(np.clip(colour,0,255).astype(np.uint8)).save(folder/'soil_color.png')
    height=.022*clods+.006*grain
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(32/size)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(32/size)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1)[...,None]
    Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype(np.uint8)).save(folder/'soil_normal.png')
    Image.fromarray(np.clip((.91+.025*clods)*255,0,255).astype(np.uint8)).save(folder/'soil_rough.png')
    (folder/'soil.vmat').write_text('// Tools/veridant_planter_shrub.py\n"Layer0"\n{\n'
        '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
        '    g_flRoughnessScaleFactor "1"\n    g_flMetalness "0"\n'
        f'    TextureColor "{PREFIX}/soil_color.png"\n'
        f'    TextureNormal "{PREFIX}/soil_normal.png"\n'
        f'    TextureRoughness "{PREFIX}/soil_rough.png"\n'
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
        '    g_vColorTint "[1 1 1 1]"\n    g_flModelTintAmount "1"\n}\n')
