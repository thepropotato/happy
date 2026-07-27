# TODO

Pending work, newest thinking at the top of each section. Tick a box when it is done and
delete the line when it stops being interesting.

## Next

- [ ] **Rebuild the desktop agent** — `hands/desktop/` is blank. It owned clicking, typing,
      pressing keys and scrolling, driven by `eyes.where()` which is still there and still
      works. Nothing else depends on it, so it can come back in any shape.
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
- [ ] `data/happy.db` grows forever. No pruning, no export.
- [ ] `recordings/` grows forever too. Nothing ever deletes a WAV.
- [ ] No tests anywhere.
- [ ] `av` (WhisperX) and `cv2` (eyes) both ship a copy of `libavdevice`, so importing both
      prints an objc duplicate-class warning at startup. Harmless so far, and it says it may
      cause "mysterious crashes". Predates the rename.
- [ ] `requirements.txt` is a frozen dump, including packages only the old browser agent
      needed. Worth splitting into what Happy needs and what an errand needs.

## Done

- [x] Renamed every module after the part of a person that does the job.
- [x] Split every file to under 200 lines.
- [x] Stripped the comments back and wrote the rule down in `AGENTS.md`.
- [x] Added the system controls: sound, brightness, media, display and dark mode, power and
      battery, Wi-Fi, clipboard.
