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

uv sync --quiet
$bin = "$env:USERPROFILE\.local\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
Set-Content -Path "$bin\happy.cmd" -Value "@`"$PSScriptRoot\.venv\Scripts\happy.exe`" %*"

uv run happy setup
