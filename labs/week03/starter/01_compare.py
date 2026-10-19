"""Blocks 2 and 3, completed. The control and the treatment, in one script.

TODO 6 and TODO 7. The written answers are at the bottom of the file.

Both systems run here on purpose. A comparison that lives in two scripts
becomes two demonstrations, and by the time you have run them separately the
conditions have drifted and you no longer know what you compared.
"""
# Load the gold set that we already created in Week 2.

from __future__ import annotations

import argparse

# We use this to load the Week 2 extractor file.
import importlib.util

# We use Path to find the Week 2 extractor from this file.
from pathlib import Path
# We use this to register the dynamically loaded Week 2 module.
import sys

from queries import QUERIES
from router import apply_policy, classify, respond
from routes import (SPECIALISTS, SYSTEM_MONOLITH,
                    check_definitions_written)
from scoring import report, score_routes

from project.contracts import GoldCase, GoldSet
from project.fixtures import ReplayClient, load_or_reference
from project.models import BASE_URL, API_KEY, SMALL
from project.trace import TraceRecorder, local_conditions, write_json

LAB = "week03_routing_and_composition"

# Find the Week 2 extractor file.
WEEK2_EXTRACTOR_PATH = (
    Path(__file__).parents[2]
    / "week02"
    / "starter"
    / "extractor.py"
)

# Load the Week 2 extractor as a Python module.
week2_spec = importlib.util.spec_from_file_location(
    "week2_extractor",
    WEEK2_EXTRACTOR_PATH
)

# Create the module object.
week2_extractor = importlib.util.module_from_spec(week2_spec)

# Register the module so Pydantic can resolve its type annotations.
sys.modules["week2_extractor"] = week2_extractor

# Run the Week 2 extractor file so we can use its functions.
week2_spec.loader.exec_module(week2_extractor)

def get_client(replay: bool):
    if replay:
        client = ReplayClient.from_lab(LAB)
        print(f"replay: {client.describe()}\n")
        return client
    from openai import OpenAI
    return OpenAI(base_url=BASE_URL, api_key=API_KEY)


def run_monolith(client, model=SMALL.name):
    """The control. One call per query, one prompt for all five kinds."""
    metas = []
    for q in QUERIES:
        rec = TraceRecorder(
            week=3, case_id=q.id,
            conditions=local_conditions(model, temperature=0.0,
                                        system="monolith", language=q.lang),
            user_input=q.text)
        with rec.step("model", model) as step:
            answer, meta = respond(client, SYSTEM_MONOLITH, q.text, model)
            step.tokens(meta["prompt_tokens"], meta["completion_tokens"])
        rec.finish(output=answer, outcome="ok")
        metas.append(meta)
    return metas


def run_router(client, model=SMALL.name):
    """The treatment. Two calls per query, and a policy layer between them."""
    routed_all, metas_c, metas_a = [], [], []
    for q in QUERIES:
        rec = TraceRecorder(
            week=3, case_id=q.id,
            conditions=local_conditions(model, temperature=0.0,
                                        system="router", language=q.lang),
            user_input=q.text)

        with rec.step("model", f"{model}:classify") as step:
            decision, meta_c = classify(client, q.text, model)
            step.tokens(meta_c["prompt_tokens"], meta_c["completion_tokens"])
            step.detail(route=decision.route if decision else None,
                        confidence=decision.confidence if decision else None)

        routed = apply_policy(decision, q.text)
        # Record what the policy layer decided.
        with rec.step("check", "policy") as step:

            # Save the final route and whether any policy rule changed it.
            step.detail(
                applied_route=routed.applied_route,
                policy_fired=routed.policy_fired,
                evidence_ok=routed.evidence_ok
            )

        # The request route uses the validated Week 2 extractor.
        if routed.applied_route == "request":

            # Record this step as an extraction call.
            with rec.step("model", f"{model}:extract") as step:

                # Run the same structured extractor that we built in Week 2.
                request_record, meta_a = week2_extractor.extract(
                    client,
                    week2_extractor.SYSTEM_ZERO_SHOT,
                    q.text,
                    model
                )

                # Record how many tokens the extraction used.
                step.tokens(
                    meta_a["prompt_tokens"],
                    meta_a["completion_tokens"]
                )

            # If validation failed, keep the raw output and mark the trace as an error.
            if request_record is None:
                answer = meta_a["raw"]
                answer_outcome = "error"

            # Otherwise, save the validated ServiceRequest as JSON.
            else:
                answer = request_record.model_dump_json()
                answer_outcome = "ok"

        # The other four routes still use their normal Week 3 specialists.
        else:

            # Record this step as a normal response call.
            with rec.step("model", f"{model}:respond") as step:

                # Use the specialist prompt for the selected route.
                answer, meta_a = respond(
                    client,
                    SPECIALISTS[routed.applied_route],
                    q.text,
                    model
                )

                # Record the tokens used by the specialist.
                step.tokens(
                    meta_a["prompt_tokens"],
                    meta_a["completion_tokens"]
                )

            # A normal specialist response is considered successful.
            answer_outcome = "ok"

        # Finish the trace with the output from the chosen specialist.
        rec.finish(
            output=answer,
            outcome=answer_outcome,
            applied_route=routed.applied_route,
            policy_fired=routed.policy_fired
        )
        routed_all.append(routed)
        metas_c.append(meta_c)
        metas_a.append(meta_a)
    return routed_all, metas_c, metas_a


