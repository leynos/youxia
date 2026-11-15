"""Exercise the shared checker against valid and deliberately leaking callers."""

import re
import shutil
from typing import NamedTuple

from support import ROOT, CommandOptions, RepositoryTest

JOB_HEADING = re.compile(r"(?m)^  (?P<name>[A-Za-z0-9_-]+):\s*$")
RUN_KEY = re.compile(r"(?m)^(?P<indent>[ ]*)(?:- )?run:[ ]*(?P<value>.*)$")
TEST_COMMAND = re.compile(r"^make test(?:\s|$)")
BLOCK_MARKERS = frozenset({"|", ">", "|-", ">-", "|+", ">+"})
MOLD_INSTALL = re.compile(r"(?m)^\s+install-mold:\s*['\"]?true['\"]?$")
STEP_ITEM = re.compile(r"(?m)^(?P<indent>[ ]*)-[ ](?P<opening>.*)$")
# `install-mold` is an input to the shared Rust setup action. An unrelated
# action receiving the key ignores it, so only that action may claim the
# installation.
MOLD_INSTALLING_ACTION = re.compile(r"uses:[ ]*\S*setup-rust(?:@|\s|$)")

# Mold is installed in `lint` only. A check that searches the whole workflow
# would accept the `test` job's `make test` step, which cannot link.
UNRELATED_MOLD_INSTALL = """\
name: Fixture

on: push

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
        with:
          install-mold: 'true'
  test:
    runs-on: ubuntu-latest
    steps:
      - run: make test
"""

# A job can list the install after the step that needs it. The ordering
# matters: `make test` has already stopped for a missing linker by the time
# the later step would have installed it.
LATE_MOLD_INSTALL = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: make test
      - uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
        with:
          install-mold: 'true'
"""

# Workflows commonly write commands under a block scalar. A pattern that reads
# only the text after `run:` on the same line would miss this job entirely and
# accept it without a linker installation.
MULTILINE_TEST_STEP = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo preparing
          make test
"""

# `install-mold` is an input to the shared setup action. An action without that
# input ignores the key, so a check that accepts any action step would pass a
# job that never installs the linker.
MOLD_KEY_ON_AN_UNRELATED_ACTION = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/cache@v4
        with:
          path: ~/.cache
          install-mold: 'true'
      - run: make test
"""

# `install-mold` is an input to the shared setup action. Naming the key inside
# a shell step provisions nothing, so a check that searches only for the key
# would accept a job that never installs the linker.
MOLD_KEY_IN_A_RUN_STEP = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: |
          install-mold: 'true'
      - run: make test
"""


class _LineScan(NamedTuple):
    """State that one workflow line leaves the scan in."""

    body_indent: int | None
    runs_test: bool


def _indent(line: str) -> int:
    """Count the leading spaces that decide block-scalar membership."""
    return len(line) - len(line.lstrip())


def _in_block_body(line: str, body_indent: int | None) -> bool:
    """Say whether a line continues an already-open block scalar."""
    if body_indent is None:
        return False
    return not line.strip() or _indent(line) > body_indent


def _inline_command(line: str) -> tuple[int | None, str | None]:
    """Split a `run:` line into any block it opens and any command it holds."""
    run = RUN_KEY.match(line)
    if run is None:
        return None, None
    value = run.group("value").strip()
    if value in BLOCK_MARKERS:
        return _indent(run.group("indent")), None
    return None, value


def _classify_line(line: str, body_indent: int | None) -> _LineScan:
    """Track block state and report whether the line invokes `make test`."""
    if _in_block_body(line, body_indent):
        return _LineScan(body_indent, bool(TEST_COMMAND.match(line.strip())))
    opened, command = _inline_command(line)
    return _LineScan(opened, command is not None and bool(TEST_COMMAND.match(command)))


def test_step_offsets(block: str) -> list[int]:
    """Locate every `make test` invocation in one job, inline or in a block.

    Workflows write the lane either as `run: make test` or as a `run: |` block
    whose following, more indented lines hold the commands. Tracking the block
    indent keeps a job's other steps and its comments out of the search.
    """
    offsets: list[int] = []
    body_indent: int | None = None
    offset = 0
    for line in block.splitlines(keepends=True):
        body_indent, runs_test = _classify_line(line, body_indent)
        if runs_test:
            offsets.append(offset)
        offset += len(line)
    return offsets


def runs_test_lane(workflow_text: str) -> bool:
    """Say whether a workflow or job invokes the public test lane."""
    return bool(test_step_offsets(workflow_text))


def test_lane_jobs(workflow_text: str) -> list[tuple[str, str]]:
    """Name the jobs that run `make test`, with each job's own block.

    A text splitter is sufficient here: a workflow indents job identifiers
    under `jobs:` by exactly two spaces and job content by four or more, so a
    two-space mapping key that starts a line begins a job.
    """
    headings = [
        (match.start(), match.group("name"))
        for match in JOB_HEADING.finditer(workflow_text)
    ]
    jobs = []
    for index, (start, name) in enumerate(headings):
        end = (
            headings[index + 1][0] if index + 1 < len(headings) else len(workflow_text)
        )
        block = workflow_text[start:end]
        if runs_test_lane(block):
            jobs.append((name, block))
    return jobs


def _step_before(block: str, offset: int) -> tuple[int, str] | None:
    """Return the start offset and opening text of the step holding `offset`."""
    items = list(STEP_ITEM.finditer(block, 0, offset))
    if not items:
        return None
    last = items[-1]
    return last.start(), last.group("opening")


