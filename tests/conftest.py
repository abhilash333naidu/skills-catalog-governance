"""Test-suite configuration.

Sets COVERAGE_PROCESS_START so every CLI subprocess spawned by the tests
(sys.executable scripts/catalog_governance.py ...) starts its own coverage
collector via scripts/sitecustomize.py. Without this, subprocess coverage is
invisible and destructive paths (move_tree, golden_gate_report) look untested.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("COVERAGE_PROCESS_START", os.path.join(ROOT, ".coveragerc"))