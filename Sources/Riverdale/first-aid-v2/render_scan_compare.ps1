# Render the two paints side by side in Blender at idle priority, and paste them into one labelled image.
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Riverdale\first-aid-v2"
$work = "$root\output\asset-improvement-20261030\first-aid"
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$p = Start-Process -FilePath $blender -ArgumentList @('-b', '--factory-startup', '-t', '4', '--python', "$src\render_scan_compare.py", '--', $work, $root) -PassThru -NoNewWindow -RedirectStandardOutput "$work\compare.log" -RedirectStandardError "$work\compare.err"
$p.PriorityClass = 'Idle'
$p.WaitForExit()
Select-String -Path "$work\compare.log" -Pattern '^(rendered|compare done)|Traceback|Error' | ForEach-Object { $_.Line }
Get-Content "$work\compare.err" | Select-String -Pattern 'Traceback|Error|error:' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
python -B "$src\sheet_scan_compare.py" $work
