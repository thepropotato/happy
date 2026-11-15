# Sets Happy up on Windows: Python environment, speech models, brain, and a `happy` command.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv (the Python package manager Happy uses)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Claude Code, which keeps your list of MCP services (no subscription needed for that)..."
    powershell -ExecutionPolicy ByPass -c "irm https://claude.ai/install.ps1 | iex"
}

# AGENT-BROWSER IS ONE FILE PER SYSTEM ON ITS RELEASES, SO NODE IS NOT NEEDED.
$agentBrowser = "$env:USERPROFILE\.local\bin\agent-browser.exe"
if (-not (Get-Command agent-browser -ErrorAction SilentlyContinue) -and -not (Test-Path $agentBrowser)) {
    Write-Host "Getting agent-browser, which lets Happy work inside pages in your own Chrome..."
    New-Item -ItemType Directory -Force -Path (Split-Path $agentBrowser) | Out-Null
    try {
        Invoke-WebRequest -UseBasicParsing -OutFile $agentBrowser `
            "https://github.com/vercel-labs/agent-browser/releases/download/v0.43.0/agent-browser-win32-x64.exe"
    } catch {
        Remove-Item -Force -ErrorAction SilentlyContinue $agentBrowser
        Write-Host "agent-browser could not be downloaded; pages are worked through UI Automation instead, and setup will try again next time."
    }
}

uv sync --quiet
$bin = "$env:USERPROFILE\.local\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
Set-Content -Path "$bin\happy.cmd" -Value "@`"$PSScriptRoot\.venv\Scripts\happy.exe`" %*"

uv run happy setup
