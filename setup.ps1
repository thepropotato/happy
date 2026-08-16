# GET THIS MACHINE READY FOR HAPPY. EVERYTHING IT DOES IS IN bones\, WHICH NEEDS ONLY THE
# STANDARD LIBRARY, SO THE ONLY JOB HERE IS FINDING A PYTHON NEW ENOUGH TO RUN IT.

$ErrorActionPreference = 'Stop'

Set-Location -LiteralPath $PSScriptRoot

$LeastMinor = 11

function Test-NewEnough($exe, $prefix) {
    try {
        $argv = @($prefix + @('-c', "import sys; sys.exit(0 if sys.version_info[:2] >= (3, $LeastMinor) else 1)"))
        & $exe @argv 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Find-Python {
    # THE LAUNCHER KNOWS ABOUT EVERY PYTHON INSTALLED, AND ASKED THIS WAY IT PICKS THE NEWEST.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($tag in @('-3.14', '-3.13', '-3.12', '-3.11', '-3')) {
            if (Test-NewEnough 'py' @($tag)) {
                return @{ Exe = 'py'; Prefix = @($tag) }
            }
        }
    }

    foreach ($name in @('python3', 'python')) {
        if ((Get-Command $name -ErrorAction SilentlyContinue) -and (Test-NewEnough $name @())) {
            return @{ Exe = $name; Prefix = @() }
        }
    }

    return $null
}

$found = Find-Python

if ($null -eq $found) {
    Write-Host "Happy needs Python 3.$LeastMinor or newer, and there is none here."
    Write-Host ""
    Write-Host "Get it with:"
    Write-Host "    winget install -e --id Python.Python.3.13"
    exit 1
}

$argv = @($found.Prefix + @('-m', 'bones') + $args)

& $found.Exe @argv

exit $LASTEXITCODE
