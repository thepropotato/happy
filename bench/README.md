# Benchmarks

Two standard benchmarks, adapted to Happy. Both are safe to run on a real machine, because
no tool ever executes.

- **Replay** (`replay.py`, `suites/`) — a real evening from the log, played back on one
  continuous thread with every tool mocked and the real tool results handed back as canned
  replies. Each turn says which tools should have been reached for, which are forbidden, and
  what the answer must and must not say; a turn marked `restart` closes and reopens Happy
  first, so it checks what survives a restart. `suites/2026-09-04.json` is the first one,
  lifted from `messages` rows 1 to 26. The rule from here: a change to prompt.md, persona.md
  or a docstring ships with the turn it fixes, and runs the whole suite.
- **ToolCall-15** (`toolcall15.py`) — fifteen spoken instructions in five categories, scored
  pass / partial / fail on which tool Happy reached for. Modelled on the ToolCall-15 in
  OpenJarvis's suite, rewritten against Happy's own tools.
- **Regression** (`regress.py`) — the phrases that drove the move to whisper-medium, plus the
  real command vocabulary, spoken by every English voice macOS ships. This is the one that
  decides the engine; VoiceBench measures general speech and disagrees with it.
- **VoiceBench** (`run_voicebench.py`) — the real `hlt-lab/voicebench` dataset (Apache 2.0),
  spoken instructions through Happy's own ears. Reports word error rate and a realtime factor
  per accent split, Indian English included.

OSWorld is deliberately absent. It needs a real virtual machine and it is Ubuntu-first, while
Happy is macOS and Windows only.

## Why this is safe to run

`sandbox.py` is the whole safety story, and it is worth understanding before trusting it.

1. **Every tool becomes a stub.** `harness()` walks `hands.tools()` and wraps each one in a
   `StructuredTool` that keeps the name, description and argument schema — so the model sees an
   identical toolset and picks exactly as it would in real life — but whose body only appends to
   a list. `run_command`, `power_control`, `move_to_trash`, `click_on` and `type_text` are inert.
2. **The database is redirected.** `throwaway()` sets `HAPPY_DB` before any Happy module is
   imported, so `memory/storage.py` opens a scratch file in `bench/runs/` instead of `data/`.
   Without this a run puts a hundred fake turns into the real history and the panel.
3. **It refuses to start if either fails.** `assert_no_real_tools()` raises unless every tool in
   the list is one of its own stubs.

Verified rather than assumed: calling the mocked `run_command` with `rm -rf ~/Desktop`, and
`power_control` with `shut down`, does nothing at all.

## Running them

    python3 bench/replay.py bench/suites/2026-09-04.json          # the whole evening, ten minutes
    python3 bench/replay.py bench/suites/2026-09-04.json 21 26    # just those rows
    python3 bench/replay.py bench/suites/2026-09-04.json --effort medium   # any brain knob

    python3 bench/run_toolcall15.py               # all fifteen, about two minutes
    python3 bench/run_toolcall15.py S2 L2         # just the named scenarios

    export HF_HOME=~/.cache/huggingface           # anywhere with a few GB spare
    python3 bench/run_voicebench.py 40 whisper    # forty clips per split, per engine
    python3 bench/run_voicebench.py 40 parakeet
    python3 bench/run_voicebench.py 20 whisper --brain   # also answer each one

The first VoiceBench run downloads the dataset. `datasets` 5.x wants FFmpeg to decode audio and
this machine has none, so the runner reads the parquet bytes and decodes with soundfile instead;
do not "fix" that by reaching for `Audio(decode=True)`.

Needs `pip install datasets`, and Ollama up with whatever `brain.model` is set to.

## Reading a report

Reports land in `bench/runs/` as JSON and stay there: results, throwaway databases and clips
are not committed. Compare runs on the machine that made them.

A ToolCall-15 scenario lists `expect` (any one of these tools is right), optional `then` (a
second call that must follow, or it scores partial), and `forbid` (`"*"` means the right answer
was to say something and call nothing).

## Where it stood on 2026-08-31

ToolCall-15: 12 pass, 1 partial, 2 fail — 83%. Both failures were prompt discipline, not
plumbing: Happy said it could not skip a track when `media_control` maps `next` on macOS, and
went straight to `open_url` for "open youtube" without the `already_open` check its own
docstring asks for first.

VoiceBench, 40 clips per split, word error rate (lower is better):

| split                 | parakeet | whisper |
|-----------------------|----------|---------|
| commoneval            | 0.031    | 0.070   |
| sd-qa Indian English  | 0.064    | 0.072   |
| sd-qa US              | 0.063    | 0.055   |
| sd-qa British         | 0.043    | 0.075   |
| realtime factor       | 0.02     | 0.25    |

Parakeet is better on three of four splits and about ten times faster. Whisper is the one
configured in `ears.engine`, so this is worth acting on — but note whisper here is
whisper-medium, the bigger ear that transcribes well and misnames the language, and neither
engine was asked to detect language in this run.

## Which ear, and why not the faster one

VoiceBench says parakeet: better word error rate on three of four splits and about ten times
faster. `regress.py` says whisper, and regress is the one that counts, because it asks in the
words this house actually uses.

Over 200 clips and eight voices, substantive misses: whisper 36, parakeet 44. The whole gap is
one family of words — "unread", 20 misses out of 22 against whisper's 14 — and it is the
regression `ears/languages.py` already documents: parakeet hears "how many unread emails" as
"how many hundred emails", and "is that one unread" as "is that 100". Parakeet also loses the
letters in "how many r's are in strawberry" on three voices of eight, which quietly breaks
count_letters. On the three Indian English voices it is whisper 10 misses to parakeet 15.

Parakeet is genuinely better at general speech and wins five of the eighteen disagreements
(GitHub, receipt). It is worse at the twenty words that get said every day, so whisper stays,
and the 0.25 realtime factor is a speed problem to solve on whisper's own terms.
