"""Generate a lookup table of buoyancy explanations, one per exact character count.

Uses OpenRouter (OpenAI-compatible chat completions) over plain HTTP, so the only
requirement is the Python standard library.

The table maps an exact character count -> an explanation of that exact length.
Every length in [TARGET_RANGE_FROM, TARGET_RANGE_TO] must be populated; the script
keeps working slots until they are all filled or the attempt budget runs out.
"""

import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TARGET_RANGE_FROM = 1     # Minimum character count that must be populated
TARGET_RANGE_TO = 500     # Maximum character count that must be populated (inclusive)
MAX_ATTEMPTS_PER_LENGTH = 20   # Refinement attempts before a slot is given up on
MAX_WORKERS = 8           # Parallel slots in flight
RENAME_RETRIES = 10       # Retries when Windows briefly locks the table file
SAVE_INTERVAL = 3.0       # Minimum seconds between unforced checkpoint writes
MODEL = "google/gemini-2.5-flash-lite"
TEMPERATURE = 0.8

API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY_PATH = "api_key.txt"
LOOKUP_TABLE_PATH = "lookup_table.json"

TOPIC = "buoyancy"

SYSTEM_PROMPT = (
    "You write explanations of a physics concept that must be an EXACT number of "
    "characters long, counting spaces and punctuation. Reply with the explanation "
    "text only: no preamble, no quotes, no markdown, no trailing newline, no "
    "character counts. Use a single paragraph with no line breaks. Prefer natural, "
    "readable prose and never pad with filler characters or repeated words."
)


def initial_prompt(character_count):
    return (
        f"Explain {TOPIC} - why objects float or sink in a fluid - in prose containing "
        f"no formulas. The explanation must be exactly {character_count} characters long, "
        f"counting spaces and punctuation."
    )


def refine_prompt(character_count, attempt_text):
    delta = character_count - len(attempt_text)
    direction = (
        f"It is {delta} characters too short; expand it."
        if delta > 0
        else f"It is {-delta} characters too long; tighten it."
    )
    return (
        f"That version is {len(attempt_text)} characters, but it must be exactly "
        f"{character_count}. {direction} Keep it a fluent explanation of {TOPIC} with no "
        f"formulas, and return only the corrected text."
    )


