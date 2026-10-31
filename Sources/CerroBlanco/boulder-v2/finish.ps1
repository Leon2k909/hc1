# Sculpt, bake, paint and export the boulders, at idle priority. Stops at the first step that fails.
#   finish.ps1 [-Build] [-Size 4096]     -Build sculpts and bakes again first; without it, this only repaints and exports.
param([switch]$Build, [int]$Size = 2048)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\CerroBlanco\boulder-v2"
$work = "$root\output\asset-improvement-20261030\cerroblanco-boulder"
$assets = "$root\Assets\models\props\cerroblanco\boulder_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
New-Item -ItemType Directory -Force $assets, $work | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $null = $p.Handle  # Without this, ExitCode stays empty.
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(a |b |parts|tris|rk_|exported|saved|baked|coverage|rock painted|rock stages)|Traceback|Error|SystemExit' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:|SystemExit' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
    if ($p.ExitCode -ne 0) { throw "$log failed with exit code $($p.ExitCode)" }
}

function Blender($stages, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python-exit-code', '1', '--python', "$src\rock.py", '--', $work, $root, "$Size") + $stages) "$work\$log"
}

if ($Build) { Blender @('build', 'bake') 'build' }
Idle 'python' @('-B', "$src\paint_rock.py", $work, $assets) "$work\paint"
Blender @('export') 'export'
"finished"
