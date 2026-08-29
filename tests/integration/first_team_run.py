from __future__ import annotations

import json
import shutil

from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager
from app.runtime.team_runtime import TeamRuntime


def main() -> None:
    user_instruction = """
Create a small Python utility that validates an email address.

The implementation should:
- expose a function called is_valid_email
- return True for a basic valid email
- return False for an invalid email
- include automated pytest tests
""".strip()

    state_manager = StateManager("data/state")
    task_manager = TaskManager(state_manager)

    workspace = "projects/demo_project"
    shutil.rmtree(workspace, ignore_errors=True)

    runtime = TeamRuntime(
        state_manager=state_manager,
        task_manager=task_manager,
        developer_workspace=workspace,
        max_iterations=2,
    )

    print("=" * 70)
    print("AI DEV TEAM - ROUTED END-TO-END RUN")
    print("=" * 70)
    print("\nUSER REQUEST:\n")
    print(user_instruction)

    print("\nTEAM CAPABILITIES:")
    print(json.dumps(runtime.describe_team(), indent=4))

    print("\nMANAGER + ORCHESTRATOR RUNNING...")

    result = runtime.run(user_instruction)

    print("\nFINAL RESULT:")
    print(json.dumps(result["result"], indent=4))

    print("\nFINAL TASK:")
    print(json.dumps(result["task"], indent=4))

    print("\n" + "=" * 70)
    print("ROUTED TEAM RUN COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
