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
- **He acts on his own.** Happy will drive you anywhere, and he does not stop halfway to ask
  whether you meant it. Nothing he does waits on a yes.
- **He does not stall.** A pause that would be invisible in a chat window is unbearable out
  loud. Latency is a correctness property here, not a nice-to-have.

When a design choice is genuinely close, pick the one Happy would make.

## What this is

A voice assistant that operates this computer. Hold the key, say what you want, it happens.
It runs entirely on your machine — the speech recognition, the model, the tools. Nothing
leaves the box.

Target platforms are macOS and Windows. Both, always. A feature that only works on one is
not finished.

## How one turn works

```
  hold the key ─► record ─► transcribe ─► think ─► speak
      ears          ears        ears       brain    voice
                                             │
                                             ▼
                                      hands/ and eyes/
                                      (tools it calls)
```

1. `ears/trigger.py` watches one modifier key from any window, and `ears/holding.py` turns a
   press into a take: record while it is down, read what was said into it, hand it on. Nothing
   is matched against a name, because holding a key is already somebody saying who they are
   talking to.
2. `ears/microphone.py` opens the device on the press and shuts it on the release. Between
   takes there is no stream at all — no blocks arriving, no battery going on them, and the
   system's own microphone light off, which is the honest answer to "is it listening". The
   take is padded at the end only, since the front of it is the moment the key went down.
3. `ears/transcribing.py` runs Parakeet locally through `onnx-asr`. The model is loaded and
   warmed at startup so the first take isn't the one that pays for it.
4. `brain/thinking.py` runs the transcribed speech through the graph. The model may call
   tools; when it is done it streams an answer back in pieces.
5. `voice/` speaks those pieces as they land. It gathers them until a sentence ends, then
   sends that sentence to be spoken while the next one is still being written. Waiting for
   the whole answer first would add all of the model's thinking to the silence.

## The parts are named after a person

Every module is a folder, and the folder is named for the part of a person that does the job:
**brain** thinks, **ears** hear, **voice** speaks, **eyes** see, **hands** do, **memory**
remembers, and **face** is what you see of him. A new capability gets the name of the part of
a person that would do it. No file is longer than 200 lines; when one grows past that it splits by job.

## Layout

| Folder | What it owns |
| --- | --- |
| `main.py` | The loop. The key, what was asked, an answer. Nothing else. |
| `brain/thinking.py` | The graph. Speech in, spoken answer out, tools called along the way. |
| `brain/wrapping.py` | What wraps every call: what goes in, what is kept, how long it took. |
| `brain/model.py` | Which model, at which URL, with which settings. |
| `brain/prompt.py` | What the model is told before it hears anything, read once from `prompt.md`. |
| `prompt.md` | The wording itself, one section per block, editable without reading Python. |
| `brain/providers.py` | The backends. One entry each, and the only file that knows a server's habits. |
| `ears/trigger.py` | The hold to talk key, watched from any window. |
| `ears/holding.py` | One press: record while it is down, read it, hand it on. |
| `ears/microphone.py` | Microphone capture, one WAV per take, device open only while held. |
| `ears/transcribing.py` | Speech to text. |
| `voice/engines.py` | Which engine speaks, and loading only that one. |
| `voice/kokoro.py` | The voice model itself. |
| `voice/styles.py` | The voice files: what is here, which one speaks, and getting more. |
| `voice/piper.py` | The Telugu voice, and nothing else now. |
| `voice/phonemes.py` | Words turned into the sounds they are made of. |
| `voice/clips.py` | Sound tidied at its edges, so one piece runs into the next. |
| `voice/collecting.py` | Fetching a missing voice behind the conversation. |
| `voice/mute.py` | The stand-in when no voice will load. |
| `voice/sentences.py` | Where one spoken sentence ends and the next begins. |
| `voice/speaker.py` | Saying it out loud: synthesis, playback, barge-in. |
| `hands/__main__.py` | Every tool the model is handed, and the prompt, for a person to read. |
| `hands/__init__.py` | The registry. Collects every tool from every module into one flat list. |
| `hands/apps/` | The machine: what's installed, what it is, opening apps, paths and addresses. |
| `hands/controls/` | The machine's settings: sound, brightness, media, display, power, Wi-Fi, clipboard. |
| `hands/files/` | Finding files and reading what is inside them, whatever the format. |
| `hands/shell/` | The shell. One command in, what it printed back out. |
| `hands/desktop/` | The pointer and the keyboard, and checking that they worked. |
| `hands/web/` | Searching the web, and reading whichever result holds the answer. |
| `hands/browser/` | The browser errand. **Blank — being rebuilt.** |
| `eyes/systems.py` | Asking each system to describe its own screen. macOS and Windows side by side. |
| `eyes/naming.py` | What each system calls a thing, and what a person calls it. |
| `eyes/elements.py` | The controls in the window in front, filtered down to the real ones. |
| `eyes/attention.py` | What is in front, and what the window in front is called. |
| `eyes/pointing.py` | Where the keyboard and the pointer are. |
| `eyes/agreeing.py` | Every sense fused into one scene, and what changed between two of them. |
| `eyes/world.py` | What Happy currently believes about the desktop, and how he tells the model. |
| `eyes/matching.py` | Matching a spoken name against what is written on the screen. |
| `eyes/locating.py` | Where something is: four ways, cheapest first. |
| `eyes/` (rest) | Seeing by pixels: text off a picture or off the screen. |
| `hands/desktop/pointer.py` | The only place anything is actually injected. |
| `hands/desktop/noticing.py` | Telling Happy's own events from the person's. |
| `hands/desktop/expecting.py` | What should be true after an act. |
| `hands/desktop/verifying.py` | Waiting for the screen, judging it, and saying what happened. |
| `hands/desktop/acting.py` | One act, start to finish. |
| `memory/conversation.py` | The conversation: every message ever, and how to read it back. |
| `memory/storage.py` | The database. Owns the file and the schema, nothing else. |
| `memory/catalogue.py` | Every knob Happy has, and what it shipped as. The defaults live here and nowhere else. |
| `memory/kinds.py` | What a setting *is*: a kind, a default, and enough for a control to draw itself. |
| `memory/settings.py` | What every knob is set to now. Held in memory, written through to the file. |
| `memory/pruning.py` | Throwing the old away, if a setting says how long to keep it. |
| `memory/exporting.py` | `data/happy.log` as a page a browser can open, which is all it is. |
| `face/show.py` | Every face at once. The rest of Happy reports here, never to a particular one. |
| `face/console.py` | What the terminal shows: one block per turn, and where the time went. |
| `face/telling.py` | What the window is told, as one JSON object per line on stdout. |
| `face/log.py` | The face nobody watches: every event, stamped, into `data/happy.log`. |
| `face/handing.py` | Pictures that go back with the answer, for somebody who is not in the room. |
| `face/requests.py` | What the window asks for, read off stdin on its own thread. |
| `face/sources.py` | The catalogue finished off with the lists only a running machine knows. |
| `face/window/` | The Electron app: the icon in the menu bar and the panel that drops out of it. |
| `face/silence.py` | Silences the libraries. Must be called before anything opens an ONNX session. |
| `mcps/__init__.py` | Services that are not this computer. What is connected, and its tools. |
| `mcps/registry.py` | Every service Happy ships, and what each one costs to connect. |
| `mcps/joining.py` | Signing in, signing out, pasting something in. Never reached by a tool. |
| `mcps/tools.py` | The one tool: where every service stands, in words. It changes nothing. |
| `mcps/session.py` | One running server, held open, and got back when it dies. |
| `mcps/pool.py` | Every connected server, started in the background, never blocking a start. |
| `mcps/loop.py` | The one event loop the servers live on. The async side of the wall. |
| `mcps/binding.py` | A tool on one of those servers, as one the graph calls like any other. |
| `mcps/shortening.py` | What came back, squeezed down to something that can be said out loud. |
| `mcps/panel.py` | Every service as one row somebody can read, for the window to draw. |
| `mcps/wording.py` | The words a row says about a service, and nothing about its shape. |
| `mcps/store.py` | What is connected, which is whatever remembers tools, and what those are. |
| `mcps/oauth.py` | The browser sign in: the consent page and the token it comes back with. |
| `mcps/tokens.py` | Where a sign in is kept, which is `data/happy.db` and nowhere else. |
| `mcps/permission.py` | The browser, and the loopback door the service sends you back through. |
| `mcps/servers/shared/` | What every server shares: its credentials, its HTTP, its answers. |
| `mcps/servers/google/` | Mail, calendar and drive on one sign in. One server, not three. |
| `mcps/servers/notion/` | Searching a workspace, reading a page, and writing one. |
| `mcps/servers/github/` | Repositories, the files in them, their issues and their commits. |
| `mcps/servers/slack/` | Channels, what was said in them, and saying something. |
| `mcps/servers/weather/` | The forecast anywhere, from the one that wants no account. |
| `mcps/servers/instagram/` | This account's own posts, their comments, and replying to one. |
| `mcps/bridging.py` | The bridge from Happy's side: starting it, asking it, putting it down. |
| `mcps/servers/whatsapp/` | Reads your chats over a local bridge, and sends on them. |
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

