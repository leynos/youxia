"""Check that the public lint and formatting targets reject real defects."""

from support import CommandOptions, RepositoryTest


class LintTests(RepositoryTest):
    """Exercise the tool boundary, including its selection and failure paths."""

    def test_yaml_rejects_defect_and_handles_spaces(self):
        path = "settings with spaces.yaml"
        self.write(path, "key: first\nkey: second\n")
        self.track(path)
        result = self.make("lint-yaml", command=CommandOptions(expected="failure"))
        self.assertIn("duplication of key", result.stdout)
        self.write(path, "on: true\n")
        self.make("lint-yaml")

    def test_actions_reject_invalid_expression(self):
        path = ".github/workflows/test.yml"
        self.write(
            path,
            """name: Fixture
on: push
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo '${{ missing.context }}'
""",
        )
        result = self.make("lint-actions", command=CommandOptions(expected="failure"))
        self.assertIn("undefined variable", result.stdout)
        self.write(
            path,
            (self.repo / path).read_text().replace("missing.context", "github.ref"),
        )
        self.make("lint-actions")

    def test_shell_rejects_defect_and_empty_selection_passes(self):
        self.make("lint-shell")
        path = "scripts/bad name.sh"
        self.write(path, "#!/bin/sh\necho $unquoted\n")
        self.track(path)
        result = self.make("lint-shell", command=CommandOptions(expected="failure"))
        self.assertIn("SC2086", result.stdout)
        self.write(path, '#!/bin/sh\necho "valid"\n')
        self.make("lint-shell")

    def test_missing_lint_tools_fail_with_help(self):
        for target, option, diagnostic in (
            ("lint-yaml", "YAMLLINT", "yamllint is required"),
            ("lint-actions", "ACTIONLINT", "actionlint is required"),
            ("lint-shell", "SHELLCHECK", "shellcheck is required"),
        ):
            with self.subTest(target=target):
                result = self.make(
                    target,
                    option + "=not-installed-youxia",
                    command=CommandOptions(expected="failure"),
                )
                self.assertIn(diagnostic, result.stdout)

    def test_git_failure_is_not_empty_success(self):
        self.write("bin/git", "#!/bin/sh\nexit 23\n", executable=True)
        env = {"PATH": str(self.repo / "bin") + ":" + self.env["PATH"]}
        for target in ("lint-yaml", "lint-shell"):
            with self.subTest(target=target):
                self.make(target, command=CommandOptions(env=env, expected="failure"))

    def test_markdown_check_includes_untracked_and_excludes_ignored(self):
        self.write(".gitignore", "ignored.md\n")
        self.write("ignored.md", "ignored " * 40 + "\n")
        self.write("draft.md", "# Draft\n\n" + "word " * 40 + "\n")
        self.track(".gitignore")
        options = ("CARGO=true", "CHECK_RUST_TOOLCHAIN=true")
        self.make("check-fmt", *options, command=CommandOptions(expected="failure"))
        self.make("fmt", *options)
        self.make("check-fmt", *options)
        self.assertEqual(
            (self.repo / "ignored.md").read_text(),
            "ignored " * 40 + "\n",
            "Ignored prose must be untouched",
        )
