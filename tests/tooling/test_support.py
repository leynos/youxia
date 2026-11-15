"""Verify fixture children cannot inherit settings that redirect the repository."""

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import child_environment


class ChildEnvironmentTests(unittest.TestCase):
    """Keep the caller's build and Git state out of a fixture repository."""

    def test_host_build_and_git_overrides_are_not_inherited(self) -> None:
        """A caller's flags, startup file and index must not reach the fixture."""
        hostile = {
            "PATH": "/usr/bin",
            "HOME": "/home/example",
            "RUSTFLAGS": "-C target-cpu=native",
            "CARGO_ENCODED_RUSTFLAGS": "-C\u001ftarget-cpu=native",
            "CARGO_ENCODED_RUSTDOCFLAGS": "--cfg\u001fdocsrs",
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


class GitIsolationTests(unittest.TestCase):
    """Prove a fixture's Git commands cannot write to the caller's repository."""

    def setUp(self) -> None:
        """Create a caller repository beside the fixture that will act on it."""
        directory = tempfile.TemporaryDirectory(prefix="youxia-git-isolation-")
        self.addCleanup(directory.cleanup)
        self.caller = Path(directory.name) / "caller"
        self.fixture = Path(directory.name) / "fixture"
        for repository in (self.caller, self.fixture):
            repository.mkdir()
            self.git(repository, "init", "-q")
        (self.caller / "base.txt").write_text("base\n", encoding="utf-8")
        self.git(self.caller, "add", "-A")
        self.git(
            self.caller,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "base",
        )
        (self.fixture / "fixture.txt").write_text("fixture\n", encoding="utf-8")

    def git(
        self, repository: Path, *arguments: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Run one Git command in a repository and fail loudly on any error."""
        return subprocess.run(
            ("git", *arguments),
            cwd=repository,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    def hostile_environment(self) -> dict[str, str]:
        """Aim every Git override at the caller, as a careless caller could."""
        common = self.caller / ".git"
        return os.environ | {
            "GIT_INDEX_FILE": str(common / "index"),
            "GIT_COMMON_DIR": str(common),
            "GIT_OBJECT_DIRECTORY": str(common / "objects"),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(common / "objects"),
        }

    def caller_state(self) -> dict[str, str]:
        """Fingerprint every file under the caller's `.git` directory.

        Hashing each file rather than listing directory names matters because a
        loose object is written *inside* an existing fan-out directory: a new
        object changes what `git add` wrote but adds no new top-level entry.
        """
        return {
            str(path.relative_to(self.caller)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted((self.caller / ".git").rglob("*"))
            if path.is_file()
        }

    def test_filtered_fixture_git_leaves_the_caller_untouched(self) -> None:
        """Filtering must keep a fixture's `git add` out of the caller's state."""
        pristine = self.caller_state()
        # Precondition: an unfiltered child really does reach the caller, so the
        # assertion below exercises the filter rather than an inert fixture.
        self.git(self.fixture, "add", "-A", env=self.hostile_environment())
        self.assertNotEqual(
            self.caller_state(),
            pristine,
            "The hostile environment must redirect a fixture into the caller",
        )
        self.git(self.caller, "reset", "-q", "--hard")
        restored = self.caller_state()
        isolated = child_environment(self.hostile_environment())
        self.git(self.fixture, "add", "-A", env=isolated)
        self.assertEqual(
            self.caller_state(),
            restored,
            "A filtered fixture must not write to the caller's index or objects",
        )
        self.assertIn(
            "A  fixture.txt",
            self.git(self.fixture, "status", "--porcelain", env=isolated).stdout,
            "The filtered fixture must stage into its own index",
        )
