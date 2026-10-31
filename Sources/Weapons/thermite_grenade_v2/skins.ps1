# Paint the early skin, re-export both models, verify, and render the skin picker's pictures, at idle priority. Run after finish.ps1.
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Weapons\thermite_grenade_v2"
$work = "$root\output\asset-improvement-20261030\thermite-grenade"
$export = "$work\export"
$final = "$work\final"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'

function Idle($exe, $list, $log) {
    $p = Start-Process -FilePath $exe -ArgumentList $list -PassThru -NoNewWindow -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.err"
    $p.PriorityClass = 'Idle'
    $p.WaitForExit()
    Select-String -Path "$log.log" -Pattern '^(exported|thermite grenade|renders done)|Traceback|Error' | ForEach-Object { $_.Line }
    Get-Content "$log.err" | Select-String -Pattern 'Traceback|Error:|error:' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
}

$env:THERMITE_SCHEME = 'early'
Idle 'python' @('-B', "$src\paint_thermite.py", $work, $export) "$work\paint_early"
Remove-Item Env:THERMITE_SCHEME
Idle $blender @('-b', '--factory-startup', '-t', '4', '--python', "$src\thermite.py", '--', $work, $root, 'export') "$work\export"
python -B "$src\verify_thermite.py" $root $work | Out-File "$work\verify.json" -Encoding utf8
"verify exit: $LASTEXITCODE"
Idle $blender @('-b', '--factory-startup', '-t', '4', '--python', "$src\render_thermite.py", '--', $root, $work, $final, '900', '48', 'front,top', 'early') "$work\render_early"
Idle $blender @('-b', '--factory-startup', '-t', '4', '--python', "$src\render_thermite.py", '--', $root, $work, $final, '512', '48', 'picture', 'new,early') "$work\render_picture"
