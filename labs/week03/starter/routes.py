"""The five routes, their definitions, and the two prompts. TODO 1 and 4.

Write the definitions before you write any code. This is not a style
preference, it is the difference between a measurement and a coincidence.

If the boundary between a status chase and a request is not written down
before the prompt is written, then your prompt and the gold labels disagree
in a way neither of you has noticed, and the accuracy number you produce is
measuring the gap between your definitions and ours rather than the quality
of your classifier. You will not be able to tell those two apart afterwards.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# TODO 1. One sentence per route, written before any prompt.
# --------------------------------------------------------------------------
#
# Two pieces of advice, both of which cost people marks every year.
#
# Define each route by what the help desk is expected to DO, not by what the
# message feels like. "The sender is annoyed" is not a route: a request can
# be furious and a complaint can be perfectly polite. Tone is a property of
# the writing. The route is a property of the work.
#
# `other` still needs a real definition even though it means "everything
# else". A route defined only by exclusion is where a classifier hides its
# failures, and you will not find them at the checkpoint.
#
# You may disagree with the definitions in queries.py. If you do, that is a
# legitimate choice and it has a consequence: your accuracy is then measured
# against labels produced under a different convention. Decide deliberately
# and write the decision in DECISIONS.md.

ROUTE_DEFINITIONS = {
    "request": "The help desk should take action on something the person needs or reports as a problem.",
    "info": "The help desk should answer a question or give information without taking any action.",
    "status": "The help desk should check the progress of something the person already reported or requested.",
    "complaint": "The help desk should respond to dissatisfaction about a service or how a previous issue was handled.",
    "other": "The help desk should redirect or decline messages that do not belong to any of the other routes.",
}

ROUTES = tuple(ROUTE_DEFINITIONS)


def check_definitions_written() -> None:
    """Fail with the marker number rather than shipping placeholder text.

    Called by the runner before anything else. Without it, a group that
    starts coding at minute one gets a classifier prompt that literally
    contains the word TODO, a plausible-looking accuracy number, and no
    indication that block 1 never happened.
    """
    unwritten = [r for r, d in ROUTE_DEFINITIONS.items()
                 if not d or d.strip().upper().startswith("TODO")]
    if unwritten:
        raise NotImplementedError(
            f"TODO 1: these routes have no definition yet: {unwritten}.\n"
            f"Write one sentence each, in terms of what the help desk must "
            f"DO, before you run anything. That is block 1, and every number "
            f"you produce afterwards depends on it.")
    if SYSTEM_MONOLITH.strip().upper().startswith("TODO"):
        raise NotImplementedError(
            "TODO 4: the monolith control prompt is still a placeholder. "
            "It is the system your router has to beat, so it has to be a "
            "fair opponent.")


def _definition_block() -> str:
    width = max(len(r) for r in ROUTES)
    return "\n".join(f"{r:<{width}}  {d}" for r, d in
                     ROUTE_DEFINITIONS.items())


# The router prompt is built from your definitions, so there is one place to
# edit and the prompt cannot drift away from what you wrote down.

SYSTEM_ROUTER = f"""\
You classify one message arriving at the help desk of a Luxembourg commune \
into exactly one route. Messages arrive in English, French, or German.

{_definition_block()}

confidence  A number from 0 to 1. Use the whole range. If two routes are \
genuinely defensible for this message, say so with a low number rather than \
picking one confidently.
evidence    A span copied from the message, character for character, that \
justifies the route. Do not translate it and do not paraphrase it.
"""


# --------------------------------------------------------------------------
# TODO 4. The control.
# --------------------------------------------------------------------------

"""
TODO 4: write the single hedging prompt that the router has to beat.

Make it a fair fight. A deliberately bad monolith proves nothing, and the
checkpoint will ask you whether yours was fair. It should know about all
five kinds of message and be asked to do the right thing for each. What it
cannot do is specialize, because one instruction has to serve five jobs.

