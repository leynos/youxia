"""Bounded property checks for the tooling's invariant-bearing scripts.

The neighbouring example modules pin one case per contract. These checks
generate many small inputs from a fixed seed instead, so a rule is not carried
by a single hand-picked example. Generation stays in the standard library
because the tooling harness takes no third-party dependency.
"""

import hashlib
import io
import random
import tarfile

import tomllib
from support import CommandOptions, RepositoryTest

SEED = 20261115
FILTER = "not binary(compile_*)"
READ_PIN = '. scripts/build-tools-common.sh; read_pin "$MOLD_VERSION_FILE"'
READ_COMPONENTS = ". scripts/build-tools-common.sh; pinned_toolchain_components"
TOKEN_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789.-_"


def digest(rng: random.Random) -> str:
    """Draw a checksum-shaped value that cannot match the served archive."""
    return "".join(rng.choice("0123456789abcdef") for _ in range(64))


def archive_bytes(version: str) -> bytes:
    """Build the release archive shape the installer expects to unpack."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name in ("bin/mold", "lib/mold/mold-wrapper.so"):
            payload = b"placeholder\n"
            member = tarfile.TarInfo(f"mold-{version}-x86_64-linux/{name}")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    return buffer.getvalue()


def token(rng: random.Random) -> str:
    """Draw one whitespace-free value of the kind a pin holds."""
    return "".join(rng.choice(TOKEN_ALPHABET) for _ in range(rng.randint(1, 8)))


def tokens(rng: random.Random, count: int) -> list[str]:
    """Draw `count` distinct whitespace-free values."""
    drawn: list[str] = []
    while len(drawn) < count:
        candidate = token(rng)
        if candidate not in drawn:
            drawn.append(candidate)
    return drawn


def padding(rng: random.Random) -> str:
    """Draw the harmless surrounding whitespace a pin may carry."""
    return "".join(rng.choice(" \t") for _ in range(rng.randint(0, 3)))


class PinProperties(RepositoryTest):
    """Show the pin readers agree with generated values, not just examples."""

    def test_single_token_pins_round_trip_through_any_padding(self) -> None:
        """Every single token is returned exactly once its padding is trimmed."""
        rng = random.Random(SEED)
        for value in tokens(rng, 8):
            with self.subTest(pin=value):
                self.write(
                    "tools/mold/VERSION", f"{padding(rng)}{value}{padding(rng)}\n"
                )
                result = self.run_command("bash", "-c", READ_PIN)
                self.assertEqual(
                    result.stdout,
                    value,
                    "A single-token pin must be returned unchanged",
                )

    def test_two_tokens_on_one_line_are_always_refused(self) -> None:
        """Any whitespace between two tokens makes the pin ambiguous."""
        rng = random.Random(SEED)
        for first, second in zip(tokens(rng, 8), tokens(rng, 8)):
            with self.subTest(pin=f"{first} {second}"):
                separator = rng.choice((" ", "\t", "  "))
                self.write("tools/mold/VERSION", f"{first}{separator}{second}\n")
                result = self.run_command(
                    "bash", "-c", READ_PIN, options=CommandOptions(expected="failure")
                )
                self.assertIn(
                    "version pin contains whitespace",
                    result.stdout,
                    "A pin holding two tokens must be refused",
                )

    def test_multi_line_pins_are_always_refused(self) -> None:
        """Two or more lines are refused however many values they hold."""
        rng = random.Random(SEED)
        for count in range(2, 6):
            with self.subTest(lines=count):
                values = tokens(rng, count)
                self.write("tools/mold/VERSION", "".join(f"{v}\n" for v in values))
                result = self.run_command(
                    "bash", "-c", READ_PIN, options=CommandOptions(expected="failure")
                )
                self.assertIn(
                    "expected one line in version pin",
                    result.stdout,
                    "A multi-line pin must name the line count it found",
                )

    def test_component_lists_round_trip_in_order(self) -> None:
        """A generated component list comes back joined, in the order given."""
        rng = random.Random(SEED)
        for count in range(1, 5):
            with self.subTest(components=count):
                names = tokens(rng, count)
                quoted = ",\n".join(f'  "{name}"' for name in names)
                self.write(
                    "rust-toolchain.toml",
                    f"[toolchain]\ncomponents = [\n{quoted},\n]\n",
                )
                result = self.run_command("bash", "-c", READ_COMPONENTS)
                self.assertEqual(
                    result.stdout,
                    ",".join(names),
                    "The component list must keep its order and join with commas",
                )

    def test_components_holding_a_separator_are_refused(self) -> None:
        """A component containing a comma or a space cannot be passed on."""
        rng = random.Random(SEED)
        for name in tokens(rng, 6):
            for separator in (",", " "):
                with self.subTest(component=name, separator=separator):
                    self.write(
                        "rust-toolchain.toml",
                        f'[toolchain]\ncomponents = ["{name}{separator}{name}"]\n',
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
                        "A component holding a separator must be refused",
                    )


ENTRIES = (
    "retries = 2",
    "fail-fast = false",
    'slow-timeout = { period = "60s" }',
    "# an operator note",
    "",
    "test-threads = 4",
)
EXTRA_TABLES = (
    "[profile.ui]\nretries = 1\n",
    "[profile.ci]\nfail-fast = true\n",
    '[profile.default.junit]\npath = "junit.xml"\n',
)
PREFIXES = ("", "# a top-level note\n")


def layout(rng: random.Random) -> str:
    """Build a nextest configuration with a default table and varied content."""
    prefix = rng.choice(PREFIXES)
    chosen = rng.sample(ENTRIES, rng.randint(0, len(ENTRIES)))
    extras = rng.sample(EXTRA_TABLES, rng.randint(0, 2))
    return prefix + "\n".join(["[profile.default]", *chosen, "", *extras]) + "\n"


class ExclusionProperties(RepositoryTest):
    """Show the exclusion edit preserves generated profiles rather than one."""

    def setUp(self) -> None:
        """Keep a compile-time target so only the configuration varies."""
        super().setUp()
        self.write("tests/compile_probe.rs", "//! Compile-time contract fixture.\n")
        self.config = self.repo / ".config/nextest.toml"

    def run_exclusion(self, expected: int | str = 0) -> str:
        """Run the script and return its output."""
        return self.run_command(
            "bash",
            "scripts/exclude-ui-targets.sh",
            options=CommandOptions(expected=expected),
        ).stdout

    def test_generated_layouts_gain_only_the_filter(self) -> None:
        """Every generated profile keeps its content and gains one key."""
        rng = random.Random(SEED)
        for case in range(6):
            with self.subTest(case=case):
                text = layout(rng)
                self.config.write_text(text, encoding="utf-8")
                before = tomllib.loads(text)
                self.assertIn("now excludes", self.run_exclusion())
                updated = self.config.read_text(encoding="utf-8")
                parsed = tomllib.loads(updated)
                self.assertEqual(
                    parsed["profile"]["default"]["default-filter"],
                    FILTER,
                    "The generated profile must carry the exclusion filter",
                )
                before["profile"]["default"]["default-filter"] = FILTER
                self.assertEqual(
                    parsed,
                    before,
                    "No other profile content may change",
                )

    def test_a_second_run_leaves_generated_layouts_byte_identical(self) -> None:
        """The edit is a fixed point, so a repeated run writes nothing."""
        rng = random.Random(SEED)
        for case in range(4):
            with self.subTest(case=case):
                self.config.write_text(layout(rng), encoding="utf-8")
                self.run_exclusion()
                settled = self.config.read_bytes()
                self.assertIn("already excludes", self.run_exclusion())
                self.assertEqual(
                    self.config.read_bytes(),
                    settled,
                    "A settled profile must not be rewritten",
                )

    def test_a_foreign_filter_is_refused_without_an_edit(self) -> None:
        """A project's own filter is never replaced, only reported."""
        rng = random.Random(SEED)
        for case in range(4):
            with self.subTest(case=case):
                foreign = f'default-filter = "not binary({token(rng)}*)"'
                text = "[profile.default]\n" + foreign + "\n"
                self.config.write_text(text, encoding="utf-8")
                output = self.run_exclusion("failure")
                self.assertIn("sets its own default-filter", output)
                self.assertEqual(
                    self.config.read_text(encoding="utf-8"),
                    text,
                    "A refused run must leave the project's filter in place",
                )


