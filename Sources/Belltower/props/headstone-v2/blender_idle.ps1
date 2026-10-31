# Run Blender in the background at idle priority on 4 threads, so a game running on this PC isn't disturbed.
# blender_idle.ps1 <script> <log> <args after --...>
param([string]$Script, [string]$Log, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$arguments = @('-b', '--factory-startup', '-t', '4', '--python', "`"$Script`"", '--') + ($Rest | ForEach-Object { "`"$_`"" })
$p = Start-Process -FilePath $blender -ArgumentList $arguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $Log -RedirectStandardError "$Log.err"
$p.PriorityClass = 'Idle'
$p.WaitForExit()
Get-Content $Log | Select-String -Pattern 'parts |tris|islands|baked|lod |exported|stages done|rendered|renders done|Error|Traceback' | ForEach-Object { $_.Line }
$errors = Get-Content "$Log.err" | Where-Object { $_ -notmatch 'TBBmalloc|DeprecationWarning|use_nodes' -and $_.Trim() }
if ($errors) { $errors | Select-Object -Last 15 }
