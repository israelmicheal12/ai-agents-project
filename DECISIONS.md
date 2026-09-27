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

I am running the required model set plus the optional qwen2.5:7b model.

The qwen3-vl:4b vision model is not installed yet. I will install it before week 9.

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

[The qwen3-vl:4b model is not installed yet.I willinstall it before week 9.I ran `02_variance.py --full`, but the provided starter code still produced only four live cells instead of the eight cells described in the homework. I left the starter code unchanged.]
