param()

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$vswhere = 'C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC x64 toolchain not found' }
& (Join-Path $vs 'Common7/Tools/Launch-VsDevShell.ps1') -Arch amd64 -HostArch amd64 -SkipAutomaticLocation
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) { throw 'MSVC environment was not initialized' }

$report = Join-Path $root 'Saved/Automation/WaterMaskMath'
New-Item -ItemType Directory -Path $report -Force | Out-Null
Push-Location $root
try {
    & cl.exe /nologo /std:c++17 /EHsc /W4 /WX /utf-8 `
        /I'Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Private' `
        'Tools/Tests/boat_interior_mask_math_test.cpp' `
        "/Fo$report/test.obj" "/Fe$report/test.exe" 2>&1 |
        Tee-Object -FilePath (Join-Path $report 'compile.log')
    if ($LASTEXITCODE -ne 0) { throw "Compile failed: $LASTEXITCODE" }
    $output = & (Join-Path $report 'test.exe') 2>&1
    $code = $LASTEXITCODE
    $output | Tee-Object -FilePath (Join-Path $report 'green.log')
    $summary = [regex]::Match(($output -join "`n"), 'MASK_CHECKS=(\d+) FAILURES=(\d+)')
    if (-not $summary.Success) { throw 'Test summary missing; no success may be claimed' }
    [ordered]@{
        timestampUtc = [DateTime]::UtcNow.ToString('o')
        runner = 'Standalone MSVC; not Unreal Automation or gameplay'
        checks = [int]$summary.Groups[1].Value
        failures = [int]$summary.Groups[2].Value
        exitCode = $code
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $report 'result.json') -Encoding utf8
    if ($code -ne 0 -or [int]$summary.Groups[2].Value -ne 0) { throw 'Mask reference tests failed' }
} finally {
    Pop-Location
}
