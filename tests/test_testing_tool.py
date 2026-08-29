from pathlib import Path

from app.tools.testing import TestingTool


def test_testing_tool_runs_passing_tests(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_sample.py").write_text(
        """
def test_example():
    assert 1 + 1 == 2
""",
        encoding="utf-8",
    )

    tool = TestingTool()

    result = tool.run_pytest(tmp_path)

    assert result["status"] == "passed"
    assert result["exit_code"] == 0
    assert result["tests_collected"] == 1
    assert result["tests_passed"] == 1
    assert result["tests_failed"] == 0


def test_testing_tool_detects_failed_tests(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_sample.py").write_text(
        """
def test_example():
    assert 1 + 1 == 3
""",
        encoding="utf-8",
    )

    tool = TestingTool()

    result = tool.run_pytest(tmp_path)

    assert result["status"] == "failed"
    assert result["exit_code"] != 0
    assert result["tests_collected"] == 1
    assert result["tests_failed"] == 1


def test_testing_tool_detects_no_tests(
    tmp_path: Path,
) -> None:
    (tmp_path / "example.py").write_text(
        "VALUE = 10\n",
        encoding="utf-8",
    )

    tool = TestingTool()

    result = tool.run_pytest(tmp_path)

    assert result["status"] == "no_tests"
    assert result["tests_collected"] == 0


def test_testing_tool_handles_missing_workspace(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "does_not_exist"

    tool = TestingTool()

    result = tool.run_pytest(workspace)

    assert result["status"] == "error"
    assert result["tests_collected"] == 0