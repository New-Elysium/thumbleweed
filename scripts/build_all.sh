#!/usr/bin/env bash
# build_all.sh — Build wheels for every supported Python interpreter.
#
# Usage:
#   ./build_all.sh          # build wheels only
#   ./build_all.sh --upload # build + upload to PyPI via twine
#
# Prerequisites:
#   - Python 3.10, 3.11, 3.12, 3.13, 3.13-nogil, 3.14, 3.14-nogil
#     installed and on PATH
#   - A venv at .venv with maturin (and twine if using --upload)
#   - Rust toolchain (stable)
set -euo pipefail

# cd to project root (one level up from scripts/)
cd "$(dirname "$0")/.."

# Activate the project venv (provides maturin + twine)
if [ ! -d .venv ]; then
    echo "ERROR: .venv not found. Run: python3 -m venv .venv && . .venv/bin/activate && pip install maturin twine"
    exit 1
fi
# shellcheck source=/dev/null
. .venv/bin/activate

# Clean previous artifacts
rm -rf dist/
mkdir -p dist/

# All supported interpreters (GIL + free-threaded)
INTERPRETERS=(
    python3.10
    python3.11
    python3.12
    python3.13
    python3.13-nogil
    python3.14
    python3.14-nogil
)

for py in "${INTERPRETERS[@]}"; do
    if ! command -v "$py" >/dev/null 2>&1; then
        echo "SKIP: $py not found on PATH"
        continue
    fi

    echo "========================================"
    echo "Building for $py ($($py --version 2>&1))"
    echo "========================================"
    maturin build --release --out dist --interpreter "$py" --skip-auditwheel
    echo ""
done

# Build source distribution
echo "========================================"
echo "Building source distribution"
echo "========================================"
maturin sdist --out dist
echo ""

# Validate all artifacts
echo "========================================"
echo "Validating with twine check"
echo "========================================"
twine check dist/*.whl dist/*.tar.gz
echo ""

# Summary
echo "========================================"
echo "Built artifacts:"
echo "========================================"
ls -lh dist/

# Optional upload
if [ "${1:-}" = "--upload" ]; then
    echo ""
    echo "Uploading to PyPI..."
    twine upload dist/*
fi
