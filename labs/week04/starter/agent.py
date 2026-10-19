"""The loop, the caps, and the tool executor. TODO 1 to 5.

Twenty lines of control flow and four decisions. Week 5 replaces this file
with about four lines of Pydantic AI, and the point of today is to know
exactly what those four lines are hiding.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from handbook import INJECTION_MARKER
from tools import SCHEMAS as ANTHROPIC_SCHEMAS
from tools import compute, search_services

from project.models import LARGE
from project.trace import TraceRecorder, local_conditions

# --------------------------------------------------------------------------
# TODO 1. The schemas, in the shape this endpoint speaks.
# --------------------------------------------------------------------------
#
# The descriptions in tools.py are already good and they are the actual
# lesson: each one says what the tool returns, when NOT to use it, and what
# an empty result means. A tool description is an interface contract whose
# audience is a model, so it is prompt engineering rather than documentation.
#
# What changes here is only the envelope. The local endpoint speaks the
# OpenAI wire format, which nests the schema under "function" and calls the
# parameter block "parameters". Other providers nest it differently and call
# it "input_schema". Nothing about your tool changes, which is the point:
# the envelope is plumbing and the description is the design.

def to_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Wrap one Anthropic-shaped schema for the OpenAI wire format.

    The descriptions in tools.py are already written and they are the actual
    lesson: read them before you write this function. Each one says what the
    tool returns, when NOT to use it, and what an empty result means.

    All you do here is change the envelope. OpenAI nests the schema under a
    "function" key and calls the parameter block "parameters"; the shape in
    tools.py calls it "input_schema". Nothing about your tool changes, which
    is the point: the envelope is plumbing and the description is design.
    """
    # Return the tool schema in the format expected by the OpenAI-style API.
    return {
        # Tell the API that this tool is a function.
        "type": "function",

        # The actual function information goes inside this block.
        "function": {
            # Keep the same tool name from tools.py.
            "name": schema["name"],

            # Keep the lecturer's tool description unchanged.
            "description": schema["description"],

            # OpenAI calls the input schema "parameters".
            # In tools.py, the same information is called "input_schema".
            "parameters": schema["input_schema"],
        },
    }

    # TODO 1 completed.
    # raise NotImplementedError("TODO 1: convert the schema envelope")


SCHEMAS = [to_openai_schema(s) for s in ANTHROPIC_SCHEMAS]
DISPATCH: dict[str, Callable[..., Any]] = {
    "search_services": search_services,
    "compute": compute,
}

# The list of concrete triggers on the search_services line is not
# decoration, and removing it costs four tasks. Without it the model
# decides from its own prior whether a commune handbook would plausibly
# contain the answer, and it is wrong about that surprisingly often, in
# the direction of refusing to look. Measured: 7/10 with the list, 3/10
# without it, same model and same everything else.
SYSTEM = """\
You answer questions for the help desk of Remerbaach, a Luxembourg commune, \
using the tools provided.

search_services  searches the commune handbook. Use it for any fee, opening \
time, form number, phone number, address, deadline, or procedure.
compute          evaluates one arithmetic expression.

How to work:
  1. Decide whether the question needs a fact from the handbook. If it does, \
you MUST call search_services before answering. You do not know what this \
handbook contains and you cannot tell from the question alone.
  2. You may only say the handbook does not cover something AFTER a search \
has come back without it. Saying it without searching is always wrong.
  3. If the answer needs arithmetic, call compute. Do not calculate in your \
head, even when it looks easy.
  4. If the question needs no handbook fact and no arithmetic, answer \
directly and call nothing at all.

Rules for the answer:
  Never state a fee, opening time, form number, or deadline that did not \
appear in a search result. Quote figures exactly as the handbook gives them.
  Answer in the language of the question, in under eighty words.
"""


# --------------------------------------------------------------------------
# The record of one run
# --------------------------------------------------------------------------

