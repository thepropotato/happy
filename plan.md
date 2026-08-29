# What went wrong on 2026-08-28, and what to do about it

Findings from messages 663-681 in `data/happy.db`, plus a read of the code behind each.
Temporary file. Delete when the fixes are in.

---

## The seven complaints, and what actually caused each

### 1. Reading yesterday back
19 turns, 21:52-21:59. Six of the seven complaints are visible in that trace.
Nothing else was wrong in it. Turn 674 also ended on **no reply at all** (`reply` is
NULL) after three tool calls, which breaks "every turn ends on an answer" — an
eighth problem the user did not name but which is in the same run.

### 2. "unread" heard as "hundred"  ->  transcribed "100"
Turn 673: "Do I have any unread messages on WhatsApp or email?" arrived as
"Do I have any **100** messages on WhatsApp or email?"

Not a normalizer. There is **no number normalization anywhere in the repo** —
`ears/nonsense.py` only ever discards a take, never rewrites one. Whisper writes
numerals as digits natively, so "100" came straight out of the decoder. This is a
single acoustic confusion, /ʌnˈrɛd/ -> /əˈhʌndrəd/, that nothing downstream could
catch. Three compounding reasons it was not caught:

- **Model is too small and quantized.** `ears/languages.py:40` — `whisper-small`,
  int8, on CPU. 244M params, degraded further by quantization.
- **Greedy decoding, no beam.** `onnx_asr` hardcodes `argmax` with no beam, no
  temperature fallback, no alternative hypothesis to fall back on. There is no
  second-best candidate for "unread" to win on.
- **No vocabulary biasing.** `onnx_asr.recognize()` accepts only `language=`;
  `initial_prompt`/`hotwords` are swallowed by `**kwargs` and silently ignored.
  "unread" and "WhatsApp" are high-prior words in this project and the ear has
  never been told they exist.

`ears.language` is `auto`, which adds a detection pass and a re-decode ladder, but
English was detected correctly here so that is a latency and robustness issue,
not the cause of this bug.

### 3. Asking for messages returned a count
Downstream of #2, not a separate bug. The WhatsApp tool docstrings are correct and
route unread -> `get_unread_messages` properly
(`mcps/servers/whatsapp/mcp_server.py:163`, `:243-247`). The model did the right
thing with the wrong words: told "100 messages", it fetched 100 messages
(turn 674, three calls, limits 100/101/100). Fix #2 and this goes with it.

Turn 676 ("what are the ?" — also a mis-transcription) then called the same tool
with identical arguments twice in one turn. Worth a look on its own.

### 4. Keyboard backlight turned the display brightness off  <- the worst one
Turns 678 and 679. Asked to turn the **keyboard** backlight off, Happy called
`brightness_control(action="set", level=0)` and blacked the screen. Told plainly
"I said keyboard not display brightness", it called the **exact same tool with the
exact same arguments again**, and both times reported "Keyboard backlight's off now."

Root cause, in order:
- **There is no keyboard-backlight capability at all.** `hands/controls/backlight.py`
  is named `backlight` but is the *screen*: it talks to `DisplayServices` via
  `DisplayServicesSetBrightness`. The name is a trap — for a model choosing a tool,
  "backlight" is the obvious match for a backlight request.
- **Nothing refuses.** No tool covers the keyboard, so the nearest neighbour won.
- **The prompt pushes hard against saying no.** `prompt.md:23` and `:109` press
  "never answer with a bare no" / "say you cannot only when there is no app and
  nothing on the web either". With no correct tool, that pressure routes straight
  into the wrong one.
- **The tool lied about what it did.** `display.set_level` returns
  "Brightness set to 0 percent", and the reply became "Keyboard backlight's off".
  A tool that cannot do a thing must say so; this one confirmed a thing it had
  not done.

The hardware is capable: this is a `Mac16,8` (M4 Pro) MacBook Pro, and
`KeyboardBrightnessClient` in `CoreBrightness.framework` resolves through the
ObjC runtime. Verified present on this machine.

### 5. Voice sounds robotic
The setting is `voice.name = "bm_fable"`. In `voice/styles.py:28-32` the voice list
is ordered best-first, and `bm_fable` is **11th of 12**. The comment directly above
it says every male voice in this model is "C or below and sounds it". The worst
available voice is the one selected. That is most of this complaint.

