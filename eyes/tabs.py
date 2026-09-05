"""EVERY PAGE OPEN IN EVERY BROWSER, WHICH NO WINDOW TITLE EVER SHOWS."""

from hands.controls.commands import on_mac, on_windows, osascript, powershell

SPLIT = "\x1f"

MOST = 60

# THE NAME APPLESCRIPT KNOWS EACH ONE BY. SAFARI ALONE CALLS A TAB'S TITLE name.
MAC_CHROMIUM = (
    "Google Chrome",
    "Google Chrome Canary",
    "Chromium",
    "Brave Browser",
    "Microsoft Edge",
    "Opera",
    "Opera GX",
    "Vivaldi",
    "Arc",
)

MAC_SAFARI = ("Safari", "Safari Technology Preview")

WINDOWS_BROWSERS = ("chrome", "msedge", "brave", "opera", "vivaldi", "firefox")


CHROMIUM_TABS = """tell application "{name}"
    set found to ""
    repeat with w in windows
        repeat with t in tabs of w
            set found to found & (title of t) & "{split}" & (URL of t) & linefeed
        end repeat
    end repeat
    return found
end tell"""

SAFARI_TABS = """tell application "{name}"
    set found to ""
    repeat with w in windows
        repeat with t in tabs of w
            set found to found & (name of t) & "{split}" & (URL of t) & linefeed
        end repeat
    end repeat
    return found
end tell"""

WINDOWS_TABS = """
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
foreach ($p in Get-Process | Where-Object {{ '{names}' -split ',' -contains $_.ProcessName }}) {{
  if ($p.MainWindowHandle -eq 0) {{ continue }}
  $root = [System.Windows.Automation.AutomationElement]::FromHandle($p.MainWindowHandle)
  if (-not $root) {{ continue }}
  $cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::TabItem)
  foreach ($t in $root.FindAll('Descendants', $cond)) {{
    Write-Output ($t.Current.Name + '{split}')
  }}
}}"""


def open_now():
    """EVERY TAB AS (BROWSER, TITLE, ADDRESS). EMPTY WHEN NO BROWSER IS RUNNING."""
    try:
        if on_mac():
            return mac_tabs()

        if on_windows():
            return windows_tabs()
    except Exception:
        return []

    return []


def awake():
    """THE BROWSERS ALREADY RUNNING, SO ASKING ONE NEVER STARTS IT."""
    # A BROWSER FULLSCREEN ON ANOTHER DESKTOP IS OFTEN LISTED AS UNTITLED FURNITURE, SO
    # HAVING A WINDOW IS THE WRONG TEST AND ITS TABS WENT MISSING ALONG WITH THE WINDOW.
    from AppKit import NSWorkspace

    from eyes.naming import wording

    here = {
        wording(app.localizedName())
        for app in NSWorkspace.sharedWorkspace().runningApplications()
    }

    return [name for name in MAC_CHROMIUM + MAC_SAFARI if name in here]


def mac_tabs():
    found = []

    for name in awake():
        recipe = SAFARI_TABS if name in MAC_SAFARI else CHROMIUM_TABS
        said = osascript(recipe.format(name=name, split=SPLIT))

        for line in (said or "").splitlines():
            if SPLIT not in line:
                continue

            title, address = line.split(SPLIT, 1)

            if title.strip():
                found.append((name, title.strip(), address.strip()))

    return found[:MOST]


def windows_tabs():
    """TITLES ONLY: UI AUTOMATION NAMES A TAB BUT NEVER HANDS OVER ITS ADDRESS."""
    said = powershell(WINDOWS_TABS.format(names=",".join(WINDOWS_BROWSERS), split=SPLIT))
    found = []

    for chunk in (said or "").split(SPLIT):
        title = chunk.strip()

        if title:
            found.append(("browser", title, ""))

    return found[:MOST]


def worded(found):
    """THE TABS AS LINES SOMEBODY COULD READ OUT."""
    return "\n".join(
        f'{browser} — "{title}"{f" ({address})" if address else ""}'
        for browser, title, address in found
    )


FRONT_TAB = """tell application "{name}"
    if (count of windows) is 0 then return ""
    return (URL of active tab of front window)
end tell"""

SAFARI_FRONT = """tell application "{name}"
    if (count of documents) is 0 then return ""
    return (URL of front document)
end tell"""


def front(browser):
    """THE ADDRESS OF THE TAB BEING LOOKED AT IN THIS BROWSER, OR "". A WINDOW TITLE NAMES A
    PAGE AND NEVER SAYS WHERE IT IS, AND WHERE IT IS IS WHAT A LINK IS."""
    if not on_mac() or browser not in MAC_CHROMIUM + MAC_SAFARI:
        return ""

    recipe = SAFARI_FRONT if browser in MAC_SAFARI else FRONT_TAB

    try:
        return (osascript(recipe.format(name=browser)) or "").strip()
    except Exception:
        return ""
