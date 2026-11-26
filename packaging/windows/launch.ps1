# Happy's Start menu shortcut runs this. When Happy is set up for this version it starts him straight away. The first
# time, and after an update, it first shows a window with what is being installed, and opens Happy only once everything
# he needs to listen and talk is on this PC. `launch.ps1 -Work` is that setup itself, run hidden behind the window.
param([switch]$Work)
$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "app"
$base = if ($env:HAPPY_HOME) { $env:HAPPY_HOME } else { Join-Path $env:USERPROFILE ".happy" }
$app = Join-Path $base "app"
$stamp = Join-Path $app ".app-version"
$log = Join-Path $base "install.log"
$version = (Get-Content (Join-Path $source ".app-version") -Raw).Trim()
$pythonw = Join-Path $app ".venv\Scripts\pythonw.exe"
# WINDOWS READS FILES AS CP1252 UNLESS TOLD OTHERWISE, AND HAPPY'S ARE UTF-8.
$env:PYTHONUTF8 = "1"
New-Item -ItemType Directory -Force -Path $base | Out-Null

if ($Work) {
    # NATIVE PROGRAMS WRITE WARNINGS TO STDERR, WHICH "STOP" WOULD TURN INTO A FAILURE; EXIT CODES DECIDE HERE.
    $ErrorActionPreference = "Continue"
    Write-Output "== $(Get-Date) setting up Happy $version"
    Write-Output ":: 1 Copying Happy's files"
    # THE CODE IS REPLACED WHOLE, BUT ITS PYTHON ENVIRONMENT STAYS, SO AN UPDATE ONLY FETCHES WHAT CHANGED.
    robocopy $source $app /MIR /XD .venv /XF .app-version /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -ge 8) { Write-Output "::error Happy's files could not be copied into $app."; exit 1 }
    $env:HAPPY_NO_START = "1"
    $env:HAPPY_SETUP_PROGRESS = "1"
    $env:PYTHONUNBUFFERED = "1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $app "setup.ps1")
    if ($LASTEXITCODE -ne 0) { exit 1 }
    # THE STAMP GOES LAST, SO A SETUP THAT STOPPED PARTWAY RUNS AGAIN ON THE NEXT OPEN.
    Copy-Item (Join-Path $source ".app-version") $stamp -Force
    exit 0
}

