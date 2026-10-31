# Repaint and re-render v2 against the old model's renders, in Blender in the background at idle priority, then verify.
# The old model's renders only need making once: pass -Old to make them as well.
#   finish.ps1 <blender runner script> [-Old]
param([string]$Run, [switch]$Old)
$src = 'C:\sbox-projects\hc1\forked-shooter-main\Sources\Weapons\he_grenade_v2'
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$work = "$root\output\asset-improvement-20261030\he-grenade"
$assets = "$root\Assets\Weapons\Throwable\HE_Grenade\he_grenade_v2"
$final = "$work\final"
$which = if ($Old) { 'old,new' } else { 'new' }
python "$src\paint_grenade.py" $work $assets 2>&1 | Select-String -NotMatch 'Warning'
& $Run -Script "$src\grenade.py" -Log "$work\export.log" -Rest @($work, $root, 'export') 2>&1 | Select-String 'exported|Traceback|Error'
& $Run -Script "$src\render_grenade.py" -Log "$work\final.log" -Rest @($root, $work, $final, '900', '48', 'front,lever,pin,top', $which) 2>&1 | Select-String 'renders done|Traceback|Error'
foreach ($lod in 1, 2) {
    & $Run -Script "$src\render_grenade.py" -Log "$work\lod$lod.log" -Rest @($root, $work, $final, '520', '32', 'lodview', 'new', "$lod") 2>&1 | Select-String 'renders done|Traceback|Error'
}
& $Run -Script "$src\render_grenade.py" -Log "$work\lod0.log" -Rest @($root, $work, $final, '520', '32', 'lodview', $which, '0') 2>&1 | Select-String 'renders done|Traceback|Error'
python "$src\sheet.py" "$final\sheet-1-whole.png" 2 900 "$final\front-before.png|BEFORE  (Blender render)" "$final\front-after.png|AFTER  (Blender render)" "$final\lever-before.png|BEFORE" "$final\lever-after.png|AFTER"
python "$src\sheet.py" "$final\sheet-2-detail.png" 2 900 "$final\top-before.png|BEFORE  (Blender render)" "$final\top-after.png|AFTER  (Blender render)" "$final\pin-before.png|BEFORE" "$final\pin-after.png|AFTER"
python "$src\sheet.py" "$final\sheet-3-lods.png" 4 520 "$final\lodview-before.png|OLD LOD 0" "$final\lodview-after.png|NEW LOD 0" "$final\lodview-after-lod1.png|NEW LOD 1" "$final\lodview-after-lod2.png|NEW LOD 2"
python "$src\verify_grenade.py" $root $work
