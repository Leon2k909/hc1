from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
t=(ROOT/'Sources/Riverdale/shared-cone-v1/build.py').read_text().replace('shared-cone-v1','sand-bin-v1').replace('yard_without_cone','yard_without_bin')
start=t.index('audit=dict(');end=t.index("(OUT/'existing-upgrade-audit.json')",start)
t=t[:start]+'''audit=dict(target='Court sand bin at (-1250,258)',existing_improvement_found=False,checked=['Sources and docs for sand_bin/grit_bin','Asset filenames for sand/grit models','Existing Boxyard wheelie bin and Railhead station bin upgrades'],findings=['No existing sand/grit bin replacement found','Wheelie bin and station bin shapes are different functional props','Live bin is still the original box and flat lid'],reuse=['Original yellow finish and SAND label atlas'])
'''+t[end:]
t=t.replace("Y.cone(legacy,'lane cone 0',(300,2433))","Y.sand_bin(legacy,'court sand',(-1250,258),(0,1))")
start=t.index('radial=1.');end=t.index('files={',start)
t=t[:start]+'''from model import model
candidate=model();triangles=K.write_model(MODEL,RES,'sand_bin',candidate)
placement=dict(resource=RES+'/sand_bin.vmdl')
'''+t[end:]
t=t.replace("reused_resource=audit['reuse']","reused_resource=None").replace("reused_resource=audit['reuse'],triangles","triangles")
t=t.replace("for filename in ('native.py'","for filename in ('native.py'")
t=t.replace("('yard_without_cone',)","('sand_bin','yard_without_bin')")
# Generated review.py originally comes from taxi harness.
t=t.replace("('yard_without_reel',)","('sand_bin','yard_without_bin')")
t=t.replace("('taxi_post','east_without_taxi')\",\"('yard_without_bin',)","('taxi_post','east_without_taxi')\",\"('sand_bin','yard_without_bin')")
start=t.index("  anchor='if(replacement.Model.IsError)'");end=t.index("  start=t.index(' var views",start)
t=t[:start]+t[end:]
t=t.replace("audit['reuse']","RES+'/sand_bin.vmdl'")
t=t.replace('new Vector3(2375,-343,36),Target=new Vector3(2433,-300,13),Fov=33f','new Vector3(318,1295,45),Target=new Vector3(258,1250,14),Fov=38f').replace('new Vector3(2394,-326,24),Target=new Vector3(2433,-300,13),Fov=33f','new Vector3(305,1213,43),Target=new Vector3(258,1250,19),Fov=38f').replace('Name="cone"','Name="bin"')
(HERE/'build.py').write_text(t)
print('Sand bin builder ready')
