# Runs Blender stages for one or more variants at idle priority, in the background.
# run.ps1 <stages, comma separated> <variants, comma separated>
param([string]$Stages = "build,bake,export", [string]$Variants = "intact,ruptured,cap")
$root = "C:\sbox-projects\hc1\forked-shooter-main"
$work = "$root\output\asset-improvement-20261030\lpg-canister"
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
New-Item -ItemType Directory -Force $work | Out-Null
foreach ($variant in $Variants.Split(",")) {
    $list = @("-b", "--factory-startup", "-t", "4", "--python", "$root\Sources\Lowtide\lpg_canister_v2\lpg.py", "--", $work, $root, $variant) + $Stages.Split(",")
    $p = Start-Process -FilePath $blender -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$work\$variant.log" -RedirectStandardError "$work\$variant.err"
    $p.PriorityClass = "Idle"
    $p.WaitForExit()
    Select-String -Path "$work\$variant.log" -Pattern "^(parts|tris|islands|tear|cap bounds|lpg_lod|baked|lod |exported|saved|lpg stages)|Error|Traceback" | ForEach-Object { "$variant> " + $_.Line }
    Get-Content "$work\$variant.err" | Select-String -Pattern "Traceback|Error|error:" -Context 0,12 | ForEach-Object { "$variant! " + $_.ToString() }
}
