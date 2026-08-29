# TODO

Pending work, newest thinking at the top of each section. Tick a box when it is done and
delete the line when it stops being interesting.

## Next

- [ ] **Windows, at all.** The accessibility tree, the pointer and every act are written for
      both systems and **only macOS has ever run them**. Windows also needs `comtypes`, which
      is not in `requirements.txt` yet because it does not install on macOS.
- [ ] **Act through the tree, not the pointer.** `AXPress` and UI Automation's Invoke press a
      button without moving the mouse, which is faster and does not fight the person for the
      pointer. Worth measuring against the click before switching: a real click is what an
      application expects to receive.
- [ ] **The first click after switching app does nothing** — macOS gives it to activating the
      window. Happy reports this honestly rather than lying about it, which is the right
      behaviour but not the nicest one. Worth seeing whether the window can be activated
      first without stealing focus from the person.
- [ ] **A third search engine, from someone else's index.** `hands/web/engines.py` has two
      doors and both are DuckDuckGo's, so a bad day there is a bad day for both. Mojeek and
      the public SearXNG instances were tried and answer a script with a captcha or a 429.
      A search API is the other way out and costs a key; see HAPPY.md before reaching for it.
- [ ] **Pages that are only a script.** `read_page` fetches and parses, so a site that
      renders itself in the browser comes back as "it wants a real browser" and the model
      reads the next result instead. That is the honest answer and usually the right one.
      The day it is not, the fallback is the browser errand, not a second fetcher.
- [ ] **Nothing does a multi-step web errand.** `hands/browser/` came back as two tools —
      `bring_to_front` and `play_pause` — which is a page already open, not a job worked
      through in a browser. Filling a form, going through a checkout or reading down a list
      of results and following one is still nobody's. The unprompted plumbing the old agent
      needed is back and in use: `main.py` speaks off `show.unprompted()` and
      `memory.begin(unprompted=True)` sets the row.

## Reminders

`heart/` keeps the time and `hands/reminders/` is how it is asked. The clock is polled
every twenty seconds rather than slept on, because a timer set for three hours does not
survive the lid going down. `due` is an epoch; a recurrence is stored in wall clock so
eight in the morning stays eight in the morning the week the clocks go. `python -m heart`
checks forty two phrases against a fixed Wednesday lunchtime and is the only test in here.

A time is worked out one way and one way only: **the soonest future moment the words could
mean.** "At four" at one o'clock is four this afternoon; at five o'clock it is four
tomorrow morning; "on May 21" is midnight on the twenty first. Nothing is ever asked back
and nothing is ever left half set — the answer says the time in full and invites a
correction, and `change_reminder` is how the correction lands. That say-back is the whole
safety net, so it is not something to trim.

- [ ] **Only the parser is tested.** Firing, rolling and the catch-up were run by hand
      against a throwaway database and are right, but nothing checks them tomorrow. They
      want the same table treatment `python -m heart` gives the phrases.
- [ ] **Nothing understands "next Friday", "a quarter past" or "after lunch"** and it
      refuses them rather than guessing. `BEYOND` in `heart/words.py` is that list, and it
      is deliberately short — anything added to it should be a word that genuinely means
      different things to different people, not one nobody got round to parsing.
- [ ] **A reminder only goes off while Happy is running.** Nothing wakes the machine and
      nothing starts him at login. What was missed while he was off is accounted for in one
      breath when he comes back, and a repeating one just resumes — but neither is the same
      thing as it having happened. Launching at login is the real fix and it needs the
      packaged app that does not exist yet.
- [ ] **`my_reminders` never mentions the finished ones.** It answers with what is still to
      come, which is nearly always the question. "Did you remind me to take my tablets this
      morning" has no answer but the panel.
- [ ] **The routine a reminder runs cannot be changed.** `change_reminder` moves the time
      and rewords the text; swapping which routine it runs means forgetting it and setting
      it again. The name is at least checked when it is set rather than at seven in the
      morning.
