"""Verify fixture children cannot inherit settings that redirect the repository."""

import unittest

from support import child_environment


class ChildEnvironmentTests(unittest.TestCase):
    """Keep the caller's build and Git state out of a fixture repository."""

    def test_host_build_and_git_overrides_are_not_inherited(self) -> None:
        """A caller's flags, startup file and index must not reach the fixture."""
        hostile = {
            "PATH": "/usr/bin",
            "HOME": "/home/example",
            "RUSTFLAGS": "-C target-cpu=native",
            "BASH_ENV": "/tmp/startup.sh",
            "GIT_DIR": "/tmp/caller-repository",
            "GIT_WORK_TREE": "/tmp/caller-worktree",
            "GIT_INDEX_FILE": "/tmp/caller-index",
        }
        environment = child_environment(hostile)
        self.assertEqual(
            environment,
            {"PATH": "/usr/bin", "HOME": "/home/example"},
            "Only overrides that would redirect the fixture may be dropped",
        )
        self.assertNotIn(
            "GIT_INDEX_FILE",
            environment,
            "A fixture's git commands must never write the caller's index",
        )
