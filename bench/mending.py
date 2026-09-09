"""WHAT MUST BE TRUE OF A MENDED TOOL CALL, CHECKED AGAINST WHAT THE MODEL REALLY WROTE.

    python3 bench/mending.py

NO MODEL RUNS HERE. THE RAW LINES BELOW WERE COPIED OFF A REAL EVENING WHERE FOUR GOES AT
READING A WHATSAPP THREAD ALL DIED ON THE SAME PUNCTUATION, SO THE ANSWER IS THE SAME EVERY
TIME AND ARRIVES AT ONCE."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain import mending

# THE WHATSAPP TOOL'S SHAPE, ENOUGH OF IT TO SAY WHETHER A MEND FITS.
MESSAGES = {
    "properties": {
        "contact": {},
        "limit": {},
        "order_newest": {},
        "received_only": {},
        "why": {},
    },
    "required": ["contact"],
}

# WHAT WENT WRONG, WHAT IT SHOULD COME BACK AS, AND WHY THE CASE IS HERE.
CASES = [
    (
        "THE SPLICE, WHOLE: BOTH SETS OF KEYS BELONG TO THE ONE CALL",
        '{"contact":["Swish"],{"limit":3,"order_newest":true,"received_only":true,"why":"..."}',
        {
            "contact": ["Swish"],
            "limit": 3,
            "order_newest": True,
            "received_only": True,
            "why": "...",
        },
    ),
    (
        "THE SPLICE, CUT OFF MID-KEY: WHAT WAS FINISHED IS KEPT, THE HALF-KEY IS DROPPED",
        '{"contact":["Musalodu"],{"limit":3,"order_newout?"}',
        {"contact": ["Musalodu"], "limit": 3},
    ),
    (
        "NOTHING WRONG WITH IT: A GOOD CALL IS LEFT EXACTLY AS IT IS",
        '{"contact":["Aunty"],"limit":3}',
        {"contact": ["Aunty"], "limit": 3},
    ),
    (
        "STOPPED PART-WAY: EVERY BRACKET STILL OPEN IS SHUT",
        '{"contact":["Aunty"],"limit":3',
        {"contact": ["Aunty"], "limit": 3},
    ),
    (
        "A STRING LEFT OPEN IS SHUT WHERE IT STOPPED",
        '{"contact":["Aunty"],"why":"reading the',
        {"contact": ["Aunty"], "why": "reading the"},
    ),
    (
        "A LIST OF OBJECTS IS NOT A SPLICE AND MUST SURVIVE WHOLE",
        '{"contact":["A"],"notes":[{"a":1},{"b":2}]}',
        {"contact": ["A"], "notes": [{"a": 1}, {"b": 2}]},
    ),
    (
        "A BRACE INSIDE A STRING IS TEXT, NOT PUNCTUATION",
        '{"contact":["A"],"why":"say },{ out loud"}',
        {"contact": ["A"], "why": "say },{ out loud"},
    ),
    (
        "NOTHING SURVIVES BEING CUT: BETTER TO ASK AGAIN THAN TO CALL ON A GUESS",
        '{"contact"',
        None,
    ),
    (
        "EMPTY IS NOT A CALL",
        "",
        None,
    ),
]

# THE WHOLE COMPLAINT, AS THE BACKEND HANDS IT OVER.
COMPLAINT = (
    "error parsing tool call: raw='{\"contact\":[\"Swish\"],{\"limit\":3}', "
    "err=invalid character '{' looking for beginning of object key string"
)


def main():
    wrong = 0

    for why, raw, wanted in CASES:
        got = mending.mended(raw)

        if got != wanted:
            wrong += 1
            print(f"WRONG  {why}\n       {raw}\n       wanted {wanted}\n       got    {got}")
        else:
            print(f"ok     {why}")

    # THE RAW TEXT HAS TO COME OUT OF THE COMPLAINT BEFORE ANY OF THE ABOVE CAN RUN AT ALL.
    lifted = mending.wrote(COMPLAINT)

    if lifted != '{"contact":["Swish"],{"limit":3}':
        wrong += 1
        print(f"WRONG  THE RAW TEXT IS LIFTED OUT OF THE COMPLAINT\n       got {lifted}")
    else:
        print("ok     THE RAW TEXT IS LIFTED OUT OF THE COMPLAINT")

    # A MEND THAT DOES NOT FIT THE TOOL IS NOT ALLOWED TO BE CALLED.
    for why, args, wanted in (
        ("A MEND THAT FITS THE TOOL IS ALLOWED", {"contact": ["A"], "limit": 3}, True),
        ("A NAME THE TOOL DOES NOT TAKE IS REFUSED", {"contact": ["A"], "nope": 1}, False),
        ("A MISSING REQUIRED ARGUMENT IS REFUSED", {"limit": 3}, False),
    ):
        if mending.fitting(args, MESSAGES) is not wanted:
            wrong += 1
            print(f"WRONG  {why}")
        else:
            print(f"ok     {why}")

    print(f"\n{wrong} wrong" if wrong else "\nall good")

    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main())
