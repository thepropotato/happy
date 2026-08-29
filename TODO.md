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
- [ ] **Rebuild the browser agent** — `hands/browser/` is blank. It owned the multi-step web
      errand in its own process. Two things went with it and need putting back if the new one
      works the same way:
      - `main.py` no longer wires up unprompted speech. `face.console.unprompted()` is still
        there, unused, waiting for it.
      - `conversation.add(unprompted=True)` is still in the schema and nothing sets it.
- [ ] **Setup script** — there is no one-time installer any more. It should get Ollama and
      the models, the ears' weights, a voice, Tesseract, and say what it could not do.

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
- [x] **A routine never starts itself.** Half of this is done: `heart/` keeps time, and
      `remind_me` with a `routine` name set makes one go off on a clock — at eight every
      morning, every weekday at nine. The other triggers are still missing: on waking, when
      the headphones connect. Those are a second kind of trigger into the same firing path,
      not a second feature.
- [ ] **The standing prompt grew by about two thousand characters** for the ROUTINES section,
      and by a line for every routine saved. `brain/prompt.py` caps nothing, so a person with
      fifty routines pays for fifty lines on every single turn. Twenty is fine; there should
      be a ceiling before it is not.
- [ ] **`brain/thinking.py` is 326 lines** and was already 295 before the two short methods
      that dispatch a routine went in. It wants splitting either way.

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
- [ ] **`brain.calls` is 14 rounds**, and an errand that clicks its way through an app can
      spend them all and be cut off mid task, which reads as Happy giving up. Fewer round
      trips is the better answer than a bigger number.
- [ ] `hands/controls/` is only tested on macOS. Every Windows path is written and unrun.
- [ ] The window is only run on macOS. The tray, the placing and the icons are written for
      Windows and unrun there. On macOS a menu bar with no room left hides the icon and then
      reports nonsense bounds for it, so the panel falls back to the top right corner.
- [ ] There is no packaged app yet — no `electron-builder`, no `.app`, no `.exe`. It is
      `npm start` from the repo, so it cannot be launched at login the way it should be.
- [ ] `data/happy.db` prunes only if `memory.messages` says how many days to keep. No export.
- [ ] `recordings/` the same, under `memory.recordings`. Both ship keeping everything.
- [ ] No tests anywhere.
- [ ] `requirements.txt` is still a frozen dump. The WhisperX half is gone, but the packages
      only the old browser agent needed are still in it — `browser-use` and friends are pinned
      and nothing imports them.
- [ ] Parakeet's own docs put the ceiling at 20-30 seconds a call and suggest VAD past that.
      A 14-second take is the longest tried and it was fine. `model.with_vad(load_vad("silero"))`
      is the fix if a long ramble ever comes back cut short.
- [ ] `ears.device = auto` lets onnxruntime pick CoreML. Never measured against the pinned CPU
      it ships with, and a 650 MB encoder is not an obvious win to compile.
- [ ] One take in `recordings/` that WhisperX heard — "It looks familiar." — comes back empty
      now. It is the quietest of the fifty at peak 0.08, and gain does not recover it.

## Done

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
