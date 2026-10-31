# Build, bake, paint, export, verify and render the smoke grenade, in Blender in the background at idle priority.
#   finish.ps1 [-Build] [-Old]     -Build rebuilds and rebakes first; -Old also renders the old model, which only needs doing once.
param([switch]$Build, [switch]$Old)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Weapons\smoke_grenade_v2"
$work = "$root\output\asset-improvement-20261030\smoke-grenade"
$assets = "$root\Assets\Weapons\Throwable\M18_Smoke_Grenade\smoke_grenade_v2"
$final = "$work\final"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$which = if ($Old) { 'old,new' } else { 'new' }
New-Item -ItemType Directory -Force $assets, $final | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(parts|tris|islands|baked|lod |exported|saved|smoke grenade|renders done)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
}

function Blender($script, $rest, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python', "$src\$script", '--') + $rest) "$work\$log"
}

if ($Build) { Blender 'smoke.py' @($work, $root, 'build', 'bake') 'build' }
Idle 'python' @('-B', "$src\paint_smoke.py", $work, $assets) "$work\paint"
Blender 'smoke.py' @($work, $root, 'export') 'export'
python -B "$src\verify_smoke.py" $root $work | Out-File "$work\verify.json" -Encoding utf8
"verify exit: $LASTEXITCODE"
Get-Content "$work\verify.json" | Select-String -Pattern '"outward"|"failures"|"triangles_by_lod"' -Context 0,4
Blender 'render_smoke.py' @($root, $work, $final, '900', '48', 'front,lever,pin,top', $which) 'render'
foreach ($lod in 1, 2) { Blender 'render_smoke.py' @($root, $work, $final, '520', '24', 'lodview', 'new', "$lod") "render$lod" }
Blender 'render_smoke.py' @($root, $work, $final, '520', '24', 'lodview', $which, '0') 'render0'
$sheet = "$root\Sources\Weapons\he_grenade_v2\sheet.py"
python -B $sheet "$final\sheet-1-whole.png" 2 900 "$final\front-before.png|BEFORE  (Blender render)" "$final\front-after.png|AFTER  (Blender render)" "$final\lever-before.png|BEFORE" "$final\lever-after.png|AFTER"
python -B $sheet "$final\sheet-2-detail.png" 2 900 "$final\top-before.png|BEFORE  (Blender render)" "$final\top-after.png|AFTER  (Blender render)" "$final\pin-before.png|BEFORE" "$final\pin-after.png|AFTER"
python -B $sheet "$final\sheet-3-lods.png" 4 520 "$final\lodview-before.png|OLD LOD 0" "$final\lodview-after.png|NEW LOD 0" "$final\lodview-after-lod1.png|NEW LOD 1" "$final\lodview-after-lod2.png|NEW LOD 2"