### MCP, in one direction only

Happy is an MCP **client** and not an MCP **server**, and the difference is the whole
argument. Nothing under `hands/` is exposed over MCP: every tool there is Python running on
the same machine as the model, so wrapping it in a subprocess and a JSON-RPC hop would buy
nothing. That becomes worth doing the day you want something *else* — Claude Desktop,
another client — driving these tools, or the day you want the shell tool genuinely sandboxed
rather than pattern-checked. Not before.

Reaching *out* is a different question. A calendar, a mailbox, a tickets board — none of
those are on this computer. So `mcps/` reaches them, and the tools it brings back are bound
flat into the one graph beside `read_file` and `click_on`. Still one loop, still no routing.

**Happy writes those servers itself.** Every service is a Python MCP server under
`mcps/servers/<service>/mcp_server.py`, started on Happy's own Python and talked to over a
pipe. Writing them is what makes the rest simple: there is no discovery, no registration and
no allowlist, because none of that is needed for a server we wrote.

One rule holds it together: **a server looks up its own credentials.** Every one reads
`connection_secrets` in `data/happy.db` through `mcps/servers/shared/credentials.py`, the
single module both sides import. Nothing is passed on a command line, where every `ps` on the
machine would see it, and the client half carries no tokens at all — starting a server is the
same three lines whether it is signed into or not.

**There is no way to add a server of your own**, and that is deliberate: a URL or a shell
command somebody pasted is an unknown program with the model's hands on it, and a row that
cannot say what it is about to do.

The costs are real and paid for deliberately: a tool that takes a second instead of a
millisecond, a wall of JSON that must be cut down before it can be spoken, and credentials on
disk. **Nothing is connected until somebody connects it** — a person who never opens the panel
has exactly the tools this machine always had, and `mcps/tools.py` is how they hear about the
rest: Happy can say what is connected, what is not, and the one thing somebody presses for
each, without being able to press any of it himself.

### WhatsApp reads over the bridge and writes on the screen

The one connection that is deliberately half a connection. It lives in
`mcps/servers/whatsapp/` and is two processes: `bridge.py` is a Flask server on loopback
running **neonize**, which links to your account the way WhatsApp Web does; `mcp_server.py`
is the MCP side and talks to it over HTTP. Only the bridge ever touches WhatsApp.

Linking an unofficial client is against their terms whether it sends anything or not. That is the
part you accept when you press it, and no amount of care here removes it — but it is written in
the row's note rather than shouted as a warning on the row itself. Amber is for something that
has gone wrong, and this is a standing condition of the connection, not a fault. It reads
"Runs on this machine" like any other local server, which it now is: Happy ships the thing, runs
it on Happy's own Python, and there is nothing left to go and install.

What it is best at is reading. Searching a year of chats for the address somebody sent you is the
one thing driving the app on screen cannot do at any speed, and it is why the bridge earns its
place. It sends too — text, media, and to groups — but sending is the half that gets numbers
banned, because volume and spam reports are the signals WhatsApp acts on.

So the line is drawn at **who asked**. Nothing is gated: a send happens because somebody asked
Happy for it in that turn, and that is the whole of it.

**There is no auto reply, and there will not be one.** Sending somebody just said yes to and
sending nobody was asked about are different things: the second arrives while nobody is
watching, which is exactly the shape that looks like a bot from the outside. Ten tools — seven
read, three send, none of them unattended. There is no allowlist trimming that list either: a
server whose tools are chosen twice is a server that will one day disagree with itself.

**The chat with Happy is a group called Happy**, which he makes himself the moment the account
comes on rather than leaving somebody a setup step. Nothing in there was meant for anybody
else, so everything said in it is said to him and nothing has to be tagged; he is the only
other member. That is not the auto reply above, and neither is `@happy` in any other chat:
both are somebody asking him something in that turn, which is the same line the tools draw.
The tag is read only off the owner's own messages, because anybody in any group can type it
and none of them is who Happy answers to. `mcps/servers/whatsapp/chatting.py` is the loop,
`grouping.py` the one chat that is his, `replying.py` what goes back — and the guards that stop
an answer of his, which reads exactly like a question in there, from being answered again.

**Tagged in somebody's chat, he is told whose chat it is** (`placing.py`), because "tell her I
love her" is only a sentence if he knows who her is, and the chat it arrived from is the whole
answer. He is told the other half too: what he says next is not read out to whoever asked, it
is sent into that chat, so the message *is* the answer. That contradicts the standing rule
about never reading a message out, which is named and lifted for that one turn. Wording alone
does not hold it — a fifth of the time he still reaches for a send tool, and then the errand is
done and his "told her" lands underneath it, in front of the person it was about. So the bridge
notes every send it acknowledged (a message this device sends is never echoed back to it, so it
is in no chat we can read), and Happy never says anything into a chat he has already written
into by tool that turn. The prompt makes the good answer likely; that makes the bad one
impossible.

No cloud storage, no telemetry, no backend callbacks. This runs on one machine for one person.

**Happy starts the bridge itself**, rather than leaving it a second terminal somebody has to
remember — the worst possible shape given the paragraph below, since forgetting it errors
nothing. `mcps/bridging.py` owns it: it starts the bridge when WhatsApp is connected and
not before, never doubles up on one already serving the port, puts down only a bridge it
started, and refuses to respawn a dead one more than once every thirty seconds so that a bridge
which cannot start is one dead process and not a stream of them. Its output goes to
`data/whatsapp.log` and never to ours: in `--serve` mode Happy's stdout *is* the protocol the
window reads, and one Flask request log on it is a panel that stops updating.

**The QR is scanned in a browser, not in the panel.** Pressing Connect opens
`127.0.0.1:3001/default/scan`, a page the bridge serves that shows the code and refreshes itself
every two seconds until it is linked — no script, so there is nothing to authenticate. That is
the same shape as signing into Google, a button and then a tab, so both services work the one
way and the panel needs no QR path of its own.

Two things fall out of that and both are the point. **Connecting is not linking** — WhatsApp's
server starts and offers all ten of its tools with nobody signed in at all, so a row that read
`tools` alone said *Connected* the instant somebody pressed the button and would have said it
forever if they never scanned. The registry marks WhatsApp `scan: True`, and until the bridge
reports a real linked account the row says *Waiting for the QR to be scanned* under **Not
connected**. And because the scan happens in a tab this side would never notice, a watcher
started by Connect looks every three seconds until it lands, then tells the panel to redraw —
the window asks for its settings exactly once, when it starts.

**One button, never two.** A row waiting to be scanned offers Connect and nothing else; a linked
one offers Sign out and nothing else. Both at once asks somebody to work out which of the two
they are, and before the scan there is nothing signed in to sign out of.

None of it is announced in the conversation. That stream is what Happy and a person said to
each other and nothing else — "Scan the QR in your browser" is neither. The service's own row
is already saying it, which is where somebody who just pressed the button is looking.

The failure to know about: **if the bridge is not running, nothing errors.** The MCP half
answers happily from whatever it last saw. A WhatsApp connection that has quietly stopped looks
exactly like a quiet afternoon, which is why `get_status` is one of the ten tools bound to the
model rather than a diagnostic nobody calls.

### Signing in is its own step, not something a refusal sets off

The MCP SDK's sign in is sprung by a **401**: you connect, the server turns you away, and the
browser opens. That assumes a server turns a stranger away, and ours do not — a server answers
`initialize` and `tools/list` to anybody and only refuses when a tool is actually *called*. So
nothing ever sprang it: connecting reported success, counted the tools, switched the service
on, and every one of those tools then failed the first time the model reached for it.

So `mcps/oauth.py` owns the flow and does it in the open, the moment a person presses Connect:
PKCE, browser, code, token, written down. Only after that is the server started and asked what
it offers. There is no discovery step — the one service needing a consent screen is named in
`mcps/registry.py` with the two addresses its sign in uses, so a connection is one round trip
rather than four fetches and a fallback.

Asking in the open is also the only way to get Google's **refresh token**, which it gives only
to somebody who says `access_type=offline` and shows the consent screen. Without those the sign
in is dead an hour later.

