$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$report = Join-Path $root 'Saved/Automation/WaterMaskMath'
New-Item -ItemType Directory -Path $report -Force | Out-Null

# สร้าง fixture GLB ขนาดเล็กเพื่อจับการมองข้าม transform ของ grandparent จริง ไม่ใช่ตรวจข้อความ source
$g = @{
    asset = @{ version = '2.0' }
    buffers = @(@{ byteLength = 48 })
    bufferViews = @(@{ buffer = 0; byteOffset = 0; byteLength = 48 })
    accessors = @(@{ bufferView = 0; componentType = 5126; count = 4; type = 'VEC3' })
    meshes = @(@{ primitives = @(@{ attributes = @{ POSITION = 0 } }) })
    nodes = @(
        @{ name = 'Hull | teak inner liner'; mesh = 0 },
        @{ name = 'immediate identity parent'; children = @(0) },
        @{ name = 'translated grandparent'; children = @(1); translation = @(1, 0, 0) }
    )
    scenes = @(@{ nodes = @(2) })
    scene = 0
}
function Write-Fixture([string]$Name) {
$json = $g | ConvertTo-Json -Depth 12 -Compress
while (($json.Length % 4) -ne 0) { $json += ' ' }
$jsonBytes = [Text.Encoding]::UTF8.GetBytes($json)
$binary = [Collections.Generic.List[byte]]::new()
foreach ($number in @(0.3,0.17,0.2163, 0.3,0.31,0.309, 0.3,0.494,0.515, 0.3,0.17,0)) {
    $binary.AddRange([BitConverter]::GetBytes([single]$number))
}
$glb = [Collections.Generic.List[byte]]::new()
foreach ($value in @(0x46546C67,2,(12+8+$jsonBytes.Length+8+$binary.Count),$jsonBytes.Length,0x4E4F534A)) {
    $glb.AddRange([BitConverter]::GetBytes([uint32]$value))
}
$glb.AddRange($jsonBytes)
$glb.AddRange([BitConverter]::GetBytes([uint32]$binary.Count))
$glb.AddRange([BitConverter]::GetBytes([uint32]0x004E4942))
$glb.AddRange($binary.ToArray())
$fixture = Join-Path $report $Name
[IO.File]::WriteAllBytes($fixture, $glb.ToArray())
return $fixture
}
$fixture = Write-Fixture 'grandparent-fixture.glb'
$rejected = $false
try {
    & (Join-Path $PSScriptRoot 'measure_boat_mask_section.ps1') -SourcePath $fixture | Out-Null
} catch {
    if ($_.Exception.Message -notmatch 'ancestor|parent transform') { throw }
    $rejected = $true
}
if (-not $rejected) { throw 'FAIL: transformed grandparent was accepted as boat-local geometry' }
'PASS: transformed ancestor rejected'

$g.nodes[2].Remove('translation')
function Expect-Rejected([string]$Name, [string]$Pattern) {
    $fixture = Write-Fixture "$Name.glb"
    $rejected = $false
    try { & (Join-Path $PSScriptRoot 'measure_boat_mask_section.ps1') -SourcePath $fixture -ExportMesh | Out-Null }
    catch {
        if ($_.Exception.Message -notmatch $Pattern) { throw "FAIL: $Name produced unrelated error: $($_.Exception.Message)" }
        $rejected = $true
    }
    if (-not $rejected) { throw "FAIL: $Name was accepted" }
    "PASS: $Name rejected"
}
$g.nodes[0].mesh = -1
Expect-Rejected 'negative-mesh-index' 'mesh reference'
$g.nodes[0].mesh = 0
$g.meshes[0].primitives[0].attributes.POSITION = -1
Expect-Rejected 'negative-accessor-index' 'accessor reference'
$g.meshes[0].primitives[0].attributes.POSITION = 0
$g.accessors[0].bufferView = -1
Expect-Rejected 'negative-view-index' 'buffer view reference'
$g.accessors[0].bufferView = 0
$g.bufferViews[0].byteOffset = -4
$g.bufferViews[0].byteLength = 52
$g.accessors[0].byteOffset = 4
Expect-Rejected 'cancelled-negative-offset' 'offset'
