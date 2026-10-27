
#!/usr/bin/env bash
set -euo pipefail

echo "P35_START"

python3 p35_matrix.py

test -f LNZCertificatePayloadP33.lean
test -f LNZCertificateBridge.lean

lake exe cache get
lake build

echo "P35_BUILD_DEPENDENCIES"

lake env lean -o LNZCertificateBridge.olean \
  LNZCertificateBridge.lean

lake env lean -o LNZCertificatePayloadP33.olean \
  LNZCertificatePayloadP33.lean

export LEAN_PATH=".:${LEAN_PATH:-}"

echo "P35_CHECK_GENERATED_FILES"

shopt -s nullglob
files=(p35_generated/P35_*.lean)

if (( ${#files[@]} != 7 )); then
  echo "ERROR: expected exactly 7 Lean files"
  exit 1
fi

if grep -R -n -E '\b(sorry|sorryAx|admit)\b' \
  p35_generated/*.lean; then
  echo "FORBIDDEN_PROOF_PLACEHOLDER"
  exit 1
fi

for f in "${files[@]}"; do
  echo "LEAN_CHECK $f"
  lake env lean "$f"
done

echo "P35_LEAN_COMPILE_ALL_PASS"
