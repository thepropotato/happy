"""SMALL LOCAL KNOWLEDGE BASE OF FACTS AND NOTES."""

import inspect
import pickle
from pathlib import Path

import numpy as np

from memory import embedding, storage

FACTS = "facts.pkl"
MEMORIES = "memories.pkl"
DUPLICATE_MINIMUM = 0.9


class KnowledgeError(Exception):
    pass


def recall(entity, service):
    who = said(entity)
    where = named(service)

    if not who or not where:
        return None

    return loaded_facts().get(who, {}).get(where)


def resolve_or_confirm(said_name, service, candidate):
    known = recall(said_name, service)

    if known:
        return known

    if candidate:
        raise KnowledgeError(
            f"'{said_name}' isn't a known exact match for {service}. The closest "
            f"guess is '{candidate}', but this must be confirmed directly "
            f"by the person before using or remembering it — browsing a "
            f"list or a fuzzy match is not confirmation on its own."
        )

    return None


async def resolved(query, service, searcher):
    """CHECK THE SAVED KNOWLEDGE BASE FIRST; ONLY CALL searcher(query) IF NOTHING'S KNOWN.

    RETURNS (result, remembered) WHERE remembered IS True IF THE VALUE CAME FROM THE
    KNOWLEDGE BASE (ALREADY CONFIRMED EARLIER). searcher MAY BE SYNC OR ASYNC —
    inspect.isawaitable HANDLES BOTH: wa.search_contacts IS ASYNC, SO ITS RETURN
    VALUE IS A COROUTINE THAT IS AWAITED HERE RATHER THAN RETURNED UN-AWAITED.
    """
    known = recall(query, service)

    if known:
        return known, True

    result = searcher(query)

    if inspect.isawaitable(result):
        result = await result

    return result, False


def remember_fact(entity, service, value):
    who = said(entity)
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


def root():
    return Path(storage.path()).parent


def said(value):
    return str(value or "").strip().lower()


def named(value):
    return str(value or "").strip().lower()


def cosine(vectors, asked):
    scale = np.linalg.norm(vectors, axis=1) * np.linalg.norm(asked)
    dots = vectors @ asked

    return np.divide(dots, scale, out=np.zeros(vectors.shape[0], dtype=np.float32), where=scale > 0)