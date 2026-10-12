# Week 1: the stack, the first call, and what it costs

Copy this into your `DECISIONS.md` and fill it in. Keep the headings. In
week 13 this becomes a section of your project report that you do not have
to write.

---

## Week 1

**Run conditions.** Everything below was produced on:

- machine: [MacBook Air 15 inch , Apple M2, 16 GB RAM]
- model: [qwen3:4b-instruct]
- served by: Ollama, one request at a time, locally
- date: [ first call 2026-09-16 ; variance and cost 2026-09-27]

Every number in this file is meaningless without those four lines, so they
are stated once here and referred to rather than repeated.

### 1. Machine and model set

I am running the required model set plus the optional qwen2.5:7b  and qwen3-vl:4b  model . qwen3-vl:4b vision model is  installed on 2026-09-28 .

### 2. The first call

| | |
| finish reason | stop |
| prompt tokens |24 |
| completion tokens | 45|
| elapsed | 1.67s|

One sentence on the finish reason: what my program would do differently if
it came back as a truncation rather than a normal stop.

The finish reason was `stop`, which means the model completed its response normally.
If the finish reason indicated truncation, my program could detect that the response
was incomplete and handle it differently instead of treating it as a complete answer.



### 3. Variance

| cell | distinct (recording) | distinct (mine) | median latency |
| closed_short, t=0.0 | 1/12 | 1/6|0.11 s|
| closed_short, t=1.0 | 1/12 | 1/6|0.11 s|
| open_list, t=0.0 | 1/12 | 1/6|1.19 s|
| open_list, t=1.0 | 11/12 |6/6 |1.25 s|

Which cell still returns a single answer at temperature 1.0, and why that
one:

[closed_short still returned one distinct answer at temperature 1.0 because the prompt is highly constrained because it asks for the capital of Luxembourg in one word so there was almost no room for the model to give different answers ]

Which cells a test asserting exact string equality would pass on, and what
that tells me about testing this system:

[Exact string equality worked for closed_short at both temperatures and for open_list at temperature 0.0 in my tests. However, it did not work for open_list at temperature 1.0 because the answers were different even though they were still valid. This shows that exact string equality is better when the answer is fixed and predictable, but it may not work well when there can be different correct answers.]

**The sentence that carries into week 10.** [I can rely on repeated output
more when the prompt is limited or the temperature is 0.0, but I cannot
always rely on it for open prompts at a higher temperature.]

### 4. The cold start

- cold call: [ 1.05] s
- warm call: [0.11 ] s
- ratio: [ 9.30 x]

What this implies for a system that uses more than one model, and what I
will do about it:

[The cold call was much slower because the model had to be loaded into memory first . For a system that uses more than one model , switching between models  too often  could make the system slower because a model may need to be loaded before it can answer . I would try to choose the model before starting the task and avoid switching between models many times inside one request]

### 5. Cost, estimated

A 200-case golden set, at the token cost of my long case:

| | one run | nightly for the semester |
| small tier |0.03352 EUR  | 3.28496 EUR|
| large tier | 2.49120 EUR| 244.13760 EUR|

Estimates against the price list dated  2026-08-10, not
measurements.Running locally, my actual monetary cost was zero.

Which tier I would run nightly, which I would run before a release, and why
not the same one for both:

[I would run the small tier nightly because it is much cheaper. I would use
the large tier before a release for an important final evaluation. I would
not use the large tier every night because the estimated cost is much higher.]

### Deferred

[I ran `02_variance.py --full`, but the provided starter code still produced only four live cells instead of the eight cells described in the homework. I left the starter code unchanged.]
# Week 2: a structured-output extractor, measured

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 2

**Run conditions.** model: [qwen3:4b-instruct] ] | temperature: 0.0 | prompt version: [ week02-zero-shot-v1] |
served locally | date: [2026-10-12] | scored on: [ my own machine]

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: [ use None, which becomes null in JSON]
- due_date, when the message states only a relative expression: [ use None and do not calculate a calendar date]
- quote, and what "verbatim" means in my scorer: [ the quote must appear exactly in the original message without changing, translating, or normalizing it]
- what my scorer does with a record that failed validation: [counts it as invalid and counts all four fields as wrong ]

