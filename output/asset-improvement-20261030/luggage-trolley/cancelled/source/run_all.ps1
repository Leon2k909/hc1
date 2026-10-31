# The whole pipeline in order, at idle priority: build, bake, paint, export, verify, renders, sheets.
# A rebuild can change the unwrap, so bake and paint always follow it; the export refuses to run otherwise.
# run_all.ps1 <width> <samples>
param([int]$Width = 1100, [int]$Samples = 48)
$root = (Resolve-Path "$PSScriptRoot\..\..\..\..").Path
$work = "$root\output\asset-improvement-20261030\luggage-trolley"
$mats = "$root\Assets\materials\railhead\luggage_trolley_v2"
New-Item -ItemType Directory -Force $work, $mats | Out-Null

& "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\trolley.py" "$work\build.log" $work $root build bake
$p = Start-Process -FilePath python -ArgumentList @("`"$PSScriptRoot\paint_trolley.py`"", "`"$work`"", "`"$mats`"", "trolley") -PassThru -WindowStyle Hidden -RedirectStandardOutput "$work\paint.log" -RedirectStandardError "$work\paint.err"
$p.PriorityClass = 'Idle'
$p.WaitForExit()
"paint exit $($p.ExitCode)"
Get-Content "$work\paint.err" -Tail 12
if ($p.ExitCode -ne 0) { exit 1 }
& "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\trolley.py" "$work\export.log" $work $root export
python "$PSScriptRoot\verify_trolley.py" $root
"verify exit $LASTEXITCODE"
& "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\render_trolley.py" "$work\render.log" $root "$work\renders" $Width $Samples "front,rear,player,crate,cases,wheel,roll"
& "$PSScriptRoot\blender_idle.ps1" "$PSScriptRoot\render_trolley.py" "$work\render_lods.log" $root "$work\renders" 1800 32 "lods" lods
python "$PSScriptRoot\make_sheets.py" "$work\renders" "$work\sheets" trolley-whole "front,rear,player"
python "$PSScriptRoot\make_sheets.py" "$work\renders" "$work\sheets" trolley-details "crate,cases,wheel,roll"
