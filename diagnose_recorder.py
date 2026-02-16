"""Quick diagnostic script to check recorder issues."""
import json
from pathlib import Path

def diagnose_recording(session_dir: str):
    """Analyze a recording session for missing steps."""
    session_path = Path(session_dir)
    metadata_path = session_path / "metadata.json"
    
    if not metadata_path.exists():
        print(f"❌ No metadata.json found in {session_dir}")
        return
    
    with open(metadata_path) as f:
        data = json.load(f)
    
    actions = data.get("actions", [])
    warnings = data.get("warnings", [])
    
    print(f"\n📊 Recording Analysis: {session_path.name}")
    print("=" * 60)
    print(f"Total actions captured: {len(actions)}")
    print(f"Warnings: {len(warnings)}")
    
    # Check for pause markers
    pauses = [a for a in actions if a.get("action") == "pause"]
    resumes = [a for a in actions if a.get("action") == "resume"]
    print(f"\n⏸️  Pauses: {len(pauses)}, Resumes: {len(resumes)}")
    
    # Check for degraded/console fallback events
    degraded = [a for a in actions if a.get("degraded") or a.get("extra", {}).get("fromConsole")]
    print(f"⚠️  Degraded events (console fallback): {len(degraded)}")
    
    # Check for missing selectors
    no_selector = [a for a in actions if not a.get("selectorStrategies")]
    print(f"🔍 Actions without selectors: {len(no_selector)}")
    
    # Time gaps analysis
    if len(actions) > 1:
        gaps = []
        for i in range(1, len(actions)):
            prev_ts = actions[i-1].get("timestampEpochMs", 0)
            curr_ts = actions[i].get("timestampEpochMs", 0)
            if prev_ts and curr_ts:
                gap = (curr_ts - prev_ts) / 1000.0  # seconds
                if gap > 5:  # More than 5 seconds
                    gaps.append((i, gap, actions[i-1].get("action"), actions[i].get("action")))
        
        if gaps:
            print(f"\n⏱️  Large time gaps detected ({len(gaps)}):")
            for idx, gap, prev_action, curr_action in gaps[:5]:
                print(f"   Step {idx}: {gap:.1f}s gap between '{prev_action}' and '{curr_action}'")
    
    # Action type breakdown
    action_types = {}
    for a in actions:
        atype = a.get("action", "unknown")
        action_types[atype] = action_types.get(atype, 0) + 1
    
    print(f"\n📋 Action Types:")
    for atype, count in sorted(action_types.items(), key=lambda x: -x[1]):
        print(f"   {atype}: {count}")
    
    # Warnings
    if warnings:
        print(f"\n⚠️  Warnings:")
        for w in warnings:
            print(f"   - {w}")
    
    print("\n" + "=" * 60)
    
    # Recommendations
    print("\n💡 Recommendations:")
    if len(pauses) > 0:
        print("   ⚠️  Recording was paused - check if you meant to pause")
    if len(degraded) > len(actions) * 0.3:
        print("   ⚠️  High degraded event rate - CSP may be blocking bindings")
    if len(no_selector) > 5:
        print("   ⚠️  Many actions missing selectors - elements may be dynamic")
    if len(actions) < 5:
        print("   ⚠️  Very few actions captured - check if recorder started properly")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python diagnose_recorder.py <session_directory>")
        print("\nExample:")
        print("  python diagnose_recorder.py recordings/20250115_143022")
        sys.exit(1)
    
    diagnose_recording(sys.argv[1])
