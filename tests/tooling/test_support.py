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
            "GIT_COMMON_DIR": "/tmp/caller-common",
            "GIT_OBJECT_DIRECTORY": "/tmp/caller-objects",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/tmp/caller-alternate-objects",
        }
        environment = child_environment(hostile)
        self.assertEqual(
            environment,
            {"PATH": "/usr/bin", "HOME": "/home/example"},
            "Only overrides that would redirect the fixture may be dropped",
        )
        for name in (
            "GIT_INDEX_FILE",
            "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        ):
            self.assertNotIn(
                name,
                environment,
                f"A fixture's git commands must never reach the caller's {name}",
            )
