"""Block 4. What one call costs, in the three currencies that matter here.

    python 03_cost.py

You are running locally, so nothing you do today costs money. That is
convenient and it is also a distortion, because in any job you take,
somebody watches the bill. So this block measures the two costs that are
real on your machine, and estimates the one that is not.

  seconds   measured, and it is dominated by how much the model writes
  memory    measured, and it decides which model you can run at all
  euros     estimated from a dated price list, and labeled as an estimate

Two TODO markers.
"""

from __future__ import annotations

import subprocess
import time

from openai import OpenAI

from project.models import BASE_URL, API_KEY, LARGE, SMALL
from project.prices import PRICE_DATE, estimate, local_cost_note
from project.trace import write_json

SHORT = "What is the capital of Luxembourg? Answer in one word."
LONG = ("A resident asks whether they need a parking vignette if they park "
        "in a visitor bay. Explain what information you would need before "
        "answering, and why.")


def timed(client, prompt: str, model: str, max_tokens: int = 200):
    t0 = time.perf_counter()
    reply = client.chat.completions.create(
        model=model, temperature=0.0, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}])
    return reply, time.perf_counter() - t0


def main() -> int:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    rows = []

    # Cost one, seconds. Two prompts, same model, same settings, and the
    # only thing that changes is how much the model has to write.
    for label, prompt in (("short", SHORT), ("long", LONG)):
        reply, secs = timed(client, prompt, SMALL.name)
        rows.append({
            "case": label, "model": SMALL.name, "seconds": round(secs, 3),
            "prompt_tokens": reply.usage.prompt_tokens,
            "completion_tokens": reply.usage.completion_tokens,
        })
        print(f"{label:<6} {secs:>6.2f}s  "
              f"in {reply.usage.prompt_tokens:>4} "
              f"out {reply.usage.completion_tokens:>4}")

    ratio = rows[1]["seconds"] / max(rows[0]["seconds"], 1e-9)
    print(f"\nThe long answer took {ratio:.0f} times as long as the short "
          f"one.\nCompare that with the ratio of their output tokens.\n")

    # TODO 7. Measure the cold start, which is the number the recording
    # deliberately leaves out and the largest one you will see today.
    #
    #   1. Free the model from memory:
    #        subprocess.run(["ollama", "stop", SMALL.name])
    #   2. Time one call, exactly as `timed` does above.
    #   3. Time a second, identical call.
    #
    #   Record both. The first includes loading several gigabytes from disk,
    #   the second does not.
    #
    #   Then answer, in DECISIONS.md: your system will call two different
    #   models. What does this measurement tell you about switching between
    #   them inside one request, and what would you do instead?
    subprocess.run(["ollama", "stop", SMALL.name])
    cold_reply, cold_secs = timed(client, SHORT, SMALL.name)
    warm_reply, warm_secs = timed(client, SHORT, SMALL.name)
    cold_ratio = cold_secs / max(warm_secs, 1e-9)
    print(f"cold call: {cold_secs:.2f}s")
    print(f"warm call: {warm_secs:.2f}s")
    print(f"cold/warm ratio: {cold_ratio:.2f}x")
    

    # TODO 8. Estimate what a real evaluation run would cost hosted.
    #
    #   In week 10 you build a golden set and run it. Assume 200 cases, each
    #   costing what your `long` case above cost in tokens, run once a night
    #   for the fourteen weeks of this course.
    #
    #   Use project.prices.estimate(input_tokens, output_tokens, tier=...)
    #   and compute it on the "small" tier and on the "large" tier.
    #
    #   Print both, then write the two numbers in DECISIONS.md next to one
    #   sentence: which tier would you run nightly, which would you run
    #   before a release, and why not the same one for both.
    #
    #   Label them as estimates. They are not measurements and the price
    #   list is dated {PRICE_DATE}.

    # The golden set will contain 200 test cases.
    cases = 200

    # We run the evaluation once every night for 14 weeks.
    # 14 weeks * 7 nights = 98 runs.
    nights = 14 * 7


    # rows[1] is the long case.
    # Get its number of input tokens.
    input_tokens = rows[1]["prompt_tokens"]

    # Get its number of output tokens.
    output_tokens = rows[1]["completion_tokens"]


    # Estimate the cost of running 200 cases once
    # using the small tier.
    small_one = estimate(
        input_tokens * cases,
        output_tokens * cases,
        tier="small"
    )


    # Estimate the cost of running 200 cases once
    # using the large tier.
    large_one = estimate(
        input_tokens * cases,
        output_tokens * cases,
        tier="large"
    )


    # Estimate the total cost of running the 200 cases
    # every night for 14 weeks using the small tier.
    small_semester = estimate(
        input_tokens * cases * nights,
        output_tokens * cases * nights,
        tier="small"
    )


    # Estimate the total cost of running the 200 cases
    # every night for 14 weeks using the large tier.
    large_semester = estimate(
        input_tokens * cases * nights,
        output_tokens * cases * nights,
        tier="large"
    )


    # Print the estimated cost for one 200-case run
    # using the small tier.
    print(
        f"Small tier, one 200-case run: "
        f"{small_one.total:.5f} EUR"
    )

    # Print the estimated small-tier cost for
    # nightly runs over 14 weeks.
    print(
        f"Small tier, nightly for 14 weeks: "
        f"{small_semester.total:.5f} EUR"
    )

    # Print the estimated cost for one 200-case run
    # using the large tier.
    print(
        f"Large tier, one 200-case run: "
        f"{large_one.total:.5f} EUR"
    )

    # Print the estimated large-tier cost for
    # nightly runs over 14 weeks.
    print(
        f"Large tier, nightly for 14 weeks: "
        f"{large_semester.total:.5f} EUR"
    )

    # The euro values come from the course price list.
    # They are estimates, not actual money spent.
    print(
        f"Price list date: {PRICE_DATE}. "
        "Estimates, not measurements."
    )

    write_json("artifacts/week01_cost.json",
               {"rows": rows, "price_list_date": PRICE_DATE})
    print(local_cost_note())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
