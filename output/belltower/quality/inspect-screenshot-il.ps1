$belltowerEngine = [Environment]::GetEnvironmentVariable('FACEPUNCH_ENGINE', 'User')
if (-not $belltowerEngine) { $belltowerEngine = $env:FACEPUNCH_ENGINE }
if (-not $belltowerEngine) { throw 'FACEPUNCH_ENGINE is unavailable' }
$belltowerManaged = Join-Path $belltowerEngine 'bin/managed'
Add-Type -Path (Join-Path $belltowerManaged 'Mono.Cecil.dll')
$belltowerAssembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $belltowerManaged 'Sandbox.Engine.dll'))
try {
    $belltowerTypes = $belltowerAssembly.MainModule.Types | Where-Object FullName -cin @('Sandbox.Game', 'Sandbox.SceneCamera', 'Sandbox.ScreenCaptureUtility', 'Sandbox.ScreenshotService')
    $belltowerMethods = $belltowerTypes.Methods | Where-Object Name -in @('TakeScreenshot', 'TakeHighResScreenshot', 'RequestCapture', 'CaptureFrame', 'CaptureRenderTexture', 'ConfigureView', 'get_Tonemap', '.ctor')
    $belltowerLines = foreach ($belltowerMethod in $belltowerMethods) {
        $belltowerMethod.FullName + ' public=' + $belltowerMethod.IsPublic
        foreach ($belltowerInstruction in $belltowerMethod.Body.Instructions) { $belltowerInstruction.ToString() }
    }
    $belltowerReport = Join-Path (Get-Location).Path 'output/belltower/quality/screenshot-render-il.txt'
    $belltowerLines | Set-Content -LiteralPath $belltowerReport -Encoding UTF8
    'Saved screenshot IL: ' + $belltowerLines.Count + ' lines'
} finally { $belltowerAssembly.Dispose() }
