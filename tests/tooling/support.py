"""Disposable repositories for public tooling integration tests."""

import os
import shutil
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RepositoryTest(unittest.TestCase):
    """Own a repository and child environment that are restored after a test."""

    def setUp(self):
        """Create the smallest repository that can exercise the public gates."""
        directory = tempfile.TemporaryDirectory(prefix="youxia-tooling-")
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if key
            not in {
                "RUSTFLAGS",
                "RUSTDOCFLAGS",
                "CARGO_TARGET_DIR",
                "CARGO_BUILD_TARGET_DIR",
                "MAKEFLAGS",
                "NEXTEST_PROFILE",
                # Make runs recipes through bash, and a startup file named by
                # BASH_ENV can rewrite PATH inside the child. That would shadow
                # fixtures which stand in for host tools, so the child starts
                # without one.
                "BASH_ENV",
            }
        }
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

    def write(self, name, text, *, executable=False):
        """Write one fixture; executable fixtures can stand in for host tools."""
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if executable:
            path.chmod(0o755)
        return path

    def run_command(self, *arguments, expected=0, env=None, timeout=60):
        """Run a bounded child; report its complete output on failure."""
        with subprocess.Popen(
            arguments,
            cwd=self.repo,
            env=self.env | (env or {}),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process:
            try:
                output, _ = process.communicate(timeout=timeout)
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
        if expected == 0:
            self.assertEqual(result.returncode, 0, result.stdout)
        elif expected == "failure":
            self.assertNotEqual(result.returncode, 0, result.stdout)
        else:
            self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def make(self, target, *options, **kwargs):
        """Exercise the copied public Makefile without installing prerequisites."""
        return self.run_command(
            "make", "--no-print-directory", target, *options, **kwargs
        )

    def track(self, *paths):
        """Stage fixtures because lint selection deliberately follows Git."""
        self.run_command("git", "add", "--", *paths)
