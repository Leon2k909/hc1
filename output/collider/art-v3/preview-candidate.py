from pathlib import Path
import json
import platform
import sys
platform._wmi_query=lambda *a,**k: (_ for _ in ()).throw(OSError("Skip WMI"))
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/"Tools"))
import collider_map as C
import collider_preview_textured as P
C.STAGE=root/"output/collider/art-v3/stage"
models=C.build()
(C.STAGE/"collider.scene.json").write_text(json.dumps(C.scene_data(),indent=2)+"\n")
view=json.loads((root/"output/collider/art-v3/capture-config.json").read_text())["views"][-1]
P.render(models,view,960,540,exposure=.32).save(root/"output/collider/art-v3/offline-machinery.png")
print("Offline shape preview written; native lighting review is still pending.",flush=True)