def normalize(text):
    """Collapse the text to the single-line form that gets stored and measured."""
    text = text.strip().strip('"').strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class LookupTable:
    """Thread-safe store that persists to disk as new exact-length hits arrive."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._save_lock = threading.Lock()
        self._data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                self._data = {int(k): v for k, v in json.load(file).items()}
        self._dirty = False
        self._last_save = 0.0

    def __contains__(self, length):
        with self._lock:
            return length in self._data

    def __len__(self):
        with self._lock:
            return len(self._data)

    def keys(self):
        with self._lock:
            return sorted(self._data)

    def get(self, length):
        with self._lock:
            return self._data.get(length)

    def offer(self, text):
        """Store `text` under its own length if that slot is still empty."""
        length = len(text)
        if not length:
            return False
        with self._lock:
            if length in self._data:
                return False
            self._data[length] = text
            self._dirty = True
            return True

    def save(self, force=False):
        # Serialize writers: the temp file is shared, and on Windows a concurrent
        # os.replace against an open handle fails outright.
        with self._save_lock:
            now = time.monotonic()
            if not force and now - self._last_save < SAVE_INTERVAL:
                return  # Checkpoint is debounced; the data stays dirty for the next save.
            with self._lock:
                if not (self._dirty or force):
                    return
                snapshot = dict(sorted(self._data.items()))
                self._dirty = False

            tmp_path = f"{self.path}.tmp.{os.getpid()}"
            try:
                with open(tmp_path, "w", encoding="utf-8") as file:
                    json.dump(snapshot, file, indent=4, ensure_ascii=False)
                # An antivirus scanner or indexer can hold a transient handle on the
                # freshly written file, which makes os.replace fail with EACCES or
                # EBUSY. Retry rather than losing the run over a momentary lock.
                for attempt in range(RENAME_RETRIES):
                    try:
                        os.replace(tmp_path, self.path)
                        self._last_save = time.monotonic()
                        return
                    except PermissionError:
                        if attempt == RENAME_RETRIES - 1:
                            raise
                        time.sleep(0.1 * (attempt + 1))
            except OSError as error:
                # Keep the data in memory and try again on the next save; a failed
                # checkpoint must never abort generation.
                with self._lock:
                    self._dirty = True
                print(f"  warning: could not save lookup table ({error}); will retry")
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass


def load_api_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    if os.path.exists(API_KEY_PATH):
        with open(API_KEY_PATH, "r", encoding="utf-8") as file:
            return file.read().strip()
    sys.exit(
        "No OpenRouter API key found. Set OPENROUTER_API_KEY or place the key in "
        f"{API_KEY_PATH}."
    )


def chat(api_key, messages, retries=4):
    payload = json.dumps(
        {"model": MODEL, "messages": messages, "temperature": TEMPERATURE}
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/matthiasheim3d/gravity-explained-in-n-characters",
        "X-Title": "Buoyancy Explained in n Characters",
    }

    for attempt in range(retries):
        request = urllib.request.Request(API_URL, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.load(response)
            return body["choices"][0]["message"]["content"]
        except (urllib.error.URLError, KeyError, IndexError, ValueError) as error:
            if attempt == retries - 1:
                print(f"  request failed: {error}")
                return ""
            time.sleep(2 ** attempt + random.random())
    return ""


def fill_length(api_key, table, target):
    """Drive one slot to an exact hit, harvesting off-by-n attempts into free slots."""
    if target in table:
        return True

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": initial_prompt(target)},
    ]

    for attempt in range(1, MAX_ATTEMPTS_PER_LENGTH + 1):
        raw = chat(api_key, messages)
        if not raw:
            continue
        text = normalize(raw)
        if not text:
            continue

        if len(text) == target:
            table.offer(text)
            table.save()
            print(f"  {target}: hit on attempt {attempt}")
            return True

        # A miss is still a valid explanation - bank it wherever it fits.
        if table.offer(text):
            table.save()

        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": refine_prompt(target, text)})
        # Keep the conversation short so the model stays anchored on the target.
        if len(messages) > 8:
            messages = messages[:2] + messages[-4:]

    print(f"  {target}: no exact match after {MAX_ATTEMPTS_PER_LENGTH} attempts")
    return False


def missing_lengths(table):
    return [n for n in range(TARGET_RANGE_FROM, TARGET_RANGE_TO + 1) if n not in table]


def main():
    api_key = load_api_key()
    table = LookupTable(LOOKUP_TABLE_PATH)

    total = TARGET_RANGE_TO - TARGET_RANGE_FROM + 1
    pending = missing_lengths(table)
    print(f"{total - len(pending)} of {total} lengths already populated.")

    round_number = 0
    while pending:
        round_number += 1
        print(f"\nRound {round_number}: filling {len(pending)} missing lengths")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            list(pool.map(lambda n: fill_length(api_key, table, n), pending))

        table.save(force=True)
        still_missing = missing_lengths(table)
        if len(still_missing) == len(pending):
            print(
                f"\nRound {round_number} made no progress; stopping with "
                f"{len(still_missing)} lengths unfilled."
            )
            pending = still_missing
            break
        pending = still_missing

    table.save(force=True)
    print(f"\nLookup table saved to {LOOKUP_TABLE_PATH} ({len(table)} entries).")

    remaining = missing_lengths(table)
    if remaining:
        preview = ", ".join(str(n) for n in remaining[:20])
        suffix = " ..." if len(remaining) > 20 else ""
        print(
            f"INCOMPLETE: {len(remaining)} lengths in "
            f"[{TARGET_RANGE_FROM}, {TARGET_RANGE_TO}] are still empty: {preview}{suffix}"
        )
        return 1

    print(f"All lengths from {TARGET_RANGE_FROM} to {TARGET_RANGE_TO} are populated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