@dataclass
class Run:
    task_id: str
    answer: str = ""
    steps: int = 0
    tool_calls: list[str] = field(default_factory=list)
    seconds: float = 0.0
    tokens: int = 0
    cap_fired: str | None = None
    saw_injection: bool = False       # did the hostile text reach the model
    tool_errors: int = 0

    @property
    def stopped_cleanly(self) -> bool:
        return self.cap_fired is None


# --------------------------------------------------------------------------
# TODO 5. Running the tools.
# --------------------------------------------------------------------------

MAX_RESULT_CHARS = 2000


def run_tool_call(name: str, raw_arguments: str) -> tuple[Any, bool]:
    """TODO 5. Validate, execute, catch, and cap. Four jobs, none the model's.

    Return (result, errored).

    1. The arguments arrive as a JSON string the model wrote. Parse them, and
       handle the case where it is not valid JSON, because sometimes it is
       not.
    2. The tool name is also something the model wrote. It can name a tool
       that does not exist. That is a real failure category, not an
       impossibility, so say so in a way the model can act on.
    3. Execute inside a try. An exception has to become a result the model
       can read rather than a crash, because the interesting question is
       what the agent does NEXT, and a traceback ends the run before you
       find out.
    4. Cap the size of what you return, in characters. A tool that returns
       half a megabyte should not blow up your context mid-run.

    One thing to get right that is not obvious. Do NOT put the exception's
    file path or stack into the result. A model handed a stack trace will
    paste it into its answer, and you have just told whoever asked the
    question what your directory layout is.
    """
        # First, try to turn the model's JSON text into Python data.
    try:
        arguments = json.loads(raw_arguments)

    # If the model produced invalid JSON, return an error instead of crashing.
    except json.JSONDecodeError:
        return "Tool call failed: arguments were not valid JSON.", True

    # The model may ask for a tool name that does not exist.
    if name not in DISPATCH:
        return f"Tool call failed: unknown tool '{name}'.", True

    # The arguments should be a JSON object, which becomes a Python dictionary.
    if not isinstance(arguments, dict):
        return "Tool call failed: arguments must be a JSON object.", True

    # Try to run the requested tool with the supplied arguments.
    try:
        result = DISPATCH[name](**arguments)

    # Turn tool errors into a short message the model can understand.
    # We do not return a traceback or file path.
    except Exception as exc:
        return f"{name} failed: {exc}", True

    # Convert the result to JSON when possible so it can be sent back
    # to the model as text.
    try:
        result_text = json.dumps(result, ensure_ascii=False)

    # If the result is not JSON serializable, fall back to normal text.
    except (TypeError, ValueError):
        result_text = str(result)

    # Keep tool output small so one large result does not fill the context.
    if len(result_text) > MAX_RESULT_CHARS:
        result_text = result_text[:MAX_RESULT_CHARS] + "...[truncated]"

    # False means the tool ran successfully.
    return result_text, False

    # TODO 5 completed.
    # raise NotImplementedError("TODO 5: validate, execute, catch, cap")


# --------------------------------------------------------------------------
# TODO 2, 3, 4. The loop and its caps.
# --------------------------------------------------------------------------

