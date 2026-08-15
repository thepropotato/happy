"""AN UTTERANCE THAT IS NOT OVER: WHETHER IT IS FINISHED, AND WHAT IS HELD WHILE
IT IS NOT.

SILENCE ON ITS OWN CANNOT TELL THE TWO APART: THE PAUSE IN "PLAY ME THE... ER..."
SOUNDS EXACTLY LIKE THE PAUSE AFTER A FINISHED SENTENCE. SO THE SILENCE ENDS THE
TAKE QUICKLY, AND WHAT THE TAKE TURNED OUT TO SAY DECIDES WHETHER TO WAIT FOR
MORE. A LINE THAT TRAILS OFF MID THOUGHT BUYS ANOTHER FEW SECONDS, AND Held IS
WHERE THE FRONT HALF SITS WHILE THEY FINISH IT."""

import collections
import re
import time

from ears.naming import WORDS

# WHAT WAS ASKED, THE RECORDING IT WAS ASKED IN, AND WHAT THE HEARING COST.
Heard = collections.namedtuple("Heard", "text audio seconds")

# A LINE ENDING ON ONE OF THESE IS A LINE WITH SOMETHING STILL COMING. THESE ARE
# ENGLISH; A SENTENCE IN ANOTHER SCRIPT SIMPLY FALLS THROUGH AND IS TAKEN AS DONE.
HANGING = {
    # JOINING ONE HALF TO A HALF NOT SAID YET.
    "and", "or", "but", "so", "because", "if", "when", "while", "that", "which",
    "than", "then", "though", "although", "unless", "until", "whether", "plus",
    # POINTING AT A THING NOT NAMED YET.
    "to", "of", "in", "on", "at", "for", "from", "with", "about", "into", "onto",
    "over", "under", "by", "as", "like", "near", "upto",
    "a", "an", "the", "my", "your", "his", "her", "its", "our", "their",
    "this", "these", "those", "some", "any", "every", "another",
    # A VERB WAITING ON WHAT IT DOES.
    "is", "are", "was", "were", "am", "be", "been", "can", "could", "will",
    "would", "shall", "should", "may", "might", "must", "do", "does", "did",
    "have", "has", "had", "want", "need", "going", "gonna", "let", "get", "put",
    # NOISES MADE WHILE THINKING.
    "um", "uh", "er", "erm", "hmm", "mm", "well", "actually", "basically",
    "just", "really", "very", "quite", "how", "what", "which", "who", "where",
}

# NOTHING BUT THINKING NOISES IS NOT A QUESTION, IT IS SOMEBODY GETTING READY.
NOISES = {"um", "uh", "er", "erm", "hmm", "mm", "hm", "uhh", "ahh", "ah", "oh"}

# TRAILING OFF IN WRITING, WHICH IS WHAT A TRANSCRIBER PUTS WHERE A VOICE DID.
UNFINISHED_MARKS = ("...", "…", ",", "-", "–", "—", ":", ";")

FINISHED_MARKS = (".", "?", "!")


def unfinished(text):
    """TRUE WHEN THIS SOUNDS LIKE THE FRONT HALF OF SOMETHING."""
    said = (text or "").strip()

    if not said:
        return False

    if said.endswith(UNFINISHED_MARKS):
        return True

    # A FULL STOP IS THE TRANSCRIBER SAYING IT HEARD A SENTENCE END. BELIEVE IT.
    if said.endswith(FINISHED_MARKS):
        return False

    found = WORDS.findall(said.lower())

    return bool(found) and found[-1] in HANGING


def nothing(text):
    """TRUE WHEN THE WHOLE TAKE WAS SOMEBODY CLEARING THEIR THROAT."""
    found = WORDS.findall((text or "").lower())

    return not found or all(word in NOISES for word in found)


def joined(carried, said):
    """WHAT WAS HEARD IN TWO GOES, PUT BACK INTO ONE SENTENCE."""
    if not carried:
        return said.strip()

    if not said:
        return carried.strip()

    # THE PAUSE ITSELF IS NOT PART OF THE QUESTION, SO ITS COMMA GOES WITH IT.
    front = re.sub(r"[\s,;:\-–—]+$|\.{3}$|…$", "", carried.strip())

    return f"{front} {said.strip()}".strip()


class Held:
    """WHAT HAS BEEN HEARD OF A QUESTION SO FAR, AND HOW LONG TO WAIT FOR MORE."""

    def __init__(self):
        self.until = 0.0  # UNTIL THIS MOMENT, ANY TAKE IS PART OF THE QUESTION.
        self.text = ""
        self.times = 0  # HOW OFTEN THIS ONE QUESTION HAS BEEN PICKED BACK UP.
        self.where = None
        self.spent = None

    def open(self, at):
        """TRUE WHEN A TAKE STARTING THEN BELONGS TO WHAT WAS ALREADY BEING SAID."""
        return at < self.until

    def hold(self, text, where, wait, spent=None):
        """KEEP WHAT WAS HEARD AND WAIT FOR THE REST OF IT."""
        self.times = self.times + 1 if text else 0
        self.text = text
        self.until = time.monotonic() + wait
        self.spent = spent

        self.keep(where)

    def keep(self, where):
        """THE NEWEST TAKE IS THE ONE THAT IS KEPT: ALL THE RECORDING IS EVER USED
        FOR IS WHICH LANGUAGE THIS PERSON IS SPEAKING, AND THE LATEST SAYS THAT."""
        if self.where is not None and self.where != where:
            self.where.unlink(missing_ok=True)

        self.where = where

    def taken(self, text, spent=None):
        """THE WHOLE QUESTION, WITH NOTHING LEFT HELD BEHIND IT."""
        found = Heard(text=text, audio=self.where, seconds=spent or self.spent)

        self.clear(drop=False)

        return found

    def ran_out(self):
        """WHETHER THE WAIT IS OVER. None WHILE THERE IS STILL TIME ON IT."""
        if not self.until or time.monotonic() < self.until:
            return None

        # THEY TRAILED OFF AND NEVER CAME BACK. HALF A QUESTION IS STILL A
        # QUESTION, AND IS A BETTER ANSWER THAN PRETENDING IT WAS NEVER ASKED.
        if self.text and self.where:
            return self.taken(self.text)

        self.clear()

        return False

    def clear(self, drop=True):
        if drop and self.where is not None:
            self.where.unlink(missing_ok=True)

        self.until = 0.0
        self.text = ""
        self.times = 0
        self.where = None
        self.spent = None