**Renewal is not here at all now, and that is the point.** The server holds the credentials, so
it refreshes them itself the moment it needs to and writes the new token straight back into the
same row the panel reads. `mcps/oauth.py` ends the instant the first token is written down.
Nothing that starts on its own can open a browser — a sign in that has finally died surfaces as
the service refusing, which a row can say out loud, and not as a window appearing in front of
whoever is standing there mid sentence.

**The sign in is checked on the way into every tool call, and never once at startup.** A server
comes up when it is first wanted and then stays up for the rest of the day, so an access token
it read at breakfast is a dead token by the afternoon, and there is no moment after startup
when anything would have thought to look again. So the check belongs on the path every call
already takes: `credentials.token(name, renew=…)` reads the row, sees whether the token has run
out, renews it in place and writes it back before handing it over, and every server asks for
its token **inside** the tool rather than above it. A token is treated as gone a minute before
it really is, because a call that takes a second must not set out on a token with a second left.
Google is the one with a refresh token today, and `google/account.py` does the same thing with
`google.auth` doing the renewing.

**Only the service knows how to renew, so only the service says how.** The shared side owns the
policy — when to look, when to give up, what to say — and takes the *how* as an argument.
Nothing in `servers/shared` holds a URL belonging to any one service, and adding a service that
renews differently is a function passed in, not a branch added here.

**A renewal that cannot work is a sentence, not a stack trace.** A refresh token can be revoked
rather than expired — Google drops one weekly for an app left unpublished — and no amount of
refreshing mends that. When the renewal itself fails, or when a token has run out and the
service has no way to get another, the call is refused with `credentials.STALE`, which names
the service and says to connect it again in the panel. That is the one thing that fixes it, and
it is what the person hears.

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

**`python -m hands` prints exactly what the model was handed** — every tool in the order it
sees them, grouped by where each came from, with the description it actually reads. `--full`
adds the argument names, `--prompt` dumps the system prompt word for word, and a bare word
filters. When Happy reaches for the wrong tool, that list and those words are the only honest
place to look; a tool missing there is missing from the model too.

### Adding a service

1. Write `mcps/servers/yourthing/mcp_server.py` — **the whole server, in the one file.** Make a
   `FastMCP`, decorate functions with `@mcp.tool()`, and put the credentials, the HTTP and the
   tidying of what comes back underneath them. **The docstring is the prompt** here too.
2. Take what you need from `servers.shared`: `credentials.token(name)` is the signed in token,
   asked for **inside** each tool so it is checked afresh every call, and given `renew=` where
   the service can get another one; `reaching.Service` is an HTTP client with the sign in
   already on it, and `answering.ok` is what a tool returns. Do not catch exceptions — a tool
   that raises comes back as a failed call carrying the reason, and `mcps/shortening.py` turns
   that into one plain line.
3. Add one entry to `KNOWN` in `mcps/registry.py`: a name, a label, the folder, and whether it
   wants nothing, a pasted token, or a browser sign in.

There is no fourth step. Nothing in the panel, the store or the binding knows any service by
name, so a row, its paste boxes, its button and its tools all appear from that one entry.

The one line of ceremony every server starts with is `sys.path[0] = …parents[2]`, which takes
the server's own folder **off** the path and puts `mcps/` on in its place. Everything is then
reached as `servers.something`. Left on, a file sitting beside the server is what an `import`
anywhere in the process finds first — `google/calendar.py` would be what the standard library
gets when it asks for `calendar`, and the `google/` folder itself would swallow the real
`google.auth` that `googleapiclient` needs.

Split a server across files only when it earns it. Google is four — `mail.py`, `calendar.py`,
`drive.py` and the `account.py` all three sign in through — because one file for all fourteen
tools would run past 200 lines. The others are one file each.

Two rules the servers live by. **Every tool you write is a tool the model gets** — there is no
allowlist to also remember, and nothing gates a call once it is bound. The single exception is
`mcps/binding.py`'s `OURS`, which Happy calls himself and never shows the model; put a tool in
there only when he is the only one who would ever call it, or it is six more schemas read on
every turn for nothing. And **name tools so a reader can tell what they touch**:
`search_emails` reads, `send_email` sends, and the name is the only warning anybody gets.

A service that signs in as somebody answers `who_signed_in()` too, returning the name on the
account and nothing else. It is in `OURS`, so it costs the model nothing; `mcps.signed_in()`
asks every server that offers one, all at once on the shared loop, and `hands/owner` turns
that into the name Happy calls the person he works for. A service with no account of its own —
Weather — simply does not write one, and nothing has to be told that.

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
reliably raise one already running, and a zero exit code says nothing about which window came
forward. Trusting it once meant WhatsApp never appeared, Opera stayed in front, every look
afterwards read Opera's window, and the model went hunting for a chat in a browser. So the
application is told to activate, waited for until it really is in front, and when it is not,
that is said out loud along with "do not click". Everything downstream reads whatever is in
front, so this is the one claim the rest of a task rests on.

**Bound the loop.** `brain.calls` caps how many times the model may go round before it has to
answer. A loop that keeps going is a person staring at a silent assistant, which is worse than
a half answer. **But bound it above the real work**, which is easy to underestimate: opening an
app, finding a chat, typing and sending is six rounds with nothing going wrong, and the glance
to see where the click landed makes seven. The default is fourteen, and it costs a short answer
nothing — a cap only bites when the work is long.

**History is trimmed, not kept.** `recent()` keeps the last `brain.history`
messages, starting on a human message so a tool reply never appears whose tool call was
trimmed away. That orphan is an API error, not a degradation.

## The ears

**The key is the only way in, and it needs no name at all.** `ears/trigger.py` watches one
modifier globally — `ears.key`, Right Option by default, and every option is a modifier so
holding it never types anything. Held, it records; released, it transcribes and hands the whole
take over without matching a name, because holding a key down is already somebody saying who
they are talking to. On macOS the permission belongs to whatever started Python, and an untrusted
listener is handed only this process's own keys — which looks exactly like push to talk working
until you click another window — so `ears.DEAF` says so on startup.

**There was a wake word and it is gone.** "Hey happy" worked by keeping the microphone open,
capturing every run of sound in the room, transcribing all of it, and throwing away everything
that did not have his name in it. That is a speech model decode per utterance anybody nearby
makes, plus a second early decode purely so the window could react before the take had ended,
all of it to save reaching for a key. It also could not be trusted: it failed silently on a
headset that handed over digital silence, it needed a matcher tolerant enough to read "hay
happy" as his name and therefore loose enough to answer things that were not, and a whole layer
existed to guess whether a sentence that stopped mid-thought was finished. The key has none of
those questions in it. Do not bring the wake word back without an answer to the battery.

**Nothing is heard between takes.** The device opens on the press and shuts on the release, so
there is no stream running while nobody is talking to him — no blocks arriving, nothing decoded,
and the system's own microphone light off. That light is the only thing a person can check, and
it should mean what it says.

**Barge-in is the key.** Pressing it reaches `Speaker.stop()` from the listener's own thread,
before any device opens, so cutting Happy off mid-sentence is the same gesture as asking him the
next thing. The window's stop button does it too.

**A dead microphone is not somebody who said nothing, and only the code can tell them apart.** A
device that has stopped hearing still hands over blocks on time, all of them zero — AirPods take
the default input the moment they connect and some hand over nothing at all. So a take that came
back with no words in it is checked for being pure zeros, and Happy says which device is doing
it. Only an empty take is ever a reason to look, which is why this cannot cry wolf about a press
that really was silence. `ears.microphone` pins one device by name so a headset connecting cannot
take the ears away again; empty means whatever the system picks.

**Parakeet TDT 0.6B v2**, int8, through `onnx-asr`. Measured on this machine over the fifty takes
in `recordings/`: **232.8 s of speech in 4.5 s — 51.8x realtime**, against WhisperX medium's 2.9x.
The model loads and warms in 0.77 s where WhisperX took 2.89 s. 631 MB in `models/parakeet/`.

**v2 is the English one, and it was picked over multilingual v3 by listening.** v3 covers 25
languages and mis-hears *"open the most recent **chat**"* as "chart" or "set" in four of the fifty
takes. That phrase is a command Happy is actually given, so being right about it beats a language
nobody here speaks. v2 gets all four. There is no `ears.language` knob, because this model takes
no language at all.

**int8, and no knob for it.** Full precision is 2.55 GB against int8's 631 MB for a vendor claim of
parity. A knob whose other setting nobody has downloaded only ever produces an error.

