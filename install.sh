#!/usr/bin/env bash
# One-liner: curl -fsSL https://raw.githubusercontent.com/abhilash333naidu/skills-catalog-governance/main/install.sh | bash
set -euo pipefail

REPO_URL="https://github.com/abhilash333naidu/skills-catalog-governance.git"
TEMP_ROOT=""
cleanup() {
  if [[ -n "$TEMP_ROOT" && -d "$TEMP_ROOT" ]]; then
    rm -rf "$TEMP_ROOT"
  fi
}
trap cleanup EXIT

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/scripts/catalog_governance.py" ]]; then
  PACKAGE_ROOT="$SCRIPT_DIR"
elif [[ -f "$PWD/scripts/catalog_governance.py" ]]; then
  PACKAGE_ROOT="$PWD"
else
  if ! command -v git >/dev/null 2>&1; then
    echo "error: this is not a checkout and git is required to download the installer source" >&2
    exit 1
  fi
  TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/skills-catalog-governance.XXXXXX")"
  if ! git clone --quiet "$REPO_URL" "$TEMP_ROOT/repo"; then
    echo "error: could not clone $REPO_URL" >&2
    exit 1
  fi
  PACKAGE_ROOT="$TEMP_ROOT/repo"
fi

# git-bash / MSYS paths (e.g. /tmp/... or /c/Users/...) are not understood by
# native Windows python. Convert to a Windows-native path when cygpath exists.
if command -v cygpath >/dev/null 2>&1; then
  PACKAGE_ROOT="$(cygpath -w "$PACKAGE_ROOT")"
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "error: Python 3 is required to install skills-catalog-governance" >&2
  exit 1
fi

# curl | bash consumes the script on stdin. Reconnect the child to the terminal
# when available so the Python install picker can still read a selection.
if [[ -t 0 && -r /dev/tty ]]; then
  "$PYTHON" "$PACKAGE_ROOT/scripts/catalog_governance.py" install "$@" </dev/tty
else
  "$PYTHON" "$PACKAGE_ROOT/scripts/catalog_governance.py" install "$@"
fi
