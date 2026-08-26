"""Subprocess coverage hook (imported automatically by every Python process).

Coverage.py cannot see into code running in a child process unless the child
starts measuring itself. When the environment variable COVERAGE_PROCESS_START
points at a coverage config file, this module starts the collector at interpreter
startup, so every `sys.executable scripts/catalog_governance.py ...` call the test
suite makes contributes to the combined report.

This file is imported by EVERY python process in the repo's directory scope, so
it must degrade to a no-op (and never break the CLI) when coverage is not
installed or the env var is unset.
"""

import os

if os.environ.get("COVERAGE_PROCESS_START"):
    import coverage

    coverage.process_startup()
