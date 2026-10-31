# Run the tarp pile's stages in Blender in the background at idle priority.
#   finish.ps1 [-Stages sim,clay,build,bake,export] [-Paint]
param([string]$Stages = '', [switch]$Paint, [switch]$Export)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Orion\tarp_pile_v2"
$work = "$root\output\asset-improvement-20261030\tarp-pile"
$mats = "$root\Assets\materials\orion\tarp_pile_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
New-Item -ItemType Directory -Force $mats, "$root\Assets\models\props\orion\tarp_pile_v2", $work | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(frame|simulated|clay|pressed|parts|tris|islands|tp_lod|baked|lod |exported|saved|tarp |coverage)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
}

if ($Stages) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python', "$src\tarp.py", '--', $work, $root) + ($Stages -split ',')) "$work\blender"
}
if ($Paint) {
    Idle 'python' @('-B', "$src\paint_tarp.py", $work, $mats) "$work\paint"
}
if ($Export) {
    Idle $blender @('-b', '--factory-startup', '-t', '4', '--python', "$src\tarp.py", '--', $work, $root, 'export') "$work\export"
}
