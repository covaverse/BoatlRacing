param(
    [double]$SectionXcm = 30,
    [double]$AllowedGapCm = 2,
    [switch]$ExportMesh,
    [string]$SourcePath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../SourceAssets/ThaiLongtail/thai_racing_longtail_runtime_2k.glb'))
)

$ErrorActionPreference = 'Stop'
if (-not [double]::IsFinite($SectionXcm) -or -not [double]::IsFinite($AllowedGapCm) -or $AllowedGapCm -le 0) {
    throw 'Section and allowed gap must be finite; gap must be positive'
}
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$source = (Resolve-Path -LiteralPath $SourcePath).Path
$bytes = [IO.File]::ReadAllBytes($source)
if ($bytes.Length -lt 28) { throw 'Truncated GLB' }
if ([BitConverter]::ToUInt32($bytes, 0) -ne 0x46546C67 -or [BitConverter]::ToUInt32($bytes, 4) -ne 2) {
    throw 'Expected GLB 2'
}
$jsonLength = [BitConverter]::ToUInt32($bytes, 12)
if ([BitConverter]::ToUInt32($bytes, 8) -ne $bytes.Length -or 28L + $jsonLength -gt $bytes.Length) {
    throw 'Invalid GLB length'
}
if ([BitConverter]::ToUInt32($bytes, 16) -ne 0x4E4F534A) { throw 'GLB JSON chunk missing' }
$g = [Text.Encoding]::UTF8.GetString($bytes, 20, $jsonLength) | ConvertFrom-Json
$binHeader = 20 + $jsonLength
if ([BitConverter]::ToUInt32($bytes, $binHeader + 4) -ne 0x004E4942) { throw 'GLB BIN chunk missing' }
$bin = $binHeader + 8
$binLength = [BitConverter]::ToUInt32($bytes, $binHeader)
if ($bin + [long]$binLength -gt $bytes.Length) { throw 'Truncated BIN chunk' }
function Get-CheckedReference($Items, $Index, [string]$Label) {
    if ($null -eq $Index -or ($Index -isnot [int] -and $Index -isnot [long]) -or
        $Index -lt 0 -or $Index -ge $Items.Count) { throw "Invalid $Label reference" }
    return $Items[$Index]
}
function Get-CheckedOffset($Value, [string]$Label) {
    if ($null -eq $Value) { return 0L }
    if (($Value -isnot [int] -and $Value -isnot [long]) -or $Value -lt 0 -or $Value -gt $bytes.Length) {
        throw "Invalid $Label offset"
    }
    return [long]$Value
}
function Get-AccessorLayout($Accessor, $View, [int]$Size) {
    if ($null -eq $View.buffer -or $View.buffer -ne 0 -or
        $null -eq $Accessor.count -or ($Accessor.count -isnot [int] -and $Accessor.count -isnot [long]) -or
        $Accessor.count -lt 1 -or $Accessor.count -gt $bytes.Length) { throw 'Invalid buffer or accessor count' }
    $viewOffset = Get-CheckedOffset $View.byteOffset 'buffer view'
    $accessorOffset = Get-CheckedOffset $Accessor.byteOffset 'accessor'
    $viewLength = Get-CheckedOffset $View.byteLength 'buffer view length'
    $stride = $Size
    if ($null -ne $View.byteStride) { $stride = Get-CheckedOffset $View.byteStride 'stride' }
    $span = ([long]$Accessor.count - 1) * $stride + $Size
    if ($stride -lt $Size -or $viewOffset + $viewLength -gt $binLength -or
        $accessorOffset + $span -gt $viewLength) { throw 'Accessor exceeds its buffer view' }
    return @{ start = $bin + $viewOffset + $accessorOffset; stride = $stride }
}
$nodes = @($g.nodes | Where-Object name -eq 'Hull | teak inner liner')
if ($nodes.Count -ne 1) { throw 'Expected one named interior liner' }
$node = $nodes[0]
$meshObject = Get-CheckedReference $g.meshes $node.mesh 'mesh'
if ($node.translation -or $node.rotation -or $node.scale -or $node.matrix) {
    throw 'Liner has an unhandled transform; do not claim measurements in boat space'
}
$current = [array]::IndexOf($g.nodes, $node)
$visited = [Collections.Generic.HashSet[int]]::new()
while ($true) {
    if (-not $visited.Add($current)) { throw 'Cyclic ancestor hierarchy is invalid' }
    $ancestors = @(
        for ($index = 0; $index -lt $g.nodes.Count; $index++) {
            if ($g.nodes[$index].children -contains $current) { $index }
        }
    )
    if ($ancestors.Count -eq 0) { break }
    if ($ancestors.Count -ne 1) { throw 'Multiple ancestor paths have ambiguous boat-local coordinates' }
    $current = $ancestors[0]
    $parent = $g.nodes[$current]
    if ($parent.translation -or $parent.rotation -or $parent.scale -or $parent.matrix) {
        throw 'Transformed ancestor requires a full transform traversal'
    }
}
if ($ExportMesh) {
    $vertices = [Collections.Generic.List[object]]::new()
    $triangles = [Collections.Generic.List[object]]::new()
    foreach ($primitive in $meshObject.primitives) {
        if ($null -ne $primitive.mode -and $primitive.mode -ne 4) { throw 'Expected triangle primitive' }
        $a = Get-CheckedReference $g.accessors $primitive.attributes.POSITION 'accessor'
        $v = Get-CheckedReference $g.bufferViews $a.bufferView 'buffer view'
        if ($a.componentType -ne 5126 -or $a.type -ne 'VEC3' -or $a.sparse -or $v.buffer -ne 0) {
            throw 'Unsupported position accessor'
        }
        $layout = Get-AccessorLayout $a $v 12
        $start = $layout.start
        $stride = $layout.stride
        $base = $vertices.Count
        for ($i = 0; $i -lt $a.count; $i++) {
            $o = $start + $i * $stride
            $point = @(([double][BitConverter]::ToSingle($bytes, $o) * 100),
                (-[double][BitConverter]::ToSingle($bytes, $o + 8) * 100),
                ([double][BitConverter]::ToSingle($bytes, $o + 4) * 100))
            foreach ($coordinate in $point) {
                if (-not [double]::IsFinite($coordinate)) { throw 'Non-finite mesh coordinate' }
            }
            $vertices.Add($point)
        }
        if ($null -eq $primitive.indices) { throw 'Expected indexed triangles' }
        $a = Get-CheckedReference $g.accessors $primitive.indices 'index accessor'
        $v = Get-CheckedReference $g.bufferViews $a.bufferView 'index buffer view'
        if ($a.type -ne 'SCALAR' -or $a.sparse -or $v.buffer -ne 0 -or $a.count % 3 -ne 0) {
            throw 'Unsupported triangle index accessor'
        }
        $size = switch ($a.componentType) { 5121 { 1 } 5123 { 2 } 5125 { 4 } default { throw 'Unsupported index type' } }
        $layout = Get-AccessorLayout $a $v $size
        $stride = $layout.stride
        $start = $layout.start
        for ($i = 0; $i -lt $a.count; $i += 3) {
            $indices = @(
                for ($j = 0; $j -lt 3; $j++) {
                    $offset = $start + ($i + $j) * $stride
                    $index = switch ($size) {
                        1 { [uint32]$bytes[$offset] }
                        2 { [uint32][BitConverter]::ToUInt16($bytes, $offset) }
                        4 { [BitConverter]::ToUInt32($bytes, $offset) }
                    }
                    if ($index -ge $vertices.Count - $base) { throw 'Triangle index out of range' }
                    $base + $index
                }
            )
            $triangles.Add($indices)
        }
    }
    [pscustomobject]@{
        source = $source
        sourceSha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        node = $node.name
        checkedAncestorCount = $visited.Count - 1
        vertices = $vertices.ToArray()
        triangles = $triangles.ToArray()
    }
    return
}
$points = @(
    foreach ($primitive in $meshObject.primitives) {
        $a = Get-CheckedReference $g.accessors $primitive.attributes.POSITION 'accessor'
        $v = Get-CheckedReference $g.bufferViews $a.bufferView 'buffer view'
        if ($a.componentType -ne 5126 -or $a.type -ne 'VEC3' -or $a.sparse -or $v.buffer -ne 0) {
            throw 'Unsupported position accessor'
        }
        $layout = Get-AccessorLayout $a $v 12
        $start = $layout.start
        $stride = $layout.stride
        for ($i = 0; $i -lt $a.count; $i++) {
            $o = $start + $i * $stride
            $x = [BitConverter]::ToSingle($bytes, $o) * 100
            if ([math]::Abs($x - $SectionXcm) -lt .001) {
                # GLB Y-up -> boat Z-up; ความสมมาตรใช้ |GLB Z| เป็น half width
                [pscustomobject]@{
                    halfWidthCm = [math]::Abs([BitConverter]::ToSingle($bytes, $o + 8)) * 100
                    zCm = [BitConverter]::ToSingle($bytes, $o + 4) * 100
                }
            }
        }
    }
) | Sort-Object zCm, halfWidthCm -Unique
if ($points.Count -lt 3) { throw 'No authored section at this X; interpolation is not implemented' }
$floor = ($points | Measure-Object zCm -Minimum).Minimum
$rim = ($points | Measure-Object zCm -Maximum).Maximum
$widthFloor = ($points | Where-Object { [math]::Abs($_.zCm - $floor) -lt .001 } | Measure-Object halfWidthCm -Maximum).Maximum
$widthRim = ($points | Where-Object { [math]::Abs($_.zCm - $rim) -lt .001 } | Measure-Object halfWidthCm -Maximum).Maximum
$outerBoundary = $points | Where-Object { $_.zCm -gt $floor + .001 -or $_.halfWidthCm -ge $widthFloor - .001 }
$maximumChordOvercut = 0.0
foreach ($p in $outerBoundary) {
    $t = ($p.zCm - $floor) / ($rim - $floor)
    $chordWidth = $widthFloor + $t * ($widthRim - $widthFloor)
    $maximumChordOvercut = [math]::Max($maximumChordOvercut, $chordWidth - $p.halfWidthCm)
}
# ถ้าขยับปลายเส้นเข้ามาได้ไม่เกิน tolerance ทั้งสองปลาย chord กลางลดได้ไม่เกิน tolerance เช่นกัน
# ดังนั้น chord gap > tolerance พิสูจน์ว่าเส้นเดียวทำทั้ง no-overcut และ <= tolerance พร้อมกันไม่ได้
$result = [ordered]@{
    source = $source
    sourceSha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    node = $node.name
    sampling = 'Authored vertices on this exact section; not arbitrary triangle-plane intersections'
    checkedAncestorCount = $visited.Count - 1
    sectionXcm = $SectionXcm
    floorZcm = $floor
    rimZcm = $rim
    floorHalfWidthCm = $widthFloor
    rimHalfWidthCm = $widthRim
    points = $points
    maximumSingleLineOvercutCm = $maximumChordOvercut
    allowedEndpointGapCm = $AllowedGapCm
    singleLinearWidthCannotMeetNoOvercutAndGap = $maximumChordOvercut -gt $AllowedGapCm
    meaning = 'Geometry characterization only; no water material or Unreal asset changed'
}
$report = Join-Path $root 'Saved/Automation/WaterMaskMath'
New-Item -ItemType Directory -Path $report -Force | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $report 'geometry-section.json') -Encoding utf8
$result | ConvertTo-Json -Depth 6
