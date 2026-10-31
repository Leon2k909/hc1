# Run a command at idle priority and wait for it, with its output in a log: run_idle.ps1 <log> <exe> "<all its arguments>"
# The arguments are one string because PowerShell's binder would eat a bare "--".
param([string]$Log, [string]$Exe, [string]$Arguments)
$p = Start-Process -FilePath $Exe -ArgumentList $Arguments -NoNewWindow -PassThru -RedirectStandardOutput $Log -RedirectStandardError "$Log.err"
try { $p.PriorityClass = 'Idle' } catch {}
$p.WaitForExit()
Get-Content $Log -Tail 14
Get-Content "$Log.err" -Tail 6
exit $p.ExitCode
