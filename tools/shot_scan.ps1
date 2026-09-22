Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class SW {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  public struct R { public int L, T, Rt, B; }
}
"@
$p = Get-Process | Where-Object { $_.MainWindowTitle -eq 'Cache Cleaner' } | Select-Object -First 1
if (-not $p) { Write-Output 'NO WINDOW'; exit 1 }
$h = $p.MainWindowHandle
[void][SW]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 300
# 'R' is the interface shortcut for rescan; the animation runs for a few seconds after
[System.Windows.Forms.SendKeys]::SendWait("r")
$dir = 'C:\Users\Mohammad\Desktop\CacheCleaner\ui'
for ($i = 1; $i -le 18; $i++) {
  Start-Sleep -Milliseconds 230
  $r = New-Object SW+R
  [void][SW]::GetWindowRect($h, [ref]$r)
  $w = $r.Rt - $r.L; $ht = $r.B - $r.T
  if ($w -le 0 -or $ht -le 0) { continue }
  $bmp = New-Object System.Drawing.Bitmap $w, $ht
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hdc = $g.GetHdc()
  [void][SW]::PrintWindow($h, $hdc, 2)
  $g.ReleaseHdc($hdc)
  $out = Join-Path $dir ("_s{0:d2}.png" -f $i)
  $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
}
Write-Output "captured 18 frames"
