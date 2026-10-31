# The whole pipeline in order, at idle priority. A rebuild can change the unwrap, so bake and paint always follow it;
# the export refuses to run otherwise. finish.ps1 [-Build] [-Width 1100] [-Samples 48] [-Views a,b] [-AfterOnly]
param([switch]$Build, [int]$Width = 1100, [int]$Samples = 48, [string]$Views = "player,above,end,side,lug,inside", [switch]$AfterOnly)
$root = (Resolve-Path "$PSScriptRoot\..\..\..").Path
$work = "$root\output\asset-improvement-20261030\skip"
$export = "$work\skip_v2"
$mats = "$export\materials\boxyard\skip_v2"
New-Item -ItemType Directory -Force $work, $mats | Out-Null

if ($Build) {
    & "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\skip.py" "$work\build.log" $work $root build bake
}
$p = Start-Process -FilePath python -ArgumentList @("`"$PSScriptRoot\paint_skip.py`"", "`"$work`"", "`"$mats`"", "skip") -PassThru -WindowStyle Hidden -RedirectStandardOutput "$work\paint.log" -RedirectStandardError "$work\paint.err"
$p.PriorityClass = 'Idle'
$p.WaitForExit()
"paint exit $($p.ExitCode)"
Get-Content "$work\paint.err" -Tail 12
if ($p.ExitCode -ne 0) { exit 1 }
& "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\skip.py" "$work\export.log" $work $root export
python "$PSScriptRoot\verify_skip.py" $root $export
"verify exit $LASTEXITCODE"
$after = @(); if ($AfterOnly) { $after = @("after") }
& "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\render_skip.py" "$work\render.log" $root $export "$work\renders" $Width $Samples $Views @after
