"""SMALL LOCAL KNOWLEDGE BASE OF FACTS AND NOTES."""

import inspect
import pickle
from pathlib import Path

import numpy as np

from memory import embedding, storage

FACTS = "facts.pkl"
MEMORIES = "memories.pkl"
PENDING = "pending.pkl"
DUPLICATE_MINIMUM = 0.9


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


def search_memory(query, top=3, minimum=0.25):
    kept = loaded_memories()
    notes = list(kept.get("notes") or [])

    if not notes:
        return []

    vectors = np.asarray(kept.get("vectors"), dtype=np.float32)

    if vectors.size == 0:
        return []

    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)

    if vectors.shape[0] != len(notes):
        return []

    asked = embedding.vector(query)

    if vectors.shape[1] != asked.shape[0]:
        return []

    scores = cosine(vectors, asked)
    limit = max(1, int(top))
    floor = float(minimum)

    ranked = sorted(range(len(notes)), key=lambda i: float(scores[i]), reverse=True)

    return [notes[i] for i in ranked if float(scores[i]) >= floor][:limit]


def remember_note(text):
    note = str(text or "").strip()

    if not note:
        return

    kept = loaded_memories()
    notes = list(kept.get("notes") or [])
    vectors = np.asarray(kept.get("vectors"), dtype=np.float32)

    made = embedding.vector(note)

    if notes and vectors.size:
        if vectors.ndim == 1:
            seen = vectors.reshape(1, -1)
        else:
            seen = vectors

        if seen.shape[0] == len(notes) and seen.shape[1] == made.shape[0]:
            scores = cosine(seen, made)

            if float(np.max(scores)) >= DUPLICATE_MINIMUM:
                return

    if vectors.size == 0:
        vectors = made.reshape(1, -1)
    elif vectors.ndim == 1:
        vectors = np.vstack([vectors.reshape(1, -1), made.reshape(1, -1)])
    else:
        vectors = np.vstack([vectors, made.reshape(1, -1)])

    notes.append(note)

    saved(memories_file(), {"notes": notes, "vectors": vectors})


def loaded_facts():
    return loaded(facts_file(), {})


def loaded_pending():
    return loaded(pending_file(), {})


def loaded_memories():
    empty = {"notes": [], "vectors": np.empty((0, 0), dtype=np.float32)}
    kept = loaded(memories_file(), empty)

    notes = list(kept.get("notes") or [])
    vectors = np.asarray(kept.get("vectors"), dtype=np.float32)

    if vectors.size == 0:
        vectors = np.empty((0, 0), dtype=np.float32)

    return {"notes": notes, "vectors": vectors}


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


def memories_file():
    return root() / MEMORIES


def pending_file():
    return root() / PENDING


def root():
    return Path(storage.path()).parent


def folded(value):
    return str(value or "").strip().lower()


def named(value):
    return str(value or "").strip().lower()


def cosine(vectors, asked):
    scale = np.linalg.norm(vectors, axis=1) * np.linalg.norm(asked)
    dots = vectors @ asked

    return np.divide(dots, scale, out=np.zeros(vectors.shape[0], dtype=np.float32), where=scale > 0)