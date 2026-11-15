"""Probe fake capabilities without modifying the host toolchain or linker."""

import shutil

from support import RepositoryTest


class BuildToolsTests(RepositoryTest):
    """Keep the checker read-only and the installer fail-closed."""

    def setUp(self):
        """Provide recording tool executables in the child process PATH."""
        super().setUp()
        self.env["BUILD_TOOLS_PREFIX"] = str(self.repo)
        self.env["PATH"] = str(self.repo / "bin") + ":" + self.env["PATH"]
        self.write("bin/uname", "#!/bin/sh\necho Linux\n", executable=True)
        self.write("bin/mold", "#!/bin/sh\necho 'mold 0.0.1'\n", executable=True)
        self.write("bin/clang", "#!/bin/sh\necho clang\n", executable=True)
        self.write("bin/ld.lld", "#!/bin/sh\necho lld\n", executable=True)
        self.write(
            "bin/curl", "#!/bin/sh\necho curl >> effects\nexit 99\n", executable=True
        )
        self.rustup()

    def rustup(self, *, toolchain=True, component=True):
        """Fake only the queries accepted by a read-only preflight."""
        channel = "nightly-2026-11-12" if toolchain else "stable"
        components = (
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

    def test_checker_accepts_available_tools_and_only_warns_on_mold_pin(self):
        result = self.make("check-build-tools")
        self.assertIn("does not match the pin", result.stdout)
        self.assertFalse(
            (self.repo / "effects").exists(),
            "Checks must not install tools or download anything",
        )
        self.assertIn("component list", (self.repo / "queries").read_text())

    def test_missing_toolchain_and_components_are_failures(self):
        for has_toolchain, has_components, message in (
            (False, True, "is not installed"),
            (True, False, "component clippy is not installed"),
        ):
            with self.subTest(toolchain=has_toolchain):
                self.rustup(toolchain=has_toolchain, component=has_components)
                result = self.make("check-rust-toolchain", expected="failure")
                self.assertIn(message, result.stdout)
                self.assertFalse(
                    (self.repo / "effects").exists(),
                    "Missing capabilities must never trigger installs",
                )

    def test_unusable_linkers_fail(self):
        for tool, target, message in (
            ("mold", "check-build-tools", "cannot report its version"),
            ("clang", "check-build-tools", "cannot report its version"),
            ("ld.lld", "check-coverage-tools", "cannot report its version"),
        ):
            with self.subTest(tool=tool):
                path = self.repo / "bin" / tool
                original = path.read_text()
                self.write("bin/" + tool, "#!/bin/sh\nexit 1\n", executable=True)
                result = self.make(target, expected="failure")
                self.assertIn(message, result.stdout)
                path.write_text(original)

    def test_missing_linkers_do_not_fall_back_to_host_tools(self):
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
                result = self.make(target, env=isolated, expected="failure")
                self.assertIn(message, result.stdout)
                self.write("bin/" + tool, original, executable=True)

    def test_installer_rejects_bad_checksum_before_unpacking(self):
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
        result = self.make("install-build-tools", expected="failure")
        self.assertIn("checksum mismatch", result.stdout)
        self.assertFalse(
            (self.repo / "effects").exists(),
            "A rejected archive must never reach extraction",
        )
