# Runs powerups.py's Blender stages in the background at idle priority: run.ps1 <stages, comma separated> <variants, comma separated>
param([string]$Stages = "build,bake,export", [string]$Variants = "one_hit,clean_sweep")
$root = "C:\sbox-projects\hc1\forked-shooter-main"
$work = "$root\output\asset-improvement-20261030\powerups"
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
New-Item -ItemType Directory -Force $work | Out-Null
foreach ($variant in $Variants.Split(",")) {
    $list = @("-b", "--factory-startup", "-t", "4", "--python", "$root\Sources\Zombies\powerups_v2\powerups.py", "--", $work, $root, $variant) + $Stages.Split(",")
    $p = Start-Process -FilePath $blender -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$work\$variant.log" -RedirectStandardError "$work\$variant.err"
    $p.PriorityClass = "Idle"
    $p.WaitForExit()
    Select-String -Path "$work\$variant.log" -Pattern "^(parts|tris|islands|pu_lod|baked|lod |exported|saved|powerup stages)|Error|Traceback" | ForEach-Object { "$variant> " + $_.Line }
    Get-Content "$work\$variant.err" | Select-String -Pattern "Traceback|Error|error:" -Context 0,12 | ForEach-Object { "$variant! " + $_.ToString() }
}
