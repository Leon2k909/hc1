# Rebuild and repaint the drum, render it against the old one in Blender at idle priority, make the sheets, and check the files.
#   finish.ps1 <blender runner script> [-Build] [-Old]
param([string]$Run, [switch]$Build, [switch]$Old)
$src = 'C:\sbox-projects\hc1\forked-shooter-main\Sources\Boxyard\oil_drum_v2'
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$work = "$root\output\asset-improvement-20261030\oil-drum"
$assets = "$root\Assets\models\maps\boxyard\oil_drum_v2"
$final = "$work\final"
$sheet = "$root\Sources\Weapons\he_grenade_v2\sheet.py"
$which = if ($Old) { 'old,new' } else { 'new' }
if ($Build) {
    & $Run -Script "$src\oil_drum.py" -Log "$work\build.log" -Rest @($work, $root, 'build', 'bake') 2>&1 | Select-String 'tris|islands|parts|Traceback|Error'
}
python "$src\paint_oil_drum.py" $work $assets 2>&1 | Select-String -NotMatch 'Warning'
& $Run -Script "$src\oil_drum.py" -Log "$work\export.log" -Rest @($work, $root, 'export') 2>&1 | Select-String 'exported|Traceback|Error'
& $Run -Script "$src\render_oil_drum.py" -Log "$work\final.log" -Rest @($root, $final, '900', '48', 'site,close,head,red', $which) 2>&1 | Select-String 'renders done|Traceback|Error'
foreach ($lod in 1, 2) {
    & $Run -Script "$src\render_oil_drum.py" -Log "$work\lod$lod.log" -Rest @($root, $final, '520', '32', 'lodview', 'new', "$lod") 2>&1 | Select-String 'renders done|Traceback|Error'
}
& $Run -Script "$src\render_oil_drum.py" -Log "$work\lod0.log" -Rest @($root, $final, '520', '32', 'lodview', $which, '0') 2>&1 | Select-String 'renders done|Traceback|Error'
python $sheet "$final\sheet-1-site.png" 2 900 "$final\site-before.png|BEFORE  (Blender render)" "$final\site-after.png|AFTER  (Blender render)" "$final\red-before.png|BEFORE" "$final\red-after.png|AFTER"
python $sheet "$final\sheet-2-detail.png" 2 900 "$final\close-before.png|BEFORE  (Blender render)" "$final\close-after.png|AFTER  (Blender render)" "$final\head-before.png|BEFORE" "$final\head-after.png|AFTER"
python $sheet "$final\sheet-3-lods.png" 4 520 "$final\lodview-before.png|OLD" "$final\lodview-after.png|NEW LOD 0" "$final\lodview-after-lod1.png|NEW LOD 1" "$final\lodview-after-lod2.png|NEW LOD 2"
python "$src\verify_oil_drum.py" $root
