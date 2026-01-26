#!/usr/bin/env python3
import json, hashlib, time
from pathlib import Path

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")

def write_jsonl(p: Path, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")

def make_chain(rows):
    # egyszerű append-only hash lánc (determinista): prev + json(row)
    prev="0"*64
    out=[]
    for i,r in enumerate(rows):
        payload=json.dumps(r, sort_keys=True)
        head=hashlib.sha256((prev+payload).encode()).hexdigest()
        out.append({"i":i,"prev":prev,"head":head,"payload":r})
        prev=head
    return out, prev

def bundle(root: Path, name: str, scenario: str, decision: str, policy: str, events):
    bdir=root/name
    bdir.mkdir(parents=True, exist_ok=True)

    ts=int(time.time())
    receipt={
        "bundle": name,
        "scenario": scenario,
        "decision": decision,
        "policy_gate": policy, # ALLOW/WARN/BLOCK
        "timestamp": ts,
        "determinism": "expected",
        "inputs": {"events_sha256": None},
        "outputs": {"decision": decision, "policy_gate": policy},
        "notes": "synthetic demo bundle for mission assurance proof"
    }

    events_path=bdir/"events.jsonl"
    write_jsonl(events_path, events)

    receipt["inputs"]["events_sha256"]=sha256_file(events_path)
    write_json(bdir/"decision_receipt.json", receipt)

    chain_rows=[
        {"type":"event_stream","sha256":receipt["inputs"]["events_sha256"]},
        {"type":"decision_receipt","decision":decision,"policy_gate":policy,"ts":ts},
    ]
    chain, head = make_chain(chain_rows)
    write_jsonl(bdir/"audit_chain.jsonl", chain)

    replay={
        "bundle": name,
        "replay_steps": [
            {"action":"load_events","path":"events.jsonl","sha256":receipt["inputs"]["events_sha256"]},
            {"action":"apply_policy","policy_gate":policy},
            {"action":"emit_receipt","path":"decision_receipt.json"},
            {"action":"verify_chain","path":"audit_chain.jsonl"}
        ],
        "expected": {"policy_gate": policy, "decision": decision}
    }
    write_json(bdir/"replay_manifest.json", replay)

    manifest={
        "bundle": name,
        "created": ts,
        "files": {
            "events.jsonl": sha256_file(events_path),
            "decision_receipt.json": sha256_file(bdir/"decision_receipt.json"),
            "audit_chain.jsonl": sha256_file(bdir/"audit_chain.jsonl"),
            "replay_manifest.json": sha256_file(bdir/"replay_manifest.json"),
        },
        "chain_head": head
    }
    write_json(bdir/"manifest.json", manifest)

    return {"name":name,"chain_head":head,"manifest_sha256":sha256_file(bdir/"manifest.json")}

def main():
    root=Path("bundles")
    root.mkdir(exist_ok=True)

    out=[]

    out.append(bundle(root,
        "bundle_readiness_go_nogo",
        "Readiness & Maintenance",
        "NO-GO (defer mission)",
        "BLOCK",
        events=[
            {"t":1,"src":"sensor","k":"vibration_rms","v":9.8,"unit":"mm/s","tag":"maintenance"},
            {"t":2,"src":"log","k":"fault_code","v":"P-AXLE-OVERTEMP","tag":"readiness"},
            {"t":3,"src":"policy","k":"threshold_vibration","v":7.0,"tag":"gate"},
        ]
    ))

    out.append(bundle(root,
        "bundle_supplychain_release_gate",
        "Supply-chain Release Gate",
        "RELEASE BLOCKED (provenance mismatch)",
        "BLOCK",
        events=[
            {"t":1,"src":"sbom","k":"artifact","v":"component_X_v2.1","tag":"supply-chain"},
            {"t":2,"src":"provenance","k":"slsa_level","v":"unknown","tag":"supply-chain"},
            {"t":3,"src":"policy","k":"require_slsa","v":"SLSA>=2","tag":"gate"},
        ]
    ))

    out.append(bundle(root,
        "bundle_incident_triage",
        "Incident Triage",
        "ISOLATE + ESCALATE",
        "WARN",
        events=[
            {"t":1,"src":"net","k":"anomaly_score","v":0.92,"tag":"incident"},
            {"t":2,"src":"auth","k":"failed_logins_5m","v":47,"tag":"incident"},
            {"t":3,"src":"policy","k":"triage_action","v":"isolate_then_escalate","tag":"gate"},
        ]
    ))

    Path("bundles/index.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("OK: bundles generated:")
    for x in out:
        print(f" - {x['name']} chain_head={x['chain_head']} manifest_sha256={x['manifest_sha256']}")

if __name__=="__main__":
    main()
