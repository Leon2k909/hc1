# Build, bake, paint and export the cabinet in Blender and Python at idle priority.
#   make.ps1 [-Build]     -Build rebuilds and rebakes first.
param([switch]$Build)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Riverdale\first-aid-v2"
$work = "$root\output\asset-improvement-20261030\first-aid"
$assets = "$root\Assets\models\maps\riverdale\first_aid_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
New-Item -ItemType Directory -Force $work, $assets | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(parts|tris|islands|baked|lod |first_aid_lod|exported|saved|covered|first aid painted)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error|error:' -Context 0,12 | ForEach-Object { '! ' + $_.ToString() }
}

function Blender($rest, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python', "$src\first_aid.py", '--', $work, $root) + $rest) "$work\$log"
}

if ($Build) { Blender @('build', 'bake') 'build' }
Idle 'python' @('-B', "$src\paint_first_aid.py", $work, $assets) "$work\paint"
Blender @('export') 'export'
# The scan-based finish, which the model uses by default; the code-painted one above stays as first_aid.vmat.
& "$src\paint_scanned.ps1"
python -B "$root\Sources\Gameplay\capture-flag-v2\check_outward.py" "$assets\first_aid_lod0.obj" first_aid
