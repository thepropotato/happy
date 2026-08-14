"""BRINGING A PAGE THAT IS ALREADY OPEN BACK IN FRONT OF SOMEBODY."""

from hands.controls.commands import on_mac, on_windows, osascript, run

# THE WHOLE POINT IS THAT THEY CAN SEE IT, SO A WINDOW LEFT IN A CORNER IS A FAIL.
FULL = 'tell application "Finder" to get bounds of window of desktop'

CHROMIUM_SHOW = """tell application "{name}"
    set hit to false
    repeat with w in windows
        set i to 0
        repeat with t in tabs of w
            set i to i + 1
            if (title of t contains "{want}") or (URL of t contains "{want}") then
                set active tab index of w to i
                set index of w to 1
                set hit to true
                exit repeat
            end if
        end repeat
        if hit then exit repeat
    end repeat
    if hit then
        activate
        set bounds of window 1 to {{{box}}}
        return title of active tab of window 1
    end if
    return ""
end tell"""

SAFARI_SHOW = """tell application "{name}"
    set hit to false
    repeat with w in windows
        repeat with t in tabs of w
            if (name of t contains "{want}") or (URL of t contains "{want}") then
                set current tab of w to t
                set index of w to 1
                set hit to true
                exit repeat
            end if
        end repeat
        if hit then exit repeat
    end repeat
    if hit then
        activate
        set bounds of window 1 to {{{box}}}
        return name of current tab of window 1
    end if
    return ""
end tell"""

PLAY = 'tell application "System Events" to key code 49'

WINDOWS_SHOW = """
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -Namespace W -Name N -MemberDefinition '
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);'
foreach ($p in Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{want}*' }}) {{
  [W.N]::ShowWindow($p.MainWindowHandle, 3) | Out-Null
  [W.N]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
  Write-Output $p.MainWindowTitle
  break
}}"""


def screen():
    """THE WHOLE DESKTOP AS AN APPLESCRIPT BOUNDS LIST."""
    said = osascript(FULL) or ""
    parts = [piece.strip() for piece in said.split(",")]

    return ", ".join(parts) if len(parts) == 4 else "0, 0, 1440, 900"


def shown(want):
    """THE TAB BROUGHT TO THE FRONT AND FILLED OUT, OR None WHEN THERE IS NO SUCH TAB."""
    if on_mac():
        return mac_shown(want)

    if on_windows():
        return windows_shown(want)

    return None


def mac_shown(want):
    from eyes.tabs import MAC_SAFARI, awake  # LATE: eyes.tabs REACHES BACK INTO hands.

    box = screen()
    safe = want.replace('"', "")

    for name in awake():
        recipe = SAFARI_SHOW if name in MAC_SAFARI else CHROMIUM_SHOW
        said = (osascript(recipe.format(name=name, want=safe, box=box)) or "").strip()

        if said:
            return name, said

    return None


def windows_shown(want):
    from hands.controls.commands import powershell

    said = (powershell(WINDOWS_SHOW.format(want=want.replace("'", ""))) or "").strip()

    return ("browser", said) if said else None


def played():
    """SPACE, WHICH IS PLAY AND PAUSE ON EVERY PLAYER THERE IS."""
    if on_mac():
        return osascript(PLAY) is not None

    if on_windows():
        return run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(New-Object -ComObject WScript.Shell).SendKeys(' ')"]
        ) is not None

    return False