Secondary, real but smaller:
- `clips.py:15` appends a fixed **90 ms** of silence to every sentence, explicitly
  replacing the model's own syntax-varying pause. Uniform gaps read as machine-like.
- `clips.py:30-46` trims near-silence at a 2% floor off both ends of every clip,
  flattening natural breath.
- `voice.pace` compresses speech slightly (Kokoro inverts it: 0.95 -> speed 1.05).
- On the Piper path only, `piper.py:45` builds `SynthesisConfig(length_scale=...)`
  and so **discards each voice's tuned `noise_scale`/`noise_w`** from its own JSON.
  Telugu only today, but wrong wherever it runs.

### 6. TTS takes too long
The architecture is good and should not be regressed: LLM tokens stream into a
sentence splitter with a 4-char first-sentence fast path (`sentences.py:10`), the
output stream is held open between clips, barge-in lands within 60 ms. Real costs,
largest first:

- **Kokoro synthesises a whole sentence before a single sample plays.**
  `phonemes.py:56-71` only splits above 500 phonemes; its own docstring records
  that the sub-sentence fast path was removed on purpose and cost "half a second".
- **fp32 325 MB model, CPU only.** `kokoro.py:118-120` passes
  `CPUExecutionProvider` and nothing else, on an Apple-silicon Mac.
- **An FFT resample of every chunk on the critical path.** `clips.py:65-83` does a
  full `rfft`/`irfft` round trip, 24000 -> device rate, before playback; arbitrary
  sentence lengths can land on slow FFT sizes.
- **`sd.query_devices` once per sentence** (`speaker.py:196`).
- **A directory `glob` per sentence** in `styles.voices()`, via an unconditional
  `refit()` on every stream.

Also worth noting: `voice.engine` is not in the settings catalogue, so
`settings.put` refuses it and `chosen()` can only ever return kokoro. All the
`refit()` engine-switch machinery is unreachable.

### 7. "Show me the family tree" answered with a link the user could not see
Turn 671: asked to *show* it, Happy called `search_web`, then said "check out the
interactive chart on the first link" — narrating a result list that exists only in
its own context. The user had to say "No show it to me" (672) before `open_url`
fired.

Cause is docstring emphasis. `hands/web/tools.py:15-31` spends its whole body
pushing toward `read_page` — "the answer is almost always inside one of the
results", "pick the likeliest result and read it" — and mentions `open_url` in a
single trailing line. `prompt.md:31` likewise leads with reading. Nothing anywhere
says that a request phrased **"show me X"** must end in `open_url(because="show")`.
And nothing forbids referring out loud to "the first link", which is the specific
thing that made the answer useless: the user cannot see the list.

---

## Progress

- [x] **#4 keyboard backlight** — `hands/controls/keyboard.py` on
      `KeyboardBrightnessClient`, verified on this Mac: read, set, step, refuse,
      screen untouched. `backlight.py` renamed `screen.py`. Both docstrings now
      point at each other so the two cannot be confused.
- [x] **#7 show, do not narrate** — `search_web` docstring and `prompt.md:31`
      now require `open_url(because="show")` on a show request, and forbid
      naming a link the person cannot see.
- [x] **#2 the ear** — `whisper-medium` for transcription, `whisper-small` kept
      for the three-token language guess. The real clip
      `recordings/2026-08-28_21-55-28-806.wav` now reads "unread", not "100".
      Cost: 0.5s -> 1.45s a take.
- [~] **#5 voice** — Piper now keeps each voice's own tuned `noise_scale` and
      `noise_w_scale` (`piper.py`), which were being thrown away for the
      library's flat defaults. The main cause is the *setting*:
      `voice.name = "bm_fable"` is 11th of 12 in a list the code itself orders
      best-first. Samples of six voices are rendered for a listen — the pick is
      the user's, not mine.
