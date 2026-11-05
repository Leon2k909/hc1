"""Stage matching fixture replacements and retain the complete original as a reusable model."""
from pathlib import Path
import importlib.util,inspect,json,math,re,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_wall_lanterns as Lanterns
import belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('chair_install',ROOT/'Sources/Belltower/bistro-chair-v2/stage_install.py');Chairs=importlib.util.module_from_spec(spec);spec.loader.exec_module(Chairs)
OUT=Path(tempfile.gettempdir())/'belltower-wall-lantern-v2';STAGE=OUT/'install-stage';Patch.STAGE=STAGE
ORIGINAL='models/maps/belltower/wall-lantern-original'

class Discard(K.Model):
    def polygon(self,*args,**kwargs):pass

def fixtures():
    original=getattr(B,'_legacy_wall_lantern',B.wall_lantern);previous=B.wall_lantern;west=K.Model();placements=[]
    def record(model,wall,r,z_top,*args,**kwargs):
        fixture=K.Model();accepted=original(fixture,wall,r,z_top,*args,**kwargs)
        if accepted and Lanterns.matches(kwargs.get('reach',15.),kwargs.get('scale',.8)):
            d,sign,out=B.wall_out(wall)
            placements.append(('west',tuple(wall.point(r,d,z_top)),math.degrees(math.atan2(out[1],out[0]))))
            for paint,rows in fixture.polygons.items():west.polygons[paint].extend(rows)
        return accepted
    B.wall_lantern=record
    try:
        # Match the real west generator's RNG order through the houses, bakery and inn.
        rng=np.random.default_rng(2024);model=Discard();B._shops[0]=0
        B.west_houses(model,rng);B.bakery(model,[],rng);B.inn(model,[],rng)
    finally:B.wall_lantern=previous
    return placements,west,west.mirrored(B.EAST_PAINTS)

def preserved_original():
    # Same full bracket/lantern as the original, with its wall anchor at local zero.
    original=K.Model();wall=K.Wall('n',(-100,100),(-12,0),(-100,100),'+e')
    assert getattr(B,'_legacy_wall_lantern',B.wall_lantern)(original,wall,0,0,reach=15.,scale=.8)
    D.configure(original);assert original.triangle_count()==960
    folder=STAGE/'Assets'/ORIGINAL;folder.mkdir(parents=True,exist_ok=True)
    K.write_obj(folder/'original.obj',original,'wall_lantern_original')
    maps={p:D.MATERIALS.get(p,'materials/buildings/'+p+'.vmat') for p in original.polygons}
    remaps=', '.join('{ from = "'+p+'.vmat" to = "'+v+'" }' for p,v in maps.items())
    doc='<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
    doc+='{ rootNode = { _class = "RootNode" children = [ { _class = "MaterialGroupList" children = [{ _class = "DefaultMaterialGroup" remaps = ['+remaps+'] use_global_default = false global_default_material = "" }] }, { _class = "RenderMeshList" children = [{ _class = "RenderMeshFile" name = "original" filename = "'+ORIGINAL+'/original.obj" import_scale = 1.0 import_translation = [0,0,0] import_rotation = [0,0,0] align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {exclude_by_default = false exception_list = []} }] } ] } }\n'
    (folder/'wall_lantern_original.vmdl').write_text(doc)
    return {p.relative_to(STAGE).as_posix():sha(p) for p in folder.iterdir() if p.is_file()}

def main():
    STAGE.mkdir(parents=True,exist_ok=False)
    (STAGE/'legacy-wall-lantern.py.txt').write_text(inspect.getsource(B.wall_lantern))
    review=json.loads((OUT/'manifest.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in review['files'].items())
    retained=preserved_original();placements,west,east=fixtures()
    n=len(placements);assert n>0 and len(set(p[1] for p in placements))==n
    assert any(tuple(p[1])==(-1850.,475.,126.) for p in placements)
    placements+=[('east',(-p[0],p[1],p[2]),180.-yaw) for _,p,yaw in placements.copy()]
    wanted=geometry(west)+geometry(east);assert sum(wanted.values())==n*2*960
    documents={p:(ROOT/p).read_text() for p in Chairs.DOCUMENTS}
    references={ref for text in documents.values() for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text)}
    candidates={f'Assets/models/maps/belltower/belltower_{side}.obj' for side in ('west','east')}
    candidates.update('Assets/'+r for r in references if re.search(r'_(iron_black|lantern_glass|lamp_bulb|lamp_reflector)\.obj$',r))
    files={}
    for relative in sorted(candidates):
        row,found=Patch.render(ROOT/relative,wanted)
        if not row:continue
        assert all(v<=wanted[k] for k,v in found.items()) and row['triangles_after']>0
        files[relative]=row
    assert all(files[f'Assets/models/maps/belltower/belltower_{side}.obj']['removed_triangles']==n*960 for side in ('west','east'))
    protected={p:sha(ROOT/p) for p in Chairs.DOCUMENTS}
    protected.update({'Assets/'+r:sha(ROOT/'Assets'/r) for r in references if 'Assets/'+r not in files})
    protected.update({p:h for p,h in review['files'].items() if re.search(r'/(wall_lantern\.vmdl|lantern_lod[0-2]\.(obj|mtl))$',p)})
    (STAGE/'lanterns.json').write_text(json.dumps(Lanterns.group(B.ids,placements),indent=2))
    report={'revision':'belltower-wall-lantern-v2-install','files':files,'protected':protected,'retained_original_files':retained,'deleted':{},'compile_models':Chairs.DOCUMENTS,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'lanterns.json'),'lanterns':n*2,'old_triangles_removed':n*2*960,'placements':placements}
    (STAGE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'lanterns':n*2,'west':n,'east':n,'targets':len(files),'original_design_retained':Lanterns.ORIGINAL,'old_triangles_replaced':n*2*960,'files_deleted':0}))

if __name__=='__main__':main()
