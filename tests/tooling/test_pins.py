"""Probe the shared pin readers with well-formed and malformed pins."""

from support import CommandOptions, RepositoryTest

READ_PIN = '. scripts/build-tools-common.sh; read_pin "$MOLD_VERSION_FILE"'
READ_COMPONENTS = ". scripts/build-tools-common.sh; pinned_toolchain_components"
READ_ARCH = ". scripts/build-tools-common.sh; mold_arch"


def fake_machine(test: RepositoryTest, name: str) -> dict[str, str]:
    """Make `uname -m` report `name` without touching the host."""
    test.write(
        "bin/uname",
        f"#!/bin/sh\nprintf '%s\\n' '{name}'\n",
        executable=True,
    )
    return {"PATH": str(test.repo / "bin") + ":" + test.env["PATH"]}


class PinTests(RepositoryTest):
    """Keep a malformed pin a diagnostic rather than a silent value."""

    def test_missing_pin_file_is_reported(self) -> None:
        """An absent pin must name the file instead of reading as empty."""
        (self.repo / "tools/mold/VERSION").unlink()
        result = self.run_command(
            "bash", "-c", READ_PIN, options=CommandOptions(expected="failure")
        )
        self.assertIn(
            "missing version pin",
            result.stdout,
            "A pin file that does not exist must be reported by name",
        )
        self.assertIn(
            "tools/mold/VERSION",
            result.stdout,
            "The diagnostic must name the file that is missing",
        )

    def test_two_line_pin_is_refused(self) -> None:
        """Adjacent lines must not be concatenated into one version."""
        self.write("tools/mold/VERSION", "2.41.0\n2.41.1\n")
        result = self.run_command(
            "bash", "-c", READ_PIN, options=CommandOptions(expected="failure")
        )
        self.assertIn(
            "expected one line in version pin",
            result.stdout,
            "A multi-line pin must be reported rather than trimmed",
        )

    def test_pin_with_internal_whitespace_is_refused(self) -> None:
        """Two versions on one line are ambiguous, not a value to trim."""
        self.write("tools/mold/VERSION", "2.41.0 2.41.1\n")
        result = self.run_command(
            "bash", "-c", READ_PIN, options=CommandOptions(expected="failure")
        )
        self.assertIn(
            "version pin contains whitespace",
            result.stdout,
            "A pin with an internal space must be reported",
        )

    def test_padded_pin_is_returned_trimmed(self) -> None:
        """Surrounding whitespace is harmless and must not reach the caller."""
        self.write("tools/mold/VERSION", "  2.41.0\t\n")
        result = self.run_command("bash", "-c", READ_PIN)
        self.assertEqual(
            result.stdout,
            "2.41.0",
            "A padded pin must be returned exactly, without its whitespace",
        )

    def test_toolchain_without_components_is_refused(self) -> None:
        """A toolchain pin with no component list must not read as empty."""
        self.write(
            "rust-toolchain.toml",
            '[toolchain]\nchannel = "nightly-2026-11-12"\n',
        )
        result = self.run_command(
            "bash",
            "-c",
            READ_COMPONENTS,
            options=CommandOptions(expected="failure"),
        )
        self.assertIn(
            "could not read components",
            result.stdout,
            "A missing component list must be reported",
        )

    def test_component_with_a_comma_is_refused(self) -> None:
        """A comma inside a component name would silently split the argument."""
        self.write(
            "rust-toolchain.toml",
            '[toolchain]\ncomponents = ["clippy,rustfmt"]\n',
        )
        result = self.run_command(
            "bash",
            "-c",
            READ_COMPONENTS,
            options=CommandOptions(expected="failure"),
        )
        self.assertIn(
            "could not read components",
            result.stdout,
            "A comma inside a component name must be reported",
        )

    def test_component_with_whitespace_is_refused(self) -> None:
        """A space inside a component name would reach rustup as two words."""
        self.write(
            "rust-toolchain.toml",
            '[toolchain]\ncomponents = ["clippy rustfmt"]\n',
        )
        result = self.run_command(
            "bash",
            "-c",
            READ_COMPONENTS,
            options=CommandOptions(expected="failure"),
        )
        self.assertIn(
            "could not read components",
            result.stdout,
            "A space inside a component name must be reported",
        )

    def test_component_list_is_joined_with_commas(self) -> None:
        """The reader must return the list rustup expects, in order."""
        self.write(
            "rust-toolchain.toml",
            '[toolchain]\ncomponents = [\n  "clippy",\n  "rustfmt",\n]\n',
        )
        result = self.run_command("bash", "-c", READ_COMPONENTS)
        self.assertEqual(
            result.stdout,
            "clippy,rustfmt",
            "The component list must be returned exactly and keep its order",
        )


class ArchitectureTests(RepositoryTest):
    """Pin the mold architecture aliases the installer depends on."""

    def test_every_linux_alias_maps_to_its_release_name(self) -> None:
        """Both spellings of each architecture name the same mold archive."""
        for machine, release in (
            ("x86_64", "x86_64"),
            ("amd64", "x86_64"),
            ("aarch64", "aarch64"),
            ("arm64", "aarch64"),
        ):
            with self.subTest(machine=machine):
                result = self.run_command(
                    "bash",
                    "-c",
                    READ_ARCH,
                    options=CommandOptions(env=fake_machine(self, machine)),
                )
                self.assertEqual(
                    result.stdout,
                    release,
                    "The architecture alias must select its release name",
                )

    def test_unsupported_architecture_is_reported(self) -> None:
        """An architecture with no pinned release must not guess one."""
        result = self.run_command(
            "bash",
            "-c",
            READ_ARCH,
            options=CommandOptions(
                env=fake_machine(self, "riscv64"), expected="failure"
            ),
        )
        self.assertIn(
            "unsupported architecture for the pinned mold release",
            result.stdout,
            "An unmapped architecture must be reported rather than defaulted",
        )
        self.assertIn(
            "riscv64",
            result.stdout,
            "The diagnostic must name the machine it could not map",
        )
