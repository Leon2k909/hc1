from pathlib import Path

path=Path('CLAUDE.md')
raw=path.read_bytes()
original=raw
newline=b'\r\n' if b'\r\n' in raw else b'\n'
def replace(old,new):
    global raw
    old=old.encode().replace(b'\n',newline)
    new=new.encode().replace(b'\n',newline)
    if raw.count(old)!=1:
        raise ValueError('Documentation changed; inspect before replacing')
    raw=raw.replace(old,new)

replace('''    surface. Council Hall piers have small bevels. `belltower_detail.py` uses smooth parasol gores and scalloped hems.
''','''    surface. Council Hall piers have small bevels. `belltower_detail.py` uses smooth parasol gores and scalloped hems.
  - `belltower_furniture.py` builds separate cart and crate boards, wheel felloes/spokes/tyres, raked bench slats,
    cast-iron arms and feet, and rounded sacks with seams. Wood uses original 4K `brown_planks_03` maps at their
    photographed one-metre scale; board UVs avoid scan seams. Lanterns have transparent glass around separate bulbs.
    `belltower_architecture.street_door` adds bevelled raised panels, rails, stiles and brass fittings to 38 closed
    street doors. Neither pass changes playable doorways or collision. Both halves now have 939,001 visual triangles;
    the centre has 163,416. All 94 placement/reachability checks and native model compiles passed. Native material
    resource checks are in `props-v1-native-resources.json`; reviewed door captures are in `doors-v1-viewport/`.
''')
replace('''  - The isolated native capture script dispatches scene render hooks and updates the DDGI system, then destroys
    the temporary scene. It renders settling frames for exposure and records the actual camera exposure settings.
    The map's post-process volume takes priority over camera-local effects. Fixed exposure diagnostics must modify
    that volume; ExposureCompensation has no effect with auto exposure disabled. Use saved-scene captures for final
    verification, without staged lighting overrides or temporary duplicate indirect-light volumes.
''','''  - Use `Sources/Belltower/editor/capture-viewport.cs.txt` with the persistent Belltower editor document. It captures
    one bitmap per call, dispatches render hooks, and explicitly applies the scene's post-process volume to the
    viewport camera. A hidden tab can have no `Scene.Camera` while another map is playing. It records the actual
    camera exposure and restores the selected document, view and game state. Use saved-scene captures for final
    verification. Do not revive the older isolated-scene capture/benchmark loops. `scene.Push()` changes global
    `Game.ActiveScene`: use only synchronous scopes and never keep one across `await`.
''')
replace('''    detail and some simple furniture still need work. The Council Hall's black column blotches, cafe plinth speckle
''','''    detail and interior dressing still need work. The Council Hall's black column blotches, cafe plinth speckle
''')
replace('''    The capture script now calls the engine's trace and relocation methods sequentially on the main thread, yielding
    between rows. Full two-pass hall and town bakes subsequently passed without new console errors and preserved
    the user's Lowtide scene. `DDGIProbeUpdaterCubemapper.RunAsync` replaces GeneratedIrradianceTexture for its
''','''    `bake-editor-lighting.cs.txt` calls trace and relocation methods sequentially on the main thread, yielding
    between rows. It uses the persistent editor scene and the updater's own scene world.
    `DDGIProbeUpdaterCubemapper.RunAsync` replaces GeneratedIrradianceTexture for its
''')
replace('''    town bake uses a 360-second cancellation limit and a longer connection timeout (`editor_check.py --timeout 480`);
    regular captures use 240 seconds. A cancelled bake must never be published. An apparent editor hang during this
    recovery was a separate native asset compilation; inspect the running operation before terminating the editor.
''','''    town bake currently uses a 600-second cancellation limit and a longer connection timeout. A cancelled bake must
    never be published. In the v8 recovery, Quality GGX reflection filtering faulted the GPU in
    `envmap_filtering_cs.shader_cs`; preserve the accepted v7 reflections and do not repeat that capture path.
    `daylight-v8-gpu-crash/` preserves the diagnostics and unaccepted reflection. Apparent hangs can also be native
    asset compilation or resident-resource reloads; inspect progress before terminating an editor.
''')
pending=path.with_name('CLAUDE.md.belltower-notes')
pending.write_bytes(raw)
if path.read_bytes()!=original:
    raise ValueError('CLAUDE.md changed during this update; inspect before replacing')
pending.replace(path)
print('Updated only the Belltower workflow notes; preserved existing line endings.')
