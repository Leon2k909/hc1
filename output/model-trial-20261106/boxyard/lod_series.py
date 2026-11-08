"""LOD review for the Boxyard perimeter wall (boxyard-model session). Native viewport only: the Boxyard tab's real
viewport camera looks at the same north-wall bay (plan e = -400) along one clear line at 12 / 17.4 / 20 / 30 / 40 m, once
with the engine's own LOD choice (auto) and once per forced LOD (ModelRenderer.LodOverride on the 56 wall instances).
The overrides are put back to null at the end (and in a finally).

    python lod_series.py run          # capture everything into lod/
    python lod_series.py reset        # only reset the overrides
    python lod_series.py analyse      # diff auto against each forced LOD per distance, write lod/summary.json and lod_sheet2.png
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageStat
import ed, cap

HERE = Path(__file__).parent
LOD = HERE / "lod"
LOD.mkdir(exist_ok=True)
DISTS = [12, 17.4, 20, 30, 40]            # metres from the wall's inner face
Y_TARGET = 400                              # engine y of the bay (plan e = -400); clear line of sight per rays_and_lines.cs
PITCH = 1.0

SET = '''
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
int n = 0;
using ( s.Scene.Push() )
{{
    foreach ( var r in s.Scene.GetAllComponents<ModelRenderer>() )
    {{
        var path = r.Model?.ResourcePath ?? "";
        if ( !path.Contains( "perimeter_wall_v1" ) ) continue;
        r.LodOverride = {value};
        n++;
    }}
}}
await Task.Delay( 300 );
return new {{ n, Active = Editor.SceneEditorSession.Active?.Scene.Name }};
'''


def set_lod(value):
    v = "null" if value is None else str(int(value))
    r = ed.script(SET.format(value=v), f"set-lod-{v}.cs")
    return r


def pose(d):
    return (round(832 - d * 39.37, 2), Y_TARGET, 64, PITCH, 0)


def run():
    """ Captures what is missing in lod/ (so an interrupted run can be resumed). """
    try:
        for mode in (None, 0, 1, 2):
            label = "auto" if mode is None else f"lod{mode}"
            todo = [d for d in DISTS if not (LOD / f"{label}_{str(d).replace('.', '_')}m.png").exists()]
            if not todo:
                continue
            print("mode", label, set_lod(mode))
            for d in todo:
                cap.capture(f"lod/{label}_{str(d).replace('.', '_')}m", pose(d), tries=14)
    finally:
        print("reset", set_lod(None))


def crop_box(d, size):
    # the bay sits a little above the viewport centre; a fixed angular window around it
    w, h = size
    f = 657.0                       # px for an 80 degree horizontal field over 1102 px
    din = d * 39.37
    cw = min(w, int(360 * f / din * 1.5) + 40)
    ch = min(h, int(200 * f / din * 1.5) + 30)
    cx, cy = w // 2, int(h * 0.5) - 8
    return (cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2)


def analyse():
    summary = {}
    rows = []
    for d in DISTS:
        key = str(d).replace('.', '_')
        ims = {m: Image.open(LOD / f"{m}_{key}m.png").convert("RGB") for m in ("auto", "lod0", "lod1", "lod2")}
        box = crop_box(d, ims["auto"].size)
        diffs = {}
        for m in ("lod0", "lod1", "lod2"):
            dif = ImageChops.difference(ims["auto"].crop(box), ims[m].crop(box)).convert("L")
            diffs[m] = round(ImageStat.Stat(dif).mean[0], 3)
        auto_is = min(diffs, key=diffs.get)
        summary[str(d)] = {"auto matches": auto_is, "mean abs diff auto vs forced (0-255)": diffs, "crop": box}
        rows.append((d, ims, box, auto_is, diffs))
    (LOD / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    # contact sheet: rows = distance, columns = auto / LOD0 / LOD1 / LOD2, crops scaled to a common width
    cell_w = 460
    cells = []
    for d, ims, box, auto_is, diffs in rows:
        r = []
        for m in ("auto", "lod0", "lod1", "lod2"):
            c = ims[m].crop(box)
            sc = cell_w / c.width
            c = c.resize((cell_w, max(1, int(c.height * sc))), Image.NEAREST if sc > 1.5 else Image.LANCZOS)
            r.append(c)
        cells.append((d, r, auto_is))
    row_h = [max(c.height for c in r) for _, r, _ in cells]
    sheet = Image.new("RGB", (cell_w * 4 + 5 * 6, sum(row_h) + 6 * (len(cells) + 1) + 24), (20, 20, 20))
    dr = ImageDraw.Draw(sheet)
    for i, name in enumerate(("auto (engine's choice)", "forced LOD0", "forced LOD1", "forced LOD2")):
        dr.text((6 + i * (cell_w + 6) + 4, 6), name, fill=(240, 240, 240))
    y = 24
    for (d, r, auto_is), h in zip(cells, row_h):
        for i, c in enumerate(r):
            sheet.paste(c, (6 + i * (cell_w + 6), y))
        dr.text((10, y + 4), f"{d} m  (auto = {auto_is})", fill=(255, 220, 80))
        y += h + 6
    sheet.save(HERE / "lod_sheet2.png")
    print("sheet", sheet.size)


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "run":
        run()
    elif a == "reset":
        print(set_lod(None))
    elif a == "analyse":
        analyse()
