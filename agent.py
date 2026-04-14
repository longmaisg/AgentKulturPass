# agent.py
# The core Agent class.
# - Loads memory on start, injects it into the system prompt.
# - run(task) sends the task to Claude, then loops:
#     Claude replies → if it calls a tool, we run it and send the result back
#     → repeat until Claude says it's done (stop_reason == "end_turn").
# - Saves the run to episodic memory when done.

import anthropic
from memory import Memory
from tools import TOOLS, execute_tool

MODEL = "claude-opus-4-6"


class Agent:
    def __init__(
        self,
        system: str = "You are a helpful AI agent.",
        max_facts: int = 5,      # how many recent facts to prepend
        max_episodes: int = 3,   # how many recent runs to prepend
    ):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self.base_system = system
        self.max_facts = max_facts
        self.max_episodes = max_episodes
        self.memory = Memory()
        self.messages: list = []             # conversation history (reset each run)

    def _build_system(self) -> str:
        """Combine base system prompt with filtered memory context."""
        summary = self.memory.context_summary(
            max_facts=self.max_facts,
            max_episodes=self.max_episodes,
        )
        return f"{self.base_system}\n\n{summary}"

    def run(self, task: str) -> str:
        """Run a task and return the final text response."""
        print(f"\n[Agent] Task: {task}")
        self.messages = [{"role": "user", "content": task}]

        # Agentic loop: keep going as long as Claude wants to call tools
        while True:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=self._build_system(),
                tools=TOOLS,
                messages=self.messages,
            )

            # Add Claude's response to history (keep tool_use blocks too)
            self.messages.append({"role": "assistant", "content": response.content})

            # Done — save run to memory and return final text
            if response.stop_reason == "end_turn":
                result = next(b.text for b in response.content if b.type == "text")
                self.memory.log_run(task, result)
                return result

            # Claude wants to call tools — run each one and collect results
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  [tool] {block.name}({block.input})")
                        result = execute_tool(block.name, block.input, self.memory)
                        print(f"  [result] {result[:120]}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                # Send all tool results back to Claude in one message
                self.messages.append({"role": "user", "content": tool_results})
