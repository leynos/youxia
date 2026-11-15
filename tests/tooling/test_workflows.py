"""Exercise the shared workflow scanner against valid and deliberately leaking callers."""

import shutil

from support import ROOT, CommandOptions, RepositoryTest
from workflow_fixtures import (
    LATE_MOLD_INSTALL,
    MOLD_INSTALL_LISTED_AFTER_WITH,
    MOLD_INSTALL_OPENING_THE_STEP,
    MOLD_KEY_IN_A_RUN_STEP,
    MOLD_KEY_ON_A_LOOKALIKE_ACTION,
    MOLD_KEY_ON_AN_UNRELATED_ACTION,
    MOLD_KEY_QUOTED_IN_A_BLOCK,
    MOLD_KEY_QUOTED_IN_A_COMMENTED_BLOCK,
    MOLD_KEY_UNDER_ENV,
    MULTILINE_TEST_STEP,
    MULTILINE_TEST_STEP_WITH_COMMENTED_HEADER,
    SETUP_STEP_QUOTED_IN_A_HEREDOC,
    UNRELATED_MOLD_INSTALL,
)
from workflow_lane import jobs_missing_mold, runs_test_lane, test_lane_jobs

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

    def assert_fixture_installs_mold(self, fixture: str, expectation: str) -> None:
        """Assert a fixture owns a test lane the checker reports as provisioned."""
        self.assertEqual(
            [name for name, _ in test_lane_jobs(fixture)],
            ["test"],
            "The fixture must still own exactly one test lane",
        )
        self.assertEqual(jobs_missing_mold(fixture), [], expectation)

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

    def test_multiline_test_step_with_a_commented_header_requires_the_linker(
        self,
    ) -> None:
        """A block header may carry a comment without hiding the lane."""
        self.assert_fixture_is_missing_mold(
            MULTILINE_TEST_STEP_WITH_COMMENTED_HEADER,
            "A commented block header must not hide the test lane",
        )

    def test_mold_install_must_belong_to_an_action_step(self) -> None:
        """A `run:` step that only names the key installs nothing."""
        self.assert_fixture_is_missing_mold(
            MOLD_KEY_IN_A_RUN_STEP,
            "A key outside an action step must not satisfy the lane",
        )

    def test_mold_key_outside_the_with_mapping_installs_nothing(self) -> None:
        """`env:` is not the action's input mapping, whatever it holds."""
        self.assert_fixture_is_missing_mold(
            MOLD_KEY_UNDER_ENV,
            "The input must be a `with:` key of the setup action",
        )

    def test_setup_step_quoted_in_a_heredoc_installs_nothing(self) -> None:
        """A quoted step item cannot stand in for a real installation."""
        self.assert_fixture_is_missing_mold(
            SETUP_STEP_QUOTED_IN_A_HEREDOC,
            "A step quoted inside a heredoc must not satisfy the check",
        )

    def test_mold_install_must_target_the_setup_action(self) -> None:
        """An unrelated action cannot install mold by accepting the key."""
        self.assert_fixture_is_missing_mold(
            MOLD_KEY_ON_AN_UNRELATED_ACTION,
            "Only the shared setup action can satisfy the installation",
        )

    def test_mold_install_must_use_the_shared_action_path(self) -> None:
        """A third-party action reusing the name installs nothing here."""
        self.assert_fixture_is_missing_mold(
            MOLD_KEY_ON_A_LOOKALIKE_ACTION,
            "A look-alike action must not satisfy the installation",
        )

    def test_action_reference_quoted_in_a_block_installs_nothing(self) -> None:
        """Text inside a shell block cannot stand in for an action step."""
        self.assert_fixture_is_missing_mold(
            MOLD_KEY_QUOTED_IN_A_BLOCK,
            "A quoted action reference must not satisfy the installation",
        )

    def test_action_reference_quoted_in_a_commented_block_installs_nothing(
        self,
    ) -> None:
        """A commented block header still opens a body of quoted text."""
        self.assert_fixture_is_missing_mold(
            MOLD_KEY_QUOTED_IN_A_COMMENTED_BLOCK,
            "A quoted action reference in a commented block must not count",
        )

    def test_the_setup_action_may_list_its_input_before_uses(self) -> None:
        """Key order inside a step mapping does not change what it installs."""
        self.assert_fixture_installs_mold(
            MOLD_INSTALL_LISTED_AFTER_WITH,
            "A step that lists `with:` before `uses:` still installs mold",
        )

    def test_the_setup_action_may_open_the_step(self) -> None:
        """The action reference may be the step's opening key."""
        self.assert_fixture_installs_mold(
            MOLD_INSTALL_OPENING_THE_STEP,
            "A step written as `- uses:` still installs mold",
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