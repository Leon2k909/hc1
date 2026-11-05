"""Accepted physical A-frame, shared geometry with both original menu variants."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,re,sys,tempfile,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_detail as D
import belltower_furniture as F
from belltower_move_square_lamps import geometry,sha

OUT=Path(tempfile.gettempdir())/'belltower-menu-board-v2'
STAGE=OUT/'stage'
RES='models/maps/belltower/menu-board-v2'
MODEL=STAGE/'Assets'/RES

def link(model,centre,major,minor,segments=8,tube=4):
    centre,major,minor=map(lambda v:np.asarray(v,float),(centre,major,minor))
    axis=np.cross(major,minor);axis/=np.linalg.norm(axis)
    vertices=[];normals=[]
    for k in range(segments):
        a=k*math.tau/segments
        point=centre+major*math.cos(a)+minor*math.sin(a)
        tangent=-major*math.sin(a)+minor*math.cos(a);tangent/=np.linalg.norm(tangent)
        radial=np.cross(tangent,axis)
        vertices.append([]);normals.append([])
        for j in range(tube):
            b=j*math.tau/tube
            n=radial*math.cos(b)+axis*math.sin(b)
            vertices[-1].append(point+.075*n);normals[-1].append(n)
    for k in range(segments):
        for j in range(tube):
            ids=((k,j),((k+1)%segments,j),((k+1)%segments,(j+1)%tube),(k,(j+1)%tube))
            D.outward(model,F.IRON,[vertices[a][b] for a,b in ids],sum(normals[a][b] for a,b in ids),normals=[normals[a][b] for a,b in ids])

def build(lod):
    m=K.Model();X=np.array((1.,0,0));Y=np.array((0,1.,0));Z=np.array((0,0,1.))
    for side in (-1,1):
        p0=np.array((side*8.,0,.12));p1=np.array((side*.9,0,35.12))
        along=K.normalise(p1-p0);length=np.linalg.norm(p1-p0)
        outward=K.normalise(np.cross(Y,along))*side
        axes=(Y*side,along,outward)
        def at(y,t,depth=0):return p0+Y*y+along*t+outward*depth
        def box(y,t,depth,size,paint=F.DARK,seed=0):
            if lod<2:F.bevel_box(m,at(y,t,depth),axes,size,paint,bevel=.085,seed=seed)
            else:
                # Keep low-distance geometry inexpensive, retaining the open feet.
                m.oriented_box(at(y,t,depth),axes,size,paint)
        bottom,top=4.55,length-1.0
        # Separate stiles, rails and inset board; feet are open below the bottom rail.
        for k,y in enumerate((-11.2,11.2)):
            box(y,length/2,0,(1.6,length,1.15),seed=6+k+side)
        for k,t in enumerate((bottom,top)):
            box(0,t,0,(20.8,1.6,1.15),seed=13+k+side)
        lo,hi=bottom+.83,top-.83
        box(0,(lo+hi)/2,-.22,(20.78,hi-lo,.50),seed=31+side)
        pts=[at(-side*10.38,lo,.045),at(side*10.38,lo,.045),at(side*10.38,hi,.045),at(-side*10.38,hi,.045)]
        # Crop UVs to the existing chalk surface. Its painted frame is replaced by
        # real timber; all original image/normal/roughness pixels remain unchanged.
        D.outward(m,'chalkboard_a',pts,outward,uv=[(.067,.045),(.933,.045),(.933,.955),(.067,.955)])
        if lod<2:
            for y in (-11.2,11.2):
                for t in (bottom,top):F.bolt(m,at(y,t,.58),outward,.14,washer=False)
            # Thin metal shoes protect the bottom end grain on the four feet.
            for y in (-11.2,11.2):
                box(y,.60,-.61,(1.68,1.12,.07),F.IRON)
                box(y,.60,.61,(1.68,1.12,.07),F.IRON)
        # Hinges attach to the inside faces of both frames.
        for y in (-8.6,8.6):
            box(y,length-1.2,-.61,(2.4,2.1,.07),F.IRON)
    for y in (-8.6,8.6):
        # Alternating hinge knuckles, with a continuous metal pin through them.
        if lod<2:
            for k in range(5):
                c=np.array((0.,y-1.2+k*.5,35.47))
                F.turned(m,c,Y,X,[(.35,0.),(.40,.06),(.40,.37),(.35,.44)],F.IRON,segments=12 if lod==0 else 8)
        D.rod(m,(0,y-1.5,35.47),(0,y+1.5,35.47),.17,F.IRON,sides=8 if lod<2 else 5)
    for y in (-11.25,11.25):
        if lod<2:
            for k,x in enumerate(np.linspace(-5.03,5.03,12)):
                # Adjacent links lie in alternating planes and overlap physically.
                sag=.42*(1-(x/5.03)**2)
                minor=np.array((0,.27,0)) if k%2 else np.array((0,0,.27))
                link(m,(x,y,14.0-sag),(.54,0,0),minor,8 if lod==0 else 6,4 if lod==0 else 3)
            for s in (-1,1):D.hoop(m,(s*5.34,y,14.05),X,Z,.23,.075,F.IRON,segments=8)
        else:D.rod(m,(-5.3,y,14.),(5.3,y,14.),.065,F.IRON,sides=4)
    D.configure(m)
    m.material_overrides[F.DARK]='materials/belltower/furniture_wood_dark.vmat'
    return m

def modeldoc(picture='chalkboard_a'):
    assert picture in ('chalkboard_a','chalkboard_b')
    remaps=', '.join('{ from = "'+p+'.vmat" to = "'+mat+'" }' for p,mat in [('chalkboard_a',f'materials/belltower/{picture}.vmat'),(F.DARK,'materials/belltower/furniture_wood_dark.vmat'),(F.IRON,'materials/buildings/iron_black.vmat')])
    meshes=',\n'.join('{ _class = "RenderMeshFile" name = "lod'+str(i)+'" filename = "'+RES+'/menu_board_lod'+str(i)+'.obj" import_scale = 1.0 import_translation = [0,0,0] import_rotation = [0,0,0] align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = {exclude_by_default = false exception_list = []} }' for i in range(3))
    return ('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
        '{ rootNode = { _class = "RootNode" children = [\n'
        '{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = ['+remaps+'] use_global_default = false global_default_material = "" } ] },\n'
        '{ _class = "RenderMeshList" children = [ '+meshes+' ] },\n'
        '{ _class = "LODGroupList" children = [ { _class = "LODGroup" switch_threshold = 0.0 meshes = ["lod0"] }, { _class = "LODGroup" switch_threshold = 15.0 meshes = ["lod1"] }, { _class = "LODGroup" switch_threshold = 45.0 meshes = ["lod2"] } ] }\n'
        '] model_archetype = "" primary_associated_entity = "" anim_graph_name = "" base_model_name = "" } }\n')

def main():
    previous=json.loads((OUT/'manifest.json').read_text())['files'] if (OUT/'manifest.json').exists() else {}
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[]
    for i in range(3):
        m=build(i);lods.append(K.write_obj(MODEL/f'menu_board_lod{i}.obj',m,f'menu_board_lod{i}'))
    (MODEL/'menu_board.vmdl').write_text(modeldoc())
    (MODEL/'menu_board_b.vmdl').write_text(modeldoc('chalkboard_b'))
    guard=[ROOT/'Assets/scenes/maps/Belltower/belltower.scene',ROOT/'Assets/materials/belltower/chalkboard_a.vmat',ROOT/'Assets/materials/belltower/chalkboard_b.vmat',ROOT/'Assets/materials/belltower/furniture_wood_dark.vmat']
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in guard}
    retained=[MODEL/f'menu_board_lod{i}.{ext}' for i in range(3) for ext in ('obj','mtl')]+[MODEL/'menu_board.vmdl',MODEL/'menu_board_b.vmdl']
    report={'revision':'belltower-menu-board-v2','review_only':False,'files':{p.relative_to(STAGE).as_posix():sha(p) for p in retained},'previous_files':previous,'guards':guards,'source_sha256':sha(Path(__file__)),'lod_triangles':lods,'old_triangles':264,'world_position':[-218,628,0]}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    template=(ROOT/'Sources/Belltower/terracotta-pot-v2/import.cs.txt').read_text().replace('terracotta-pot-v2','menu-board-v2')
    template=template.replace('if(System.IO.File.Exists(target) && Hash(target)!=hash)throw', 'var before=manifest["previous_files"]?[pair.Key]?.GetValue<string>();\n if(System.IO.File.Exists(target) && Hash(target)!=hash && Hash(target)!=before)throw')
    template=template.replace('if(!System.IO.File.Exists(item.Target))System.IO.File.Copy(item.Source,item.Target);','if(!System.IO.File.Exists(item.Target) || Hash(item.Target)!=item.Hash) { var incoming=item.Target+".menu-board-incoming"; System.IO.File.Copy(item.Source,incoming,true); System.IO.File.Move(incoming,item.Target,true); }')
    (HERE/'import.cs.txt').write_text(template)
    print(json.dumps({'lods':lods,'files':len(report['files']),'review_only':False}))

if __name__=='__main__':main()
