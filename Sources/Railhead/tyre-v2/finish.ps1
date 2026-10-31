# Sculpt, bake, paint and export the tyres, at idle priority. Stops at the first step that fails.
#   finish.ps1 [-Build]     -Build sculpts and bakes again first; without it, this only repaints and exports.
param([switch]$Build)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Railhead\tyre-v2"
$work = "$root\output\asset-improvement-20261030\tyre"
$assets = "$root\Assets\models\props\railhead\tyre_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
New-Item -ItemType Directory -Force $assets, $work | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $null = $p.Handle  # Without this, ExitCode stays empty.
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(a |b |px/in|exported|saved|baked|coverage|tyre painted|tyre stages)|Traceback|Error|SystemExit' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:|SystemExit' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
    if ($p.ExitCode -ne 0) { throw "$log failed with exit code $($p.ExitCode)" }
}

function Blender($stages, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python-exit-code', '1', '--python', "$src\tyre.py", '--', $work, $root) + $stages) "$work\$log"
}

if ($Build) { Blender @('build', 'bake') 'build' }
Idle 'python' @('-B', "$src\paint_tyre.py", $work, $assets) "$work\paint"
Blender @('export') 'export'
"finished"
