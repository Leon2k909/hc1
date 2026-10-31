# Paint, compile and compare the power cabinet, at low priority: cycle.ps1 [-Build] [-Views a_wide,a_door]
# -Build rebuilds and rebakes the meshes first. A full run takes about two minutes.
param([switch]$Build, [string[]]$Views)
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Sewage\power_cabinet_v2"
$work = "$root\output\asset-improvement-20261030\sewage-power-cabinet\work"
$mats = "$root\Assets\materials\maps\sewage\power_cabinet_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$cli = 'C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe'
New-Item -ItemType Directory -Force $work | Out-Null
$clock = [Diagnostics.Stopwatch]::StartNew()

if ($Build) {
    $list = @('-b', '--factory-startup', '-t', '4', '--python', "`"$src\cabinet.py`"", '--', "`"$work`"", "`"$root`"", 'build', 'bake', 'export')
    $p = Start-Process -FilePath $blender -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$work\build.log" -RedirectStandardError "$work\build.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$work\build.log" -Pattern '^(islands|exported|  total)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$work\build.err" | Select-String -Pattern 'Traceback|Error' -Context 0, 8
}
$p = Start-Process python -ArgumentList @('-B', "`"$src\paint_cabinet.py`"", "`"$work`"", "`"$mats`"", 'cabinet') -PassThru -NoNewWindow -RedirectStandardOutput "$work\paint.log" -RedirectStandardError "$work\paint.err"
$p.PriorityClass = 'BelowNormal'
$peak = 0
while (-not $p.HasExited) { try { $p.Refresh(); $peak = [math]::Max($peak, $p.WorkingSet64) } catch {} ; Start-Sleep -Milliseconds 300 }
"paint peak memory: $([math]::Round($peak / 1GB, 1)) GB"
Get-Content "$work\paint.log" -Tail 2
Get-Content "$work\paint.err" -Tail 12
"painted at $([int]$clock.Elapsed.TotalSeconds)s"
foreach ($asset in 'materials/maps/sewage/power_cabinet_v2/power_cabinet.vmat', 'models/maps/sewage/power_cabinet_v2/power_cabinet.vmdl') {
    python -c "import json,subprocess,sys; r=subprocess.run([sys.argv[1],'--call','asset_compile',json.dumps({'path':sys.argv[2]})],cwd=sys.argv[3],capture_output=True); print((r.stdout+r.stderr).decode('utf-8','replace')[:120].replace(chr(10),' '))" $cli $asset $root
}
"compiled at $([int]$clock.Elapsed.TotalSeconds)s"
python -B "$src\compare.py" @Views | Select-String -Pattern 'left edge|Exception|rror|SourceUnchanged|Traceback'
"done at $([int]$clock.Elapsed.TotalSeconds)s"
