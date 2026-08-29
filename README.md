# Happy

A voice assistant that operates your computer. Hold a key, say what you want, it happens.

Everything runs on your machine — the speech recognition, the model, the voice, the tools.
Nothing about a turn leaves the box unless you connect a service that is somewhere else.

```
  hold the key ─► record ─► transcribe ─► think ─► speak
      ears          ears        ears       brain    voice
                                             │
                                             ▼
                                      hands/ and eyes/
                                      (tools it calls)
```

## What it can do

Happy sees the screen and works the machine: opening apps, clicking and typing, reading files
whatever their format, changing sound and brightness and Wi-Fi, running a shell command,
searching the web. It remembers what you have said to it before.

It also reaches services that are not on this computer — mail, calendar, drive, Notion,
GitHub, Slack, the weather, WhatsApp — but only the ones you connect yourself, in the panel.
Nothing is connected out of the box.

## Install

macOS and Windows are both supported, always. One line:

```sh
curl -fsSL https://raw.githubusercontent.com/thepropotato/happy/main/install.sh | sh
```

```powershell
irm https://raw.githubusercontent.com/thepropotato/happy/main/install.ps1 | iex
```

Everything it installs goes in one folder (`~/.happy`), and uninstalling is deleting it.
You need Python 3.11 or newer and git; the installer will tell you if either is missing.

To run from a clone instead:

```sh
git clone https://github.com/thepropotato/happy.git
cd happy
./setup.sh          # setup.ps1 on Windows
python main.py
```

## Using it

Hold the trigger key, say the thing, let go. There is no wake word — holding a key is already
somebody saying who they are talking to, and it means the microphone is shut the rest of the
time, with the system's own microphone light off to prove it.

The menu bar icon opens a panel: what Happy heard, what it did, the settings, and the services
you can connect.

## How it is built

Every module is a folder named after the part of a person that does the job — `brain` thinks,
`ears` hear, `voice` speaks, `eyes` see, `hands` do, `memory` remembers, `face` shows. There is
exactly one model loop, in `brain/thinking.py`; the folders under `hands/` export tools and
think about nothing.

[HAPPY.md](HAPPY.md) is the full architecture: what each file owns, why the shape is what it
is, and the decisions that have already been made and unmade. Read it before changing anything
structural.

[AGENTS.md](AGENTS.md) is how code in this repo is written. Read it before writing any.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: read `AGENTS.md`, keep files under
200 lines, and make it work on both macOS and Windows.

## License

MIT — see [LICENSE](LICENSE).
