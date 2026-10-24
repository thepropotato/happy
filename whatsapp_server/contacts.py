"""Who a said name means on WhatsApp, remembered across turns in two small files."""

import inspect
import os
import pickle
from pathlib import Path

FACTS = "facts.pkl"
PENDING = "pending.pkl"


class KnowledgeError(Exception):
    pass


def recall(entity, service):
    who = folded(entity)
    where = named(service)

    if not who or not where:
        return None

    return loaded_facts().get(who, {}).get(where)


def resolve_or_confirm(said_name, service, candidate):
    known = recall(said_name, service)

    if known:
        return known

    if candidate:
        # KEPT WHERE THE NEXT TURN CAN FIND IT, BECAUSE THEIR YES ARRIVES ON THE NEXT TURN
        # AND IN A CONNECTOR'S CASE IN A DIFFERENT PROCESS ENTIRELY.
        expect(said_name, candidate, service)

        raise KnowledgeError(
            f"'{said_name}' isn't a known exact match for {service}. The closest "
            f"guess is '{candidate}', but this must be confirmed directly "
            f"by the person before using or remembering it — browsing a "
            f"list or a fuzzy match is not confirmation on its own. "
            f"Ask them whether '{candidate}' is who they meant. If they say it is, "
            f"remember it against '{said_name}' and then carry on with what they "
            f"originally asked for, on this same service."
        )

    return None


async def resolved(query, service, searcher):
    """CHECK THE SAVED KNOWLEDGE BASE FIRST; ONLY CALL searcher(query) IF NOTHING'S KNOWN."""
    known = recall(query, service)

    if known:
        return known, True

    result = searcher(query)

    if inspect.isawaitable(result):
        result = await result

    return result, False


def awaiting(candidate, service):
    """WHAT THEY ORIGINALLY SAID, IF candidate IS A GUESS STILL WAITING ON THEIR YES.

    THIS OUTLIVES THE TURN THAT ASKED, WHICH IS THE WHOLE POINT: THE QUESTION GOES OUT ON
    ONE TURN AND THE ANSWER COMES BACK ON THE NEXT, AND A CONNECTOR IS A SUBPROCESS THAT IS
    HANDED A FRESH CLIENT EVERY REQUEST. HELD IN MEMORY THIS WAS ALWAYS EMPTY BY THE TIME
    IT WAS READ, SO ONE SHORT NAME'S LONGER FORM WAS CONFIRMED THREE TIMES AND LEARNED NONE."""
    where = named(service)
    guess = folded(candidate)

    if not where or not guess:
        return None

    return loaded_pending().get(where, {}).get(guess)


def expect(said, candidate, service):
    """KEEP THAT candidate IS THE GUESS WE PUT TO THEM FOR said, UNTIL THEY ANSWER."""
    where = named(service)
    guess = folded(candidate)
    spoken = str(said or "").strip()

    if not where or not guess or not spoken:
        return

    kept = loaded_pending()
    held = kept.get(where, {})

    held[guess] = spoken
    kept[where] = held

    saved(pending_file(), kept)


def settle(candidate, service):
    """THE GUESS IS ANSWERED, SO IT IS NO LONGER WAITING."""
    where = named(service)
    guess = folded(candidate)

    if not where or not guess:
        return

    kept = loaded_pending()
    held = kept.get(where, {})

    if held.pop(guess, None) is not None:
        kept[where] = held
        saved(pending_file(), kept)


def remember_fact(entity, service, value):
    who = folded(entity)
    where = named(service)

    if not who or not where:
        return

    kept = loaded_facts()
    held = kept.get(who, {})

    held[where] = str(value or "").strip()
    kept[who] = held

    saved(facts_file(), kept)


def loaded_facts():
    return loaded(facts_file(), {})


def loaded_pending():
    return loaded(pending_file(), {})


def loaded(where, fallback):
    if not where.exists():
        return fallback

    with where.open("rb") as handle:
        return pickle.load(handle)


def saved(where, value):
    with where.open("wb") as handle:
        pickle.dump(value, handle)


def facts_file():
    return root() / FACTS


def pending_file():
    return root() / PENDING


def folded(value):
    return str(value or "").strip().lower()


def named(value):
    return str(value or "").strip().lower()


def root():
    folder = Path(os.environ.get("HAPPY_WHATSAPP") or Path.home() / ".happy" / "whatsapp")
    folder.mkdir(parents=True, exist_ok=True)
    return folder
