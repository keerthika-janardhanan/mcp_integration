import json, re

with open('recordings/wordy/metadata.json') as f:
    metadata = json.load(f)

actions = metadata['actions']

def get_element_id(action):
    html = action.get("element", {}).get("html", "")
    
    # Try data-testid first
    testid = re.search(r'data-testid="([^"]+)"', html)
    if testid:
        return f"testid:{testid.group(1)}"
    
    # Try id attribute
    id_match = re.search(r'\bid="([^"]+)"', html)
    if id_match:
        return f"id:{id_match.group(1)}"
    
    # Try name attribute
    name_match = re.search(r'name="([^"]+)"', html)
    if name_match:
        return f"name:{name_match.group(1)}"
    
    # Fallback to css selector
    css = action.get("element", {}).get("selector", {}).get("css", "")
    return f"css:{css}" if css else ""

print("All actions and their IDs:")
for i, a in enumerate(actions):
    elem_id = get_element_id(a)
    text = a.get('visibleText', '')[:30]
    is_span = '<span' in a.get('element', {}).get('html', '')
    span_marker = '[SPAN]' if is_span else ''
    print(f"{i+1:2d}. {elem_id:40s} {span_marker:7s} {a['action']:8s} {text}")
