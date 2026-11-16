# Installs or updates Happy in one line: irm https://raw.githubusercontent.com/thepropotato/happy/main/install.ps1 | iex
& {
    $ErrorActionPreference = "Stop"
    $repo = "https://github.com/thepropotato/happy"
    $dir = if ($env:HAPPY_DIR) { $env:HAPPY_DIR } else { Join-Path $env:USERPROFILE ".happy\app" }
    $git = Get-Command git -ErrorAction SilentlyContinue

    if ($git -and (Test-Path (Join-Path $dir ".git"))) {
        Write-Host "Updating Happy in $dir..."
        git -C $dir pull --ff-only --quiet
    } elseif ($git -and -not (Test-Path $dir)) {
        Write-Host "Getting Happy..."
        git clone --depth 1 --quiet "$repo.git" $dir
    } else {
        Write-Host "Getting Happy..."
        $zip = Join-Path $env:TEMP "happy-main.zip"
        $unpacked = Join-Path $env:TEMP ("happy-main-" + (Get-Random))
        Invoke-WebRequest -UseBasicParsing "$repo/archive/refs/heads/main.zip" -OutFile $zip
        Expand-Archive $zip $unpacked -Force
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Copy-Item (Join-Path $unpacked "happy-main\*") $dir -Recurse -Force
        Remove-Item $zip -Force
        Remove-Item $unpacked -Recurse -Force
    }

    powershell -ExecutionPolicy Bypass -File (Join-Path $dir "setup.ps1")
}
