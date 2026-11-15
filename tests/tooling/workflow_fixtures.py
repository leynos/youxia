"""Workflow samples that exercise the shared mold-installation check.

Each fixture is a complete workflow: the checker reads the job heading and
the step items, so a sample has to carry the job it describes. The comments
record the defect each sample is meant to expose.
"""

# Mold is installed in `lint` only. A check that searches the whole workflow
# would accept the `test` job's `make test` step, which cannot link.
UNRELATED_MOLD_INSTALL = """\
name: Fixture

on: push

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
        with:
          install-mold: 'true'
  test:
    runs-on: ubuntu-latest
    steps:
      - run: make test
"""

# A job can list the install after the step that needs it. The ordering
# matters: `make test` has already stopped for a missing linker by the time
# the later step would have installed it.
LATE_MOLD_INSTALL = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: make test
      - uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
        with:
          install-mold: 'true'
"""

# Workflows commonly write commands under a block scalar. A pattern that reads
# only the text after `run:` on the same line would miss this job entirely and
# accept it without a linker installation.
MULTILINE_TEST_STEP = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo preparing
          make test
"""

# A block header may carry a trailing comment, as in `run: | # write a sample`.
# A pattern that expects the marker alone misses the block, so its body reads as
# step keys and the lane it runs is invisible to the checker.
MULTILINE_TEST_STEP_WITH_COMMENTED_HEADER = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: | # write a sample
          echo preparing
          make test
"""

# `install-mold` is an input to the shared setup action. An action without that
# input ignores the key, so a check that accepts any action step would pass a
# job that never installs the linker.
MOLD_KEY_ON_AN_UNRELATED_ACTION = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/cache@v4
        with:
          path: ~/.cache
          install-mold: 'true'
      - run: make test
"""

# A third-party action may reuse the shared action's name. Only the reviewed
# `leynos/shared-actions` path is known to install mold, so a name match alone
# must not satisfy the check.
MOLD_KEY_ON_A_LOOKALIKE_ACTION = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: someone/setup-rust@v1
        with:
          install-mold: 'true'
      - run: make test
"""

# A block can quote the action path or the input key inside a shell script, and
# a `with:` value of the setup action can itself be a block. Both are text
# rather than keys, so a check that read raw step text would accept a job that
# installs nothing.
MOLD_KEY_QUOTED_IN_A_BLOCK = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: |
          cat <<'EOF' > snippet.yml
          uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
          EOF
          install-mold: 'true'
      - uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
        with:
          script: |
            install-mold: 'true'
      - run: make test
"""

# The same quoting can hide behind a commented block header, which is still a
# block scalar. Missing the header makes those lines look like step keys.
MOLD_KEY_QUOTED_IN_A_COMMENTED_BLOCK = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: | # write a sample
          cat <<'EOF' > snippet.yml
          uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
          EOF
          install-mold: 'true'
      - run: make test
"""

# `install-mold` is an input to the shared setup action. Naming the key inside
# a shell step provisions nothing, so a check that searches only for the key
# would accept a job that never installs the linker.
MOLD_KEY_IN_A_RUN_STEP = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: |
          install-mold: 'true'
      - run: make test
"""

# `install-mold` is an input, so it belongs under the action's `with:` mapping.
# An `env:` variable of that name reaches the action as environment, not as the
# input, so a check that matched any indented key would accept it.
MOLD_KEY_UNDER_ENV = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
        env:
          install-mold: 'true'
      - run: make test
"""

# YAML mapping keys may appear in either order. A check that read only the
# lines above the input would reject a step that does install the linker.
MOLD_INSTALL_LISTED_AFTER_WITH = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - with:
          install-mold: 'true'
        uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
      - run: make test
"""

# The action may also open the step. A check that expected the reference to
# continue a step would report this valid installation as missing.
MOLD_INSTALL_OPENING_THE_STEP = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
        with:
          install-mold: 'true'
      - run: make test
"""

# A shell heredoc can hold a complete `- uses:` step, dash and mapping alike.
# A step splitter that reads every dash makes that quoted item a step of its
# own, and the slice then reaches the checker without its `run: |` header, so
# the quoted installation looks real.
SETUP_STEP_QUOTED_IN_A_HEREDOC = """\
name: Fixture

on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: |
          cat <<'EOF' > sample.yml
          - uses: leynos/shared-actions/.github/actions/setup-rust@0000000000000000000000000000000000000000
            with:
              install-mold: 'true'
          EOF
      - run: make test
"""

