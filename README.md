# Happy

A voice agent that lives on your computer, not inside a project folder. Say **"Hey Happy, …"** or hold the **right Option** key (right Ctrl on Windows), and it does the thing, out loud and on screen:

- "Set the brightness to 20." "Turn the keyboard light off." "Mute."
- "Pause the video." "Next song." "Close this tab." "Switch to the Gmail tab."
- "Open the happy project in VS Code." "Show my resume in Finder."
- "Do I have unread WhatsApp messages?" "Find the address I sent my dad." "Tell mom I'll be late."
- "Read my latest emails." "Summarise this article." "What's on my screen?"
- "Build me a snake game." Happy opens a coding agent in a Terminal window with the task typed in, so you watch it work.

A small mascot sits in the corner of the screen. You can drag it anywhere, and it shows what Happy is doing: listening, thinking, working, speaking. A bubble beside it shows your words, the step in progress and the answer, with links you can click.

## Install

```sh
git clone <this repo> happy && cd happy
./setup.sh          # Windows: .\setup.ps1
happy               # or: happy start, to run it in the background
```

Setup installs [uv](https://docs.astral.sh/uv/) if needed, downloads about 500 MB of speech models, asks which brain to use, and puts a `happy` command in `~/.local/bin`. No developer account or app signing is involved.

On macOS, grant your terminal **Microphone**, **Accessibility** (for the push-to-talk key, typing and clicking), **Screen Recording** (for "what's on my screen") and **Automation** (for Chrome, Safari, Finder and Terminal) when asked.

## Brains

Happy uses whatever you already have. `happy setup` lists what it finds, best first:

| You have | Happy uses |
|---|---|
| Claude Code, logged in with Pro or Max | Claude, through your own `claude` install. Your Claude Code MCP servers and claude.ai connectors (Gmail, Drive and others) come along. |
| An API key: OpenAI, OpenRouter, Groq, Gemini or any OpenAI-compatible URL | That model |
| Ollama or LM Studio running | The biggest local model that can call tools |

Everyday commands (brightness, volume, the keyboard light, play and pause, tabs, opening and quitting apps, keyboard shortcuts) never touch a model. They're parsed directly, so they're instant and work the same with any brain. Local models get small, purpose-built tools that do the heavy lifting in code. On a 24 GB Mac, `gpt-oss:20b` picks the right tool 19–20 times out of 20 on `bench/choice.py`.

## Talking to it

- **Wake word**: say its name at the start: "Happy, …" or "Hey Happy, …". Saying the name in passing ("I'm so happy") does nothing. Speech is transcribed on your computer and only acted on when it addresses Happy.
- **Push-to-talk**: hold the key while you talk. A quick tap listens until you stop speaking. Pressing it while Happy talks cuts it off.
- **Follow-ups**: when Happy asks a question, it listens for the answer without needing its name again.
- **Never silent**: it says "one sec" if a reply is slow to start, a short line when a slow task begins, and what it's still doing during long tasks.
- **Speech, not text**: links, file paths and markdown are never read out. "Here's the link" is spoken, and the link shows in the bubble.

## Connections

- **WhatsApp** comes from the separate `whatsapp-mcp` server. Setup finds it next to this folder, or you point `whatsapp.path` at it. Happy runs it in its own environment under `~/.happy/envs`.
- **Email** works with any provider over IMAP with an app password: `happy connect mail`.
- **MCP servers** already set up for Claude Code, Claude Desktop, Cursor, VS Code or Windsurf are picked up automatically. Claude uses them directly. Local models search them with `find_service_tool`.
- **Coding** goes to the first agent installed (Claude Code, Codex, Gemini CLI, Cursor Agent, opencode, Qwen Code or Amp), opened in a visible Terminal. Without one, Happy pastes the task into the Claude app. With neither, it says it can't.

## Make it yours

```sh
happy name Jarvis                         # the name is the wake word
happy persona ~/Downloads/got-s01.srt      # copy the way people talk in any subtitles or script
happy say "Hello there"                    # hear the voice
```

Settings live in `~/.happy/config.toml`: `voice` (14 Kyutai Pocket TTS voices), `push_to_talk`, `wake_word`, `brain`, `input.device`. Remembered facts go in `~/.happy/memory.md`, the persona in `~/.happy/persona.md`, and secrets in `~/.happy/secrets.toml` (readable only by you).

## Commands

| | |
|---|---|
| `happy` / `happy run` | run with the mascot, logging to this terminal |
| `happy start` / `happy stop` | run in the background / stop it |
| `happy ask "…"` / `happy chat` | type instead of talking (`--voice` to hear the answers) |
| `happy setup` / `happy doctor` | choose things / check everything is in place |
| `happy connect mail` / `happy connect whatsapp` | connect a service |

## How it works

```
mic ──► Silero VAD ──► Parakeet (speech to text, on the CPU) ──► addressed to Happy?
                                                                   │
                         everyday command? ──yes──► run it directly ─┤
                                │ no                                 │
                                ▼                                    ▼
                  brain: Claude (Agent SDK) or any            Pocket TTS, streamed
                  OpenAI-compatible endpoint  ──tools──►      sentence by sentence
                                                                   │
                                          mascot + bubble ◄────────┘
```

| Folder | What's in it |
|---|---|
| `happy/ears` | microphone, speech detection, transcription, the "said to Happy?" check |
| `happy/voice` | Pocket TTS playback, and turning text into something worth saying |
| `happy/brain` | the fast command parser, the Claude brain, the OpenAI-compatible brain, the prompt |
| `happy/tools` | every action, each defined once and given to every brain |
| `happy/connectors` | MCP client, WhatsApp server launcher, MCP servers found in other apps |
| `happy/face` | the mascot, the bubble, the push-to-talk key |
| `happy/platforms` | macOS and Windows system calls |
| `bench` | tool-choice benchmark with every tool mocked |

Speech-to-text, voice and wake-up run on your computer. Only the text of a request goes to the brain you chose.

## Status

macOS (Apple Silicon) is the tested platform. Windows has the same structure, but its controls haven't been run on real hardware yet. Linux runs the core but lacks most system controls.

```sh
uv run pytest -q                 # tests (ears and voice use recorded clips, no mic or speaker)
uv run python bench/choice.py    # tool choice on the local model
```
