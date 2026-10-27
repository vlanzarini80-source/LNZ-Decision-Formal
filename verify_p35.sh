
#!/usr/bin/env bash
set -euo pipefail

echo "P35_START"

cd "$(dirname "$0")"

python3 p35_matrix.py

test -f LNZCertificateBridge.lean
test -f LNZCertificatePayloadP33.lean

lake exe cache get

export LEAN_PATH="$(pwd):${LEAN_PATH:-}"

echo "P35_BUILD_DEPENDENCIES"

lake env lean -o LNZCertificateBridge.olean \
  LNZCertificateBridge.lean

test -f LNZCertificateBridge.olean

lake env lean -o LNZCertificatePayloadP33.olean \
  LNZCertificatePayloadP33.lean

test -f LNZCertificatePayloadP33.olean

echo "P35_CHECK_GENERATED_FILES"

shopt -s nullglob
files=(p35_generated/P35_*.lean)

if (( ${#files[@]} != 7 )); then
  echo "ERROR: expected exactly 7 Lean files"
  exit 1
fi

if grep -R -n -E '(^|[^[:alnum:]_])(sorry|sorryAx|admit)([^[:alnum:]_]|$)' \
  p35_generated/*.lean; then
  echo "FORBIDDEN_PROOF_PLACEHOLDER"
  exit 1
fi

for f in "${files[@]}"; do
  echo "LEAN_CHECK $f"
  lake env lean "$f"
done

echo "P35_LEAN_COMPILE_ALL_PASS"
