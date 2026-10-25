"""The memory store, and the handle. TODO 1 to 3.

Two things live here and they are easy to confuse.

**Memory** is what the agent remembers about a resident across runs: facts,
written once and searched later. It is a store.

**A handle** is a name for a piece of state that the agent carries in its own
messages. It is not memory, it is an address. `open_case` mints one, and
every later call passes it back as an ordinary argument.

The distinction is the whole week. Block 2 shows why: when the protocol stops
carrying state for you, the state does not vanish, it becomes an argument
with a name the model can see.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path("artifacts/memory_store.json")


@dataclass
class Fact:
    subject: str
    kind: str
    text: str
    handle: str
    written_at: str


@dataclass
class MemoryStore:
    """A file-backed store. Deliberately not a database and not a vector store.

    Week 7 replaces `search` with real retrieval over embeddings. Keep the
    keyword version behind this one method and next week costs you ten lines
    instead of a refactor.
    """

    path: Path = DEFAULT_PATH
    facts: list[Fact] = field(default_factory=list)
    cases: dict[str, str] = field(default_factory=dict)

    # ----------------------------------------------------------------
    # TODO 1. Writing, and the handle it returns.
    # ----------------------------------------------------------------

    def write(self, subject: str, kind: str, text: str) -> str:
        """TODO 1. Append one fact and return a handle for it.

        Three decisions here, and all three go in DECISIONS.md with a reason.

        What does a handle look like? A sequential `fact-0007` tells anyone
        who sees it how many facts exist and lets them guess `fact-0006`,
        which is a read of somebody else's data. Week 12 attacks exactly
        this.

        What happens when a new fact contradicts an older one? Keeping both
        means `recall` can return two contradictory facts and something has
        to cope. Overwriting means losing what changed and when. Pick one.

        How long does a record live? Nothing here expires, which is a choice
        and the wrong one for a real service holding residents' data. If you
        keep it, say so rather than leaving it unsaid.
        """
        # Make a random handle so people cannot guess other fact handles.
        handle = f"fact-{secrets.token_hex(6)}"

        # Create the fact we want to remember.
        fact = Fact(
            subject=subject,
            kind=kind,
            text=text,
            handle=handle,
            written_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # Keep the new fact. If it conflicts with an older fact, we keep both.
        self.facts.append(fact)

        # Save the updated memory so it survives when the program stops.
        self.save()

        # Give the caller the handle for this fact.
        return handle

        # raise NotImplementedError("TODO 1: append a fact, return a handle")

    # ----------------------------------------------------------------
    # TODO 2. Searching, and what k costs.
    # ----------------------------------------------------------------

    def search(self, subject: str, query: str, k: int = 3) -> list[str]:
        """TODO 2. Return at most k remembered facts about ONE subject.

        Scope to the subject BEFORE you score anything. That is not an
        optimization, it is the boundary that stops one resident's memory
        leaking into another's conversation, and it belongs here rather than
        in a sentence asking the model not to do it.

        Keyword overlap is fine. Week 7 replaces the body of this method
        with embeddings and the signature does not change, so keep the
        matching inside this one method.

        Then answer, at the checkpoint: what does k cost you in tokens per
        call, and what happens when the store holds four hundred facts?
        """
        # First, keep only facts belonging to this resident.
        subject_facts = [fact for fact in self.facts if fact.subject == subject]

        # Split the search query into lowercase words.
        query_words = set(query.lower().split())

        # Score each fact by how many query words match.
        scored_facts = []
        for fact in subject_facts:
            fact_words = set(fact.text.lower().split())
            score = len(query_words & fact_words)
            scored_facts.append((score, fact))

        # Put the facts with the highest scores first.
        scored_facts.sort(key=lambda item: item[0], reverse=True)

        # Return at most k facts, as strings.
        return [fact.text for score, fact in scored_facts[:max(0, k)]]

        # raise NotImplementedError("TODO 2: search, scoped to the subject")

    # ----------------------------------------------------------------
    # TODO 3. Forgetting, which is not optional.
    # ----------------------------------------------------------------

    def forget(self, handle: str) -> bool:
        """TODO 3. Hard delete by handle. Return whether it existed.

        Not optional. A store that can only be written to is not a store you
        can operate, and "we keep everything forever" is an answer with a
        legal department attached to it.

        One line in DECISIONS.md about what this does NOT reach: anything
        already copied into a running conversation's messages. Deleting the
        fact does not un-say it.
        """
        # Find the fact with the given handle.
        for fact in self.facts:
            if fact.handle == handle:
                # Remove the fact from memory.
                self.facts.remove(fact)

                # Save the change to the JSON file.
                self.save()

                return True

        # No fact with this handle was found.
        return False

        # raise NotImplementedError("TODO 3: hard delete by handle")

    # ----------------------------------------------------------------
    # The handle, which is block 2's subject
    # ----------------------------------------------------------------

    def open_case(self, subject: str) -> str:
        """Mint an explicit handle for a piece of ongoing state."""
        handle = f"case-{secrets.token_hex(6)}"
        self.cases[handle] = subject
        self.save()
        return handle

    def subject_of(self, handle: str) -> str | None:
        return self.cases.get(handle)

    # ----------------------------------------------------------------
    # Persistence
    # ----------------------------------------------------------------

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "facts": [vars(f) for f in self.facts],
            "cases": self.cases,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "MemoryStore":
        store = cls(path=path)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            store.facts = [Fact(**f) for f in data.get("facts", [])]
            store.cases = data.get("cases", {})
        return store
