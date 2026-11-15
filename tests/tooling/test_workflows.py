"""Exercise the shared checker against valid and deliberately leaking callers."""

import re
import shutil

from support import ROOT, CommandOptions, RepositoryTest

JOB_HEADING = re.compile(r"(?m)^  (?P<name>[A-Za-z0-9_-]+):\s*$")
TEST_LANE_STEP = re.compile(r"(?m)^\s*(?:-\s*)?run:.*\bmake test(?:\s|$)")
MOLD_INSTALL = re.compile(r"(?m)^\s+install-mold:\s*['\"]?true['\"]?$")

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
        if TEST_LANE_STEP.search(block):
            jobs.append((name, block))
    return jobs


def installs_mold_before_each_test_step(block: str) -> bool:
    """Say whether every test step has a mold installation earlier in its job.

    A later install cannot help: the step that links with mold has already
    failed by then, so ordering is part of the contract rather than incidental.
    """
    installations = [match.start() for match in MOLD_INSTALL.finditer(block)]
    return all(
        any(installed < step for installed in installations)
        for step in (match.start() for match in TEST_LANE_STEP.finditer(block))
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
            if TEST_LANE_STEP.search(path.read_text())
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
        self.assertEqual(
            [name for name, _ in test_lane_jobs(UNRELATED_MOLD_INSTALL)],
            ["test"],
            "Only the job that runs `make test` counts as a test lane",
        )
        self.assertEqual(
            jobs_missing_mold(UNRELATED_MOLD_INSTALL),
            ["test"],
            "Installation in another job must not satisfy the check",
        )

    def test_mold_install_must_precede_the_test_step(self) -> None:
        """An install listed after `make test` cannot satisfy the lane."""
        self.assertEqual(
            [name for name, _ in test_lane_jobs(LATE_MOLD_INSTALL)],
            ["test"],
            "The late-install fixture still owns a test lane",
        )
        self.assertEqual(
            jobs_missing_mold(LATE_MOLD_INSTALL),
            ["test"],
            "A later installation must not satisfy an earlier test step",
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