**`ears.device` names an execution provider, not a torch device.** Left alone, onnxruntime puts
CoreML ahead of CPU and would compile a 650 MB encoder on the way up; CPU is pinned by default and
`auto` is opt-in and unmeasured.

Silence comes back empty, which mattered as much as the speed: WhisperX answered one 1.5-second
take of room tone with "Thank you." Two things got worse and are written down rather than hidden
— one quiet take WhisperX heard and this does not, and proper nouns are no better. `python -m
ears` transcribes everything in `recordings/` with timings, which is how both were found.

Nothing imports torch, which is 55 packages and a gigabyte not installed.

## The voice

**Kokoro** speaks everything except Telugu, which **Piper** reads. One engine and one named
exception — not a fallback layer. `voice/engines.py` names both and imports only what is asked
for; `ELSEWHERE` there is the whole of the exception, and it has one entry.

*This reverses an earlier decision, on purpose.* Piper was picked first on speed and Kokoro was
rejected for being slow, and the numbers were right — measured on this machine, warmed, Piper is
**20 ms to first word** and 54x realtime, Kokoro is **234 ms** and 4.4x. What that reasoning got
wrong is what the slowness costs. Piper is intelligible and metallic, and a person asked to
listen to it all day hears a machine every time; the quarter second before Happy starts talking
is roughly the pause a person leaves before answering anyway, and 4.4x realtime is still four
times faster than the mouth it is feeding. Speed only reads as competence while the voice is one
somebody wants to keep listening to.

**macOS `say` was tried and rejected; do not reach for it again.** Asked to write a WAV so the
speaker keeps barge-in, it is 330 ms warmed and flat at that whatever the sentence. Its fast
path, `AVSpeechSynthesizer` at 12 ms, cannot be used: the callback only fires on the main
thread's runloop, while sentences are synthesised on a daemon thread and the main thread sits
blocked waiting to be spoken to. Windows SAPI was never measured, since the macOS half already
failed.

Phonemes come from an espeak-ng that ships inside a wheel, so there is nothing to install by hand
and it behaves the same on Windows.

It is **one 326 MB model** plus a half-megabyte style per voice, so a voice costs almost nothing
once the model is down. The style is a table indexed by how many sounds are in the sentence,
which is why `sound()` picks its row off the token count rather than loading anything, and why
the model is loaded once per run and shared by every voice rather than per voice.

**Telugu is Piper's, and the reason is worth writing down because the obvious test lied.**
Kokoro has no Telugu voice. Its Hindi voices look like they could stand in: espeak spells Telugu
into sounds, and **100% of them survive Kokoro's alphabet** — nothing is dropped, so on paper it
reads. It does not. A symbol being *in* the alphabet is not the model having been *trained* on
it in that position, and Telugu's palatal `c`, its `ʋ` and its vowel runs are not things the
Hindi voices ever saw. What comes out is fluent-sounding nonsense.

*Do not re-test this with speech recognition.* Synthesising Telugu and reading it back with
Happy's own Telugu ear scored **0.90 / 0.93 / 0.98** against Piper's 0.94 / 0.96 / 0.98, which
says the two are equivalent. They are not, and the number is an artefact: Whisper carries a
language model strong enough to reconstruct the intended sentence out of mangled sound. It was
measuring its own guessing, not Kokoro's speaking. A person listening heard gibberish
immediately. **For "is this intelligible", the ear is the instrument.**

**A voice handed a script it cannot read says the name of the language out loud, once before
every letter.** This is espeak's behaviour, not a bug in anything here, and it is the single
worst-sounding failure in the voice: `"Downloads folder తెరిచాను."` came out as *"telugu, telugu,
telugu…"* for fifteen seconds. It happened because the language of a sentence was picked by
`tongue.language()`, which answers *which language most of it is in* — and two English words beat
one Telugu word, so the sentence went to an English voice that could not read a third of it.

Choosing a **voice** is not the same question as identifying a language. `tongue.reading()` is
the one to use: the language whose voice can read *all* of this, hardest script first. One
Telugu word in an otherwise English sentence makes the whole sentence Telugu's, because an
Indian voice reads an embedded English word perfectly well and the reverse is a catastrophe.
Mixed sentences also make espeak switch languages mid-way and mark where it did; those marks are
sound if left in, so `phonemes.sounds()` asks for them removed while keeping the words.

So `ELSEWHERE = {"te": PIPER}`, and Kokoro's `say()` hands a Telugu sentence to a Piper voice
built the first time one arrives. Piper runs at 22050 against Kokoro's 24000, and rather than
teach the player about two rates, `clips.resampled()` puts Piper's output on Kokoro's rate on
the way out — so there is exactly one sample rate in the system and `Speaker` never learns that
any of this happened.

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
- **A sentence is spoken in pieces, not after it.** Nothing is heard until a mouthful has been
  synthesised, and the model costs about **a tenth of a second flat plus another per 200 sounds**
  — so a full-length sentence was a **two second** wait with its words already on the screen.
  `phonemes.mouthfuls()` now cuts a short first mouthful (`FIRST`) and leaves the rest long, and
  `Speaker.pour()` queues each piece the moment it exists rather than at the end of the sentence.
  First sound is **0.35–0.45 s whatever the length**. The rest is made at 7x realtime, so it is
  always there before it is wanted — checked against PortAudio's own underflow flag, not by ear.
  Under `WHOLE` a sentence is still said in one go: the join would cost more than the wait saves.
- **The join is free, and that is measurable.** Each piece is trimmed and faded by `clips.tidied()`
  as mouthfuls always were, and only the last one gets the breath on the end. Across the seam the
  step between samples is **0.0000** and the lull is **25 ms**, against the 100–184 ms pauses the
  model puts inside the same sentence unsplit. What splitting does cost is prosody: the second
  piece starts its own intonation, which is why the first is the only short one.
- **The output device is opened once and held.** `sd.play()` builds a whole stream per clip —
  **120 ms** of silence before every piece, and **1.5 s** when CoreAudio has let the device sleep.
  One `OutputStream` is kept and written into in `BLOCK_MS` blocks, which is also how long barging
  in takes to land, since the lock is let go between them. When nothing is pending `rest()` stops
  the stream without closing it: starting again is **30 ms**, flat however long the silence was.
- **Abbreviations are not sentence ends.** That short first-sentence floor makes "Mr. Stark
  is on the phone" likely to break in half, so `SHORTENED` and the single-initial rule catch
  it. Decimals are already safe — the split needs whitespace after the full stop.
- **Barge-in is `Speaker.stop()`**, reached from the key's own listener thread the instant it
  goes down, before any microphone opens. So cutting him off is the same gesture as asking the
  next thing, and the window's stop button does it too. Everything queued is dropped and
  playback is cut.
- **In-flight work is cancelled by an era counter**, not by trying to kill a thread. `stop()`
  bumps it; work stamped with an older era is thrown away when it surfaces.
- **The count of what is still to be said is stamped with an era too**, and `settle()` ignores
  anything older. Without that, a sentence cut off mid-synthesis would take its count off
  whatever was being said *instead* when it finally surfaced, and Happy read as finished while
  still talking.

## Searching the web, and reading a result

`hands/web/` is two tools and the line between them and everything else is worth holding.
**Searching** is `search_web`: a question in, five titles and summaries back. **Reading** is
`read_page`: one address in, the words on that page back. **Opening** is `open_url`, which
puts a page in front of the person. An **errand** is clicking and typing on a site, which is
the browser and nothing else. Most of what gets asked out loud — a score, a price, when a
place opens, what the weather is — is the first two, and before they existed the model either
guessed or said it could not check.

**The answer is almost never in the results. It is inside one of them.** A snippet describes
a page rather than quoting the number off it: search "hyderabad weather today" and five
weather sites come back, not a temperature. So `search_web` finds *which page holds it* and
the model picks one and reads it. That choice is the model's and is deliberately not
automated — nothing in this module decides which result is the answer. The prompt and both
docstrings say the same thing, because a search tool that returns a list is the single easiest
thing for a model to answer straight out of and be wrong.

**It is requests and parses, not a browser.** A results page is plain HTML that says
everything it has to say without running a script, so `httpx` fetches it and `BeautifulSoup`
reads it: **about a second**, against the seconds a browser costs before it has even
navigated, and none of the memory. A whole search-then-read-a-result round is a second plus
one page fetch. A browser here would buy nothing but the wait, and somebody is stood in their
kitchen through all of it.

**Two engines, tried in order.** `hands/web/engines.py` is the only file that knows how any
engine writes its page; everything else sees the same three fields. The second door is not a
luxury. An engine that decides a script is asking serves a **captcha with a 200 on it**, which
parses as zero results and is otherwise indistinguishable from a question nobody has ever
written about — so the page's own title is checked for one, and a refusal moves to the next
engine rather than being reported as ignorance.

