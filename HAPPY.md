# Happy

## Who Happy is

Happy Hogan drove Tony Stark's car, ran his security, and carried his calendar. Later he
did the same for a fifteen year old from Queens who kept calling him at two in the morning.
He was never the smartest person in the room and never tried to be. What he was, reliably,
was *there* — you said the thing, and the thing got handled.

That is the whole personality brief, and it is not decoration. Every design decision in this
project falls out of it:

- **He does it, he doesn't explain it.** Asked to open a folder, Happy opens the folder. He
  does not describe the folder, offer three ways to open it, or read the path out loud.
- **He is brief.** Happy is *heard*, not read. Two spoken sentences is a long answer. No
  markdown, no bullet points, no code blocks, no emoji — none of that survives a speaker.
- **He asks before he breaks something.** Happy will drive you anywhere. He will not drive
  the car into a wall because he thought that's what you said.
- **He does not stall.** A pause that would be invisible in a chat window is unbearable out
  loud. Latency is a correctness property here, not a nice-to-have.

When a design choice is genuinely close, pick the one Happy would make.

## What this is

A voice assistant that operates this computer. Hold a key, say what you want, it happens.
It runs entirely on your machine — the speech recognition, the model, the tools. Nothing
leaves the box.

Target platforms are macOS and Windows. Both, always. A feature that only works on one is
not finished.

## How one turn works

```
  hold key ─► record ─► transcribe ─► graph ─► speak
   controls   audio/    audio/stt    brain.py  audio/tts
              recorder                  │
                                        ▼
                                   agents/*.py
                                  (tools it calls)
```

1. `controls.py` watches globally for the push-to-talk key. Global, so the terminal does not
   have to be the focused window — on macOS that needs Accessibility permission.
2. `audio/recorder.py` keeps the microphone stream open for the life of the process and only
   gates whether it *keeps* what it hears. Opening a device costs about a tenth of a second,
   which is enough to swallow your first word. Each take is padded at both ends because
   nobody presses a key exactly on the first syllable.
3. `audio/stt.py` runs WhisperX locally. The model is loaded at startup so the first take
   isn't the one that pays for it.
4. `brain.py` runs the transcribed speech through the graph. The model may call tools; when it is
   done it streams an answer back in pieces.
5. `audio/tts.py` speaks those pieces as they land. It gathers them until a sentence ends,
   then sends that sentence to be spoken while the next one is still being written. Waiting
   for the whole answer first would add all of the model's thinking to the silence.

## Layout

| File | What it owns |
| --- | --- |
| `main.py` | The loop. Hold, speak, release, hear an answer. Nothing else. |
| `brain.py` | The graph. Speech in, spoken answer out, tools called along the way. |
| `llm.py` | Which model, at which URL, told what. The system prompt lives here too. |
| `providers.py` | The backends. One entry each, and the only file that knows a server's habits. |
| `agents/__init__.py` | The registry. Collects every tool from every module into one flat list. |
| `agents/system.py` | The machine: what's installed, what it is, opening apps and paths. |
| `agents/files.py` | Finding files and reading what is inside them, whatever the format. |
| `agents/vision.py` | Seeing: text off a picture or off the screen, and where on the screen it is. |
| `agents/desktop.py` | The pointer and the keyboard. Clicking what `vision.py` found. |
| `agents/bash.py` | The shell. One command in, what it printed back out. |
| `agents/browser.py` | The browser errand: starts it, watches it, reports back — and, below the line in the same file, runs it in a child process. |
| `audio/recorder.py` | Microphone capture, one WAV per take. |
| `audio/stt.py` | Speech to text. |
| `audio/tts.py` | Saying it out loud: the voice, sentence streaming, playback, barge-in. |
| `controls.py` | Push to talk. |
| `console.py` | What the terminal shows: one block per turn, and where the time went. |
| `chat.py` | The conversation: every message ever, and how to read it back. |
| `store.py` | The database. Owns the file and the schema, nothing else. |
| `logs.py` | Silences the libraries. Must be called before anything imports whisperx. |
| `AGENTS.md` | How to write code in this repo. Read it before you write any. |

## The agent model — read this before adding one

