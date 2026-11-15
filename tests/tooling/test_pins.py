"""Probe the shared pin readers with well-formed and malformed pins."""

from support import CommandOptions, RepositoryTest

READ_PIN = '. scripts/build-tools-common.sh; read_pin "$MOLD_VERSION_FILE"'
READ_COMPONENTS = ". scripts/build-tools-common.sh; pinned_toolchain_components"


class PinTests(RepositoryTest):
    """Keep a malformed pin a diagnostic rather than a silent value."""

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
            result.stdout.strip(),
            "2.41.0",
            "A padded pin must be returned without its whitespace",
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

    def test_component_list_is_joined_with_commas(self) -> None:
        """The reader must return the list rustup expects, in order."""
        self.write(
            "rust-toolchain.toml",
            '[toolchain]\ncomponents = [\n  "clippy",\n  "rustfmt",\n]\n',
        )
        result = self.run_command("bash", "-c", READ_COMPONENTS)
        self.assertEqual(
            result.stdout.strip(),
            "clippy,rustfmt",
            "The component list must keep its order",
        )
