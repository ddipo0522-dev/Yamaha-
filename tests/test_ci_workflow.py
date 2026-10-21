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


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def extract_permissions_blocks(text: str) -> list[dict[str, str]]:
    """Return every `permissions:` mapping in the workflow as a key/value dict."""
    lines = text.splitlines()
    blocks: list[dict[str, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)permissions\s*:\s*(.*)$", line)
        if not match:
            continue
        indent = len(match.group(1))
        if match.group(2).strip():
            # Inline form such as `permissions: {}` grants nothing.
            blocks.append({})
            continue
        mapping: dict[str, str] = {}
        for follow in lines[index + 1 :]:
            if not follow.strip():
                continue
            if _indent_of(follow) <= indent:
                break
            key, _, value = follow.strip().partition(":")
            mapping[key.strip()] = value.strip().strip("\"'")
        blocks.append(mapping)
    return blocks


def extract_step_entries(text: str) -> list[dict[str, str | None]]:
    """Return each step of the workflow's `steps:` list.

    Each entry maps the keys `uses` and `run` to their scalar values; a key
    that the step does not define maps to None.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.match(r"^\s*steps\s*:\s*$", line):
            start = index
            break
    if start is None:
        return []

    base_indent = _indent_of(lines[start])
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and _indent_of(line) <= base_indent:
            break
        body.append(line)

    raw_entries: list[list[str]] = []
    entry_indent: int | None = None
    for line in body:
        if line.strip().startswith("- "):
            if entry_indent is None:
                entry_indent = _indent_of(line)
            if _indent_of(line) == entry_indent:
                raw_entries.append([line])
                continue
        if raw_entries:
            raw_entries[-1].append(line)

    entries: list[dict[str, str | None]] = []
    for raw in raw_entries:
        key_indent = entry_indent + 2 if entry_indent is not None else 0
        for line in raw[1:]:
            if line.strip():
                key_indent = _indent_of(line)
                break
        entries.append(
            {
                "uses": _entry_value(raw, "uses", key_indent),
                "run": _entry_value(raw, "run", key_indent),
            }
        )
    return entries


def _entry_value(entry: list[str], key: str, key_indent: int) -> str | None:
    """Return the scalar value of `key` within a step, or None if absent."""
    pattern = re.compile(r"^(\s*)" + re.escape(key) + r"\s*:\s*(.*)$")
    for index, line in enumerate(entry):
        match = pattern.match(line)
        if not match or len(match.group(1)) != key_indent:
            continue
        value = match.group(2).strip()
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            collected: list[str] = []
            for follow in entry[index + 1 :]:
                if follow.strip() and _indent_of(follow) <= key_indent:
                    break
                collected.append(follow.strip())
            return "\n".join(collected)
        return value
    return None


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

    def test_runs_on_ubuntu_latest(self):
        self.assertRegex(
            read_workflow(),
            r"(?m)^\s*runs-on\s*:\s*[\"']?ubuntu-latest[\"']?\s*$",
            "expected the workflow to run on ubuntu-latest",
        )

    def test_permissions_are_least_privilege(self):
        blocks = extract_permissions_blocks(read_workflow())
        self.assertTrue(
            blocks,
            "expected a `permissions:` block in .github/workflows/ci.yml",
        )
        for block in blocks:
            self.assertEqual(
                block,
                {"contents": "read"},
                "expected the workflow to grant only `contents: read`",
            )

    def test_triggers_are_not_narrowed(self):
        on_block = extract_on_block(read_workflow())
        self.assertTrue(on_block, "expected an `on:` trigger block")
        for narrowing in (
            "branches:",
            "branches-ignore:",
            "paths:",
            "paths-ignore:",
            "tags:",
        ):
            self.assertNotIn(
                narrowing,
                on_block,
                f"the trigger block must not narrow the gate with {narrowing!r}",
            )

    def test_only_public_actions_are_used(self):
        used = re.findall(r"(?m)^\s*uses\s*:\s*(\S+)\s*$", read_workflow())
        self.assertTrue(used, "expected the workflow to use at least one action")
        for action in used:
            self.assertTrue(
                action.startswith("actions/"),
                f"expected only public `actions/*` steps, found {action!r}",
            )

    def test_run_step_command_is_exactly_the_gate(self):
        commands = [
            entry["run"]
            for entry in extract_step_entries(read_workflow())
            if entry["run"] is not None
        ]
        self.assertTrue(commands, "expected the workflow to run a shell command")
        self.assertEqual(
            {command.strip() for command in commands if command.strip()},
            {GATE_COMMAND},
            "expected the only shell command to be the documented gate",
        )

    def test_workflow_has_no_empty_or_noop_steps(self):
        entries = extract_step_entries(read_workflow())
        self.assertTrue(entries, "expected the workflow to define steps")
        shell_steps = 0
        for entry in entries:
            uses = entry["uses"]
            run = entry["run"]
            self.assertTrue(
                uses or (run is not None and run.strip()),
                "expected no empty or no-op steps in the workflow",
            )
            if run is not None:
                shell_steps += 1
                self.assertTrue(
                    run.strip(),
                    "expected no step with an empty command body",
                )
        self.assertEqual(
            shell_steps,
            1,
            "expected only the gate step to run a shell command",
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