The word "agent" in `agents/` is aspirational. **These are tool namespaces, not minds.**
There is exactly one model loop, in `brain.py`. It sees every tool from every module at
once, calls what it needs, and answers.

The alternative — a supervisor model that routes to a sub-agent, which runs its own loop and
reports back — is the more fashionable shape and the wrong one here. It costs two to three
extra round trips through the model. On a 20B running locally that is several seconds of a
person standing in their kitchen waiting for a sentence. Happy does not stall.

So: **a module here exports tools and thinks about nothing.**

The one exception is the browser, and it now exists. "Find the cheapest flight on Friday" is a
dozen looks and clicks, each one decided by what the last one put on screen, and that does not
belong in the main loop where it would bury every other tool under page text. So it has its
own loop, its own model and its own context — and it *still* exports one ordinary tool,
`browse(task)`. The main graph hands it a sentence and gets an answer back, and never sees the
clicks. **The shape of the registry did not change.**

### Why not MCP

MCP is a transport for tools that live in another process. Every tool here is Python running
on the same machine as the model, so MCP would buy a subprocess and a JSON-RPC hop for
nothing. It becomes worth it the day you want something *else* — Claude Desktop, another
client — driving these same tools, or the day you want the shell tool genuinely sandboxed
rather than pattern-checked. Not before.

### Adding a capability

1. Write `agents/yourthing.py`.
2. Decorate functions with `@tool` from `langchain_core.tools`. **The docstring is the
   prompt** — it is the only thing the model reads to decide whether to call you. Write it as
   plain prose for a reader, say when to use it *and when not to*, and give an example of the
   argument. This is the highest-leverage text in the file.
3. Export `TOOLS = [...]`.
4. Add the module to `MODULES` in `agents/__init__.py`.

That is the whole extension point. A module exporting `TOOLS = []` is valid and registers
nothing, which is a useful way to stub something you have not built yet.

## Things that are easy to get wrong here

**Tool output is not speech.** Whatever a tool returns lands in the model's context and may
end up spoken. Return short, plain, already-summarised text. `agents/bash.py` truncates
command output for exactly this reason.

**Never stream the tool-calling turn.** The model's turn that *decides* on a tool arrives
through the same stream as the answer, as half-built JSON arguments. Streaming it is the
assistant muttering JSON at you. `brain.spoken()` in `brain.py` is the filter that stops
this; if you touch streaming, keep it.

**Speech arrives misheard, not wrong.** "Saffari", "Vishwal Studio Code". Anything that takes
a name from the user should match loosely — see `system.resolve()`.

**But loosely is not the same as certainly.** "slack" and "clock" score exactly 0.6 against
each other, "photoshop" and "Photos" score 0.8, and "word" sits inside "Passwords". Asked
whether Slack was installed, Happy called `open_app` and the Clock appeared. So `resolve()`
returns a name *and whether it is sure*: a short name that starts a word of exactly one app
is sure, a close-but-not-that-close spelling is not, and `open_app` turns the unsure ones
into "did you mean Clock?" instead of opening them. A tool that changes the screen should
never act on a guess it could have asked about. And it says in its own description that it
is not how you check whether an app exists — that is `list_installed_apps`, which opens
nothing.

**Bound the loop.** `MAX_MODEL_CALLS` in `brain.py` caps how many times the model may go
round before it has to answer. A loop that keeps going is a person staring at a silent
assistant, which is worse than a half answer.

**History is trimmed, not kept.** `brain.recent()` keeps the last `HISTORY_MESSAGES`
messages, starting on a human message so a tool reply never appears whose tool call was
trimmed away. That orphan is an API error, not a degradation.

## The voice

**Piper**, and nothing else. One voice module, no engine abstraction — an abstraction with one
implementation is just indirection.

Measured on this machine, warmed: **15 ms to first word**, 56x realtime, ~60 MB on disk. It
sounds less like a person than the heavier options, and that is the trade taken on purpose. A
reply that starts instantly and keeps up reads as someone who knows the answer; one that drags
reads as someone who does not, whatever the timbre.

*Kokoro was the default briefly and has been removed.* It sounds markedly better in isolation
and lost anyway: 264 ms to first word against Piper's 15 ms, and 7x realtime against 56x. In
use that gap is the difference between an assistant and a demo. Judging it from measurements
alone was a mistake — it took hearing both in the loop to settle it.