class ChecksumProperties(RepositoryTest):
    """Show checksum-row validation accepts exactly one matching row."""

    VERSION = "9.9.9"

    def setUp(self) -> None:
        """Serve a real archive through fakes that record what they did."""
        super().setUp()
        self.env["BUILD_TOOLS_PREFIX"] = str(self.repo / "prefix")
        self.env["PATH"] = str(self.repo / "bin") + ":" + self.env["PATH"]
        self.write(
            "bin/uname",
            '#!/bin/sh\ncase "$1" in -s) echo Linux ;; -m) echo x86_64 ;; esac\n',
            executable=True,
        )
        self.write("bin/rustup", "#!/bin/sh\nexit 0\n", executable=True)
        self.write(
            "bin/tar", "#!/bin/sh\necho unpack >> effects\nexit 0\n", executable=True
        )
        self.write("tools/mold/VERSION", f"{self.VERSION}\n")
        self.archive = self.repo / "served.tar.gz"
        self.archive.write_bytes(archive_bytes(self.VERSION))
        self.write(
            "bin/curl",
            f"""#!/bin/bash
while [ "$#" -gt 0 ]; do
  if [ "$1" = --output ]; then cp '{self.archive}' "$2"; exit 0; fi
  shift
done
exit 93
""",
            executable=True,
        )
        self.name = f"mold-{self.VERSION}-x86_64-linux.tar.gz"
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def install(self, rows: list[str], expected: int | str = 0) -> str:
        """Run the installer against one generated checksum file."""
        self.write("tools/mold/SHA256SUMS", "".join(f"{row}\n" for row in rows))
        return self.make(
            "install-build-tools", command=CommandOptions(expected=expected)
        ).stdout

    def reached_extraction(self) -> bool:
        """Report whether the fake `tar` was asked to unpack anything."""
        return (self.repo / "effects").exists()

    def test_rows_for_other_archives_stop_before_extraction(self) -> None:
        """A file with no row for the selected archive provisions nothing."""
        rng = random.Random(SEED)
        for case in range(3):
            with self.subTest(case=case):
                other = f"mold-{token(rng)}-aarch64-linux.tar.gz"
                output = self.install([f"{digest(rng)}  {other}"], expected="failure")
                self.assertIn("no checksum recorded", output)
                self.assertFalse(
                    self.reached_extraction(),
                    "A missing checksum must stop before extraction",
                )

    def test_a_single_matching_row_installs(self) -> None:
        """One row for the selected archive is the only accepted shape."""
        output = self.install([f"{self.digest}  {self.name}"])
        self.assertIn("installed mold", output)
        self.assertTrue(
            self.reached_extraction(),
            "A single matching row must reach extraction",
        )

    def test_duplicate_matching_rows_are_refused(self) -> None:
        """Two rows for one archive make the pin ambiguous."""
        rng = random.Random(SEED)
        for case in range(2):
            with self.subTest(case=case):
                (self.repo / "effects").unlink(missing_ok=True)
                output = self.install(
                    [f"{self.digest}  {self.name}", f"{digest(rng)}  {self.name}"],
                    expected="failure",
                )
                self.assertIn("refusing to guess", output)
                self.assertFalse(
                    self.reached_extraction(),
                    "An ambiguous pin must stop before extraction",
                )

    def test_a_matching_row_with_a_wrong_digest_is_refused(self) -> None:
        """A row that names the archive but not its bytes is a mismatch."""
        rng = random.Random(SEED)
        output = self.install([f"{digest(rng)}  {self.name}"], expected="failure")
        self.assertIn("checksum mismatch", output)
        self.assertFalse(
            self.reached_extraction(),
            "A mismatched digest must stop before extraction",
        )
