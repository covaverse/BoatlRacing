# Cuts main-menu buttons out of the reference image and builds hover/pressed variants.
# Usage: powershell -File make_buttons.ps1   (writes PNGs next to this script)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here '..\..\..')
$layout = Get-Content (Join-Path $here 'layout.json') -Raw | ConvertFrom-Json
$loaded = [System.Drawing.Bitmap]::FromFile((Join-Path $root $layout.source))
$source = New-Object System.Drawing.Bitmap $loaded; $loaded.Dispose()
$out = Join-Path $here 'Textures'

# The reference bakes a "selected" orange glow into the HOME row. Pull the orange out of those pixels:
# the more orange a pixel is (R much higher than B), the more it is replaced by a dark tone of its own
# brightness. White icon/label pixels are not orange, so the original HOME text survives unchanged and
# the edges of the glow fade out on their own.
for ($y = 226; $y -lt 308; $y++) {
  for ($x = 0; $x -lt 262; $x++) {
    $c = $source.GetPixel($x, $y)
    $mask = [math]::Min(1.0, [math]::Max(0.0, (($c.R - $c.B) / 255.0 - 0.06) / 0.22))
    if ($mask -le 0) { continue }
    $l = 0.3 * $c.R + 0.59 * $c.G + 0.11 * $c.B
    $tr = $l * 0.085 + 7; $tg = $l * 0.07 + 6; $tb = $l * 0.06 + 5
    $source.SetPixel($x, $y, [System.Drawing.Color]::FromArgb([int]($c.R + ($tr - $c.R) * $mask), [int]($c.G + ($tg - $c.G) * $mask), [int]($c.B + ($tb - $c.B) * $mask)))
  }
}
New-Item -ItemType Directory -Force $out | Out-Null
# The PLAY / RACE card also has a baked "selected" glow. Within 28 px of its slanted outline, turn the
# bright edge into a thin grey rim like the other cards and pull the orange out of the halo.
$card = @(@(247, 554), @(733, 554), @(704, 757), @(212, 757))
function SegmentDistance($px, $py, $a, $b) {
  $dx = $b[0] - $a[0]; $dy = $b[1] - $a[1]
  $t = [math]::Max(0.0, [math]::Min(1.0, (($px - $a[0]) * $dx + ($py - $a[1]) * $dy) / ($dx * $dx + $dy * $dy)))
  [math]::Sqrt([math]::Pow($px - $a[0] - $t * $dx, 2) + [math]::Pow($py - $a[1] - $t * $dy, 2))
}
for ($y = 524; $y -lt 788; $y++) {
  for ($x = 182; $x -lt 764; $x++) {
    $d = 99
    for ($i = 0; $i -lt 4; $i++) { $next = $card[($i + 1) % 4]; $d = [math]::Min($d, (SegmentDistance $x $y $card[$i] $next)) }
    if ($d -gt 28) { continue }
    # Inside the card only the rim itself glows; leave the artwork (its orange sky) alone.
    $inside = $true
    for ($i = 0; $i -lt 4; $i++) { $a = $card[$i]; $b = $card[($i + 1) % 4]; if ((($b[0] - $a[0]) * ($y - $a[1]) - ($b[1] - $a[1]) * ($x - $a[0])) -lt 0) { $inside = $false } }
    if ($inside -and $d -gt 6) { continue }
    $c = $source.GetPixel($x, $y)
    $l = 0.3 * $c.R + 0.59 * $c.G + 0.11 * $c.B
    if ($d -le 1.2) { $v = [int][math]::Min(175, $l * 0.7); $source.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($v, $v, [math]::Min(255, $v + 4))); continue }
    $mask = [math]::Min(1.0, [math]::Max(0.0, (($c.R - $c.B) / 255.0 - 0.06) / 0.22)) * [math]::Min(1.0, (28 - $d) / 6.0)
    if ($mask -le 0) { continue }
    $tr = $l * 0.2 + 8; $tg = $l * 0.17 + 7; $tb = $l * 0.15 + 7
    $source.SetPixel($x, $y, [System.Drawing.Color]::FromArgb([int]($c.R + ($tr - $c.R) * $mask), [int]($c.G + ($tg - $c.G) * $mask), [int]($c.B + ($tb - $c.B) * $mask)))
  }
}
$source.Save((Join-Path $out 'T_MainMenu_BG.png'), [System.Drawing.Imaging.ImageFormat]::Png)

