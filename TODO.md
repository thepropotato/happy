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
- [ ] **Rebuild the browser agent** — `hands/browser/` is blank. It owned the multi-step web
      errand in its own process. Two things went with it and need putting back if the new one
      works the same way:
      - `main.py` no longer wires up unprompted speech. `face.console.unprompted()` is still
        there, unused, waiting for it.
      - `conversation.add(unprompted=True)` is still in the schema and nothing sets it.
- [ ] **Setup script** — there is no one-time installer any more. It should get Ollama and
      the models, WhisperX, a Piper voice, Tesseract, and say what it could not do.

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

- [ ] `hands/controls/` is only tested on macOS. Every Windows path is written and unrun.
- [ ] The window is only run on macOS. The tray, the placing and the icons are written for
      Windows and unrun there. On macOS a menu bar with no room left hides the icon and then
      reports nonsense bounds for it, so the panel falls back to the top right corner.
- [ ] There is no packaged app yet — no `electron-builder`, no `.app`, no `.exe`. It is
      `npm start` from the repo, so it cannot be launched at login the way it should be.
- [ ] `data/happy.db` prunes only if `memory.messages` says how many days to keep. No export.
- [ ] `recordings/` the same, under `memory.recordings`. Both ship keeping everything.
- [ ] No tests anywhere.
- [ ] `av` (WhisperX) and `cv2` (eyes) both ship a copy of `libavdevice`, so importing both
      prints an objc duplicate-class warning at startup. Harmless so far, and it says it may
      cause "mysterious crashes". Predates the rename.
- [ ] `requirements.txt` is a frozen dump, including packages only the old browser agent
      needed. Worth splitting into what Happy needs and what an errand needs.

## Done

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
