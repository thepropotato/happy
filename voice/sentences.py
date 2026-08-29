"""WHERE ONE SPOKEN SENTENCE ENDS AND THE NEXT BEGINS."""

import re

# A FULL STOP FOLLOWED BY SPACE, OR A LINE BREAK. THE SPACE KEEPS "3.5" WHOLE.
ENDINGS = re.compile(r"(?<=[.!?])[\"')\]]*\s+|\n+")

MIN_CHARS = 24

MIN_CHARS_FIRST = 4

MAX_CHARS = 260

# A FULL STOP AFTER ONE OF THESE BELONGS TO THE WORD, NOT THE SENTENCE.
SHORTENED = {
    "mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "vs", "etc", "eg", "ie",
    "no", "approx", "inc", "ltd", "co", "dept", "fig", "al", "am", "pm",
}

INITIAL = 1  # ONE LETTER AND A DOT IS NEVER A SENTENCE.

# WHERE A SENTENCE TOO LONG TO READ IN ONE GO IS BROKEN: A CLAUSE ENDS AT ONE OF THESE, AND
# THE VOICE ALREADY PAUSES THERE, SO THE BREAK IS HEARD AS THE WRITING RATHER THAN AS A FAULT.
CLAUSE = re.compile(r"[,;:][\"')\]]*\s")

BEFORE = re.compile(r"([A-Za-z]+)\.[\"')\]]*\s*$")


class Sentences:
    """PIECES IN, WHOLE SENTENCES OUT."""

    def __init__(self):
        self.buffer = ""
        self.started = False

    def feed(self, piece):
        """TAKE A PIECE. WHOLE SENTENCES COME BACK, THE REST WAITS."""
        self.buffer += piece
        ready = []

        while True:
            cut = self.edge()

            if cut is None:
                return ready

            head, self.buffer = self.buffer[:cut].strip(), self.buffer[cut:]

            if head:
                self.started = True
                ready.append(head)

    def flush(self):
        """WHATEVER IS LEFT, EVEN WITHOUT A FULL STOP ON THE END."""
        rest, self.buffer = self.buffer.strip(), ""
        self.started = False

        return [rest] if rest else []

    def clear(self):
        self.buffer = ""
        self.started = False

    def edge(self):
        """WHERE THE NEXT THING WORTH SAYING ENDS, OR None IF IT HAS NOT YET."""
        least = MIN_CHARS if self.started else MIN_CHARS_FIRST

        for found in ENDINGS.finditer(self.buffer):
            if found.end() >= least and not self.shortened(found.end()):
                return found.end()

        if len(self.buffer) < MAX_CHARS:
            return None

        # A CLAUSE END IS WHERE A PERSON WOULD HAVE BREATHED ANYWAY. CUTTING AT THE LAST
        # SPACE INSTEAD PUTS A FULL STOP'S WORTH OF SILENCE INSIDE A PHRASE.
        clause = [found.end() for found in CLAUSE.finditer(self.buffer, 0, MAX_CHARS)]

        if clause and clause[-1] >= least:
            return clause[-1]

        space = self.buffer.rfind(" ", 0, MAX_CHARS)  # NEVER CUT A WORD IN HALF.

        return space + 1 if space > 0 else MAX_CHARS

    def shortened(self, at):
        """TRUE WHEN THE FULL STOP ENDING AT at BELONGS TO A WORD."""
        word = BEFORE.search(self.buffer[:at])

        if not word:
            return False

        return len(word.group(1)) == INITIAL or word.group(1).lower() in SHORTENED
