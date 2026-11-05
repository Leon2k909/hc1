# Rebuild the installed cabinet's mesh inputs; paint_cabinet.py paints its maps separately.
param([string]$Stages = "build,bake,export-meshes")
$root = "C:\sbox-projects\hc1\forked-shooter-main"
$work = "$root\output\cabinet-instruments-20261104\work"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$taskArgs = @("-b", "--factory-startup", "-t", "2", "--python", "$root\Sources\Sewage\power_cabinet_v2\cabinet.py", "--", $work, $root) + $Stages.Split(",")
$taskProcess = Start-Process -FilePath "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -ArgumentList $taskArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput "$work\build.log" -RedirectStandardError "$work\build.err"
$taskProcess.PriorityClass = "Idle"
$taskProcess.WaitForExit()
Get-Content -LiteralPath "$work\build.log" -Tail 16
Get-Content -LiteralPath "$work\build.err" -Tail 12
exit $taskProcess.ExitCode