function Show-Setup($fresh) {
    # AN UPDATE SAYS SO, AND WHICH VERSION; ONLY A FIRST OPEN IS "GETTING HAPPY READY".
    $script:title = if ($fresh) { "Getting Happy ready" } else { "Updating Happy to $version" }
    $script:blurb = if ($fresh) { "This happens once and takes a few minutes, mostly downloading. Happy opens by himself when it's done." } else { "Getting what the new version needs. Happy opens by himself when it's done." }
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()

    $script:out = Join-Path $base "setup-progress.log"
    $script:problem = ""
    $script:reached = 0.0
    $script:shown = 0.0
    $script:offset = 0
    $script:pending = ""
    $script:worker = $null
    $script:ok = $false
    # WHERE EACH STEP STARTS, SO THE BAR CAN CREEP TOWARDS THE NEXT ONE WHILE A LONG STEP SAYS NOTHING.
    $script:milestones = @(1, 2, 5, 10, 14, 50, 86, 96, 100)
    $font = "Segoe UI"

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Happy"
    $form.ClientSize = New-Object System.Drawing.Size(500, 200)
    $form.FormBorderStyle = "FixedSingle"
    $form.MaximizeBox = $false
    $form.StartPosition = "CenterScreen"
    $form.BackColor = [System.Drawing.Color]::White
    $form.TopMost = $true
    $icon = Join-Path $PSScriptRoot "happy.ico"
    $picture = New-Object System.Windows.Forms.PictureBox
    $picture.SetBounds(24, 26, 64, 64)
    $picture.SizeMode = "Zoom"
    if (Test-Path $icon) {
        $form.Icon = New-Object System.Drawing.Icon($icon)
        $picture.Image = (New-Object System.Drawing.Icon($icon, 64, 64)).ToBitmap()
    }
    $form.Controls.Add($picture)

    $heading = New-Object System.Windows.Forms.Label
    $heading.Text = $script:title
    $heading.Font = New-Object System.Drawing.Font($font, 13, [System.Drawing.FontStyle]::Bold)
    $heading.SetBounds(104, 22, 372, 28)
    $form.Controls.Add($heading)

    $status = New-Object System.Windows.Forms.Label
    $status.Text = "Starting..."
    $status.Font = New-Object System.Drawing.Font($font, 9.5)
    $status.ForeColor = [System.Drawing.Color]::FromArgb(90, 90, 90)
    $status.AutoEllipsis = $true
    $status.SetBounds(104, 54, 372, 20)
    $form.Controls.Add($status)

    $bar = New-Object System.Windows.Forms.ProgressBar
    $bar.Minimum = 0
    $bar.Maximum = 1000
    $bar.SetBounds(104, 80, 372, 18)
    $form.Controls.Add($bar)

    $note = New-Object System.Windows.Forms.Label
    $note.Font = New-Object System.Drawing.Font($font, 9)
    $note.ForeColor = [System.Drawing.Color]::FromArgb(110, 110, 110)
    $note.SetBounds(104, 106, 372, 40)
    $form.Controls.Add($note)

    $quit = New-Object System.Windows.Forms.Button
    $quit.Text = "Quit"
    $quit.SetBounds(104, 156, 90, 28)
    $details = New-Object System.Windows.Forms.Button
    $details.Text = "Show details"
    $details.SetBounds(244, 156, 110, 28)
    $retry = New-Object System.Windows.Forms.Button
    $retry.Text = "Try again"
    $retry.SetBounds(376, 156, 100, 28)
    foreach ($button in @($quit, $details, $retry)) { $button.Visible = $false; $form.Controls.Add($button) }
    $form.AcceptButton = $retry

    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 250

    $begin = {
        $script:problem = ""
        $script:reached = 0.0
        $script:shown = 0.0
        $script:offset = 0
        $script:pending = ""
        $heading.Text = $script:title
        $status.Text = "Starting..."
        $note.Text = $script:blurb
        $bar.Value = 0
        $bar.Visible = $true
        $status.AutoEllipsis = $true
        $status.ForeColor = [System.Drawing.Color]::FromArgb(90, 90, 90)
        $status.SetBounds(104, 54, 372, 20)
        foreach ($button in @($quit, $details, $retry)) { $button.Visible = $false }
        Set-Content -Path $script:out -Value "" -Encoding ASCII
        # CMD WRITES THE FILE, SO NOTHING HERE TURNS STDERR INTO AN ERROR, AND THIS WINDOW NEVER WAITS ON A PIPE.
        $info = New-Object System.Diagnostics.ProcessStartInfo
        $info.FileName = "$env:SystemRoot\System32\cmd.exe"
        $info.Arguments = "/d /c `"`"$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe`" -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Work > `"$($script:out)`" 2>&1`""
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $script:worker = [System.Diagnostics.Process]::Start($info)
        $timer.Start()
    }

    $readNew = {
        try {
            $stream = [System.IO.File]::Open($script:out, "Open", "Read", "ReadWrite")
            try {
                if ($stream.Length -gt $script:offset) {
                    [void]$stream.Seek($script:offset, "Begin")
                    $reader = New-Object System.IO.StreamReader($stream)
                    $script:pending += $reader.ReadToEnd()
                    $script:offset = $stream.Length
                }
            } finally { $stream.Dispose() }
        } catch { return }
        $lines = $script:pending -split "`r?`n"
        $script:pending = $lines[-1]
        if ($lines.Count -lt 2) { return }
        foreach ($line in $lines[0..($lines.Count - 2)]) {
            if ($line -match '^::error (.+)$') { $script:problem = $Matches[1].Trim() }
            elseif ($line -match '^:: (\d+) (.+)$') {
                $script:reached = [Math]::Max($script:reached, [double]$Matches[1])
                $script:shown = [Math]::Max($script:shown, $script:reached)
                $status.Text = $Matches[2].Trim()
            }
        }
    }

    $timer.Add_Tick({
        & $readNew
        # THE LONGEST STEPS SAY NOTHING FOR MINUTES; A BAR THAT STILL MOVES TELLS YOU NOTHING HAS FROZEN.
        $next = ($script:milestones | Where-Object { $_ -gt $script:reached } | Select-Object -First 1)
        if (-not $next) { $next = 100 }
        $ceiling = $next - 0.5
        if ($script:shown -lt $ceiling) { $script:shown += ($ceiling - $script:shown) * 0.003 }
        $bar.Value = [int][Math]::Min(1000, $script:shown * 10)
        if ($script:worker -and $script:worker.HasExited) {
            $timer.Stop()
            & $readNew
            if ($script:worker.ExitCode -eq 0) {
                $script:ok = $true
                $bar.Value = 1000
                $status.Text = "Happy is ready"
                $form.Close()
                return
            }
            $heading.Text = "Happy couldn't finish setting up"
            # THE REASON TAKES THE BAR'S PLACE AND WRAPS, SINCE IT IS WHAT THE PERSON NEEDS TO READ WHOLE.
            $bar.Visible = $false
            $status.AutoEllipsis = $false
            $status.ForeColor = [System.Drawing.Color]::Black
            $status.SetBounds(104, 54, 372, 48)
            $status.Text = if ($script:problem) { $script:problem } else { "Setup stopped partway." }
            $note.Text = "Nothing is lost: trying again picks up where it stopped. The details are in $log."
            foreach ($button in @($quit, $details, $retry)) { $button.Visible = $true }
            $form.Activate()
        }
    })

    $retry.Add_Click({ & $begin })
    $details.Add_Click({ Start-Process notepad.exe -ArgumentList "`"$log`"" })
    $quit.Add_Click({ $form.Close() })
    $form.Add_Shown({ $form.TopMost = $false; $form.Activate(); & $begin })
    $form.Add_FormClosing({
        $timer.Stop()
        # CLOSING THE WINDOW STOPS THE SETUP; WHAT IT ALREADY FETCHED STAYS FOR NEXT TIME.
        if ($script:worker -and -not $script:worker.HasExited) {
            Start-Process "$env:SystemRoot\System32\taskkill.exe" -ArgumentList "/T", "/F", "/PID", $script:worker.Id -WindowStyle Hidden -Wait
        }
        if (Test-Path $script:out) { Get-Content $script:out | Add-Content $log }
    })
    [void]$form.ShowDialog()
    return $script:ok
}

function Trouble($what) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show("$what The details are in $base\happy.log.", "Happy couldn't start", "OK", "Error") | Out-Null
    exit 1
}

$first = @()
$installed = if (Test-Path $stamp) { (Get-Content $stamp -Raw).Trim() } else { "" }
if ($installed -ne $version -or -not (Test-Path $pythonw)) {
    if (-not (Test-Path (Join-Path $app ".venv"))) { $first = @("--settings") }
    if (-not (Show-Setup ($first.Count -gt 0))) { exit 1 }
}

if (-not (Test-Path $pythonw)) { Remove-Item -Force -ErrorAction SilentlyContinue $stamp; Trouble "Its Python environment is missing; open Happy again to set it up." }
# WHERE HAPPY IS INSTALLED, SO HE CAN RUN A NEWER INSTALLER WHEN AN UPDATE COMES.
$env:HAPPY_INSTALLED = $PSScriptRoot
# HAPPY REFUSES A SECOND COPY OF ITSELF, SO OPENING THE SHORTCUT AGAIN WHILE IT RUNS IS HARMLESS.
$happy = Start-Process $pythonw -ArgumentList (@("-m", "happy", "run", "--quiet") + $first) -WorkingDirectory $app -PassThru
# PYTHONW HAS NO CONSOLE, SO A HAPPY THAT DIES AS HE STARTS WOULD OTHERWISE JUST NEVER APPEAR. EXIT CODE 3 MEANS
# HAPPY ALREADY SHOWED WHY HIMSELF.
if ($happy.WaitForExit(20000) -and $happy.ExitCode -ne 0 -and $happy.ExitCode -ne 3) { Trouble "Happy stopped as he was starting." }
