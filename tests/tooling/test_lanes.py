"""Run real Cargo fixtures through ordinary, compile-time and timeout lanes."""

import tomllib
from support import RepositoryTest


class LaneTests(RepositoryTest):
    """Check selected tests, cleanup boundaries and actual timeout termination."""

    def setUp(self):
        """Create a dependency-free crate whose tests leave observable markers."""
        super().setUp()
        self.write(
            "Cargo.toml",
            """[package]
name = "lane-probe"
version = "0.1.0"
edition = "2024"
""",
        )
        self.write("src/lib.rs", "//! Tooling fixture.\n")

    def probe(self, name, body=None):
        """Create a test that records execution and nextest group ownership."""
        self.write(
            "tests/" + name + ".rs",
            body
            or f"""//! Tooling fixture.
#[test]
fn {name}() {{
    let group = std::env::var("NEXTEST_TEST_GROUP").unwrap_or_default();
    std::fs::write("{name}.ran", group).expect("record fixture execution");
}}
""",
        )

    def test_normal_ui_and_cargo_fallback_retain_tests(self):
        self.probe("ordinary")
        self.probe("compile_probe")
        options = ("CHECK_BUILD_TOOLS=true",)
        self.make("test", *options)
        self.assertTrue(
            (self.repo / "ordinary.ran").exists(),
            "The ordinary lane must execute its integration test",
        )
        self.assertFalse(
            (self.repo / "compile_probe.ran").exists(),
            "nextest must leave compile targets for the UI lane",
        )
        self.make("test-ui", *options)
        self.assertEqual(
            (self.repo / "compile_probe.ran").read_text(),
            "nested-cargo",
            "UI tests must use the serialized group",
        )
        (self.repo / "compile_probe.ran").unlink()
        self.make("test", *options, "TEST_CMD=test")
        self.assertTrue(
            (self.repo / "compile_probe.ran").exists(),
            "Cargo fallback must not silently drop compile targets",
        )

    def test_empty_ui_lane_is_an_explicit_noop(self):
        result = self.make("test-ui", "CHECK_BUILD_TOOLS=true")
        self.assertIn("nothing to run", result.stdout)

    def test_coverage_exclusion_preserves_targets_and_refuses_conflicts(self):
        self.probe("ordinary")
        self.probe("compile_probe")
        self.run_command("bash", "scripts/exclude-ui-targets.sh")
        config = self.repo / ".config/nextest.toml"
        first = config.read_bytes()
        self.run_command("bash", "scripts/exclude-ui-targets.sh")
        self.assertEqual(config.read_bytes(), first, "Exclusion must be idempotent")
        self.run_command("cargo", "nextest", "run")
        self.assertTrue(
            (self.repo / "ordinary.ran").exists(),
            "Coverage selection must retain ordinary tests",
        )
        self.assertFalse(
            (self.repo / "compile_probe.ran").exists(),
            "The shared coverage route must not execute UI tests",
        )
        self.make("test-ui", "CHECK_BUILD_TOOLS=true")
        self.assertTrue(
            (self.repo / "compile_probe.ran").exists(),
            "The UI profile must override coverage's default filter",
        )
        self.assertTrue(
            (self.repo / "tests/compile_probe.rs").exists(),
            "Exclusion must never remove target sources",
        )
        config.write_text(
            config.read_text().replace("not binary(compile_*)", "test(ordinary)")
        )
        conflicting = config.read_bytes()
        self.run_command("bash", "scripts/exclude-ui-targets.sh", expected="failure")
        self.assertEqual(
            config.read_bytes(),
            conflicting,
            "A conflicting filter must be preserved for diagnosis",
        )

    def test_coverage_overrides_the_development_cranelift_profile(self):
        self.write(
            ".cargo/config.toml",
            """[unstable]
codegen-backend = true
[profile.dev]
codegen-backend = "cranelift"
""",
        )
        self.write(
            "src/lib.rs", "//! Coverage fixture.\npub fn answer() -> u32 { 42 }\n"
        )
        self.write(
            "src/main.rs",
            "//! Mirror the application coverage boundary.\n"
            "fn main() { std::hint::black_box(lane_probe::answer()); }\n",
        )
        self.probe(
            "ordinary",
            """//! Exercise instrumented library code.
#[test]
fn covered() { assert_eq!(lane_probe::answer(), 42, "Fixture answer must be 42"); }
""",
        )
        sysroot = self.run_command("rustc", "--print", "sysroot").stdout.strip()
        host = self.run_command("rustc", "-vV").stdout.split("host: ")[1].split()[0]
        linker_dir = f"{sysroot}/lib/rustlib/{host}/bin/gcc-ld"
        self.env["PATH"] = linker_dir + ":" + self.env["PATH"]
        # Instrumenting the fixture compiles it from scratch, so a cold build
        # can outlast the harness's one-minute default while compiler admission
        # queues it behind unrelated work. Keep the run bounded, but wide enough
        # that the assertion tests instrumentation rather than queue latency.
        self.make("coverage", "CHECK_COVERAGE_TOOLS=true", timeout=300)
        self.assertRegex(
            (self.repo / "lcov.info").read_text(),
            r"(?m)^FNDA:[1-9]\d*,",
            "The public coverage route must produce instrumented data",
        )

    def test_timeouts_terminate_a_hanging_test(self):
        config = self.repo / ".config/nextest.toml"
        text = config.read_text()
        profile = tomllib.loads(text)["profile"]["default"]
        self.assertGreater(
            profile["slow-timeout"]["terminate-after"],
            0,
            "Per-test termination must be enabled",
        )
        self.assertIn("global-timeout", profile, "The full run must also be bounded")
        self.probe(
            "hanging",
            """//! Deliberately stalled timeout fixture.
#[test]
fn hanging() {
    std::thread::sleep(std::time::Duration::from_secs(60));
}
""",
        )
        for period, total, message in (
            ("100ms", "3s", "timeout"),
            ("180s", "100ms", "global timeout"),
        ):
            with self.subTest(limit=message):
                config.write_text(
                    text.replace('"180s"', f'"{period}"')
                    .replace('"5s"', '"100ms"')
                    .replace('"90m"', f'"{total}"')
                )
                result = self.run_command("cargo", "nextest", "run", expected="failure")
                self.assertIn(
                    message,
                    result.stdout.lower(),
                    "The configured limit must terminate a built test",
                )