**A search engine wants a browser asking. A page's own host often wants the opposite.** This
inverts and it will waste your afternoon if you assume one identity does both. The engines
serve a script a different page or none, so `searching.py` asks wearing Chrome's user agent.
Wikipedia does the reverse: it **403s anything calling itself Chrome** and answers an honest
`Happy/1.0` — but only one with a contact URL in it, so `Happy/1.0 (voice assistant; reads a
page)` is refused and `Happy/1.0 (+https://github.com/thepropotato/happy)` is served. So
`pages.py` says who it is first and only dresses up for the hosts that turn that away, which
is one retry and covers both populations. AccuWeather is the mirror image of Wikipedia: it
answers the honest one and 403s the browser.

**A site that will not hand its text over is one site, not a dead end.** Some 403, some are a
JavaScript shell with nothing in it, some trickle a script along until it times out. All three
come back as one plain sentence ending *"Try another result"*, and both docstrings and the
prompt say to read the next result down rather than guess at what could not be read. Ten
seconds is all any page gets, because there are four more behind it.

**Tried and rejected: the instant answer API.** `api.duckduckgo.com` returns an abstract for
encyclopedic queries and an empty string for everything live — nothing for the weather,
nothing for a conversion, nothing for who runs a company. A second request on every search to
occasionally repeat what result one already says is not worth the wait.

**Not used: a search API.** Google's Custom Search JSON API needs a key *and* a search engine
ID, gives 100 queries a day and then charges, and puts a signup in front of a machine that
otherwise needs none. Reading the HTML costs nothing and needs nobody's account. The day the
engines start refusing in earnest, that is the trade to revisit — and it is a new entry in
`ENGINES`, not a rewrite.

## The browser — blank, being rebuilt

> `hands/browser/` is empty on purpose and is being written again from scratch. None of what
> follows is code, and all of it is still true about this machine, so read it before writing
> the next one. Unprompted speech went with it: `face.console.unprompted()` is still there
> waiting, and nothing sets the `unprompted` column.

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

`open_url`, in `hands/apps/`, is for anything an address reaches — a site, a video, a search. It
lands in the browser you already use, signed in to your accounts, and it is what "play this on
YouTube" should always have done. Without it the model reaches for `open_app` instead and types
into whatever that opened: when `open_app`'s docstring offered **"Safari"** as its example, that
is exactly what happened. An example in a tool description is an instruction.

It addresses your **profile**, not just your application, and that distinction is the whole
point. The system opener hands a link to whichever copy of that browser is already running,
so while a browser errand has one open on Happy's own profile, your link can arrive in a
window signed in to nothing. A Chromium started with no profile flag uses the one you browse
with and forwards the address to that window when it is already open. Safari, Firefox and
unknown platforms fall back to the system opener.

**The docstring is where an invented address gets stopped, because the docstring is what
invited it.** Asked to play a song, the model called `already_open`, found nothing and went
straight to `youtube.com/watch?v=example` — it has never been told a video's id, so it filled
the slot with the word that fills slots and then said the song was playing. The prompt said
twice to search first and it was not read at the moment of the call; what *was* read was this
tool's own description, which offered **"a video, a search"** and *"accepts a full address"*.
That is an instruction, the same way `open_app`'s **"Safari"** was. So the description now
says where an address may come from — a search result, a tool, their own mouth, or a site's
bare name — and `already_open` ends on *search and open what comes back* rather than "open or
search for it as normal", which is the fork it took.

**Tried and rejected: checking the address exists first.** A fetch before handing it to the
browser would catch a made-up id in general rather than one shape of it, and it does not
work: `youtube.com/watch?v=example` answers **200**. The page is a script shell that only
says the video is gone once it runs, and this is the same wall `pages.py` documents. **Tried
and rejected: remembering every address a tool handed over** and refusing any other. It works
— a search result and the address opened out of it reduce to the same thing — but it is a
module, a store and a hook in `keep_record` to enforce one sentence, and every tool that ever
returns a link has to feed it. **Tried and rejected: a list of stand-in words** (`example`,
`VIDEO_ID`, `xxxx`): that is fitted to the one token this model happened to write, and it
never catches a plausible id.

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
| A `Modelfile` with `PARAMETER num_ctx N` | Works, and is the wrong fix. |

The Modelfile is the right fix for the wrong problem: it exists only because the OpenAI `/v1`
request has nowhere to put a context length, so it bakes one into a copy of the model under
another name — a setup step, a second name for the same weights, and a fact only true on the
machine where the tag was built. Talking to Ollama natively makes it a field on the request.
**Prefer a provider's own client over a compatibility shim**: a shim quietly drops whatever it
cannot express, which is exactly how this cost an afternoon.

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

Happy has three, and none of them knows about the others. Everything he does is reported to
`face/show.py`, which hands it to whichever faces are attached — a terminal, a window, the log,
any of them, none. A face that has no opinion on something simply does not define the method, and
`show` skips it. That is why the microphone can report its loudness ten times a second without
`face/console.py` growing a single line about it.

`main.py` attaches the terminal or the window at startup, and that is the whole of the difference
between the two ways of running Happy. The log is attached either way.

**The log is a face and not a logging library.** `face/log.py` writes one stamped line per event
into `data/happy.log` — the same account the terminal gives, kept, and the only account at all
when Happy is running behind the window. Nothing anywhere has to remember to log, because it
hears exactly what the other two hear. What it leaves out is the live part: how loud the room is
and which mood the orb is in are not events, and both arrive ten times a second.

Every line is one line — a reply with newlines in it is flattened on the way in, because a log
where one event can span six lines is a log nothing can grep. The kind column is the thing to
grep for: `run`, `note`, `you`, `tool`, `no` for a call that worked and found nothing, `happy`,
`spent`, `error`. **Full logs** in the Memory controls writes `memory/viewer.html` out around it
and opens that, which is the same lines with the kinds coloured and somewhere to search them.
The file itself is the real thing, and anybody who would rather `tail -f` it should.

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
not know a terminal exists.

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
Electron exiting ends Happy, because the reader in `face/requests.py` sees stdin end and shuts him
down.

**The panel has no close button, only minimize.** A cross would promise something it cannot
mean: Happy is still listening with the panel shut, and the key is global precisely so it works
from anywhere. So the button puts the panel away and nothing else. Ending him lives on the menu
bar icon, which is where a thing that ends him belongs.

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
- **Every tool call as one row**, on a solid surface rather than a wash over the moving colour
  behind it — it is a block of machine output in the middle of a conversation, and the aurora
  drifting through its arguments made it the hardest thing on the panel to read. Shut, the row
  is the tool's name and the model's own reason for calling it, clipped to one line. Open, that
  reason takes a line of its own beneath the name — it is a whole sentence, and sharing a row
  with the name and the stopwatch left it a fragment exactly where somebody had asked to read
  all of it — and the **Arguments** and the **Result** follow underneath.
- **A box to type in**, because not every question is worth saying out loud. A typed line takes
  the same turn a spoken one does, on the same lock, so the two can never overlap.
- **Every control**, which is the next section.

**None of his own plumbing.** "Loading models", `Answering in "Happy"`, a model being fetched:
the terminal prints those and the log keeps every one of them, and the panel simply has no
`note` method, so `show` skips it. The stream is what the two of you said to each other, and it
was already saying "loading" twice over — the orb, the mood and the hint are the whole face of
the panel while he wakes up, and a line of text under them repeating it is the second copy.
Something going *wrong* still lands there, because that is about what you asked for.

Sound outlives the words. Happy is still a sentence behind himself when the model has finished,
so the panel goes quiet when the last clip ends and not when the last word arrives.

**The orb yields.** It owns the panel while there is nothing to read and shrinks into the header
the moment there is, which is 250 pixels won back for the conversation. What it was saying
carries on beside his name. Tapping the small one brings the big one back.

**The key he wakes to is under the orb**, in the hint, named as the key you actually press, and
the orb itself moves with the room whenever a take is running. The hint is sent again whenever a
knob moves, because a hint still naming the old key is a hint that is wrong.

**The controls are the whole panel**, not a drawer over part of one, and they are six sections
that fold open where they sit rather than six tabs over fifty knobs. A shut section still says
what it is set to, because most visits are somebody checking rather than changing, and anything
set once and never again is marked `rare` in the catalogue and sits behind one more tap.

### He comes up when he is spoken to

