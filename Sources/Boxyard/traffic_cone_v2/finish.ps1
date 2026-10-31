# Build, bake, paint, export, verify and render the traffic cone, in Blender in the background at idle priority.
#   finish.ps1 [-Build] [-Old]     -Build rebuilds and rebakes first; -Old also renders the old cones, which only needs doing once.
param([switch]$Build, [switch]$Old)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Boxyard\traffic_cone_v2"
$work = "$root\output\asset-improvement-20261030\traffic-cone"
$export = "$work\export"
$final = "$work\final"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$which = if ($Old) { 'old,new' } else { 'new' }
New-Item -ItemType Directory -Force $export, $final | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(parts|tris|islands|baked|lod |cone_lod|exported|saved|traffic cone|yaw|renders done)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
}

function Blender($script, $rest, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python', "$src\$script", '--') + $rest) "$work\$log"
}

if ($Build) { Blender 'cone.py' @($work, $root, 'build', 'bake') 'build' }
Idle 'python' @('-B', "$src\paint_cone.py", $work, $export) "$work\paint"
Blender 'cone.py' @($work, $root, 'export') 'export'
python -B "$src\verify_cone.py" $root $work | Out-File "$work\verify.json" -Encoding utf8
"verify exit: $LASTEXITCODE"
Get-Content "$work\verify.json" | Select-String -Pattern '"outward"|"failures"|"triangles"' -Context 0,2
Blender 'render_cone.py' @($root, $work, $final, '900', '48', 'pair,close,sleeve,base,tip,lying', $which) 'render'
foreach ($lod in 1, 2) { Blender 'render_cone.py' @($root, $work, $final, '520', '24', 'lodview', 'new', "$lod") "render$lod" }
Blender 'render_cone.py' @($root, $work, $final, '520', '24', 'lodview', $which, '0') 'render0'
$sheet = "$root\Sources\Weapons\he_grenade_v2\sheet.py"
python -B $sheet "$final\sheet-1-whole.png" 2 900 "$final\pair-before.png|BEFORE  (Blender render)" "$final\pair-after.png|AFTER  (Blender render)" "$final\close-before.png|BEFORE" "$final\close-after.png|AFTER"
python -B $sheet "$final\sheet-2-detail.png" 2 900 "$final\sleeve-before.png|BEFORE  (Blender render)" "$final\sleeve-after.png|AFTER  (Blender render)" "$final\base-before.png|BEFORE" "$final\base-after.png|AFTER"
python -B $sheet "$final\sheet-3-more.png" 2 900 "$final\tip-before.png|BEFORE  (Blender render)" "$final\tip-after.png|AFTER  (Blender render)" "$final\lying-before.png|BEFORE" "$final\lying-after.png|AFTER"
python -B $sheet "$final\sheet-4-lods.png" 4 520 "$final\lodview-before.png|OLD" "$final\lodview-after.png|NEW LOD 0" "$final\lodview-after-lod1.png|NEW LOD 1" "$final\lodview-after-lod2.png|NEW LOD 2"