[One sentence on why the last one matters. A scorer that skips the records
it could not parse reports a number that improves as the model gets worse.]

[This matters because if failed records were skipped, the reported score
could look better even though the model was producing more invalid outputs.]


### 2. Zero-shot, per field

| field | correct | of |
| category |10 | 10 |
| urgency |9 | 10 |
| due_date |6 | 10 |
| quote |8 | 10 |
| invalid records |0 | 10 |

My prediction, written before block 3: examples will help most on [ due_date]
because [ most of the zero-shot errors were due_date errors. The model sometimes created a date from a relative expression or returned the string "null" instead of the null value].

### 3. Few-shot

Examples chosen, and the job each one does:

| example | why it is in the block | field it should move |
| EX-02 | French facilities example with urgent behavior and no calendar date | category / due_date |
| EX-04 | Shows that a relative expression such as "next week" should still produce null | due_date / urgency |
| EX-05 | Shows a real French calendar date converted to ISO format | due_date |
| EX-01 | Shows an access request with no deadline and standard urgency | due_date / urgency |

| field | zero-shot | few-shot | move |
| category | 10/10 | 10/10 | 0 |
| urgency | 9/10 | 10/10 | +1 |
| due_date | 6/10 | 7/10 | +1 |
| quote | 8/10 | 6/10 | -2 |

[My prediction was partly correct. due_date improved from 6/10 to 7/10,
but urgency also improved from 9/10 to 10/10. The quote field became worse,
dropping from 8/10 to 6/10.]

### 4. What got worse

[Name the field, if any, and diagnose it. If nothing got worse, say so and
say how you checked. Then look at the failure lines rather than the counts,
and say whether any error disappeared or merely changed shape. A wrong label
that became a different wrong label has not been fixed.]

[The quote field got worse, decreasing from 8/10 in zero-shot to 6/10
in few-shot. REQ-03 and REQ-05 became new quote failures, while the quote
errors on REQ-04 and REQ-06 were still present. The failed quotes contained
changed, truncated, or added text, so they were no longer exact substrings
of the original messages.

Some errors really disappeared: the urgency error on REQ-02 was fixed, and
the due_date error on REQ-08 was fixed. Other errors only changed shape.
For example, REQ-01 changed from an invented date of 2023-10-10 to another
invented date of 2024-04-15. REQ-05 changed from the string "null" to the
invented date 2024-12-31. REQ-10 remained wrong with 2024-12-31.]

### 5. What the examples cost

- extra input tokens per call: [ 364]
- per thousand calls: [ 364000]
- estimated euros per thousand calls on the small tier: [0.0728 EUR ], against the
  price list dated [2026-08-10 ]. Estimate, not a measurement.

### 6. Ship it or not

[Which variant, on what evidence, and what would change your mind. Ten
records is not enough to be confident and saying so is worth more than
claiming a win. If your answer is "keep one example and drop the rest", say
which one and why.]

[I would not ship the few-shot variant in its current form. It improved
urgency from 9/10 to 10/10 and due_date from 6/10 to 7/10, but quote
accuracy decreased from 8/10 to 6/10 and the examples add 364 input tokens
to every call. The evaluation also contains only ten records, which is too
small to be confident that the improvements will generalize. I would change
my mind if a revised example block kept the urgency and due_date improvements
without reducing quote accuracy, and the result held on a larger evaluation
set.]

### Sensitivity variant

Variant assigned: [role]. What I changed: [prepended "You are a senior service desk analyst." to the few-shot system prompt]. What moved: [nothing; all four field scores stayed the same].

[My prediction was correct. I predicted that the role sentence would make little or no difference because the task already has fixed labels, a structured schema, and explicit instructions. In the live run, category stayed 10/10, urgency stayed 10/10, due_date stayed 7/10, and quote stayed 6/10. The per-language field-error counts also did not change.]

### The gold set

Ten cases written to `artifacts/goldset.json`, tagged by language.

One thing my scorer cannot currently detect:

[This is the most valuable line on the page. An example: "our scorer cannot
tell a correctly formatted date that is simply the wrong date from a
correctly extracted one, because it only compares strings."]


[The quote scorer can check that the quote is an exact substring of the
original message, but it cannot tell whether that substring actually
supports the urgency decision.]

### Deferred

[Nothing from the required Week 2 work was deferred.]