A panel that hides when it loses focus is a panel that is never on the screen at the moment it
matters: you hold the key with another application in front, and nothing anywhere moves. So
a turn nobody opened the window for brings the window up on its own — `showInactive()`, never
`show()`, because taking the focus would pull the caret out of whatever sentence somebody is in
the middle of typing. It goes away again five seconds after the turn ends, unless it was pinned,
opened on purpose, or clicked on in the meantime.

This is the other half of "the key is global". The permission makes him *hear* it from anywhere;
this makes him *answer* somewhere you can see.

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
out of a setting — the graph, the speech model, the voice — checks a
counter that only goes up, and puts itself back together when its own group has moved. The
counter is per group, so nudging the voice pace does not rebuild the brain. The conversation
survives a rebuild because the checkpointer outlives the graph.

Two of them are not knobs so much as a broom: `memory.messages` and `memory.recordings` say how
many days to keep things, and `memory/pruning.py` runs once at startup. Zero keeps everything,
which is what they ship as.

### A connection is not a setting

Connections as ordinary knobs was tried and does not work: every service became a row for the
switch, a row for signing out and a row per secret, twenty-one identical rows deep, in which a
timeout slider, a client secret and a thing you sign into all looked the same — and nowhere did
it say what was actually connected.

So `memory/kinds.py` has three shapes that are not settings, and `mcps/panel.py` builds the
whole panel out of them: a **heading** over a run of rows, a **service** — one row saying what
it is and how it is, with what it wants folded inside until somebody taps it — and a **folded**
row, which is an ordinary group of knobs behind one line. The two global settings live in one
of those at the bottom, because nobody opens this panel to move a timeout.

What is *inside* a service is still ordinary knobs, so the window draws the boxes and buttons
with the same code it draws everything else with. It knows what a service looks like and still
nothing about any particular one — which services exist, what each wants pasted and what is
worth warning about are all in `mcps/registry.py`.

**Google is one row because it is one server.** One account agreeing to mail, calendar and
drive is one question, so it is one row, one sign in and one process — no family, no members,
no row inside a row.

A connected service shows the **tool names it hands over**, which is simply everything its
server offers. There is no filtering step left to disagree with the list.

**Connected means used**, and there is no "Let Happy use this" switch. It would describe a
state nobody wants — a service you went and signed into that then answers nothing — and signing
out is already the way to stop a service. So there is no `enabled` column either: a service is
connected when it remembers tools, every tool it remembers goes to the model, and signing out
forgets them. One state, one place, nothing to disagree with.

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

**There is one table and one index, and that is deliberate.** An FTS5 full-text index was tried:
it works, and it quietly brings four shadow tables and three triggers with it, none of them ever
read by anything here. That is a lot of machinery to avoid a scan taking **159 ms across two
hundred thousand messages**, which is more than anyone will ever say to Happy. So
`memory.search()` is a `LIKE`.

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

`hands/files/` is the answer to "I don't have the ability to read that file". `read_file`
handles PDF, Word, spreadsheets, presentations, RTF and anything textual, and always returns
plain text — the model should not have to know which kind of file it is before it asks.

A person does not say "read `/Users/me/Documents/CV_final_v3.pdf`", they say "read my resume".
So `read_file` takes a description as readily as a path, and `find_files` searches where
people actually put things — Desktop, Documents, Downloads — rather than the whole disk,
pruning `Library`, `node_modules` and friends.

Long files are cut at `MAX_CHARS` with a marker, and `start` reads on from there.

Images go to `eyes/` because OCR is not guessing: `.png`, `.jpg`, `.bmp`, `.tiff` and `.webp`
are formats like any other in `READERS`. `.gif` and `.heic` are only named, because OpenCV will
not reliably decode either, and a name beats a confident hallucination. Happy still does not
*look* at a photograph — he reads the text off it, so a screenshot of a message reads fine and a
picture of a dog comes back empty.

## Seeing the screen

`eyes/` answers three different questions and it matters enormously which is which.

**What is there** is the accessibility tree: the application is *asked* what it drew. About
**90 ms**, exact, and the only source that knows a thing's *kind* and *state*. `list_controls`.

**What does it say** is OCR: exact about the letters, blind to everything else, and about a
second and a half for a full screen. `read_screen`.

**What does it look like** is a vision model: tens of seconds, and needed far less often than it
looks. `look_at_screen(question)`.

**What is this person doing** comes before all three and costs **40 ms**: the application in
front and the title of its window, which is nearly always the specific thing — the file, the
page, the episode. `current_activity`. Asked to tell somebody what he was up to, Happy used to
answer "I'm on my computer", which is what whoever asked had already assumed, and when pushed
would invent a photo gallery he had never seen and send that to them.

**It is a tool call and nothing else.** For a day it was not: a message turn was *handed* what
was in front before the model started, because told to look he looked about one time in three,
and 40 ms beats an extra round trip to the model every time. It worked and it was still wrong.
An answer about somebody's screen turned up with no row on the exchange, nothing in the log and
no tool on the turn in the database — from the outside, a look and a guess are the same thing,
which is exactly the failure this was meant to end. So the injection is gone and the standing
rules carry it instead: the third-person phrasing a chat actually uses ("what is he doing",
"what is she up to") is named there beside "what am I doing", because that is the one wording a
model reads as somebody else's business.

The other half was that he looked and saw himself. His panel comes up over everything the second
the key goes down and stays the active application while anybody types into it, so the system's
honest answer to *what is in front* was "Electron" — and that is what he told somebody. He is
skipped now: `attention.pile()` walks the windows front to back, past his own process and its
parent, past the menu bar and every other floating thing, and the first ordinary window left is
what somebody is actually doing.

**"What am I doing" is that person; "what are you doing" is Happy.** One is answered by looking
at their screen and the other has nothing to do with it, and both the standing rules and the
tool say so, because a model that blurs the two answers a question nobody asked.

The order is the whole design. Asking beats looking by roughly ten to one on time and does not
lose the argument on quality either — a picture cannot tell you that the Share button is greyed
out, that a box is ticked, or where the keyboard is. Pixels are for what has no structure to
read.

### Asking the application

`AXUIElement` on macOS, UI Automation on Windows. On macOS this needs no new dependency and
`AXIsProcessTrusted()` is the one permission the panel asks for out loud, so it is usually true.

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

Matching is scored, not first-hit: `"OUTPUT"` matches the sentence *"we may also feed the OCR
output"* exactly as well as it matches a tab labelled OUTPUT. So a match is worth **how much of
the label it accounts for**, which is all of a button and almost none of a paragraph. Below the
floor the model is asked, which is slower and better than a confident wrong click.

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
A screenshot is one observation of the state, and not the best one. `eyes/agreeing.py` fuses
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
**OCR never runs inside the verify loop** — it puts five seconds on every act.

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

The case that proves it: clicking a Finder sidebar item straight after bringing Finder to the
front does nothing at all, because the first click activates the window. What comes back is
*"I clicked Documents but nothing on the screen changed"*, which is both true and the thing you
needed to know.

**Waiting is two questions, not one.** `settled()` first waits for the screen to *react*, then
waits for it to *stop*. Waiting only for it to stop is a bug that looks like it works: a window
that has not started yet is also perfectly still, and would be judged a failure a tenth of a
second before it opened.

**It never retries.** A click that did nothing is reported as a click that did nothing. Pressing
an unknown button a second time is how one failure becomes two. What it does instead is wait
half a second and look once more, because a slow window is the commonest reason a good click
looks like a bad one.

**Nothing a click could do stops it.** Delete, send, spend, install, quit — the label is read to
find the thing, never to decide whether pressing it is allowed. Happy presses it and reports what
happened.

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
here for the eyes and the recorder. On macOS the accessibility tree needs nothing new either.
**Windows needs `comtypes`**, and says so plainly when it is missing instead of failing oddly.

**What is verified and what is not.** Clicking, typing, shortcuts and scrolling are proven end to
end on real UI — Finder and System Settings — including the greyed-out refusal, the unknown
target, and the honest failure report above. The thin-tree fallback is proven against VS Code.
**Every Windows path is written and unrun.**

## Which project they are working in

Asked how many commits he had made today, Happy ran `git rev-list --count` in the home folder,
was told it was not a repository, listed the home folder, and gave up. Told the project was the
one he was working in, he called `current_activity`, got back **"Code is in front, and the
window is *Evaluate wakeword vs pus… — happy*"** — the name of the folder sitting right there in
the title — and then ran `pwd` in the home folder as if that were an answer to where somebody
works. It took being told *the project inside VS Code, not VS Code* before he found it, and he
found it by listing Documents, then Desktop, then `Desktop/projects`, one after another in front
of the person who already knew.

