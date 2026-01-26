#!/usr/bin/env bash
set -euo pipefail

SITE="${SITE:-https://sc691583.github.io/gatekeeperops-site}"
BUNDLE="${1:-bundle_readiness_go_nogo}"

WORK="_tmp_${BUNDLE}"
rm -rf "$WORK"
mkdir -p "$WORK/$BUNDLE"

echo "[1/3] Download verifier..."
curl -sSL -o "$WORK/verify.py" "$SITE/bundles/verify.py"

echo "[2/3] Download bundle files..."
for f in manifest.json events.jsonl decision_receipt.json audit_chain.jsonl replay_manifest.json; do
  curl -sSL -o "$WORK/$BUNDLE/$f" "$SITE/bundles/$BUNDLE/$f"
done

echo "[3/3] Verify..."
python3 "$WORK/verify.py" --bundle "$WORK/$BUNDLE"
