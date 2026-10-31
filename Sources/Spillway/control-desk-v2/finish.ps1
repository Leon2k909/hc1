# Build, bake, paint and export the control desk, in Blender in the background at idle priority.
#   finish.ps1 [-Build] [-Jobs body,panel,glow]     -Build rebuilds and rebakes first.
param([switch]$Build, [string]$Jobs = 'glow,panel,body')
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Spillway\control-desk-v2"
$work = "$root\output\asset-improvement-20261030\spillway-desk"
$mats = "$root\Assets\materials\spillway\control_desk_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
New-Item -ItemType Directory -Force $mats | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(parts|tris|islands|baked|lod |body_lod|exported|saved|painted)|painted$|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:' -Context 0,12 | ForEach-Object { '! ' + $_.ToString() }
}

if ($Build) { Idle $blender @('-b', '--factory-startup', '-t', '4', '--python', "$src\desk.py", '--', $work, $root, 'build', 'bake') "$work\build" }
Idle 'python' (@('-B', "$src\paint_desk.py", $work, $mats) + ($Jobs -split ',')) "$work\paint"
Idle $blender @('-b', '--factory-startup', '-t', '4', '--python', "$src\desk.py", '--', $work, $root, 'export') "$work\export"
foreach ($material in 'cd_body') {
    python -B "$root\Sources\Gameplay\capture-flag-v2\check_outward.py" "$root\Assets\models\props\spillway\control_desk_v2\control_desk_lod0.obj" $material
}
