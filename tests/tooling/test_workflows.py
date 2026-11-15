"""Exercise the shared checker against valid and deliberately leaking callers."""

import shutil

from support import ROOT, RepositoryTest


class WorkflowTests(RepositoryTest):
    """Verify the public checker invocation without copying its private rules."""

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