Phonemes come from an espeak-ng that ships inside the package, so there is nothing to install
besides the voice file and it behaves the same on Windows. Any Piper voice works; drop it in
`models/piper/` and it is picked up. A voice is **two files** — the `.onnx` and its `.onnx.json`
— and half a download is not a voice, so `find()` requires both rather than failing later with
a confusing traceback.

If no voice is there, `tts.create()` returns a `Mute` voice and the reason. Happy carries on
answering in writing, and nothing downstream has to check whether there is a voice.

### How speaking works

Two threads behind a queue each: one turns sentences into sound, the other plays it. They are
separate so sentence three is being synthesised while sentence two is still in the air.

- **The first sentence of a reply goes out fast.** `MIN_CHARS_FIRST` is deliberately tiny, so
  "Done." is said immediately rather than waiting to be joined to the paragraph after it.
  Later sentences use the larger `MIN_CHARS` because by then smoothness beats speed.
- **Abbreviations are not sentence ends.** That short first-sentence floor makes "Mr. Stark
  is on the phone" likely to break in half, so `SHORTENED` and the single-initial rule catch
  it. Decimals are already safe — the split needs whitespace after the full stop.
- **Barge-in is `Speaker.stop()`**, wired to the push-to-talk key going down via the
  `on_press` callback in `controls.py`. It fires from the listener's own thread, because the
  main loop is usually busy exactly when someone decides to interrupt. Everything queued is
  dropped and playback is cut — someone who has started talking has stopped listening, and
  the microphone must not hear Happy either.
- **In-flight work is cancelled by an era counter**, not by trying to kill a thread. `stop()`
  bumps it; work stamped with an older era is thrown away when it surfaces.

## The browser

