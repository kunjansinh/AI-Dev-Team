from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.agents.manager_agent import ManagerAgent
from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager
from app.tools.llm.ollama_client import OllamaClient


def main() -> None:
    proposal = """
I propose that every specialist in our AI development team should
use a completely different local AI model.

We currently have a laptop with:
- 8 GB RAM
- 4 GB GPU VRAM

The team will eventually contain:
- Manager
- Architect
- Researcher
- Developer
- QA
- Security

Evaluate whether this is a good architecture for our first version.
Do not agree with me automatically. Challenge the proposal if it is
technically weak and recommend a better architecture.
""".strip()

    with tempfile.TemporaryDirectory() as temporary_directory:
        state_path = Path(temporary_directory) / "state"

        state_manager = StateManager(state_path)
        task_manager = TaskManager(state_manager)
        llm_client = OllamaClient(model="qwen3:1.7b")

        manager = ManagerAgent(
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=llm_client,
        )

        print("\n" + "=" * 70)
        print("LIVE MANAGER EVALUATION")
        print("=" * 70)
        print("\nProposal:\n")
        print(proposal)

        print("\n" + "-" * 70)
        print("Qwen3:4b is evaluating...")
        print("-" * 70)

        result = manager.evaluate_proposal(proposal)

        print("\nMANAGER DECISION")
        print("=" * 70)

        print(json.dumps(result, indent=4))

        print("\n" + "=" * 70)
        print("EVALUATION COMPLETE")
        print("=" * 70)


if __name__ == "__main__":
    main()