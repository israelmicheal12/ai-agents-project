"""Block 2, first half: call the memory tools over MCP. TODO 6.

    python mcp_server.py &          # in one terminal
    PORT=8001 python mcp_server.py & # and a second instance
    python 01_mcp_client.py

Three things happen here and the third is the one to watch.
"""

from __future__ import annotations

import asyncio

from mcp.client import Client

SUBJECT = "A. Muller"


def text_of(result) -> str:
    content = getattr(result, "content", result)
    if isinstance(content, list) and content:
        return getattr(content[0], "text", str(content[0]))
    return str(content)


async def call(port: int, tool: str, **args):
    async with Client(f"http://127.0.0.1:{port}/mcp") as client:
        return await client.call_tool(tool, args)


async def main() -> int:
    """TODO 6. Three steps, and the third has a warning attached.

    1. Connect to :8000 and print the tool catalog. Seeing it arrive over
       HTTP is what makes the boundary real: these tools are not in this
       process.

    2. Call open_case and then remember on :8000. Watch
       artifacts/memory_store.json change while it runs.

    3. Redeem the SAME handle on :8001, the second instance, and recall from
       it.

    The warning: step 3 on its own does not prove the protocol is stateless.
    It would work under the old session-based protocol too, because each
    call opens its own connection and the state is on disk. It shows that a
    file is a file. 02_stateless.py is the demonstration that actually
    distinguishes the two, and it is the next thing you run.
    """
    # Connect to the MCP server on port 8000.
    async with Client("http://127.0.0.1:8000/mcp") as client:

        # Ask the server which tools are available.
        tools = await client.list_tools()

        # Print the tools returned by the server.
        print("Available MCP tools:", tools)
        # Ask the server to open a case for our test resident.
        case_result = await client.call_tool(
            "open_case",  # Name of the MCP tool we want to call.
            {"subject": SUBJECT}  # Send the resident's name to the tool.
        )

        # Get the case handle from the tool's response.
        case_handle = text_of(case_result)

        # Print the handle so we can check it.
        print("Case handle:", case_handle)
        # Ask the MCP server to remember a fact about this resident.
        fact_result = await client.call_tool(
            "remember",  # Name of the MCP tool we want to call.
            {
                "subject": SUBJECT,       # The resident from the starter file.
                "kind": "semantic",       # The type of memory we are saving.
                "fact": "Prefers French"   # The fact we want to remember.
            }
        )

        # Get the saved fact's handle from the response.
        fact_handle = text_of(fact_result)

        # Print the handle to confirm the fact was saved.
        print("Fact handle:", fact_handle)
    # Connect to the second MCP server on port 8001.
    async with Client("http://127.0.0.1:8001/mcp") as client:

        # Ask the second server who owns the case handle.
        subject_result = await client.call_tool(
            "case_subject",  # Find the resident linked to a case.
            {"handle": case_handle}  # Use the handle from server 8000.
        )

        # Print the resident returned by the second server.
        print("Resident from server 8001:", text_of(subject_result))
        # Ask server 8001 to search for the resident's saved fact.
        recall_result = await client.call_tool(
            "recall",  # Name of the MCP search tool.
            {
                "subject": SUBJECT,  # Search only this resident's memory.
                "query": "French",   # Search for the word French.
                "k": 3              # Return at most three facts.
            }
        )

        # Print the facts returned by the second server.
        print("Facts from server 8001:", text_of(recall_result))
    # Tell Python that the program finished successfully.
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
