# Happy's Start menu shortcut runs this: it puts the installed code in ~\.happy\app, sets it up the first time and after an update, then runs Happy.
$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "app"
$base = if ($env:HAPPY_HOME) { $env:HAPPY_HOME } else { Join-Path $env:USERPROFILE ".happy" }
$app = Join-Path $base "app"
$stamp = Join-Path $app ".app-version"
$version = (Get-Content (Join-Path $source ".app-version") -Raw).Trim()

function Trouble($what) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show("$what The details are in $base\install.log.", "Happy couldn't finish setting up", "OK", "Error") | Out-Null
    exit 1
}

New-Item -ItemType Directory -Force -Path $base | Out-Null
$first = @()
$installed = if (Test-Path $stamp) { (Get-Content $stamp -Raw).Trim() } else { "" }
if ($installed -ne $version) {
    if (-not (Test-Path (Join-Path $app ".venv"))) { $first = @("--settings") }
    # THE CODE IS REPLACED WHOLE, BUT ITS PYTHON ENVIRONMENT STAYS, SO AN UPDATE ONLY FETCHES WHAT CHANGED.
    robocopy $source $app /MIR /XD .venv /XF .app-version /NFL /NDL /NJH /NJS /NP | Out-File -Append (Join-Path $base "install.log")
    if ($LASTEXITCODE -ge 8) { Trouble "Its files could not be copied." }
    # SETUP RUNS IN A WINDOW YOU CAN SEE, SINCE THE FIRST TIME TAKES A FEW MINUTES.
    $env:HAPPY_NO_START = "1"
    $setup = Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$app\setup.ps1`"" -Wait -PassThru
    if ($setup.ExitCode -ne 0) { Trouble "Setup stopped partway." }
    Copy-Item (Join-Path $source ".app-version") $stamp -Force
}

$pythonw = Join-Path $app ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) { Trouble "Its Python environment is missing." }
# HAPPY REFUSES A SECOND COPY OF ITSELF, SO OPENING THE SHORTCUT AGAIN WHILE IT RUNS IS HARMLESS.
Start-Process $pythonw -ArgumentList (@("-m", "happy", "run", "--quiet") + $first) -WorkingDirectory $app
