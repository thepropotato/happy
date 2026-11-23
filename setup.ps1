# Sets Happy up on Windows: Python environment, speech models, brain, and a `happy` command.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# THE WINDOWS SETUP WINDOW READS ":: <percent> <text>" LINES; A PERSON IN A TERMINAL JUST SEES THE TEXT.
function Step($percent, $text) {
    if ($env:HAPPY_SETUP_PROGRESS) { Write-Host ":: $percent $text" } else { Write-Host $text }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Step 2 "Installing uv, the Python package manager Happy uses"
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Step 5 "Installing Claude Code, which keeps your list of MCP services (no subscription needed for that)"
    powershell -ExecutionPolicy ByPass -c "irm https://claude.ai/install.ps1 | iex"
    if ($LASTEXITCODE -ne 0) { Write-Host "Claude Code could not be installed right now. Happy works without it; setup will try again next time." }
}

# AGENT-BROWSER IS ONE FILE PER SYSTEM ON ITS RELEASES, SO NODE IS NOT NEEDED.
$agentBrowser = "$env:USERPROFILE\.local\bin\agent-browser.exe"
if (-not (Get-Command agent-browser -ErrorAction SilentlyContinue) -and -not (Test-Path $agentBrowser)) {
    Step 10 "Getting agent-browser, which lets Happy work inside pages in your own Chrome"
    New-Item -ItemType Directory -Force -Path (Split-Path $agentBrowser) | Out-Null
    try {
        Invoke-WebRequest -UseBasicParsing -OutFile $agentBrowser `
            "https://github.com/vercel-labs/agent-browser/releases/download/v0.43.0/agent-browser-win32-x64.exe"
    } catch {
        Remove-Item -Force -ErrorAction SilentlyContinue $agentBrowser
        Write-Host "agent-browser could not be downloaded; pages are worked through UI Automation instead, and setup will try again next time."
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "::error uv could not be installed. Check the internet connection and try again."
    exit 1
}

Step 14 "Installing Happy's Python packages (the longest part)"
uv sync --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "::error Installing Happy's Python packages failed. Check the internet connection and try again."
    exit 1
}
$bin = "$env:USERPROFILE\.local\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
Set-Content -Path "$bin\happy.cmd" -Value "@set PYTHONUTF8=1`r`n@`"$PSScriptRoot\.venv\Scripts\happy.exe`" %*"

# THE SPEECH MODELS AND THE VOICE COME NOW, SO HAPPY'S FIRST WINDOW CAN LISTEN AND TALK STRAIGHT AWAY.
# ITS WARNINGS GO TO STDERR, WHICH "STOP" WOULD TURN INTO A FAILURE, SO ONLY ITS EXIT CODE DECIDES.
$env:PYTHONUTF8 = "1"
$ErrorActionPreference = "Continue"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m happy prepare
if ($LASTEXITCODE -ne 0) { exit 1 }
$ErrorActionPreference = "Stop"

# THE WINDOWS INSTALLER RUNS SETUP ITSELF AND STARTS HAPPY ITS OWN WAY, SO IT ASKS FOR SETUP ALONE.
if (-not $env:HAPPY_NO_START) { uv run happy setup }
