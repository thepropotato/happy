# Benchmarks

Four layers, cheapest first. All of them are safe to run on a real machine, because no tool
ever executes.

The layers exist because one test cannot answer two questions. `shape.py` asks whether the
prompt and the tools are structurally what they were, and answers in a second, the same way
every time. `choosing.py` asks whether one sentence reaches for the right tool. `replay.py`
asks what survives across turns and across a restart, which is the only thing it can do that
the others cannot, and it is also the slowest and the narrowest. Reach for the cheap one on
every change and the dear one before a release.

- **Shape** (`shape.py`, `golden/`) — no model at all. Every tool describes itself, no two
  tools open alike, no name is registered twice, every tool asks for its `why`, the prompt
  carries no XML, and neither the prompt nor the toolset has moved from the blessed copy in
  `golden/`. That last one is the guard on the prefix cache: a prompt change is often right,
  but not knowing one happened is how a docstring edit flips a routing nobody was looking at.
  Run `--bless` to accept what is there now as what ought to be there.
- **Choosing** (`choosing.py`) — forty-five single utterances, one turn each, on a thread of
  their own. Six groups: the plain calls, the ones that must go and look, the `already_open`
  discipline, the boundaries between two tools that are easy to confuse, the sequences, and
  the ones whose right answer is to say something and call nothing. These carry nothing about
  anybody — no project, no channel, no handle, no path — so they can be read by anyone. Every
  boundary case names its neighbour as forbidden, because the failure is never "called
  nothing", it is "called the neighbour".
- **Replay** (`replay.py`, `suites/`) — a real evening from the log, played back on one
  continuous thread with every tool mocked and the real tool results handed back as canned
  replies. Each turn says which tools should have been reached for, which are forbidden, and
  what the answer must and must not say; a turn marked `restart` closes and reopens Happy
  first, so it checks what survives a restart. Each suite is named for what it exercises
  rather than the day it was recorded, because the name is how you know whether the bug you
  are fixing is covered; the evening it came off is inside the file, as its `name`.
- **Regression** (`regress.py`) — the phrases that drove the move to whisper-medium, plus the
  real command vocabulary, spoken by every English voice macOS ships. This is the one that
  decides the engine; VoiceBench measures general speech and disagrees with it.
- **VoiceBench** (`run_voicebench.py`) — the real `hlt-lab/voicebench` dataset (Apache 2.0),
  spoken instructions through Happy's own ears. Reports word error rate and a realtime factor
  per accent split, Indian English included.

## Held out, and why

Half the choosing cases and every second replay row are marked held out: never tuned against,
only checked. Both runners report the two halves apart. A change that lifts the rows it was
written against and leaves the rest where they were is fitted to the suite rather than to
Happy, and one number hides that completely. A harvested evening should default to held out.

## One run is not a score

The suites swing run to run. `run_choosing.py` runs everything three times by default and
prints the low, the high and the spread, and it separates a case that failed **every** run
from one that failed **some** — the first is a regression, the second is a coin flip. Do not
compare a number to yesterday's without the spread beside it, and measure HEAD on the tree in
front of you rather than trusting a number written down last week.

Before measuring anything: `ollama ps`, because a running Happy evicts the bench model, and
`ps` for another replay, because two runs against one Ollama double every turn.

OSWorld is deliberately absent. It needs a real virtual machine and it is Ubuntu-first, while
Happy is macOS and Windows only.

## Why this is safe to run

`sandbox.py` is the whole safety story, and it is worth understanding before trusting it.

1. **Every tool becomes a stub.** `harness()` walks `hands.tools()` and wraps each one in a
   `StructuredTool` that keeps the name, description and argument schema — so the model sees an
   identical toolset and picks exactly as it would in real life — but whose body only appends to
   a list. `run_command`, `system_control`, `move_to_trash` and `control_app` are inert.
2. **The database is redirected.** `throwaway()` sets `HAPPY_DB` before any Happy module is
   imported, so `memory/storage.py` opens a scratch file in `bench/runs/` instead of `data/`.
   Without this a run puts a hundred fake turns into the real history and the panel.
3. **It refuses to start if either fails.** `assert_no_real_tools()` raises unless every tool in
   the list is one of its own stubs.

Verified rather than assumed: calling the mocked `run_command` with `rm -rf ~/Desktop`, and
`system_control` with `power`, `shutdown`, does nothing at all.

## Running them

    python3 bench/replay.py bench/suites/project-docs-and-shopping.json        # the whole evening, ten minutes
    python3 bench/replay.py bench/suites/project-docs-and-shopping.json 21 26  # just those rows
    python3 bench/replay.py bench/suites/watching-and-documents.json --effort medium   # any brain knob

    python3 bench/shape.py                        # every structural check, one second
    python3 bench/shape.py --bless                # accept the prompt as it now stands

    python3 bench/run_choosing.py                 # forty-five cases, three times each
    python3 bench/run_choosing.py --times 5       # five
    python3 bench/run_choosing.py B1 B2 R3        # just the named cases

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

A choosing case lists `expect` (any one of these tools is right), optional `then` (a second
call that must follow, or it scores partial), and `forbid` (`"*"` means the right answer was to
say something and call nothing). A call a guard turned back is not counted as a call the model
got to make, because scoring a refusal as a choice marks the guard working as a fault.

## Where it stood on 2026-08-31

ToolCall-15, the fifteen cases that `choosing.py` grew out of: 12 pass, 1 partial, 2 fail — 83%. Both failures were prompt discipline, not
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