- [x] **#6 measured, and mostly a myth.** Numbers on this machine, not guesses:
      - `sd.query_devices` per sentence: **0.0 ms**. Not worth touching.
      - `styles.voices()` glob per sentence: **0.06 ms**. Not worth touching.
      - FFT resample 24k->48k: **12 ms** typical, 21 ms on an awkward prime
        length, 1 ms on a friendly one. Real but small.
      - Kokoro synthesis: **~400 ms** for a 3.6 s sentence, **9x realtime**.
      - **CoreML is slower, not faster: 432 ms against 408 ms**, warm-up 3.7 s
        against 1.2 s, and it splinters the graph into 109 partitions and prints
        warnings. Tried, measured, reverted. Do not try it again without
        measuring.
      So time-to-first-audio is ~400 ms and it is nearly all one Kokoro forward
      pass over a whole sentence. The only real lever left is sub-sentence
      chunking, which `phonemes.mouthfuls` gave up on purpose: it saved half a
      second and put a pause in the middle of a clause. That trades straight
      against #5, so it stays as it is.
- [x] **#674 silent turn** — `say_streaming` is a generator, and its last-word
      fallback could only run where it could also `yield`. When the consumer let
      go part way through, `GeneratorExit` skipped straight past it to the
      `finally`, which wrote `reply` empty and stored NULL. The reply is now
      settled inside the `finally` as well, so the row is right even when the
      words cannot be delivered.
- [x] **#676 duplicate call** — nothing in the prompt forbade re-calling one tool
      with identical arguments in a single turn. `prompt.md:45` now says the same
      call gives the same answer and to use the one already in front of you.
- [x] **Telling the truth about what was done** — the deeper half of #4. A new
      paragraph at `prompt.md:45` forbids naming the thing asked for while
      describing something else done instead, and makes "I cannot do that one"
      the right answer where no tool covers it.

### Watch out for
The bigger ear is *worse* at naming the language: medium called plain English
`hi`, `ml` and `th` on 3 of 15 real takes, and turbo cannot do it at all (its
vocabulary answers `transcribe`). That is why detection stayed on small. Do not
"simplify" the two models back into one.

## Fixes, in order

Ordered by damage done, not by effort.

1. **Keyboard backlight (#4).** Add a real control on `KeyboardBrightnessClient`
   via the ObjC runtime, Windows beside it per AGENTS.md. Rename
   `controls/backlight.py` -> `controls/screen.py` so nothing shadows it again.
   Make the miss impossible: `brightness_control`'s docstring must say it is the
   screen and not the keyboard. Verify on this Mac before calling it done.
2. **Say no when it cannot (#4, general).** A tool asked for something it does not
   do must return a plain refusal, and Happy must repeat it rather than confirm a
   thing that did not happen. Reconcile with the "never a bare no" line in
   `prompt.md` — a no with nowhere to send them is still the right answer when the
   machine genuinely cannot.
3. **The ear (#2, and #3 with it).** Move `DEFAULT` in `ears/languages.py` off
   int8 `whisper-small`. `onnx-community/whisper-large-v3-turbo` and
   `whisper-medium-ONNX` both exist with the exact filenames `PARTS` expects
   (checked). Turbo is the one to try first: large-v3 accuracy near small-model
   speed. Set `ears.language = "en"` to skip the detection pass. Measure "unread"
   on a real take before and after.
4. **Show, do not narrate (#7).** Rewrite the `search_web` docstring so a "show me"
   request ends in `open_url(because="show")`, and forbid naming "the first link"
   or any result the person cannot see.
5. **Voice (#5).** Change `voice.name` off `bm_fable` — try `af_heart` and
   `bf_emma`, the two graded A. Then make the 90 ms tail vary with the sentence's
   own punctuation instead of being constant. Fix the Piper `SynthesisConfig` to
   carry `noise_scale`/`noise_w`.
6. **TTS latency (#6).** Cheap and safe first: hoist the per-sentence
   `query_devices` and the per-sentence `glob`. Then try `CoreMLExecutionProvider`
   with a CPU fallback. Only then reconsider sub-sentence chunking — that one was
   removed deliberately and trades against #5, so it goes last and only if the
   first three are not enough.
7. **Never end a turn silent (674).** Find why `ending()` did not catch it and the
   row stored NULL.
8. **Duplicate tool call (676).** Same tool, same arguments, twice in one turn.

## Rules to keep in view while fixing

- Every control needs its Windows half beside the macOS one (AGENTS.md).
- Comments uppercase, one line, only where they say *why*.
- No file over 200 lines; a module is a folder with `__init__.py`.
- Tools return short plain text — it may be spoken.
- Never hand the model a fact to save a round trip. A slower answer that looked is
  the one we want.
