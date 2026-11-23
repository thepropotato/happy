# Happy

A voice agent that lives on your computer, not inside a project folder. Bring your own MCP servers: anything you can add to Claude Code or Codex, Happy can use by voice, with Claude or with a model running on your own machine. Say **"Hey Happy, …"** or hold the **right Option** key (right Ctrl on Windows), and it does the thing, out loud and on screen.

https://github.com/user-attachments/assets/1dd26595-ba60-4191-a712-92f5a7c52670

## What you can say

- "Set the brightness to 20." "Turn the keyboard light off." "Mute."
- "Pause the video." "Next song." "Close this tab." "Switch to the Gmail tab."
- "Open the happy project in VS Code." "Show my resume in Finder."
- "Click Send in Mail." "Type hello into the search box in Spotify." "In Finder, choose View, as List." Happy works the buttons, fields and menus inside an app by their names, even when the app is behind other windows, and says when it could not see the result.
- "Do I have unread WhatsApp messages?" "Find the address I sent my dad." "Tell mom I'll be late."
- "Read my latest emails." (through whichever email MCP server you add) "Summarise this article." "What's on my screen?"
- "Build me a snake game." Happy opens a coding agent in a Terminal window with the task typed in, so you watch it work.
- "Remind me to call the dentist at four." "Remind me to drink water every hour." "Remind me again in ten minutes."
- "What's the weather?" "Will it rain this afternoon?" "How much battery is left?" "Turn the Wi-Fi off."
- "What does my resume say about my last job?" "Delete old notes." "Bring it back."
- "Download a picture of Tyrion Lannister." "Download this" (a link you give, or the page in front).
- "Save that as a routine called morning brief." Then "morning brief", or "run my morning brief every weekday at 7".

## The smile and the panel

Happy's face is its smile, in the bottom-right corner of the screen; drag it anywhere. The smile moves with what Happy is doing: listening, working something out, talking (the mouth follows the voice), pleased when a turn ends, and sorry when one goes wrong. Click it and the panel opens down the right edge of the screen, a quarter of the screen wide. The panel shows the whole conversation, every request with the steps Happy took (click a step to see what went in and what came back) and the answer. There's a box for typing too. The settings open in the same panel. A menu-bar icon opens it as well.

## Install

