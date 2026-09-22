Add-Type -AssemblyName System.Drawing
$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut('C:\Users\Mohammad\Desktop\Cache Cleaner.lnk')
Write-Output ("target      : {0}" -f $lnk.TargetPath)
Write-Output ("workingdir  : {0}" -f $lnk.WorkingDirectory)
Write-Output ("icon        : {0}" -f $lnk.IconLocation)
Write-Output ("description : {0}" -f $lnk.Description)
# extract the icon the shell actually shows for the .lnk and check its colours
$ico = $lnk.IconLocation -replace ',\d+$',''
if (Test-Path $ico) {
  $i = New-Object System.Drawing.Icon($ico, 32, 32)
  $bmp = $i.ToBitmap()
  $sum = @(0,0,0); $n = 0; $green = 0
  for ($y=0; $y -lt $bmp.Height; $y++) {
    for ($x=0; $x -lt $bmp.Width; $x++) {
      $c = $bmp.GetPixel($x, $y)
      $sum[0] += $c.R; $sum[1] += $c.G; $sum[2] += $c.B; $n++
      if ($c.G -gt ($c.R + 20) -and $c.G -gt 90) { $green++ }
    }
  }
  Write-Output ("ico avg RGB : {0},{1},{2}   accent-green px: {3}" -f [int]($sum[0]/$n), [int]($sum[1]/$n), [int]($sum[2]/$n), $green)
  Write-Output ("verdict     : {0}" -f $(if ($green -ge 5) { 'shortcut uses OUR icon' } else { 'NOT our icon' }))
} else { Write-Output 'icon file missing' }
