# Build, bake, paint, export, verify and render the IBC tote, in Blender in the background at idle priority.
#   finish.ps1 [-Build] [-Views list] [-Which old|new|both] [-Width n] [-Samples n] [-Out folder]
param([switch]$Build, [string]$Views = 'hero,valve,side', [string]$Which = 'both', [string]$Width = '760', [string]$Samples = '32', [string]$Out = 'renders-pass1')
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Boxyard\ibc_tote_v2"
$work = "$root\output\asset-improvement-20261030\ibc-tote"
$mats = "$root\Assets\materials\boxyard\ibc_tote_v2"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
New-Item -ItemType Directory -Force $mats, "$root\Assets\models\props\boxyard\ibc_tote_v2", "$work\$Out" | Out-Null

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(parts|tris|islands|it_lod|baked|lod |exported|saved|ibc tote|renders done|coverage)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
}

function Blender($script, $rest, $log) {
    Idle $blender (@('-b', '--factory-startup', '-t', '4', '--python', "$src\$script", '--') + $rest) "$work\$log"
}

if ($Build) {
    Blender 'ibc_tote.py' @($work, $root, 'build', 'bake') 'build'
    Idle 'python' @('-B', "$src\paint_tote.py", $work, $mats) "$work\paint"
    Blender 'ibc_tote.py' @($work, $root, 'export') 'export'
    python -B "$src\verify_tote.py" $root | Out-File "$work\verify.json" -Encoding utf8
    "verify exit: $LASTEXITCODE"
    Get-Content "$work\verify.json" | Select-String -Pattern '"outward"|"failures"' -Context 0,4
}
Blender 'render_tote.py' @($root, $work, "$work\$Out", $Width, $Samples, $Views, $Which) 'render'