def _installs_mold(block: str, start: int, offset: int) -> bool:
    """Say whether the step opening at `start` hands the key to the installer.

    A `run:` step that merely names the key provisions nothing, and neither
    does an action that has no such input. The installation counts only when
    the step holding the key invokes the shared Rust setup action.
    """
    return bool(MOLD_INSTALLING_ACTION.search(block, start, offset))


def mold_installation_offsets(block: str) -> list[int]:
    """Locate steps that install mold through the shared setup action."""
    offsets: list[int] = []
    for match in MOLD_INSTALL.finditer(block):
        step = _step_before(block, match.start())
        if step is None:
            continue
        start, _ = step
        if _installs_mold(block, start, match.start()):
            offsets.append(start)
    return offsets


def installs_mold_before_each_test_step(block: str) -> bool:
    """Say whether every test step has a mold installation earlier in its job.

    A later install cannot help: the step that links with mold has already
    failed by then, so ordering is part of the contract rather than incidental.
    """
    installations = mold_installation_offsets(block)
    return all(
        any(installed < step for installed in installations)
        for step in test_step_offsets(block)
    )


def jobs_missing_mold(workflow_text: str) -> list[str]:
    """Name test-lane jobs that do not install mold before their test steps."""
    return [
        name
        for name, block in test_lane_jobs(workflow_text)
        if not installs_mold_before_each_test_step(block)
    ]


class WorkflowTests(RepositoryTest):
    """Verify the public checker invocation without copying its private rules."""

    def assert_fixture_is_missing_mold(self, fixture: str, expectation: str) -> None:
        """Assert a fixture owns a test lane that the checker reports as unprovisioned."""
        self.assertEqual(
            [name for name, _ in test_lane_jobs(fixture)],
            ["test"],
            "The fixture must still own exactly one test lane",
        )
        self.assertEqual(jobs_missing_mold(fixture), ["test"], expectation)

    def test_workflows_running_the_test_lane_install_the_dev_linker(self) -> None:
        """Provision mold wherever a workflow exercises the public test lane.

        `make test` links development binaries with mold, and its
        `check-build-tools` prerequisite stops the lane when the linker is
        absent. A workflow that runs the lane therefore has to install it in
        the same job and before the test step, otherwise the hosted job reports
        a missing host capability instead of a test regression.
        """
        lane_workflows = {
            path.name: path.read_text()
            for path in sorted((ROOT / ".github/workflows").glob("*.yml"))
            if runs_test_lane(path.read_text())
        }
        self.assertTrue(
            lane_workflows,
            "At least one workflow must exercise the public `make test` lane",
        )
        for name, text in lane_workflows.items():
            with self.subTest(workflow=name):
                self.assertTrue(
                    test_lane_jobs(text),
                    f"{name} matched the test-lane pattern but no job owns it",
                )
                self.assertEqual(
                    jobs_missing_mold(text),
                    [],
                    f"{name}: these jobs run `make test` without installing mold",
                )

    def test_mold_check_requires_installation_in_the_test_job(self) -> None:
        """An unrelated job's mold install must not satisfy a test-lane job."""
        self.assert_fixture_is_missing_mold(
            UNRELATED_MOLD_INSTALL,
            "Installation in another job must not satisfy the check",
        )

    def test_mold_install_must_precede_the_test_step(self) -> None:
        """An install listed after `make test` cannot satisfy the lane."""
        self.assert_fixture_is_missing_mold(
            LATE_MOLD_INSTALL,
            "A later installation must not satisfy an earlier test step",
        )

    def test_multiline_test_step_requires_the_linker(self) -> None:
        """A block-scalar lane must still be checked for the installation."""
        self.assert_fixture_is_missing_mold(
            MULTILINE_TEST_STEP,
            "A block-scalar lane without mold must be reported",
        )

    def test_mold_install_must_belong_to_an_action_step(self) -> None:
        """A `run:` step that only names the key installs nothing."""
        self.assert_fixture_is_missing_mold(
            MOLD_KEY_IN_A_RUN_STEP,
            "A key outside an action step must not satisfy the lane",
        )

    def test_mold_install_must_target_the_setup_action(self) -> None:
        """An unrelated action cannot install mold by accepting the key."""
        self.assert_fixture_is_missing_mold(
            MOLD_KEY_ON_AN_UNRELATED_ACTION,
            "Only the shared setup action can satisfy the installation",
        )

    def test_shared_checker_rejects_a_pr_secret_leak(self) -> None:
        shutil.copytree(ROOT / ".github", self.repo / ".github")
        self.make("test-workflow-contracts", command=CommandOptions(timeout=120))
        path = self.repo / ".github/workflows/ci.yml"
        original = path.read_text()
        path.write_text(
            original.replace(
                "      BUILD_PROFILE: debug",
                "      BUILD_PROFILE: debug\n      LEAK: ${{ secrets.CS_ACCESS_TOKEN }}",
            )
        )
        result = self.make(
            "test-workflow-contracts",
            command=CommandOptions(expected="failure", timeout=120),
        )
        self.assertIn(
            "exactly one workflow may contact CodeScene",
            result.stdout,
            "A PR credential leak must break the coverage contract",
        )
        path.write_text(original)
        self.make("test-workflow-contracts", command=CommandOptions(timeout=120))
