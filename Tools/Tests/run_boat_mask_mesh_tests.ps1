param()
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$report = Join-Path $root 'Saved/Automation/WaterMaskMath'
New-Item -ItemType Directory -Path $report -Force | Out-Null
$mesh = & (Join-Path $PSScriptRoot 'measure_boat_mask_section.ps1') -ExportMesh
$culture = [Globalization.CultureInfo]::InvariantCulture
$lines = [Collections.Generic.List[string]]::new()
$lines.Add("$($mesh.vertices.Count) $($mesh.triangles.Count)")
foreach ($point in $mesh.vertices) {
    $lines.Add(($point | ForEach-Object { ([double]$_).ToString('R', $culture) }) -join ' ')
}
foreach ($triangle in $mesh.triangles) { $lines.Add($triangle -join ' ') }
$inputPath = Join-Path $report 'liner-mesh.txt'
[IO.File]::WriteAllLines($inputPath, $lines)
$vswhere = 'C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC x64 toolchain not found' }
& (Join-Path $vs 'Common7/Tools/Launch-VsDevShell.ps1') -Arch amd64 -HostArch amd64 -SkipAutomaticLocation
Push-Location $root
try {
    & cl.exe /nologo /std:c++17 /EHsc /W4 /WX /utf-8 `
        /I'Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Private' `
        'Tools/Tests/boat_mask_mesh_test.cpp' "/Fo$report/mesh-test.obj" "/Fe$report/mesh-test.exe" 2>&1 |
        Tee-Object -FilePath (Join-Path $report 'mesh-compile.log')
    if ($LASTEXITCODE -ne 0) { throw 'Mesh tests failed to compile' }
    $output = & (Join-Path $report 'mesh-test.exe') $inputPath (Join-Path $report 'hull-survey.json') 2>&1
    $code = $LASTEXITCODE
    $output | Tee-Object -FilePath (Join-Path $report 'mesh-test.log')
    $summary = [regex]::Match(($output -join "`n"), 'MESH_CHECKS=(\d+) FAILURES=(\d+)')
    if (-not $summary.Success) { throw 'Mesh test summary missing' }
    [ordered]@{
        timestampUtc = [DateTime]::UtcNow.ToString('o')
        runner = 'Standalone MSVC; not Unreal Automation or gameplay'
        sourceSha256 = $mesh.sourceSha256
        vertexCount = $mesh.vertices.Count
        triangleCount = $mesh.triangles.Count
        checks = [int]$summary.Groups[1].Value
        failures = [int]$summary.Groups[2].Value
        exitCode = $code
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $report 'mesh-result.json') -Encoding utf8
    if ($code -ne 0 -or [int]$summary.Groups[2].Value -ne 0) { throw 'Mesh survey tests failed' }
} finally { Pop-Location }
