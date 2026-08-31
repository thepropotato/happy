"""THE PHRASES THAT DROVE THE MOVE TO whisper-medium, SPOKEN BY A VOICE THAT IS NOT OURS.

macOS `say` MAKES THE CLIPS, SO THE THING BEING TESTED IS THE EAR AND NOTHING ELSE.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import sandbox

sandbox.throwaway("regress.db")

import ears.engines as engines

# ORDINARY WORDS A SMALL MODEL TURNS INTO NUMBERS, AND THE EVERYDAY ASKS AROUND THEM.
# THE FIRST GROUP IS THE REGRESSION THAT DROVE whisper-medium; THE REST IS THE REAL VOCABULARY.
PHRASES = [
    # THE unread FAMILY, THE DOCUMENTED FAILURE.
    "how many unread emails do I have",
    "mark it as unread",
    "anything unread in there",
    "read me the unread ones",
    "is that one unread",
    "show me my unread messages",

    # LETTERS AND SPELLING, WHICH count_letters AND spell_word DEPEND ON.
    "how many r's are in strawberry",
    "how many s's are in mississippi",
    "spell out the word receipt",
    "what letter does it start with",

    # NUMBERS THAT SHOULD STAY NUMBERS.
    "turn the volume down to twenty",
    "set a reminder for four thirty",
    "make it thirty percent brighter",
    "remind me in fifteen minutes",

    # APPS AND SERVICES, THE NAMES IT HAS TO GET RIGHT.
    "open notion and find my notes",
    "check my calendar for tomorrow",
    "search github for that repo",
    "put it on the clipboard",
    "what's in my downloads folder",

    # PLAIN COMMANDS THAT SHOULD NEVER BREAK.
    "open the second one",
    "what's playing right now",
    "skip to the next track",
    "close that window",
    "take a screenshot of this",
    "what am I looking at",
]

# INDIAN ENGLISH FIRST, BECAUSE THAT IS THE VOICE THIS IS FOR.
VOICES = ["Rishi", "Aman", "Tara", "Samantha", "Karen", "Daniel", "Moira", "Tessa"]



NUMBERS = {"twenty": "20", "thirty": "30", "fifteen": "15", "four thirty": "4.30",
           "four thirty ": "430", "second": "2nd", "percent": "%"}


def cosmetic(said, heard):
    """TRUE WHEN THE ONLY DIFFERENCE IS DIGITS FOR WORDS OR PUNCTUATION."""
    import re

    def bare(text):
        text = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
        return re.sub(r"\s+", " ", text)

    a, b = bare(said), bare(heard)
    if a == b:
        return True

    for word, digit in NUMBERS.items():
        a = a.replace(word, digit)
    a = re.sub(r"\s+", " ", a).strip()

    return a == b


def clip(text, voice, where):
    """ONE PHRASE AS 16k WAV, WHICH IS WHAT BOTH EARS EXPECT."""
    aiff = where.with_suffix(".aiff")
    subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
                    str(aiff), str(where)], check=True)
    aiff.unlink()
    return where


def main():
    folder = Path(__file__).resolve().parent / "runs" / "regress"
    folder.mkdir(parents=True, exist_ok=True)

    engine_names = sys.argv[1:] or ["parakeet", "whisper"]
    wrong = {name: 0 for name in engine_names}
    total = 0

    for voice in VOICES:
        print(f"\n-- {voice} --")
        for i, said in enumerate(PHRASES):
            path = clip(said, voice, folder / f"{voice}-{i:02d}.wav")
            total += 1
            heard, bad = {}, {}
            for name in engine_names:
                got = (engines.transcribe(str(path), engine=name) or "").strip()
                heard[name] = got
                bad[name] = not cosmetic(said, got)
                if bad[name]:
                    wrong[name] += 1

            # ONLY PRINT THE ROWS WHERE AN ENGINE GOT SOMETHING SUBSTANTIVELY WRONG.
            if any(bad.values()):
                print(f"  said : {said}")
                for name in engine_names:
                    print(f"  {'XX' if bad[name] else '  '} {name:<9}: {heard[name]}")

    print(f"\nout of {total} clips, substantive misses (digits-for-words not counted):")
    for name in engine_names:
        print(f"  {name:<9} {wrong[name]:>3}")


if __name__ == "__main__":
    main()
