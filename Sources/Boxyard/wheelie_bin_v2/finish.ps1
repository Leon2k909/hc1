# Paint, export, render the matched before/after views and the LOD view, in Blender in the background at idle priority.
#   finish.ps1 <blender runner script> [draft]
param([string]$Run, [string]$Mode = 'final')
$src = 'C:\sbox-projects\hc1\forked-shooter-main\Sources\Boxyard\wheelie_bin_v2'
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$work = "$root\output\asset-improvement-20261030\wheelie-bin"
$final = "$work\final"
$sheet = "$root\Sources\Weapons\flashbang_v2\sheet.py"
New-Item -ItemType Directory -Force "$work\export", $final | Out-Null
python "$src\paint_bin.py" $work "$work\export" 2>&1 | Select-String -NotMatch 'Warning'
& $Run -Script "$src\wheelie_bin.py" -Log "$work\export.log" -Rest @($work, $root, 'export') 2>&1 | Select-String 'exported|Traceback|Error'
if ($Mode -eq 'draft') {
    & $Run -Script "$src\render_bin.py" -Log "$work\draft.log" -Rest @($root, "$work\draft", '700', '20', 'row,close,grey,wheel', 'new') 2>&1 | Select-String 'renders done|Traceback|Error'
} else {
    & $Run -Script "$src\render_bin.py" -Log "$work\final.log" -Rest @($root, $final, '900', '40', 'row,close,grey,wheel,side', 'old,new') 2>&1 | Select-String 'renders done|Traceback|Error'
    foreach ($lod in 1, 2) {
        & $Run -Script "$src\render_bin.py" -Log "$work\lod$lod.log" -Rest @($root, $final, '640', '24', 'lodview', 'new', "$lod") 2>&1 | Select-String 'renders done|Traceback|Error'
    }
    & $Run -Script "$src\render_bin.py" -Log "$work\lod0.log" -Rest @($root, $final, '640', '24', 'lodview', 'old,new', '0') 2>&1 | Select-String 'renders done|Traceback|Error'
    python $sheet "$final\sheet-1-whole.png" 2 900 "$final\row-before.png|BEFORE  (Blender render)" "$final\row-after.png|AFTER  (Blender render)" "$final\close-before.png|BEFORE  (Blender render)" "$final\close-after.png|AFTER  (Blender render)"
    python $sheet "$final\sheet-2-detail.png" 2 900 "$final\grey-before.png|BEFORE  (Blender render)" "$final\grey-after.png|AFTER  (Blender render)" "$final\wheel-before.png|BEFORE  (Blender render)" "$final\wheel-after.png|AFTER  (Blender render)"
    python $sheet "$final\sheet-3-lods.png" 4 640 "$final\lodview-before.png|OLD" "$final\lodview-after.png|NEW LOD 0" "$final\lodview-after-lod1.png|NEW LOD 1" "$final\lodview-after-lod2.png|NEW LOD 2"
    python "$src\verify_bin.py" $root $work
}