**A window title is a name. It is not a path, and a path is what every other tool needs.** That
is the whole of what was missing, and it was never a question about code: a PDF open in Preview,
a letter in Word, a picture in an image viewer are all the same sentence — *send this one*, *read
this one*, *what is in here* — and all of them die on the same step. So the piece that fills it
is `hands/files/infront.py` and the tool is **`file_in_front`**, which answers for anything open,
and the project half is one of its answers rather than its purpose.

**Two ways to find out, and the good one is asking.** macOS will tell you outright: a window's
`AXDocument` is the `file://` address of what it is showing, so Preview, TextEdit, Word and Pages
hand over the exact file and nothing is searched for at all. `eyes.attention.document()` is that
question. Only when it comes back with nothing is the title read instead: split on what an
application puts between a file, a folder and its own name — the em dash VS Code uses, the en
dash JetBrains uses, the ` - ` Windows spells it with, brackets, parens, the ● that means unsaved
— and each piece looked for on the disk. A piece with a suffix is looked for as a file, one
without as a folder, and a folder holding a `.git` beats one that merely has the right name.

**An Electron window answers `AXDocument` with an empty string**, so every VS Code-shaped editor
takes the title route no matter what, and **Windows has no such property at all** — there the
title is the only route. That half is written and unrun.

The last piece of a title is tried first, because that is where VS Code puts the folder, and the
first is tried next, because that is where JetBrains puts it. Pieces that could not name anything
never cost a walk round the disk: the application's own name, `(Workspace)`, and above all a
piece ending in `…`, which is a title bar running out of room and never the name of a real file.
Only the front window is worth the whole search; the ones behind it are looked up **only when
their title plainly names a file**, which is what keeps "the PDF behind the editor" cheap and
stops a browser tab's title being hunted across the disk. Browsers are skipped outright and say
so: a page is not a file, `already_open` reads tabs and `download` is what puts one on the disk.

**What it adds over what was already there is the exact path and the project.** `read_file` and
`attach_file` have always taken a bare name and found it themselves through `locate`, so a file
with a distinctive name was already reachable. What they cannot do is tell two files of the same
name apart, or name the folder a command has to run in. That is this.

### The name was the whole fight

It was `current_project` first, and asked how many commits were made today it worked five times
out of five. Widened to cover documents it was renamed `whats_open` — and Happy **stopped calling
it entirely**. He reached for `current_activity` instead, got the title, and invented
`~/happy` and `/Users/me/happy` out of it: the original failure, back verbatim, from a rename.

Two things fixed it. The name became `file_in_front`, which says *path* rather than *open* and
stops colliding with `current_activity` and `already_open`, and **`current_activity`'s own
docstring now hands off** — it says in as many words that it gives a name and never a location,
and that working a path out of a title is making one up. That is the one the model actually
reaches for, so that is where the signpost has to be. Back to three out of three, in two calls.

**A tool nobody picks is worth nothing, and what gets it picked is the name and a handoff from
the tool it is being confused with.** Not the docstring on the tool itself, which is only read
once it has already been chosen.

## The shell tool

`run_command` is the widest thing Happy has and the one holding the knife. A misheard word is
a different command, and it runs anyway: **nothing asks.**

`hands/shell/guard.py` is the plumbing — which shell the command is handed to, and how what it
printed comes back — plus one steer, `deleting()`, described below. There is no list of dangerous
shapes and no gate. `sudo`, piping the internet into a shell: all of it runs the moment the model
asks for it. Happy is autonomous by design, and that is the trade the design makes. Do not add a
capability that assumes something downstream is checking.

## Deleting

**Nothing waits on a yes, and deleting is not the exception.** A spoken *"shall I?"* gets a
reflexive yes, which is a turn-taking noise and not a decision, and reading a command back to
somebody who cannot hear a path is not a check. Confirmation also guards the wrong failure: the
common case is not that Happy misheard, it is that the person meant it and wanted it back an
hour later.

**So the guardrail is reversibility, not permission.** `move_to_trash` in `hands/files/` is the
only tool that deletes, and it does not delete: it moves the thing to the Trash, where the person
puts it back themselves without Happy. Nothing asks, nothing waits, and the mistake stays fixable.
`hands/files/trashing.py` is the mechanism — `NSFileManager.trashItemAtURL_` on a Mac, which asks
nobody and leaves Put Back working, the Recycle Bin through `Microsoft.VisualBasic` on Windows,
and the freedesktop `.trashinfo` folder on Linux.

**Windows asks for the Recycle Bin and is not told when it does not get one.** There are four
ways a delete that requested recycling is carried out as a permanent one instead: the item is
**larger than that drive's bin**, the drive has **`NukeOnDelete`** set, the item is on a
**network** drive or **removable** media (neither keeps a bin), or the machine has the
**`NoRecycleFiles`** policy on. In every one of them Windows destroys the thing, warns nobody,
and returns success. `Microsoft.VisualBasic` cannot see any of it.

`FOF_WANTNUKEWARNING` on the raw shell call is Microsoft's answer to exactly this, and it is the
wrong one here: it warns by putting a modal dialog on the screen, which is a yes to wait on, in
front of somebody who may not be at the machine.

**So `recoverable()` asks first, and the answer decides.** One PowerShell script, one word back:
drive type, the `NoRecycleFiles` policy, the volume's `NukeOnDelete`, then the item's total size
against `MaxCapacity` — falling back to Windows' own default of a tenth of the first 40 GB plus a
twentieth of the rest when nobody has set one. Anything but `SAFE` and the thing is not touched.

**Unknown counts as unsafe.** A missing volume GUID, a script that threw, a timeout, an empty
answer, output that does not parse — all of them land on the same refusal as a definite no. The
one direction this must never fail in is *proceeding while unsure*, so the default is refusal and
the `catch` at the bottom of the script prints `UNKNOWN` rather than letting the run die quietly.
An absent `BitBucket` key is not an unknown, though: it is the ordinary case, and it means nobody
ever changed the settings.

**It is the slowest check, so it runs last** — after `meant()` and `allowed()` — because it adds
up every file in a folder before it can answer. It gets 90 seconds rather than the usual 15.

**A link is not the thing it points at.** Nothing here calls `resolve()` on the way to a delete;
`whole()` makes a path absolute without following it. `resolve()` hands back the *target*, so a
shortcut given to it comes back as somebody's real folder, which is then what gets trashed while
the shortcut sits on the desktop untouched. That is the quietest way this could destroy
something, and `named()` keeps the same rule one layer up: a link is *the shortcut*, never *the
folder, it had 30 things in it*, because none of the thirty are going anywhere.

**Where the refusals are is the whole point.** They live in the tool that holds a *path*, never in
the one that holds a *command string*. `allowed()` turns down three things and nothing else: home
itself, anything outside home, and the folders a home is built around (`Documents`, `Desktop`,
`Library`…). Those are not "delete a folder", they are a different act wearing the same words.
Everything else goes, unasked.

**It never guesses which one.** `read_file` picks the first of several matches and says so, because
reading the wrong file costs a wasted sentence. `meant()` refuses and reads the paths out instead,
because trashing the wrong one costs somebody's work. The docstring closes the loop that would
undo this — *do not call it again with the same name* — since a model told "several matched" will
otherwise retry verbatim.

**It counts the folder before it moves it.** The count is the only warning anybody gets that more
went than they pictured, and it cannot be taken afterwards.

**`deleting()` in the shell guard is a steer, not a wall, and the comment there says so.** `rm`
has endless spellings — `find -delete`, a two-line Python, a `mv` over the top — and a blocklist
over a shell is theatre. It exists to turn a model that reached past `move_to_trash` back towards
it, which is the same move as the `find_files` → `read_file` handoff above: what gets a tool
picked is the name and a handoff from the tool it is being confused with. Nothing downstream may
assume it checked.

**A date written into a command is a fact he was never given.** Asked how many commits were made
today, he wrote `--since=2024-08-16` — the right day of the right month, two years out, because
he was working the year out rather than asking for it. `where_we_are` was sitting there and he
did not call it. Asked afterwards what day it was he called it, said the sixteenth of August
2026 correctly, and still did not connect the two until he was walked into it.

Getting the year right would not have saved him. **`--since=2026-08-16` returns zero.** git reads
a bare date as that date *at the current hour*, so at 23:01 it means "since eleven tonight", and
the answer is a plausible small number for a day with 34 commits in it. A wrong date fails
loudly; a bare one fails quietly, which is worse. So the rule in the docstring is the general
one — **you are not told what day it is, so say when you mean in words the command works out for
itself** — and where a real date cannot be avoided it comes from `where_we_are`.

