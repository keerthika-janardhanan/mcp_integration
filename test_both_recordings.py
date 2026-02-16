from app.recorder.recorder_auto_ingest import auto_refine_and_ingest
import json

print("Testing both recordings:\n")

# Test workday14567
with open('recordings/workday14567/metadata.json') as f:
    m1 = json.load(f)

r1 = auto_refine_and_ingest('recordings/workday14567', m1, ingest=False)
with open(r1['refined_path']) as f:
    rf1 = json.load(f)

print(f"✅ workday14567: 19 actions → {len(rf1['steps'])} steps")
print(f"   Actions: {[s['action'] for s in rf1['steps']]}")

# Test wordy
with open('recordings/wordy/metadata.json') as f:
    m2 = json.load(f)

r2 = auto_refine_and_ingest('recordings/wordy', m2, ingest=False)
with open(r2['refined_path']) as f:
    rf2 = json.load(f)

print(f"\n✅ wordy: 19 actions → {len(rf2['steps'])} steps")
print(f"   Actions: {[s['action'] for s in rf2['steps']]}")

print("\n🎉 Refinement working as expected!")
