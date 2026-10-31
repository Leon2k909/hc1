# Runs cash_bag.py's Blender stages in the background at idle priority: run.ps1 <stages, comma separated>
param([string]$Stages = "build,bake,export")
$root = "C:\sbox-projects\hc1\forked-shooter-main"
$work = "$root\output\asset-improvement-20261030\cash-bag"
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
New-Item -ItemType Directory -Force $work | Out-Null
$list = @("-b", "--factory-startup", "-t", "4", "--python", "$root\Sources\Weapons\cash_bag_v2\cash_bag.py", "--", $work, $root) + $Stages.Split(",")
$p = Start-Process -FilePath $blender -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$work\build.log" -RedirectStandardError "$work\build.err"
$p.PriorityClass = "Idle"
$p.WaitForExit()
Select-String -Path "$work\build.log" -Pattern "^(parts|tris|islands|body bounds|cb_lod|baked|lod |exported|saved|cash bag stages)|Error|Traceback" | ForEach-Object { $_.Line }
Get-Content "$work\build.err" | Select-String -Pattern "Traceback|Error|error:" -Context 0,12 | ForEach-Object { "! " + $_.ToString() }
