#!/usr/bin/env bash
set -euo pipefail

SITE="${SITE:-https://sc691583.github.io/gatekeeperops-site}"
BUNDLE="${1:-bundle_readiness_go_nogo}"

WORK="_tmp_${BUNDLE}"
rm -rf "$WORK"
mkdir -p "$WORK/$BUNDLE"

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
receipt="proof_run_${BUNDLE}_${ts}.txt"
receipt="${receipt//:/-}" # fájlnévben ne legyen :

echo "[1/3] Download verifier..."
curl -sSL -o "$WORK/verify.py" "$SITE/bundles/verify.py"

echo "[2/3] Download bundle files..."
for f in manifest.json events.jsonl decision_receipt.json audit_chain.jsonl replay_manifest.json; do
  curl -sSL -o "$WORK/$BUNDLE/$f" "$SITE/bundles/$BUNDLE/$f"
done

# kliens oldali evidence pointerek
vsha="$(python3 - <<PY
import hashlib
p=open("$WORK/verify.py","rb").read()
print(hashlib.sha256(p).hexdigest())
PY
)"
msha="$(python3 - <<PY
import hashlib
p=open("$WORK/$BUNDLE/manifest.json","rb").read()
print(hashlib.sha256(p).hexdigest())
PY
)"

echo "[3/3] Verify..."
set +e
out="$(python3 "$WORK/verify.py" --bundle "$WORK/$BUNDLE" 2>&1)"
rc=$?
set -e

status="FAIL"
if [ $rc -eq 0 ] && echo "$out" | grep -q "^PASS"; then
  status="PASS"
fi

# receipt log
{
  echo "Gatekeeper/SEMAF — Proof Run Receipt"
  echo "timestamp_utc: $ts"
  echo "site: $SITE"
  echo "bundle: $BUNDLE"
  echo "verifier_sha256: $vsha"
  echo "manifest_sha256: $msha"
  echo "status: $status"
  echo
  echo "--- verifier output ---"
  echo "$out"
} > "$receipt"

echo "$out"
echo "receipt: $receipt"

# a status kód maradjon korrekt
exit $rc
