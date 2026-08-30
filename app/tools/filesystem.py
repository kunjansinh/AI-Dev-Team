from __future__ import annotations

from pathlib import Path


class FilesystemTool:
    """Safe filesystem operations constrained to a workspace."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def safe_path(self, relative_path: str | Path) -> Path:
        path = (self.workspace / Path(relative_path)).resolve()
        try:
            path.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("Path escapes the workspace.") from exc
        return path

    def list_files(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.workspace)).replace("\\", "/")
            for p in self.workspace.rglob("*")
            if p.is_file()
        )

    def read_file(self, relative_path: str) -> str:
        return self.safe_path(relative_path).read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> str:
        if not isinstance(content, str):
            raise TypeError("File content must be a string.")
        path = self.safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.relative_to(self.workspace)).replace("\\", "/")
