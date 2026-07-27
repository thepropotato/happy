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
  hold key ─► record ─► transcribe ─► think ─► speak
    ears        ears        ears       brain    voice
                                         │
                                         ▼
                                  hands/ and eyes/
                                  (tools it calls)
```

1. `ears/trigger.py` watches globally for the push-to-talk key. Global, so the terminal does
   not have to be the focused window — on macOS that needs Accessibility permission.
2. `ears/microphone.py` keeps the microphone stream open for the life of the process and only
   gates whether it *keeps* what it hears. Opening a device costs about a tenth of a second,
   which is enough to swallow your first word. Each take is padded at both ends because
   nobody presses a key exactly on the first syllable.
3. `ears/transcribing.py` runs WhisperX locally. The model is loaded at startup so the first
   take isn't the one that pays for it.
4. `brain/thinking.py` runs the transcribed speech through the graph. The model may call
   tools; when it is done it streams an answer back in pieces.
5. `voice/` speaks those pieces as they land. It gathers them until a sentence ends, then
   sends that sentence to be spoken while the next one is still being written. Waiting for
   the whole answer first would add all of the model's thinking to the silence.

## The parts are named after a person

Every module is a folder, and the folder is named for the part of a person that does the job:
**brain** thinks, **ears** hear, **voice** speaks, **eyes** see, **hands** do, **memory**
remembers, **face** is what you see of him, and **conscience** is what asks before something
that cannot be undone. A new capability gets the name of the part of a person that would do
it. No file is longer than 200 lines; when one grows past that it splits by job.

## Layout

| Folder | What it owns |
| --- | --- |
| `main.py` | The loop. Hold, speak, release, hear an answer. Nothing else. |
| `brain/thinking.py` | The graph. Speech in, spoken answer out, tools called along the way. |
| `brain/model.py` | Which model, at which URL, with which settings. |
| `brain/prompt.py` | What the model is told before it hears anything. |
| `brain/providers.py` | The backends. One entry each, and the only file that knows a server's habits. |
| `ears/trigger.py` | Push to talk. |
| `ears/microphone.py` | Microphone capture, one WAV per take. |
| `ears/transcribing.py` | Speech to text. |
| `voice/piper.py` | The voice model itself, and the mute stand-in when it will not load. |
| `voice/sentences.py` | Where one spoken sentence ends and the next begins. |
| `voice/speaker.py` | Saying it out loud: synthesis, playback, barge-in. |
| `hands/__init__.py` | The registry. Collects every tool from every module into one flat list. |
| `hands/apps/` | The machine: what's installed, what it is, opening apps, paths and addresses. |
| `hands/controls/` | The machine's settings: sound, brightness, media, display, power, Wi-Fi, clipboard. |
| `hands/files/` | Finding files and reading what is inside them, whatever the format. |
| `hands/shell/` | The shell. One command in, what it printed back out. |
| `hands/desktop/` | The pointer and the keyboard, and checking that they worked. |
| `hands/browser/` | The browser errand. **Blank — being rebuilt.** |
| `eyes/asking.py` | Asking each system to describe its own screen. macOS and Windows side by side. |
| `eyes/naming.py` | What each system calls a thing, and what a person calls it. |
| `eyes/structure.py` | The controls in the window in front, filtered down to the real ones. |
| `eyes/attention.py` | What is in front, what has the caret, where the pointer is. |
| `eyes/estimating.py` | Every sense fused into one scene, and what changed between two of them. |
| `eyes/world.py` | What Happy currently believes about the desktop, and how he tells the model. |
| `eyes/matching.py` | Matching a spoken name against what is written on the screen. |
| `eyes/finding.py` | Where something is: four ways, cheapest first. |
| `eyes/` (rest) | Seeing by pixels: text off a picture or off the screen. |
| `hands/desktop/pointer.py` | The only place anything is actually injected. |
| `hands/desktop/noticing.py` | Telling Happy's own events from the person's. |
| `hands/desktop/expecting.py` | What should be true after an act. |
| `hands/desktop/verifying.py` | Waiting for the screen, judging it, and saying what happened. |
| `hands/desktop/acting.py` | One act, start to finish. |
| `memory/conversation.py` | The conversation: every message ever, and how to read it back. |
| `memory/storage.py` | The database. Owns the file and the schema, nothing else. |
| `memory/catalogue.py` | Every knob Happy has, and what it shipped as. The defaults live here and nowhere else. |
| `memory/knobs.py` | What a setting *is*: a kind, a default, and enough for a control to draw itself. |
| `memory/settings.py` | What every knob is set to now. Held in memory, written through to the file. |
| `memory/pruning.py` | Throwing the old away, if a setting says how long to keep it. |
| `face/show.py` | Every face at once. The rest of Happy reports here, never to a particular one. |
| `face/console.py` | What the terminal shows: one block per turn, and where the time went. |
| `face/panel.py` | What the window is told, as one JSON object per line on stdout. |
| `face/orders.py` | What the window asks for, read off stdin on its own thread. |
| `face/window/` | The Electron app: the icon in the menu bar and the panel that drops out of it. |
| `face/silence.py` | Silences the libraries. Must be called before anything imports whisperx. |
| `conscience/` | Asking before something that cannot be undone. |
| `AGENTS.md` | How to write code in this repo. Read it before you write any. |
| `TODO.md` | What is still pending. |

## The agent model — read this before adding one

The folders under `hands/` are **tool namespaces, not minds.** There is exactly one model
loop, in `brain/thinking.py`. It sees every tool from every module at once, calls what it
needs, and answers.

The alternative — a supervisor model that routes to a sub-agent, which runs its own loop and
reports back — is the more fashionable shape and the wrong one here. It costs two to three
extra round trips through the model. On a 20B running locally that is several seconds of a
person standing in their kitchen waiting for a sentence. Happy does not stall.

So: **a module here exports tools and thinks about nothing.**

The one exception is the browser. "Find the cheapest flight on Friday" is a dozen looks and
clicks, each one decided by what the last one put on screen, and that does not belong in the
main loop where it would bury every other tool under page text. So it gets its own loop, its
own model and its own context — and it *still* exports one ordinary tool. The main graph
hands it a sentence and gets an answer back, and never sees the clicks. **The shape of the
registry does not change.** `hands/browser/` is blank right now and being rebuilt; the
registry skips a module with no `TOOLS` rather than breaking, so it can stay in the list
while it is empty.

### Why not MCP

MCP is a transport for tools that live in another process. Every tool here is Python running
on the same machine as the model, so MCP would buy a subprocess and a JSON-RPC hop for
nothing. It becomes worth it the day you want something *else* — Claude Desktop, another
client — driving these same tools, or the day you want the shell tool genuinely sandboxed
rather than pattern-checked. Not before.

### Adding a capability

1. Write `hands/yourthing/`, as a folder with an `__init__.py`. Put the work in files named
   after what they do, and the tools in `tools.py`.
2. Decorate functions with `@tool` from `langchain_core.tools`. **The docstring is the
   prompt** — it is the only thing the model reads to decide whether to call you. Write it as
   plain prose for a reader, say when to use it *and when not to*, and give an example of the
   argument. This is the highest-leverage text in the folder.
3. Export `TOOLS = [...]` from the package.
4. Add the module to `MODULES` in `hands/__init__.py`.

That is the whole extension point. A module with no `TOOLS` at all is valid and registers
nothing, which is how something being rebuilt stays in the list without breaking startup.

## Things that are easy to get wrong here

**Tool output is not speech.** Whatever a tool returns lands in the model's context and may
end up spoken. Return short, plain, already-summarised text. `hands/shell/` truncates command
output for exactly this reason.

**Never stream the tool-calling turn.** The model's turn that *decides* on a tool arrives
through the same stream as the answer, as half-built JSON arguments. Streaming it is the
assistant muttering JSON at you. `spoken()` in `brain/thinking.py` is the filter that stops
this; if you touch streaming, keep it.

**Speech arrives misheard, not wrong.** "Saffari", "Vishwal Studio Code". Anything that takes
a name from the user should match loosely — see `hands/apps/installed.py`, `resolve()`.

**But loosely is not the same as certainly.** "slack" and "clock" score exactly 0.6 against
each other, "photoshop" and "Photos" score 0.8, and "word" sits inside "Passwords". Asked
whether Slack was installed, Happy called `open_app` and the Clock appeared. So `resolve()`
returns a name *and whether it is sure*: a short name that starts a word of exactly one app
is sure, a close-but-not-that-close spelling is not, and `open_app` turns the unsure ones
into "did you mean Clock?" instead of opening them. A tool that changes the screen should
never act on a guess it could have asked about. And it says in its own description that it
is not how you check whether an app exists — that is `list_installed_apps`, which opens
nothing.

**Opening is not the same as being in front.** `open -a` launches an application but does not
reliably raise one that is already running, and the old `open_app` reported "Opened WhatsApp"
on a zero exit code without looking. WhatsApp never came forward, Opera stayed in front, and
every look afterwards read Opera's window — so the model hunted for a chat in a browser and
eventually opened `web.whatsapp.com`. It now tells the application to activate, waits until it
really is the one in front, and when it is not it says so and says not to click. Everything
downstream reads whatever is in front, so this is the one claim the rest of a task rests on.

**Bound the loop.** `brain.calls` caps how many times the model
may go round before it has to answer. A loop that keeps going is a person staring at a silent
assistant, which is worse than a half answer. **But bound it above the real work.** Six was the
first guess and it was one short: opening an app, finding a chat, typing and sending is six
rounds with nothing going wrong, and the glance to see where the click landed makes seven. Asked
to send a message, Happy did every step right and then died on the limit. The default is
fourteen now, and it costs a short answer nothing — a cap only bites when the work is long.

**History is trimmed, not kept.** `recent()` keeps the last `brain.history`
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

If no voice is there, `voice.create()` returns a `Mute` voice and the reason. Happy carries on
answering in writing, and nothing downstream has to check whether there is a voice.

### How speaking works

Two threads behind a queue each: one turns sentences into sound, the other plays it. They are
separate so sentence three is being synthesised while sentence two is still in the air.

The splitting rules live on their own in `voice/sentences.py`; the threads and the queues
live in `voice/speaker.py`.

- **The first sentence of a reply goes out fast.** `MIN_CHARS_FIRST` is deliberately tiny, so
  "Done." is said immediately rather than waiting to be joined to the paragraph after it.
  Later sentences use the larger `MIN_CHARS` because by then smoothness beats speed.
- **Abbreviations are not sentence ends.** That short first-sentence floor makes "Mr. Stark
  is on the phone" likely to break in half, so `SHORTENED` and the single-initial rule catch
  it. Decimals are already safe — the split needs whitespace after the full stop.
- **Barge-in is `Speaker.stop()`**, wired to the push-to-talk key going down via the
  `on_press` callback in `ears/trigger.py`. It fires from the listener's own thread, because the
  main loop is usually busy exactly when someone decides to interrupt. Everything queued is
  dropped and playback is cut — someone who has started talking has stopped listening, and
  the microphone must not hear Happy either.
- **In-flight work is cancelled by an era counter**, not by trying to kill a thread. `stop()`
  bumps it; work stamped with an older era is thrown away when it surfaces.

## The browser — blank, being rebuilt

> `hands/browser/` is empty on purpose and is being written again from scratch. Everything
> below is what the first one learned the hard way. None of it is code any more, and all of
> it is still true about this machine, so read it before writing the next one. What went with
> it: unprompted speech is no longer wired up in `main.py`, though `face.console.unprompted()`
> is still there waiting, and nothing sets the `unprompted` column any more.

The first one was built on [browser-use](https://github.com/browser-use/browser-use), driving the local model
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
business running under a voice assistant. So the module ran *itself* again with `--run`,
handed the task on argv, and read back one marked line of JSON. Happy's half never imported
`browser-use` at all. The task is all that crosses — the child read the backend out of
`brain/model.py` directly, the same as every other module.

**It returns immediately.** `browse(task)` starts the job and answers "Started, I will say
when it is done." Happy stays responsive, you keep talking to him, and the job speaks up
unprompted when it lands. That announcement was wired in `main.py` and **waited for a gap** —
it will not cut across you mid-sentence, because being a sentence late is better than talking
over someone. A status tool covered "is it done yet".

**It needs a real context window.** See below — this is the thing most likely to waste your
afternoon.

**It uses the browser you chose.** `hands.apps.drivable_browser()` reads the actual `https`
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

`open_url`, in `hands/apps/`, is for anything an address reaches — a site, a video, a search. It lands in
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
the page says so on stderr, so that is what `released()` in `hands/apps/running.py` checks. A
quick exit means it forwarded; still being alive means it *is* the browser now. Both are
success.

Telemetry has to be disabled explicitly wherever `browser-use` is used: it sets
`ANONYMIZED_TELEMETRY` to `'true'` by default and cloud sync follows it, which is not what
"completely local" means.

## Swapping the model out

A model here is inference and nothing else. The flow belongs to LangGraph, the tools belong to
`hands/` and `eyes/`, the prompt belongs to `brain/prompt.py`. What is left is a name, an
address and a few settings — so changing backend is two rows in the `settings` table, which is
two controls in the panel:

```
brain.provider   ollama    # anything in brain/providers.py
brain.url        ""        # empty takes that backend's own default
```

`brain/providers.py` holds one builder per backend and is **the only file that knows a
particular server's habits.** Adding one is writing the builder and putting it in `PROVIDERS`;
nothing else moves. Two things actually differ between them, and both are named there: where
the context length goes, and what the thinking knob is called.

A backend that cannot do something **says so instead of dropping it.** `SETS_CONTEXT` records
whether a request can carry a context length — the OpenAI shape cannot — and `brain.caveat()`
turns that into a line printed at startup. Silence about a dropped setting is the failure mode
this whole file exists to prevent.

The browser is the one place the client has to be mirrored rather than shared: `browser-use`
will not take a LangChain model, so it needs the same provider name mapped onto its own
client. Only the client differs — the name comes from `brain/providers.py` and the model,
address and key come from `brain/model.py`, so the choice is still made in one place.

## The context window, or: why the model looks stupid

Ollama serves **4096 tokens** unless told otherwise, no matter that `gpt-oss:20b` supports
131072. It does not warn you. It just forgets the oldest thing you said.

This is not a tuning knob, it is a correctness bug waiting to happen. One resume PDF read
through `hands/files/` is ~1250 tokens. A verbose shell command is ~1000. The system prompt
and tool schemas are ~1100 before you open your mouth. browser-use's system prompt **alone is
~6000** and never fit in 4096 at all.

**Happy runs at the full 131072 now**, as `CONTEXT` in `brain/model.py`, sent with every request.
There is no `Modelfile` and no `ollama create` step. The models are the ones you pulled.

Measured on an M-series with 26 GB: it loads at **12 GB, 100% GPU, no CPU spill**, and replies
in **2.18s against 2.22s at 4096**. It is free. gpt-oss uses sliding-window attention on
alternate layers, so the key-value cache stays small. There was never a reason to run at 4096.

What works and what does not — the first row is the trap, because it looks like it should:

| | Result |
| --- | --- |
| `extra_body={"options": {"num_ctx": N}}` via `/v1` | **Silently ignored.** Still loads at 4096. |
| `ChatOllama(num_ctx=N)` via `/api/chat` | Works. This is what `brain/providers.py` does. |
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
`reasoning_effort` nor `/no_think` reaches it through `/v1`. Natively it is `eyes.effort`
set to off, which is a field on the request, plus 32768 of room.

The browser sets its own, deliberately lower at 32768: `num_ctx` is a ceiling rather than a
reservation, but page text expands to fill whatever it is given, and a 130k-token page makes
every step slow for no benefit.

**Always confirm with `ollama ps`.** The CONTEXT column is the only thing in this stack that
tells you the truth.

## The faces

Happy has two, and neither of them knows about the other. Everything he does is reported to
`face/show.py`, which hands it to whichever faces are attached — a terminal, a window, both,
or none. A face that has no opinion on something simply does not define the method, and
`show` skips it. That is why the microphone can report its loudness ten times a second without
`face/console.py` growing a single line about it.

`main.py` attaches one face at startup and that is the whole of the difference between the two
ways of running Happy.

## The terminal

`face/console.py` owns everything the terminal shows. One block per turn, separated by a rule and
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

Tools report themselves from the middleware in `brain/thinking.py`, so a tool added later
appears here with nobody wiring it up. `brain.watches()` takes the callback — the brain does
not know a terminal exists, the same way `conscience.asks()` works.

**What it immediately showed:** tools are noise (7 ms for `system_info`) and the voice is noise
(15 ms). The model is essentially the entire turn. A question needing a tool costs two model
round trips and lands around 5–12 seconds to first word. That is the number to attack, and no
amount of TTS tuning touches it.

## The window

`face/window/` is an Electron app. It puts an icon in the menu bar — the tray on Windows — and
drops a panel out of it when you click. There is no dock icon and no taskbar entry: the icon is
the app.

**Electron owns the process.** It spawns `python main.py --serve` as a child and the two talk
over that child's own pipes: one JSON object per line, events down stdout, orders up stdin. No
port, no server, no dependency on either side — `json` on one end and `JSON.parse` on the other.
Closing the window closes Happy, because the reader in `face/orders.py` sees stdin end and
shuts him down.

While the window is attached, **stdout carries nothing but JSON**. Anything a person might want
to read goes to stderr, which Electron logs and nobody parses. That is the only rule the two
sides share.

What the panel shows:

- An **orb** that breathes when nothing is happening, swells with the microphone while you talk,
  turns while Happy thinks, and rides the actual clip he is playing. The loudness is real:
  `ears/microphone.py` reports the level of each 100 ms block while it is recording, and
  `voice/speaker.py` sends the shape of every clip just before it plays. The colour behind
  everything moves with it — amber for listening, violet for thinking, green for speaking.
- **What was said**, streaming a piece at a time, with the same stats line the terminal prints.
- **A box to type in**, because not every question is worth saying out loud. A typed line takes
  the same turn a spoken one does, on the same lock, so the two can never overlap.
- **Every control**, which is the next section.
- **The asking**, when a tool wants permission. `conscience.asks()` is pointed at the panel, so
  a shell command that cannot be undone stops the window rather than a terminal nobody is
  looking at.

Sound outlives the words. Happy is still a sentence behind himself when the model has finished,
so the panel goes quiet when the last clip ends and not when the last word arrives.

## Controls come from the database

Nothing Happy runs on is written into the code any more. `memory/catalogue.py` lists every knob
— what it is called, what kind of thing it is, what it may be set to, and what it shipped as.
`memory/settings.py` holds what it is set to now, in a `settings` table beside `messages`.

The catalogue is the only place a default exists. `brain/model.py` does not know that thinking
effort starts on low; it asks. This is what makes the panel possible: the window draws controls
it has never heard of, because the catalogue tells it that `brain.effort` is one of four things
and `voice.pace` is a number between 0.6 and 1.6. **Adding a setting is a line in a Python file
and nothing at all in the JavaScript.**

Changing one takes effect on the next turn, not the next restart. Every part that was *built*
out of a setting — the graph, the speech model, the voice, the push-to-talk key — checks a
counter that only goes up, and puts itself back together when its own group has moved. The
counter is per group, so nudging the voice pace does not rebuild the brain. The conversation
survives a rebuild because the checkpointer outlives the graph.

Two of them are not knobs so much as a broom: `memory.messages` and `memory.recordings` say how
many days to keep things, and `memory/pruning.py` runs once at startup. Zero keeps everything,
which is what they ship as.

## The conversation

Everything ever said lives in a **SQLite database** at `data/happy.db`. `memory/storage.py`
owns the file and the schema; `memory/conversation.py` owns what a message is and how it
reads back; `memory/transcript.py` lays it out for a person.

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
more than anyone will ever say to Happy. So `memory.search()` is a `LIKE` now.

What that costs: no relevance ranking, and no stemming, so "meet" will not find "meeting". What
it buys: `sqlite_master` has two rows in it and you can read the whole schema at a glance. The
one index stays because it is not a table and it earns its place — asking for the newest fifty
messages is **123 ms without it and 0.1 ms with it** at that same scale.

`%` and `_` are wildcards to `LIKE`, so they are escaped before the search runs. Searching for
"75%" finds the message about response times, not every message.

```sh
python -m memory.transcript             # the whole conversation, as a chat
python -m memory.transcript --tools     # with the plumbing shown
python -m memory.transcript dentist     # search
```

`memory/storage.py` gives each thread its own connection, because SQLite objects do not travel
between threads and a background errand finishing on its own thread writes at the same moment
the voice loop does. WAL mode lets a reader read while a writer writes. A failed write never
costs you a turn. `add(at=...)` exists so messages can be carried in from elsewhere with their
own times on them — everything live leaves it alone and means now.

## Reading files

`hands/files/` is the answer to "I don't have the ability to read that file", which was a
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
go to `eyes/`; `.gif` and `.heic` stay named, because OpenCV will not reliably
decode either. Happy still does not *look* at a photograph — he reads the text off it, so a
screenshot of a message reads fine and a picture of a dog comes back empty.

## Seeing the screen

`eyes/` answers three different questions and it matters enormously which is which.

**What is there** is the accessibility tree: the application is *asked* what it drew. About
**90 ms**, exact, and the only source that knows a thing's *kind* and *state*. `list_controls`.

**What does it say** is OCR: exact about the letters, blind to everything else, and about a
second and a half for a full screen. `read_screen`.

**What does it look like** is a vision model: tens of seconds, and needed far less often than it
looks. `look_at_screen(question)`.

The order is the whole design. Asking beats looking by roughly ten to one on time and does not
lose the argument on quality either — a picture cannot tell you that the Share button is greyed
out, that a box is ticked, or where the keyboard is. Pixels are for what has no structure to
read.

### Asking the application

`AXUIElement` on macOS, UI Automation on Windows. On macOS this needs no new dependency and
`AXIsProcessTrusted()` is already true, because push-to-talk needed that permission anyway.

Measured on this machine: a Finder window is **160 elements in 124 ms**, and every one of them
arrives knowing its own box, its kind, whether it is enabled and whether it is ticked. The same
window through OCR is a second and a half and a list of words with no idea what any of them are.

Four things had to be got right before it was useful:

- **An application's windows are not among its children.** `AXChildren` on the application hands
  back the menu bar and nothing else — for Finder, for a browser, for WhatsApp, for everything
  measured here. The windows have to be asked for by name, and not always the same name: most
  answer `AXWindows`, and a Catalyst application like WhatsApp leaves that empty and only answers
  `AXFocusedWindow` and `AXMainWindow`. Walking children alone made every application look like
  one that describes nothing, which is not a blind spot you notice — it reads as *"there is no
  message field"*, and everything quietly fell through to OCR and the vision model. All four are
  walked now, deduplicated with `CFEqual`, because the same window is usually both the main one
  and the focused one.
- **A closed menu keeps its entire subtree**, all of it invisible and unclickable, reported at
  position `(0, 982)` with size `0×0`. That was most of the walk for none of the answer, so a
  zero-sized menu is not descended into and nothing without a real box is ever returned.
- **The menu bar is always there and always named.** It made every application look like it
  described itself well, including the ones handing back an empty window, so `thin()` counts only
  what is actually *inside* the window. That check is what decides whether OCR runs at all.
- **A tree repeats itself.** A button's label is often also a piece of static text sitting exactly
  on top of it, and both were being offered as targets. Nameless rows, cells, columns and scroll
  bars are scaffolding and go; a named group stays, because it is often the only thing holding a
  dialog's title.
- **Labels carry characters that draw nothing.** An application built for Arabic and Hebrew as
  well as English puts a left-to-right mark in front of nearly every label, so WhatsApp's *New
  Chat* is really `‎New Chat`. It looks identical, it reads aloud identically, and it is not
  an exact match for anything a person says. The direction marks are stripped in `wording()`,
  where both systems pass through.

**Not every application answers.** That is not a bug to fix, it is why `eyes/` still has pixels —
and it is detected rather than assumed, which is what `thin()` is for. It is worth being slow to
conclude it, though: a browser was written off here as "the page title and three empty groups"
when the real answer was that nobody had asked it for its window.

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

Ties are broken towards **the thing you could actually press**, and then towards the one that is
not greyed out. A label and the button under it very often say the same word, and the person
meant the button.

**Except when the person named somewhere to type.** People put words around what they mean, so
`tidy()` strips "the", "button", "field", "box" before scoring — right for matching, and it threw
away the one word that mattered. `"the message field"` became `"message"`, which scores *better*
against WhatsApp's **Voice message** button than against its **Compose message** box; pressing
that starts recording a voice note instead of writing a message. So the target is checked for
"field", "box", "input" or "bar" *as said*, before tidying, and when one is there a thing you can
type into outranks any score. Everything being ranked has already passed the floor, and only one
of them takes words.

## The screenshot is not the state

This is the idea the whole desktop half is built on, and it is worth stating plainly because the
obvious design is the other one.

The obvious design is: screenshot, OCR, model, click, repeat. It works until something normal
happens — a notification lands, a window is still loading, the person moves the mouse — and then
it keeps going, confidently, having no way to know the world stopped matching its assumptions.

So the desktop is treated as **a state estimation problem rather than a computer vision one**.
A screenshot is one observation of the state, and not the best one. `eyes/estimating.py` fuses
every sense that answered into a single `Scene` — what is in front, what has the keyboard, where
the pointer is, the controls the application described, and the words only if they were needed.
`eyes/world.py` holds the current belief, and the one before it, because **every useful question
about an act is a question about the difference between two moments.**

**The belief is never trusted for a click.** It is refreshed first, every time. It exists so that
one act does not look at the screen four times, not so that a remembered position can be reused.

**Confidence names its source rather than pretending to be a probability.** `TOLD` (0.90) is the
application saying so, `READ` (0.75) is OCR, `PICKED` (0.55) is the model choosing from what OCR
found, `POINTED` (0.35) is the model giving a coordinate. They rank the senses and nothing more.
Multiplying them together would manufacture a precision nobody measured — and the one place it
changes behaviour is honest: a click grounded at `POINTED` reports *"Clicked where I think Send
is"*, not *"Clicked Send"*.

There is deliberately **no score for two senses agreeing**, tempting as it looked. Confirming a
tree result against OCR would cost the second and a half that asking exists to avoid, so nothing
would ever pay for it, and a constant nothing can reach is a lie in the source.

**Change detection is deliberately cheap.** Measured here: asking is 90 ms, a screen grab is
270 ms, fingerprinting that grab is 3 ms, and OCR is about 1500 ms. So verification compares the
tree, and falls back to a 64×64 fingerprint of the screen when the application describes nothing.
**OCR never runs inside the verify loop.** It did briefly, and it put five seconds on every act.

What comes back out is one sentence, not a list. `difference()` returns the single most
significant change, because this ends up spoken and *"the window is now Documents, and one thing
appeared, and nine things went away"* is nobody's idea of being told what happened.

## Working the desktop

`hands/desktop/` is the other half of seeing: `click_on`, `type_text`, `press_keys`, `scroll`,
and `list_controls` to see what is there first.

**No tool takes a coordinate.** They take a description — "Send", "the search box" — the screen
is read fresh on every call, and the pointer goes where that thing actually is. One act per
call, and the screen is never assumed to have stayed still between two of them: a menu that
opened half a second late makes every remembered position a lie.

Every act has the same shape, and the last step is the one that matters:

```
  look ─► find it by name ─► ask if it matters ─► do it ─► look again ─► say
