# Rebuild the installed bollard's mesh inputs; paint_bollard.py paints its maps separately.
param([string]$Stages = "build,bake,export-meshes")
$root = "C:\sbox-projects\hc1\forked-shooter-main"
$work = "$root\output\bollard-rope-20261104\work"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$taskArgs = @("-b", "--factory-startup", "-t", "2", "--python", "$root\Sources\Lowtide\mooring_bollard_v2\bollard.py", "--", $work, $root) + $Stages.Split(",")
$taskProcess = Start-Process -FilePath "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -ArgumentList $taskArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput "$work\build.log" -RedirectStandardError "$work\build.err"
$taskProcess.PriorityClass = "Idle"
$taskProcess.WaitForExit()
Get-Content -LiteralPath "$work\build.log" -Tail 14
Get-Content -LiteralPath "$work\build.err" -Tail 14
exit $taskProcess.ExitCode