**Mac** (macOS 13 or later): download [Happy.dmg](https://github.com/thepropotato/happy/releases/latest/download/Happy.dmg), drag Happy into Applications and open it. It isn't signed by Apple yet, so the first time allow it under **System Settings → Privacy & Security → Open Anyway**.

**Windows** (10 or 11): download [Happy-Setup.exe](https://github.com/thepropotato/happy/releases/latest/download/Happy-Setup.exe) and run it. If Windows says it protected your PC, choose **More info → Run anyway**.

On either, the first launch shows a small window with what it's installing (about 3 GB, a few minutes), then opens Happy ready to listen and talk. Every version is on the [releases page](https://github.com/thepropotato/happy/releases).

Or run it from source:

```sh
git clone https://github.com/thepropotato/happy.git && cd happy
./setup.sh          # Windows: .\setup.ps1
```

`setup.sh` installs [uv](https://docs.astral.sh/uv/) and Claude Code if needed, puts a `happy` command in `~/.local/bin`, and starts Happy with its settings open. Setup downloads the speech models (about 500 MB) and the voice before Happy opens, so everything Happy can work out is already filled in: the model it found, WhatsApp, your MCP servers, and macOS permissions. You press **Start Happy**, and only scan a QR code if you want WhatsApp. No developer account or app signing is involved.

## Brains

Happy uses whatever you already have. `happy setup` lists what it finds, best first:

| You have | Happy uses |
|---|---|
| Claude Code, logged in with Pro or Max | Claude, through your own `claude` install. Your Claude Code MCP servers and claude.ai connectors (Gmail, Drive and others) come along. |
| An API key: OpenAI, OpenRouter, Groq, Gemini or any OpenAI-compatible URL | That model |
| Ollama or LM Studio running | The biggest local model that can call tools |

Everyday commands (brightness, volume, the keyboard light, play and pause, tabs, opening and quitting apps, keyboard shortcuts) never touch a model. They're parsed directly, so they're instant and work the same with any brain. Local models get small, purpose-built tools that do the heavy lifting in code. On a 24 GB Mac, `gpt-oss:20b` picks the right tool 25–27 times out of 27 on `evals/choice.py`. "Is my email connected?" and similar are answered from the connections themselves, never by opening an app.

## Talking to it

- **Wake word**: the chime comes the moment you've said the name, about 0.6 s after you start talking, while you're still going. Say its name at the start: "Happy, …" or "Hey Happy, …". Saying the name in passing ("I'm so happy") does nothing. The name is matched by sound, so a name like "Daemon" still wakes it when it's heard as "Damon" or "demon". Speech is transcribed on your computer and only acted on when it addresses Happy.
- **Push-to-talk**: hold the key while you talk. A quick tap listens until you stop speaking. Pressing it while Happy talks cuts it off.
- **Follow-ups**: when Happy asks a question, it listens for the answer without needing its name again.
- **History**: every request, what Happy did and what it answered is kept in `~/.happy/history.db`. It's what the panel shows. `happy history` prints it in the terminal (add words to search).
- **Never silent**: it says "one sec" if a reply is slow to start, a short line when a slow task begins, and what it's still doing during long tasks.
- **Speech, not text**: links, file paths and markdown are never read out. "Here's the link" is spoken, and the link shows in the bubble.

## Remembering, reminders and routines

- **Memory**: when you explain who you mean ("my brother is John Doe in my contacts"), Happy keeps it in `~/.happy/memory.md` without being asked, so tomorrow "my brother" is already known. "Remember …" and "forget …" work for anything else.
- **Reminders** are worked out from your words in code ("at four" is the next four o'clock, "tomorrow at 4" is the afternoon) and said back in full so a wrong guess is heard. They repeat by the hour, the day, weekdays or named days. One missed while Happy was off is said when it starts again. Happy starts at login (a switch under Talking in the settings) so reminders survive a restart.
- **Routines** are a name for a few requests. Saying the name replays them as one request, and a reminder can run one at a set time.

## Connections

- **Your MCP servers.** Paste the install command a service gives for Claude Code or Codex (or its MCP URL, or its JSON) into Services in the settings. Happy registers it in Claude Code's user list, so it's there for every model. Servers you already set up in Claude Code, Codex, Claude Desktop, Cursor, VS Code or Windsurf show up on their own. Each one shows whether it really answers. Servers that need a sign-in get a **Sign in** button: with Claude as the model it opens Claude Code's MCP screen, otherwise Happy signs in through your browser itself. ChatGPT-authenticated Codex servers only work inside Codex. Local models get a service's tools directly, while they fit.
- **Email** comes from an email MCP server. With Claude, the claude.ai Gmail connector works as it is. Google's official Gmail server (`gmailmcp.googleapis.com`) is a preset in Setup. Google asks each person to bring their own OAuth client for it and keeps it in a developer preview. It searches, reads, labels and drafts mail, but doesn't send.
- **WhatsApp** ships with Happy, in `whatsapp_server`, since nobody else serves it. It runs in its own Python environment under `~/.happy/envs` and keeps its data in `~/.happy/whatsapp`. Link it once from Setup by scanning the QR code, like WhatsApp Web.
- **Happy's own WhatsApp chat**: once WhatsApp is linked, Happy makes a group with its name and nobody else in it. Write there from your phone and Happy does it on the computer and answers in the chat, without speaking aloud. It only takes messages from your own account. Turn it off with `own_chat = false` under `[whatsapp]` in the config.
- **Pages in your Chrome.** Setup downloads [agent-browser](https://github.com/vercel-labs/agent-browser) (no Homebrew or Node needed), and Happy works pages through it in your own Chrome, signed in as you. Only Chrome can switch it on: **Open** next to Chrome pages under Privacy in the settings takes you to the switch, then allow the prompt Chrome shows the first time. Until then, pages are worked through accessibility, which reaches less.
- **Coding** goes to the first agent installed (Claude Code, Codex, Gemini CLI, Cursor Agent, opencode, Qwen Code or Amp), opened in a visible Terminal.

Setup installs Claude Code if it's missing. It keeps the list of services, and no subscription is needed for that.

## Make it yours

```sh
happy name Jarvis                         # the name is the wake word
happy persona ~/Downloads/got-s01.srt      # copy the way people talk in any subtitles or script
happy say "Hello there"                    # hear the voice
```

Settings live in `~/.happy/config.toml`: `voice` (14 Kyutai Pocket TTS voices), `push_to_talk`, `wake_word`, `call_me` (what Happy calls you, like "my lord"), `start_at_login`, `brain`, `input.device`.

**Speaking speed**: choose 0.75x, 1x (the default), 1.25x, 1.5x or 1.75x under **Voice and ears**, or tap the speed pill on the reply while Happy speaks. The pill cycles through the steps and wraps to 0.75x. Say or type "talk faster", "slow down", "normal speed", or "set the speed to 1.5" to change it without a model. All three controls save the same `speech_speed` float in `~/.happy/config.toml`; other numeric values snap to the nearest step. Changes affect the unplayed part of a reply and keep the voice's pitch.

**Personality**: under Talking in the settings, describe how Happy should talk ("like a knight from Game of Thrones"), or paste a whole script or subtitles. A long paste is learned from a sample into short style notes, and only those notes are used, so pasting a book costs nothing at runtime. Saying "from now on, talk like a pirate" or "talk normally again" does the same by voice. Either takes effect on the next reply.

Remembered facts go in `~/.happy/memory.md`, the persona in `~/.happy/persona.md`, and secrets in `~/.happy/secrets.toml` (readable only by you).

**Help make Happy better** (off by default, in the settings or `share_usage = true`): each turn sends anonymous counts to PostHog, namely how it was asked, which tools ran (services you added are just "mcp"), how long it took, whether it failed or went silent, the model name, OS and Happy version. Never your words, replies, tool arguments, files or contacts. The settings show the last one sent, and `happy/usage.py` is the whole of it.

## Commands

| | |
|---|---|
| `happy` / `happy run` | run with the mascot, logging to this terminal |
| `happy start` / `happy stop` | run in the background / stop it |
| `happy ask "…"` / `happy chat` | type instead of talking (`--voice` to hear the answers) |
| `happy setup` / `happy doctor` | start Happy on its settings / check every connection |
| `happy history [words]` | past requests and answers |

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
| `happy/app.py` | one running Happy: a turn from request to spoken answer |
| `happy/cli.py` | the `happy` command |
| `happy/history.py` | the local conversation history, and what Happy moved to the Trash |
| `happy/timing.py`, `happy/reminders.py`, `happy/routines.py` | spoken times, reminders and routines, kept in the same database |
| `happy/speech` | microphone listener, transcription, "was that said to Happy?", the voice, text made speakable, model downloads |
| `happy/agent` | quick commands that skip the model, the prompt, the Claude and OpenAI-compatible backends, choosing one |
| `happy/tools` | every action, each defined once and handed to every backend |
| `happy/integrations` | MCP client with OAuth sign-in, servers found in other apps, adding your own, WhatsApp, connection status |
| `happy/system` | macOS and Windows system calls, and the controls inside apps: the Accessibility API on macOS, UI Automation on Windows |
| `happy/ui` | the windows (`overlay.py`), the settings behind the panel, the talk key, and `web/`: the panel and the smile as HTML, CSS and JavaScript, shown in Qt's web view |
| `whatsapp_server` | the WhatsApp bridge and MCP server Happy ships with |
| `evals` | tool-choice benchmark with every tool mocked |

Speech-to-text, voice and wake-up run on your computer. Only the text of a request goes to the brain you chose.

## Status

macOS (Apple Silicon) is the tested platform. Windows has the same structure, but its controls haven't been run on real hardware yet. Linux runs the core but lacks most system controls.

```sh
uv run pytest -q                 # tests (ears and voice use recorded clips, no mic or speaker)
uv run python evals/choice.py    # tool choice on the local model
uv run python evals/choice.py claude sonnet   # the same on Claude, through your Claude Code login
```

## Credits

The panel's text is set in [Inter](https://rsms.me/inter/) (SIL Open Font License, `happy/ui/web/fonts`). Answers are drawn with [marked](https://marked.js.org) (MIT) and cleaned by [DOMPurify](https://github.com/cure53/DOMPurify) (Apache 2.0 / MPL 2.0).

## Privacy and security

Happy has no account and no server of its own. What it keeps stays in `~/.happy`, which it makes readable by your account alone. The [privacy policy](website/privacy.html) lists everything that leaves your computer and where it goes, and the [terms](website/terms.html) cover using Happy and the services it connects to. To report a security problem privately, see [SECURITY.md](SECURITY.md).

## Support

Happy is free and always will be. If it saves you time, you can support it on [GitHub Sponsors](https://github.com/sponsors/thepropotato).

## License

MIT. See [LICENSE](LICENSE).