Built on [browser-use](https://github.com/browser-use/browser-use), driving the local model
text-only (`use_vision=False`) — the accessibility/DOM representation is read as text, so no
vision model is needed. That stays true now that Happy *has* eyes: a web page exposes its own
structure, and reading it beats squinting at a picture of it. Pixels are for what has no such
structure to read. Measured against `gpt-oss:20b`: it correctly read the top story off
Hacker News, in **84 seconds, for a two-step task.** Anything real is minutes.

Three consequences shape the design, and none of them are optional.

**It runs in its own process, out of the one virtualenv.** `browser-use` pins
`openai==2.16.0` exactly, so it cannot sit beside `langchain-openai` 1.4, which wants
`>=2.45.0`. That is a version to pick, not a wall: `langchain-openai==1.1.7` is the pairing
`browser-use` ships in its own `all` extra, and pinning to it resolves the whole tree cleanly.
The price is that Happy's OpenAI-compatible backend is pinned to whatever `browser-use`
tolerates, so a future bump to it may force another. That is worth knowing before bumping.

The child process stays, because the two reasons for it were never about packages. A browser
that crashes cannot take Happy with it, and `browser-use` owns an asyncio loop that has no
business running under a voice assistant. So `agents/browser.py` runs *itself* again with
`--run`, hands the task on argv, and reads back one marked line of JSON. Everything above the
line in that file is Happy's side and never imports `browser-use`; everything below it is the
child's. The task is all that crosses — the child reads the backend out of `llm.py` directly,
the same as every other module.

**It returns immediately.** `browse(task)` starts the job and answers "Started, I will say
when it is done." Happy stays responsive, you keep talking to him, and the job speaks up
unprompted when it lands. That announcement is wired in `main.py` via `browser.announces()`
and **waits for a gap** — it will not cut across you mid-sentence, because being a sentence
late is better than talking over someone. `browsing_status()` covers "is it done yet".

**It needs a real context window.** See below — this is the thing most likely to waste your
afternoon.

**It uses the browser you chose.** `system.drivable_browser()` reads the actual `https`
handler — Launch Services on macOS, the registry on Windows, `xdg-settings` on Linux — and
hands `browser-use` that binary. No hardcoded Chrome. Whether a browser can be driven at all
is answered by looking at it rather than by a list: every Chromium bundle ships its engine as
a framework beside its binary, and nothing else does, so a browser nobody has heard of yet
still answers correctly. Safari and Firefox cannot be driven this way, and then the errand
falls back to whatever Chromium `browser-use` can find.

**One profile per browser**, `~/.happy/browser-<name>`. A Chromium profile belongs to the
brand that made it: hand Chrome's to Opera and you get a browser that starts, drops its
debugging connection half a minute later, and fails as `Cannot navigate - browser not
connected` with nothing saying why. `browser-use` guards its own default directory the same
way. It also means changing default browser leaves the old logins where they are.

One browser, one errand at a time. Logins persist in `~/.happy/browser`, a profile of Happy's
own, so WhatsApp Web is scanned once rather than daily and **nothing Happy does touches your
real browser profile**. That last part is not a choice: **Chromium since 136 refuses a
debugging port on the profile you actually browse with**, and will not open a profile a
running browser already holds — `browser-use` asserts on the first and silently retries into a
temp directory on the second. So an errand gets your browser and a profile you sign into once.
It runs headful on purpose: the first visit to anything worth automating wants a login, and a
QR code nobody can see is a task that hangs forever without saying why.

**If an address alone would do it, this is the wrong tool.** That is `open_url`, below.

## Opening a page: your browser, your profile

`system.open_url` is for anything an address reaches — a site, a video, a search. It lands in
the browser you already use, signed in to your accounts, and it is what "play this on
YouTube" should always have done. Before it existed the model had no tool for an address at
all, so it reached for `open_app` — whose docstring offered **"Safari"** as its example — and
typed into it. An example in a tool description is an instruction.

It addresses your **profile**, not just your application, and that distinction is the whole
point. The system opener hands a link to whichever copy of that browser is already running,
so while a browser errand has one open on Happy's own profile, your link can arrive in a
window signed in to nothing. A Chromium started with no profile flag uses the one you browse
with and forwards the address to that window when it is already open. Safari, Firefox and
unknown platforms fall back to the system opener.

**Do not test this on the exit code.** Opera prints `Opening in existing browser session.`
and exits **24** having done exactly what was asked. A browser that genuinely could not open
the page says so on stderr, so that is what `released()` checks. A quick exit means it
forwarded; still being alive means it *is* the browser now. Both are success.

Telemetry is disabled explicitly in both files. `browser-use` sets `ANONYMIZED_TELEMETRY` to
`'true'` by default and cloud sync follows it, which is not what "completely local" means.

## Swapping the model out

A model here is inference and nothing else. The flow belongs to LangGraph, the tools belong to
`agents/`, the prompt belongs to `llm.py`. What is left is a name, an address and a few
settings — so changing backend is two lines at the top of `llm.py`:

```python
PROVIDER = providers.OLLAMA    # anything in providers.py
URL = None                     # None takes that backend's own default
```

`providers.py` holds one builder per backend and is **the only file that knows a particular
server's habits.** Adding one is writing the builder and putting it in `PROVIDERS`; nothing
else moves. Two things actually differ between them, and both are named there: where the
context length goes, and what the thinking knob is called.

A backend that cannot do something **says so instead of dropping it.** `SETS_CONTEXT` records
whether a request can carry a context length — the OpenAI shape cannot — and `llm.caveat()`
turns that into a line printed at startup. Silence about a dropped setting is the failure mode
this whole file exists to prevent.

The browser is the one place the client is mirrored rather than shared: `browser-use` will not
take a LangChain model, so the child half of `agents/browser.py` maps the same provider name
onto `browser-use`'s own client. Only the client differs — the name comes from `providers.py`
and the model, address and key come from `llm.py`, so the choice is still made in one place.

## The context window, or: why the model looks stupid

Ollama serves **4096 tokens** unless told otherwise, no matter that `gpt-oss:20b` supports
131072. It does not warn you. It just forgets the oldest thing you said.

This is not a tuning knob, it is a correctness bug waiting to happen. One resume PDF read
through `agents/files.py` is ~1250 tokens. A verbose shell command is ~1000. The system prompt
and tool schemas are ~1100 before you open your mouth. browser-use's system prompt **alone is
~6000** and never fit in 4096 at all.

**Happy runs at the full 131072 now**, as `CONTEXT` in `llm.py`, sent with every request.
There is no `Modelfile` and no `ollama create` step. The models are the ones you pulled.

Measured on an M-series with 26 GB: it loads at **12 GB, 100% GPU, no CPU spill**, and replies
in **2.18s against 2.22s at 4096**. It is free. gpt-oss uses sliding-window attention on
alternate layers, so the key-value cache stays small. There was never a reason to run at 4096.

What works and what does not — the first row is the trap, because it looks like it should:

| | Result |
| --- | --- |
| `extra_body={"options": {"num_ctx": N}}` via `/v1` | **Silently ignored.** Still loads at 4096. |
| `ChatOllama(num_ctx=N)` via `/api/chat` | Works. This is what `providers.py` does. |
| A `Modelfile` with `PARAMETER num_ctx N` | Works, and was how this used to be done. |

The Modelfile was the right fix for the wrong problem. It only existed because the OpenAI
`/v1` request has nowhere to put a context length — so the workaround was to bake one into a
copy of the model under another name. Talking to Ollama natively makes it a field on the
request, which deletes a setup step, a second name for the same weights, and a fact that was
only true on the machine where the tag got built. **Prefer a provider's own client over a
compatibility shim**: a shim quietly drops whatever it cannot express, which is exactly how
this cost an afternoon.

The vision model wants the same thing for a sharper reason. `qwen3-vl` thinks before it
answers, and a screenshot is ~1800 tokens of prompt on its own. At 4096 it spends every
remaining token thinking, gets cut off at `finish_reason: length`, and returns **an empty
string** — not an error, not a bad answer, nothing at all, after ninety seconds. Neither
`reasoning_effort` nor `/no_think` reaches it through `/v1`. Natively it is `VISION_EFFORT =
False`, which is a field on the request, plus 32768 of room.

The browser sets its own, deliberately lower at 32768: `num_ctx` is a ceiling rather than a
reservation, but page text expands to fill whatever it is given, and a 130k-token page makes
every step slow for no benefit.

**Always confirm with `ollama ps`.** The CONTEXT column is the only thing in this stack that
tells you the truth.

## The terminal

`console.py` owns everything the terminal shows. One block per turn, separated by a rule and
stamped with the time, so turns never run together.

```
──────────────────────────────────────────────────────────── 17:51:26
you   read my resume and name the top skill on it
happy The top skill listed on your resume is Python.
      heard 710ms │ thought 4.97s │ tools 196ms │ first word 4.95s │ total 5.25s
      · find_files 72ms · read_file 123ms
```

The stats line exists because a voice assistant spends most of a turn doing nothing visible,
so when it feels slow there is no way to tell *which part* was slow. Now there is:

- **heard** — speech to text
- **thought** — the model's own time, with tool waiting subtracted so the two do not double count
- **tools** — total, then each one named on its own line
- **first word** — from the end of your sentence to the first word out. The only latency a
  person actually feels.
- **total** — the whole turn

Tools report themselves from the middleware in `brain.py`, so a tool added later appears here
with nobody wiring it up. `brain.watches()` takes the callback — the brain does not know a
terminal exists, the same way `bash.asks()` and `browser.announces()` work.

**What it immediately showed:** tools are noise (7 ms for `system_info`) and the voice is noise
(15 ms). The model is essentially the entire turn. A question needing a tool costs two model
round trips and lands around 5–12 seconds to first word. That is the number to attack, and no
amount of TTS tuning touches it.

## The conversation

Everything ever said lives in a **SQLite database** at `data/happy.db`. `store.py` owns the
file and the schema; `chat.py` owns what a message is and how it reads back.

One running conversation — not one per day, not one per session, because talking to someone you
live with does not restart at midnight. **The time is a column on the message and never a
heading between messages**, so "what did I say last Tuesday" is a query rather than a parse.

A database rather than a file of lines because the questions worth asking are queries:
*what did I say about the dentist*, *how often does that tool fail*, *what did he do on
Tuesday*. `messages` carries `who`, `text`, `at`, `epoch`, and — on the rows that have them —
`tool`, `args` as JSON, `seconds`, the `audio` path of the recording behind a spoken line, and
`unprompted` for a browser job reporting back on its own.

**There is one table and one index, and that is deliberate.** An FTS5 full-text index lived
here briefly. It worked, and it quietly brought four shadow tables and three triggers with it —
all created by SQLite on your behalf, none of them ever read by anything here. That is a lot of
machinery to avoid a scan that takes **159 ms across two hundred thousand messages**, which is
more than anyone will ever say to Happy. So `chat.search()` is a `LIKE` now.

What that costs: no relevance ranking, and no stemming, so "meet" will not find "meeting". What
it buys: `sqlite_master` has two rows in it and you can read the whole schema at a glance. The
one index stays because it is not a table and it earns its place — asking for the newest fifty
messages is **123 ms without it and 0.1 ms with it** at that same scale.

`%` and `_` are wildcards to `LIKE`, so they are escaped before the search runs. Searching for
"75%" finds the message about response times, not every message.

```sh
python chat.py               # the whole conversation, as a chat
python chat.py --tools       # with the plumbing shown
python chat.py dentist       # full-text search
```

`store.py` gives each thread its own connection, because SQLite objects do not travel between
threads and a browser errand finishing on its own thread writes at the same moment the voice
loop does. WAL mode lets a reader read while a writer writes. A failed write never costs you a
turn. `chat.add(at=...)` exists so messages can be carried in from elsewhere with their own
times on them — everything live leaves it alone and means now.

## Reading files

`agents/files.py` is the answer to "I don't have the ability to read that file", which was a
real gap and not a design choice. `read_file` handles PDF, Word, spreadsheets, presentations,
RTF, and anything textual, and always returns plain text — the model should not have to know
which kind of file it is before it asks.

A person does not say "read `/Users/me/Documents/CV_final_v3.pdf`", they say "read my resume".
So `read_file` takes a description as readily as a path, and `find_files` searches where
people actually put things — Desktop, Documents, Downloads — rather than the whole disk,
pruning `Library`, `node_modules` and friends.

Long files are cut at `MAX_CHARS` with a marker, and `start` reads on from there.

Images used to be **named, not guessed at** — "that's a PNG, I can't see it" was worth more
than a confident hallucination. That is no longer the trade, because OCR is not guessing.
`.png`, `.jpg`, `.bmp`, `.tiff` and `.webp` are now formats like any other in `READERS` and
go to `agents/vision.py`; `.gif` and `.heic` stay named, because OpenCV will not reliably
decode either. Happy still does not *look* at a photograph — he reads the text off it, so a
screenshot of a message reads fine and a picture of a dog comes back empty.

## Seeing the screen

`agents/vision.py` answers two different questions and it matters which is which. **What does
it say** is OCR: exact, and about a second and a half for a full screen. **What does it look
like** is a vision model: several seconds, and needed far less often than it looks. `read_screen`
is the first, `look_at_screen(question)` is the second, and the tool descriptions push the model
towards the cheap one whenever the answer is written on the screen in words.

### Reading a picture

Tesseract, with the preprocessing a screenshot actually needs. A screenshot is the wrong shape
for it: small letters, text scattered in corners rather than flowing down a page, and half the
world in dark mode, which is white on black — the exact inverse of what it expects.

So the picture is fixed before it is read — greyed, enlarged toward 3000px wide because UI text
is ~13px and the LSTM engine wants ~30, evened out, thresholded, deskewed, inverted if the text
turns out to be the light part, and given a white border so no letter touches the edge. **No one
recipe wins on every picture**, so three run against two page modes and each reading is scored
by *expected correct characters* — per-word confidence times length — rather than by confidence
alone, which a recipe can win by finding one perfect word and missing the page. A clean
screenshot clears the bar on the first pass and the rest are skipped.

Measured against generated screenshots with known ground truth: **100%** on a light-mode UI,
**96.2%** on a dark-mode terminal, **96.6%** on a tilted, noisy, JPEG'd photo of a screen. The
first two resolve in under half a second; only the photo pays for all six passes.

**`--psm 6` is a trap and is excluded from the defaults.** It is the mode every tutorial reaches
for, and on a desktop it reads straight across the screen and staples the sidebar onto the end of
a sentence in the main window — then reports the same 95% confidence as a correct reading, so
nothing downstream can tell. Sparse mode is first, page mode second. Blank lines in the output
follow *real vertical gaps*, measured against the picture's own line spacing, because sparse mode
calls every line its own block and would otherwise double-space the whole screen.

### Capture

`grab()` returns a `Shot`: the image, and its **density**. That second field is not decoration.
The grab on this machine is 3024×1964 but the pointer lives in 1512×982, so a click sent at OCR
pixel coordinates lands past the bottom-right corner. Density is derived from the primary
monitor rather than assumed, so it is 1.0 on an unscaled display and 2.0 here.

macOS refuses screen recording **silently** — the grab succeeds and every pixel is black. An
all-black frame is therefore treated as a permission failure with the settings path spelled out,
not as an empty screen. Capture sees the current Space: a full-screen app on another Space is
invisible and cannot be driven.

### Pointing at things

This is the part that makes clicking possible, and the design is one idea: **a vision model
should never be asked for a coordinate.** It is bad at them, and a wrong coordinate is not a
wrong answer, it is a thing that happened somewhere on your desktop. OCR already knows exactly
where it read every word. So `where(target)` escalates and stops at the first step that answers:

1. **The words.** Match the target against what OCR read. No model, no round trip.
2. **The model picks.** The screen text goes up as a numbered menu and the VLM answers with an
   *index*. A right answer is exactly right; a wrong one still lands on something real.
3. **The model points.** Only for what has no text at all — an icon, a switch. Least exact, and
   last.

Matching is scored, not first-hit. An early version resolved `"OUTPUT"` to the sentence *"we may
also feed the OCR output"* — which contains the word exactly as much as a tab labelled OUTPUT
does. A match is now worth **how much of the label it accounts for**, which is all of a button
and almost none of a paragraph. Below the floor, the model is asked; that is slower and better
than a confident wrong click.

## Working the desktop

`agents/desktop.py` is the other half of seeing. `click_on`, `type_text`, `press_keys`, `scroll`.

**No tool here takes a coordinate.** They take a description — "Send", "the search box" — the
screen is read fresh on every call, and the pointer goes where the words actually are. One act
per call, and the screen is never assumed to have stayed still between two of them: a menu that
opened half a second late makes every remembered position a lie. The model looks, does one
thing, and looks again. That costs a grab plus an OCR pass, about two seconds, per act.

The guard is the same shape as the shell's, applied to what is written on the thing being
clicked: delete, send, spend, install, grant permission, quit. `desktop.asks(handler)` is
pluggable exactly like `bash.asks()`, so it becomes a spoken question for free.

The pointer and the keyboard needed nothing new — pynput, screeninfo and Pillow were already
here for push-to-talk and the recorder. Seeing added two: `pytesseract` and
`opencv-python-headless`. **Tesseract itself is not a Python package** and has to be installed
as a program; see below.

**What is verified and what is not.** Clicking is proven end to end on a real UI: a located
panel tab, a click delivered, the screen changing as predicted, and a click back to restore it.
Typing and shortcuts are proven the same way. Step 1 of grounding — which covers most labelled
UI — is working. **Steps 2 and 3 have never run against real weights**, only against stubbed
answers that confirm the parsing and the coordinate scaling; until `qwen3-vl` is pulled they
answer "I can read the screen but I cannot look at it yet."

## The shell tool and safety

`run_command` is the widest thing Happy has and the one holding the knife. A misheard word is
a different command.

`agents/bash.py` matches the command against a list of shapes — deletes, disk writes, `sudo`,
piping the internet into a shell, kills, schedulers — and anything that matches goes past a
person first. This catches a **careless** model, not a **hostile** one; it is a guardrail, not
a sandbox. Do not add a capability that assumes it is more than that.

How the asking happens is pluggable. `bash.asks(handler)` takes a
`handler(command, reason) -> bool`. The default reads from the console. When TTS lands, that
becomes a spoken "Happy wants to run something that deletes files — okay?" and the reason
strings in `RISKY` are already written to be said out loud.

`desktop.asks()` is the same handler shape over what is written on the thing being clicked, so
one spoken confirmation covers both knives.

## What is not built

- **The accessibility tree.** Native GUI control *is* built now, but through pixels — see
  "Seeing the screen". This section used to say the answer was an `agents/screen.py` reading
  the tree — `AXUIElement` on macOS, UI Automation on Windows — and to reach for screenshots
  and a vision model was called out as the wrong move. That was overridden on purpose, and the
  module landed as `agents/vision.py` plus `agents/desktop.py` instead.
  The tree is still the better answer where it exists, and is worth building: it knows an
  element's *kind* and *state* — is that checkbox ticked, is that button disabled — it reaches
  what is scrolled out of view or behind another window, and it costs no model call and no OCR
  pass. Pixels cover what it cannot: a canvas, a game, a remote desktop, an app that exposes
  nothing. The macOS half still needs no new dependency, and `AXIsProcessTrusted()` is already
  true because push-to-talk needed that permission anyway.
  **The memory warning it carried was right.** `gpt-oss:20b` is 13 GB and `qwen3-vl` is ~6 GB
  on a 24 GB machine, so the two do not sit in memory together and Ollama swaps one out for the
  other. That swap is exactly why OCR is the default and looking is the last resort: the cheap
  path is not just faster, it is the one that does not evict the model that has to speak.
- **Anything on the web that needs a login** works only after you have signed in once, by
  hand, in Happy's own browser profile. There is no credential handling and there should not
  be one.
- **`setup.py`.** Meant to be one-command setup — Ollama, the model pull, the STT weights.
  Currently a stub with a TODO.
- **Gmail.** There was an `agents/gmail.py`. It was removed on purpose: it is a remote
  service behind OAuth, not computer control, and it was the odd one out. Happy is about
  this machine for now. Revisit once bash, system and browser are solid.

## Running it

```sh
ollama serve                 # separate terminal
ollama pull gpt-oss:20b      # the stock tag. nothing to build on top of it.
ollama pull qwen3-vl         # the eyes. only for look_at_screen, OCR needs nothing.

# reading text off pictures. NOT a python package, it is a program.
brew install tesseract                          # macOS
winget install UB-Mannheim.TesseractOCR         # Windows, and it does not add itself to PATH

# the voice. any piper voice works, this one is a plain American man.
.venv/bin/python -m piper.download_voices en_US-hfc_male-medium --download-dir models/piper
.venv/bin/python audio/tts.py --voices      # which voice files are installed

.venv/bin/python main.py     # the real thing: hold RIGHT OPTION to talk
.venv/bin/python brain.py    # the same brain, typed at instead of spoken to
.venv/bin/python audio/tts.py "say this out loud"   # just the voice
.venv/bin/python agents/browser.py "find the top story on hacker news"   # one errand
.venv/bin/python agents/files.py "resume"   # find and read one file
.venv/bin/python agents/vision.py shot.png [--thorough]  # read a picture, or compare recipes
.venv/bin/python agents/desktop.py "Send"   # where would it click, without clicking
.venv/bin/python chat.py [--tools] [words]  # the conversation, or search it
.venv/bin/python agents/bash.py    # one shell command, straight through the tool
.venv/bin/python agents/system.py  # list installed apps
```

If a download fails with `CERTIFICATE_VERIFY_FAILED`, this Python has no root certificates —
run `/Applications/Python\ 3.13/Install\ Certificates.command` once, or prefix the command
with ``SSL_CERT_FILE=`.venv/bin/python -c "import certifi;print(certifi.where())"` ``. pip
carries its own certificates, which is why it works when nothing else does.

`brain.py` is the one to use while developing. It skips the microphone and WhisperX entirely
and exercises the graph, the tools and the guard — everything except audio.

**Two permissions, both granted to whatever runs Happy, not to Happy.** Accessibility, which
push-to-talk already needed and which the pointer and keyboard also use; and Screen Recording,
which capture needs. macOS refuses the second silently — you get a black picture, not an error
— so if Happy says he cannot see the screen, that is the one to check. Both live in System
Settings, Privacy & Security, and both need the app restarting after they are given.

Pointing at a different model or a hosted one is the four constants at the top of `llm.py`.
Ollama, LM Studio, llama.cpp, vLLM and the hosted providers all speak the same request shape,
so a swap is a URL and possibly a key in `$LLM_API_KEY`.
