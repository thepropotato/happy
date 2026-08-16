# THE ONE LINE. GETS HAPPY, GETS EVERYTHING HE NEEDS, AND LEAVES A SHORTCUT YOU CAN CLICK:
#
#     irm https://raw.githubusercontent.com/thepropotato/happy/main/install.ps1 | iex
#
# Everything it installs goes in one folder, and taking him off again is deleting it.

$ErrorActionPreference = 'Stop'

$Repo = 'https://github.com/thepropotato/happy.git'
$Home_Dir = if ($env:HAPPY_HOME) { $env:HAPPY_HOME } else { Join-Path $HOME '.happy' }

# GIT IS THE ONE THING THAT HAS TO BE HERE ALREADY, BECAUSE IT IS WHAT FETCHES THE REST.
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Happy is fetched with git, and there is none here."
    Write-Host ""
    Write-Host "Get it with:"
    Write-Host "    winget install -e --id Git.Git"
    exit 1
}

if (Test-Path (Join-Path $Home_Dir '.git')) {
    Write-Host "Happy is already in $Home_Dir. Bringing him up to date."
    git -C $Home_Dir pull --ff-only --quiet
} else {
    Write-Host "Putting Happy in $Home_Dir"
    git clone --quiet $Repo $Home_Dir
}

Set-Location -LiteralPath $Home_Dir

# setup.ps1 FINDS A PYTHON AND HANDS OVER TO bones, WHICH DOES ALL THE ACTUAL WORK.
& (Join-Path $Home_Dir 'setup.ps1') @args

exit $LASTEXITCODE
