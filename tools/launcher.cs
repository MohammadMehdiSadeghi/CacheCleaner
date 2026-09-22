// launcher.cs — source of CacheCleaner.exe, the icon-bearing launcher in the project root.
//
// A .bat file can never carry its own icon (Windows draws file icons from the registry
// association, not from the file), so the visible main file of the project is a tiny
// winforms-free exe compiled from this file with the app icon embedded:
//
//     tools\build_launcher.bat
//
// It does exactly what CacheCleaner.bat does: find a Python that actually has pywebview
// installed (tested, not trusted from PATH) and start app.py with it, then exit.
// C# 5 only — this is compiled by the .NET Framework csc.exe shipped with Windows.

using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;

[assembly: AssemblyTitle("Cache Cleaner")]
[assembly: AssemblyProduct("Cache Cleaner")]
[assembly: AssemblyDescription("Find and clear the cache of every application")]
[assembly: AssemblyVersion("1.0.0.0")]

static class Launcher
{
    const uint MB_OK = 0;
    const uint MB_ICONERROR = 0x10;
    const int WAIT_MS = 15000;

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern int MessageBox(IntPtr hWnd, string text, string caption, uint type);

    static readonly string[] KnownPythons = new string[]
    {
        @"%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe",
        @"%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe",
        @"%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe",
    };

    static void Fail(string text)
    {
        MessageBox(IntPtr.Zero, text, "Cache Cleaner", MB_OK | MB_ICONERROR);
    }

    // The candidate must prove it can import webview — PATH order means nothing here.
    static bool HasWebview(string exe)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = exe;
            psi.Arguments = "-c \"import webview\"";
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;

            using (Process p = Process.Start(psi))
            {
                p.StandardOutput.ReadToEnd();
                p.StandardError.ReadToEnd();
                if (!p.WaitForExit(WAIT_MS))
                {
                    try { p.Kill(); }
                    catch { }
                    return false;
                }
                return p.ExitCode == 0;
            }
        }
        catch
        {
            return false;
        }
    }

    static string FindOnPath(string exeName)
    {
        string path = Environment.GetEnvironmentVariable("PATH") ?? "";
        string[] dirs = path.Split(Path.PathSeparator);
        for (int i = 0; i < dirs.Length; i++)
        {
            string dir = dirs[i].Trim();
            if (dir.Length == 0)
                continue;
            string candidate = Path.Combine(dir, exeName);
            if (File.Exists(candidate) && HasWebview(candidate))
                return candidate;
        }
        return null;
    }

    static string FindPython()
    {
        for (int i = 0; i < KnownPythons.Length; i++)
        {
            string candidate = Environment.ExpandEnvironmentVariables(KnownPythons[i]);
            if (File.Exists(candidate) && HasWebview(candidate))
                return candidate;
        }
        string fromPath = FindOnPath("pythonw.exe");
        if (fromPath != null)
            return fromPath;
        return FindOnPath("python.exe");
    }

    [STAThread]
    static int Main()
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string app = Path.Combine(dir, "app.py");

        if (!File.Exists(app))
        {
            Fail("app.py was not found next to CacheCleaner.exe.\n\n" +
                 "Keep the executable in the project root (the folder that contains app.py).");
            return 1;
        }

        string py = FindPython();
        if (py == null)
        {
            Fail("Could not find a Python with pywebview installed.\n\n" +
                 "Install it with:\n" +
                 "python -m pip install pywebview");
            return 1;
        }

        ProcessStartInfo psi = new ProcessStartInfo();
        psi.FileName = py;
        psi.Arguments = "\"" + app + "\"";
        psi.WorkingDirectory = dir;
        psi.UseShellExecute = false;
        Process.Start(psi);
        return 0;
    }
}
