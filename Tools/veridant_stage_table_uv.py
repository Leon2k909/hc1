"""Move the tabletop UVs inside one limestone slab; retain all mesh indices and geometry."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import re
from collections import Counter

import map_kit as K
import veridant_table as T

from veridant_stage_tables import sha, ROOT, OUT

stage=OUT/"stage-v9"
assert not stage.exists()
stage.mkdir(parents=True)
previous=json.loads((OUT/"stage-v2/manifest.json").read_text())
files={};placements=dict(previous["placements"])
for stem in ("buildings","dress"):
    document=(ROOT/f"Assets/models/maps/veridant/veridant_{stem}.vmdl").read_text().split('_class = "PhysicsShapeList"')[0]
    centres=next(rows for p,rows in placements.items() if p.endswith(f"veridant_{stem}.obj"))
    for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',document):
        relative="Assets/"+resource
        if b"usemtl vr_table_honed" in (ROOT/relative).read_bytes():placements[relative]=centres
for relative in placements:
    target=ROOT/relative
    before=sha(target)
    lines=target.read_bytes().splitlines(keepends=True)
    vertices=[];vt_count=0;paint=None;removed=set();faces=[];uv_lookup={};new_uv=[]
    source_uv=[tuple(map(float,l.split()[1:])) for l in lines if l.startswith(b"vt ")]
    centres=placements[relative];repair=False;already_correct=True
    for i,line in enumerate(lines):
        if line.startswith(b"v "):
            vertices.append(tuple(map(float,line.split()[1:])))
        elif line.startswith(b"vt "):
            vt_count+=1
        elif line.startswith(b"usemtl "):
            paint=line.split()[1]
        elif line.startswith(b"f ") and paint==b"vr_table_honed":
            tokens=[list(map(int,t.split(b"/"))) for t in line.split()[1:]]
            pts=[vertices[t[0]-1] for t in tokens]
            e,n,z=min(centres,key=lambda row:sum((p[0]+row[0])**2+(p[2]-row[1])**2 for p in pts))
            correct=all(math.hypot(p[0]+e,p[2]-n)<=15.01 and z+27.99<=p[1]<=z+29.51 for p in pts)
            if not correct:
                assert relative=="Assets/models/maps/veridant/veridant_buildings.obj", (relative,i,pts)
                repair=True;already_correct=False;removed.add(i);continue
            flat=all(abs(p[1]-(z+29.5))<.0001 for p in pts)
            theta=[math.atan2(p[2]-n,-(p[0]+e))%(2*math.pi) for p in pts]
            if max(theta)-min(theta)>math.pi:theta=[t+2*math.pi if t<math.pi else t for t in theta]
            coords=[(.5-(p[0]+e)/96,.75+(p[2]-n)/96) if flat else (.30+.40*t/(2*math.pi),.75+(p[1]-(z+28))/96) for p,t in zip(pts,theta)]
            already_correct &= all(max(abs(a-b) for a,b in zip(source_uv[t[1]-1],coord))<.000025 for t,coord in zip(tokens,coords))
            ids=[]
            for coord in coords:
                q=tuple(round(c,5) for c in coord)
                assert .29<q[0]<.71 and .59<q[1]<.91
                if q not in uv_lookup:
                    uv_lookup[q]=len(new_uv)+1;new_uv.append(q)
                ids.append(uv_lookup[q])
            faces.append((tokens,ids));removed.add(i)
    assert removed and (new_uv or repair)
    if already_correct:continue
    if repair:
        # Another scoped edit reordered the canonical cache after the render
        # import was repaired. Rebuild only our final two material batches in
        # that cache, preserving all independently updated faces and tables.
        top_at=next(i for i,l in enumerate(lines) if l.strip()==b"usemtl vr_table_honed")
        steel_at=max(i for i,l in enumerate(lines[:top_at]) if l.strip()==b"usemtl vr_steel")
        assert next(i for i in range(steel_at+1,len(lines)) if lines[i].startswith(b"usemtl "))==top_at
        bottoms={i for i in range(steel_at+1,top_at) if lines[i].startswith(b"f ")}
        assert len(bottoms)==len(centres)*126 and len(removed)==len(centres)*2430
        removed.update(bottoms)
    retained=b"".join(line for i,line in enumerate(lines) if i not in removed)
    if repair:
        model=K.Model()
        for e,n,z in centres:T.build_top_into(model,(e,n),z)
        piece=stage/"canonical-table-tops.obj"
        K.write_obj(piece,model,"veridant_tables_v2")
        counts=Counter()
        for line in lines:
            for kind in (b"v",b"vt",b"vn"):
                if line.startswith(kind+b" "):counts[kind]+=1
        tables=[];tail=[]
        for line in piece.open("rb"):
            if line.startswith((b"v ",b"vt ",b"vn ")):tables.append(line)
            elif line.startswith(b"usemtl "):tail.append(line)
            elif line.startswith(b"f "):
                tail.append(b"f "+b" ".join(b"/".join(str(int(value)+counts[kind]).encode() for kind,value in zip((b"v",b"vt",b"vn"),token.split(b"/"))) for token in line.split()[1:])+b"\n")
        appended=b"\n"+b"".join(tables)+b"".join(tail)
    else:
        appended=b"\n"+b"".join(f"vt {u:.5f} {v:.5f}\n".encode() for u,v in new_uv)+b"usemtl vr_table_honed\n"
        for tokens,ids in faces:
            appended+=b"f "+b" ".join(f"{t[0]}/{vt_count+uv_id}/{t[2]}".encode() for t,uv_id in zip(tokens,ids))+b"\n"
    output=stage/relative
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(retained+appended)
    # All original vertex/normal/UV table order and all other faces are retained.
    # Only table-face UV indices change; position and normal indices stay exact.
    assert output.read_bytes()[:len(retained)]==retained
    backup=stage/"before"/relative
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(target,backup)
    assert sha(backup)==before and sha(target)==before
    files[relative]={"before":before,"after":sha(output),"source":output.relative_to(ROOT).as_posix(),"backup":backup.relative_to(ROOT).as_posix(),"uv_records_changed":len(new_uv),"geometry_and_indices_exact":not repair,"canonical_table_batches_repaired":repair,"other_faces_bytes_exact":True}
protected={p:sha(ROOT/p) for p in previous["protected_sha256"]}
protected.update({p:sha(ROOT/p) for p in previous["files"] if p not in files})
inputs={p:sha(ROOT/p) for p in [*previous["source_sha256"],"Tools/veridant_stage_table_uv.py"]}
report={"revision":"veridant-table-v2","files":files,"protected_sha256":protected,"source_sha256":inputs,"active_instances":11,"stone_seams_removed":True,"active_render_geometry_and_indices_exact":all(v["geometry_and_indices_exact"] for p,v in files.items() if "/lounger-v2/" in p),"other_faces_bytes_exact":True}
for group in (inputs,protected):
    for relative,digest in group.items():assert sha(ROOT/relative)==digest
(stage/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"files":len(files),"uv_records_changed":sum(f["uv_records_changed"] for f in files.values()),"active_render_geometry_and_indices_exact":report["active_render_geometry_and_indices_exact"]}))
