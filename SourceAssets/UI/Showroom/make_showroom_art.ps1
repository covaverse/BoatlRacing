# Art for the 3D showroom set: an LED-screen image cut from the clean middle band of UI_REF2
# (no UI elements in it) and a Thai flag for the hanging banners.
# Usage: powershell -File make_showroom_art.ps1   (writes PNGs into Textures/)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here '..\..\..')
$out = Join-Path $here 'Textures'
New-Item -ItemType Directory -Force $out | Out-Null

$ref = [System.Drawing.Bitmap]::FromFile((Join-Path $root 'Content\Boats\UI_REF2.png'))
$band = New-Object System.Drawing.Rectangle 330, 222, 1342, 323
$screen = New-Object System.Drawing.Bitmap $band.Width, $band.Height
$g = [System.Drawing.Graphics]::FromImage($screen)
$g.DrawImage($ref, (New-Object System.Drawing.Rectangle 0, 0, $band.Width, $band.Height), $band, 'Pixel')
$g.Dispose(); $ref.Dispose()
$screen.Save((Join-Path $out 'T_SR_Screen.png'))

# Thai flag, 3:2 with stripes red/white/blue(double)/white/red.
$flag = New-Object System.Drawing.Bitmap 300, 200
$g = [System.Drawing.Graphics]::FromImage($flag)
$stripes = @(@(237, 28, 36), @(255, 255, 255), @(36, 29, 79), @(255, 255, 255), @(237, 28, 36))
$heights = @(33, 33, 68, 33, 33); $y = 0
for ($i = 0; $i -lt 5; $i++) { $c = $stripes[$i]; $g.FillRectangle((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb($c[0], $c[1], $c[2]))), 0, $y, 300, $heights[$i]); $y += $heights[$i] }
$g.Dispose()
$flag.Save((Join-Path $out 'T_SR_FlagThai.png'))
"SHOWROOM_ART " + (Get-ChildItem $out -Filter *.png).Count