- [ ] **Clearing the finished ones is a button and not a sentence.** Deliberate — it is
      tidying, and tidying is what a panel is for — but "get rid of the old reminders" is a
      thing somebody will say out loud eventually.

## Controls that are not built yet

- [ ] **Bluetooth** — macOS needs `blueutil` from Homebrew, Windows needs the radio APIs.
      Left out rather than shipped as a tool that says "not supported" on most machines.
- [ ] **Do not disturb / Focus** — no honest way to set it on modern macOS without a
      Shortcut the user has made themselves.
- [ ] **Audio output device** — switching speakers to headphones needs a helper on both
      systems.
- [ ] **Exact brightness on macOS** — needs `brew install brightness`. Stepping up and down
      works without it. Say so when asked rather than failing quietly.
- [ ] **Wi-Fi on Windows** — switching the adapter needs administrator rights and reports
      that plainly. Joining a named network is not built.

## Known rough edges

- [ ] **Where a routine begins is worked out by following its arguments, and that is a
      guess with a bias.** An argument a tool was handed that came out of an earlier tool's
      answer pulls that turn in, and the parts of a value are looked for as well as the whole
      of it, because a path is often a folder from one answer and a filename from another. A
      part matching by coincidence drags in a turn that was not wanted and the routine does a
      little more than it had to; missing one leaves it unable to run at all. It leans the
      second way on purpose. Six turns is the ceiling and nothing walks past it.
- [ ] **A routine can be renamed and forgotten, and nothing else.** There is no saying "add a
      step to that one" or "drop the calendar bit" — the only way to change what a routine
      does is to run the job again and save over it with `replace`. Editing by voice is the
      obvious next thing and it is not built. The panel shows a routine and will delete it;
      it does not let anything be typed into one either, so there is no way round it.
- [ ] **Only the plainly named form is guaranteed to run.** "Run my morning brief", "do the
      morning brief", or the name on its own go straight to the routine before the model is
      asked anything, and that is what makes it reliable. Everything vaguer than that —
      asking for the job in other words and hoping the description matches — is left to the
      model off the listing in the standing prompt, and it often does the job itself instead.
      Measured: with a fresh conversation and a routine called *where check*, "run the where
      check" got the routine every time through the plain path and never once through the
      model's own choosing. The listing is worth keeping for the near misses, but it is not
      the thing to lean on.
- [ ] **A routine still cannot call another routine.** Playbooks have `${PLAYBOOK: name}` for this
      and it is the natural way to build a long one out of short ones. Nothing here does it.
- [ ] **A routine only starts itself on a clock.** `heart/` keeps time and `remind_me` with a
      `routine` name set makes one go off — at eight every morning, every weekday at nine. The
      other triggers are still missing: on waking, when the headphones connect. Those are a
      second kind of trigger into the same firing path, not a second feature.
- [ ] **The standing prompt grew by about two thousand characters** for the ROUTINES section,
      and by a line for every routine saved. `routines.listing()` writes one line per routine
      and caps nothing, so a person with fifty routines pays for fifty lines on every single
      turn. Twenty is fine; there should be a ceiling before it is not.
- [ ] **`brain/thinking.py` is 333 lines** and `brain/wrapping.py` 359, both well past the
      200 the rule in `AGENTS.md` asks for. They want splitting. `eyes/attention.py` at 380,
      `main.py` at 377, `voice/speaker.py` at 364 and `mcps/bridging.py` at 349 are the same
      story; `mcps/servers/whatsapp/bridge.py` at 2653 is somebody else's code and is not.

- [ ] **`list_controls` hides things behind "and 17 more".** `MAX_PER_KIND` is 12 and
      `MAX_CHARS` 1400, and the chat being asked for was cut by both, so the model chose from
      a list the answer was not in. Cutting is right, cutting silently is not: it should say
      what kind of thing it dropped, or drop the least useful rather than the last.
- [ ] **Nothing says which conversation is open.** The tree holds a group called *Messages in
      chat with Priya* and the heading never mentions it, so the model clicks to open a chat
      that is already open. The heading has room for the context, not just the app name.
