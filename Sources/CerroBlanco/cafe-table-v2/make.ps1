# Build, bake, paint and export the cafe table in Blender and Python at idle priority.
#   make.ps1 [-Build] [-Preview]     -Build rebuilds and rebakes first; -Preview renders the bare build in Blender and stops.
param([switch]$Build, [switch]$Preview)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\CerroBlanco\cafe-table-v2"
$work = "$root\output\asset-improvement-20261030\cerroblanco-cafe-table\work"
$assets = "$root\Assets\models\maps\cerroblanco\cafe_table_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
New-Item -ItemType Directory -Force $work, $assets | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(parts|tris|islands|baked|lod |table |table_lod|exported|saved|covered|table painted|rendered)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error|error:' -Context 0,12 | ForEach-Object { '! ' + $_.ToString() }
}

function Blender($script, $rest, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python', "$src\$script", '--', $work, $root) + $rest) "$work\$log"
}

if ($Preview) {
    Blender 'table.py' @('build') 'build'
    Blender 'preview.py' @() 'preview'
    return
}
if ($Build) { Blender 'table.py' @('build', 'bake') 'build' }
Idle 'python' @('-B', "$src\paint_table.py", $work, $assets) "$work\paint"
Blender 'table.py' @('export') 'export'
python -B "$root\Sources\Gameplay\capture-flag-v2\check_outward.py" "$assets\table_lod0.obj" table
