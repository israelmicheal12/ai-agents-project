"""Week 8: persistent human approval gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command, interrupt


DB_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "app_approvals.sqlite"


class ApprovalState(TypedDict):
    payload: dict
    decision: dict


def submit(state: ApprovalState) -> dict:
    # No writes or other side effects before interrupt().
    answer = interrupt(state["payload"])

    verdict = answer.get("verdict", "reject")
    by = answer.get("by", "human")
    arguments = dict(state["payload"].get("arguments", {}))

    if verdict == "edit":
        changes = answer.get("arguments", {})
        if not isinstance(changes, dict):
            verdict = "reject"
        else:
            arguments.update(changes)

    if verdict not in ("approve", "reject", "edit"):
        verdict = "reject"

    return {
        "decision": {
            "verdict": verdict,
            "by": by,
            "arguments": arguments,
        }
    }


def build(saver):
    builder = StateGraph(ApprovalState)
    builder.add_node("submit", submit)
    builder.add_edge(START, "submit")
    builder.add_edge("submit", END)
    return builder.compile(checkpointer=saver)


def config_for(case_id: str) -> dict:
    return {
        "configurable": {
            "thread_id": f"app-approval:{case_id}"
        }
    }


def request_approval(payload: dict, unattended: bool = False) -> dict:
    # Week 10 must never wait for a human.
    if unattended:
        return {
            "verdict": "timeout",
            "by": "unattended_policy",
            "arguments": {},
        }

    # Exactly one action is gated: submitting a case.
    if payload.get("action") != "submit_case":
        return {
            "verdict": "reject",
            "by": "unsupported_action",
            "arguments": {},
        }

    case_id = str(payload.get("case_id", ""))
    if not case_id:
        return {
            "verdict": "reject",
            "by": "missing_case_id",
            "arguments": {},
        }

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = config_for(case_id)

    with SqliteSaver.from_conn_string(str(DB_PATH)) as saver:
        graph = build(saver)

        graph.invoke(
            {"payload": payload, "decision": {}},
            config=config,
        )

        snapshot = graph.get_state(config)

        if snapshot.next:
            return {
                "verdict": "pending",
                "by": "human",
                "arguments": {},
            }

        return snapshot.values["decision"]


def resume_approval(
    case_id: str,
    verdict: str,
    arguments: dict | None = None,
) -> dict:
    if verdict not in ("approve", "reject", "edit"):
        raise ValueError("Decision must be approve, reject, or edit")

    config = config_for(case_id)

    with SqliteSaver.from_conn_string(str(DB_PATH)) as saver:
        graph = build(saver)
        snapshot = graph.get_state(config)

        if "submit" not in snapshot.next:
            raise ValueError("This case is not awaiting approval")

        response = {
            "verdict": verdict,
            "by": "local_human",
        }

        if verdict == "edit":
            if not isinstance(arguments, dict):
                raise ValueError("Edit requires a JSON arguments object")
            response["arguments"] = arguments

        result = graph.invoke(
            Command(resume=response),
            config=config,
        )

        return result["decision"]


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start")
    start.add_argument("case_id")

    resume = commands.add_parser("resume")
    resume.add_argument("case_id")
    resume.add_argument("verdict", choices=["approve", "reject", "edit"])
    resume.add_argument("--arguments", default=None)

    args = parser.parse_args()

    if args.command == "start":
        payload = {
            "action": "submit_case",
            "case_id": args.case_id,
            "arguments": {
                "topic": "parking vignette",
                "fee": {"fee_eur": 60.0, "period": "year"},
            },
            "evidence": ["Parking vignette information"],
            "degraded": False,
            "missing": [],
        }
        result = request_approval(payload)
    else:
        edits = json.loads(args.arguments) if args.arguments else None
        result = resume_approval(args.case_id, args.verdict, edits)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
