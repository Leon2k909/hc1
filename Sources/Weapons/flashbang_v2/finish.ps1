# Repaint, export, then render the matched before/after views and the LOD view, in Blender in the background at idle priority.
#   finish.ps1 <blender runner script> [draft]
param([string]$Run, [string]$Mode = 'final')
$src = 'C:\sbox-projects\hc1\forked-shooter-main\Sources\Weapons\flashbang_v2'
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$work = "$root\output\asset-improvement-20261030\flashbang"
$export = "$work\export"
$final = "$work\final"
python "$src\paint_flash.py" $work $export 2>&1 | Select-String -NotMatch 'Warning'
& $Run -Script "$src\flash.py" -Log "$work\export.log" -Rest @($work, $root, 'export') 2>&1 | Select-String 'exported|Traceback|Error'
if ($Mode -eq 'draft') {
    & $Run -Script "$src\render_flash.py" -Log "$work\draft.log" -Rest @($root, $work, "$work\draft", '640', '20', 'front,ports,lever,top', 'new') 2>&1 | Select-String 'renders done|Traceback|Error'
} else {
    & $Run -Script "$src\render_flash.py" -Log "$work\final.log" -Rest @($root, $work, $final, '900', '48', 'front,lever,ports,top', 'old,new') 2>&1 | Select-String 'renders done|Traceback|Error'
    foreach ($lod in 1, 2) {
        & $Run -Script "$src\render_flash.py" -Log "$work\lod$lod.log" -Rest @($root, $work, $final, '520', '32', 'lodview', 'new', "$lod") 2>&1 | Select-String 'renders done|Traceback|Error'
    }
    & $Run -Script "$src\render_flash.py" -Log "$work\lod0.log" -Rest @($root, $work, $final, '520', '32', 'lodview', 'old,new', '0') 2>&1 | Select-String 'renders done|Traceback|Error'
    python "$src\sheet.py" "$final\sheet-1-whole.png" 2 900 "$final\front-before.png|BEFORE  (Blender render)" "$final\front-after.png|AFTER  (Blender render)" "$final\lever-before.png|BEFORE  (Blender render)" "$final\lever-after.png|AFTER  (Blender render)"
    python "$src\sheet.py" "$final\sheet-2-detail.png" 2 900 "$final\ports-before.png|BEFORE  (Blender render)" "$final\ports-after.png|AFTER  (Blender render)" "$final\top-before.png|BEFORE  (Blender render)" "$final\top-after.png|AFTER  (Blender render)"
    python "$src\sheet.py" "$final\sheet-3-lods.png" 4 520 "$final\lodview-before.png|OLD LOD 0" "$final\lodview-after.png|NEW LOD 0" "$final\lodview-after-lod1.png|NEW LOD 1" "$final\lodview-after-lod2.png|NEW LOD 2"
    python "$src\verify_flash.py" $root $work
}
