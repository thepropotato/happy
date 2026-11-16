# Security

Happy acts on your computer, reads your messages and holds your keys, so a security problem in it matters. Thank you for reporting one.

## Reporting a vulnerability

Please report it privately, not in a public issue:

1. Go to [Report a vulnerability](https://github.com/thepropotato/happy/security/advisories/new) on this repository.
2. Describe what you found, how to reproduce it, and what someone could do with it.

You'll get an answer within 7 days. Once a fix is released, the advisory is published with credit to you, unless you'd rather stay anonymous. Please give us a reasonable time to fix it before you talk about it publicly.

## Supported versions

Only the [latest release](https://github.com/thepropotato/happy/releases/latest) and the `main` branch get security fixes.

## In scope

- The Happy app and its setup scripts (`happy/`, `setup.sh`, `setup.ps1`, `packaging/`)
- The bundled WhatsApp bridge and MCP server (`whatsapp_server/`)
- The website (`website/`)

Out of scope: problems in the model providers, MCP servers, coding agents or other software Happy talks to (report those to their makers); attacks that need someone already signed in as you on your computer; and the builds not being code-signed yet, which is known.

## How Happy protects what it keeps

- Everything Happy keeps is in `~/.happy` (`%USERPROFILE%\.happy` on Windows). On macOS and Linux Happy makes that folder readable by your account alone, and `secrets.toml` and OAuth sign-ins are written readable by you alone.
- A key you paste into the settings is saved and never sent back to the settings window, so it is never shown again.
- The WhatsApp bridge listens only on `127.0.0.1`, refuses requests addressed to any other host name (so a web page cannot reach it through DNS rebinding), and answers only callers that hold a random key Happy keeps in `secrets.toml`.
- OAuth sign-ins come back to a one-time listener on `127.0.0.1` and `::1` only.
- Speech is turned into text on your computer, and audio is never saved.
- Usage sharing is off by default, and `happy/usage.py` is all of it. See the [privacy policy](website/privacy.html).

## Checking a download

Releases are not code-signed yet. Download Happy only from the [releases page](https://github.com/thepropotato/happy/releases) or the website's download buttons, which point there. Each release has a `SHA256SUMS.txt`. Compare it with `shasum -a 256 Happy.dmg` on a Mac, or `Get-FileHash Happy-Setup.exe` in PowerShell.
