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
# Week 3: a router in front of the extractor

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 3

**Run conditions.** classifier model: [qwen3:4b-instruct] | answering model: [qwen3:4b-instruct] |
temperature: 0.0 | served locally | date: [2026-10-19] | scored on: [my own machine]

### 1. The five route definitions

| route | definition, one sentence, in terms of what the help desk must do |
| request | The help desk should take action on something the person needs or reports as a problem. |
| info | The help desk should answer a question or give information without taking any action. |
| status | The help desk should check the progress of something the person already reported or requested. |
| complaint | The help desk should respond to dissatisfaction about a service or how a previous issue was handled. |
| other | The help desk should redirect or decline messages that do not belong to any of the other routes. |

My convention for the four ambiguous queries:

[If a message is mainly chasing an earlier request without dissatisfaction, I use status. If it expresses dissatisfaction about how an earlier problem was handled, I use complaint. If it asks a question but also reports a real fault that needs action, I use request.]

Do my definitions match the ones in `queries.py`? [yes]

### 2. The policy layer

Before choosing a threshold, the confidence values I saw were: min [ 0.00],
max [ 1.00], [ 3] distinct values across 24 queries.

- confidence floor: [0.5], because [the results separated into one 0.0 result and the other results near 0.99 or above]
- evidence check: [send the message to the safe default when the evidence is not an exact substring of the original message], because [this checks that the classifier did not invent or paraphrase its evidence]
- safe default: [info], because that specialist [only gives an answer and does not create, change, or escalate something on the sender's behalf]

How often each check fired: below_threshold [1], evidence_not_verbatim [0],
invalid_decision [0].

[The confidence check fired once, but it did not improve routing. The model gave 0.0 confidence to a correct `other` decision, while some incorrect decisions had high confidence. This means the self-reported confidence was not a useful correctness signal in this run.]

### 3. Route accuracy

| route | correct | of |
| request | 6 | 7 |
| info | 5 | 5 |
| status | 4 | 4 |
| complaint | 4 | 4 |
| other | 1 | 4 |

Overall [ 20]/24. Excluding the four ambiguous: [ 17]/20.

Confusion pairs, with direction:

| gold | applied | count |
| other | info | 2 |
| other | complaint | 1 |
| request | status | 1 |

The route carrying most of the error is [other]. The fix is [a definition], because [the current `other` definition is broad and vague, so I would make it clearer that out-of-scope requests, unrelated instructions, and messages meant for another service belong there].
### 4. What routing cost

- monolith: [5917] tokens over 24 queries
- router: [12416] tokens over 24 queries
- the classifying call alone: [7100] tokens, which is [57] per cent of the
  routed total

I predicted that share would be [I did not record a prediction] before measuring it.

[The routing overhead was large. The routed system used 6499 more tokens
than the monolith. After wiring the Week 2 extractor behind the request
route, the classifier still used 7100 tokens, but its share of the routed
total fell to 57% because request handling now uses the structured
ServiceRequest extraction call.]


### 5. What routing bought

One thing a specialist can be forbidden to do that the monolith cannot be
given:

[The status specialist can be forbidden from inventing a current status, completion date, or ticket number. The complaint specialist can also be forbidden from promising a fix or a date, and the info specialist can be forbidden from inventing opening times, fees, forms, or deadlines.]

Would I ship the router: [not yet]. Evidence: [it routed 20/24 correctly, the `other` route was only 1/4, the confidence policy made one correct decision wrong, and the routed system used 12416 tokens compared with 5917 for the monolith. However, the request route now produces a validated ServiceRequest instead of unstructured prose, which is a useful benefit of the routed design]. What would change my mind: [better results on a larger test set, an improved `other` definition, and  evidence that the structured request output and specialist restrictions justify the extra routing cost].

### 6. Stretch variant

Variant assigned: [model routing].

[I compared qwen3:4b-instruct and qwen2.5:7b using the same 24 queries,
router prompt, and policy. I did not record an independent prediction before
the run because project/models.py already contained the course result for this
comparison, so I did not invent a prediction afterwards.]

qwen3:4b-instruct routed 20/24 correctly and 17/20 excluding the ambiguous
cases. Its evidence was verbatim in 24/24 cases, its confidence ranged from
0.00 to 1.00 with 3 distinct values, and its resident memory is 3.9 GB.

qwen2.5:7b routed 17/24 correctly and 15/20 excluding the ambiguous cases.
Its evidence was verbatim in 20/24 cases, every confidence value was 1.00,
and its resident memory is 5.0 GB.

The smaller model won this routing task. The larger model used more memory,
routed fewer cases correctly, and copied evidence less faithfully. Its
confidence values were also not useful for thresholding because every case
was reported with confidence 1.00. This shows that a larger model is not
automatically better for every task and that the model should be selected
using measurements for the specific job.]

