"""Disposable repositories for public tooling integration tests."""

import os
import shutil
import signal
import subprocess
import tempfile
import unittest
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[2]

# Host settings that would redirect a fixture. Build flags and target
# directories move its output, Makefile options change its target graph, and
# the Git entries are repository-local overrides that Git applies whatever the
# working directory is.
EXCLUDED_ENVIRONMENT = frozenset(
    {
        "RUSTFLAGS",
        "RUSTDOCFLAGS",
        "CARGO_TARGET_DIR",
        "CARGO_BUILD_TARGET_DIR",
        "MAKEFLAGS",
        "NEXTEST_PROFILE",
        "BASH_ENV",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    }
)


@dataclass(frozen=True)
class CommandOptions:
    """Bound one child command and state the result the caller expects.

    `expected` is either an exit status or `"failure"` for any non-zero exit.
    """

    expected: int | Literal["failure"] = 0
    timeout: float = 60
    env: Mapping[str, str] | None = None


DEFAULT_OPTIONS = CommandOptions()


def child_environment(source: Mapping[str, str]) -> dict[str, str]:
    """Copy an environment without settings that would redirect a fixture.

    `BASH_ENV` matters because Make runs recipes through bash: a startup file
    named there can rewrite `PATH` inside the child and shadow fixture tools.
    The `GIT_*` entries matter because a caller's `GIT_INDEX_FILE`, for
    example, would make the fixture's `git add` write to the caller's index.
    """
    return {
        key: value for key, value in source.items() if key not in EXCLUDED_ENVIRONMENT
    }


class RepositoryTest(unittest.TestCase):
    """Own a repository and child environment that are restored after a test."""

    def setUp(self) -> None:
        """Create the smallest repository that can exercise the public gates."""
        directory = tempfile.TemporaryDirectory(prefix="youxia-tooling-")
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        self.env = child_environment(os.environ)
        self.env["RUSTUP_TOOLCHAIN"] = "nightly-2026-11-12"
        for name in (
            "Makefile",
            "rust-toolchain.toml",
            ".yamllint-estate.yml",
            ".yamllint.yml",
            ".config",
            "scripts",
            "tools",
        ):
            source = ROOT / name
            target = self.repo / name
            if source.is_dir():
                shutil.copytree(source, target)
            elif source.exists():
                shutil.copy2(source, target)
        self.run_command("git", "init", "-q")

    def write(self, name: str, text: str, *, executable: bool = False) -> Path:
        """Write one fixture; executable fixtures can stand in for host tools."""
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if executable:
            path.chmod(0o755)
        return path

    def run_command(
        self,
        *arguments: str,
        options: CommandOptions = DEFAULT_OPTIONS,
    ) -> subprocess.CompletedProcess[str]:
        """Run a bounded child; report its complete output on failure."""
        with subprocess.Popen(
            arguments,
            cwd=self.repo,
            env=self.env | (options.env or {}),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process:
            try:
                output, _ = process.communicate(timeout=options.timeout)
            except BaseException:
                # A failed test must also stop nested Cargo and test processes
                # before its temporary checkout is removed.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                raise
        result = subprocess.CompletedProcess(arguments, process.returncode, output)
        if options.expected == 0:
            self.assertEqual(result.returncode, 0, result.stdout)
        elif options.expected == "failure":
            self.assertNotEqual(result.returncode, 0, result.stdout)
        else:
            self.assertEqual(result.returncode, options.expected, result.stdout)
        return result

    def make(
        self,
        target: str,
        *options: str,
        command: CommandOptions = DEFAULT_OPTIONS,
    ) -> subprocess.CompletedProcess[str]:
        """Exercise the copied public Makefile without installing prerequisites."""
        return self.run_command(
            "make",
            "--no-print-directory",
            target,
            *options,
            options=command,
        )

    def track(self, *paths: str) -> None:
        """Stage fixtures because lint selection deliberately follows Git."""
        self.run_command("git", "add", "--", *paths)
