"""Original RAZED objective prop. Rebuild geometry/UVs; preserves the generated albedo atlas.
Units are Source inches, Z up. This is a fictional sealed game prop, not functional hardware.
"""
from pathlib import Path
import json, math, uuid

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'Assets/Weapons/C4/field_device'
DEST.mkdir(parents=True, exist_ok=True)
vertices, texcoords, faces = [], [], []

def face(points, uv):
    start = len(vertices) + 1
    vertices.extend(points)
    texcoords.extend((u, 1-v) for u,v in uv)
    for i in range(1,len(points)-1):
        faces.append((start,start+i,start+i+1))

TILES = {'metal':(.02,.02,.48,.48), 'cloth':(.52,.02,.98,.48), 'rubber':(.52,.52,.98,.98), 'panel':(.003,.503,.497,.997)}

def box(center, size, material='metal', bevel=.12, top_uv=None):
    x,y,z=center; sx,sy,sz=[v/2 for v in size]; b=min(bevel,sx*.4,sy*.4,sz*.4)
    # Chamfered rectangular rings with a real bevel along all edges.
    def ring(w,h,zz):
        return [(x+a,y+c,z+zz) for a,c in [(-w+b,-h), (w-b,-h), (w,-h+b), (w,h-b), (w-b,h),(-w+b,h),(-w,h-b),(-w,-h+b)]]
    rings=[ring(sx-b,sy-b,-sz), ring(sx,sy,-sz+b),ring(sx,sy,sz-b),ring(sx-b,sy-b,sz)]
    u0,v0,u1,v1=TILES[material]
    def planar(p, bounds=None):
        a,c,d,e = bounds or (u0,v0,u1,v1)
        return (a+(sy-(p[1]-y))/(2*sy)*(d-a), c+(sx-(p[0]-x))/(2*sx)*(e-c))
    face(list(reversed(rings[0])), [planar(p) for p in reversed(rings[0])])
    face(rings[-1], [planar(p,top_uv) for p in rings[-1]])
    for bottom,top in zip(rings,rings[1:]):
        for i in range(8):
            j=(i+1)%8
            face([bottom[i],bottom[j],top[j],top[i]],[(u0,v0),(u1,v0),(u1,v1),(u0,v1)])

def cylinder(center,radius,height,segments=16,material='metal'):
    x,y,z=center; u0,v0,u1,v1=TILES[material]
    bottom=[(x+radius*math.cos(i*math.tau/segments),y+radius*math.sin(i*math.tau/segments),z-height/2) for i in range(segments)]
    top=[(a,b,z+height/2) for a,b,_ in bottom]
    uv=[((u0+u1)/2+(u1-u0)*.45*math.cos(i*math.tau/segments),(v0+v1)/2+(v1-v0)*.45*math.sin(i*math.tau/segments)) for i in range(segments)]
    face(top,uv);face(list(reversed(bottom)),list(reversed(uv)))
    for i in range(segments):
        j=(i+1)%segments
        face([bottom[i],bottom[j],top[j],top[i]],[(u0,v0),(u1,v0),(u1,v1),(u0,v1)])

# Reinforced tray, sealed canvas-covered modules, rubber bumpers, woven retaining bands.
box((0,0,.35),(12.4,11.4,.7),'rubber',.2)
for y in [-3.65,0,3.65]: box((0,y,1.65),(11.8,3.5,2.5),'cloth',.25)
for x in [-4.8,4.8]:
    box((x,0,2.97),(1.15,11.3,.25),'rubber',.06)
    for y in [-5.4,5.4]: box((x,y,1.6),(1.15,.3,2.9),'rubber',.06)
    box((x,-4.5,3.13),(1.45,1.6,.25),'metal',.07)
    box((x,-4.5,3.28),(.65,.9,.12),'rubber',.03)

# Central electronics enclosure; the control surface is mapped once, upright to the carrier.
box((0,0,3.25),(9.3,7.6,1.05),'metal',.2)
box((0,0,3.82),(8.9,7.25,.2),'panel',.065,top_uv=TILES['panel'])

# Key caps lift the exact corresponding atlas regions into real geometry.
# Atlas bottom-left panel: keys span u=.122..377, v=.67..928.
panel_x,panel_y=8.9,7.25
for row in range(4):
    for col in range(3):
        ua=.123+col*.091; ub=ua+.069
        va=.674+row*.066; vb=va+.050
        cy=(.25-(ua+ub)/2)/.494*panel_y
        cx=(.75-(va+vb)/2)/.494*panel_x
        box((cx,cy,4.02),((vb-va)/.494*panel_x,(ub-ua)/.494*panel_y,.30),'rubber',.09,top_uv=(ua,va,ub,vb))

# Corner fasteners and shallow engraved slots.
for x in [-4.13,4.13]:
    for y in [-3.28,3.28]:
        cylinder((x,y,3.99),.18,.12)
        box((x,y,4.061),(.21,.035,.015),'rubber',.003)

obj = ['# Original RAZED Field Unit 04', 'o field_device', 'usemtl field_device']
# ModelDoc's OBJ importer maps Y-up OBJ (y,z,x) back to Source (x,y,z).
obj += ['v %.6f %.6f %.6f' % (v[1],v[2],v[0]) for v in vertices]
obj += ['vt %.6f %.6f' % t for t in texcoords]
obj += ['f '+' '.join(f'{i}/{i}' for i in f) for f in faces]
(DEST/'field_device.obj').write_text('\n'.join(obj)+'\n')
(DEST/'field_device.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{
 rootNode = {
  _class = "RootNode"
  children = [
   { _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [] use_global_default = true global_default_material = "weapons/c4/field_device/field_device.vmat" } ] },
   { _class = "RenderMeshList" children = [ { _class = "RenderMeshFile" filename = "weapons/c4/field_device/field_device.obj" import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" } ] }
  ]
 }
}
''')
(DEST/'field_device.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 TextureColor "weapons/c4/field_device/field_device_color.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "materials/default/default_rough.tga"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_flRoughnessScale "0.75"
 g_flMetalness "0.15"
}
''')
print(f'Built original field device: {len(vertices)} vertices, {len(faces)} triangles')
