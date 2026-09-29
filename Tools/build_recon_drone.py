"""Build the original RAZED AER-03 recon aircraft and its PBR texture atlas.

Source units (inches), X forward, Z up. No downloaded geometry or textures.
Run from the project with Python, Pillow and NumPy. Outputs are reproducible.
"""
from pathlib import Path
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "Assets/models/recon_drone"
DEST.mkdir(parents=True, exist_ok=True)
ASSET = "models/recon_drone"
RNG = np.random.default_rng(304)

# A painted composite shell, woven carbon, rubber, and a dedicated markings tile.
N = 1024
yy, xx = np.mgrid[:N, :N]
grain = RNG.normal(0, 1.2, (N, N))
rgb = np.zeros((N, N, 3), dtype=np.float32)
rgb[:] = (170, 179, 179)
rgb += grain[:, :, None]
rough = np.full((N, N), 177, dtype=np.float32) + grain * 1.5
weave = ((xx // 5 + yy // 5) % 2) * 5 + np.sin((xx + yy) * .9) * 2
rgb[:512, 512:] = np.stack([32 + weave[:512, 512:]] * 3, -1)
rough[:512, 512:] = 143 + weave[:512, 512:] * 2
rgb[512:, :512] = np.stack([23 + grain[512:, :512]] * 3, -1)
rough[512:, :512] = 221 + grain[512:, :512]
albedo = Image.fromarray(np.uint8(np.clip(rgb, 0, 255)), "RGB")
draw = ImageDraw.Draw(albedo)
for y in (32, 158, 320, 480):
    draw.line((16, y, 496, y), fill=(115, 128, 130), width=2)
    draw.line((16, y + 2, 496, y + 2), fill=(193, 201, 199), width=1)
for x in (20, 492):
    for y in (36, 154, 324, 476):
        draw.ellipse((x-2,y-2,x+2,y+2),fill=(84,96,98))
draw.rectangle((535, 532, 998, 999), fill=(173, 182, 181))
draw.rounded_rectangle((561, 558, 974, 974), radius=16, outline=(90, 105, 108), width=3)
draw.rectangle((562, 560, 973, 592), fill=(226, 133, 45))
font_path = Path("C:/Windows/Fonts/bahnschrift.ttf")
if not font_path.exists():
    font_path = Path("C:/Windows/Fonts/arialbd.ttf")
font = ImageFont.truetype(str(font_path), 68)
small = ImageFont.truetype(str(font_path), 24)
draw.text((592, 644), "AER-03", font=font, fill=(39, 55, 61))
draw.text((594, 740), "RAZED / RECON", font=small, fill=(48, 67, 72))
draw.text((594, 794), "OPTICAL SURVEY UNIT", font=small, fill=(68, 83, 88))
draw.text((594, 914), "03-017  /  NO STEP", font=small, fill=(68, 83, 88))
for x in range(592, 946, 6):
    draw.line((x, 859, x, 889 if x % 4 else 898), fill=(66, 81, 84), width=2)
albedo.save(DEST / "recon_color.png")
Image.fromarray(np.uint8(np.clip(rough,0,255)), "L").save(DEST / "recon_roughness.png")
height = np.asarray(Image.fromarray(np.uint8(np.clip(128+grain*3,0,255))).filter(ImageFilter.GaussianBlur(.7)),dtype=float)
height[:512,512:] += weave[:512,512:] * .4
gy, gx = np.gradient(height)
normal = np.stack((-gx*.012, -gy*.012, np.ones_like(gx)), -1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
Image.fromarray(np.uint8((normal*.5+.5)*255), "RGB").save(DEST / "recon_normal.png")
for name, color in {"lens":(12,35,43), "red":(185,29,19), "green":(22,164,93), "metal":(90,106,114)}.items():
    Image.new("RGB", (32,32), color).save(DEST / f"{name}_color.png")

TILES = {"shell":(.03,.03,.47,.47), "carbon":(.53,.03,.97,.47),
         "rubber":(.03,.53,.47,.97), "marking":(.526,.520,.977,.977)}

def unit(v):
    v=np.asarray(v,dtype=float)
    return v / max(np.linalg.norm(v),1e-9)

class Mesh:
    def __init__(self):
        self.vertices=[]; self.uvs=[]; self.normals=[]; self.faces=[]

    def face(self, pts, tile="shell", material="recon", outward=None, uvs=None, normals=None):
        pts=[np.asarray(p,dtype=float) for p in pts]
        normal=unit(np.cross(pts[1]-pts[0],pts[2]-pts[0]))
        if outward is not None and np.dot(normal,outward)<0:
            pts.reverse()
            if uvs: uvs=list(reversed(uvs))
            if normals is not None: normals=list(reversed(normals))
            normal=-normal
        if uvs is None:
            u0,v0,u1,v1=TILES[tile]
            uvs=[(u0,v1),(u1,v1),(u1,v0),(u0,v0)][:len(pts)]
            if len(pts)>4:
                uvs=[((u0+u1)/2+(u1-u0)*.45*math.cos(i*math.tau/len(pts)),
                      (v0+v1)/2+(v1-v0)*.45*math.sin(i*math.tau/len(pts))) for i in range(len(pts))]
        start=len(self.vertices)+1
        self.vertices.extend(pts); self.uvs.extend(uvs)
        self.normals.extend(normals if normals is not None else [normal]*len(pts))
        for i in range(1,len(pts)-1): self.faces.append((material,(start,start+i,start+i+1)))

    def loft_x(self, sections, tile="shell", segments=32, material="recon"):
        # Sections: x, y-radius, z-radius, z-centre. Smooth radial vertex normals.
        rings=[]
        for x,ry,rz,z in sections:
            rings.append([np.array((x,ry*math.cos(i*math.tau/segments),z+rz*math.sin(i*math.tau/segments))) for i in range(segments)])
        for k in range(len(rings)-1):
            for i in range(segments):
                j=(i+1)%segments
                pts=[rings[k][i],rings[k][j],rings[k+1][j],rings[k+1][i]]
                norms=[]
                for a,b in ((k,i),(k,j),(k+1,j),(k+1,i)):
                    sec=sections[a]; t=b*math.tau/segments
                    lo=max(0,a-1);hi=min(len(sections)-1,a+1)
                    dr=(sections[hi][1]-sections[lo][1])/max(sections[hi][0]-sections[lo][0],.01)
                    norms.append(unit((-dr,math.cos(t),math.sin(t)*sec[1]/max(sec[2],.1))))
                self.face(pts,tile,material,outward=(0,math.cos((i+.5)*math.tau/segments),math.sin((i+.5)*math.tau/segments)),normals=norms)
        self.face(rings[0],tile,material,outward=(-1,0,0))
        self.face(rings[-1],tile,material,outward=(1,0,0))

    def tube(self,a,b,radius,tile="carbon",segments=16,material="recon"):
        a=np.asarray(a,float);b=np.asarray(b,float);axis=unit(b-a)
        u=unit(np.cross(axis,(0,0,1) if abs(axis[2])<.9 else (0,1,0)));v=np.cross(axis,u)
        rings=[[p+radius*(u*math.cos(i*math.tau/segments)+v*math.sin(i*math.tau/segments)) for i in range(segments)] for p in (a,b)]
        for i in range(segments):
            j=(i+1)%segments
            self.face([rings[0][i],rings[0][j],rings[1][j],rings[1][i]],tile,material,outward=rings[0][i]-a)
        self.face(rings[0],tile,material,outward=-axis);self.face(rings[1],tile,material,outward=axis)

    def box(self,center,size,tile="shell",material="recon"):
        c=np.asarray(center);s=np.asarray(size)*.5
        for axis in range(3):
            others=[i for i in range(3) if i!=axis]
            for side in (-1,1):
                pts=[]
                for a,b in ((-1,-1),(1,-1),(1,1),(-1,1)):
                    p=c.copy().astype(float);p[axis]+=s[axis]*side;p[others[0]]+=s[others[0]]*a;p[others[1]]+=s[others[1]]*b;pts.append(p)
                n=np.zeros(3);n[axis]=side;self.face(pts,tile,material,outward=n)

    def wing(self,stations,tile="shell"):
        # y, leading x, chord, z, thickness. A real closed airfoil with a tapered tip.
        ts=[(1-math.cos(i*math.pi/12))*.5 for i in range(13)]
        outline=[(t,1) for t in ts]+[(t,-1) for t in reversed(ts[1:-1])]
        rings=[]
        for y,leading,chord,z,thickness in stations:
            rings.append([np.array((leading-t*chord,y,z+side*thickness*math.sin(math.pi*t)**.75)) for t,side in outline])
        for k in range(len(rings)-1):
            for i in range(len(outline)):
                j=(i+1)%len(outline)
                side=outline[i][1]
                out=(1 if i==0 else -1 if i==12 else 0,0,side)
                # Flush access panels use the airfoil's own surface; no overlapping geometry.
                surface="carbon" if tile=="shell" and k==1 and 17<=i<=19 else tile
                self.face([rings[k][i],rings[k+1][i],rings[k+1][j],rings[k][j]],surface,outward=out)
        for k,side in ((0,-1),(-1,1)):
            self.face(rings[k],tile,outward=(0,side*np.sign(stations[-1][0]-stations[0][0]),0))

    def fin(self,side):
        # Twin canted stabilizers on the aft booms.
        outline=[(-73,side*30,11),(-82,side*42,39),(-102,side*42,39),(-98,side*30,11)]
        for delta in (-.6,.6):
            self.face([(x,y+delta,z) for x,y,z in outline],outward=(0,np.sign(delta),0))
        for i in range(4):
            j=(i+1)%4;a=outline[i];b=outline[j]
            self.face([(a[0],a[1]-.6,a[2]),(b[0],b[1]-.6,b[2]),(b[0],b[1]+.6,b[2]),(a[0],a[1]+.6,a[2])],"carbon")

    def write(self,name):
        lines=[f"# Original RAZED {name}",f"o {name}"]
        # OBJ importer uses Y-up; this permutation restores Source coordinates.
        lines += ["v %.6f %.6f %.6f"%(p[1],p[2],p[0]) for p in self.vertices]
        lines += ["vt %.6f %.6f"%(u,1-v) for u,v in self.uvs]
        lines += ["vn %.6f %.6f %.6f"%(p[1],p[2],p[0]) for p in self.normals]
        previous=None
        for material,indices in self.faces:
            if material!=previous: lines.append(f"usemtl {material}");previous=material
            lines.append("f "+" ".join(f"{i}/{i}/{i}" for i in indices))
        (DEST/f"{name}.obj").write_text("\n".join(lines)+"\n")
        names=sorted({m for m,_ in self.faces})
        remaps=",\n".join('{ from = "'+m+'.vmat" to = "'+ASSET+'/'+m+'.vmat" }' for m in names)
        (DEST/f"{name}.vmdl").write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [
'''+remaps+'''
] use_global_default = false } ] },
{ _class = "RenderMeshList" children = [ { _class = "RenderMeshFile"
filename = "'''+ASSET+f'/{name}.obj'+'''"
import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1
align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None"
} ] } ] } }
''')
        points=np.array(self.vertices)
        return {"triangles":len(self.faces),"bounds_min":points.min(axis=0).tolist(),"bounds_max":points.max(axis=0).tolist()}

body=Mesh()
body.loft_x([(-61,2.5,3,6),(-53,5,5,6),(-37,8.3,8,6),(-12,10,10,6),
             (15,10.3,10.7,6),(38,9,9.2,5),(57,5.5,6.2,3),(69,.3,.4,1)])
for side in (-1,1):
    body.wing([(0,27,49,10,2.8),(side*30,23,45,10,2.6),(side*89,9,31,12,1.5),(side*108,2,23,15,.5)])
    body.tube((-11,side*30,9),(-92,side*30,11),1.6)
    body.fin(side)
    body.wing([(side*29,-76,25,11,1.1),(side*7,-78,21,11,.9)],"carbon")
    # Wing tip signal lights and underside access panels.
    body.box((-10,side*106,15.9),(5,2,.7),material="red" if side>0 else "green")
    # Inspection fasteners and control-surface hinge fairings.
    for y in (43,66,86):
        body.tube((-15,side*y,11),(-23,side*y,11),.48,"rubber")
    # Separate upper-wing identification plates with a readable UV island.
    body.face([(17,side*35,12.8),(-8,side*35,12.8),(-13,side*62,13.7),(11,side*62,13.7)],"marking",outward=(0,0,1))

# Gimballed observation camera and mount beneath the nose.
body.tube((37,0,0),(37,0,-9),2.4,"rubber")
body.loft_x([(27,.4,.4,-9),(29,5,5,-9),(33,7.5,7.5,-9),(39,7.5,7.5,-9),(43,5,5,-9),(44,.4,.4,-9)],"carbon",24)
body.tube((40,0,-11),(47,0,-14),4.2,material="metal")
body.tube((47,0,-14),(47.3,0,-14.15),3.35,material="lens",segments=32)
body.tube((43,-4,-6),(46,-4,-6),1.5,material="lens")
# Raised service hatch, cooling slots, aft motor and communications antenna.
body.box((-5,0,16),(29,12,.75),"rubber")
body.face([(9,-5.7,16.45),(9,5.7,16.45),(-19,5.7,16.45),(-19,-5.7,16.45)],"marking",outward=(0,0,1))
for x in range(-33,-15,3):
    for side in (-1,1): body.box((x,side*7.3,9.5),(1.2,.4,5.5),"rubber")
body.tube((-57,0,6),(-65,0,6),3.8,"carbon")
body.tube((-13,0,16),(-17,0,27),.45,"rubber")
body.tube((-17,0,27),(-17,0,30),.75,"rubber")
for side in (-1,1):
    body.tube((12,side*6,-2),(-18,side*6,-5),.85,"rubber")

# The pusher propeller is a separate mesh so the game can spin it about X.
prop=Mesh()
prop.tube((-1,0,0),(1.2,0,0),2,"carbon")
for blade in range(3):
    a=blade*math.tau/3
    def p(x,y,z):return (x,y*math.cos(a)-z*math.sin(a),y*math.sin(a)+z*math.cos(a))
    front=[p(-.35,2,-1),p(-.1,17,-1.5),p(.6,18.5,.5),p(.8,7,2.5),p(.5,2,1)]
    back=[(x-.45,y,z) for x,y,z in front]
    prop.face(front,"carbon",outward=(1,0,0));prop.face(back,"carbon",outward=(-1,0,0))
    for i in range(5):
        j=(i+1)%5;prop.face([front[i],front[j],back[j],back[i]],"carbon")

for name in ("recon","metal","lens","red","green"):
    color="recon_color" if name=="recon" else f"{name}_color"
    normalmap=f"{ASSET}/recon_normal.png" if name=="recon" else "materials/default/default_normal.tga"
    roughmap=f"{ASSET}/recon_roughness.png" if name=="recon" else "materials/default/default_rough.tga"
    scale={"recon":1,"metal":.5,"lens":.12,"red":.4,"green":.4}[name]
    metal={"recon":.08,"metal":.8,"lens":.35,"red":.1,"green":.1}[name]
    (DEST/f"{name}.vmat").write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 TextureColor "{ASSET}/{color}.png"
 TextureNormal "{normalmap}"
 TextureRoughness "{roughmap}"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_flRoughnessScale "{scale}"
 g_flMetalness "{metal}"
}}
''')
stats={"body":body.write("recon_drone"),"propeller":prop.write("recon_propeller")}
(DEST/"asset-info.json").write_text(json.dumps(stats,indent=2)+"\n")
print(json.dumps(stats))
