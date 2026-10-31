# The whole pipeline in order for the three lengths, at idle priority. A rebuild can change the unwrap, so bake and paint always
# follow it; the export refuses to run otherwise. finish.ps1 [-Build] [-Lengths 84,96,120] [-Width 1100] [-Samples 48] [-Views a,b] [-AfterOnly]
param([switch]$Build, [int[]]$Lengths = @(84, 96, 120), [int]$Width = 1100, [int]$Samples = 48, [string]$Views = "player,front,close,seat", [switch]$AfterOnly)
$root = (Resolve-Path "$PSScriptRoot\..\..\..").Path
$work = "$root\output\asset-improvement-20261030\sofa"
$export = "$work\sofa_v2"
$mats = "$export\materials\veridant\sofa_v2"
New-Item -ItemType Directory -Force $work, $mats | Out-Null
foreach ($length in $Lengths) {
    if ($Build) {
        & "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\sofa.py" "$work\build_$length.log" $work $root $length build bake
    }
    $p = Start-Process -FilePath python -ArgumentList @("`"$PSScriptRoot\paint_sofa.py`"", "`"$work\sofa_$length`"", "`"$mats`"", "$length") -PassThru -WindowStyle Hidden -RedirectStandardOutput "$work\paint_$length.log" -RedirectStandardError "$work\paint_$length.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    "paint $length exit $($p.ExitCode)"
    Get-Content "$work\paint_$length.err" -Tail 12
    if ($p.ExitCode -ne 0) { exit 1 }
    & "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\sofa.py" "$work\export_$length.log" $work $root $length export
}
if ($Lengths.Count -eq 3) {
    python "$PSScriptRoot\verify_sofa.py" $root $export
    "verify exit $LASTEXITCODE"
}
$after = @(); if ($AfterOnly) { $after = @("after") }
foreach ($length in ($Lengths | Where-Object { $_ -ne 96 })) {
    & "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\render_sofa.py" "$work\render_$length.log" $root $export "$work\renders" $Width $Samples $length $Views @after
}
