"""Exercise the shared checker against valid and deliberately leaking callers."""

import re
import shutil

from support import ROOT, RepositoryTest


class WorkflowTests(RepositoryTest):
    """Verify the public checker invocation without copying its private rules."""

    def test_workflows_running_the_test_lane_install_the_dev_linker(self):
        """Provision mold wherever a workflow exercises the public test lane.

        `make test` links development binaries with mold, and its
        `check-build-tools` prerequisite stops the lane when the linker is
        absent. A workflow that runs the lane therefore has to install it,
        otherwise the hosted job reports a missing host capability instead of a
        test regression.
        """
        lane_pattern = re.compile(r"(?m)^\s*(?:-\s*)?run:.*\bmake test(?:\s|$)")
        lane_workflows = {
            path.name: path.read_text()
            for path in sorted((ROOT / ".github/workflows").glob("*.yml"))
            if lane_pattern.search(path.read_text())
        }
        self.assertTrue(
            lane_workflows,
            "At least one workflow must exercise the public `make test` lane",
        )
        for name, text in lane_workflows.items():
            with self.subTest(workflow=name):
                self.assertRegex(
                    text,
                    r"(?m)^\s+install-mold:\s*['\"]?true['\"]?$",
                    f"{name} runs `make test`, which needs the mold linker",
                )

    def test_shared_checker_rejects_a_pr_secret_leak(self):
        shutil.copytree(ROOT / ".github", self.repo / ".github")
        self.make("test-workflow-contracts", timeout=120)
        path = self.repo / ".github/workflows/ci.yml"
        original = path.read_text()
        path.write_text(
            original.replace(
                "      BUILD_PROFILE: debug",
                "      BUILD_PROFILE: debug\n      LEAK: ${{ secrets.CS_ACCESS_TOKEN }}",
            )
        )
        result = self.make("test-workflow-contracts", expected="failure", timeout=120)
        self.assertIn(
            "exactly one workflow may contact CodeScene",
            result.stdout,
            "A PR credential leak must break the coverage contract",
        )
        path.write_text(original)
        self.make("test-workflow-contracts", timeout=120)