- [ ] **OCR reads the whole screen, not the front window.** `eyes.spot` searches the entire
      screenshot, so a word in a window sitting behind can be found and clicked. The tree is
      asked first and is correctly scoped, so this only bites when the tree has no answer.
      Tightening the spelling cutoff has taken the sting out of it, not the cause.
- [ ] **A target that is only part of a two word label scores badly.** "Send" against a button
      labelled *Send message* comes to exactly 0.5 and so does not clear the cutoff, because
      coverage is counted in characters. Counting it in words would be the honest fix.
- [ ] **`brain.calls` is 40 rounds** — raised from 14 because an errand that clicks its way
      through an app spent them all and was cut off mid task, which reads as Happy giving up.
      The number is not the fix. Fewer round trips is, and a routine already gets a budget cut
      to its own steps rather than an errand's open ended one.
- [ ] `hands/controls/` is only tested on macOS. Every Windows path is written and unrun.
- [ ] The window is only run on macOS. The tray, the placing and the icons are written for
      Windows and unrun there. On macOS a menu bar with no room left hides the icon and then
      reports nonsense bounds for it, so the panel falls back to the top right corner.
- [ ] **Launching at login.** There is a clickable app now — `bones/bundling.py` writes a
      signed `Happy.app` into `/Applications` on a Mac, a shortcut on Windows, a `.desktop`
      entry on Linux — but every one of them points back at the checkout rather than carrying
      it, and nothing registers any of them to start when the machine does. That is what a
      reminder needs to go off while nobody has opened him.
- [ ] `data/happy.db` prunes only if `memory.messages` says how many days to keep. No export.
- [ ] `recordings/` the same, under `memory.recordings`. Both ship keeping everything.
- [ ] Almost no tests. `python -m heart` checks forty two time phrases and is the only one.
      `.github/workflows/checks.yml` byte-compiles every module on macOS and Windows and lists
      the files over 200 lines, which catches a file that does not parse and nothing else.
      The line check is advisory on purpose: nineteen files are already over it.
- [ ] `requirements.txt` is still a frozen dump, 13 KB of pins. `browser-use==0.13.6` and
      `browser-use-sdk==3.4.2` are the old browser agent's and nothing imports them; the
      Kokoro, Piper and Qwen halves went the same way the voices did and want the same check.
- [ ] Parakeet is no longer what ships — `ears.engine` defaults to `whisper` — but it is still
      an engine somebody can pick, and its own docs put the ceiling at 20-30 seconds a call and
      suggest VAD past that. A 14-second take is the longest tried and it was fine.
      `model.with_vad(load_vad("silero"))` is the fix if a long ramble comes back cut short.
- [ ] `ears.device = auto` lets onnxruntime pick CoreML. Never measured against the pinned CPU
      it ships with, and a 650 MB encoder is not an obvious win to compile.
- [ ] One take in `recordings/` that WhisperX heard — "It looks familiar." — came back empty
      off Parakeet. It is the quietest of the fifty at peak 0.08, and gain does not recover it.
      Worth running the fifty again now the default ear is Whisper, to see which of these
      are still true of what ships.

## Done

- [x] **The voice, three times over.** Piper went, Kokoro measured robotic and is now the
      second choice, and Supertonic is what ships — pure ONNX, faster and more expressive,
      four diffusion steps, and never two. Qwen
      was tried and dropped: fast only on MLX or CUDA, about ten times slower on Windows than
      the voice it would have replaced. A number is now read as the words it is said as, an em
      dash is a pause rather than a character off an ASCII table, and a sentence too long for
      one read breaks where a clause ends rather than at the last space.
- [x] **One line installs him.** `install.sh` clones into `~/.happy` and hands over to
      `setup.sh`, which finds a Python and hands over to `bones/` — Node, Tesseract, the model
      server, the dependencies, the window, the weights and a voice, each one skipped if it is
      already there and named at the end if it could not be done. The last step is a signed
      `Happy.app` in `/Applications` pointing back at the checkout, so updating is a git pull.