def run_task(client, task, model: str = LARGE.name,
             max_steps: int = 6, stall_limit: int = 2,
             system: str = SYSTEM, week: int = 4) -> Run:
    """TODO 2, 3, 4. The whole agent: a while loop with three exits.

    Build it in this order, and run it after each one.

    TODO 2, the loop itself. Call the model with `tools=SCHEMAS`. If the
      reply has no tool calls, the model is done: take its content as the
      answer and stop. Otherwise append the assistant turn, run each tool
      call, append one message per result with role "tool" and the matching
      tool_call_id, and go round again.

      Two mistakes that cost people ten minutes each. The assistant turn
      must be appended BEFORE the tool results, or the endpoint rejects a
      result that answers no request. And every tool result must carry the
      id of the call it answers.

    TODO 3, the step cap. `max_steps` iterations and then stop. When it
      fires, set `run.cap_fired` and produce a partial answer through
      `_partial` below. Never an empty string and never an exception.

    TODO 4, the no-progress detector. Track which doc_ids you have already
      seen. If a step brings back nothing new, that is one stall; if it
      happens `stall_limit` times in a row, stop.

      Defining progress is the design decision here and there is more than
      one defensible answer. "A document id I had not seen" is the one this
      solution uses because it is cheap, needs no model, and does not fire
      on a legitimate second search with different keywords, which naive
      "same call twice" detectors do. Say in DECISIONS.md what yours is.

    Fill in `run` as you go: steps, tool_calls, tokens, tool_errors, and
    `saw_injection` when the tool result contains handbook.INJECTION_MARKER.
    Record a trace with TraceRecorder exactly as weeks 1 to 3 did, one span
    per model call and one per tool call, because week 10 evaluates this.

    An agent without TODO 3 and TODO 4 is a program whose termination
    depends on a model's judgment, which is not a property you can promise
    anybody.
    """
    # Start timing the whole task.
    started = time.perf_counter()

    # Create the object where we store the result of this run.
    run = Run(task_id=task.id)

    # The conversation starts with the system instructions
    # and the user's question.
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task.question},
    ]

    # Remember handbook documents we have already seen.
    # We use new document IDs as our definition of progress.
    seen_doc_ids: set[str] = set()

    # Count how many steps in a row gave us no new document.
    stalls = 0

    # Create one trace for this whole task.
    rec = TraceRecorder(
        week=week,
        case_id=task.id,
        conditions=local_conditions(
            model,
            temperature=0.0,
            system="react",
            language=task.lang,
        ),
        user_input=task.question,
    )

    # TODO 2 + TODO 3:
    # Run the agent, but never allow more than max_steps model calls.
    for step_number in range(max_steps):

        # Human-readable steps start at 1 instead of 0.
        run.steps = step_number + 1

        # Record every model call in the trace.
        with rec.step("model", model) as trace_step:

            # Ask the model what to do next.
            reply = client.chat.completions.create(
                model=model,
                temperature=0.0,
                max_tokens=400,
                messages=messages,
                tools=SCHEMAS,
            )

            # Count the tokens used by this model call.
            prompt_tokens = reply.usage.prompt_tokens
            completion_tokens = reply.usage.completion_tokens

            # Save the token counts in the trace.
            trace_step.tokens(
                prompt_tokens,
                completion_tokens,
            )

            # Add this call's tokens to the total for the run.
            run.tokens += prompt_tokens + completion_tokens

            # Get the assistant message returned by the model.
            message = reply.choices[0].message

            # Get any tool calls the model requested.
            # If there are none, the model is giving its final answer.
            tool_calls = message.tool_calls or []

            # Record useful information about this model step.
            trace_step.detail(
                finish_reason=reply.choices[0].finish_reason,
                tool_calls=[
                    call.function.name for call in tool_calls
                ],
            )

        # If the model requested no tool, the task is finished.
        if not tool_calls:

            # Store the model's final answer.
            run.answer = (message.content or "").strip()

            # Record the total time.
            run.seconds = time.perf_counter() - started

            # Finish the trace.
            rec.finish(
                output=run.answer,
                outcome="ok",
                steps=run.steps,
                tool_calls=run.tool_calls,
                cap_fired=run.cap_fired,
            )

            # Give the completed run back to the caller.
            return run

        # --------------------------------------------------------------
        # The model asked for one or more tools.
        # The assistant request MUST be added before the tool results.
        # --------------------------------------------------------------

        assistant_tool_calls = []

        # Convert every tool call into the message format expected
        # by the next model call.
        for call in tool_calls:

            call_data = {
                "id": call.id,
                "type": call.type,
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }

            # Keep the tool-call index when the endpoint provides one.
            # The recorded fixture also contains this field.
            if getattr(call, "index", None) is not None:
                call_data["index"] = call.index

            assistant_tool_calls.append(call_data)

        # Add the assistant's tool request to the conversation first.
        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": assistant_tool_calls,
        })

        # Track whether this whole step discovered a new handbook document.
        new_doc_ids: set[str] = set()

        # Run every tool requested in this model turn.
        for call in tool_calls:

            # Read the tool name and its raw JSON arguments.
            name = call.function.name
            raw_arguments = call.function.arguments

            # Keep the sequence of tools for later evaluation.
            run.tool_calls.append(name)

            # Record this tool execution as its own trace step.
            with rec.step("tool", name) as trace_step:

                # Our executor validates and runs the tool.
                result, errored = run_tool_call(
                    name,
                    raw_arguments,
                )

                # Store useful information about the tool call.
                trace_step.detail(
                    arguments=raw_arguments,
                    errored=errored,
                )

            # Count tool errors instead of crashing the agent.
            if errored:
                run.tool_errors += 1

            # Check whether hostile notice-board text reached the model.
            if INJECTION_MARKER in str(result):
                run.saw_injection = True

            # Find handbook document IDs returned by this tool.
            current_doc_ids = _doc_ids(result)

            # A document we have never seen before counts as progress.
            new_doc_ids.update(
                current_doc_ids - seen_doc_ids
            )

            # Remember all documents we have seen.
            seen_doc_ids.update(current_doc_ids)

            # Give the tool result back to the model.
            # The tool_call_id connects this result to the exact request.
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

        # --------------------------------------------------------------
        # TODO 4: no-progress detector.
        # --------------------------------------------------------------

        # If this step found at least one new document, progress was made.
        if new_doc_ids:
            stalls = 0

        # Otherwise this step did not add new handbook information.
        else:
            stalls += 1

        # Stop if too many steps in a row make no progress.
        if stalls >= stall_limit:

            # Record which cap stopped the run.
            run.cap_fired = "no_progress"

            # Return a useful partial answer instead of nothing.
            run.answer = _partial(
                run,
                "the agent stopped because it was not making progress",
            )

            # Record the total running time.
            run.seconds = time.perf_counter() - started

            # Finish the trace and mark it as capped.
            rec.finish(
                output=run.answer,
                outcome="degraded",
                steps=run.steps,
                tool_calls=run.tool_calls,
                cap_fired=run.cap_fired,
            )

            return run

    # --------------------------------------------------------------
    # TODO 3: step cap.
    # We only reach here if all max_steps iterations were used.
    # --------------------------------------------------------------

    run.cap_fired = "step_limit"

    # Return a useful partial answer rather than an empty string.
    run.answer = _partial(
        run,
        f"the maximum of {max_steps} steps was reached",
    )

    # Store the total running time.
    run.seconds = time.perf_counter() - started

    # Finish the trace.
    rec.finish(
        output=run.answer,
        outcome="degraded",
        steps=run.steps,
        tool_calls=run.tool_calls,
        cap_fired=run.cap_fired,
    )

    return run

    # TODO 2, 3, and 4 completed.
    # raise NotImplementedError("TODO 2, 3, 4: the loop and its caps")


def _partial(run: Run, reason: str) -> str:
    """What a capped run returns. Never an empty string, never a crash.

    A cap that returns nothing is indistinguishable from a system that had
    nothing to say, and week 8 spends a session on why that distinction
    matters. Say what happened and what was known so far.
    """
    return (f"I could not complete this. {reason}, after "
            f"{len(run.tool_calls)} tool call(s). Please telephone the help "
            f"desk on 4796-2222.")


def _doc_ids(tool_result: Any) -> set[str]:
    try:
        parsed = json.loads(tool_result) if isinstance(tool_result, str) \
            else tool_result
    except (json.JSONDecodeError, TypeError):
        return set()
    if not isinstance(parsed, list):
        return set()
    return {h.get("doc_id") for h in parsed
            if isinstance(h, dict) and h.get("doc_id")}
