import json

with open('recordings/wordy/metadata.json') as f:
    metadata = json.load(f)

actions = metadata['actions']

print('=== Submit Button Clicks ===')
for a in actions:
    if 'Submit' in str(a.get('visibleText')):
        elem_id = None
        html = a['element']['html']
        
        import re
        testid = re.search(r'data-testid="([^"]+)"', html)
        if testid:
            elem_id = f"testid:{testid.group(1)}"
        
        print(f"Time: {a['timestamp']}")
        print(f"Element ID: {elem_id}")
        print(f"HTML: {html[:150]}")
        print()

print('\n=== My Org Chart Clicks ===')
for a in actions:
    if 'My Org Chart' in str(a.get('visibleText')):
        elem_id = None
        html = a['element']['html']
        
        import re
        testid = re.search(r'data-testid="([^"]+)"', html)
        label = re.search(r'aria-label="([^"]+)"', html)
        if testid:
            elem_id = f"testid:{testid.group(1)}"
        elif label:
            elem_id = f"label:{label.group(1)}"
        
        print(f"Time: {a['timestamp']}")
        print(f"Element ID: {elem_id}")
        print(f"HTML: {html[:150]}")
        print()