- [x] **Reminders.** `heart/` keeps the time, a phrase comes to the soonest future moment it
      could mean, and a reminder can run a saved routine rather than say a line back. Every one
      has a row in the panel that folds open, and the panel is told the moment one is set,
      moved, fired or forgotten.
- [x] **Routines.** A job taught once and asked for by name, taken off a run that already
      worked rather than written out of imagination, run in a context with only the tools it
      named bound to it. Asking for one by name runs it before the model is asked anything.
- [x] **Something Happy says that nobody asked for** takes the same lock a turn does, so a
      reminder waits its go rather than talking over one, and it opens a turn without putting
      the window into hearing. The `unprompted` row the schema has had since the browser agent
      went is finally set by something.
- [x] **The repository is readable by a stranger** — README, CONTRIBUTING, SECURITY, a code of
      conduct, a licence and issue templates, because somebody who finds it cannot ask.
- [x] **Every request for approval crashed in the window.** `panel.send` took its line kind as
      `what`, and the confirm line carries a field of its own called `what`, so asking about
      anything guarded raised `got multiple values for argument 'what'` instead of asking.
      Sending, deleting, buying, installing, quitting and shutting down were all unreachable
      through the window from the day it was built. The console path never had it.
- [x] **Two things with one name.** WhatsApp calls both the chat in the list and the forty
      pixel chip above the conversation "Priya", they scored the same, and the tie went to
      whichever was a button — the chip, which leaves the chat for the contact's settings.
      A tie is now read as one thing described twice only when the boxes overlap. Apart, it
      is two things, the bigger one is the row being pointed at, and the other is named out
      loud instead of being silently passed over.
- [x] **A click that only moved the caret was called a failure.** WhatsApp's search is a
      button, not a field, so clicking it while it already held the keyboard changed no pixels
      and reported "nothing changed". The typing that should have followed never happened.
      The keyboard landing in the thing pressed now counts as a yes on its own.
- [x] **`attach_file` no longer clicks a box that already has the caret**, which is the usual
      state of a chat that has just opened.
- [x] **Sending a file to a person.** `attach_file` puts the file itself on the clipboard and
      pastes it where the cursor is, which is what a paperclip does anyway. Hunting for the
      paperclip was six clicks that each might land somewhere else, and once did.
- [x] **A fuzzy match has to be a misheard word, not a different one.** "Attachment" spells
      sixty per cent like "ENTERTAINMENT", cleared the click cutoff, and pressed a video in
      the window behind. Spelling alone now has to be nearly right.
- [x] **Telling a person something means sending it.** Happy read a message out loud instead
      of sending it, and did not ask which app. Both are in the standing prompt now.
- [x] **Built the window** — `face/window/`, an Electron app that owns the process and runs
      Happy as a child over one JSON line at a time. An icon in the menu bar, a panel that
      drops out of it, an orb that moves with the real microphone level and the real clip
      being played, the conversation, a box to type in, and every control.
- [x] **Took the settings out of the code.** `memory/catalogue.py` is the only place a default
      lives now, and `memory/settings.py` the only place a value does. Every part that was
      built out of one rebuilds itself when its group changes, mid conversation, without a
      restart.
- [x] **Rebuilt the desktop agent** as a state estimation problem rather than a vision one.
      The application is asked what it drew before anything is photographed, the belief about
      the screen lives in one place, and every act says what should become true and then checks
      whether it did. `list_controls`, `click_on`, `type_text`, `press_keys`, `scroll`.
- [x] Added the accessibility tree — `AXUIElement` and UI Automation — as the first way of
      seeing. It was the oldest thing on this list.
- [x] Renamed every module after the part of a person that does the job.
- [x] Split every file to under 200 lines.
- [x] Stripped the comments back and wrote the rule down in `AGENTS.md`.
- [x] Added the system controls: sound, brightness, media, display and dark mode, power and
      battery, Wi-Fi, clipboard.