function Crop($r) { $b = New-Object System.Drawing.Bitmap $r[2], $r[3]; $g = [System.Drawing.Graphics]::FromImage($b)
  $g.DrawImage($source, (New-Object System.Drawing.Rectangle 0, 0, $r[2], $r[3]), (New-Object System.Drawing.Rectangle $r[0], $r[1], $r[2], $r[3]), 'Pixel'); $g.Dispose(); $b }
function Shade($bmp, [double]$k) { $c = New-Object System.Drawing.Bitmap $bmp.Width, $bmp.Height; $g = [System.Drawing.Graphics]::FromImage($c)
  $m = New-Object System.Drawing.Imaging.ColorMatrix; $m.Matrix00 = $k; $m.Matrix11 = $k; $m.Matrix22 = $k; $m.Matrix33 = 1; $m.Matrix44 = 1
  $a = New-Object System.Drawing.Imaging.ImageAttributes; $a.SetColorMatrix($m)
  $g.DrawImage($bmp, (New-Object System.Drawing.Rectangle 0, 0, $bmp.Width, $bmp.Height), 0, 0, $bmp.Width, $bmp.Height, 'Pixel', $a); $g.Dispose(); $c }
$gold = [System.Drawing.Color]::FromArgb(255, 255, 176, 32)

foreach ($p in $layout.buttons.PSObject.Properties) {
  $name = $p.Name; $r = $p.Value
  $normal = Crop $r
  $hover = Shade $normal 1.15
  $g = [System.Drawing.Graphics]::FromImage($hover); $g.SmoothingMode = 'AntiAlias'
  if ($name -like 'Nav*') {
    # Same treatment as the reference's selected HOME row: warm gradient and a bright left bar.
    $rect = New-Object System.Drawing.Rectangle 0, 0, $r[2], $r[3]
    $grad = New-Object System.Drawing.Drawing2D.LinearGradientBrush $rect, ([System.Drawing.Color]::FromArgb(150, 255, 110, 0)), ([System.Drawing.Color]::FromArgb(0, 255, 110, 0)), 0.0
    $g.FillRectangle($grad, $rect); $g.FillRectangle((New-Object System.Drawing.SolidBrush $gold), 0, 0, 5, $r[3])
  } elseif ($name -like 'Card*') {
    # Cards are slanted parallelograms; outline the slant rather than the crop box.
    $skew = 26; $inset = 6
    $pts = @((New-Object System.Drawing.PointF ($inset + $skew), $inset), (New-Object System.Drawing.PointF ($r[2] - $inset), $inset),
             (New-Object System.Drawing.PointF ($r[2] - $inset - $skew), ($r[3] - $inset)), (New-Object System.Drawing.PointF $inset, ($r[3] - $inset)))
    $g.DrawPolygon((New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(110, 255, 150, 0)), 9), $pts)
    $g.DrawPolygon((New-Object System.Drawing.Pen $gold, 3), $pts)
  } else {
    $g.DrawRectangle((New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(110, 255, 150, 0)), 7), 4, 4, $r[2] - 9, $r[3] - 9)
    $g.DrawRectangle((New-Object System.Drawing.Pen $gold, 2), 4, 4, $r[2] - 9, $r[3] - 9)
  }
  $g.Dispose()
  $pressed = Shade $hover 0.8
  $normal.Save((Join-Path $out "T_MM_$name.png")); $hover.Save((Join-Path $out "T_MM_${name}_Hover.png")); $pressed.Save((Join-Path $out "T_MM_${name}_Pressed.png"))
}
# Plain crops (no hover states) used as artwork inside panels: avatar, currency icons, logo.
foreach ($p in $layout.crops.PSObject.Properties) { (Crop $p.Value).Save((Join-Path $out "T_MM_Crop$($p.Name).png")) }
"BUTTON_IMAGES " + (Get-ChildItem $out -Filter *.png).Count
