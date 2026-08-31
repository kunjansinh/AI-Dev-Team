AI-Dev-Team V0.4 Tool Runtime Wiring

1. Put apply_v04_tool_runtime.py in the repository's scripts/ folder.
2. From the repository root run:
   python scripts/apply_v04_tool_runtime.py
3. Then run:
   python -m pytest -q

The script is idempotent for the intended changes and patches the existing files rather than replacing the repository wholesale.
