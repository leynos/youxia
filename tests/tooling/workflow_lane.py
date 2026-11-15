"""Inspect a workflow's jobs for a mold installation before the test lane.

`make test` links development binaries with mold, and its `check-build-tools`
prerequisite stops the lane when the linker is absent. A workflow that runs the
lane therefore has to install mold in the same job and before the test step.
These helpers answer that question from the workflow text alone: the tooling
suite takes no third-party dependency, so it reads the job heading and the step
item rather than parsing the whole document as YAML.
"""

import re
from typing import NamedTuple

JOB_HEADING = re.compile(r"(?m)^  (?P<name>[A-Za-z0-9_-]+):\s*$")
RUN_KEY = re.compile(r"(?m)^(?P<indent>[ ]*)(?:- )?run:[ ]*(?P<value>.*)$")
TEST_COMMAND = re.compile(r"^make test(?:\s|$)")
BLOCK_MARKERS = frozenset({"|", ">", "|-", ">-", "|+", ">+"})
STEP_ITEM = re.compile(r"(?m)^(?P<indent>[ ]*)-[ ](?P<opening>.*)$")
# A line whose value is a block marker opens a body of quoted text. `run: |` is
# the common case, and the chomping variants appear in real workflows too.
BLOCK_OPENER = re.compile(r"^[ ]*(?:-[ ]+)?[A-Za-z0-9_.-]+:[ ]*[|>][+-]?[ ]*$")
MOLD_INSTALL = re.compile(r"^[ ]+install-mold:[ ]*['\"]?true['\"]?[ ]*$")
# `install-mold` is an input to the shared Rust setup action. An unrelated
# action receiving the key ignores it, so only the reviewed action path may
# claim the installation; a third-party action that reuses the name does not.
# The action may open the step (`- uses:`) or continue it (`uses:`).
MOLD_INSTALLING_ACTION = re.compile(
    r"[ ]*(?:-[ ]+)?uses:[ ]*leynos/shared-actions/\.github/actions/setup-rust(?:@|\s|$)"
)


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


def test_lane_offsets(block: str) -> list[int]:
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
    return bool(test_lane_offsets(workflow_text))


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


def step_boundaries(block: str) -> list[tuple[int, int]]:
    """Split a job block into its step items, each with its end offset.

    Steps share one dash indentation under `steps:`, so a later item at the
    same indentation ends the current step. A more indented dash belongs to the
    step's own content, such as a list inside a `run:` block.
    """
    items = list(STEP_ITEM.finditer(block))
    boundaries = []
    for index, item in enumerate(items):
        end = len(block)
        for later in items[index + 1 :]:
            if later.group("indent") == item.group("indent"):
                end = later.start()
                break
        boundaries.append((item.start(), end))
    return boundaries


def action_lines(step: str) -> list[str]:
    """Return a step's own YAML lines, without the bodies of block scalars.

    A `run: |` block may quote an action reference or an `install-mold` key
    inside a shell script. Those lines are text rather than keys, so a check
    that read them would accept a step that installs nothing.
    """
    kept: list[str] = []
    body_indent: int | None = None
    for line in step.splitlines():
        if _in_block_body(line, body_indent):
            continue
        kept.append(line)
        if BLOCK_OPENER.match(line):
            body_indent = _indent(line)
    return kept


def _installs_mold(step: str) -> bool:
    """Say whether a step hands the input key to the shared setup action.

    Both keys must be the step's own YAML. Reading every line of the step
    rather than only the lines above the input keeps the answer independent of
    key order, because a step mapping may list `with:` before `uses:`.
    """
    lines = action_lines(step)
    installs = any(MOLD_INSTALLING_ACTION.match(line) for line in lines)
    requested = any(MOLD_INSTALL.match(line) for line in lines)
    return installs and requested


def mold_installation_offsets(block: str) -> list[int]:
    """Locate the steps that install mold through the shared setup action."""
    return [
        start
        for start, end in step_boundaries(block)
        if _installs_mold(block[start:end])
    ]


def installs_mold_before_each_test_step(block: str) -> bool:
    """Say whether every test step has a mold installation earlier in its job.

    A later install cannot help: the step that links with mold has already
    failed by then, so ordering is part of the contract rather than incidental.
    """
    installations = mold_installation_offsets(block)
    return all(
        any(installed < step for installed in installations)
        for step in test_lane_offsets(block)
    )


def jobs_missing_mold(workflow_text: str) -> list[str]:
    """Name test-lane jobs that do not install mold before their test steps."""
    return [
        name
        for name, block in test_lane_jobs(workflow_text)
        if not installs_mold_before_each_test_step(block)
    ]