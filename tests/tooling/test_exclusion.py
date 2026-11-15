"""Exercise the coverage exclusion at the edges of a real checkout."""

from support import CommandOptions, RepositoryTest


class ExclusionTests(RepositoryTest):
    """Report the states the exclusion script has to refuse or skip."""

    def setUp(self) -> None:
        """Keep a compile-time target so only the configuration varies."""
        super().setUp()
        self.write("tests/compile_probe.rs", "//! Compile-time contract fixture.\n")
        self.config = self.repo / ".config/nextest.toml"

    def test_missing_config_is_reported(self) -> None:
        """A checkout with targets but no profile cannot be excluded."""
        self.config.unlink()
        result = self.run_command(
            "bash",
            "scripts/exclude-ui-targets.sh",
            options=CommandOptions(expected="failure"),
        )
        self.assertIn(
            "which is missing",
            result.stdout,
            "The script must name the configuration it needs",
        )
        self.assertFalse(
            self.config.exists(),
            "A missing configuration must not be invented",
        )

    def test_missing_default_profile_is_reported(self) -> None:
        """Another profile must not stand in for the default one."""
        original = self.config.read_text()
        self.config.write_text(
            original.replace("[profile.default]", "[profile.other]"),
            encoding="utf-8",
        )
        renamed = self.config.read_bytes()
        result = self.run_command(
            "bash",
            "scripts/exclude-ui-targets.sh",
            options=CommandOptions(expected="failure"),
        )
        self.assertIn(
            "has no [profile.default] table",
            result.stdout,
            "The script must report the table it could not find",
        )
        self.assertEqual(
            self.config.read_bytes(),
            renamed,
            "A file without the default profile must be left alone",
        )

    def test_no_compile_targets_leaves_the_configuration_alone(self) -> None:
        """A checkout without compile-time targets needs no exclusion."""
        (self.repo / "tests/compile_probe.rs").unlink()
        original = self.config.read_bytes()
        result = self.run_command("bash", "scripts/exclude-ui-targets.sh")
        self.assertIn(
            "coverage runs every test",
            result.stdout,
            "The script must say why it changed nothing",
        )
        self.assertEqual(
            self.config.read_bytes(),
            original,
            "A run with no targets must not rewrite the profile",
        )
