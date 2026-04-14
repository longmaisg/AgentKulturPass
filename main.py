# main.py
# Entry point. Creates the agent with a system prompt and runs a task.

from agent import Agent

SYSTEM = """You are an AI agent that helps automate interactions with the KulturPass platform.
You can search the web and save notes. Always save important findings with save_note."""

if __name__ == "__main__":
    agent = Agent(system=SYSTEM)
    result = agent.run("What is KulturPass Luxembourg? Save a brief summary as a note.")
    print(f"\n[Final answer]\n{result}")