**What is deliberately not in that docstring.** It briefly listed the git spellings — `--since=
midnight`, `--since=yesterday`, `--since="1 week ago"` — and named `git rev-list --count HEAD` as
the way to count, because `git shortlog` and `git log | wc` print nothing at all when they were
not handed `HEAD` and nothing reads as none. All of it went. Stripped back to the general rule
and asked the same question three times, he reached for `--since=midnight` himself every time
and answered 34 every time: the menu was teaching him what he already knew, on every turn, in a
docstring the model reads whether or not anybody is asking about git. **A docstring is prompt
paid for on every turn, so a line in one has to fix something the model gets wrong without it.**

What that stripping does cost is the wider question. "This week" comes back right about half the
time, and when it is wrong it is not git knowledge that failed — he wrote `--since=last%20week`,
a percent-encoded space that git could not read, so the filter was dropped and every commit in
the repository was counted. The same slip in the other direction is `directory="$(current_project)"`,
which he writes on the first try nearly every time, is told there is no folder by that name, and
recovers from in one call. **Both are the model quoting badly, not the model not knowing git**,
and neither is worth a shape list in `guard.py` — that file has no list of shapes on purpose and
this is not the reason to start one.

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
through `ctypes`. The Homebrew `brightness` helper is a fallback and not the first choice: it is
built on `IODisplay` calls Apple silicon does not answer, so on a recent Mac it is both missing
and, once installed, wrong. The helper and then the brightness keys cover the Macs predating the
framework, and a level that can only be stepped is stepped rather than refused. **A control that
cannot do something says which, and how to fix it — but it tries everything it has first.**

Anything that loses unsaved work — sleep, restart, shut down — happens as soon as it is asked
for. The docstring tells Happy to say what is about to happen, which is the only warning there is.

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
- **Anything on the web that needs a login**, in the *browser*, works only after you have
  signed in once by hand in Happy's own profile. There are no browser credentials and there
  should not be any. Connections under `mcps/` are the separate, narrower case below.
- **A setup script.** Meant to be one-command setup — Ollama, the model pull, the ears' weights,
  a voice, Tesseract. There is none; see `TODO.md`.
- **Gmail, Calendar or Drive at any scale.** Happy talks to Google's own REST APIs from a
  server it writes, and the limit is not the code: Google will not register Happy as a client.

  **Happy ships no Google client, deliberately.** Embedding one would be allowed — a desktop
  client's secret is not a secret, and `gcloud` ships one too — and the unverified warning it
  produces is only a warning: Advanced, then continue. The ceiling is what kills it. An
  unverified app asking for Gmail or Drive scopes is capped at **a hundred people for the life
  of the project**, and the hundred and first is refused with nothing to click through.
  Lifting that cap means verification, and for Gmail and Drive — whose scopes are
  **restricted** — a third-party CASA security assessment repeated every year, for as long as
  the project exists. That is a permanent bill attached to a local assistant that runs on
  other people's machines, so it is not paid.

  A client per person has no ceiling and costs nobody anything, so that is the trade: the
  setup is the price. The boxes in the panel take a client ID and secret, the panel says what
  to go and make, and it says the two things people get wrong — publish the project rather
  than leaving it in testing, or Google discards the refresh token every seven days; and the
  unverified warning is about *your* app, not about Happy. Calendar's scopes are only
  *sensitive* rather than restricted, so if a shipped client is ever revisited, Calendar alone
  is the one that needs verification without CASA. One consequence of the merge: mail,
  calendar and drive share a consent, so the one client asks for all three scopes at once and
  a project with only some of those APIs switched on fails at the consent screen rather than
  at the first call.

Credential handling is confined to `mcps/`. It holds OAuth refresh tokens and pasted API tokens
for services somebody explicitly connected, in `data/happy.db`, unencrypted, and nowhere else —
the panel says so. *The system keychain was tried and taken back out; do not reach for it again.*
Writes failed silently for a process nobody was sitting in front of, macOS allowed two items
under one name, and a read and a write could land on different copies, so a connection's state
disagreed with itself. One store Happy can see beats a safer one it cannot; guard the database
instead. It holds no passwords and no cookies.

**Connecting and disconnecting are a person's, and no tool of Happy's does either.** Both were
written — a tool that opened the consent screen, a tool that took a token read out loud — and
both were taken back out. A browser window opening in the middle of a spoken answer is not an
answer, a misheard word costs a token pulled out of the database and, for Google, another trip
to the Cloud console, and nothing waits on a yes to catch it. The panel already has the button
for both, one press, in the service's own row. So signing in and out stay where they were: the
panel, `python -m mcps connect` and `python -m mcps disconnect`.

What Happy has instead is words. `mcps/tools.py` ships one tool, `connections`, and it changes
nothing: it says how many services are connected and which, how many are not and which, and for
each one the single thing somebody presses — Connect, Sign out, scan the QR, or make a token at
the page that service wants and paste it into the box in its row. It writes those lines from the
same store and the same registry the panel draws itself from, so the sentence Happy says and the
row somebody is looking at can never disagree. Asked to connect or
disconnect something, Happy answers with where it is done rather than a bare no — a no on its
own only makes somebody ask how.

## Running it

```sh
ollama serve                 # separate terminal
ollama pull gpt-oss:20b      # the stock tag. nothing to build on top of it.
ollama pull qwen3-vl         # the eyes. only for look_at_screen, OCR needs nothing.

# reading text off pictures. NOT a python package, it is a program.
brew install tesseract                          # macOS
winget install UB-Mannheim.TesseractOCR         # Windows, and it does not add itself to PATH

# whatsapp only. neonize imports python-magic, which loads a system library.
# without it the bridge dies on its first import and whatsapp answers nothing.
brew install libmagic                           # macOS
pip install python-magic-bin                    # Windows, which carries the DLLs itself

# the ears. 631 MB, into models/parakeet.
.venv/bin/python -m ears --get
.venv/bin/python -m ears               # transcribe everything in recordings/, with timings

# the voice. 326 MB of model into models/kokoro, plus a style per voice.
.venv/bin/python -m voice --get       # english; --get hi for the hindi voices too
.venv/bin/python -m voice --voices    # which voices are installed
.venv/bin/python -m voice "say this"  # hear it without the rest of Happy

cd face/window && npm install         # once, for the window

.venv/bin/python main.py              # the real thing: an icon in the menu bar
.venv/bin/python main.py --open       # the same, with the panel already down
.venv/bin/python main.py --terminal   # no window: hold the key at a prompt

cd face/window && npm start           # the same window, from where the window lives
cd face/window && npm start -- --open

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

`python -m brain` is the one to use while developing. It skips the microphone and the ears
entirely and exercises the graph and the tools — everything except audio.

**Three permissions, all granted to whatever runs Happy, not to Happy.** The Microphone, which
hearing has always needed and now needs the whole time; Accessibility, which reading a window's
controls and moving the pointer both use; and Screen Recording, which capture needs. macOS
refuses the last two silently — you get a black picture, not an error, and an empty tree rather
than a refusal — so if Happy says he cannot see the screen, those are the ones to check. All
three live in System Settings, Privacy & Security, and all three need the app restarting after
they are given. Run the window and it is **Electron** that has to be given them, not Python.

`eyes.attention.allowed()` asks `AXIsProcessTrusted()` and the answer rides out in `ready`, so
the panel says so in as many words and offers the button. The asking itself is `systemPreferences
.isTrustedAccessibilityClient(true)` in the Electron main process, because that is the process
macOS holds responsible for the Python it started. What was built without the permission never
gets it, so the button turns into **Restart**.

A terminal that lives inside an Electron app — VS Code's — exports `ELECTRON_RUN_AS_NODE=1` to
everything it starts. Inherit it and Electron comes up as plain Node, where there is no window
and no `app`, only a confusing crash. `face/window/start.js` exists to strip it back off, which
is why `npm start` runs that rather than `electron .`. `main.py` strips the same variable for the
same reason before it spawns Electron.

**`main.py` is both ends of the same pair.** Run by hand it is only a launcher: it checks `argv`
before the heavy imports, spawns Electron and waits. Electron then finds the virtual environment
and starts `main.py --serve`, and *that* process is Happy. The argument check has to come first —
importing `brain`, `ears` and `mcps` opens an ONNX session, and the launcher would pay for it
once itself and again in the child it started. `--terminal` is the way past the launcher without
a window, and it is the only way left to reach `face/console.py`.

Pointing at a different model or a hosted one is the **Brain** group in the panel, or a row in
the `settings` table. Ollama, LM Studio, llama.cpp, vLLM and the hosted providers all speak the
same request shape, so a swap is a URL and possibly a key in `$LLM_API_KEY`.
