"""Contract tests for the GitHub Actions CI workflow.

Standard-library only: run with

    python3 -m unittest discover -s tests -t . -v
"""

import pathlib
import re
import unittest

GATE_COMMAND = "python3 -m unittest discover -s tests -t . -v"

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
README = REPO_ROOT / "README.md"


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def extract_on_block(text: str) -> str:
    """Return the `on:` block: its key line plus the indented lines below it."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.match(r"^on\s*:", line):
            start = index
            break
    if start is None:
        return ""

    block = [lines[start]]
    for line in lines[start + 1 :]:
        if line.strip() and not line[0].isspace():
            break
        block.append(line)
    return "\n".join(block)


class TestCIWorkflow(unittest.TestCase):
    def test_workflow_file_exists(self):
        self.assertTrue(
            WORKFLOW.is_file(),
            f"expected CI workflow at {WORKFLOW}",
        )

    def test_triggers_on_push_and_pull_request(self):
        on_block = extract_on_block(read_workflow())
        self.assertTrue(
            on_block,
            "expected an `on:` trigger block in .github/workflows/ci.yml",
        )
        self.assertRegex(
            on_block,
            r"(?m)^\s+push\s*:\s*(\{\s*\})?\s*$",
            "expected the workflow to trigger on push",
        )
        self.assertRegex(
            on_block,
            r"(?m)^\s+pull_request\s*:\s*(\{\s*\})?\s*$",
            "expected the workflow to trigger on pull_request",
        )

    def test_runs_exact_documented_gate_command(self):
        self.assertIn(
            GATE_COMMAND,
            read_workflow(),
            "expected the workflow to run the documented gate command verbatim",
        )

    def test_readme_documents_the_same_gate_command(self):
        self.assertIn(
            GATE_COMMAND,
            README.read_text(encoding="utf-8"),
            "expected README.md to document the same gate command CI runs",
        )

    def test_uses_public_standard_actions(self):
        text = read_workflow()
        self.assertRegex(text, r"actions/checkout@v\d+")
        self.assertRegex(text, r"actions/setup-python@v\d+")
        self.assertNotIn(
            "secrets.",
            text,
            "the workflow must not require secrets or tokens",
        )

    def test_failures_are_not_swallowed(self):
        text = read_workflow()
        self.assertNotIn("continue-on-error", text)
        self.assertNotIn("|| true", text)
        self.assertNotIn("|| exit 0", text)
        self.assertNotIn("if: always()", text)

    def test_no_npm_or_pnpm_commands(self):
        text = read_workflow()
        for forbidden in ("pnpm", "npm run", "npm test", "npx", "yarn"):
            self.assertNotIn(
                forbidden,
                text,
                f"the workflow must not invoke {forbidden!r}",
            )

    def test_workflow_parses_as_yaml_with_a_job(self):
        try:
            import yaml  # type: ignore[import-untyped]  # optional dependency
        except ImportError:
            raise unittest.SkipTest("PyYAML is not installed; skipping YAML check")

        data = yaml.safe_load(read_workflow())
        self.assertIsInstance(data, dict)
        self.assertIn("jobs", data)
        self.assertTrue(data["jobs"], "expected at least one job in the workflow")


if __name__ == "__main__":
    unittest.main()
