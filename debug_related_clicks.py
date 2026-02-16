import sys
if 'app.recorder.recorder_auto_ingest' in sys.modules:
    del sys.modules['app.recorder.recorder_auto_ingest']

from app.recorder.recorder_auto_ingest import build_refined_flow_from_metadata
import json

with open('recordings/wordy/metadata.json', 'r') as f:
    metadata = json.load(f)

# Get original actions
actions = metadata['actions']

# Test the are_related_clicks function
import re

def get_element_id(action):
    html = action.get("element", {}).get("html", "")
    testid = re.search(r'data-testid="([^"]+)"', html)
    if testid:
        return f"testid:{testid.group(1)}"
    id_match = re.search(r'\bid="([^"]+)"', html)
    if id_match:
        return f"id:{id_match.group(1)}"
    label = re.search(r'aria-label="([^"]+)"', html)
    if label:
        return f"label:{label.group(1)}"
    return None

def are_related_clicks(action1, action2):
    time1 = action1.get("timestamp", 0)
    time2 = action2.get("timestamp", 0)
    
    if abs(time2 - time1) > 1000:
        return False
    
    text1 = action1.get("visibleText", "").strip()
    text2 = action2.get("visibleText", "").strip()
    
    return text1 and text1 == text2

print("=== Testing Submit button clicks ===")
submit_clicks = [a for a in actions if 'Submit' in str(a.get('visibleText'))]
for i, a in enumerate(submit_clicks):
    elem_id = get_element_id(a)
    print(f"{i+1}. Time: {a['timestamp']}, ID: {elem_id}, Text: '{a.get('visibleText')}'")

print("\nChecking if they're related:")
if len(submit_clicks) >= 2:
    for i in range(len(submit_clicks) - 1):
        related = are_related_clicks(submit_clicks[i], submit_clicks[i+1])
        print(f"  {i+1} vs {i+2}: {related}")

print("\n=== Testing My Org Chart clicks ===")
org_clicks = [a for a in actions if 'My Org Chart' in str(a.get('visibleText'))]
for i, a in enumerate(org_clicks):
    elem_id = get_element_id(a)
    print(f"{i+1}. Time: {a['timestamp']}, ID: {elem_id}, Text: '{a.get('visibleText')}'")

print("\nChecking if they're related:")
if len(org_clicks) >= 2:
    for i in range(len(org_clicks) - 1):
        related = are_related_clicks(org_clicks[i], org_clicks[i+1])
        print(f"  {i+1} vs {i+2}: {related}")
