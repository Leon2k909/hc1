# Build, bake, paint, export, verify and render the bench, at idle priority. Stops at the first step that fails.
#   finish.ps1 [-Build] [-Old] [-Draft]     -Build rebuilds and rebakes first; -Old remakes the old model; -Draft renders quickly, to draft.
param([switch]$Build, [switch]$Old, [switch]$Draft)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\CerroBlanco\bench-v2"
$work = "$root\output\asset-improvement-20261030\cerroblanco-bench"
$assets = "$root\Assets\models\props\cerroblanco\bench_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$dir = if ($Draft) { "$work\draft" } else { "$work\final" }
$size = if ($Draft) { @('800', '32') } else { @('1000', '64') }
New-Item -ItemType Directory -Force $assets, $dir | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $null = $p.Handle  # Without this, ExitCode stays empty.
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(parts|tris|islands|bn_lod|lod |exported|saved|coverage|bench painted|renders done|written)|Traceback|Error|SystemExit' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:|SystemExit' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
    if ($p.ExitCode -ne 0) { throw "$log failed with exit code $($p.ExitCode)" }
}

function Blender($script, $rest, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python-exit-code', '1', '--python', "$src\$script", '--') + $rest) "$work\$log"
}

if ($Old) { Idle 'python' @('-B', "$src\read_old.py", $root, "$work\old") "$work\read_old" }
if ($Build) { Blender 'bench.py' @($work, $root, 'build', 'bake') 'build' }
Idle 'python' @('-B', "$src\paint_bench.py", $work, $assets) "$work\paint"
Blender 'bench.py' @($work, $root, 'export') 'export'
python -B "$src\verify_bench.py" $root $work | Out-File "$work\verify.json" -Encoding utf8
"verify exit: $LASTEXITCODE"
Get-Content "$work\verify.json" | Select-String -Pattern 'solid pieces|"failures"|"triangles"|stands|past_old'
Blender 'render_bench.py' (@($root, $work, $dir) + $size + @('player,hero,seat,end,side,lods')) 'render'
"finished"
