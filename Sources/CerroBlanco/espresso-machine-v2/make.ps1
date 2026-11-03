# Build, bake, paint and export the espresso machine in Blender and Python at idle priority.
#   make.ps1 [-Build] [-Preview]     -Build rebuilds and rebakes first; -Preview renders the bare build in Blender and stops.
param([switch]$Build, [switch]$Preview)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\CerroBlanco\espresso-machine-v2"
$work = "$root\output\asset-improvement-20261030\cerroblanco-espresso\work"
$assets = "$root\Assets\models\maps\cerroblanco\espresso_machine_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
New-Item -ItemType Directory -Force $work, $assets | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(parts|tris|islands|baked|lod |machine_lod|exported|saved|covered|machine painted|rendered)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error|error:' -Context 0,12 | ForEach-Object { '! ' + $_.ToString() }
}

function Blender($script, $rest, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python', "$src\$script", '--', $work, $root) + $rest) "$work\$log"
}

if ($Preview) {
    Blender 'machine.py' @('build') 'build'
    Blender 'preview.py' @() 'preview'
    return
}
if ($Build) { Blender 'machine.py' @('build', 'bake') 'build' }
Idle 'python' @('-B', "$src\paint_machine.py", $work, $assets) "$work\paint"
Blender 'machine.py' @('export') 'export'
python -B "$root\Sources\Gameplay\capture-flag-v2\check_outward.py" "$assets\machine_lod0.obj" machine
