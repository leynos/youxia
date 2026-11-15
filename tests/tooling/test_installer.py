"""Exercise the installer's success, component and failure paths."""

import hashlib
import io
import shutil
import tarfile

from support import CommandOptions, RepositoryTest

MOLD_VERSION = "9.9.9"
ARCHIVE = f"mold-{MOLD_VERSION}-x86_64-linux.tar.gz"
TOOLCHAIN = "nightly-2026-11-12"
COMPONENTS = "clippy,llvm-tools-preview,rustc-codegen-cranelift-preview,rustfmt"


class InstallerTests(RepositoryTest):
    """Install into a fixture prefix from local fakes and a real archive."""

    def setUp(self) -> None:
        """Serve a checksummed archive and record what rustup is asked to do."""
        super().setUp()
        self.env["BUILD_TOOLS_PREFIX"] = str(self.repo / "prefix")
        self.env["PATH"] = str(self.repo / "bin") + ":" + self.env["PATH"]
        self.write(
            "bin/uname",
            """#!/bin/sh
case "$1" in -s) echo Linux ;; -m) echo x86_64 ;; esac
""",
            executable=True,
        )
        self.write("tools/mold/VERSION", MOLD_VERSION + "\n")
        self.archive = self.repo / "served-archive.tar.gz"
        self.write_archive()
        self.write("tools/mold/SHA256SUMS", f"{self.digest()}  {ARCHIVE}\n")
        self.write(
            "bin/curl",
            f"""#!/bin/bash
out=
while [ "$#" -gt 0 ]; do
  case "$1" in --output) out=$2; shift 2 ;; *) shift ;; esac
done
[ -n "$out" ] || exit 95
cp "{self.archive}" "$out"
""",
            executable=True,
        )
        self.write(
            "bin/rustup",
            '#!/bin/sh\nprintf "%s\\n" "$*" >> rustup-args\n',
            executable=True,
        )

    def write_archive(self) -> None:
        """Create the release archive the fake download will serve."""
        payload = b"#!/bin/sh\nexit 0\n"
        with tarfile.open(self.archive, "w:gz") as archive:
            for name in ("bin/mold", "lib/mold/mold-wrapper.so"):
                info = tarfile.TarInfo(f"mold-{MOLD_VERSION}-x86_64-linux/{name}")
                info.size = len(payload)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(payload))

    def digest(self) -> str:
        """Return the digest the pin file has to record."""
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def recorded(self) -> str:
        """Return the rustup invocations the installer made."""
        return (self.repo / "rustup-args").read_text()

    def test_installer_unpacks_the_archive_and_installs_the_toolchain(self) -> None:
        """A verified archive lands under the prefix with its top level stripped."""
        self.make("install-build-tools", command=CommandOptions(timeout=120))
        self.assertTrue(
            (self.repo / "prefix/bin/mold").exists(),
            "The archive's bin directory must land directly under the prefix",
        )
        self.assertFalse(
            (self.repo / f"prefix/mold-{MOLD_VERSION}-x86_64-linux").exists(),
            "The versioned top-level directory must be stripped",
        )
        recorded = self.recorded()
        self.assertIn(
            f"toolchain install {TOOLCHAIN} --profile minimal",
            recorded,
            "The installer must install the pinned toolchain",
        )
        self.assertIn(
            f"--component {COMPONENTS}",
            recorded,
            "The installer must request every pinned component",
        )

    def test_cranelift_target_requests_the_pinned_component(self) -> None:
        """`make install-cranelift` adds the backend for the pinned toolchain."""
        self.make("install-cranelift", command=CommandOptions(timeout=60))
        self.assertIn(
            f"component add rustc-codegen-cranelift-preview --toolchain {TOOLCHAIN}",
            self.recorded(),
            "The Cranelift target must name the component and the toolchain",
        )
        self.assertFalse(
            (self.repo / "prefix").exists(),
            "Installing the backend must not download the linker",
        )

    def test_cranelift_failure_names_the_repair_target(self) -> None:
        """A refused component install points at the target that retries it."""
        self.write("bin/rustup", "#!/bin/sh\nexit 1\n", executable=True)
        result = self.make(
            "install-cranelift", command=CommandOptions(expected="failure")
        )
        self.assertIn(
            "retry with: make install-cranelift",
            result.stdout,
            "The failure must name the target that retries the install",
        )

    def test_missing_rustup_fails_with_its_diagnostic(self) -> None:
        """A host without rustup must fail rather than install half a toolchain."""
        (self.repo / "bin/rustup").unlink()
        isolated = {"PATH": str(self.repo / "bin")}
        for command in (
            "awk",
            "bash",
            "cat",
            "cp",
            "dirname",
            "grep",
            "gzip",
            "make",
            "mkdir",
            "mktemp",
            "rm",
            "sha256sum",
            "tar",
        ):
            (self.repo / "bin" / command).symlink_to(shutil.which(command))
        result = self.make(
            "install-build-tools",
            command=CommandOptions(env=isolated, expected="failure", timeout=120),
        )
        self.assertIn(
            "rustup not found on PATH",
            result.stdout,
            "The installer must report the missing rustup",
        )