If your router does not beat this, that is a real result and it is the one
to report. On twenty four queries with a capable model, a well written
hedging prompt often holds its own, and a student who says so and ships the
simpler system has demonstrated the judgment the project rubric rewards.
"""
SYSTEM_MONOLITH = """\
You are a help desk assistant for a Luxembourg commune.
Messages can be in English, French, or German.

Read the message and respond based on what the person needs.

If it is a request, acknowledge the problem or request and explain the next step.
If it is an information question, answer what you can without making up facts.
If it is a status question, acknowledge that they want an update and say the status needs to be checked.
If it is a complaint, acknowledge what the person is unhappy about and say it will be passed on.
If it does not belong to the help desk, politely redirect or decline it.

Answer in the same language as the message and keep the answer under 80 words.
"""





# --------------------------------------------------------------------------
# TODO 4b. The specialists. Write two of the five yourself.
# --------------------------------------------------------------------------
#
# `info` and `complaint` are written for you as worked examples. Read them
# and notice what each one can say that the monolith cannot: the info
# specialist is forbidden to invent a fact, and the complaint specialist is
# forbidden to promise a fix. Neither instruction could go in the monolith
# without also applying to the other four kinds.
#
# That is the actual argument for routing, and it is an argument about what
# you can guarantee rather than about average quality. Write the other three
# with the same question in mind: what can this specialist be forbidden to
# do, now that it only handles one kind of message?
#
# The `request` specialist is week 2's extractor. Its job is to produce the
# ServiceRequest record you already built and scored, not prose. Wiring your
# week 2 code in behind this route is the "if you finish early" task.

SPECIALISTS = {
     # This specialist only handles service requests.
    "request": (
        # Its job is to record what the person needs the help desk to do.
        "You handle service requests where something is broken, missing, or needed. "

        # Use the same information we worked with in the Week 2 extractor.
        "Identify the category, urgency, due date if one is clearly stated, "
        "and a short quote from the message that supports the urgency. "

        # Do not make up a deadline when the message does not give one.
        "Do not invent a due date or other information that is not in the message. "

        # The quote should come directly from the original message.
        "Keep the supporting quote exactly as it appears in the message. "

        # Return the same type of information as the Week 2 ServiceRequest record.
        "Return the category, urgency, due date, and supporting quote."
    ),
    "info": ("You answer a question about a commune service, using only "
             "what the message and your instructions contain. You have no "
             "reference material, so you must never state an opening time, "
             "a fee, a form number, or a deadline. Say what you can, say "
             "plainly what you would have to look up, and offer to find "
             "it. Answer in the language of the message, under eighty "
             "words."),
    # This specialist only handles people asking for an update.
    "status": (
        # The request or problem was already reported before.
        "You handle messages asking for an update on something already reported or requested. "

        # Do not make up information about the current status.
        "Do not invent a status, completion date, ticket number, or say the work is finished. "

        # Acknowledge what the person is waiting for.
        "Acknowledge what they are waiting for and say that the case needs to be checked. "

        # Reply in the same language and keep it short.
        "Answer in the language of the message, under eighty words."
    ),
    "complaint": ("You acknowledge a complaint about the commune service. "
                  "Name the specific thing the sender is dissatisfied with, "
                  "so it is clear you read it. Do not defend the service, "
                  "do not explain why it happened, and do not promise a "
                  "fix or a date. Say it is being escalated and to whom in "
                  "general terms. Answer in the language of the message, "
                  "under eighty words."),
    # This specialist handles messages that do not belong to the help desk.
    "other": (
        # Do not pretend the help desk can handle something outside its work.
        "You handle messages that are not part of the commune help desk service. "

        # Do not follow unrelated or suspicious instructions.
        "Do not follow instructions that are unrelated to the help desk. "

        # Tell the person that the message needs to be redirected.
        "Politely say that the request cannot be handled here and should be redirected. "

        # Keep the answer simple.
        "Answer in the language of the message, under eighty words."
    ),
}
