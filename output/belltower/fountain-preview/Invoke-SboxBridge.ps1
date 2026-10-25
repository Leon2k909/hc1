param([string]$Command, [string]$Parameters = '{}')
$ipc = Join-Path $env:TEMP 'sbox-bridge-ipc'
$requestId = [guid]::NewGuid().ToString('N')
$request = @{id=$requestId;command=$Command;protocolVersion=1;params=($Parameters | ConvertFrom-Json -AsHashtable)} | ConvertTo-Json -Depth 16 -Compress
$tmp = Join-Path $ipc ('req_'+$requestId+'.json.tmp')
$req = Join-Path $ipc ('req_'+$requestId+'.json')
$res = Join-Path $ipc ('res_'+$requestId+'.json')
[IO.File]::WriteAllText($tmp,$request,[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $tmp -Destination $req
for ($i=0;$i -lt 550 -and -not (Test-Path -LiteralPath $res);$i++) { Start-Sleep -Milliseconds 100 }
if (Test-Path -LiteralPath $res) { Get-Content -LiteralPath $res -Raw } else { throw "Bridge timeout: $Command ($requestId)" }