def totals(*meta_lists):
    tok = sum(m["prompt_tokens"] + m["completion_tokens"]
              for ms in meta_lists for m in ms)
    secs = sum(m["seconds"] for ms in meta_lists for m in ms)
    return tok, secs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--model", default=SMALL.name)
    args = ap.parse_args()

    check_definitions_written()      # block 1 before block 2
    client = get_client(args.replay)

    mono_metas = run_monolith(client, args.model)
    routed, metas_c, metas_a = run_router(client, args.model)

    s = score_routes(routed, QUERIES)
    print(report(s, "router"))

    m_tok, m_secs = totals(mono_metas)
    r_tok, r_secs = totals(metas_c, metas_a)
    c_tok, _ = totals(metas_c)
    print(f"\n{'':<12}{'tokens':>10}{'seconds':>10}")
    print(f"{'monolith':<12}{m_tok:>10}{m_secs:>10.1f}")
    print(f"{'router':<12}{r_tok:>10}{r_secs:>10.1f}")
    print(f"  of which the routing call: {c_tok} tokens, "
          f"{c_tok / r_tok * 100:.0f} per cent of the routed total")

    write_json("artifacts/week03_routing.json", {
        "model": args.model,
        "router_hits": s.hits, "total": s.total,
        "unambiguous": [s.unambiguous_hits, s.unambiguous_total],
        "per_route": s.per_route,
        "confusion": {f"{g}->{p}": n for (g, p), n in s.confusion.items()},
        "policy_fired": dict(s.policy_fired),
        "evidence_ok": s.evidence_ok,
        "monolith_tokens": m_tok, "router_tokens": r_tok,
        "routing_call_tokens": c_tok,
    })

    # TODO 6. Grow the gold set.
    #
    #   Week 2 wrote ten extraction cases to artifacts/goldset.json. Add the
    #   twenty four routing cases to the SAME file rather than starting a
    #   second one. Week 10 builds one harness over one gold set, and a
    #   system with two gold sets has two definitions of correct.
    #
    #   Load it with project.fixtures.load_or_reference, which hands you the
    #   reference copy if you do not have your own yet. Print which you got,
    #   and if it says 'reference', record that in DECISIONS.md.
    #
    #   For each query, a GoldCase with week_added=3, expected={"route": ...},
    #   an expected_behavior sentence, and slice_tags carrying the language,
    #   the route, and the tag "ambiguous" for the four that have no correct
    #   answer.
    #
    #   That last tag matters. Those four cases have only a documented
    #   convention, and tagging them lets week 10 report them as their own
    #   slice instead of counting them as failures. A gold set that pretends
    #   every case has one right answer will misreport the four cases you
    #   understand best.
    #
    #   Skip any case_id already in the file, so this is safe to re-run.

    # Load the gold set that we already created in Week 2.
    gold_data, gold_source = load_or_reference(
        "goldset.json",
        LAB
    )

    # Show whether we loaded our own gold set or the lecturer's reference copy.
    print(f"\ngold set source: {gold_source}")

    # Turn the loaded JSON data into a validated GoldSet object.
    goldset = GoldSet.model_validate(gold_data)

    # Save all case IDs that are already in the gold set.
    # This prevents duplicates if we run this file again.
    existing_ids = {
        case.case_id
        for case in goldset.cases
    }

    # Go through all 24 Week 3 routing queries.
    for q in QUERIES:

        # Skip this query if it is already in the gold set.
        if q.id in existing_ids:
            continue

        # Every case should record its language and expected route.
        tags = [
            q.lang,
            q.route,
        ]

        # Mark the four cases where more than one route is reasonable.
        if q.ambiguous:
            tags.append("ambiguous")

        # Write a simple sentence describing the expected behavior.
        if q.ambiguous:
            expected_behavior = (
                f"Routes this message to {q.route} using the documented "
                "ambiguity convention."
            )
        else:
            expected_behavior = (
                f"Routes this message to {q.route}."
            )

        # Add this Week 3 routing case to the existing gold set.
        goldset.cases.append(
            GoldCase(
                # Keep the same ID used in queries.py.
                case_id=q.id,

                # These cases were added during Week 3.
                week_added=3,

                # Store the original help desk message.
                question=q.text,

                # Store the gold route in the expected result.
                expected={
                    "route": q.route
                },

                # Explain in words what the correct behavior is.
                expected_behavior=expected_behavior,

                # Store useful tags for later evaluation.
                slice_tags=tags,
            )
        )

        # Remember this ID so it cannot be added twice in this run.
        existing_ids.add(q.id)

    # Save the updated gold set back to the same file used in Week 2.
    write_json(
        "artifacts/goldset.json",
        goldset.model_dump(mode="json")
    )

    # Print the final number so we can confirm that it reached 34.
    print(f"gold set now has {len(goldset.cases)} cases")

    # TODO 7. Answer four questions in DECISIONS.md. The comparison is the
    # deliverable, not the two running systems.
    #
    #   a. Name the confusion pairs and say which DIRECTION they point. If
    #      they all point into one route, that route's definition is too
    #      wide, and the fix is the definition rather than the prompt.
    #   b. What fraction of the routed system's tokens is the routing call?
    #      The routed system makes two calls where the monolith makes one,
    #      so it has to buy something with that.
    #   c. What can each specialist be forbidden to do, now that it only
    #      handles one kind of message? Could the monolith be given the same
    #      instruction? That question is the real argument for routing.
    #   d. Would you ship the router, on what evidence, and what would
    #      change your mind? At twenty four queries the accuracy difference
    #      is probably inside the noise, and saying so is worth more than
    #      claiming a win.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
