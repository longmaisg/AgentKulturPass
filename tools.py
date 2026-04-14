# tools.py
# Defines the tools Claude can call during a run.
# Each tool has: name, description, input_schema (what args Claude must pass).
# execute_tool() receives the Memory object so save_note writes to real storage.

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory import Memory

TOOLS = [
    {
        "name": "search_web",
        "description": "Search the web for information about a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_note",
        "description": "Save an important fact or result to long-term memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key":   {"type": "string", "description": "Short label for the fact."},
                "value": {"type": "string", "description": "Content to save."},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "recall_note",
        "description": "Look up a previously saved fact from long-term memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The label to look up."}
            },
            "required": ["key"],
        },
    },
]


def execute_tool(name: str, inputs: dict, memory: "Memory") -> str:
    """Run the tool Claude requested and return the result as a string."""
    if name == "search_web":
        # TODO: replace with real web search
        return f"[stub] Search results for '{inputs['query']}': no real search connected yet."

    if name == "save_note":
        memory.remember(inputs["key"], inputs["value"])
        return f"Saved: '{inputs['key']}'."

    if name == "recall_note":
        value = memory.recall(inputs["key"])
        return value if value else f"No note found for '{inputs['key']}'."

    return f"Unknown tool: {name}"
