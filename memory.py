# memory.py
# Persistent memory stored in memory.json.
# Two sections:
#   semantic  — facts the agent has learned {key: {value, saved_at}}
#   episodic  — log of past runs [{timestamp, task, result}]
#
# context_summary(max_facts, max_episodes) controls what gets prepended
# to the system prompt — always the MOST RECENT facts + episodes.
# Claude can also pull specific facts on demand via the recall_note tool.

import json
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path("memory.json")
MAX_EPISODES = 50  # hard cap on stored episodes


class Memory:
    def __init__(self):
        self._data = self._load()

    # --- persistence ---

    def _load(self) -> dict:
        if MEMORY_FILE.exists():
            data = json.loads(MEMORY_FILE.read_text())
            # Migrate old plain-string facts to {value, saved_at} format
            for k, v in data.get("semantic", {}).items():
                if isinstance(v, str):
                    data["semantic"][k] = {"value": v, "saved_at": "2000-01-01T00:00:00"}
            return data
        return {"semantic": {}, "episodic": []}

    def save(self) -> None:
        MEMORY_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))

    # --- semantic memory (facts) ---

    def remember(self, key: str, value: str) -> None:
        """Store a fact with a timestamp. Overwrites if key exists."""
        self._data["semantic"][key] = {
            "value": value,
            "saved_at": datetime.utcnow().isoformat(timespec="seconds"),
        }
        self.save()

    def recall(self, key: str) -> str | None:
        """Look up a fact by key. Returns the value string or None."""
        entry = self._data["semantic"].get(key)
        return entry["value"] if entry else None

    def all_facts(self) -> dict:
        """Return {key: value} for all facts (no timestamps)."""
        return {k: v["value"] for k, v in self._data["semantic"].items()}

    def recent_facts(self, n: int) -> list[tuple[str, str]]:
        """Return the N most recently saved (key, value) pairs."""
        entries = [
            (k, v["value"], v["saved_at"])
            for k, v in self._data["semantic"].items()
        ]
        entries.sort(key=lambda x: x[2], reverse=True)  # newest first
        return [(k, v) for k, v, _ in entries[:n]]

    # --- episodic memory (run log) ---

    def log_run(self, task: str, result: str) -> None:
        """Append a completed run to the episode log."""
        self._data["episodic"].append({
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "task": task[:120],
            "result": result[:300],
        })
        self._data["episodic"] = self._data["episodic"][-MAX_EPISODES:]
        self.save()

    def recent_runs(self, n: int = 3) -> list:
        return self._data["episodic"][-n:]

    # --- context for system prompt ---

    def context_summary(self, max_facts: int = 5, max_episodes: int = 3) -> str:
        """
        Build the memory block prepended to the system prompt.
        max_facts    — how many of the most recent facts to include
        max_episodes — how many of the most recent runs to include
        Set either to 0 to exclude that section entirely.
        """
        lines = []

        if max_facts > 0:
            facts = self.recent_facts(max_facts)
            lines.append("[Memory — recent facts]")
            if facts:
                for k, v in facts:
                    lines.append(f"  - {k}: {v[:120]}")
            else:
                lines.append("  (none yet)")

        if max_episodes > 0:
            runs = self.recent_runs(max_episodes)
            lines.append("[Memory — recent runs]")
            if runs:
                for ep in runs:
                    lines.append(f"  - [{ep['timestamp']}] {ep['task'][:80]}")
            else:
                lines.append("  (none yet)")

        return "\n".join(lines)
