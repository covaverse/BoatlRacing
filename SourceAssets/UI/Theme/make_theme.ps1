# Builds the shared UI theme textures (dark glass + gold, matching Content/Boats/UI_REF.png).
# Usage: powershell -File make_theme.ps1   (writes PNGs into Textures/ next to this script)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$out = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'Textures'
New-Item -ItemType Directory -Force $out | Out-Null
function C($a, $r, $g, $b) { [System.Drawing.Color]::FromArgb($a, $r, $g, $b) }
function Canvas($w, $h) { $b = New-Object System.Drawing.Bitmap $w, $h, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb); $g = [System.Drawing.Graphics]::FromImage($b); $g.SmoothingMode = 'AntiAlias'; $g.Clear((C 0 0 0 0)); @($b, $g) }
function VGrad($g, $x, $y, $w, $h, $top, $bottom) { $r = New-Object System.Drawing.Rectangle $x, $y, $w, $h; $g.FillRectangle((New-Object System.Drawing.Drawing2D.LinearGradientBrush $r, $top, $bottom, 90.0), $r) }
function HGrad($g, $x, $y, $w, $h, $left, $right) { $r = New-Object System.Drawing.Rectangle $x, $y, $w, $h; $g.FillRectangle((New-Object System.Drawing.Drawing2D.LinearGradientBrush $r, $left, $right, 0.0), $r) }
$gold = C 255 255 176 32; $orange = C 255 238 112 12

# Panel: dark glass, faint rim, gold accent fading along the top edge.
$b, $g = Canvas 256 256
VGrad $g 0 0 256 256 (C 240 22 26 34) (C 246 9 11 15)
$g.DrawRectangle((New-Object System.Drawing.Pen (C 40 255 255 255), 1), 0, 0, 255, 255)
HGrad $g 0 0 256 3 $gold (C 0 255 176 32)
$b.Save((Join-Path $out 'T_UI_Panel.png'))

# Buttons: idle dark, hover gold-to-orange, pressed deeper orange. Drawn as 9-slice boxes in UMG.
foreach ($state in 'Idle', 'Hover', 'Pressed') {
  $b, $g = Canvas 96 48
  switch ($state) {
    'Idle'    { VGrad $g 0 0 96 48 (C 235 34 39 50) (C 240 18 21 28); $rim = C 60 255 255 255 }
    'Hover'   { VGrad $g 0 0 96 48 $gold $orange; $rim = C 255 255 214 120 }
    'Pressed' { VGrad $g 0 0 96 48 (C 255 200 92 8) (C 255 160 64 4); $rim = C 255 255 176 32 }
  }
  $g.DrawRectangle((New-Object System.Drawing.Pen $rim, 1), 0, 0, 95, 47)
  if ($state -eq 'Idle') { $g.FillRectangle((New-Object System.Drawing.SolidBrush $gold), 0, 0, 3, 48) }
  $b.Save((Join-Path $out "T_UI_Button_$state.png"))
}

# Selection marker drawn over the chosen option: faint gold fill, gold rim, bright left bar.
$b, $g = Canvas 96 48
$g.FillRectangle((New-Object System.Drawing.SolidBrush (C 46 255 176 32)), 0, 0, 96, 48)
$g.DrawRectangle((New-Object System.Drawing.Pen $gold, 2), 1, 1, 93, 45)
$g.FillRectangle((New-Object System.Drawing.SolidBrush $gold), 0, 0, 6, 48)
$b.Save((Join-Path $out 'T_UI_Selected.png'))

# Header tag: slanted gold label like the reference's "SEASONAL EVENT" strip.
$b, $g = Canvas 256 40
$pts = @((New-Object System.Drawing.PointF 0, 0), (New-Object System.Drawing.PointF 256, 0), (New-Object System.Drawing.PointF 240, 40), (New-Object System.Drawing.PointF 0, 40))
$g.FillPolygon((New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.Rectangle 0, 0, 256, 40), $gold, $orange, 0.0), $pts)
$b.Save((Join-Path $out 'T_UI_Tag.png'))

# Progress bar fill and track.
$b, $g = Canvas 128 12; HGrad $g 0 0 128 12 $orange $gold; $b.Save((Join-Path $out 'T_UI_BarFill.png'))
$b, $g = Canvas 128 12; $g.FillRectangle((New-Object System.Drawing.SolidBrush (C 220 10 12 16)), 0, 0, 128, 12); $g.DrawRectangle((New-Object System.Drawing.Pen (C 50 255 255 255), 1), 0, 0, 127, 11); $b.Save((Join-Path $out 'T_UI_BarTrack.png'))

# Divider line that fades at both ends.
$b, $g = Canvas 256 2
HGrad $g 0 0 128 2 (C 0 255 255 255) (C 70 255 255 255); HGrad $g 128 0 128 2 (C 70 255 255 255) (C 0 255 255 255)
$b.Save((Join-Path $out 'T_UI_Divider.png'))
"THEME_TEXTURES " + (Get-ChildItem $out -Filter *.png).Count
