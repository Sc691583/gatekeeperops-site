#!/usr/bin/env python3
import argparse, json, hashlib, sys
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def load_jsonl(p: Path):
    rows=[]
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def calc_chain_head(chain_rows):
    prev = "0"*64
    for row in chain_rows:
        payload = json.dumps(row["payload"], sort_keys=True)
        head = hashlib.sha256((prev + payload).encode()).hexdigest()
        if row.get("prev") != prev:
            return None, f"prev mismatch at i={row.get('i')}"
        if row.get("head") != head:
            return None, f"head mismatch at i={row.get('i')}"
        prev = head
    return prev, None

def main():
    ap = argparse.ArgumentParser(description="Verify Gatekeeper/SEMAF sample bundle (offline).")
    ap.add_argument("--bundle", required=True, help="Path to bundle dir (contains manifest.json)")
    args = ap.parse_args()

    bdir = Path(args.bundle).resolve()
    manifest_path = bdir / "manifest.json"
    if not manifest_path.exists():
        print("FAIL: missing manifest.json")
        return 2

    m = load_json(manifest_path)
    files = m.get("files", {})
    expected_head = m.get("chain_head")

    for rel, exp in files.items():
        p = bdir / rel
        if not p.exists():
            print(f"FAIL: missing file {rel}")
            return 2
        got = sha256_file(p)
        if got != exp:
            print(f"FAIL: sha256 mismatch {rel}\n expected: {exp}\n got: {got}")
            return 2

    chain_path = bdir / "audit_chain.jsonl"
    if chain_path.exists():
        chain_rows = load_jsonl(chain_path)
        head, err = calc_chain_head(chain_rows)
        if err:
            print("FAIL:", err)
            return 2
        if expected_head and head != expected_head:
            print("FAIL: chain_head mismatch")
            return 2

    print("PASS")
    print("bundle:", m.get("bundle"))
    print("manifest_sha256:", sha256_file(manifest_path))
    if expected_head:
        print("chain_head:", expected_head)
    return 0

if __name__ == "__main__":
    sys.exit(main())