```

**Nothing reports success it has not checked for.** Before acting, the act writes down what
should become true; afterwards the screen is read again and that question is asked. A click on a
checkbox is checked exactly, because the application reports the tick. Somewhere to type is
checked exactly too, and had to be: focusing a text box changes nothing a glance can see, and
WhatsApp's compose box already holds the keyboard the moment a chat opens, so "the screen should
not be identical" called every one of them a failure — `type_text` found the right box, was told
it had failed, and gave up before typing a letter. What is checked there is that the keyboard
ended up in it. Everything else is still "the screen should not be identical", which is weak and
still catches the failure that actually happens, which is nothing happening at all. When nothing
can tell us either way it says so rather than inventing a verdict — `Verdict.sure` is a separate
field from `Verdict.ok` for exactly that reason.

It came up immediately in testing. Clicking a Finder sidebar item straight after bringing Finder
to the front does nothing at all: the first click activates the window. The old code would have
said "Clicked Documents" and moved on. This one says *"I clicked Documents but nothing on the
screen changed"*, which is both true and the thing you needed to know.

**Waiting is two questions, not one.** `settled()` first waits for the screen to *react*, then
waits for it to *stop*. Waiting only for it to stop is a bug that looks like it works: a window
that has not started yet is also perfectly still, and would be judged a failure a tenth of a
second before it opened.

**It never retries.** A click that did nothing is reported as a click that did nothing. Pressing
an unknown button a second time is how one failure becomes two. What it does instead is wait
half a second and look once more, because a slow window is the commonest reason a good click
looks like a bad one.

The guard is the same shape as the shell's, applied to what is written on the thing being
clicked: delete, send, spend, install, grant permission, quit — and to shortcuts that end
something, like `cmd+q`. It goes through `conscience/`, the one place that asks, so it becomes
a spoken question for free.

**The looking model is not in this loop, and that is a measurement, not a preference.** Grounding
escalates through four steps (see above), but an act stops after step 2. Asked to click something
that was not on the screen, the full escalation reached `qwen3-vl` and took **eighty four
seconds**. So `clicked()` passes `ask=False` and a thing with no name anywhere is simply not
found, in under three seconds. If you genuinely need the picture understood, that is
`look_at_screen`, asked for on purpose.

**The cost is not only time.** `gpt-oss:20b` is 13 GB and `qwen3-vl` is ~6 GB, so on a 24 GB
machine the two do not sit in memory together and Ollama swaps one out for the other. Reaching
for the looking model mid-act evicts the model that has to speak the answer. That is the real
reason the cheap paths are the default and looking is the last resort.

**Telling our own events from the person's** lives in `hands/desktop/noticing.py`, beside the
injector rather than with the other senses, because the only way to know whether a click was ours
is to know what we injected. Every call in `pointer.py` marks a short window as ours first.
**Only times are kept — which key was pressed is never recorded**, because this is here to notice
a person, not to read one. What it cannot do: macOS will not say whether an event was synthetic,
so the window is the whole mechanism, and verification is what actually catches the rest.

The pointer and the keyboard needed nothing new — pynput, screeninfo and Pillow were already
here for push-to-talk and the recorder. On macOS the accessibility tree needs nothing new either.
**Windows needs `comtypes`**, and says so plainly when it is missing instead of failing oddly.

**What is verified and what is not.** Clicking, typing, shortcuts and scrolling are proven end to
end on real UI — Finder and System Settings — including the greyed-out refusal, the unknown
target, and the honest failure report above. The thin-tree fallback is proven against VS Code.
**Every Windows path is written and unrun.**

## The shell tool and safety

`run_command` is the widest thing Happy has and the one holding the knife. A misheard word is
a different command.

`hands/shell/guard.py` matches the command against a list of shapes — deletes, disk writes,
`sudo`, piping the internet into a shell, kills, schedulers — and anything that matches goes
past a person first. This catches a **careless** model, not a **hostile** one; it is a
guardrail, not a sandbox. Do not add a capability that assumes it is more than that.

**Asking lives in one place: `conscience/`.** `conscience.asks(handler)` takes a
`handler(what, reason) -> bool` and `conscience.allowed(what, reason)` is what a tool calls.
The default reads from the console. When a spoken confirmation lands it is wired once and
covers every knife at once — the shell, the desktop, and shutting the machine down. The reason
strings are already written to be said out loud.

## The machine's own settings

`hands/controls/` is the ordinary stuff a person asks for out loud: turn it down, make the
screen brighter, pause that, lock it, how much battery is left, what wifi am I on, what did I
just copy. One file per part of the machine — `sound`, `screen`, `power`, `network`, `media`,
`clipboard` — and **both systems are written side by side in the same function**, so a control
that only works on one of them is visible in the diff rather than discovered later.

**Seven tools, not twenty.** One per part of the machine, each taking an action: `sound_control
("up")`, `power_control("battery")`, `clipboard_control("write", text)`. Every extra tool costs
prompt tokens on every single turn and one more thing for a 20B model to pick wrongly between,
so grouping wins. The allowed actions are spelled out in the docstring, and anything else comes
back as "I can set, step, mute or report the volume, not *that*", which the model can recover
from.

**No shelling out to a command that might not be there.** Sound on macOS is AppleScript, which
is always installed; on Windows it is the audio endpoint addressed directly through a small
C# shim, because Windows ships no command for the volume at all and the media keys can only
step it. Brightness is WMI on Windows and, on macOS, `DisplayServices` — the private framework
the slider in System Settings and the keys on the keyboard both go through, called directly
through `ctypes`. It was the Homebrew `brightness` helper, which is built on `IODisplay` calls
Apple silicon no longer answers: on every recent Mac it is both missing and, once installed,
wrong, so telling someone to go and brew it was not even good advice. The helper and then the
brightness keys remain as fallbacks for the Macs that predate the framework, and a level that
can only be stepped is stepped rather than refused. **A control that cannot do something says
which, and how to fix it — but it tries everything it has first.**

Anything that loses unsaved work — sleep, restart, shut down — goes through `conscience/`
first. The battery and the lock do not, because neither costs you anything.

## What is not built

- **Reaching what is not on the screen.** The tree can describe what is scrolled out of view or
  behind another window, and none of that is used: everything is filtered down to what is
  visible and clickable right now, because that is what a pointer can reach. Scrolling something
  into view and looking again is the supported way, and it is the honest one.
- **Acting through the tree instead of the pointer.** Both systems can press a button directly
  — `AXPress`, UI Automation's Invoke — without moving the mouse at all. That would be faster
  and would not fight the person for the pointer. It would also skip the thing being pressed
  actually receiving a click the way it expects, so it is a change to make deliberately and
  measure, not a free win.
- **Windows, in practice.** Every Windows path here is written and unrun; see `TODO.md`.
  It also needs `comtypes`, which macOS does not.
- **A second monitor.** Everything assumes the application in front, on the current Space. A
  full-screen app on another Space is invisible and cannot be driven.
- **Anything on the web that needs a login** works only after you have signed in once, by
  hand, in Happy's own browser profile. There is no credential handling and there should not
  be one.
- **A setup script.** Meant to be one-command setup — Ollama, the model pull, the STT weights,
  a voice, Tesseract. There is none; see `TODO.md`.
- **Gmail.** There was a Gmail module. It was removed on purpose: it is a remote
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
.venv/bin/python -m voice --voices    # which voice files are installed

cd face/window && npm install         # once, for the window
cd face/window && npm start           # the real thing: an icon in the menu bar
cd face/window && npm start -- --open # the same, with the panel already down

.venv/bin/python main.py              # no window: hold RIGHT OPTION to talk in a terminal
.venv/bin/python -m brain             # the same brain, typed at instead of spoken to
.venv/bin/python -m voice "say this out loud"        # just the voice
.venv/bin/python -m eyes shot.png [--thorough]       # read a picture, or compare recipes
.venv/bin/python -m hands.desktop                    # the controls in the window in front
.venv/bin/python -m hands.desktop where Send         # find it on screen, and touch nothing
.venv/bin/python -m hands.desktop click Send         # one act, with the check after it
.venv/bin/python -m hands.files resume               # find and read one file
.venv/bin/python -m hands.apps                       # installed apps, and the default browser
.venv/bin/python -m hands.controls                   # every setting, as it stands now
.venv/bin/python -m hands.shell "ls ~"               # one command, straight through the tool
.venv/bin/python -m memory.transcript [--tools] [words]   # the conversation, or search it
```