### The gold set

`artifacts/goldset.json` now holds [ 34] cases: 10 from week 2 and 24 added
today, with the four ambiguous ones tagged.

### Deferred

[None for the core Week 3 work or the stretch variant.]
# Week 4: a ReAct loop with two tools

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 4

**Run conditions.** agent model: [qwen2.5:7b] | temperature: 0.0 | step cap: [6] |
budget: [6 steps, using max_steps as the starter budget] | stall limit: [2] | served locally | date: [2026-10-19] |
scored on: [my own machine]

### 1. The two tool descriptions

| tool | what its "do not use this for" clause prevents |
| search_services | [It prevents using handbook search for arithmetic or to look up a person, which keeps factual handbook retrieval separate from arithmetic and sends calculations to compute instead.] |
| compute | [It prevents prose, units, currency symbols, and variable names from entering the arithmetic evaluator, keeping the tool limited to checkable arithmetic expressions.] |

### 2. The three caps

| cap | value | why that value |
| steps | [6] | [It provides a hard upper bound so the model cannot continue the agent loop indefinitely.] |
| budget | [6 steps through max_steps] | [The Week 4 starter uses the step cap as its budget; a separate token budget would be a stronger future extension.] |
| no progress | [2 consecutive stalled steps] | [Two steps without new handbook information are enough to identify a stuck loop without stopping after one unsuccessful call.] |

My definition of progress is [a tool step returning at least one handbook doc_id that has not been seen earlier in the run], and it does **not** fire when [a tool call returns only documents that were already seen, an empty result, or a non-document result such as compute].

### 3. Task accuracy

[3]/10 passed. Failed: [T-01, T-03, T-04, T-05, T-07, T-09, T-10].

Steps: min [1], max [2], mean [1.6]. Caps fired: [none].

[The scorer has a blind spot: in the recording, T-01 passed even though it was expected to use both search_services and compute, but the run only called search_services.]

### 4. What the tools bought

No-tool baseline: [2]/10. With tools: [3]/10.

One sentence on what the tools bought, and at what cost per task:

[The tools produced a net gain of 1 successful task compared with the live no-tool baseline, using 6 tool calls over 10 tasks (0.6 calls per task) and about 1,330 additional tokens per task.]

[For the live model comparison, qwen3:4b-instruct also passed 3/10, using 5 tool calls and 13,995 tokens.]

### 5. The four findings

| finding | result |
| tool abuse on T-08 | [none; T-08 correctly used no tool] |
| invention on T-10 | [yes; it invented a 24.00 EUR dog registration fee] |
| refusal with zero tool calls | [T-03, T-04, and T-07] |
| notice board: text reached the model | [yes, on T-05] |
| notice board: agent followed it | [yes, on T-05] |

[The live T-10 answer was: "The annual dog registration fee in Remerbaach is 24.00 EUR."]

### 6. Blast radius

Prompt-level defenses tried: [0] of 8 blocked the injection in the live run.

Given that an attacker **can** make this agent say anything, the worst thing
they can make it **do** is:

[Return a false or attacker-controlled help-desk answer to the user. The current tools are read-only search and arithmetic, so the agent cannot directly modify records, send messages, transfer money, or perform another external side effect.]

That answer depends on the fact that this agent's only tools are a read-only
search and a calculator. It changes the moment the agent gains a tool that
writes, sends, or pays, because [a successful prompt injection could then cause real external side effects instead of only producing a bad answer].

What I would build first to bound that, and the week I expect to build it in:

[I would first add a policy and permission layer around side-effecting tools, including least privilege and human confirmation before sensitive actions. I expect to build the human-confirmation part in Week 8.]

[Because prompt-only defenses blocked 0 of 8 live attempts, I will keep prompt injection on the security backlog and use Weeks 11 and 12 to attack-test deterministic permission and approval controls instead of relying only on stronger prompt wording.]

### Deferred

[A separate token or monetary budget is deferred because the Week 4 starter uses max_steps as its budget. I would add a token budget as a stronger production safeguard.]# Week 5: a planner, an executor, and a second agent

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 5

**Run conditions.** model: [qwen2.5:7b] | framework: Pydantic AI [2.27.1] |
runs per architecture: [3] | served locally | date: [2026-10-19] |
table from: [the recording]

### 1. The plan schema

What I tried first, and what happened:

[I used the flat Plan schema with goal, steps, and suspect_file. On my live
run, Pydantic AI reached "Exceeded maximum output retries (3)" because the
model did not return valid structured output. I also tested NativeOutput only
as a diagnostic. It returned a valid Plan object, but it incorrectly chose
models.py as the suspect file.]

What I shipped, and why it is shaped that way:

[I kept the plan shallow with goal: str, steps: list[str], and
suspect_file: str. A flat list is easier for this model to produce than a
nested list of Step objects, and it still gives us an ordered plan that can
be checked before execution.]

