"""The classifier and the policy layer. TODO 2 and 3.

Two calls per request in the routed system: one to decide, one to answer.
The first is cheap and its output is inspectable. The second is the work.

The policy layer between them is about three lines of code and three design
decisions, and the decisions are where the marks are.
"""

from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from routes import ROUTES, SPECIALISTS, SYSTEM_ROUTER

from project.models import BASE_URL, API_KEY, SMALL


class Decision(BaseModel):
    route: Literal["request", "info", "status", "complaint", "other"]
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(max_length=200)


class Routed(BaseModel):
    """What the policy layer decided, and why."""

    decision: Decision
    applied_route: str
    policy_fired: str | None = None      # None means the decision stood
    evidence_ok: bool = True


# --------------------------------------------------------------------------
# TODO 2. The classifying call.
# --------------------------------------------------------------------------

def classify(client, text: str, model: str = SMALL.name,
             temperature: float = 0.0) -> tuple[Decision | None, dict]:
    """One cheap call whose only job is to pick a route.

    Build it the same way as week 2's extractor: a schema-constrained call
    with SYSTEM_ROUTER as the system message and `text` as the user message.
    Return (Decision or None, meta), where meta carries seconds,
    prompt_tokens, completion_tokens, and the raw string.

    Return None rather than raising when validation fails. You need to be
    able to count how often that happens, and an exception is not a count.

    Note what this call does not get: no tools, no reference material, and
    no instruction about how to answer. It decides and it stops. That is
    what makes it cheap enough to be worth adding, and it is what makes its
    output inspectable.
    """
       # Start a timer so we can measure how long the model call takes.
    t0 = time.perf_counter()

    # Send the message to the model and ask it to classify the route.
    reply = client.chat.completions.create(

        # Use the model passed into this function.
        model=model,

        # Use the temperature passed into this function.
        temperature=temperature,

        # Limit how many tokens the model can generate.
        max_tokens=200,

        # Give the model the router instructions and the user's message.
        messages=[
            # The system message contains our route definitions and rules.
            {"role": "system", "content": SYSTEM_ROUTER},

            # The user message is the help desk message we want to classify.
            {"role": "user", "content": text},
        ],

        # Force the model to return JSON that matches the Decision class.
        response_format={
            "type": "json_schema",

            # Describe the JSON structure we expect.
            "json_schema": {
                # Give this schema a simple name.
                "name": "decision",

                # Build the schema from our Decision class above.
                "schema": Decision.model_json_schema(),
            },
        },
    )

    # Get the text returned by the model.
    # If the model returned nothing, use an empty string instead.
    raw = reply.choices[0].message.content or ""

    # Save useful information about this model call.
    meta = {

        # How many seconds the call took.
        "seconds": time.perf_counter() - t0,

        # How many input tokens were sent to the model.
        "prompt_tokens": reply.usage.prompt_tokens,

        # How many output tokens the model generated.
        "completion_tokens": reply.usage.completion_tokens,

        # Save the original model output so we can inspect it later.
        "raw": raw,
    }

    # Try to turn the model's JSON into a valid Decision object.
    try:
        decision = Decision.model_validate_json(raw)

    # If the JSON is invalid, do not crash the program.
    except ValidationError:
        decision = None

    # Return both the decision and the information about the model call.
    return decision, meta

    # Original lecturer TODO marker kept for reference.
    # raise NotImplementedError("TODO 2: the classifying call")


# --------------------------------------------------------------------------
# TODO 3. The policy layer.
# --------------------------------------------------------------------------

# TODO 3a. Pick a number, but look at the distribution before you pick it.
#
# Choosing a threshold because 0.7 sounds reasonable is the mistake this
# exercise exists to catch. Run the classifier over the twenty four queries
# first, print the confidences, and then decide. On one of the two course
# models the answer will surprise you.

# I chose 0.5 after looking at the confidence values.
# It separates the one 0.0 confidence result from all the 0.99+ results.
CONFIDENCE_FLOOR = 0.5

# TODO 3b. Where does anything the policy rejects go?
#
# Not every route is equally safe to be wrong into. Ask what each specialist
# DOES on the sender's behalf, and pick the one whose actions are easiest to
# undo. One of the five logs a ticket, one escalates to a human, and one
# only answers. That should decide it.

# I chose info because it only gives an answer and does not create or escalate anything.
SAFE_DEFAULT = "info"


def apply_policy(decision: Decision | None, text: str) -> Routed:
    """Take a Decision and return what will actually happen.

    Three checks. Each one is a design decision that goes in DECISIONS.md
    with a reason.

    1. The call produced no valid decision at all. Rare, and it still has to
       be handled, because the alternative is a crash on the one message
       unusual enough to break the schema.

    2. The evidence check, inherited from week 2 and still free. Is the
       evidence span actually in `text`? A router that invents its
       justification is a router you cannot audit. Note that this checks
       honesty, not correctness: a route can be right with fabricated
       evidence, and that is still a defect, because the evidence is what a
       human reviewing a misroute will read.

    3. The confidence floor from TODO 3a.

    Set `policy_fired` to a short string naming which check fired, or leave
    it None when the decision stood. You will count these at the checkpoint,
    and "the policy fired sometimes" is not a count.
    """
        # Check if the classifier did not return a valid decision.
    if decision is None:

        # Create a simple fallback decision because Routed needs a Decision object.
        fallback = Decision(
            route=SAFE_DEFAULT,
            confidence=0.0,
            evidence=""
        )

        # Send the message to the safe default route.
        return Routed(
            decision=fallback,
            applied_route=SAFE_DEFAULT,
            policy_fired="invalid",
            evidence_ok=False
        )

    # Check if the evidence is copied exactly from the original message.
    evidence_ok = decision.evidence in text

    # If the evidence is not really in the message, use the safe default.
    if not evidence_ok:
        return Routed(
            decision=decision,
            applied_route=SAFE_DEFAULT,
            policy_fired="evidence",
            evidence_ok=False
        )

    # Check if the model's confidence is below our chosen confidence floor.
    if decision.confidence < CONFIDENCE_FLOOR:
        return Routed(
            decision=decision,
            applied_route=SAFE_DEFAULT,
            policy_fired="confidence",
            evidence_ok=True
        )

    # If all checks pass, keep the route chosen by the classifier.
    return Routed(
        decision=decision,
        applied_route=decision.route,
        policy_fired=None,
        evidence_ok=True
    )

    # Original lecturer TODO marker kept for reference.
    # raise NotImplementedError("TODO 3: the policy layer")

# --------------------------------------------------------------------------
# Given. The answering call.
# --------------------------------------------------------------------------

def respond(client, system: str, text: str,
            model: str = SMALL.name) -> tuple[str, dict]:
    t0 = time.perf_counter()
    reply = client.chat.completions.create(
        model=model, temperature=0.0, max_tokens=250,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": text}])
    return reply.choices[0].message.content, {
        "seconds": time.perf_counter() - t0,
        "prompt_tokens": reply.usage.prompt_tokens,
        "completion_tokens": reply.usage.completion_tokens,
    }
