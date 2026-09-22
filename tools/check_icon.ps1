Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinIcon {
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern IntPtr GetClassLongPtr(IntPtr h, int i);
  [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr h, int i);
  [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr h, uint c);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern IntPtr LoadImage(IntPtr i, string f, uint t, int x, int y, uint l);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
}
"@
# window icon lives on the app's top-level window class; report handle + class name
$p = Get-Process | Where-Object { $_.MainWindowTitle -eq 'Cache Cleaner' } | Select-Object -First 1
if (-not $p) { Write-Output 'NO WINDOW'; exit 1 }
Write-Output ("pid {0}  hwnd {1}" -f $p.Id, $p.MainWindowHandle)
$sb = New-Object System.Text.StringBuilder 256
[void][WinIcon]::GetClassName($p.MainWindowHandle, $sb, 256)
Write-Output ("class {0}" -f $sb.ToString())
$ico = 'C:\Users\Mohammad\Desktop\CacheCleaner\assets\sparkles.ico'
$h = [WinIcon]::LoadImage([IntPtr]::Zero, $ico, 1, 0, 0, 0x10)
Write-Output ("LoadImage(ICON) -> {0}  (0 = ico could not be loaded)" -f $h)
Write-Output ("shortcut exists: {0}" -f (Test-Path 'C:\Users\Mohammad\Desktop\Cache Cleaner.lnk'))
