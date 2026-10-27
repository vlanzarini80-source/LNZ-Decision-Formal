
#!/usr/bin/env bash
set -euo pipefail

python3 p35_matrix.py

lake update
lake exe cache get
lake build

for f in p35_generated/P35_*.lean; do
  echo "LEAN_CHECK $f"
  lake env lean "$f"
done

if grep -R -n -E '\b(sorry|sorryAx|admit)\b' \
  p35_generated/*.lean; then
  echo 'FORBIDDEN_PROOF_PLACEHOLDER'
  exit 1
fi

echo 'P35_LEAN_COMPILE_ALL_PASS'