If a download fails with `CERTIFICATE_VERIFY_FAILED`, this Python has no root certificates —
run `/Applications/Python\ 3.13/Install\ Certificates.command` once, or prefix the command
with ``SSL_CERT_FILE=`.venv/bin/python -c "import certifi;print(certifi.where())"` ``. pip
carries its own certificates, which is why it works when nothing else does.

`python -m brain` is the one to use while developing. It skips the microphone and WhisperX
entirely and exercises the graph, the tools and the guard — everything except audio.

**Two permissions, both granted to whatever runs Happy, not to Happy.** Accessibility, which
push-to-talk already needed and which the pointer and keyboard also use; and Screen Recording,
which capture needs. macOS refuses the second silently — you get a black picture, not an error
— so if Happy says he cannot see the screen, that is the one to check. Both live in System
Settings, Privacy & Security, and both need the app restarting after they are given. Run the
window and it is **Electron** that has to be given them, not Python.

A terminal that lives inside an Electron app — VS Code's — exports `ELECTRON_RUN_AS_NODE=1` to
everything it starts. Inherit it and Electron comes up as plain Node, where there is no window
and no `app`, only a confusing crash. `face/window/start.js` exists to strip it back off, which
is why `npm start` runs that rather than `electron .`.

Pointing at a different model or a hosted one is the **Brain** group in the panel, or a row in
the `settings` table. Ollama, LM Studio, llama.cpp, vLLM and the hosted providers all speak the
same request shape, so a swap is a URL and possibly a key in `$LLM_API_KEY`.
