"""Block 3. The few-shot variant, and the honest comparison.

    python 02_few_shot.py --replay
    python 02_few_shot.py

Same schema, same scorer, same ten documents. One variable changes, which is
the presence of examples. That is the whole experimental design, and it is
the part most student comparisons get wrong.

Two ways to break it, both easy and both fatal:

  * editing the schema or the scorer between the two runs, which makes the
    two numbers incomparable
  * taking examples from DOCS, which turns the second measurement into a
    memory test. Examples come from EXAMPLE_POOL, which is held out for
    exactly this reason.

Two TODO markers.
"""

from __future__ import annotations

import argparse
import json

from documents import DOCS, EXAMPLE_POOL, GOLD
from extractor import SYSTEM_ZERO_SHOT, get_client, run_variant
from scoring import compare

from project.trace import write_json


# --------------------------------------------------------------------------
# TODO 5. Choose your examples and build the block.
# --------------------------------------------------------------------------

def few_shot_block(n: int = 4) -> str:
    """Return the example block that gets appended to the system prompt.

    Choose from EXAMPLE_POOL, never from DOCS. Three to five examples. Fewer
    is usually better than more, and you pay for every one of them in input
    tokens on every single call, forever.

    Choose deliberately, one per thing you could not say clearly in words:

      * a boundary you struggled to define, for example the line between
        facilities and hardware
      * a message with no stated deadline, which demonstrates the null
        convention rather than describing it
      * a message in a language other than English, because the corpus is
        multilingual and an all English example block quietly teaches the
        model that English is the norm

    Write the reason for each choice in DECISIONS.md. "It seemed useful" is
    not a reason, and at the checkpoint you will be asked which field each
    example was meant to move.

    One trap worth knowing before you fall into it. Whatever you show in the
    `quote` field of your examples is what the model will imitate. If your
    examples carry truncated or tidied quotes, you have just taught it to
    stop copying verbatim, and the field that scored perfectly zero-shot
    will get worse. Look at the recording if you want to see that happen.
    """

    # Choose four examples deliberately from EXAMPLE_POOL.
    # The order here refers to EX-02, EX-04, EX-05, and EX-01.
    selected = [
        EXAMPLE_POOL[1],
        EXAMPLE_POOL[3],
        EXAMPLE_POOL[4],
        EXAMPLE_POOL[0],
    ][:n]

    # Store an exact quote from each original example message.
    # These must appear character-for-character in the source message.
    quotes = {
        "EX-01": (
            "The badge reader at the side entrance rejects my card since the "
            "system update."
        ),
        "EX-02": (
            "L'ascenseur du batiment administratif est bloque entre le rez et "
            "le premier avec une personne a l'interieur."
        ),
        "EX-04": (
            "For information only: the new intranet search will be switched "
            "on next week."
        ),
        "EX-05": (
            "Nous avons recu deux fois la meme facture pour l'entretien des "
            "espaces verts, reference 2026-0417."
        ),
    }

    # Start the example section of the prompt.
    parts = [
        "Examples. Follow these exactly, including the quote style.",
        "",
    ]

    # Build one example at a time.
    for doc, gold in selected:

        # Create the structured answer that we want the model to imitate.
        record = {
            "category": gold.category,
            "urgency": gold.urgency,
            "due_date": gold.due_date,
            "quote": quotes[doc.id],
        }

        # Add the original message.
        parts.append(f"Message: {doc.text}")

        # Convert the Python dictionary into JSON text.
        parts.append(
            "Record: " + json.dumps(record, ensure_ascii=False)
        )

        # Add a blank line between examples.
        parts.append("")

    # Join all the pieces into one prompt block.
    return "\n".join(parts)

    # Original teacher TODO marker:
    # raise NotImplementedError("TODO 5: build the example block")


   # raise NotImplementedError("TODO 5: build the example block")


SYSTEM_FEW_SHOT = SYSTEM_ZERO_SHOT + "\n"   + few_shot_block()#, once written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = get_client(args.replay)

    zero_board, _, zero_metas = run_variant(client, SYSTEM_ZERO_SHOT,
                                            "zero-shot", DOCS, GOLD)
    few_board, _, few_metas = run_variant(
        client, SYSTEM_ZERO_SHOT + "\n" + few_shot_block(), "few-shot",
        DOCS, GOLD)

    print(compare(zero_board, few_board, "zero-shot", "few-shot"))

    zero_tok = sum(m["prompt_tokens"] for m in zero_metas)
    few_tok = sum(m["prompt_tokens"] for m in few_metas)
    per_call = (few_tok - zero_tok) / len(DOCS)
    print(f"\nexample block costs {per_call:.0f} input tokens per call, "
          f"{per_call * 1000:.0f} per thousand calls")

    write_json("artifacts/week02_comparison.json", {
        "zero_shot": {"hits": zero_board.hits, "invalid": zero_board.invalid},
        "few_shot": {"hits": few_board.hits, "invalid": few_board.invalid},
        "extra_input_tokens_per_call": round(per_call, 1),
    })

    # TODO 6. Read the comparison table and answer four questions in
    # DECISIONS.md. The table is the deliverable, not the two runs.
    #
    #   a. Which fields moved, and which did not move at all? Do not report
    #      one overall number. The interesting content is that they do not
    #      move together.
    #
    #   b. Did any field get WORSE? If one did, say which and diagnose it.
    #      This is the most valuable observation available today and it is
    #      the one students skip past looking for a win.
    #
    #   c. Did an error disappear, or did it change shape? A wrong label that
    #      became a different wrong label is not a fix. Look at the failure
    #      lines, not just the counts.
    #
    #   d. Would you ship the few-shot variant? Give the evidence, the token
    #      cost per thousand calls, and one sentence saying what would change
    #      your mind. "It scored higher" is not sufficient on ten records,
    #      and saying so is worth more marks than claiming a win.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
