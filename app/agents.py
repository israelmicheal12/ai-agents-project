"""Stage: the planner and the reviewer. Replaced in week 5.

Week 5 builds a planner, a free plan validator, and a reviewer on Pydantic
AI, against a toy repository. The pattern transfers to this application and
the repository does not, so this is one of the two stages you write rather
than copy. Keep the shapes week 5 taught you, minus `suspect_file`, which
named a file in the toy repository:

    Plan(goal: str, steps: list[str])      flat, because nested fails
    validate_plan(plan) -> tuple[bool, list[str]]
    Verdict(decision: "approve" | "reject", reason: str)

and provide the two functions `pipeline.py` calls, plus the name of the
model your agents use, so the trace records it:

    make_plan(question: str) -> Plan
    review(question: str, answer: str, evidence: list[str]) -> Verdict | None
    MODEL_NAME: str                         for example LARGE.name

Your `validate_plan` checks steps against the tools the agent actually has
(`tools.REGISTRY`) instead of week 5's KNOWN_FILES. Your reviewer sees the
answer and the evidence and not the agent's reasoning, for the reason week 5
gave: a reviewer that inherits the reasoning inherits the mistake.

`review` returning None means "not reviewed". The stub returns None rather
than an approval, because a stub that approves everything would be a stub
claiming to have checked something.

If week 5 measured that the plain loop wins, keep all three pass-throughs
and delete all three `@stub` lines below, and say so in DECISIONS.md. A
pass-through you chose is a design. One you skipped is a stub.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .stub import stub


class Plan(BaseModel):
    goal: str
    steps: list[str]


class Verdict(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(max_length=200)


from pydantic_ai import Agent, NativeOutput
from project.models import LARGE, pydantic_ai_model

MODEL_NAME = LARGE.name

_planner = Agent(
    pydantic_ai_model(LARGE),
    output_type=NativeOutput(Plan),
    retries=3,
    system_prompt=(
        "You are a planner for a commune help-desk assistant. "
        "Create a plan only. Do not execute any tools. "
        "Return a goal and exactly 3 steps for questions without arithmetic, or exactly 4 steps when arithmetic is necessary. "
        "Every step must begin with exactly one of these prefixes: search_services:, compute:, verify:, answer:. Never use the literal prefix 'action:'. "
        "Available tools are search_services and compute. "
        "Use search_services for facts about forms, fees and procedures. "
        "Use compute only when arithmetic is necessary. "
        "You must include a 'verify:' step to check the evidence. "
        "The final step must begin with 'answer:'. "
        "Use no other actions or tools. "
        "For a question about a form, use this exact three-step pattern: 'search_services: Find the relevant form', 'verify: Check the form number against retrieved evidence', 'answer: Provide the verified form information'. Do not add unnecessary steps. Never invent facts or claim that tools have already run."
    ),
)


def make_plan(question: str) -> Plan:
    """Create a structured plan using the Week 5 approach."""
    result = _planner.run_sync(question)
    return result.output


def validate_plan(plan: Plan) -> tuple[bool, list[str]]:
    """Check a proposed plan without calling an AI model."""

    from .tools import REGISTRY

    problems = []

    # Week 5 rule: plans must have between 2 and 6 steps.
    if not 2 <= len(plan.steps) <= 6:
        problems.append("plan must contain between 2 and 6 steps")

    # Tools come from the actual Week 4 registry.
    allowed = set(REGISTRY) | {"verify", "answer"}

    for step in plan.steps:
        action, separator, detail = step.partition(":")
        action = action.strip()

        if not separator or not detail.strip():
            problems.append(f"invalid step format: {step}")
        elif action not in allowed:
            problems.append(f"unknown tool or action: {action}")

    # The agent must verify the information before answering.
    if not any(s.strip().startswith("verify:") for s in plan.steps):
        problems.append("plan has no verification step")

    # Answering should be the final step.
    if not plan.steps or not plan.steps[-1].strip().startswith("answer:"):
        problems.append("final step must be answer")

    return len(problems) == 0, problems


@stub(week=5, does="not reviewed: returns None, never an approval")
def review(question: str, answer: str,
           evidence: list[str]) -> Verdict | None:
    return None