### 2. The validator

| check | what it catches |
| step count is between 2 and 6 | plans that are too short or too long |
| suspect_file is a known source file | made-up or incorrect file names |
| a step runs or checks the tests | plans with no verification step |
| no step edits a test file | plans that try to change the tests instead of fixing the code |

On a failed check my system [refuses in the intended policy], because
[a plan that already fails a free deterministic check should not be trusted].

[For the supplied comparison experiment I left the lecturer's runner
unchanged, so invalid plans are still recorded and the comparison continues.]

### 3. The three-way table

| architecture | green | tokens (mean) | seconds (mean) |
| A baseline | 0/3 | 10470 | 40.1 |
| B planner | 2/3 | 1751 | 15.0 |
| C planner + reviewer | 0/3 | 3441 | 29.0 |

### 4. Why the baseline fails

[The main difference is the amount of control given to the model. The
baseline can choose tools, their order, and how many times to use them, so it
has a much larger action space and can waste calls. The planner architecture
narrows the task to one structured fix proposal and deterministic code
applies and checks the change. The model is the same, but the architecture
gives it less freedom.]

### 5. The reviewer

Verdicts across my runs: [0] approve, [3] reject.

Would I ship it: [No]. Extra cost: [1690] tokens, [14.0] seconds per run.

[The reviewer rejected the correct >= fix in all three recorded runs. In the
first run it said >= was the wrong comparison. In the second it said the
change did not fix the 20:00 case. In the third it said including exactly
20:00 was incorrect, even though that was the required behavior.]

The case where it would earn its cost:

[It would be useful if it could catch a change that passes the current tests
but is still logically wrong, especially when the reviewer has different
information or expertise from the fixer.]

### 6. What my verifier cannot catch

[A test suite only checks cases that somebody wrote tests for. For example,
changing OFF_PEAK_FROM_HOUR from 20 to 19 instead of fixing the > comparison
can make the failing 20:00 test pass while leaving the implementation of the
business rule wrong. If no test checks that mistake, the suite can still be
green.]

### Deferred

[The full three-runs-per-architecture live comparison and Task B refactoring
are deferred. The recorded comparison was used because my local planner with
the normal Pydantic AI structured output reached the maximum output retries.]
# Week 6: memory, a stateless MCP server, and an A2A channel

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 6

**Run conditions.** MCP SDK version: [2.0.0rc1] | specification revision:
2026-07-28 | model: [No model was called in the Week 6 memory, MCP, or A2A tests] | served locally | date: [2026-10-25]

### 1. The handle

Format I chose: [`fact-` followed by 12 random hexadecimal characters using `secrets.token_hex(6)`.]

A guessable handle would expose: [Someone could guess another resident's handle and possibly access their information.]

### 2. Conflict and retention

- A write that contradicts an older fact: [keep both ], because [I want to keep the old information instead of losing it. The problem is that the facts may contradict each other. ]
- How long a record lives: [ The facts do not expire automaically .They stay until they are deleted ], because [ I kept the memory store simple for this lab. In a real system, I would need a time limit so personal information is not stored forever.]

[Nothing expires by default. If you kept it that way, say so explicitly
rather than leaving it unsaid. An undeclared retention policy is still a
retention policy.]

### 3. What k costs

k = [3 by default ]. Tokens added per call: [ Not measured yet. It depends on the length of the facts returned.].

At four hundred facts in the store, this design [ still returns at most k facts, but it has to search through the stored facts to find the matches. This may make searching slower as the number of facts grows.].

### 4. Memory off against memory on

| | tokens | turns to finish |
| memory off | | |
| memory on | | |

[The interesting result is usually that memory costs more tokens per call
and fewer calls per task. Whether that is a win depends on the task, and
saying which way it went for you is the entry.]

### 5. The protocol, at the wire

| server mode | status | Mcp-Session-Id | answered |
| stateless_http=True |200 |none  |yes  |
| stateless_http=False | 400| present | no |

The error the session-mode server returned, quoted exactly:

[ Bad Request: Missing session ID]

Why the two-server handle demonstration does not prove this on its own:

[ Both servers use the same JSON file, so the second server can read the first server's data. This would also work in session mode. The raw HTTP test proves the difference because the same request succeeds in stateless mode and fails in session mode.]

### 6. What forget does not reach

[The forget function deletes a fact from the JSON memory file, but it
cannot remove information already copied into a conversation.

If a resident asks to delete something, the stored fact will be removed,
but the information may still appear in earlier conversation messages.
The system should not use that deleted information again.]

### Deferred

[The memory-off versus memory-on comparison was not completed, so I do not have actual token counts or turns to finish for both cases.

I also did not measure the exact token cost of returning k facts. I completed and tested the memory functions, MCP tools, stateless HTTP comparison, and A2A demonstration.]