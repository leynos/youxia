"""Probe fake capabilities without modifying the host toolchain or linker."""

import shutil

from support import CommandOptions, RepositoryTest


class BuildToolsTests(RepositoryTest):
    """Keep the checker read-only and the installer fail-closed."""

    def setUp(self) -> None:
        """Provide recording tool executables in the child process PATH."""
        super().setUp()
        self.env["BUILD_TOOLS_PREFIX"] = str(self.repo)
        self.env["PATH"] = str(self.repo / "bin") + ":" + self.env["PATH"]
        self.write("bin/uname", "#!/bin/sh\necho Linux\n", executable=True)
        for tool, answer in (
            ("mold", "mold 0.0.1"),
            ("clang", "clang"),
            ("ld.lld", "lld"),
        ):
            self.write(
                f"bin/{tool}",
                f"#!/bin/sh\necho {tool} >> calls\necho '{answer}'\n",
                executable=True,
            )
        self.write(
            "bin/curl", "#!/bin/sh\necho curl >> effects\nexit 99\n", executable=True
        )
        self.rustup()

    def rustup(
        self,
        *,
        toolchain: bool = True,
        component: bool = True,
        installed: str | None = None,
    ) -> None:
        """Fake only the queries accepted by a read-only preflight."""
        channel = "nightly-2026-11-12" if toolchain else "stable"
        components = installed or (
            "clippy\nllvm-tools\nrustc-codegen-cranelift\nrustfmt"
            if component
            else "rustfmt"
        )
        self.write(
            "bin/rustup",
            f"""#!/bin/bash
echo "$*" >> queries
[ "$RUSTUP_AUTO_INSTALL" = 0 ] || exit 91
case "$1 $2" in
  "toolchain list") echo '{channel}' ;;
  "component list") printf '%s\n' '{components}' ;;
  *) echo mutation >> effects; exit 92 ;;
esac
""",
            executable=True,
        )

    def cargo(self, version: str | None) -> None:
        """Fake only the launcher's cargo-nextest version query."""
        answer = (
            f'echo "cargo-nextest {version}"; exit 0'
            if version is not None
            else "exit 1"
        )
        self.write(
            "bin/cargo",
            f"""#!/bin/bash
echo cargo >> calls
[ "$1 $2" = "nextest --version" ] || exit 97
{answer}
""",
            executable=True,
        )

    def test_checker_accepts_available_tools_and_only_warns_on_mold_pin(self) -> None:
        """Accept available tools, warn on the mold pin, and install nothing."""
        result = self.make("check-build-tools")
        self.assertIn("does not match the pin", result.stdout)
        self.assertFalse(
            (self.repo / "effects").exists(),
            "Checks must not install tools or download anything",
        )
        self.assertIn("component list", (self.repo / "queries").read_text())

    def test_cargo_nextest_must_satisfy_the_pinned_release(self) -> None:
        """The profile's `global-timeout` needs the release that added it."""
        for version, message, expected in (
            ("0.9.100", "cargo-nextest 0.9.100", 0),
            ("0.9.99", "is older than the pinned 0.9.100", "failure"),
        ):
            with self.subTest(version=version):
                self.cargo(version)
                result = self.make(
                    "check-build-tools", command=CommandOptions(expected=expected)
                )
                self.assertIn(
                    message,
                    result.stdout,
                    "The check must report the pinned cargo-nextest release",
                )

    def test_absent_cargo_nextest_keeps_the_cargo_fallback(self) -> None:
        """A missing runner is a supported fallback, not a broken toolchain."""
        self.cargo(None)
        result = self.make("check-build-tools")
        self.assertIn(
            "falls back to cargo test",
            result.stdout,
            "An absent cargo-nextest must be reported as the supported fallback",
        )

    def test_missing_toolchain_and_components_are_failures(self) -> None:
        """Fail on a missing toolchain or component without triggering installs."""
        for has_toolchain, has_components, message in (
            (False, True, "is not installed"),
            (True, False, "component clippy is not installed"),
        ):
            with self.subTest(toolchain=has_toolchain):
                self.rustup(toolchain=has_toolchain, component=has_components)
                result = self.make(
                    "check-rust-toolchain", command=CommandOptions(expected="failure")
                )
                self.assertIn(message, result.stdout)
                self.assertFalse(
                    (self.repo / "effects").exists(),
                    "Missing capabilities must never trigger installs",
                )

    def test_unusable_linkers_fail(self) -> None:
        """Fail when a present linker cannot report its version."""
        for tool, target, message in (
            ("mold", "check-build-tools", "cannot report its version"),
            ("clang", "check-build-tools", "cannot report its version"),
            ("ld.lld", "check-coverage-tools", "cannot report its version"),
        ):
            with self.subTest(tool=tool):
                path = self.repo / "bin" / tool
                original = path.read_text()
                self.write("bin/" + tool, "#!/bin/sh\nexit 1\n", executable=True)
                result = self.make(target, command=CommandOptions(expected="failure"))
                self.assertIn(message, result.stdout)
                path.write_text(original)

    def test_missing_linkers_do_not_fall_back_to_host_tools(self) -> None:
        """Fail when a linker is absent instead of using host tools."""
        for command in ("bash", "make", "dirname", "grep", "awk", "cat"):
            (self.repo / "bin" / command).symlink_to(shutil.which(command))
        isolated = {"PATH": str(self.repo / "bin")}
        for tool, target, message in (
            ("mold", "check-build-tools", "mold not found"),
            ("clang", "check-build-tools", "clang driver not found"),
            ("ld.lld", "check-coverage-tools", "lld linker not found"),
        ):
            with self.subTest(tool=tool):
                path = self.repo / "bin" / tool
                original = path.read_text()
                path.unlink()
                result = self.make(
                    target, command=CommandOptions(env=isolated, expected="failure")
                )
                self.assertIn(message, result.stdout)
                self.write("bin/" + tool, original, executable=True)

    def calls(self) -> list[str]:
        """Read the tools invoked since the record was last cleared."""
        path = self.repo / "calls"
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8").split()

    def test_toolchain_only_skips_the_linker_and_runner_checks(self) -> None:
        """A toolchain-only check must neither demand nor invoke the linkers."""
        self.cargo("0.9.100")
        self.make("check-build-tools")
        self.assertEqual(
            sorted(set(self.calls())),
            ["cargo", "clang", "mold"],
            "The full check must invoke the tools it reports",
        )
        (self.repo / "calls").unlink()
        only = self.make("check-rust-toolchain").stdout
        self.assertEqual(
            self.calls(),
            ["cargo"],
            "A toolchain-only check must invoke no linker; the single runner"
            " query is make's own parse-time probe of the test command",
        )
        for absent in ("mold", "clang", "lld", "cargo-nextest"):
            self.assertNotIn(
                absent,
                only,
                f"A toolchain-only check must not inspect {absent}",
            )

    def test_coverage_only_invokes_the_coverage_linkers(self) -> None:
        """Coverage needs lld, not mold, and still reports the runner."""
        self.cargo("0.9.100")
        self.make("check-coverage-tools")
        self.assertEqual(
            sorted(set(self.calls())),
            ["cargo", "clang", "ld.lld"],
            "A coverage check must invoke its linkers and the runner only",
        )

    def test_coverage_only_does_not_require_the_cranelift_component(self) -> None:
        """Coverage builds with LLVM, so the backend is not a coverage tool."""
        self.rustup(installed="clippy\nllvm-tools\nrustfmt")
        coverage = self.make("check-coverage-tools")
        self.assertNotIn(
            "rustc-codegen-cranelift",
            coverage.stdout,
            "A coverage check must not require the Cranelift backend",
        )
        full = self.make(
            "check-rust-toolchain",
            command=CommandOptions(expected="failure"),
        )
        self.assertIn(
            "component rustc-codegen-cranelift-preview is not installed",
            full.stdout,
            "The full check must still require every pinned component",
        )

    def test_unknown_mode_and_extra_arguments_are_usage_errors(self) -> None:
        """The checker accepts exactly one optional mode."""
        for arguments in (("--bogus",), ("--toolchain-only", "--coverage-only")):
            with self.subTest(arguments=arguments):
                result = self.run_command(
                    "bash",
                    "scripts/check-build-tools.sh",
                    *arguments,
                    options=CommandOptions(expected="failure"),
                )
                self.assertIn(
                    "usage:",
                    result.stdout,
                    "An unrecognised invocation must print the usage text",
                )
                self.assertIn(
                    "--coverage-only",
                    result.stdout,
                    "The usage text must list the accepted modes",
                )

    def test_installer_rejects_bad_checksum_before_unpacking(self) -> None:
        """Reject a corrupt download before any archive is unpacked."""
        self.write(
            "bin/uname",
            """#!/bin/sh
case "$1" in -s) echo Linux ;; -m) echo x86_64 ;; esac
""",
            executable=True,
        )
        self.write(
            "bin/curl",
            """#!/bin/bash
while [ "$#" -gt 0 ]; do
  if [ "$1" = --output ]; then printf corrupt > "$2"; exit 0; fi
  shift
done
exit 93
""",
            executable=True,
        )
        self.write(
            "bin/tar", "#!/bin/sh\necho unpack >> effects\nexit 94\n", executable=True
        )
        result = self.make(
            "install-build-tools", command=CommandOptions(expected="failure")
        )
        self.assertIn("checksum mismatch", result.stdout)
        self.assertFalse(
            (self.repo / "effects").exists(),
            "A rejected archive must never reach extraction",
        )
