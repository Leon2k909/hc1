"""Smooth the matching table pedestals, keeping all other geometry and physics."""
from collections import Counter
import json
from pathlib import Path
import re
import shutil

import map_kit as K
from belltower_safe_imports import span
from railhead_stage_extinguisher import coverage,lookup_polygons,point,sha
from veridant_stage_tables import ROOT,OUT,ROWS,replace_preserving_vertex_order
import veridant_table as T

stage=OUT/"stage-pedestal-v1"
assert not stage.exists()
stage.mkdir(parents=True)
wanted={};owner={}
for row,(e,n,z) in enumerate(ROWS):
    model=K.Model();T.legacy_pedestal(model,(e,n),z)
    lookup,_=lookup_polygons(model)
    for key in lookup:
        assert key not in wanted
        wanted[key]=True;owner[key]=row
positions={p for _,points in wanted for p in points}
candidates=[];protected_paths=["Assets/scenes/maps/Veridant/veridant.scene"]
for stem in ("buildings","dress"):
    canonical=Path(f"Assets/models/maps/veridant/veridant_{stem}.obj")
    vmdl=canonical.with_suffix(".vmdl")
    protected_paths.append(vmdl.as_posix())
    raw=(ROOT/vmdl).read_text();a,b=span(raw,'_class = "RenderMeshList"')
    imports=[Path("Assets")/p for p in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',raw[a:b])]
    candidates.extend([canonical,*imports])
files={};reports={};active_count=0
for relative in dict.fromkeys(candidates):
    source=ROOT/relative;sparse={};found=Counter();count=0;paint=None
    for line in source.open("rb"):
        if line.startswith(b"v "):
            count+=1;p=point(line[2:].decode())
            if p in positions:sparse[count]=p
        elif line.startswith(b"usemtl "):paint=line.split()[1]
        elif line.startswith(b"f ") and paint==b"vr_steel":
            ids=[int(t.split(b"/")[0]) for t in line.split()[1:]]
            if all(i in sparse for i in ids):
                key=paint,frozenset(sparse[i] for i in ids)
                if key in wanted:found[owner[key]]+=1
    if not found:
        protected_paths.append(relative.as_posix());continue
    assert all(n==50 for n in found.values()),(relative,found)
    old=K.Model();new=K.Model()
    for row in sorted(found):
        e,n,z=ROWS[row];T.legacy_pedestal(old,(e,n),z);T.build_pedestal_into(new,(e,n),z)
    piece=stage/"pieces"/(relative.as_posix().replace("/","--")+".obj")
    piece.parent.mkdir(parents=True,exist_ok=True)
    K.write_obj(piece,new,"veridant_table_pedestals")
    lookup,polygons=lookup_polygons(old)
    output=stage/relative;retained=stage/"retained"/relative
    stats,matched=replace_preserving_vertex_order(source,output,retained,lookup,piece)
    coverage(matched,lookup,polygons)
    assert stats["removed_triangles"]==len(found)*50
    backup=stage/"before"/relative
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,backup)
    files[relative.as_posix()]={"before":sha(backup),"after":sha(output),"source":output.relative_to(ROOT).as_posix(),"backup":backup.relative_to(ROOT).as_posix()}
    reports[relative.as_posix()]={**stats,"instances":len(found),"new_triangles":new.triangle_count()}
    if relative!=Path(f"Assets/models/maps/veridant/veridant_{'buildings' if 'buildings' in relative.name else 'dress'}.obj") and "/lounger-v2/" not in relative.as_posix():active_count+=len(found)
protected_paths.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/"Assets/models/maps/veridant").glob("*_hulls_*.obj"))
protected={p:sha(ROOT/p) for p in protected_paths if p not in files}
sources=["Tools/veridant_table.py","Tools/veridant_parts.py","Tools/veridant_map.py","Tools/veridant_stage_tables.py","Tools/veridant_stage_table_pedestals.py"]
inputs={p:sha(ROOT/p) for p in sources}
report={"revision":"veridant-table-v2","files":files,"source_sha256":inputs,"protected_sha256":protected,"replacement":reports,"active_instances":11,"pedestal_radius_inches":9,"stem_radius_inches":1.2,"base_segments":64,"stem_segments":32,"collision_unchanged":True}
for p,data in files.items():assert sha(ROOT/p)==data["before"]
for group in (inputs,protected):
    for p,digest in group.items():assert sha(ROOT/p)==digest
(stage/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"files":len(files),"replacement":reports,"base_segments":64,"stem_segments":32}))
